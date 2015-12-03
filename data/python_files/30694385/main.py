import logging, os
# Must set this env var before importing any part of Django
# 'project' is the name of the project created with django-admin.py
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()

# Google App Engine imports.
from google.appengine.ext.webapp import util


# Force Django to reload its settings.
from django.conf import settings
settings._target = None


import django.core.handlers.wsgi
import django.core.signals
import django.db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import blobstore_handlers

def log_exception(*args, **kwds):
    logging.exception('Exception in request:')
    
# Log errors.
django.core.signals.got_request_exception.connect(log_exception)

# Unregister the rollback event handler.
django.core.signals.got_request_exception.disconnect(django.db._rollback_on_exception)

logging.getLogger().setLevel(logging.DEBUG)
logging.debug('Spawning new handler...')

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        upload_files = self.get_uploads('file') or self.get_uploads('blob_key')  # 'file' is file upload field in the form
        blob_info = upload_files[0]
        url=self.request.uri.replace('/_uh_','',1)
        key=self.request.POST.get('pk','None')
        self.redirect(str('%s%s/%s/' % (url,key,blob_info.key())))
        
# Create a Django application for WSGI.
django_app = django.core.handlers.wsgi.WSGIHandler()
upload_handler = webapp.WSGIApplication([('/.*', UploadHandler),], debug=True)