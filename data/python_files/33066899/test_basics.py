import uuid
from tests.test_helper import KrumTestCase, data_file_path, dicteq, alldictseq
from tests.functional.api.version_1 import create_version_url
from nose.tools import eq_, raises
from nose.plugins.attrib import attr
import krum.playback.session as kps
import krum.playback.messagetypes as kpm
import krum.utilities as u

class TestMessageTypes(KrumTestCase):

    def _setUp(self):
        pass

    def test_create_request(self):
        kwargs = {
            'method': 'POST',
            'id': 42,
            'path': '/dood',
            'body': {1: 2}
        }
        msg = kpm.Request(**kwargs)
        dicteq(kwargs, u.extract_attrs(msg, kwargs.keys()))
        kwargs['type'] = 'REQUEST'
        dicteq(kwargs, msg.to_json_dict())

        msg2 = kpm.Request.from_json_dict(kwargs)
        dicteq(msg2.to_json_dict(), kwargs)

    def test_create_response(self):
        kwargs = {
            'status': 200,
            'id': 42,
            'body': {1: 2}
        }
        msg = kpm.Response(**kwargs)
        dicteq(kwargs, u.extract_attrs(msg, kwargs.keys()))
        kwargs['type'] = 'RESPONSE'
        dicteq(kwargs, msg.to_json_dict())

        msg2 = kpm.Response.from_json_dict(kwargs)
        dicteq(msg2.to_json_dict(), kwargs)

    def test_create_event(self):
        kwargs = {
            'name': 'A momentous eventous!',
            'path': '/dood',
            'body': {1: 2}
        }
        msg = kpm.Event(**kwargs)
        dicteq(kwargs, u.extract_attrs(msg, kwargs.keys()))
        kwargs['type'] = 'EVENT'
        dicteq(kwargs, msg.to_json_dict())

        msg2 = kpm.Event.from_json_dict(kwargs)
        dicteq(msg2.to_json_dict(), kwargs)

class DummyPlayer(object):
    def __init__(self):
        super(DummyPlayer, self).__init__()

        self.guid = uuid.uuid4().hex

    def get_meta(self):
        return {
            'guid': self.guid,
            'supported_versions': [1],
            'version': 1,
            'client_type': 'Dummy'
        }

    def gen_url(self, id):
        return 'fakeurl/{}'.format(id)

class TestPlayerState(KrumTestCase):
    def _setUp(self):
        self.state = kps.PlayerState()

    def test_add_player(self):
        p = DummyPlayer()

        self.state.add_player(p.get_meta(), p, p.gen_url)

        # make sure it's in the list
        p1 = None
        for id, (player, meta, _) in self.state.players_by_url.iteritems():
            if player == p:
                p1 = player

        eq_(p, p1)

    @raises(kps.PlayerInUseError)
    def test_aquire_player(self):
        p = DummyPlayer()

        self.state.add_player(p.get_meta(), p, p.gen_url)

        # construct the URL
        player_url = p.gen_url(1)

        # acquire it
        player = self.state.acquire_player('Sandy', player_url)
        # re-aquire with same name, should succeed
        eq_(player, self.state.acquire_player('Sandy', player_url))

        # aqcuire with different name, should fail
        self.state.acquire_player('Biily', player_url)
