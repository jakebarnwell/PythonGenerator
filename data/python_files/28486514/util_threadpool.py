import sys, traceback
import Queue as queue
import threading
import collections

theVmIsGILFree = False
if sys.platform == 'cli':
    theVmIsGILFree = True
# perhaps "unladen swallow will goes GIL free.

if sys.platform == 'cli':
    # workaround for IronPython
    import System
    theAvailableNativeThreads = System.Environment.ProcessorCount
else:
    import multiprocessing
    theAvailableNativeThreads = multiprocessing.cpu_count()

INFINITE = object()

_ENDMARK = object()
_NOID = object()

class Full(queue.Full): pass
class Empty(queue.Empty): pass

class ThreadPool(object):
    __slots__ = [ '__taskQ', '__resultQ', '__workerThreads', '__taskRemains', 
        '__taskCounter', '__keepEmptyResults', '__printStackTrace' ]
    
    def __init__(self, workerCount, queueSize=None, 
            keepEmptyResults=False, printStackTrace=False):
        assert workerCount > 0
        assert queueSize is None or queueSize >= workerCount
        
        self.__printStackTrace = printStackTrace
        
        if queueSize is None:
            queueSize = workerCount
        if queueSize is INFINITE:
            self.__taskQ = queue.Queue(0) # infinite
        else:
            self.__taskQ = queue.Queue(queueSize)
        
        self.__resultQ = collections.deque() # deque is thread safe in both CPython and IronPython.
        
        self.__workerThreads = []
        for _ in xrange(workerCount):
            t = threading.Thread(target=self.__worker_func)
            t.setDaemon(True)
            t.start()
            self.__workerThreads.append(t)
            
        self.__taskRemains = 0
        self.__taskCounter = 0
        
    def __worker_func(self):
        taskQ_get = self.__taskQ.get
        taskQ_task_done = self.__taskQ.task_done
        resultQ_append = self.__resultQ.append
        
        while True:
            taskID, func, args  = taskQ_get()
            if taskID is _ENDMARK: 
                taskQ_task_done()
                break # while
            
            try:
                resultQ_append(( taskID, func(*args) ))
            except Exception, e:
                if self.__printStackTrace:
                    sys.stderr.write("".join(traceback.format_exception(*sys.exc_info())))
                resultQ_append(( taskID, e ))
                
            taskQ_task_done()
    
    def __len__(self):
        return self.__taskRemains
    
    def __nonzero__(self):
        return self.__taskRemains != 0
    
    def apply_nowait(self, func, args, taskID=_NOID):
        """
        Add a task to the thread pool. When the queue of the tread pool is full,
        raise an exception Full.
        A task is represented as a callable (func) and its arguments (args). 
        When taskID is not given, it will automatically assigned a serial number 
        starting from 1.
        """
        if not self.__workerThreads: raise ValueError("the thread pool is already join()'ed.")
        assert taskID is not _ENDMARK
        self.__taskCounter += 1
        try:
            self.__taskQ.put_nowait(( (taskID if taskID is not _NOID else self.__taskCounter), func, args ))
        except queue.Full:
            # roll back
            self.__taskCounter -= 1
            
            raise Full
        self.__taskRemains += 1
        
    def apply(self, func, args, taskID=_NOID):
        """
        Add a task to the thread pool. When the queue of the tread pool is full,
        wait until a worker thread in the pool get a task in the queue.
        A task is represented as a callable (func) and its arguments (args). 
        When taskID is not given, it will automatically assigned a serial number 
        starting from 1.
        """
        if not self.__workerThreads: raise ValueError("apply() is called for join()'ed thread pool")
        assert taskID is not _ENDMARK
        self.__taskCounter += 1
        self.__taskQ.put(( (taskID if taskID is not _NOID else self.__taskCounter), func, args ))
        self.__taskRemains += 1
        
    def get_nowait(self):
        """
        If there is no task in the thread pool, raise Empty.
        Otherwise, if no task in the pool finished, return None.
        Otherwise, remove a finished task in the pool and return a tuple 
        of its taskID and its return value. 
        In case of a task raising an exception, the returned tuple will have
        task ID and the exception.
        """
        if self.__taskRemains == 0: raise Empty
        if not self.__resultQ:
            return None # no available result now
        r = self.__resultQ.popleft()
        self.__taskRemains -= 1
        return r
            
    def get(self):
        """
        If there is no task in the thread pool, raise Empty.
        get() can call after calling join() of the thread pool.
        In case of a task raising an exception, the returned tuple will have
        task ID and the exception.
        """
        if self.__workerThreads: raise ValueError("get() is called for not join()'ed thread pool")
        if self.__taskRemains == 0: return Empty
        r = self.__resultQ.popleft()
        self.__taskRemains -= 1
        return r
            
    def join(self):
        """
        Wait until all tasks in the thread pool finish.
        """
        if self.__workerThreads is None: return
        for _ in self.__workerThreads:
            self.__taskQ.put(( _ENDMARK, None, None ))
        for t in self.__workerThreads:
            t.join()
        self.__taskQ.join()
        self.__workerThreads = None
        
    def get_iter(self):
        """
        Repeat get() up-to maxCount times. 
        get_iter() can call after calling join() of the thread pool.
        """
        if self.__workerThreads: raise ValueError("get_iter() is called for not join()'ed thread pool")
        
        self_resultQ_popleft = self.__resultQ.popleft
        
        while self.__taskRemains != 0:
            r = self_resultQ_popleft()
            self.__taskRemains -= 1
            yield r
    
    def get_iter_nowait(self):
        """
        Repeat get_nowait() up-to maxCount times. 
        """
        self_resultQ_popleft = self.__resultQ.popleft
        
        while self.__taskRemains != 0 and self.__resultQ:
            r = self_resultQ_popleft()
            self.__taskRemains -= 1
            yield r
    
    def apply_iter(self, tasks, func=None):
        """
        Repeat apply() for the given tasks, call join(), and repeat get() until
        all results of the tasks being extracted.
        tasks is an iteratable, and each item of tasks is a tuple.
        When func is None, an item is either; (function, args, taskID) or
        (function, args). When func is a callable, an item is either;
        (args, taskID) or (args,).
        """
        if not self.__workerThreads: raise ValueError("apply_iter() is called for join()'ed thread pool")
        if self.__taskRemains != 0: raise ValueError("apply_iter() requires no task remains in the thread pool")
        assert self.__taskRemains == 0
        
        if func is None:
            self_get_iter_nowait = self.get_iter_nowait
            self_apply = self.apply
            
            for task in tasks:
                for v in self_get_iter_nowait(): yield v
                if len(task) in ( 2, 3 ):
                    self_apply(*task)
                else:
                    raise ValueError("apply_iter()'s argument task must be a tuple with length 2 or 3")
        else:
            self_get_iter_nowait = self.get_iter_nowait
            self_taskQ_put = self.__taskQ.put
            
            def __apply2(args, taskID=_NOID):
                assert taskID is not _ENDMARK
                self.__taskCounter += 1
                self_taskQ_put(( (taskID if taskID is not _NOID else self.__taskCounter), func, args ))
                self.__taskRemains += 1
                
            for task in tasks:
                for v in self_get_iter_nowait(): yield v
                if len(task) in ( 1, 2 ):
                    __apply2(*task)
                else:
                    raise ValueError("apply_iter(,,func=...)'s argument task must be a tuple with length 1 or 2")
        self.join()
        for v in self.get_iter():
            yield v
    
if __name__ == '__main__':
    import time, random
    
    stdoutLock = threading.Condition()
    def lockedPrint(message):
        stdoutLock.acquire()
        print message
        stdoutLock.release()
    
    def func(t):
        funcID = str(t)
        lockedPrint("func %s started" % funcID)
        time.sleep(t)
        lockedPrint("func %s stopped" % funcID)
        return funcID
        
    pool = ThreadPool(4, INFINITE)
    
    for t in xrange(30):
        t = random.random() * 1 # 0 to 1.0
        pool.apply_nowait(func, (t, ))
        lockedPrint("remaining tasks: %d" % len(pool))
        v = pool.get_nowait()
        if v is not None:
            taskID, result = v
            lockedPrint("taskID=%s result=%s" % (repr(taskID), repr(result)))
            assert not isinstance(result, Exception)
        time.sleep(0.1)
    lockedPrint("remaining tasks: %d" % len(pool))
    
    pool.join()
    lockedPrint("now joined")
    
    lockedPrint("remaining tasks: %d" % len(pool))
    for taskID, result in pool.get_iter():
        lockedPrint("taskID=%s result=%s" % (repr(taskID), repr(result)))
        assert not isinstance(result, Exception)
    assert len(pool) == 0
        
