import unittest
import yaml
from struct import *
import muzykaProtocol
from muzykaProtocol.muzykaFrame import muzykaFrame
from FrameProcessor import FrameProcessor
from PlayerFrameProcessor import PlayerFrameProcessor
from QueueFrameProcessor import QueueFrameProcessor

import QueueEntry
from QueueEntry import QueueEntry

import PlayerControl
from PlayerControl import *

class testMuzykaPlayer(unittest.TestCase):
	def setUp(self):
			"""
			set up data used in the tests.
			setUp is called before each test function execution.
			"""
	def testMuzykaProtocolParseFrame(self):
		mf = muzykaFrame( muzykaProtocol.PLAYER, muzykaProtocol.PLAYER_STOP, "NYAN")
		parsedFrame = muzykaFrame(mf.toString())
		# self.assertTrue(True)
		
		# All frame properties should be equal
		self.assertEqual(mf.commandgroup, parsedFrame.commandgroup)
		self.assertEqual(mf.subcommand, parsedFrame.subcommand)
		self.assertEqual(mf.payload, parsedFrame.payload)
		
	def testMuzykaFrameToString(self):
		mf = muzykaFrame( muzykaProtocol.PLAYER, muzykaProtocol.PLAYER_STOP, "NYAN")
		self.assertEqual(mf.toString()[0], muzykaProtocol.MFS )
		self.assertEqual(mf.toString()[1], muzykaProtocol.PLAYER )
		self.assertEqual(mf.toString()[2], muzykaProtocol.PLAYER_STOP )
		self.assertEqual(mf.toString()[3:-1], "NYAN" )
		self.assertEqual(mf.toString()[-1], muzykaProtocol.MFE )
		
	# =========================
	# = Frame Processor tests =
	# =========================
	def testAbstractDefinitionOfProcessors(self):
		try:
			fp = FrameProcessor()
			fp.process("")
			# The Frame Processor should Raise a NotImplementedError.
			# Therefore, you should not access the next expression.
			self.assertTrue(False, "FrameProcessor.process() should raise an exception!")
		except NotImplementedError, e:
			# An exception has been raised. This is the desired action.
			self.assertTrue(True)
	  
		try:
			playerControl = PlayerControl()
			pfp = PlayerFrameProcessor(playerControl)
			pfp.process(muzykaFrame( muzykaProtocol.PLAYER, muzykaProtocol.PLAYER_PLAY, ""))
			# The Frame Processor _shouldnt_ raise a NotImplementedError.
			# Therefore, you should be able to access the next expression.
			self.assertTrue(True)
		except NotImplementedError, e:
			# An exception should not be raised. Test should fail otherwise.
			self.assertTrue(False,"PlayerFrameProcessor raises an exception on process()")
  
	# Send a PLAYER Frames and test their correct handling	
	def testPlayerFrames(self):
		playerControl = PlayerControl()
		playerFrameProcessor = PlayerFrameProcessor(playerControl)
		
		# Create PLAYER_PLAY frame and process it
		mf = muzykaFrame( muzykaProtocol.PLAYER, muzykaProtocol.PLAYER_PLAY, "")
		response = playerFrameProcessor.process(mf)
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.PLAYER,
		 									muzykaProtocol.PLAYER_PLAY, muzykaProtocol.SERVER_ACK ).toString(),
											"The Processor response for PLAYER_PLAY is invalid")
		
		# Create PLAYER_STOP frame and process it
		mf = muzykaFrame( muzykaProtocol.PLAYER, muzykaProtocol.PLAYER_STOP, "")
		response = playerFrameProcessor.process(mf)
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.PLAYER,
		 									muzykaProtocol.PLAYER_STOP, muzykaProtocol.SERVER_ACK ).toString(),
											"The Processor response for PLAYER_STOP is invalid")
		
		# Create PLAYER_PAUSE frame and process it
		mf = muzykaFrame( muzykaProtocol.PLAYER, muzykaProtocol.PLAYER_PAUSE, "")
		response = playerFrameProcessor.process(mf)
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.PLAYER,
		 									muzykaProtocol.PLAYER_PAUSE, muzykaProtocol.SERVER_ACK ).toString(),
											"The Processor response for PLAYER_PAUSE is invalid")		
		
		# Test the handling of PLAYER subcommands, which havent been implemented.
		try:
			mf = muzykaFrame( muzykaProtocol.PLAYER, '\xFF', "")
			playerFrameProcessor.process(mf)
			# The Player Frame Processor should raise a NotImplementedError.
			# Therefore, you should not access the next expression.
			self.assertTrue(False, "An unimplemented subcommand in PLAYER should raise a NotImplementedError Exception")
		except NotImplementedError, e:
			# An exception has been raised. This is the desired action.
			self.assertTrue(True)
		
		
		
		
	# Send QUEUE Frames and test their correct handling	
	def testQueueFrames(self):
		playerControl = PlayerControl()
		queueFrameProcessor = QueueFrameProcessor(playerControl)
		
		# Create QUEUE_ADD frame and process it
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_ADD,
											yaml.dump({'type': 'song', 'song_id': 5}))
		response = queueFrameProcessor.process(mf)
		
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_ADD, muzykaProtocol.SERVER_ACK + str(0) ).toString(),
											"The QueueFrameProcessor response for QUEUE_ADD is invalid. The response should be SERVER_ACK with id 0")
											
		# print playerControl.getQueue()[0].toString()
		self.assertEqual( playerControl.getQueue()[0].toString() , QueueEntry( QueueEntry.TYPE_SONG, 5).toString() ,"The list is in an unexcepted state")
		
		# Create QUEUE_ADD frame and process it
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_ADD,
											yaml.dump({'type': 'song', 'song_id': 30000}))
		response = queueFrameProcessor.process(mf)
		
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_ADD, muzykaProtocol.SERVER_ACK + str(1) ).toString(),
											"The QueueFrameProcessor response for QUEUE_ADD with a song is invalid. The response should be SERVER_ACK with id 1")
											
		# self.assertEqual( playerControl.getQueue() , [5,30000],"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[0].toString() , QueueEntry( QueueEntry.TYPE_SONG, 5).toString() ,"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[1].toString() , QueueEntry( QueueEntry.TYPE_SONG, 30000).toString() ,"The list is in an unexcepted state")
		
		
		# Create QUEUE_ADD frame and process it
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_ADD,
											yaml.dump({'type': 'song', 'song_id': 3000000000}))
		response = queueFrameProcessor.process(mf)
		
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_ADD, muzykaProtocol.SERVER_ACK + str(2) ).toString(),
											"The QueueFrameProcessor response for QUEUE_ADD with a song is invalid. The response should be SERVER_ACK with id 2")
											
		# self.assertEqual( playerControl.getQueue() , [5,30000,3000000000],"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[0].toString() , QueueEntry( QueueEntry.TYPE_SONG, 5).toString() ,"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[1].toString() , QueueEntry( QueueEntry.TYPE_SONG, 30000).toString() ,"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[2].toString() , QueueEntry( QueueEntry.TYPE_SONG, 3000000000).toString() ,"The list is in an unexcepted state")
		
		# Test the removal of queue items.
		# Begin with a removal request which is out of bounds.
		
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_REMOVE, 3)
		response = queueFrameProcessor.process(mf)
		
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_REMOVE, muzykaProtocol.QUEUE_ENTRY_NOT_FOUND ).toString(),
											"The QueueFrameProcessor response for QUEUE_REMOVE is invalid. The response should \
											 be QUEUE_ENTRY_NOT_FOUND because the requested index is too damn high")
											
		# The queue shouldnt been altered.
		# self.assertEqual( playerControl.getQueue() , [5,30000,3000000000],"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[0].toString() , QueueEntry( QueueEntry.TYPE_SONG, 5).toString() ,"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[1].toString() , QueueEntry( QueueEntry.TYPE_SONG, 30000).toString() ,"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[2].toString() , QueueEntry( QueueEntry.TYPE_SONG, 3000000000).toString() ,"The list is in an unexcepted state")
		
		# Perform a valid remove request
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_REMOVE, 1)
		response = queueFrameProcessor.process(mf)
		
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_REMOVE, muzykaProtocol.SERVER_ACK ).toString(),
											"The QueueFrameProcessor response for QUEUE_REMOVE is invalid. The response should \
											 be SERVER_ACK and the list should be queue.PRE.size()-1")
											
		# The item in the  middle should have been removed.
		# self.assertEqual( playerControl.getQueue() , [5,3000000000],"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[0].toString() , QueueEntry( QueueEntry.TYPE_SONG, 5).toString() ,"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[1].toString() , QueueEntry( QueueEntry.TYPE_SONG, 3000000000).toString() ,"The list is in an unexcepted state")
		
		# Perform a QUEUE_LIST request
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_LIST, "")
		response = queueFrameProcessor.process(mf)
		
		self.assertEqual(response.toString(),
		 									muzykaFrame( muzykaProtocol.QUEUE,
		 																muzykaProtocol.QUEUE_LIST,
		 																yaml.dump( [QueueEntry( QueueEntry.TYPE_SONG, 5),
																								QueueEntry( QueueEntry.TYPE_SONG, 3000000000)] ) 
																	).toString(),
											"The QueueFrameProcessor response for QUEUE_LIST is invalid. The response should \
											 be a YAML serialized queue list")
											
		# # The item in the  middle should have been removed.
		# self.assertEqual( playerControl.getQueue() , [5,3000000000],"The list is in an unexcepted state")
		
		# Perform a QUEUE_INSERT_SONG_AT request
		# mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_INSERT_SONG_AT, pack('ii',1,23) )
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_INSERT_AT,
											yaml.dump({'type': 'song', 'song_id': 23, 'idx': 1}))

		response = queueFrameProcessor.process(mf)
		
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_INSERT_AT, muzykaProtocol.SERVER_ACK + str(1) ).toString(),
											"The QueueFrameProcessor response for QUEUE_INSERT_AT is invalid. The response should \
											 be SERVER_ACK + '1'")
											
		# The item 23 should now be in the middle of the queue.
		# self.assertEqual( playerControl.getQueue() , [5,23,3000000000],"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[0].toString() ,
		 									QueueEntry( QueueEntry.TYPE_SONG, 5).toString() ,"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[1].toString() ,
		 									QueueEntry( QueueEntry.TYPE_SONG, 23).toString() ,"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[2].toString() ,
		 									QueueEntry( QueueEntry.TYPE_SONG, 3000000000).toString() ,"The list is in an unexcepted state")
		
		
		# Perform a QUEUE_INSERT_SONG_AT request out of bounds
		# mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_INSERT_SONG_AT, pack('ii',500,42) )
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_INSERT_AT,
											yaml.dump({'type': 'song', 'song_id': 42, 'idx': 500}))
		
		response = queueFrameProcessor.process(mf)
		
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_INSERT_AT, muzykaProtocol.SERVER_ACK + str(3) ).toString(),
											"The QueueFrameProcessor response for QUEUE_INSERT_AT is invalid. The response should \
											 be SERVER_ACK + '3'")
											
		# The item 42 should be at the end of the queue.
		# self.assertEqual( playerControl.getQueue() , [5,23,3000000000,42],"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[0].toString() ,
		 									QueueEntry( QueueEntry.TYPE_SONG, 5).toString() ,"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[1].toString() ,
		 									QueueEntry( QueueEntry.TYPE_SONG, 23).toString() ,"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[2].toString() ,
		 									QueueEntry( QueueEntry.TYPE_SONG, 3000000000).toString() ,"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[3].toString() ,
		 									QueueEntry( QueueEntry.TYPE_SONG, 42).toString() ,"The list is in an unexcepted state")
		
		playerControl.flushQueue()
		
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_ADD,
											yaml.dump({'type': 'file', 'path': "./dummyMP3Test.mp3"}))
		
		response = queueFrameProcessor.process(mf)
		
		self.assertEqual( playerControl.getQueue()[0].toString() ,
		 									QueueEntry( QueueEntry.TYPE_FILE, "./dummyMP3Test.mp3").toString() ,"The list is in an unexcepted state")

		# mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_INSERT_FILE_AT, pack('is', 0 ,) )
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_INSERT_AT,
											yaml.dump({'type': 'file', 'path': "./dummyMP3Test2.mp3", 'idx': 0}))

		response = queueFrameProcessor.process(mf)
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_INSERT_AT, muzykaProtocol.SERVER_ACK + str(0) ).toString(),
											"QUEUE_INSERT_AT with valid filepath doesnt respond with SERVER_ACK")		
		
		
		self.assertEqual( playerControl.getQueue()[0].toString() ,
		 									QueueEntry( QueueEntry.TYPE_FILE, "./dummyMP3Test2.mp3").toString() ,"The list is in an unexcepted state")
		self.assertEqual( playerControl.getQueue()[1].toString() ,
		 									QueueEntry( QueueEntry.TYPE_FILE, "./dummyMP3Test.mp3").toString() ,"The list is in an unexcepted state")
		
	# Send QUEUE Frames and test their correct handling	
	def testMoreInvalidQueueFrames(self):	
		playerControl = PlayerControl()
		queueFrameProcessor = QueueFrameProcessor(playerControl)
		
		# Test a non-existing file
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_ADD,
											yaml.dump({'type': 'file', 'path': "./djakdj231ndile.bla"}))

		response = queueFrameProcessor.process(mf)
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_ADD, muzykaProtocol.FILE_NOT_FOUND ).toString(),
											"QUEUE_ADD with invalid filepath doesnt respond with FILE_NOT_FOUND")		
	
		# Create a QUEUE_ADD frame and process it
		# It doesnt contain a valid entry TYPE in the yaml params and should
		# therefore return INVALID_FRAME
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_ADD,
											yaml.dump({'type': 'unknownTypeOfEntry', 'song_id': 30000}))
		response = queueFrameProcessor.process(mf)
    
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_ADD, muzykaProtocol.INVALID_FRAME ).toString(),
											"The QueueFrameProcessor response for QUEUE_ADD with an invalid frame is invalid. The response should be INVALID_FRAME")
		
	

	# ================================
	# = Test the PlayerControl Class =
	# ================================
	def testPlayerControlClass(self):
		pc = PlayerControl()
		pc.addQueueItem(5)
		self.assertEqual(pc.getQueue(), [5])
		
		# Test queue item removal in an unallowed range
		self.assertFalse(pc.removeQueueItem(2) , "You cannot delete an item at index 2 if there is only 1 item in the queue" )
		pc.addQueueItem(6)
		
		# Test queue item removal on a valid index
		self.assertTrue(pc.removeQueueItem(1) , "You should be able to delete a queue item by a valid index" )
		
		# Create an empty queue
		pc.flushQueue()
		self.assertEqual(pc.getQueue(), [], "Queue should be empty after flushQueue")
		
		pc.addQueueItem(1)
		pc.addQueueItem(2)
		pc.addQueueItem(3)
		
		# Set the current queue entry pointer to a valid value. True must be returned.
		self.assertTrue(pc.setCurrentQueueEntry(1))

		# Set the current queue entry pointer to an invalid value. False must be returned.
		self.assertFalse(pc.setCurrentQueueEntry(3))
	
	# ============================================================
	# = Test the adding of audio files by a given directory path =
	# ============================================================
	def testAddingDirectories(self):
		pc = PlayerControl()
		queueFrameProcessor = QueueFrameProcessor(pc)
		
		# Test a non-existing directory
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_ADD,
											yaml.dump({'type': 'file', 'path': "./noneExistingDir/"}))

		response = queueFrameProcessor.process(mf)
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_ADD, muzykaProtocol.FILE_NOT_FOUND ).toString(),
											"QUEUE_ADD with invalid filepath doesnt respond with FILE_NOT_FOUND")
		# Add an existing directory
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_ADD,
											yaml.dump({'type': 'file', 'path': "./testAudioFiles/"}))
    
		response = queueFrameProcessor.process(mf)
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_ADD, muzykaProtocol.SERVER_ACK + str(0) ).toString(),
											"QUEUE_ADD with a valid directory doesnt respond with SERVER_ACK")
		
		# Check the entries of the list
		self.assertEqual( pc.getQueue()[0].toString() ,
		 									QueueEntry( QueueEntry.TYPE_FILE, "./testAudioFiles/audio1.mp3").toString() ,"The list is in an unexcepted state")
		self.assertEqual( pc.getQueue()[1].toString() ,
		 									QueueEntry( QueueEntry.TYPE_FILE, "./testAudioFiles/audio2.mp3").toString() ,"The list is in an unexcepted state")
		
		# There should only be 2 audio files in the queue. 
		self.assertEqual( len (pc.getQueue()), 2)
		
		pc.flushQueue()
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_ADD,
											yaml.dump({'type': 'file', 'path': "./dummyMP3Test.mp3"}))
		queueFrameProcessor.process(mf)
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_ADD,
											yaml.dump({'type': 'file', 'path': "./dummyMP3Test2.mp3"}))
		queueFrameProcessor.process(mf)

		# There should be 2 audio files in the queue now. 
		self.assertEqual( len (pc.getQueue()), 2)							

			
		# Use INSERT_AT to add the contents of the directory testAudioFiles
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_INSERT_AT,
											yaml.dump({'type': 'file', 'path': "./testAudioFiles", 'idx': 1}))
											
		response = queueFrameProcessor.process(mf)
		# muzykaFrame.debugString(response.toString())
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_INSERT_AT, muzykaProtocol.SERVER_ACK + str(1) ).toString(),
											"QUEUE_ADD with a valid directory doesnt respond with SERVER_ACK")											
		
		# There should be 4 audio files in the queue now. 
		self.assertEqual( len (pc.getQueue()), 4)							
		
		# Check the entries of the list
		self.assertEqual( pc.getQueue()[0].toString() ,
		 									QueueEntry( QueueEntry.TYPE_FILE, "./dummyMP3Test.mp3").toString() ,"The list is in an unexcepted state")
		self.assertEqual( pc.getQueue()[1].toString() ,
		 									QueueEntry( QueueEntry.TYPE_FILE, "./testAudioFiles/audio1.mp3").toString() ,"The list is in an unexcepted state")
		self.assertEqual( pc.getQueue()[2].toString() ,
		 									QueueEntry( QueueEntry.TYPE_FILE, "./testAudioFiles/audio2.mp3").toString() ,"The list is in an unexcepted state")
		self.assertEqual( pc.getQueue()[3].toString() ,
		 									QueueEntry( QueueEntry.TYPE_FILE, "./dummyMP3Test2.mp3").toString() ,"The list is in an unexcepted state")
		
		
	# Send QUEUE Frames and test their correct handling	
	def testAddingURLs(self):	
		pc = PlayerControl()
		queueFrameProcessor = QueueFrameProcessor(pc)
  
		# Test a faulty URL
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_ADD,
											yaml.dump({'type': 'url', 'path': "xxxx://bla.de:9303"}))
  
		response = queueFrameProcessor.process(mf)
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_ADD, muzykaProtocol.INVALID_FRAME ).toString(),
											"QUEUE_ADD with invalid url doesnt respond with INVALID_FRAME")
											
		# Test a correct URL
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_ADD,
											yaml.dump({'type': 'url', 'path': "http://207.200.96.229:8030"}))
    
		response = queueFrameProcessor.process(mf)
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_ADD, muzykaProtocol.SERVER_ACK + str(0) ).toString(),
											"QUEUE_ADD with valid url doesnt respond with SERVER_ACK")
											
		# Test a correct URL
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_INSERT_AT,
											yaml.dump({'type': 'url', 'path': "http://207.200.96.229:8031", 'idx': 0}))
    
		response = queueFrameProcessor.process(mf)
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_INSERT_AT, muzykaProtocol.SERVER_ACK + str(0) ).toString(),
											"QUEUE_INSERT_AT with valid url doesnt respond with SERVER_ACK")

		self.assertEqual( pc.getQueue()[0].toString() ,
		 									QueueEntry( QueueEntry.TYPE_URL, "http://207.200.96.229:8031").toString() ,"The list is in an unexcepted state")
		self.assertEqual( pc.getQueue()[1].toString() ,
		 									QueueEntry( QueueEntry.TYPE_URL, "http://207.200.96.229:8030").toString() ,"The list is in an unexcepted state")
	def testSetCurrentQueueEntry(self):
		pc = PlayerControl()
		queueFrameProcessor = QueueFrameProcessor(pc)
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_SET_CURRENT_QUEUE_ENTRY,
											str(1) )
  
		response = queueFrameProcessor.process(mf)
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_SET_CURRENT_QUEUE_ENTRY, muzykaProtocol.QUEUE_ENTRY_NOT_FOUND ).toString(),
											"QUEUE_SET_CURRENT_QUEUE_ENTRY with an invalid queue entry id should respond QUEUE_SET_CURRENT_QUEUE_ENTRY")
											
		# Add a queue entry to test the method
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_INSERT_AT,
											yaml.dump({'type': 'url', 'path': "http://207.200.96.229:8031", 'idx': 0}))
    
		response = queueFrameProcessor.process(mf)

		# Send QUEUE_SET_CURRENT_QUEUE_ENTRY again with 0 as payload. This should be working.
		mf = muzykaFrame( muzykaProtocol.QUEUE, muzykaProtocol.QUEUE_SET_CURRENT_QUEUE_ENTRY,
											str(0) )
  
		response = queueFrameProcessor.process(mf)
		self.assertEqual(response.toString(), muzykaFrame( muzykaProtocol.QUEUE,
		 									muzykaProtocol.QUEUE_SET_CURRENT_QUEUE_ENTRY, muzykaProtocol.SERVER_ACK ).toString(),
											"QUEUE_SET_CURRENT_QUEUE_ENTRY with a valid queue entry id should respond SERVER_ACK")

		
		
def suite():
	suite = unittest.TestSuite()
	suite.addTest(unittest.makeSuite(testMuzykaPlayer))
	return suite

if __name__ == '__main__':
	suiteFew = unittest.TestSuite()
	suiteFew.addTest(testMuzykaPlayer("testMuzykaProtocolParseFrame"))
	suiteFew.addTest(testMuzykaPlayer("testMuzykaFrameToString"))
	suiteFew.addTest(testMuzykaPlayer("testAbstractDefinitionOfProcessors"))
	suiteFew.addTest(testMuzykaPlayer("testPlayerFrames"))
	suiteFew.addTest(testMuzykaPlayer("testPlayerControlClass"))
	suiteFew.addTest(testMuzykaPlayer("testQueueFrames"))
	suiteFew.addTest(testMuzykaPlayer("testMoreInvalidQueueFrames"))
	suiteFew.addTest(testMuzykaPlayer("testAddingDirectories"))
	suiteFew.addTest(testMuzykaPlayer("testAddingURLs"))
	suiteFew.addTest(testMuzykaPlayer("testSetCurrentQueueEntry"))
	unittest.TextTestRunner(verbosity=2).run(suite())
