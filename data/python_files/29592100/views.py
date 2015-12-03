'''
'''
import os, re
import mimetypes
from webob import Response
from webob.exc import HTTPFound
from zope.interface import providedBy
from repoze.bfg.interfaces import IRequest, IView
from repoze.bfg.exceptions import NotFound

from library.views import BaseView 
from restructured import publish_source

def directory_view(context, request):
    path_info = request.environ['PATH_INFO']
    if not path_info.endswith('/'):
        response = HTTPFound(location=path_info + '/')
        return response

    defaults = ('index.html', 'index.rst')
    for name in defaults:
        try:
            index = context[name]
        except KeyError:
            continue        
        file_view = request.registry.adapters.lookup((IRequest, providedBy(index)), IView, name='', default=None)
        return file_view(index, request)
    raise NotFound('No default view for %s' % os.path.basename(context.path))

reh1 = re.compile('^<h1>(?P<title>[-\w\s]+)</h1>', re.I)

def split_content(src):

    m = reh1.match(src)
    if m:
        title = m.groupdict()['title']
        content = reh1.sub('', src)
    else:
        title = ''
        content = src
    return title, content

# predicates
def ishtml(context, request):
    return context.ext == 'html'

def isrst(context, request):
    return context.ext == 'rst'

# file views 
def restructured_text_view(context, request):
    """ File system-based ReST view
    """
    content = publish_source(context.source.decode('UTF-8'))
    title, content = split_content(content)
    return BaseView(context, request)(title=title, content=content)



def html_view(context, request):
    """ Just return the source raw.
    """

    title, content = split_content(context.source.decode('UTF-8'))
    return BaseView(context, request)(title=title, content=content)

def raw_view(context, request):
    """ Just return the raw source.
    """
    response = Response(context.source)
    mimetype, encoding = mimetypes.guess_type(context.path)
    response.content_type = mimetype or 'text/plain'
    return response
