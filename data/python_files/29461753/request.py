import os
import time
import urlparse
import Cookie
import email.utils

from exceptions import *
from autodict import autodict

pwt_version = 'pwt/0.3'

class Request:
    def __init__(self, app, env):
        self.env = env
        self.data = autodict()
        self.root = app._root
        self.indexes = app._indexes
        self.location = None
        self.types = app._types
        self.method = env['REQUEST_METHOD'].upper()
        self.headers = {
            'Server': pwt_version,
            'Content-Type': 'text/html',
            'Date': time.ctime(),
        }
        self.request_uri = urlparse.urlsplit(env['REQUEST_URI'])
        self.status = 200
        if app._prefix:
            self.prefix = app._prefix
        else:
            self.prefix = env.get('SCRIPT_NAME', '')
        prefixlen = len(self.prefix)
        if 0 == prefixlen or not self.request_uri.path.startswith(self.prefix):
            prefixlen = 0
        elif self.prefix[-1] == '/':
            prefixlen -= 1
        self.uri = self.request_uri.path[prefixlen:]
        self._args = None
        self._body = ''
        self._cookies_out = { }

    def static_file(self, path):
        try:
            st = os.stat(path)
        except OSError:
            raise notfound()
        if_modified_since = email.utils.parsedate(self.env.get('HTTP_IF_MODIFIED_SINCE', ''))
        if None != if_modified_since and time.mktime(if_modified_since) >= st.st_mtime:
            raise notmodified()
        self.headers['Content-Length'] = str(st.st_size)
        self.headers['Last-Modified'] = time.ctime(st.st_mtime)
        try:
            e = path.split('/')[-1].split('.')[-1]
            self.headers['Content-Type'] = self.types[e]
        except:
            pass
        return open(path)

    def static_dir(self, path):
        for fn in self.indexes:
            fullpath = '/'.join([path, fn])
            if os.path.isfile(fullpath):
                return self.static_file(fullpath)
        # Generate directory listing?
        raise forbidden

    def static_uri(self, uri):
        path = ''.join([self.root, uri])
        try:
            if os.path.isfile(path):
                return self.static_file(path)
            elif os.path.isdir(path):
                return self.static_dir(path)
            raise notfound
        except IOError:
            raise forbidden

    def add_args(self, args):
        for key, value in args.items():
            if 0 == len(value):
                self._args[key] = ''
            elif 1 == len(value):
                self._args[key] = value[0]
            else:
                self._args[key] = value

    def args(self):
        if None != self._args:
            return self._args

        self._args = autodict()
        self.add_args(urlparse.parse_qs(self.request_uri.query, True))
        content_type = self.env.get('CONTENT_TYPE', '')
        if 'POST' == self.method and content_type in \
                ['application/x-www-form-urlencoded', 'multipart/form-data']:
            try:
                size = int(self.env.get('CONTENT_LENGTH', '0'))
            except ValueError:
                size = 0
            data = self.env['wsgi.input'].read(size)
            self.add_args(urlparse.parse_qs(data, True))

        return self._args

    def _parse_cookies(self):
        if None != self._cookies_in:
            return

        self._cookies_in = autodict()
        try:
            cookies = Cookie.SimpleCookie(self.env.get('HTTP_COOKIE', ''))
            for key, value in cookies.iteritems():
                self._cookies_in[key] = value.value
        except Cookie.CookieError:
            pass

    def get_cookie(self, name):
        self._parse_cookies()
        return self._cookies_in[name]

    def set_cookie(self, name, value, **kwargs):
        cookie = Cookie.SimpleCookie()
        morsel = Cookie.Morsel()
        morsel.set(name, *cookie.value_encode(value))
        for key, value in kwargs.iteritems():
            if 'max_age' == key: key = 'max-age'
            morsel[key] = value
        self._cookies_out[name] = morsel
        return morsel

