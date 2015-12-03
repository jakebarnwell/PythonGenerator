import urllib
import os
import socket
import commands
import sys

import logging

import simplejson as json
import pymongo

CONF_FILENAME = "twitter.conf"

class TwitterCrawler:
  URL = "http://search.twitter.com/search.json?"

  def __init__(self, words=[], username=None, password=None):
    self.password = password
    self.username = username
    self.query_args = dict()
        

  def readConfiguration(self, filename):
    import yaml

    f = open(filename)
    self.conf = yaml.load(f, Loader=yaml.CLoader)
    f.close()
    
    location = "%s,%s,%s" \
        % (self.conf['latitude'], self.conf['longitude'], self.conf['radius'])

    self.update_args(geocode = location)

    # mongodb connection
    self.connection = pymongo.Connection(self.conf['mongodb_host'])
    self.collection = self.connection[self.conf['mongodb_db']][self.conf['mongodb_collection']]

  def update_args(self, **kwargs):
    self.query_args.update(kwargs)

  def _get_url(self, url, params=dict()):
      
    params = urllib.urlencode(params)
    data = dict()
          
    logging.info("%s%s" % (url, params))
    f = urllib.urlopen(url+params)

    json_data = f.read()
    data = json.loads(json_data)
    
    if (data.has_key('results')==False):
      logging.error("Error calling API")
      return None
    
    return data
  
  def get_latest_tweets(self):

    result = self._get_url(self.URL, self.query_args)
    
    return result

  def process_tweets(self, tweets):
      
    for t in tweets:
      try:
        self.collection.insert(t)
        #TODO: fix this to a more specific exception
      except Exception, inst:
        logging.error("error processing tweet: %s - %s" % (t, inst))
  
  def start(self):
      
    # we should get here the last tweet id saved
    resultset = self.get_latest_tweets()
      
    self.process_tweets(resultset['results'])
    while (resultset.has_key('next_page')):
      next_page = self.URL + resultset['next_page'][1:]
      resultset = self._get_url(next_page)

      self.process_tweets(resultset['results'])

    #ok exit.. for another 5 minutos or so


def check_running_and_kill(name):
    ''' in this function we check if there is another
    process running (previous job).. if it is kill it 
    because he is tooo slow processing tweets'''

    COMMAND = "ps x -o pid,args | grep python | grep %s | grep -v grep" % name
  
    data = commands.getoutput("ps x -o pid,args | grep python | grep %s | grep -v grep" % name)
    
    mypid = os.getpid()
    for l in data.split('\n'):
        pid = int(l.strip().split(' ')[0])
        if pid != mypid:
            os.kill(pid, 9)

def run():

  logging.basicConfig(filename="twitter.log", level=logging.DEBUG)
  check_running_and_kill(sys.argv[0])
    
  # condif default socket timeout
  # to 10 seconds
  socket.setdefaulttimeout(10)

  t = TwitterCrawler()
  
  path = os.path.dirname(__file__)
  t.readConfiguration(path+os.sep+CONF_FILENAME)

  #try:
  t.start()
  #except Exception, inst:
  #  logging.critical(inst)

if __name__=="__main__":
  run()

