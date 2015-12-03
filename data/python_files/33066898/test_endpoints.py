import uuid
from functools import partial
from tests.test_helper import data_file_path, dicteq, alldictseq
from nose.tools import eq_, raises
from tornado.testing import AsyncHTTPTestCase
from tornado.web import url, Application
from tornado.httpclient import HTTPRequest
from tornado.ioloop import IOLoop
from krum.websocket import WebSocket
import krum.playback.session as ps
import krum.playback.messagetypes as pm
import krum.utilities as u

class DummyRemotePlayer(pm.KrumSocketClient):
    def __init__(self, *args, **kwargs):
        super(DummyRemotePlayer, self).__init__(*args, **kwargs)

        self.guid = uuid.uuid4().hex
        self.meta = {
                'version': 1,
                'supported_versions': [1],
                'guid': self.guid,
                'client_type': 'DummyRemotePlayer',
                'registered_url': None,
                'registered_name': None
            }
        self.playback = {
            'playlist': [],
            'position': 0.0,
            'volume': 1.0,
            'paused': False
        }

        # callback defaults
        self.on_close_callback = None

    @property
    def registered(self):
        return self.meta['registered_url'] is not None

    @property
    def player_url(self):
        return self.meta.get('registered_url')

    def close_with_callback(self, callback):
        self.on_close_callback = callback
        self.close()

    def on_close(self):
        print('On close triggered!!!')
        self.meta['registered_url'] = None
        self.meta['registered_name'] = None

        if callable(self.on_close_callback):
            self.on_close_callback()

    def on_event(self, event):
        pass

    def on_request(self, request):
        if request.method not in ('GET', 'PATCH'):
            self.send_response(405, request.id, {'message': 'Only GET and PATCH supported'})
            return

        # cruddy path checking
        if request.path == '/meta':
            if request.method == 'GET':
                self.send_response(200, request.id, self.meta)
            elif request.method == 'PATCH':
                self.meta.update(request.body)
                self.send_response(204, request.id)

                if self.meta['registered_url'] is not None:
                    self.on_registered()
            else:
                raise Exception('WTF?')

        elif request.path == '/playback':
            if request.method == 'GET':
                self.send_response(200, request.id, self.meta)
            elif request.method == 'PATCH':
                self.playback.update(request.body)
                self.send_response(204, request.id)
            else:
                raise Exception('WTF2?')

        else:
            self.send_response(
                404,
                request.id,
                {'message': 'Path "{}" not found.'.format(request.path)}
            )

    def on_registered(self):
        print('Class on register called')

class TestRegister(AsyncHTTPTestCase):
    def get_app(self):
        args = {'state': ps.PlayerState()}

        return Application([
            (r'/api/1/playback/players',            ps.RemotePlayerListHandler , args),
            url(r'/api/1/playback/players/(\d+)',   ps.RemotePlayerHandler, args, 'player'),
            (r'/api/1/playback/players/register',   ps.RemotePlayerSocket, args),
            (r'/api/1/playback/sessions',           ps.SessionListHandler, args),
            url(r'/api/1/playback/sessions/(\d+)',  ps.SessionHandler, args, 'session'),
        ])

    def get_new_ioloop(self):
        return IOLoop.instance()

    def test_register_player(self):
        url = self.get_url('/api/1/playback/players/register').replace('http://','ws://')
        player = DummyRemotePlayer(url=url)

        def on_registered():
            self.stop()

        player.on_registered = on_registered # ugly but meh
        self.wait()

