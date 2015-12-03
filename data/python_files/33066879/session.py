import uuid
import logging
from functools import partial
from tornado.web import RequestHandler, asynchronous, HTTPError
from tornado.ioloop import IOLoop
import models as m
from messagetypes import KrumSocketHandler
from krum.utilities import is_json, to_json, from_json, extract_attrs, update_attributes

logger = logging.getLogger(__name__)

KRUM_PLAYER_API_VERSION = 1

class CannotAddPlayerError(Exception):
    pass

class PlayerInUseError(Exception):
    def __init__(self, player_url, other_session):
        self.player_url = player_url
        self.other_session = other_session
        self.message = 'The player "{}" is being used by "{}"'.format(player_url, other_session)

class NoSuchPlayerError(Exception):
    pass

class SessionProxy(object):
    '''This takes a session and maps the requests through to the current remote player.
    When a change of remote player is requested, it will tell the old one to clear and
    give the new one the full set of state, allowing a seemless transition.
    '''
    DEFAULTS = {
        'playlist': [],
        'paused': False,
        'position': 0,
        'volume': 1.0,
    }
    def __init__(self, player_set, data={}, gen_url=None, callback=None):
        '''This guy maintains the state of a Playback session. Interleaving both
        the requests from clients via process_request and events that come back
        from the Remote Player itself via process_event.

        On return, the session is persisted to SQL.
        The callback is called once the remote players state is up-to-date. It will
        always be called after this method has returned.'''

        super(SessionProxy, self).__init__()

        # Precondition: There isn't an active session with this name
        # Note: There might be a saved session with this name

        # it must have a name
        name = data.get('name') or ''
        if name == '' or not isinstance(name, basestring):
            # TODO: This should be a Session Error or such, not HTTP specific
            raise HTTPError(400, 'Sessions must have a string name of at least 1 character')

        # check we can get the remote player
        if 'player_url' in data:
            player = player_set.acquire_player(name, data['player_url'])
        else:
            player = None

        # ensure the model exists, and update it's properties
        try:
            model = m.Session.objects.get(name=name)
        except m.Session.DoesNotExist:
            model = m.Session(name=name)

            # update it with the defaults
            update_attributes(model, SessionProxy.DEFAULTS, SessionProxy.DEFAULTS.viewkeys())

        # apply the changes in the payload
        update_attributes(model, data, SessionProxy.DEFAULTS.viewkeys())

        # save the boring stuff
        self.player_set = player_set
        self.url = gen_url and gen_url(model.id)
        self.name = name
        self.model = model
        self.player = None
        self.duration = None # will recieve in playback events

        # now apply our state, by setting player to None, we force a full aquire cycle of the new player
        self.apply_state_change({}, callback)

    @property
    def id(self):
        return self.model.id

    def clear_player(self):
        '''This will clear the playlist on the current player'''
        def on_clear(status, body):
            if not (200 <= status < 300):
                logger.error('Got non-2xx response from Remote Player: {}'.format(body))

        self.player.send_request('PATCH', '/playback', {'playlist':[]}, on_clear)

    def get_current_state(self):
        state = extract_attrs(self.model, SessionProxy.DEFAULTS.iterkeys())
        state['duration'] = self.duration

        return state

    def apply_state_change(self, data, callback=None):
        # TODO: This code is intertwined untestable rubbish. Need to pull out
        #   steps into seperate methods to allow testing...
        '''Will take the provided data and propegate out the necessary changes
        to the sessions Remote Player.

        On return, the remote player, if present, has been asked to sync up.
        The callback is called once the remote player has confirmed it is in sync.
        Callback is always called after this function has returned.'''

        logger.debug('Got state change request on session {}, new state {}'.format(self.id, data))

        # if we're changing player
        new_url = data.get('player_url')
        if isinstance(new_url, basestring) and (self.player == None or new_url != self.model.player_url):

            # aquire the new one, do first in case of failure
            if new_url == '':
                new_player = None
            else:
                new_player = self.player_set.acquire_player(self.name, new_url)

            # push out a request to clear the old one, retry apply with new player :)
            if self.player:
                self.clear_player()
                self.player_set.release_player(self.name, self.model.player_url)

            # save this stuff
            self.player = new_player
            self.model.player_url = new_url
            self.model.save()

            # it's a new player, we want to resend everything, not just a delta
            full_data = extract_attrs(self.model, SessionProxy.DEFAULTS.iterkeys())
            full_data.update(data)
            data = full_data

        if self.player is None:
            # persist changes
            update_attributes(self.model, data, SessionProxy.DEFAULTS.keys(), False)
            self.model.save()

            if callback is not None:
                # done this way to make sure the function is called after we've returned
                IOLoop.instance().add_callback(partial(callback, 204, None))
            return

        def player_callback(status, body):
            if 200 <= status < 300:
                # make sure to save the new state
                update_attributes(self.model, data, SessionProxy.DEFAULTS.keys(), False)
                self.model.save()
            else:
                logger.error('Non 2xx response, {}, from Remote Player: {}'.format(status, body))

            if callback:
                callback(status, body)

        # send of the request to the player
        self.player.send_request('PATCH', '/playback', data, callback=player_callback)

    def apply_state_event(self, data):
        '''Events come back from remote players to signal position progress and
        completion of a playlist item. This method incorporates those updates
        into the locally cached state.'''
        pass

    def player_removed(self):
        '''This is called if the player is removed forcibly from this session.'''
        self.player = None
        self.model.player_url = None
        self.model.save()
        self.duration = None    # we're not playing, we no longer know our duration

    @property
    def id(self):
        return self.model.id

    def to_json(self):
        data = {
            'url': self.url,
            'name': self.name,
            'duration': self.duration,
        }
        data.update(extract_attrs(self.model, ['id', 'player_url', 'playlist',
            'paused', 'position', 'volume']))
        return data

