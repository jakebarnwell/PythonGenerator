import os
import pickle
import re
from django.utils import simplejson as json
from UserService import UserService
import httplib
import urllib
from datetime import datetime
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import RequestHandler, WSGIApplication
from google.appengine.api.urlfetch import fetch as urlfetch, GET, POST
from wsgiref.handlers import CGIHandler
from google.appengine.ext import webapp
import ShortLink

class BlankCredentialsException(Exception):
    pass

class WrongCredentialsException(Exception):
    pass

AppID		= '179976055368084'
AppSecret	= 'fe4b52bcc577d5c130b1dfbd3d50d5ce'

class FacebookStatusUpdater:
    def __init__(self, user):
        try:
            self.config = json.loads(user.facebook)
            self.user = user
        except Exception, err:
            pass
        self.httpheaders = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}

    def checkUserCredentials(self):
        if not hasattr(self, 'config'):
            return False
        return self.config['access_token'] != ""

    def login(self):
        if not self.checkUserCredentials():
            raise BlankCredentialsException()
        self.verifyCredentials()

    @staticmethod
    def requestAuthenticationURL():
        base = "https://www.facebook.com/dialog/oauth?"
        prop = ['client_id='+AppID, 'redirect_uri=http://grafiteapp.appspot.com/facebook/authenticated/',
            'scope=offline_access,publish_stream,read_stream,user_birthday,friends_birthday,manage_notifications']
        return base + '&'.join(prop)

    def verifyCredentials(self):
        reqStr = 'access_token='+self.config['access_token']
        httpscon = httplib.HTTPSConnection("graph.facebook.com")
        httpscon.request("GET","/me?"+reqStr)
        res = httpscon.getresponse()
        data = res.read()
        #print data
        if str(res.status)!='200':
            raise WrongCredentialsException()

    def updateStatus(self,statusObj,to='me'):
        reqStr = None
        target = ""
        if 'link' in statusObj:
            curUrl = statusObj['link']['url']
            reqStr = urllib.urlencode({'access_token':self.config['access_token'],
                        'message':statusObj['status'],
                        'link':statusObj['link']['url'],
                        'caption':"Posted from Grafite!",
                        "name":"",
                        "description":statusObj['link']['description'] if statusObj['link']['description'] else ""
            })
            target = "/%s/links"%to
        else:
            reqStr = urllib.urlencode({'access_token':self.config['access_token'],'message':statusObj['status']})
            target = "/%s/feed"%to
        httpscon = httplib.HTTPSConnection("graph.facebook.com")
        httpscon.request("POST",target,reqStr,self.httpheaders)
        res = httpscon.getresponse()
        #print res.status, res.reason
        data = res.read()
        #print data
        if str(res.status)=='200':
            fb = json.loads(self.user.facebook)
            obj = json.loads(data)
            
            #update our records..
            fb['total_statuses'] += 1
            fb['latest_status_id'] = obj['id']
            self.user.facebook = json.dumps(fb)
            self.user.put()
            
            obj['result'] = "success"
            return obj
        else:
            return  {'result':"error",'status':res.status, 'message':data}
	    
    def getDPSrc(self):
        if self.checkUserCredentials():
            return "https://graph.facebook.com/me/picture?access_token="+self.config['access_token']
        return ""
    def getAccessToken(self):
        if self.checkUserCredentials():
            return self.config['access_token']
        return None

    def getLastStatusDetails(self):
        try:
            reqStr = 'access_token='+self.config['access_token']
            httpscon = httplib.HTTPSConnection("graph.facebook.com")
            httpscon.request("GET","/me/statuses?"+reqStr)
            res = httpscon.getresponse()
            s = res.read()
            #print s
            if str(res.status) == '200':
                return json.loads(s)
        except Exception, e:
            return None
            
    def getUserFeed(self,pagingUrl):
        try:
            reqStr = 'access_token='+self.config['access_token']
            httpscon = httplib.HTTPSConnection("graph.facebook.com")
            httpscon.request("GET",pagingUrl if pagingUrl else ("/me/home?"+reqStr))
            res = httpscon.getresponse()
            s = res.read()
            #print s
            if str(res.status) == '200':
                return json.loads(s)
            return None
        except Exception, e:
            return None
    
    def getPostComments(self,postId):
        try:
            reqStr = 'access_token='+self.config['access_token']
            httpscon = httplib.HTTPSConnection("graph.facebook.com")
            httpscon.request("GET","/%s?"%postId+reqStr)
            res = httpscon.getresponse()
            s = res.read()
            #print s
            if str(res.status) == '200':
                return json.loads(s)
            return None
        except Exception, e:
            return None

    def getProfileDetails(self):
        try:
            reqStr = 'access_token='+self.config['access_token']
            httpscon = httplib.HTTPSConnection("graph.facebook.com")
            httpscon.request("GET","/me?"+reqStr)
            res = httpscon.getresponse()
            s = res.read()
            #print s
            if str(res.status) == '200':
                return json.loads(s)
            return None
        except Exception, e:
            return None

    def getNotifications(self):
        try:
            reqStr = 'access_token='+self.config['access_token']
            httpscon = httplib.HTTPSConnection("graph.facebook.com")
            httpscon.request("GET","/me/notifications/?"+reqStr)
            res = httpscon.getresponse()
            s = res.read()
            #print s
            if str(res.status) == '200':
                return json.loads(s)
            return None
        except Exception, e:
            return None
        
    def getFriends(self):
        try:
            reqStr = 'access_token='+self.config['access_token']
            httpscon = httplib.HTTPSConnection("graph.facebook.com")
            httpscon.request("GET","/me/friends?"+reqStr)
            res = httpscon.getresponse()
            s = res.read()
            
            if str(res.status) == '200':
                return json.loads(s)['data']
        except Exception, e:
            return None
    
    def postLike(self,postId,like):
        try:
            reqStr = 'access_token='+self.config['access_token']
            httpscon = httplib.HTTPSConnection("graph.facebook.com")
            httpscon.request("POST" if like else "DELETE","/"+postId+"/likes?"+reqStr)
            res = httpscon.getresponse()
            s = res.read()
            
            if str(res.status) == '200':
                return json.loads(s)
        except Exception, e:
            return {"result":"error","res":s}

    def postComment(self,postId,text):
        try:
            httpscon = httplib.HTTPSConnection("graph.facebook.com")
            reqStr = 'access_token='+self.config['access_token']
            target = "/"+postId+"/comments?"+reqStr
            body = urllib.urlencode({'message':text})
            httpscon.request("POST" if True else "DELETE","/"+postId+"/comments?"+reqStr,body)
            res = httpscon.getresponse()
            s = res.read()
            
            if str(res.status) == '200':
                return {"result":"success","content":json.loads(s)}
            return {"result":"error","message":json.loads(s), "t":target}
        except Exception, e:
            return {"result":"error","res":s}
    
    def runFQLQuery(self,query):
        try:
            httpscon = httplib.HTTPSConnection("api.facebook.com")
            reqStr = 'access_token='+self.config['access_token']
            reqStr += "&format=json&query=" + urllib.quote(query,'')
            url = "/method/fql.query?"+reqStr
            httpscon.request("GET",url)
            res = httpscon.getresponse()
            s = res.read()
            
            if str(res.status) == '200':
                return {"result":"success","content":json.loads(s)}
            return {"result":"error","message":json.loads(s)}
        except Exception, e:
            return {"result":"error","res":s}

    def getFriendsBirthdays(self):
        today = datetime.now()
        today = "%02d/%02d"%(int(today.month),int(today.day))
        query = "SELECT name,uid,birthday_date from user where uid in (SELECT uid2 FROM friend WHERE uid1=me()) and strpos(birthday_date,'%s')>=0"%today
        return self.runFQLQuery(query)
        
    @staticmethod
    def getAuthenticationStatus(user):
        fb = FacebookStatusUpdater(user)
        try:
            fb.login()
            return "",fb
        except BlankCredentialsException, e:
            return "blank credentials",None
        except WrongCredentialsException, e:
            return "wrong credentials",None
        except Exception, e:
            return "Unknown Error",None
        