class TestSessions(AsyncHTTPTestCase):
    def get_app(self):
        args = {'state': ps.PlayerState()}

        return Application([
            (r'/api/1/playback/players',            ps.RemotePlayerListHandler , args),
            url(r'/api/1/playback/players/(\d+)',   ps.RemotePlayerHandler, args, 'player'),
            (r'/api/1/playback/players/register',   ps.RemotePlayerSocket, args),
            (r'/api/1/playback/sessions',           ps.SessionListHandler, args),
            url(r'/api/1/playback/sessions/(\d+)',  ps.SessionHandler, args, 'session'),
        ])

    def get_new_ioloop(self):
        return IOLoop.instance()

    def test_create_session(self):
        # Create a session to fiddle with
        # functions that execute further steps in the test are prefixed with do_

        def on_response(response):
            eq_(201, response.code)

            self.session_url = response.headers.get('Location')

            # This is what a newly created session should look like...
            expect = {
                'name': 'Andrew',
                'player_url': '',
                'playlist': [],
                'paused': False,
                'position': 0,
                'volume': 1.0
            }
            self.check_new_state(self.session_url, expect, self.create_session_that_already_exists)

        req = HTTPRequest(
            self.get_url('/api/1/playback/sessions'),
            'POST',
            {'Content-Type': 'application/json; charset=UTF-8'},
            '{"name": "Andrew"}'
        )
        self.http_client.fetch(req, on_response)

        self.wait()

    def create_session_that_already_exists(self):
        def on_response(response):
            eq_(201, response.code)

            self.session_url = response.headers.get('Location')

            # This is what a newly created session should look like...
            expect = {
                'name': 'Andrew',
                'player_url': '',
                'playlist': [],
                'paused': False,
                'position': 0,
                'volume': 1.0
            }
            self.check_new_state(self.session_url, expect, self.do_patch_session)

        req = HTTPRequest(
            self.get_url('/api/1/playback/sessions'),
            'POST',
            {'Content-Type': 'application/json; charset=UTF-8'},
            '{"name": "Andrew"}'
        )
        self.http_client.fetch(req, on_response)

    def do_patch_session(self):
        # Now that we have a session, adjust some things to make sure that's working.
        url = self.session_url
        assert(url is not None)

        def on_response(response):
            eq_(200, response.code)
            assert(u.is_json(response.headers.get('Content-Type')))

            sess = u.from_json(response.body)
            self.session_dict = sess

            patch = {
                'volume': 0.5,
                'playlist': ['http://bob.com/vid.mp4']
            }

            self.check_send_patch(url, patch, partial(self.do_register_player, url))

        self.http_client.fetch(self.get_url(url), on_response)

    def check_send_patch(self, url, patch, next_func):
        # Will send a PATCH request to url with a payload of to_json(patch)
        # Then calls check_new_state to verify that the patch data was actually
        # incorporated.
        if not callable(next_func):
            raise Exception('Was handed non-callable "next_func"')

        def on_response(response):
            eq_(204, response.code)

            self.check_new_state(url, patch, next_func)

        # send a patch off
        req = HTTPRequest(
            self.get_url(url),
            'PATCH',
            {'Content-Type': 'application/json; charset=UTF-8'},
            u.to_json(patch)
        )
        self.http_client.fetch(req, on_response)

    def check_new_state(self, url, expect, next_func):
        # checks the dict returned by GETting the url and makes sure all keys in expect
        # are present and the values match in the returned data. Calls next_func on success.
        if not callable(next_func):
            raise Exception('Was handed non-callable "next_func"')

        def on_response(response):
            eq_(200, response.code)
            assert(u.is_json(response.headers.get('Content-Type')))

            sess = u.from_json(response.body)
            self.session_dict = sess

            for k, v in expect.viewitems():
                assert k in sess, 'Session is missing attribute {}'.format(k)
                eq_(v, sess[k])

            next_func()

        self.http_client.fetch(self.get_url(url), on_response)

    def do_register_player(self, session_url):
        # register a player so we can request it in the session
        register_url = self.get_url('/api/1/playback/players/register').replace('http://','ws://')
        self.player = DummyRemotePlayer(url=register_url)

        def on_registered():
            self.do_request_player(session_url, self.player.player_url)

        self.player.on_registered = on_registered # ugly but meh

    def do_request_player(self, session_url, player_url):
        # request that the session grab the player we just registered
        patch = {
          'player_url': player_url
        }

        def patch_done():
            self.check_player_matches_session()
            self.do_player_update(session_url, player_url)

        self.check_send_patch(session_url, patch, patch_done)

    def check_player_matches_session(self):
        # make sure the session and the player agree on their state
        pl_dict = self.player.playback
        sess_dict = self.session_dict
        for k in ('volume', 'paused', 'playlist', 'position'):
            eq_(pl_dict[k], sess_dict[k])

    def do_player_update(self, session_url, player_url):
        patch = {
            'playlist': ['http://localhost:1212/dood1','http://localhost:1212/dood2']
        }

        def patch_done():
            self.do_disconnect_player(session_url, player_url)

        self.check_send_patch(session_url, patch, patch_done)

    def do_disconnect_player(self, session_url, player_url):
        print('+++++++ CLOSING PLAYER++++++++++++++')

        def patch_done():
            print('+++++++ Patch done++++++++++++++')
            self.stop()

        def on_close():
            print('+++++++ Got close++++++++++++++')
            patch = {
                'volume': 0.5
            }
            # now make another session PATCH and see it doesn't barf
            self.check_send_patch(session_url, patch, patch_done)

        # disconnect the player, the session should accept PATCH request but
        self.player.close_with_callback(on_close)

