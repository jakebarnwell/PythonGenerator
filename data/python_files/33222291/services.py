import socket, time, os, pprint, pickle, sys
from time import mktime
from datetime import datetime, timedelta
# import os.path

from libs.dbconnect import dbConnector
import libs.utils

global cnf, db
cnf = "door.cnf"
# outpath = "%s/output" % os.path.dirname(__file__)
outpath = "%s/output" % sys.path[0] 


def main():
	global options, db
	options = libs.utils.load_options()
	db = dbConnector()
	
	print "OK"
	if len(sys.argv)>1:
		if sys.argv[1] == '--test':
			sendToLogger()
			sys.exit()
		if sys.argv[1] == '--lock':
			updateDoor('locked')
			sys.exit()
		if sys.argv[1] == '--unlock':
			updateDoor('unlocked')
			sys.exit()
		if sys.argv[1] == '--state':
			print db.getState()		
			sys.exit()
		if sys.argv[1] == '--sparks':
			sendSparklines()
			sendToServer()
			sys.exit()
		if sys.argv[1] == '--health':
			checkHealth()
			sys.exit()
		if sys.argv[1] == '--log':
			sendToLogger()
			sys.exit()
		if sys.argv[1] == '--tweet':
			sendTweets()
			sys.exit()
		if sys.argv[1] == '--test-tweet':
			from libs.services._twitter import Tweet
			tweet = Tweet()
			msg = "d queenvictoria %s" % (db.getState())
			if len(sys.argv) == 3:
				msg = "%s %s" % (msg, sys.argv[2])
			tweet.setMessage(msg)
			tweet.send()
			sys.exit()	

	sendUpdates()


def sendUpdates():
	global options, db

	state = db.getState()
	if libs.utils.get_option('state') != state:
		libs.utils.set_option('state', state)
		stateChanged(state)
	
	sendToLogger()
	sendTweets()
	sendRSS(state)
	sendSparklines()
	
	sendToServer()


def sendToLogger():
	global options, db
	from libs.services._pachube import Logger
	from libs.services._health import Health
	if db.getState().lower() == "unlocked":
		state = 0
	else:
		state = 1
	
	anxiety = db.getCurrentScore(3)
	health = Health()

	data = {
		"Anxiety" : anxiety,
		"Temperature" : get_int(health.data['temp']),
		"Signal" : get_int(health.data['wifi']),
		"State" : state,
		"Transmit" : int(health.data['traffic']['transmit']),
		"Receive" : int(health.data['traffic']['receive']),
	}
	logger = Logger(data)
	
def checkHealth():
	from libs.services._health import Health
	health = Health()
	output = []
	for k, v in health.data.items():
		output.append("%s %s" % (k,v))
	output = ', '.join(output)
	
	print "Sending %s" % output

#	send a state changed message
	from libs.services._twitter import Tweet
	tweet = Tweet()
	msg = "d queenvictoria %s" % (output)

	tweet.setMessage(msg)
	tweet.send()
	
	
def stateChanged(state):
#	update the twitter icon
	updateIcon(state)

	sys.stderr.write("Door state changed: %s" % state)
	
#	send a state changed message
	from libs.services._twitter import Tweet
	tweet = Tweet()
	msg = "d queenvictoria %s" % (state)

	tweet.setMessage(msg)
	tweet.send()

#	update the door last as it will die if the controller board is disconnected
	updateDoor(state)


def updateDoor(state):
	from libs.services._door import Door
	door = Door()
	if state.lower() == 'locked':
		door.lock()
	elif state.lower() == 'unlocked':
		door.unlock()

	
def sendSparklines():
	global options, db
	from libs.services._sparkline import Sparkline
	print "sendSparklines"

# FOO=`sqlite3 door_wordlist.db "SELECT r1q3 from scores WHERE date > date('$UTC') ORDER BY date DESC limit 144;"`;
#	smoothed results over the last day, 7 days and 3 weeks

	periods = [21, 1, 7, 91, 365]
	for p in periods:
