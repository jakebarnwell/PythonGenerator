import socket
from collections import deque
from functools import partial
from tornado import ioloop
from tornado import iostream
from tornado import gen
from encode import *
from contextlib import contextmanager
import time

class RedisError(Exception): pass

class Connection(object):
    def __init__(self, address, stream):
        self.address = address
        self.stream = stream

class ConnectionManager(object):
    def __init__(self):
        self._pools = {}

    def get(self, address):
        if address in self._pools:
            pool = self._pools[address]
            assert pool is not None, "pool shouldn't be none"
            if pool:
                return pool.popleft()
        else:
            pool = deque()
            self._pools[address] = pool
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        s.connect(address)
        stream = iostream.IOStream(s)
        conn = Connection(address, stream)
        stream.set_close_callback(partial(self.on_stream_close, conn))
        return conn

    def put(self, conn):
        address = conn.address
        assert address in self._pools, "address not exists"
        pool = self._pools[address]
        assert pool is not None, "pool shouldn't be none"
        assert conn not in pool, "conn already in pool"
        pool.append(conn)

    @contextmanager
    def connect(self, address):
        conn = self.get(address)
        yield conn
        self.put(conn)

    def on_stream_close(self, conn):
        address = conn.address
        if address in self._pools:
            pool = self._pools[address]
            if conn in pool:
                pool.remove(conn)

_manager = ConnectionManager()

class RedisClient(object):
    def __init__(self, ip="127.0.0.1", port=6379, io_loop=None):
        self.address = (ip, port)
        self.io_loop = io_loop or ioloop.IOLoop.instance()

    @gen.engine
    def execute(self, cmd, callback=None):
        with _manager.connect(self.address) as conn:
            yield gen.Task(conn.stream.write, encode(cmd))
            s = yield gen.Task(conn.stream.read_until, "\r\n")
            g = decode(s[:-2])
            reply = g.next()
            while True:
                if isinstance(reply, Reply):
                    break
                s = yield gen.Task(conn.stream.read_until, "\r\n")
                reply = g.send(s[:-2])
            if callback:
                callback(reply)

class RedisChannel(object):
    def __init__(self, ip="127.0.0.1", port=6379, io_loop=None):
        self.address = (ip, port)
        self.io_loop = io_loop or ioloop.IOLoop.instance()
        self.channels = {}
        self._pending = deque()
        self.conn = _manager.get(self.address)
        self._closed = False
        self.listen()


    def execute(self, cmd, callback=None):
        print cmd
        if cmd[0] in ["subscribe", "psubscribe", "unsubscribe", "punsubscribe"]:
            for i in cmd[1:]:
                self._pending.append(callback)
        else:
            raise RedisError("command not supported")
        self.conn.stream.write(encode(cmd))

    @gen.engine
    def listen(self):
        conn = self.conn
        while not self._closed:
            s = yield gen.Task(conn.stream.read_until, "\r\n")
            g = decode(s[:-2])
            reply = g.next()
            while True:
                if isinstance(reply, Reply):
                    break
                s = yield gen.Task(conn.stream.read_until, "\r\n")
                reply = g.send(s[:-2])
            if isinstance(reply, ErrorReply):
                callback = self._pending.popleft()
                if callback:
                    callback(ErrorReply)
            elif isinstance(reply, MultiBulkReply):
                if reply.reply[0] in ["subscribe", "psubscribe"]:
                    callback = self._pending.popleft()
                    self.channels[(reply.reply[1], reply.reply[0][0]=="p")] = callback
                    assert len(self.channels)==int(reply.reply[2]), "channel num wrong"
                elif reply.reply[0] in ["unsubscribe", "punsubscribe"]:
                    self._pending.popleft()
                    if (reply.reply[1], reply.reply[0][0]=="p") in self.channels:
                        self.channels.pop((reply.reply[1], reply.reply[0][0]=="p"))
                    assert len(self.channels)==int(reply.reply[2]), "channel num wrong"
                elif reply.reply[0]=="message":
                    self.channels[(reply.reply[1], False)](reply.reply[2])
                elif reply.reply[0]=="pmessage":
                    self.channels[(reply.reply[1], True)](reply.reply[3])
            else:
                raise RedisError("reply type error")

    def close(self):
        def put_back():
            if len(self.channels):
                sub = []
                psub = []
                for k, v in self.channels.keys():
                    if v:
                        psub.append(k)
                    else:
                        sub.append(k)
                self.execute(["punsubscribe"] + psub)
                self.execute(["unsubscribe"] + sub)
                self.io_loop.add_timeout(time.time() + 5, put_back)
            else:
                self._closed = True
                _manager.put(self.conn)
        self.io_loop.add_callback(put_back)
