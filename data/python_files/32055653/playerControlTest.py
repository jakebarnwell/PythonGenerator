import unittest
import yaml
# from struct import *
# import muzykaProtocol
# from muzykaProtocol.muzykaFrame import muzykaFrame
# from FrameProcessor import FrameProcessor
# from PlayerFrameProcessor import PlayerFrameProcessor
# from QueueFrameProcessor import QueueFrameProcessor

import QueueEntry
from QueueEntry import QueueEntry

import PlayerControl
from PlayerControl import *

class testPlayerControl(unittest.TestCase):
	def setUp(self):
			"""
			set up data used in the tests.
			setUp is called before each test function execution.
			"""
	def testPlayerControlInitAndQueueOperations(self):
		pc = PlayerControl(False) # Disable audio playback
		
		# Player should be in STOP state
		self.assertEqual( pc.state , PlayerControl.STATE_STOP )
		# Without any queue entries, the currentQueueEntry should be set to None
		self.assertEqual( pc.currentQueueEntry , None )
		
		firstQueueItem = QueueEntry( QueueEntry.TYPE_FILE, "./dummyMP3Test.mp3")
		pc.addQueueItem(firstQueueItem)
		self.assertEqual( pc.getQueue()[0].toString() ,
		 									QueueEntry( QueueEntry.TYPE_FILE, "./dummyMP3Test.mp3").toString() ,"The list is in an unexcepted state")
		self.assertEqual( pc.getQueue()[0] , firstQueueItem )
		# When the first item is stored in the queue, the currentQueueEntry should be updated.
		self.assertEqual( pc.currentQueueEntry , 0 )
		
		# Delete the item from the list
		pc.removeQueueItem(0)
		# The currentQueueEntry should be set to None again
		self.assertEqual( pc.currentQueueEntry , None )
		
		pc.addQueueItem(firstQueueItem)
		secondQueueItem = QueueEntry( QueueEntry.TYPE_FILE, "./dummyMP3Test2.mp3")
		pc.addQueueItem(secondQueueItem)
		
		# currentQueueEntry should point to the beginning of the queue.
		self.assertEqual( pc.currentQueueEntry , 0 )
		pc.next()
		# currentQueueEntry should now point to the next QueueEntry
		self.assertEqual( pc.currentQueueEntry , 1 )
		pc.next()
		# currentQueueEntry should point to the beginning again, when you call
		# next() on the last QueueEntry.
		self.assertEqual( pc.currentQueueEntry , 0 )
		
		# Test PlayerControl.prev()
		pc.prev()
		self.assertEqual( pc.currentQueueEntry , 1 )
		pc.prev()
		self.assertEqual( pc.currentQueueEntry , 0 )
		
		
		
		
def suite():
	suite = unittest.TestSuite()
	suite.addTest(unittest.makeSuite(testPlayerControl))
	return suite

if __name__ == '__main__':
	suiteFew = unittest.TestSuite()
	suiteFew.addTest(testPlayerControl("testPlayerControlInitAndQueueOperations"))
	unittest.TextTestRunner(verbosity=2).run(suite())
