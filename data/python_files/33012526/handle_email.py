import cgi
import os
import logging
import datetime

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
import util_data

class ReceiveEmail(InboundMailHandler):
    def receive(self,message):
        logging.info("Received email from %s" % message.sender)
        plaintext = message.bodies(content_type='text/plain')
        for text in plaintext:
            txtmsg = ""
            txtmsg = text[1].decode()
            textmsg = txtmsg.split('\n')
# To verify the message, one can just check his Unique Account Number
            for line in textmsg:
                if "Bill Amount" in line:
                    amt = line.split('$')[1].strip()
#                    logging.info("vipin1 %s" % amt)
                if "Bill Date" in line:
                    bdate = line.split(':')[1].strip()
                    split_date = bdate.split('/')
                    month = split_date[0]
                    day = split_date[1]
                    year = split_date[2]
                    bdate = datetime.date(int(year),int(month),int(day))
#                    logging.info("vipin2 %s %s" % (bdate, bdate))
            util = util_data.util_data(email=str(txtmsg),amount=float(amt),billdate=bdate)
            util.recddate = datetime.datetime.now().date()
            util.put()

application = webapp.WSGIApplication([ReceiveEmail.mapping()], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