class PlayerState(object):
    def __init__(self):
        super(PlayerState, self).__init__()

        # we come from nothing
        self.players_by_url = {}
        self.sessions_by_id = {}
        self.owners_by_player_url = {}    # to track who owns what

        # clear the status of the players
        m.RegisteredPlayer.objects.all().update(active=False)

    def add_player(self, meta, player_socket, url_builder):
        '''
        Persists the player names/guid, adds it to state set.

        Returns: the Krum URL for the newly registered player.
        '''
        try:
            guid = meta['guid']
        except KeyError as e:
            raise CannotAddPlayerError('player metadata missing guid'.format(e.message))

        # normalise the guid
        guid = uuid.UUID(guid).hex
        isvisible = meta.get('isvisible', False) != False

        # get the model
        try:
            player_model = m.RegisteredPlayer.objects.get(guid=guid)
        except m.RegisteredPlayer.DoesNotExist:
            player_model = m.RegisteredPlayer(guid=guid)

        # make sure the name is unique, and save it
        player_model.name = self._gen_unique_name(player_model.name or meta.get('client_type'))
        player_model.active = True
        player_model.isvisible = isvisible
        player_model.save()

        url = url_builder(player_model.id)
        self.players_by_url[url] = (player_socket, meta, player_model)

        return (url, player_model.name)

    def player_closed(self, player_socket):
        for k, v in self.players_by_url.iteritems():
            if v[0] == player_socket:
                del self.players_by_url[k]
                try:
                    player_model = v[2]
                    player_model.active = False
                    player_model.save()
                except m.RegisteredPlayer.DoesNotExist:
                    pass
                return

        # TODO: Notify the session...

    def acquire_player(self, session_name, player_url):
        try:
            player = self.players_by_url[player_url]
        except KeyError:
            raise NoSuchPlayerError('Requested: {}, available: {}'.format(player_url, self.players_by_url.keys()))

        # make sure no other session has it already
        owner = self.owners_by_player_url.get(player_url)
        if owner is not None and owner != session_name:
            raise PlayerInUseError(player_url, self.owners_by_player_url[player_url])

        self.owners_by_player_url[player_url] = session_name

        return player[0]

    def release_player(self, session_name, player_url):
        try:
            sess = self.owners_by_player_url[player_url]
            if sess != session_name:
                raise ValueError("Cannot release player {}, {} does not own, {} does".format(player_url, session_name, sess))
            else:
                del self.owners_by_player_url[player_url]
        except:
            raise ValueError("Player {} is not currently acquired by anyone".format(player_url))

    def _gen_unique_name(self, name):
        used_names = set([x[2].name for x in self.players_by_url.viewvalues()])
        name = name or 'Unknown Player'
        new_name = name
        i = 1
        while new_name in used_names:
            new_name = '{}-{}'.format(name, i)
            i += 1

        return new_name

    def create_or_renew_session(self, session_data, gen_url, callback=None):
        '''On return the session is created/re-activated and the change
        persisted to the DB. This means you can "POST" sessions with the
        same multiple times, but the same URL will be returned for all of them.

        The callback is called once the remote player has been sync'd
        with the session state. Always after this function has returned.
        '''
        name = session_data['name']

        # try to find it first
        for id_, sess in self.sessions_by_id.iteritems():
            if sess.name == name:
                if callback is not None:
                    # done this way to make sure the function is called after we've returned
                    IOLoop.instance().add_callback(partial(callback, 204, None))

                return sess

        sess = SessionProxy(self, session_data, gen_url, callback=callback)
        logger.debug('Saving session with ID: {}'.format(sess.id))
        self.sessions_by_id[sess.id] = sess
        return sess

    def update_session(self, session_id, session_data, callback=None):
        sess = self.sessions_by_id[session_id]

        sess.apply_state_request(session_data, callback)

    @property
    def sessions(self):
        return self.sessions_by_id.viewvalues()

    def get_session(self, session_id):
        return self.sessions_by_id[int(session_id)]

