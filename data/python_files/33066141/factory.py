import os
from twisted.internet import reactor, protocol, defer
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from txamqp.client import TwistedDelegate
import txamqp
from djitch.amqp import common
from djitch.amqp.protocol import AmqpProtocol, ProducerMessage

__author__ = 'gdoermann'

class AmqpFactory(protocol.ReconnectingClientFactory):
    protocol = AmqpProtocol

    def __init__(self, spec_file=None, vhost=None, host=None, port=None, credentials=None, log_level=None):
        self._spec_file = spec_file
        self.spec = txamqp.spec.load(self.spec_file)
        self.credentials = credentials or common.credentials
        self.vhost = vhost or common.VHOST
        self.host = host or common.RABBIT_MQ_HOST
        self.port = port or common.RABBIT_MQ_PORT
        self.delegate = TwistedDelegate()
        self.deferred = Deferred()
        self.log_level = log_level

        self.instance = None # The protocol instance.

        self.message_queue = [] # List of messages waiting to be sent.
        self.consumers = [] # List of message consumers to listen on.

    @property
    def spec_file(self):
        if self._spec_file and os.path.exists(self._spec_file):
            return self._spec_file
        elif os.path.exists(common.AMQP_SPEC):
            return common.AMQP_SPEC
        else:
            try:
                from django.conf import settings
                return settings.AMQP_SPEC
            except Exception:
                pass

    @inlineCallbacks
    def connect(self):
        # Make the TCP connection.
        connection = yield reactor.connectTCP(self.host, self.port, self)
        returnValue(connection)

    @inlineCallbacks
    def _connected(self):
        for consumer in self.consumers:
            yield self.read(consumer)


    def buildProtocol(self, addr):
        instance = self.protocol(self.delegate, self.vhost, self.spec)

        instance.factory = self
        self.instance = instance
        self.client = instance

        self.resetDelay()
        self._connected()
        return instance


    def clientConnectionFailed(self, connector, reason):
        print("AMQP Connection Failed.")
        self._clear_consumer_deferreds()
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)


    def clientConnectionLost(self, connector, reason):
        print("AMQP Client connection lost.")
        self.instance = None
        self._clear_consumer_deferreds()
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def _clear_consumer_deferreds(self):
        for consumer in self.consumers:
            if consumer.defer_until_reading and not consumer.defer_until_reading.called:
                continue
            consumer.defer_until_reading = defer.Deferred()

    @inlineCallbacks
    def send_message(self, message, producer, **extras):
        """Send a message."""
        # Add the new message to the queue.
        self.message_queue.append(ProducerMessage(producer, message, extras))

        # Send all queued messages.
        if self.instance is not None:
            yield self.instance.send()

    def read(self, consumer):
        """
        Configure an exchange to be read from.
        This should be a Consumer instance
        """
        if consumer.defer_until_reading is None or consumer.defer_until_reading.called:
            consumer.defer_until_reading = defer.Deferred()

        # Add this to the read list so that we have it to re-add if we lose the connection.
        if consumer not in self.consumers:
            self.consumers.append(consumer)

        # Tell the protocol to read this if it is already connected.
        if self.instance is not None:
            consumer.protocol = self.instance
            return self.instance.read(consumer) # A deferred

    def shutdown(self):
        for consumer in self.consumers:
            self.stop_consuming(consumer)
        self.stopFactory()

    def stop_consuming(self, consumer):
        if consumer in self.consumers:
            self.consumers.remove(consumer)
            if self.instance:
                self.instance.stop_consuming(consumer)