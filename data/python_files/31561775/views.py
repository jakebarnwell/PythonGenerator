import os, datetime, time
from stat import *

from django.template import RequestContext
from django.core.context_processors import csrf
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
import meweb.client.ipc as ipc
from threading import Thread, Lock

mutex = Lock()
cmd_type = 0
fname = None
worker_on = False

"""
0 sync
1 get
2 put
"""

def worker_handler():
    print "worker start"
    while mutex.acquire():
        #sync
        if cmd_type == 0:
            print "SYNC!!!"
            ipc.sync()
        #get
        elif cmd_type == 1:
            print "GET!!!"
            ipc.get(fname)
        #put
        elif cmd_type == 2:
            print "PUT!!!"
            ipc.put(fname)

def get_files(files, nextpath):
    #os.chdir('..')
    print os.getcwd()
    os.chdir(nextpath)
    path = os.getcwd()
    for fil in os.listdir("."):
        print fil
        #go into sub folders for more files
        if os.path.isdir(fil):
            get_files(files, fil)
        #else add file to list
        else:
            st = os.stat(fil)
            t = time.asctime(time.localtime(st[ST_MTIME]))
            size =  st[ST_SIZE]
            tmp = {'name': fil, 'time': t, 'size':size}
            files.append(tmp)
    os.chdir('..')
    #os.chdir('meweb/')
    print os.getcwd()

def list_files(request):
    global worker_on
    if worker_on == False:
        ipc.open_socket()
        worker_on = True
        mutex.acquire()
        print "mutex acquire"
        t = Thread(target=worker_handler)
        t.start()

    files = []
    root = os.getcwd()
    print root
    get_files(files, root)
    #print files
    return render_to_response('client.html', {'files':files})

def sync(request):
    global cmd_type
    print "sync"
    cmd_type = 0
    try:
        mutex.release()
    except:
        print "lock is already open."
    print "done."
    return HttpResponse('Syncronization complete!')

def pull_all(request):
    print "pull all"
    files = []
    get_files(files, 'files/')
    for item in files:
        ipc.get(item['name'])
    print "done."
    return HttpResponse('Everything was successfully pulled!')

def push_all(request):
    print "push all"
    files = []
    get_files(files, 'files/')
    for item in files:
        ipc.put(item['name'])
    print "done."
    return HttpResponse('Everything was successfully pushed!')

def pull_file(request):
    global cmd_type
    global fname
    print "pull file"
    if 'f' not in request.GET:
        return HttpResponse('No file specified.')
    filename = request.GET['f']
    print filename
    cmd_type = 1
    fname = filename
    try:
        mutex.release()
    except:
        print "lock is already open."
    print "done."
    return HttpResponse('The file: ' + filename + ' has been pulled.')

def push_file(request):
    global cmd_type
    global fname
    print "push file"
    if 'f' not in request.GET:
        return HttpResponse('No file specified.')
    filename = request.GET['f']
    fname = filename
    print filename
    cmd_type = 2
    try:
        mutex.release()
    except:
        print "lock is already open."
    print "done."
    return HttpResponse('The file: ' + filename + ' has been pushed.')

def delete_file(request):   
    if 'f' not in request.GET:
        return HttpResponse('No file specified.')
    filename = request.GET['f']
    return HttpResponse('The file: ' + filename + ' has been deleted.')