class RemotePlayerSocket(KrumSocketHandler):
    def initialize(self, state):
        self.player_state = state
        self._meta_retries = 0

    def open(self):
        '''This kicks off the registration process.'''
        logger.info('Got remote player connection')

        self.send_request('GET', '/meta', callback=self._meta_response)

    def _meta_response(self, status, body):
        logger.info('Got /meta response, {} {}'.format(status, body))
        if status != 200:
            logger.error('Remote player failed /meta request, got {}, expected 200. Dropping connection. Response body: {}'.format(status, body))
            self.close()
            return

        # "create" the player
        url_builder = partial(self.application.reverse_url, 'player')

        # we're all good
        try:
            player_url, player_name = self.player_state.add_player(body, self, url_builder)
        except CannotAddPlayerError as e:
            logger.error('Cannot add player. Reason: "{}", dropping connection.'.format(e))
            self.close()

        # we send a patch with "registered" to to it we're ready
        patch_body = {
            'registered_url': player_url,
            'registered_name': player_name
        }

        # check it's version
        version = body.get('version')
        if version != KRUM_PLAYER_API_VERSION:
            logger.info('Got remote player with API version, got {}, need {}'.format(version, KRUM_PLAYER_API_VERSION))

            # it doesn't support our version
            if KRUM_PLAYER_API_VERSION not in body.get('supported_versions', []):
                logger.info('Remote player doesn\'t support API version {}, only {}, dropping connection'.format(KRUM_PLAYER_API_VERSION, body.get('supported_versions', [])))
                self.close()
                return
            elif self._meta_retries > 0:
                logger.warn('Ran out of retried for version change request, dropping connection')
                self.close()
                return
            self._meta_retries += 1

            # tell it to switch to our version
            patch_body['version'] = KRUM_PLAYER_API_VERSION

        # once we're done
        def patch_callback(status, new_body):
            if status != 204:
                logger.error('Remote player, non-204 code, PATCH request to change API version, reason "{}". Dropping connection.'.format(body))
                self.close()

        self.send_request('PATCH', '/meta', patch_body, patch_callback)

    def on_request(self, request):
        pass

    def on_event(self, event):
        pass
        # pause
        # position updates
        # playlist changes

    def on_close(self):
        logger.info('Remote player close')
        self.player_state.player_closed(self)

def player_view(application, player):
    gen_url = partial(application.reverse_url, 'player')
    return {
        'id': player['id'],
        'url': gen_url(player['id']),
        'name': player['name']
    }

class RemotePlayerListHandler(RequestHandler):
    '''
    This handler provides a way to enumerate the registered Remote Players.
    '''
    def initialize(self, state):
        self.player_state = state

    def get(self):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')

        players = m.RegisteredPlayer.objects.filter(active=True,isvisible=True).order_by('name').values('id','name')
        players = [player_view(self.application, x) for x in players]
        self.write(to_json(players))

class RemotePlayerHandler(RequestHandler):
    def initialize(self, state):
        self.player_state = state

    def get(self):
        self.write({})

class SessionListHandler(RequestHandler):
    '''
    This handles requests for querying or creating/re-enstating sessions.
    '''
    def initialize(self, state):
        self.player_state = state

    def get(self):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(to_json([x.to_json() for x in self.player_state.sessions]))

    @asynchronous
    def post(self):
        '''This method is just for creating new sessions. Trying to create a new
        with the same name as one that already exists is an error.'''

        if not is_json(self.request.headers.get('Content-Type', '')):
            raise HTTPError(400, 'Client submitted non-json Content-Type')

        data = from_json(self.request.body)

        def on_complete(status, message):
            self.set_status(201)
            self.set_header('Location', self.application.reverse_url('session', sess.id))
            self.finish()

        try:
            gen_url = partial(self.application.reverse_url, 'session')
            sess = self.player_state.create_or_renew_session(data, gen_url, on_complete)
        except PlayerInUseError as e:
            self.set_status(409)
            self.write({'message': e.message})
            self.finish()
            return

class SessionHandler(RequestHandler):
    '''
    This handles querying an manipulating an individual player session.
    '''
    def initialize(self, state):
        self.player_state = state

    def get(self, id_):
        sess = self.player_state.get_session(id_)

        self.write(sess.to_json())

    @asynchronous
    def patch(self, id_):
        def on_complete(status, message):
            self.set_status(status)

            self.finish()

        if not is_json(self.request.headers.get('Content-Type', '')):
            raise HTTPError(400, 'Client submitted non-json Content-Type')

        data = from_json(self.request.body)

        sess = self.player_state.get_session(id_)
        sess.apply_state_change(data, on_complete)

class HistoryHandler(RequestHandler):
    '''
    This handler provides access to the play history of sessions.
    '''
    pass
