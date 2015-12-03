import traceback
import json
from twisted.internet.defer import inlineCallbacks, returnValue
from djitch.utils.twist.events import TwistedEventRegistry
from twisted.internet import defer
import txamqp.spec
from uuid import uuid4
from django.conf import settings
from djitch.amqp import common, queues, exchanges
import logging
from djitch.utils.twist.logs import TwistedLoggingMixin


__author__ = 'gdoermann'

log = logging.getLogger(__name__)
SPEC = common.AMQP_SPEC


class MessageConsumer(TwistedLoggingMixin):
    """
    This is the base message consumer class.
    A message consumer will subscribe to amqp queues.  It knows how to
    set itself up (create connections to amqp, get channels, bind
    to queues, etc).

    Implementation will usually include overriding the process class.  The process class
    receives one argument, the message.  The default method simply acknowledges that it
     received the message to the amqp server.
    """
    VHOST = common.VHOST
    EXCHANGE = exchanges.BaseTemporaryExchange
    ROUTING_KEY = common.ROUTING_KEY # A single key OR a list of keys. A list will create multiple bindings.
    QUEUE = queues.BaseTemporaryQueue
    PREFETCH_COUNT = None
    SPEC = SPEC
    MESSAGE_PERSISTENCE = common.NON_PERSISTENT
    RATE = None
    CONSUMER_TAG = None

    default_logger = log

    def __init__(self, key_params=None, rate=None, routing_keys=None):
        self.protocol = None
        self._queue = self._exchange = None
        self._spec = None
        from twisted.internet import reactor # Apache has issues importing reactor!

        self.reactor = reactor
        super(MessageConsumer, self).__init__()
        if key_params is None: key_params = {}
        self.key_params = key_params
        self.running = True
        self.chan = self.conn = None
        self.consumer_tag = self.CONSUMER_TAG or str(uuid4())
        self._rate = rate
        self.queue_instance = self.QUEUE(**self.key_params)
        self.exchange_instance = self.EXCHANGE(**self.key_params)
        self.routing_keys = routing_keys
        self.defer_until_reading = None
        self.processor = TwistedEventRegistry()
        self.log_info('Starting AMQP Consumer')

    def log_header_dict(self, *args, **kwargs):
        d = super(MessageConsumer, self).log_header_dict(*args, **kwargs)
        d['name'] = str(self)
        d['uuid'] = self.consumer_tag
        d['queue'] = self.queue_key
        d['exchange'] = self.exchange_key
        try:
            d['routing key'] = ','.join(self.routing_keys)
        except Exception:
            d['routing key'] = '%s: Could not parse' % repr(self)
        if self.chan:
            d['channel'] = self.chan.id
        return d

    @property
    def vhost(self):
        return self.VHOST % self.key_params

    @property
    def spec(self):
        if not self._spec:
            self._spec = txamqp.spec.load(self.SPEC)
        return self._spec

    @property
    def queue_key(self):
        try:
            return self.queue_instance.key()
        except ValueError:
            log.error('COULD NOT GENERATE KEY FOR QUEUE: %s' % self.QUEUE.__name__)
            log.error(traceback.format_exc())
            raise

    @property
    def exchange_key(self):
        return self.exchange_instance.key()

    @property
    def routing_keys(self):
        if isinstance(self.ROUTING_KEY, basestring):
            keys = [self.ROUTING_KEY % self.key_params]
        else:
            keys = [rk % self.key_params for rk in self.ROUTING_KEY]
        return keys + self.default_keys()

    def default_keys(self):
        keys = []
        if self.EXCHANGE.TYPE == exchanges.EXCHANGE_TYPES.TOPIC:
            keys.append(self.consumer_tag)
        return keys

    @routing_keys.setter
    def routing_keys(self, keys):
        self._routing_key = keys

    @property
    def rate(self):
        return self._rate or self.RATE

    @property
    def prefetch_count(self):
        if self.rate:
            return self.PREFETCH_COUNT or 1 # There must be a prefetch limit for rate limiting
        return self.PREFETCH_COUNT

    @rate.setter
    def rate(self, val):
        self._rate = val

    @inlineCallbacks
    def rate_limit(self):
        if self.rate is not None:
            d = defer.Deferred()
            self.reactor.callLater(self.rate, d.callback, None)
            yield d
        returnValue(None)

    @inlineCallbacks
    def clean(self, msg):
        """
        Override this method if you want to unserialize a message or return an object from the message.
        """
        msg = yield msg
        if getattr(settings, 'SPEW_RESPONSE', False):
            self.log('Received: %s' % msg.content.body, log_level=5)
        returnValue(msg)

    def stop(self):
        self.running = False

    @inlineCallbacks
    def close(self):
        yield self.stop()
        returnValue(None)

    def __str__(self):
        return self.__class__.__name__


class JsonMessageConsumer(MessageConsumer):
    MESSAGE_CLASS = None # Must inherit form dict

    @inlineCallbacks
    def clean(self, msg):
        msg = yield super(JsonMessageConsumer, self).clean(msg)
        value = json.loads(msg.content.body)
        if self.MESSAGE_CLASS:
            value = self.MESSAGE_CLASS(**value)
        msg.content.body = value
        returnValue(msg)