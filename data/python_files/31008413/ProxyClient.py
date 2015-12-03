import threading
import logging
import socket
import select
from time import sleep

import Settings
import EventLoop
import pickle


class ProxyClient(threading.Thread):
    """docstring for Proxy"""
    def __init__(self, inSock,outHost,outPort,adminLoop, threadIndex,latency ):
        self.proxyName = 'ProxyThread-%s' % threadIndex

        threading.Thread.__init__(self,name=self.proxyName)
        self.setDaemon(True) 

        self.inSock = inSock
        self.outPort = outPort 
        self.outHost = outHost 
        self.outSock = None
        self.adminLoop = adminLoop
        self.threadIndex = threadIndex
        self.latency = latency

        self.in_select = []
        self.in_select.append(inSock)
        self.setHandlers()
      
    def run(self):
        self.running = True
        self.createOutboundConnection()
        if self.running:
            logging.debug('%s started' % self.proxyName)
        while self.running:
            # socket selector
            #sys.stderr.write(self.proxyName+  str( self.in_select)+"\n")
            (inbound,outbound,error) = select.select(self.in_select,[],[],Settings.TIMEOUT)

            # handle inbound connection
            for sock in inbound:
                self.onSelectTCP(sock)

        logging.debug('Closing %s' % self.proxyName)
        self.inSock.close()
        self.outSock.close()
        self.inSock = None
        self.outSock = None
        logging.debug('%s stopped' % self.proxyName)


    def createOutboundConnection(self):
        """docstring for createOutboundConnection"""
        logging.debug('Initiate connection to %s on %d' % ( self.outHost,self.outPort))
        try:
            self.outSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.outSock.connect((self.outHost,self.outPort))
            self.in_select.append(self.outSock)
            logging.debug('Connect successfull')
        except socket.error, (errno,message):
            logging.error('Error while connecting to %s on %d: %s' % ( self.outHost,self.outPort, message))
            self.running=False
            self.adminLoop.postMessage((Settings.THREAD_CLOSE,self.inSock))
        

    def setHandlers(self):
        """ attach handlers to events """
        self.adminLoop.attachHandler(Settings.ADM_QUIT_PROGRAM,self.onQuit)
        self.adminLoop.attachHandler(Settings.THREAD_CLOSE,self.onQuit)
        

    def onQuit(self,data):
        """ ADM_QUIT_PROGRAM handler """
        if self.running:
            self.running = False
            #self.in_select = []

    def onSelectTCP(self,sock):
        """ select TCP """
        data = None
        try:
            data = sock.recv(Settings.BUFFSIZE)
            logging.debug("Received data:%s", pickle.dumps(data))

        except:
            pass
        targetSock = None
        if (sock == self.inSock):
            targetSock = self.outSock
       
        if (sock == self.outSock):
            targetSock = self.inSock
    
        if not data:
            #targetSock.shutdown()
            self.running=False
        else:
            if self.latency > 0:
                sleep(self.latency)

            targetSock.send(data)

