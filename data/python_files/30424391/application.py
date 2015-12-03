import os, sys
from errors import DataUnavailable
from helpers import process_coffeescript
cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.append(cwd)

import web
from helpers import render_jinja
from pypi import Pypi
import pypirss
import json





template_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')

render = render_jinja(
    template_dir,   # Set template directory.
    encoding = 'utf-8',                         # Encoding.
    file_ext = ['xml', 'html']
)

urls = (
  '/', 'index',
  '/about', 'about',
  '/package/([a-zA-Z0-9-_\.]+).rss', 'make_rss',
  '/search/([a-zA-Z0-9-_\.]+)', 'search',
)


class index(object):
    def GET(self):
        web.header('Content-Type', 'text/html')
        return render.index(version=pypirss.__version__)

class about(object):
    def GET(self):
        web.header('Content-Type', 'text/html')
        return render.about(version=pypirss.__version__)


class search(object):
    def POST(self, search_string):
        web.header('Content-Type', 'application/json')
        pypi = Pypi()
        try:
            res = [el for el in pypi.get_package_list() if search_string in el]
        except DataUnavailable:
            raise web.HTTPError("504 Gateway Time-out", 
                                headers={"Content-Type": "text/plain"}, 
                                data="Error 504: Gateway Time-out")
        else:
            return json.dumps(res)


class make_rss(object):
    def GET(self, package_name):
        pypi = Pypi()
        try:
            package = pypi.get_package(package_name)
        except DataUnavailable:
            raise web.HTTPError("504 Gateway Time-out", 
                                headers={"Content-Type": "text/plain"}, 
                                data="Error 504: Gateway Time-out")
        if package is None:
            raise web.notfound()
        web.header('Content-Type', 'application/rss+xml')
        return render.rss(package=package, ctx=web.ctx, 
                          version=pypirss.__version__)

app = web.application(urls, globals())


if __name__ == '__main__':
    web.config.debug = True
    app.add_processor(process_coffeescript)
    #app = web.application(urls, globals())
    app.internalerror = web.debugerror
    app.run()
        
        