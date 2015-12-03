import logging
from wordgravity import jmain
from google.appengine.api import urlfetch
from Location import add
from Fetcher import uqu
from Fetcher import getHead
from Fetcher import getBody
from bs import ICantBelieveItsBeautifulSoup as ibs
from bs import Comment as ibsComment
import webapp2
import urllib2
import re

remove_list = { }#'welcome':1,'the':1,'and':1,'to':1,'they':1,'a':1,'he':1,'she':1,'it':1,'an':1,'of':1,'in':1,'for':1,'that':1,'this':1,'html':1,'http':1,'www':1, 'https':1 }
dic = {"&yuml;": "y", "&Iuml;": "I", "&iuml;": "i", "&uuml;": "u", "&szlig;": "s", "&Ntilde;": "N", "&Yacute;": "Y", "&ntilde;": "n", "&THORN;": "T", "&Euml;": "E", "&oslash;": "o", "&ETH;": "D", "&AElig;": "A", "&ccedil;": "c", "&thorn;": "t", "&eth;": "e", "&aelig;": "a", "&Oslash;": "O", "&Uuml;": "U", "&Ccedil;": "C"}
class Summarer(webapp2.RequestHandler):
	def getKey(self,uri):
		result = None
		summary = None
		try:
			result = urlfetch.fetch(uri,method=urlfetch.HEAD,deadline=3,allow_truncated=True)
		except:
			pass
		if result is not None and result.status_code == 200:
			cl = result.headers.get('Content-Length')
			ct = result.headers.get('Content-Type')
			if ct is not None and 'html' not in ct or cl is not None and int(cl) > 555555:
				return self.uriKey(uri),summary
		try:
			result = urlfetch.fetch(uri,deadline=6,allow_truncated=True)
		except:
			return self.uriKey(uri),summary
		if result is not None and result.status_code == 200:
			title = getTitle(result,uri)
			summary = getSummary(result)
			if title is not None:		
				suri = summariseTitle(title)
				if suri is not None:
					return suri,summary
		return self.uriKey(uri),summary

	def uriKey(self,uri):		
		uriparts = uri.partition('//')
		urimain = uriparts[0] if len(uriparts[1]) == 0 else uriparts[2]
		return urimain.partition('/')[0]
	
	def post(self):
		uri = self.request.POST['uri']
		uri = uqu(uri)
		key,summary = self.getKey(uri)	
		key = 'mized/' + key
		#now i have to create the summary page
		key = add(key,uri,summary)
		self.response.out.write(key)
		
	def get(self):
		self.redirect('http://op.to/')

def unescape(s):
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = s.replace("&quot;", "'")
    # this has to be last:
    splits = re.split(r'(&#\w+;|&\w+;)',s)
    news = []
    for split in splits:
	if split[:2] == '&#':
		try:
			split = unichr(int(split[2:-1]))
		except:
			continue
	elif split[:1] == '&':
		try:
			split = dic[split]
		except:
			continue
	news.append(split)
    s = ''.join(news)
    s = s.replace("&amp;", "&")
    return s

def getSummary(result):
	parsed = ibs(result.content)
	to_extract = parsed.findAll(text=lambda text:isinstance(text, ibsComment))
	for item in to_extract:
    		item.extract()
	to_extract = parsed.findAll('noscript')
	for item in to_extract:
    		item.extract()
	to_extract = parsed.findAll('script')
	for item in to_extract:
    		item.extract()
	to_extract = parsed.findAll('li')
	for item in to_extract:
    		item.extract()
	paras = [' '.join(x.findAll(text=True)) for x in parsed.findAll('p')]
	zz = unescape('. '.join([unicode(a.strip()) for a in paras if len(a.strip()) > 2 and not (a.strip().lower())[:4] == 'http']))
	#zz += unescape(', '.join([unicode(a.strip()) for a in parsed.body(text=True) if len(a.strip()) > 2 and not (a.strip().lower())[:4] == 'http']))
	#zz is the rawtext
	zz = jmain(zz)
	return zz

def getTitle(result,uri):
	content = result.content
	finds = re.search(r'<\s*title\s*>(?P<title_content>[^<]*)<',content,re.UNICODE|re.IGNORECASE)
	titleText = []
	if finds is not None:
		fs = str(finds.group('title_content')).strip()
		if len(fs) > 0:
			titleText.append(unescape(fs))
	if len(titleText) == 0:
		finds = re.findall(r'\w[\w\.\'-]+\w|\w\w|\w',uri)	
		for find in finds:
			titleText.append(find)
	if len(titleText) == 0:
		return None
	return ' '.join(titleText)

def summariseTitle(title):
	title = re.split(r'[|/<>]|--',title)
	tmax = title[0]
	for t in title:
		if len(t) > len(tmax):
			tmax = t
	title = tmax
	try:
		titleWords = re.findall(r'\w[\w\'-]+\w|\w\w|\w',title,re.UNICODE)
	except:
		titleWords = re.split(' ')
	summaryTitle = []
	stlen = 0
	for word in reversed(titleWords):
		lword = word.lower()
		if lword in remove_list:
			continue
		elif re.match(r'\d+',lword) and len(lword) > 4 :
			continue
		elif len(lword) == 0 or len(lword) > 20:
			continue
		try:
			wt = word.encode('utf-8')
		except:
			continue
		lwt = len(wt)
		if '.' not in wt or wt.count('.') >= lwt-1:
			wt = wt.capitalize()
			if '\'' in wt and wt[-2] != '\'':
				wt = wt.title() # like O'Brien
		if lwt > 0:		
			summaryTitle.append(wt)
		stlen += lwt
		if stlen > 104:
			break
	if len(summaryTitle) > 0:
		if summaryTitle[-1][-1] != '+':
			return '.'.join(reversed(summaryTitle)) +'+'
	return None

app = webapp2.WSGIApplication([
	(r'/u/.*',Summarer)
	])

