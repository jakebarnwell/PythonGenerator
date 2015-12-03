import logging
import tornado.web
import tornado.wsgi
import tornado.ioloop
import tornado.options
from tornado.httpserver import HTTPServer
from tornado.web import FallbackHandler, url
import django.core.handlers.wsgi
from pkg_resources import resource_filename
from krum.content.streamer import StreamingContentHandler
# TODO: move all handlers to krum.playback for cleanliness
import krum.playback.session as ps

def runserver(args):
    # set up logging to std out as default
    logging.getLogger().setLevel(logging.DEBUG)
    tornado.options.enable_pretty_logging()

    # set up the Django app, TODO: move to webui module
    wsgi_app = tornado.wsgi.WSGIContainer(django.core.handlers.wsgi.WSGIHandler())

    # this guy tracks all the Remote Players
    player_state = dict(state=ps.PlayerState())

    application = tornado.web.Application([
        (r'/api/1/content/(\d+)/data',          StreamingContentHandler),
        (r'/api/1/playback/players',            ps.RemotePlayerListHandler , player_state),
        url(r'/api/1/playback/players/(\d+)',   ps.RemotePlayerHandler, player_state, 'player'),
        (r'/api/1/playback/players/register',   ps.RemotePlayerSocket, player_state),
        (r'/api/1/playback/sessions',           ps.SessionListHandler, player_state),
        url(r'/api/1/playback/sessions/(\d+)',  ps.SessionHandler, player_state, 'session'),
        (r'.*', FallbackHandler, dict(fallback=wsgi_app))
        ], static_path=resource_filename('krum.webui', 'static'), # TODO: move to webui module
        debug=True
    )
    server = HTTPServer(application)
    server.bind(args.port)
    server.start(1)
    tornado.ioloop.IOLoop.instance().start()