# hours ago, column
		scores = db.getScores(24 * p, 3)
		print "Number of scores: %d" % len(scores)
		if not len(scores):
			print "No results for %d" % p
			continue
		data = []
		for a_score in scores:
			data.append(a_score[0])
# if we're doing 21 days then calculate the average so we can use it everywhere
		if p == 21:
			mean = sum(data)/len(data)
		print mean 

		data.reverse()
		print "Data length: %d" % len(data)
#	every pth item (24th etc) - is this to shorten the spark ?
#		data = data[::p]
#	instead return an optimal sized array
		max_width = 240
		interval = int(len(data) / 240)
		if ( interval > 1 ):
			print "Interval %d" % interval
			data = data[::interval]
		
		print "Data length: %d" % len(data)

		spark = Sparkline()
		spark.setFormat('png')
		spark.setData(data)
		spark.setOutfile('%s/spark_%dd.png' % (outpath,p))
		spark.setXAxis(mean)
		if p == 1:
			spark.setXTicks(24)
		elif p == 7:
			spark.setXTicks(7)
		elif p == 21:
			spark.setXTicks(3)
		spark.setFillColour((255,0,0,25))
		im = spark.getImage()

#	this one is all the results in order today


def sendRSS(state):
	global options, db
#	a list of days
#	1, 7, 91
	print "sendRSS"

	from libs.services._rss2 import RSS2
	
#	db = dbConnector()
#	happy 
	d7_q4 = db.getStrongestResult(7, 4)
#	fear
#	TO FIX why do we have to specify 2 days here ?
	d1_q3 = db.getStrongestResult(2, 3)
	d7_q3 = db.getStrongestResult(7, 3)
	d21_q3 = db.getStrongestResult(21, 3)
	d91_q3 = db.getStrongestResults(91, 3, 3)
	
	current_state = []
	current_state.append(state)
	current_state.append('http://door.just1.name')
#		def getScores(self, from_hours_ago=24, quality_column=3, limit=-1):
	current_score = db.getCurrentScore(3)
	
	if current_score:
		current_score = current_score[0]
		current_state.append('[Now] %d [3wk mean] %d' % (current_score, db.getMean(21)))
	else:
		current_state.append('Unknown')
	current_state.append(time.strftime('%Y-%m-%d %H:%M:%S', datetime.today().timetuple()))
	
#	print d7_q4
#	print d7_q3

	rss = RSS2()
	rss.appendItem("Currently", current_state)
	rss.appendItem("24h fear", d1_q3)
	rss.appendItem("7d fear", d7_q3)
	rss.appendItem("3wk fear", d21_q3)
	rss.appendItem("7d happy", d7_q4)
	for item in d91_q3:
		rss.appendItem("3mo fear", item)
	print rss.getXML()
	rss.saveRSS('%s/door.rss' % outpath)

def updateTwitterFollowing():
	from libs.services._twitter import Tweet
	tweet = Tweet()
	print tweet.updateFollowing()

def sendTweets():
	global options, db
#	search the db for the weeks happiest news
#	$UTC = getUTCByDateAndTimezone(date('Y-m-d H:i:s', strtotime('-7 days')), "Australia/Sydney");	
#	$SELECT = "
#		$S
#		FROM articles 
#		LEFT JOIN ratings_1 ON articles.id = ratings_1.id 
#		WHERE articles.date_utc > date('$UTC') 
#		ORDER BY ratings_1.q4 DESC
#		LIMIT 1
#	";
#	$results3 = $db->query($SELECT);

#	the_date = datetime.today() - timedelta(days=7)
#	one_week_ago = getUTCDate(time.strftime('%Y-%m-%d %H:%M:%S', the_date.timetuple()), "Australia/Sydney")

