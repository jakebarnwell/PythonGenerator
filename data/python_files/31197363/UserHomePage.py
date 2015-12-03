import cgi
import re

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import os
import logging
from time import time    
from google.appengine.api import memcache, users
from google.appengine.ext.webapp.template import render

from UserService import UserService
from UserService import GrafiteUser
from UserService import time_format
from django.utils import simplejson as json
from FacebookService import FacebookService
from BuzzService import BuzzService
from TwitterService import TwitterService
from StatusService import StatusService

class temp:
    pass

class UserHomePage(webapp.RequestHandler):
    def get(self):
        user = UserService.getCurrentUserOrRedirect(self)
        if not user:
            return
        if self.request.get("redirect"):
            self.response.headers.add_header('Set-Cookie',UserService.makeCookieString(
            user.getLoginExpirationTime().strftime(time_format),{"access_token":user.accessToken}))
            self.response.headers.add_header('Content Type',"text/Html")
            self.redirect(self.request.get("redirect"))
            self.error(302)
            return

        DATA = temp()
        DATA.user = user
        DATA.accessToken = user.accessToken
        DATA.lastAccessTime = user.dateLastAccessed
        try:
            DATA.settings = json.loads(user.settings)
        except Exception,err:
            obj = {"TwitterShortenURL":False,"TwitterSplitStatus":False}
            user.settings = json.dumps(obj)
            user.put()
            DATA.settings = obj
        DATA.userServices = []

        for service in ['Facebook','Buzz','Twitter']:
            setattr(DATA,service.lower(),temp())
            usr = eval(service+'Service').getUser(user)
            if usr is not None:
                DATA.userServices.append(service)
                getattr(DATA,service.lower()).authenticationStatus = ""
            else:
                getattr(DATA,service.lower()).authenticationStatus = "Unauthorised"
        
        DATA.userservicesJSON = json.dumps(DATA.userServices)
        
        
        path = os.path.join(os.path.dirname(__file__), 'html/userHome.html')
        self.response.out.write(render(path, {'DATA':DATA}))

        
	
class UserProfilePage(webapp.RequestHandler):
    def get(self,userID):
        if userID == '' and self.request.get('type') in (None,""):
            self.renderSearchPage()
            return
        elif self.request.get('type') == 'search':
            self.searchUser()
            return
        elif self.request.get('type') == 'profileDetails':
            self.getProfileDetails()
            return
        self.userProfileView(userID)

    def getProfileDetails(self):
        userID = self.request.get('UserID')
        if userID in (None,""):
            self.response.out.write(json.dumps({"result":"error","message":"UserID not specified!"}))
            return

        if userID == "@me":
            curUser = UserService.getCurrentUserOrJsonError(self)
            if curUser is None:
                return
            self.response.out.write(json.dumps({"result":"success", "data":self._getProfileDetails(curUser)}))
            return

        c = GrafiteUser.all().filter("nickname =",userID)
        curUser = None
        if c.count():
            curUser = c.fetch(1)[0]
        else:
            try:
                curUser = GrafiteUser.get(db.Key(encoded=userID))
            except Exception, e:
                self.response.out.write(json.dumps({"result":"error","message":"No User!"}))
                return
        self.response.out.write(json.dumps(self._getProfileDetails(curUser)))

    def searchUser(self):
        if self.request.get('q') in (None,""):
            allUsers = GrafiteUser.all().fetch(30)
            allUsers = map(lambda x: UserProfilePage._getProfileDetails(x), [])
            self.response.out.write(json.dumps({"result":"success","data":allUsers}))
            return
        query = str(self.request.get('q'))
        exactMatches = []
        import re
        if re.match(r'^([a-zA-Z0-9_\-\.]+)@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,3})$',query):
            try:
                exactMatches.append(UserProfilePage._getProfileDetails(GrafiteUser.get_by_key_name(query)))
            except Exception,e:
                pass
            self.response.out.write(json.dumps({"result":"success", "data":exactMatches}))
            return
        
        exactMatches,matches = [],[]
        allUsers = GrafiteUser.all().fetch(GrafiteUser.all().count())
        for x in allUsers:
            if hasattr(x, "nickname"):
                if str(x.nickname).lower() == str(query).lower():
                    exactMatches.append(UserProfilePage._getProfileDetails(x))
                elif str(query).lower() in str(x.nickname).lower():
                    matches.append(UserProfilePage._getProfileDetails(x))
        exactMatches.extend(matches)
        self.response.out.write(json.dumps({"result":"success", "data":exactMatches}))

    def userProfileView(self,userID):
        user = UserService.getCurrentUser(self)

        DATA = temp()
        if user:
            DATA.user = user
        
        c = GrafiteUser.all().filter("nickname =",userID)
        if c.count():
            DATA.profileUser = c.fetch(1)[0]
        else:
            try:
                DATA.profileUser = GrafiteUser.get(db.Key(encoded=userID))
                DATA.profileUser.gUserId = str(DATA.profileUser.key())
            except Exception, e:
                self.response.out.write("OOPS! no such profile exists! Whence did you come?")
                self.error(404)
                return
        
        DATA.userServices = []
        DATA.friends = []
        for serviceStr in ['Facebook','Buzz','Twitter']:
            setattr(DATA,serviceStr.lower(),temp())
            service = eval(serviceStr+'Service')
            usr = eval(serviceStr+'Service').getUser(DATA.profileUser)
            if usr is not None:
                DATA.userServices.append(serviceStr)
                getattr(DATA,serviceStr.lower()).authenticationStatus = ""
            else:
                getattr(DATA,serviceStr.lower()).authenticationStatus = "Unauthorised"
        
        DATA.statuses = StatusService.getUserStatuses(DATA.profileUser)
        #
        if hasattr(DATA,'user'):
            #facebook
            DATA.FBFriends = FacebookService.isFriends(DATA.user,DATA.profileUser)
            
            #Buzz
            DATA.BuzzFollowing = BuzzService.isFollowing(DATA.user,DATA.profileUser)
            DATA.BuzzFollowed = BuzzService.isFollowed(DATA.user,DATA.profileUser)
            
            #Twitter
            DATA.TwitterRelationship = TwitterService.getRelationship(DATA.user, DATA.profileUser)
            
        #
        if not DATA.userServices:
            DATA.profileUser.userServicesString = "Not connected to any of the services"
        else:
            DATA.profileUser.userServicesString = "Connected to " + ",".join(DATA.userServices)
        DATA.profileUser.statusCount = StatusService.getUserStatusCount(DATA.profileUser)
        
        path = os.path.join(os.path.dirname(__file__), 'html/profilePage.html')
        self.response.out.write(render(path, {'DATA':DATA}))

    def renderSearchPage(self):
        class temp:
            pass
        
        DATA = temp()
        DATA.user = UserService.getCurrentUser(self)
        
        DATA.allUsers = GrafiteUser.all().fetch(300)
        DATA.allUsers = map(lambda x: UserProfilePage._getProfileDetails(x), DATA.allUsers)
        
        path = os.path.join(os.path.dirname(__file__), 'html/users.html')
        self.response.out.write(render(path, {'DATA':DATA}))
        
    @staticmethod
    def _getProfileDetails(x):
        return {"nickname":x.Nickname,"url":x.profileUrl,"dp":x.displayPicture}