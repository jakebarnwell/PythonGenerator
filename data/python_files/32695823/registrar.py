import cloud.serialization.cloudpickle as cloudpickle
import inspect
import pickle
import Pyro4
import os
import re
import sys

from remote_monitor import RemoteMonitor

# Global Metadata Manager

class LocalRegistrar(object):
    """
    Manages registration of functions with the server-side registrar.
    """

    _instance = None
    _metadata_manager = None

    def register(self, function, server):
        """
        Register the function with the server.

        Returns a function id used by the local invoker to proxy the call.
        """
        registrar_uri = "PYRO:remote_registrar@{0}:8007".format(server)
        remote_registrar = Pyro4.Proxy(registrar_uri)
        pickled_function = cloudpickle.dumps(function)

        try:
            if self._metadata_manager is None:
                self._metadata_manager = remote_registrar.get_metadata()
            # Check to see if function has been registered already
            pickled_function_hash = hash(pickled_function)
            if pickled_function_hash in self._metadata_manager:
                return self._metadata_manager[pickled_function_hash]
            else:
                # If not registered already, register it
                return remote_registrar.deserialize_and_register(
                    function.func_name, pickled_function)
        except Pyro4.errors.CommunicationError as comm_error:
            print "Communication error:", comm_error
            print "Did you run the easyrpc start script?"
            sys.exit(1)
        except Exception as reg_error:
            print "Remote registration error:", reg_error
            sys.exit(1)

    @staticmethod
    def singleton():
        """
        Returns a singleton instance of the registrar.
        """
        if LocalRegistrar._instance is None:
            LocalRegistrar._instance = LocalRegistrar()
        return LocalRegistrar._instance


class RemoteRegistrar(object):
    """
    Implement this to register functions with the underlying framework
    on the server.
    """

    def __init__(self, invocation_daemon):
        self.invocation_daemon = invocation_daemon
        self.invocation_daemon.start()
        # A dictionary mapping hashes of pickled functions to uris.
        self.metadata_manager = {}

    def get_metadata(self):
        return self.metadata_manager

    def deserialize_and_register(self, function_name, pickled_function):
        """
        De-marshalls the function string and then delegates then
        registration to the implemented register method.
        """
        function = pickle.loads(pickled_function)


        print "\nRegistering function '{0}' with underlying framework".format(
                function_name)

        wrapped_function = RemoteMonitor()(function)
        # Add to registered functions
        uri = self.get_invocation_daemon().register(wrapped_function)
        self.metadata_manager[hash(pickled_function)] = uri
        return uri

    def get_invocation_daemon(self):
        return self.invocation_daemon
