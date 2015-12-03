import threading
import logging
import socket
import select


import Settings
import EventLoop

import ProxyClient


class ProxyServer(threading.Thread):
    """docstring for Server"""
    def __init__(self, hostname, port, outHost, outPort, adminLoop,latency=0.0):
        logging.debug('Initializing Server')
        #initialize threading properties
        threading.Thread.__init__(self,name='ServerThread-%d'%port)
        self.setDaemon(True) 

        # init instance variables
        self.hostname = hostname 
        self.port = port
        self.adminLoop = adminLoop
        self.latency = latency
        self.threads = {}
        self.in_select = []

        self.outPort = outPort 
        self.outHost = outHost 

        # define constants
        self.MAXCONNECTIONS = 5
        #register for messages on admin bus

        self.setHandlers()
        self.connIndex=0


    def run(self):
        """docstring for run"""
        self.running = True
        self.createServer()
        logging.debug('Server started')
        while self.running:
            # socket selector
            #sys.stderr.write("ServerThread: "+  str( self.in_select)+"\n")
            (inbound,outbound,error) = select.select(self.in_select,[],[],Settings.TIMEOUT)

            # handle inbound connection
            for sock in inbound:
                self.onSelectTCP(sock)

            # treat messages
            while not self.adminLoop.isEmpty():
                self.adminLoop.dispatchMessage(self.adminLoop.getMessage())


        # wait for child threads to complete
        for sock,th in self.threads.iteritems():
            th.join()
        self.socket.close()
        logging.debug('Server stopped')
        
        
    def createServer(self):
        """ create a TCP server """
        logging.debug('Bind port %d on %s' % (self.port, self.hostname))
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind( (self.hostname,self.port) )
        self.socket.listen(self.MAXCONNECTIONS)
        self.isServer = True
        self.in_select.append(self.socket)

    def onSelectTCP(self,sock):
        """ select TCP """
        logging.debug('Processing inbounce connection on port %d' % self.port)
        if self.isServer and (sock == self.socket):
            (cnx,addr) = sock.accept()
            self.threads[cnx] = ProxyClient.ProxyClient(cnx,self.outHost,self.outPort, self.adminLoop,"%d-%d" %(self.port,self.connIndex), self.latency)
            self.connIndex = self.connIndex +1
            self.threads[cnx].start()
        else:
            pass

    def setHandlers(self):
        """ attach handlers to events """
        self.adminLoop.attachHandler(Settings.ADM_QUIT_PROGRAM,self.onQuit)
        self.adminLoop.attachHandler(Settings.THREAD_CLOSE,self.onProxyClose)
        

    def onQuit(self,data):
        """ ADM_QUIT_PROGRAM handler """
        #self.in_select = []
        self.running = False
        logging.debug('Closing Server')

    def onProxyClose(self,data):
        self.threads[data].join()