class FacebookService(webapp.RequestHandler):
    def get(self,job):
        user = UserService.getCurrentUser(self)
        if not user and job in ['authenticate','authenticated']:
            UserService.getCurrentUserOrRedirect(self)
            return
        elif not user:
            self.response.out.write(json.dumps({"result":"error","message":"unauthorised"}))
            return
        if job not in ['authenticate','authenticated','feed','comments','birthdays','notifications','accessToken']:
            self.error(404)
            return
        getattr(self,job)(user)
        
    def post(self,job):
        user = UserService.getCurrentUserOrRedirect(self)
        if not user:
            return
        if job not in ['update','status','like','comment']:
            self.error(404)
            return
        getattr(self,job)(user)
       
    def authenticate(self,user):
        self.redirect(FacebookStatusUpdater.requestAuthenticationURL())
        self.error(302)
        return

    def notifications(self,user):
        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(json.dumps(FacebookService.getNotifications(user)))

    def like(self,user):
        self.response.headers["Content-Type"] = "application/json"
        pid = self.request.get("postId")
        like = self.request.get("like")
        if pid in (None,"") or like in (None,""):
            self.response.out.write(json.dumps({"result":"error","message":"Incorrect parameters"}))
        self.response.out.write(json.dumps(FacebookService.postLike(user,pid, True if like.lower()=='like' else False)))
        
    def authenticated(self,user):
        if self.request.get("code") not in (None, ""):
            url = 'https://graph.facebook.com/oauth/access_token?'
            props = ['client_id='+AppID,'redirect_uri=http://grafiteapp.appspot.com/facebook/authenticated/',
                'client_secret='+AppSecret,'code='+self.request.get("code")]
            url = url + '&'.join(props)
            res = urlfetch(url)
            if str(res.status_code) == '200':
                pos = str(res.content).find("access_token=")
            if pos != -1:
                token = str(res.content)[pos + len('access_token='):]
                user.facebook = json.dumps({"access_token":token,"total_statuses":0,"latest_status_id":""})
                user.put()
        self.redirect('/userHome')
        self.error(302)

    def accessToken(self, user):
        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(json.dumps(FacebookService.getUserAccessToken(user)))
        
        
    def feed(self,user):
        self.response.headers["Content-Type"] = "application/json"
        paging = None
        if self.request.get('paging') not in (None,""):
            paging = self.request.get('paging')
        self.response.out.write(json.dumps(FacebookService.getUserFeed(user,paging)))
        
    def birthdays(self,user):
        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(json.dumps(FacebookService.getFriendsBirthdays(user)))
    
    def comments(self,user): #get comments
        self.response.headers["Content-Type"] = "application/json"
        if self.request.get('id') in (None,""):
            self.response.out.write(json.dumps({"result":"error","message":"id missing!"}))
        self.response.out.write(json.dumps(FacebookService.getPostComments(user,self.request.get('id'))))

    def comment(self,user): #post comment
        self.response.headers["Content-Type"] = "application/json"
        if self.request.get('postId') in (None,""):
            self.response.out.write(json.dumps({"result":"error","message":"id missing!"}))
        if self.request.get('comment') in (None,""):
            self.response.out.write(json.dumps({"result":"error","message":"id missing!"}))
        self.response.out.write(json.dumps(FacebookService.postComment(user,self.request.get('postId'),self.request.get('comment'))))

    def status(self,user):
        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(json.dumps(FacebookService.getStatus(user)))

    def update(self,user):
        self.response.headers["Content-Type"] = "application/json"
        if self.request.get("status") in (None,""):
            self.response.out.write(json.dumps({"result":"error","message":"status field missing."}))
            return
        to = 'me'
        if self.request.get("to") not in (None,""):
            to = self.request.get("to")
        self.response.out.write(json.dumps(FacebookService.updateStatus(user,{"status":self.request.get("status")},to)))

    @staticmethod
    def getUserAccessToken(user):
        res,FBUser = FacebookStatusUpdater.getAuthenticationStatus(user)
        if res != "":
            return {"result":"error","message":"Unauthorised"}
        return {"result":"success", "data":FBUser.getAccessToken()}
        
    @staticmethod
    def getStatus(user):
        status,usr = FacebookStatusUpdater.getAuthenticationStatus(user)
        if status!= "":
            return {"result":"error","message":"unauthorised",
            "link":ShortLink.getShortUrl("http://grafiteapp.appspot.com/userHome?access_token=%s&redirect=%s"%
            (user.accessToken,"/facebook/authenticate/"))}
        obj = usr.getLastStatusDetails()
        if not obj:
            return {"result":"error","message":"Unable to retrieve details"}
        comments = 0
        try:
            comments=len(obj['data'][0]['comments']['data'])
        except Exception,e:
            pass
        likes = 0
        try:
            likes=len(obj['data'][0]['likes']['data'])
        except Exception,e:
            pass

        return {"result":"success","status":obj['data'][0]['message'],
            "likes":likes,
            "comments":comments,
            "DPSrc":usr.getDPSrc(),
            "link":"http://www.facebook.com/profile.php?id=%s&sk=wall"%obj['data'][0]['from']['id']
            }
    @staticmethod
    def getNotifications(user):
        status,usr = FacebookStatusUpdater.getAuthenticationStatus(user)
        if status!= "":
            return {"result":"error","message":"unauthorised"}
        return {"result":"success","data":usr.getNotifications()}

    @staticmethod
    def getFriendsBirthdays(user):
        status,usr = FacebookStatusUpdater.getAuthenticationStatus(user)
        if status!= "":
            return None
        return usr.getFriendsBirthdays()

    @staticmethod
    def getUser(user):
        return FacebookStatusUpdater.getAuthenticationStatus(user)[1]

    @staticmethod
    def updateStatus(user,statusObj,to='me'):
        status,usr = FacebookStatusUpdater.getAuthenticationStatus(user)
        if status!= "":
            return None
        return usr.updateStatus(statusObj,to)
    
    @staticmethod
    def getUserFeed(user,paging):
        res,FBUser = FacebookStatusUpdater.getAuthenticationStatus(user)
        if res != "":
            return {"result":"error","message":"User isn't using Facebook", "value":False}
        return FBUser.getUserFeed(paging)

    @staticmethod
    def getPostComments(user,pid):
        res,FBUser = FacebookStatusUpdater.getAuthenticationStatus(user)
        if res != "":
            return {"result":"error","message":"User isn't using Facebook", "value":False}
        return FBUser.getPostComments(pid)

    @staticmethod
    def isFriends(user1,user2):
        res,FBUser = FacebookStatusUpdater.getAuthenticationStatus(user1)
        if res != "":
            return {"result":"error","message":"You aren't using Facebook", "value":False}

        res,otherFBUser = FacebookStatusUpdater.getAuthenticationStatus(user2)
        if res != "":
            return {"result":"error","message":user2.Nickname + " isn't using Facebook", "value":False}

        otherUserId = otherFBUser.getProfileDetails()['id']
        friends = FBUser.getFriends() or []
        
        friends = map(lambda x: x['id'], friends)
        
        if otherUserId in friends:
            return {"result":"success","value":True, "disconnect":"#"}
        return {"result":"success","value":False, "connect":'http://www.facebook.com/addfriend.php?id='+otherUserId}

    @staticmethod
    def postLike(user, postId, like):
        res,FBUser = FacebookStatusUpdater.getAuthenticationStatus(user)
        if res != "":
            return {"result":"error","message":"You aren't using Facebook", "value":False}
        return FBUser.postLike(postId, like)
        
    @staticmethod
    def postComment(user, postId, text):
        res,FBUser = FacebookStatusUpdater.getAuthenticationStatus(user)
        if res != "":
            return {"result":"error","message":"You aren't using Facebook", "value":False}
        return FBUser.postComment(postId, text)
