import cookielib, socket, urllib, urllib2, urllib, sys 
from urllib import urlretrieve
from shutil import copyfile
from .views.SubscriptsViews import getIntereses
from twisted.internet import reactor
from twisted.python import log
import json, os
import pickle
import threading
from autobahn.websocket import WebSocketServerFactory, \
				WebSocketServerProtocol, \
				listenWS
				
wss = set()
temas = {}
idSs = {}
refreshws = True
def reload(a = ''):
	refreshws = True
	
def notify(titulo, idTema):
	refreshws = True
	for wxs in wss:	
		if refreshws:
			temas[wxs] = [int(m['idTema']) for m in getIntereses(idSs[wxs])]
		if idTema in temas[wxs]:
			wxs.sendMessage(str(titulo))
	refreshws = False
		
class PushServerProtocol(WebSocketServerProtocol):
	
	def onOpen(self):
		wss.add(self)
		idSs[self] = 1
		refreshws = True

	def onMessage(self, msg, binary):
		idSs[self] = int(msg)
		refreshws = True
		

	def onClose(self, wasClean, code, reason):
		wss.discard(self)
		idSs[self] = 1
		refreshws = True

class PushServer ( threading.Thread ):
	def run ( self ):
			log.startLogging(sys.stdout)

			factory = WebSocketServerFactory("ws://localhost:9000", debug = False)
			factory.protocol = PushServerProtocol
			listenWS(factory)
			
			reactor.run()
			
			
			