#	query = 'SELECT articles.title, articles.link, articles.id FROM articles LEFT JOIN ratings_1 ON articles.id = ratings_1.id WHERE date(articles.date_utc) > "%s" ORDER BY ratings_1.q4 DESC LIMIT 1' % (one_week_ago)

#	from pysqlite2 import dbapi2 as sqlite
#	db = sqlite.connect('door_wordlist.db')
#	cursor = db.cursor()

#	cursor.execute(query)
#	item = cursor.fetchone()

#	d7_q4 = db.getStrongestResult(7, 4)
	d7_q4 = db.getStrongestMood(7, 'happy')
#	d7_q4 = db.getStrongestMoods(7, 'happy', 3)
	item = d7_q4
	
	print item
	
#	if we've already announced the joyous news do nothing
	last_update = libs.utils.get_option('last_update')
#	last_update = '' 
	print last_update
	
	if last_update == item[4]:
		print "Already sent"
		return
	else:
		print "New update %d" % item[4]

#	otherwise continue on and send updates
		from libs.services._twitter import Tweet
		tweet = Tweet()
#	update our followers first
		tweet.updateFollowing()

#	create a short url pointing to the original article
		url = tweet.ShortenUrl(item[1], 'trim').strip()
		print url
	
#	determine any hashtags to use
		title = item[0]
	
		max_length = 140
#	trim the title if necessary
		if len(title) + len(url) >= max_length:
			print 'Trim required.'
			title = title[:max_length-len(url)-1]
	
		msg = "%s %s" % (title, url)
		print "%s [%d]" % (msg, len(msg))
			
		tweet.setMessage(msg)
		tweet.send()	
		libs.utils.set_option('last_update', item[4])		


def updateIcon(state):
#	global db
	from libs.services._twitter import Tweet
	tweet = Tweet()
	
#	if db.isLocked():
#		tweet.setImage('http://door.just1.name/wp-content/themes/icon-locked.png')
#		tweet.setImage('/home/rossetti/door/icon-locked.jpg')
#	else:
#		tweet.setImage('http://door.just1.name/wp-content/themes/icon-unlocked.png')
#		tweet.setImage('/home/rossetti/door/icon-unlocked.jpg')

	tweet.setImage("/home/rossetti/door/icon-%s.jpg" % state.lower())

def sendToServer():
#	paramiko has a nice sftp.put(self, localpath, remotepath, callback=None) 
#	Carroll Oct 1 at 13:28
	print "Sending to the server"
	import paramiko
	import os, glob, hashlib
	host = "house.laudanum.net"
	port = 2220
	try:
		transport = paramiko.Transport((host, port))
		privatekeyfile = os.path.expanduser('~/.ssh/id_rsa')
		mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
		username = 'rossetti'
		transport.connect(username = username, pkey = mykey)
		sftp = paramiko.SFTPClient.from_transport(transport)
		
		glob_pattern = "*"
		files_copied = 0
		
		for fname in glob.glob(outpath + os.sep + glob_pattern):
			is_up_to_date = False
			local_file = os.path.join(outpath, fname)
			remote_file = '/home/rossetti/door/waikato/output/' + os.path.basename(fname)
	
			try:
				if sftp.stat(remote_file):
					local_file_data = open(local_file, "rb").read()
					remote_file_data = sftp.open(remote_file).read()
					md1 = md5.new(local_file_data).digest()
					md2 = md5.new(remote_file_data).digest()
					if md1 == md2:
						is_up_to_date = True
			except:
				print "NEW: ", os.path.basename(fname),
	
			if not is_up_to_date:
				sftp.put(local_file, remote_file)
				files_copied += 1
	
		sftp.close()
		transport.close()
	except socket.error as inst:
#	socket.error: (113, 'No route to host')
		pass
	except:
		print "Couldn't send to server."
		

def get_int(val):
	import re
	m = re.match("^\d+", val)
	return int(m.group(0))

if __name__ == "__main__":
	main()
