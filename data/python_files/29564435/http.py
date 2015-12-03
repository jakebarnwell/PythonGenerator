import base64
import json
import logging
import os
import re
import uuid

from gevent.core import EVHTTP_REQ_GET as GET
from gevent.core import EVHTTP_REQ_POST as POST
from gevent.http import HTTPServer


logger = logging.getLogger(__name__)


# Seconds after a client is guaranteed to receive an answer. We
# simply assume that there are some evil proxy servers and browser
# configurations that timeout after 60 seconds so we make sure
# to return a few seconds earlier.
POLL_TIMEOUT = 55


# prepare static files
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')
consumer_js_filename = os.path.join(static_dir, 'consumer.js')
tunnel_html_filename = os.path.join(template_dir, 'tunnel.html')
debug_html_filename = os.path.join(template_dir, 'debug.html')


class HttpError(RuntimeError):
    status_code = 500
    status_name = 'Internal Server Error'
    extra_headers = {}
    def __init__(self, content=None):
        message = content or '%d - %s' % (self.status_code, self.status_name)
        super(HttpError, self).__init__(message)


class AuthorizationRequired(HttpError):
    status_code = 401
    status_name = 'Authorization Required'
    extra_headers = {
        'WWW-Authenticate': 'Basic realm="Publisher"',
    }


class BadRequest(HttpError):
    status_code = 400
    status_name = 'Bad Request'


class Forbidden(HttpError):
    status_code = 403
    status_name = 'Forbidden'


class MethodNotAllowed(HttpError):
    status_code = 405
    status_name = 'Method Not Allowed'


class NotFound(HttpError):
    status_code = 404
    status_name = 'Not Found'
def register_url(regex, protect=True):
    def wrapper(f):
        f.url_pattern = re.compile(regex)
        f.protect = protect
        return f
    return wrapper


class PullServer(HTTPServer):

    def __init__(self, listen, config, realm):
        super(PullServer, self).__init__(listen)
        logger.info('Listening on %s:%d' % (
            listen[0] or '0.0.0.0',
            listen[1]))
        self.config = config
        self.realm = realm
        # prepare list of all member functions with a url_pattern
        # attribute
        self.urls = [
            (f.url_pattern, f)
            for f in (
                getattr(self, name)
                for name in dir(self)
            )
            if hasattr(f, 'url_pattern')
        ]

    def handle(self, request):
        try:
            for url_pattern, method in self.urls:
                m = url_pattern.match(request.uri)
                if m:
                    break
            else:
                raise NotFound
            if method.protect:
                auth = request.find_input_header('authorization')
                if not auth:
                    raise AuthorizationRequired
                try:
                    auth = auth.split()[1]
                    username, password = base64.decodestring(auth).split(':', 2)
                except ValueError:
                    raise AuthorizationRequired
                if not self.realm.check_login(username, password):
                    raise AuthorizationRequired
            response = method(request, **m.groupdict())
            if response is None:
                content = 'OK'
                content_type = 'text/plain'
            else:
                content, content_type = response
            request.add_output_header('Access-Control-Allow-Origin', '*')
            request.add_output_header('Content-type', content_type)
            request.add_output_header('Content-length', str(len(content)))
            request.send_reply(200, 'OK', content)
        except HttpError, e:
            content = '%s\r\n' % e.message
            request.add_output_header('Access-Control-Allow-Origin', '*')
            request.add_output_header('Connection', 'close')
            request.add_output_header('Content-type', 'text/plain')
            request.add_output_header('Content-length', str(len(content)))
            for name, value in e.extra_headers.items():
                request.add_output_header(name, value)
            request.send_reply(e.status_code, e.status_name, content)

    @register_url('^/$', protect=False)
    def pull(self, request):
        sid = request.find_input_header('X-Session-Id')
        if (sid is None):
            raise BadRequest('X-Session-Id header missing in request')
        session = self.realm.get_session(sid)
        if session.active:
            raise BadRequest('multiple clients polling the same session')
        messages = [(topic and topic.id, message)
                for topic, message in session.pull(timeout=POLL_TIMEOUT)]
        response = json.dumps({ 'messages': messages })
        return (response, 'application/json')

    #
    # Consumer URLs
    #

    @register_url('^/consumer.js$', protect=False)
    def consumer_js(self, request):
        with file(consumer_js_filename) as fh:
            consumer_js = fh.read() % {
                'domain': self.config.cors_domain,
                'jquery_js': self.config.static_files['jquery_js'],
            }
        return (consumer_js, 'text/javascript')

    @register_url('^/tunnel/$', protect=False)
    def api(self, request):
        with file(tunnel_html_filename) as fh:
            tunnel_html = fh.read() % {
                'domain': self.config.cors_domain,
                'jquery_js': self.config.static_files['jquery_js'],
            }
        return (tunnel_html, 'text/html')

    #
    # URLs mainly useful for debugging
    #

    @register_url('^/debug/$')
    def debug(self, request):
        session_id = 'debug-%s' % uuid.uuid4().hex[:16]
        session = self.realm.get_session(session_id, create=True)
        session.debug = True
        session.subscribe(self.realm.debug_topic)
        with file(debug_html_filename) as fh:
            d = self.config.static_files.copy()
            d['session_id'] = session_id
            debug_html = fh.read() % d
        return (debug_html, 'text/html')

    @register_url('^/session/$')
    def session_list(self, request):
        return (json.dumps({
            'sessions': [
                session.get_overview_dict()
                for session in self.realm.sessions.itervalues()
            ]
        }), 'application/json')

    @register_url('^/session/(?P<sid>[^/]+)/$')
    def session_info(self, request, sid):
        session = self.realm.get_session(sid)
        return (json.dumps({
            'id': session.id,
            'subscriptions': [
                topic.id for topic in session.topics
            ],
            'active': session.active,
            'lastActivity': int(session.last_activity),
        }), 'application/json')

    @register_url('^/object/$')
    def object_list(self, request):
        return (json.dumps({
            'objects': [
                {
                    'id': topic.id,
                    'subscriberCount': len(topic.sessions),
                }
                for topic in self.realm.topics.itervalues()
            ]
        }), 'application/json')

    @register_url('^/object/(?P<oid>[^/]+)/$')
    def object_info(self, request, oid):
        topic = self.realm.get_topic(oid)
        return (json.dumps({
            'id': topic.id,
            'subscribers': [
                session.id for session in topic.sessions
            ],
        }), 'application/json')
