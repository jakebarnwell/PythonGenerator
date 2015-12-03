import unittest

class ImportTest(unittest.TestCase):
    def test_import_everything(self):
        # Some of our modules are not otherwise tested.  Import them
        # all (unless they have external dependencies) here to at
        # least ensure that there are no syntax errors.
        import anzu.auth
        import anzu.autoreload
        # import anzu.curl_httpclient  # depends on pycurl
        # import anzu.database  # depends on MySQLdb
        import anzu.escape
        import anzu.httpclient
        import anzu.httpserver
        import anzu.httputil
        import anzu.ioloop
        import anzu.iostream
        import anzu.locale
        import anzu.options
        import anzu.netutil
        # import anzu.platform.twisted # depends on twisted
        import anzu.process
        import anzu.simple_httpclient
        import anzu.stack_context
        import anzu.template
        import anzu.testing
        import anzu.util
        import anzu.web
        import anzu.websocket
        import anzu.wsgi

    # for modules with dependencies, if those dependencies can be loaded,
    # load them too.

    def test_import_pycurl(self):
        try:
            import pycurl
        except ImportError:
            pass
        else:
            import anzu.curl_httpclient

    def test_import_mysqldb(self):
        try:
            import MySQLdb
        except ImportError:
            pass
        else:
            import anzu.database

    def test_import_twisted(self):
        try:
            import twisted
        except ImportError:
            pass
        else:
            import anzu.platform.twisted
