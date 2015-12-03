import re
import sys
import traceback
import types

from exceptions import *
from request import Request
import defaults
import hooks


class Application:
    class Location:
        def __init__(self, loc, handler):
            self._location = loc
            self._regex = re.compile(loc)
            self._handler = handler
            self._instance = handler()

    def __init__(self, locations, **kwargs):
        self._locations = []
        for t in locations:
            self._locations.append(Application.Location(*t))
        self._root = kwargs.get('root', defaults.root)
        self._prefix = kwargs.get('prefix', '')
        self._indexes = kwargs.get('indexes', defaults.indexes)
        self._types = {}
        for k, v in defaults.types.items():
            for ext in v:
                self._types[ext] = k
        self._setup_hooks = []
        self._cleanup_hooks = []

    def _handle_exception(self, req, e):
        if isinstance(e, HTTPRedirection):
            req.status = e._status
            req.headers.pop('Content-Length', None)
            req.headers.pop('Content-Type', None)
            req._body = ''
            if None != e._location:
                if 'http:' == e._location[0:5].lower() or 'https:' == e._location[0:6].lower():
                    req.headers['Location'] = e._location
                else:
                    host = req.env.get('HTTP_HOST',
                        req.env.get('HTTP_X_FORWARDED_HOST',
                        req.env.get('SERVER_NAME', 'localhost')))
                    if '/' == e._location[0]:
                        req.headers['Location'] = ''.join(['http://', host, req.prefix, e._location])
                    else:
                        uri = req.uri
                        if '/' != uri[-1]:
                            uri = '/'.join(uri.split('/')[:-1])
                        req.headers['Location'] = ''.join(['http://', host, req.prefix, uri, '/', e._location])

        elif isinstance(e, HTTPStatus):
            req.status = e._status

        else:
            traceback.print_exc(file=sys.stderr)
            req.status = internalerror()._status
            req.headers.pop('Content-Length', None)
            req.headers.pop('Content-Type', None)
            req._body = ''

    def hook_setup(self, hook):
        self._setup_hooks.append(hook)

    def hook_cleanup(self, hook):
        self._cleanup_hooks.append(hook)

    def app(self, env, *args):
        start_response = args[0]
        req = Request(self, env)

        try:
            for hook in hooks._global_class_hooks:
                handler = getattr(hook, "setup", None)
                if None != handler:
                    handler(req)

            for hook in hooks._global_setup_hooks:
                hook(req)

            for hook in self._setup_hooks:
                hook(req)

            for loc in self._locations:
                matches = loc._regex.match(req.uri)
                if None != matches:
                    handler = getattr(loc._instance, req.method, None)
                    if None == handler and 'HEAD' == req.method:
                        handler = getattr(loc._instance, 'GET', None)
                    if None == handler:
                        raise badmethod

                    req.location = loc
                    req._body = handler(req, *list(matches.groups()))
                    break

        except Exception as e:
            self._handle_exception(req, e)

        # Should all hooks always be called?
        try:
            for hook in self._cleanup_hooks:
                hook(req)

            for hook in hooks._global_cleanup_hooks:
                hook(req)

            for hook in hooks._global_class_hooks:
                handler = getattr(hook, "cleanup", None)
                if None != handler:
                    handler(req)

        except Exception as e:
            self._handle_exception(req, e)

        status_line = "%d %s" % (req.status, getattr(req, 'status_text',
            defaults.status_text.get(req.status, 'Unknown')))

        if 'HEAD' == req.method:
            req.headers['Content-Length'] = 0
            req._body = ''
        elif req.status >= 400 and len(req._body) == 0:
            req._body = '<html><head><title>%s</title></head><body><center><h1>%s</h1></center></body></html>' % \
                (status_line, status_line)

        headers_out = req.headers.items()
        headers_out.extend([ \
                tuple([ h.strip() for h in c.output().split(':', 1) ]) \
                for c in req._cookies_out.values() ])

        start_response(status_line, headers_out)

        return req._body

