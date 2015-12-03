import datetime
import ctool
import os
import logging
#from myerr import PermissionDeniedError, NotLoggedInError, NotRegisteredError
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError
from google.appengine.runtime import DeadlineExceededError


def template_values():
    now = datetime.datetime.now()
    retval = {
            'title': 'Klarnaban',
            'slogan':'v0.01 - simple-simon',
            'base_url':'http://klarnaban.flafreeit.com',
            'client_name':'KLARNABAN',
            'phone_number':'123-123-1233',
            'tollfree_number':'123-123-1233',
            'fax_number':'123-123-1233',
            'address':'',
            'email_address':'richard@flafreeit.com',
            'home':'http://www.flfreeit.com',
            
            '':'',
            'copyright':'Florida Freelance IT LLC',
            'copyright_url':'http://www.flafreeit.com',
            'noreply_email':'noreply@flafreeit.com',
            'admin_email':'richard@flafreeit.com',

            'description':'klarna kanban scrumban scrum',
            'keywords':'klarna kanban scrumban scrum',
            
            'month':now.strftime("%a"),
            'day':now.strftime("%d"),
            'copyright_years':'2010',
            'now':datetime.datetime.now().strftime("%A %d. %B %Y at %I:%M %p"),
            'logout':users.create_logout_url("/"),
            'login':users.create_login_url("/"),
            'user':users.get_current_user(),
            
            'robot':'index, nofollow, noarchive',
            'googlebot':'noarchive',
            'author':'RB',
            }
    return retval
    
def is_root(user):
    return user.email() == 'richard@flafreeit.com' 


#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write(ctool.render('home','config.html'))


def main():
    application = webapp.WSGIApplication([('/c/', MainHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
