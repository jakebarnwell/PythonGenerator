import cgi
import re

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import os
import logging
from time import time
from datetime import datetime,timedelta
from google.appengine.api import memcache, users
from google.appengine.ext.webapp.template import render

from UserService import UserService, time_format
from UserService import GrafiteUser
from UserService import time_format
from django.utils import simplejson as json
from FacebookService import FacebookService
from BuzzService import BuzzService
from TwitterService import TwitterService

class GrafiteUserUnregistered(db.Model):
    nickname = db.StringProperty()
    password = db.StringProperty()
    dateJoined = db.DateTimeProperty()
    emailId = db.StringProperty()
    
    dateLastAccessed = db.DateTimeProperty(auto_now_add=True)
    accessToken = db.StringProperty()
    verifyToken = db.StringProperty()
        
    @staticmethod
    def new():
        import uuid
        at = str(uuid.uuid4())
        usr = GrafiteUserUnregistered()
        usr.accessToken = at
        usr.dateJoined = usr.dateLastAccessed = datetime.now()
        usr.settings = "{}"
        usr.put()
        return at

    @staticmethod
    def clean():
        del1 = timedelta(minutes=11)
        res = GrafiteUserUnregistered.all().filter("dateJoined <= ",datetime.now() - del1)
        res = res.fetch(res.count())
        db.delete(res)

    @staticmethod
    def getByAccessToken(at):
        res = GrafiteUserUnregistered.all().filter("accessToken = ",at)
        if res.count():
            return res.fetch(1)[0]
        return None

    def setNickname(self,nick):
        if len(nick) < 6:
            return {"result":"error","message":"Username should be atleast 6 characters"}
        res = GrafiteUserUnregistered.all().filter("nickname =",nick)
        if res.count():
            return {"result":"error","message":"Username already exists"}
        res = GrafiteUser.all().filter("nickname =",nick)
        if res.count():
            return {"result":"error","message":"Username already exists"}

        self.nickname = nick
        self.put()
        return {"result":"success"}

    def setPassword(self,pwd):
        if pwd == "":
            return {"result":"error","message":"blank password!"}
        self.password = pwd
        self.put()
        return {"result":"success"}

    def setEmail(self,email):
        res = GrafiteUserUnregistered.all().filter("emailId =",email)
        if res.count():
            return {"result":"error","message":"Email already Registered!"}
        res = GrafiteUser.all().filter("nickname =",nick)
        if res.count():
            return {"result":"error","message":"Email already Registered!"}

        self.emailId = email
        self.put()
        return {"result":"success"}
    

class RegisterService(webapp.RequestHandler):
    def get(self):
        at = GrafiteUserUnregistered.new()
        self.response.headers.add_header('Set-Cookie', UserService.makeCookieString(
        (datetime.now() + timedelta(minutes=10)).strftime(time_format),{"at":at}))
        self.response.out.write("")
        res = GrafiteUserUnregistered.all().filter("dateJoined <=", datetime.now() - timedelta(minutes=10))
        arr = res.fetch(res.count())
        db.delete(arr)

    def post(self):
        accessToken = None
        for k,v in self.request.cookies.iteritems():
            if k=="at":
                accessToken = v
        if accessToken is None:
            self.response.out.write(json.dumps({"result":"error","message":"Invalid User!"}))
            return
        
        usr = GrafiteUserUnregistered.getByAccessToken(accessToken)
        if usr is None:
            self.response.out.write(json.dumps({"result":"error","message":"Invalid User!"}))
            return
        
        self.response.out.write(json.dumps(getattr(self,"post_" + self.request.get("type"))(usr)))
    
    def post_setNickname(self,usr):
        nickname = self.request.get("nickname")
        if nickname in (None,""):
            return {"result":"error","message":"Nickname not specified!"}

        return usr.setNickname(nickname)
        
    def post_setPassword(self,usr):
        pwd = self.request.get("password")
        if pwd in (None,""):
            return {"result":"error","message":"Password not specified!"}
        return usr.setPassword(pwd)

    def post_sendVerificationCode(self,usr):
        import uuid
        
        emailId = self.request.get("email")
        if emailId in (None,""):
            return {"result":"error","message":"Email ID not specified!"}
        usr.verifyToken = str(uuid.uuid4())
        usr.emailId = emailId
        usr.put()
        
        from EmailService import sendMail
        sendMail(emailId, "Confirmation Mail", "Add GrafiteBot(grafiteapp@appspot.com) to your GTalk chat list. Ping GrafiteBot with the following:\nverify %s"%usr.verifyToken)
        return {"result":"success"}
        
    def post_pinged(self,usr):
        res = GrafiteUser.all().filter("emailId =",usr.emailId)
        if res.count()!=1:
            return {"result":"error","message":"EmailId not found!"}
        
        user = res.fetch(1)[0]
        res1,at, expire = GrafiteUser.login(user.key().name(), user.password, "Web-browser")
        if res1!="success":
            return {"result":"error","message":"Unable to login"}

        self.response.headers.add_header('Set-Cookie',UserService.makeCookieString(
            expire.strftime(time_format),{"access_token":at}))
                
        return {"result":"success","value":res.count()==1}