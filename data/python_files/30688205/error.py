import cgi

from pylons import request, response, session, tmpl_context as c

from paste.urlparser import PkgResourcesParser
from pylons import request
from pylons.controllers.util import forward
from pylons.middleware import error_document_template
from webhelpers.html.builder import literal

from guidem.lib.base import BaseController, render
from guidem.lib import helpers as h
import guidem.model as model

class ErrorController(BaseController):

    """Generates error documents as and when they are required.

    The ErrorDocuments middleware forwards to ErrorController when error
    related status codes are returned from the application.

    This behaviour can be altered by changing the parameters to the
    ErrorDocuments middleware in your config/middleware.py file.

    """
    
    def __before__(self):
        request.environ['_auth'] = request.environ['_auth']
            
    def document(self):
        """Render the error document"""
        resp = request.environ.get('pylons.original_response')
        c.code = cgi.escape(request.GET.get('code', ''))
        c.content = cgi.escape(request.GET.get('message', ''))
        if resp:
            c.code = c.code or cgi.escape(str(resp.status_int))
            c.content = literal(resp.status)
        if not c.code:
            raise Exception('No status code found')
        return render('/error.htm')

    def img(self, id):
        """Serve Pylons' stock images"""
        return self._serve_file('/'.join(['media/img', id]))

    def style(self, id):
        """Serve Pylons' stock stylesheets"""
        return self._serve_file('/'.join(['media/style', id]))

    def _serve_file(self, path):
        """Call Paste's FileApp (a WSGI application) to serve the file
        at the specified path
        """
        request.environ['PATH_INFO'] = '/%s' % path
        return forward(PkgResourcesParser('pylons', 'pylons'))
