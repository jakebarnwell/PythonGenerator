import datetime, logging
import wsgiref.handlers
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import mail

import alerts_global, models

class AlertTaskWorker(webapp.RequestHandler):
    def get(self): # should run at most 1/s
        """
        get the next task from the queue, retrieve the file from the CDRFile datastore, 
        then load the CDRs into the CDRRecord datastore
        """

        # load the task
        alert = models.Alert.get(db.Key(self.request.get('alert')))
        # load the subscribers
        subs = models.subscriberList(alert.primary_authority)
        # put the details in the mail-queue
        for sender in subs:
            logging.info("adding to mail-queue!!!!!!")
            t = taskqueue.Task(url='/tasks/email/', method='GET',params={'to':sender.email,'subject': alert.message})
            t.add('mail-queue')

class EmailTaskWorker(webapp.RequestHandler):
    def get(self): # should run at most 1/s
        """
        get the next task from the queue, retrieve the file from the CDRFile datastore, 
        then load the CDRs into the CDRRecord datastore
        """
        template_values = alerts_global.template_values()

        # load the task
        # load the subscribers
        # put the details in the mail-queue
        logging.info("received an email task to process.")
        mail.send_mail(template_values['noreply_email'], self.request.get('to'), self.request.get('subject'), "www.parkalerts.info")
        logging.info("sent an email alert.")
        

def main():
    wsgiref.handlers.CGIHandler().run(webapp.WSGIApplication([
        ('/tasks/alert/', AlertTaskWorker),
        ('/tasks/email/', EmailTaskWorker),
    ]))

if __name__ == '__main__':
    main()

# __END__
