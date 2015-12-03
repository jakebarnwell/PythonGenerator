import os
import time
import shutil
import signal
import optparse
import socket
import traceback
import logging
import re
from itertools import chain

try:
    from functools import partial
except ImportError:
    def partial(fn, *initialargs, **initialkwds):
        def proxy(*finalargs, **finalkwds):
            args = initialargs + finalargs
            kwds = initialkwds.copy()
            kwds.update(finalkwds)
            return fn(*args, **kwds)
        return proxy


from invenio_devserver.webserver import run_simple
from werkzeug._internal import _log

from invenio_devserver import config

try:
    BaseException
except NameError:
    # Python 2.4 compatibility
    BaseException = Exception


DESCRIPTION = "Invenio web server for development"
USAGE_MESSAGE = "python serve.py [-bp]"
RE_BIBFORMAT_ELEMENTS = re.compile(u"^(/modules/bibformat/lib/elements/.+\.py|/bibformat/format_elements/.+\.py)",
                                   re.U|re.I)


def get_extension(filename):
    try:
        return filename.rsplit('.', 1)[1]
    except IndexError:
        return ''


def valid_extension(filename, dirs=config.DIRS):
    """Checks the extension of the file to see if we should monitor it"""
    return get_extension(filename) in dirs.keys()


def generate_invenio_files_list(invenio_path=config.SRC_PATH):
    """Generates the list of all the source files to be monitored"""
    if isinstance(invenio_path, basestring):
        invenio_path = [invenio_path]

    def iter_files(dirname, filenames):
        return (os.path.join(dirname, filename)
                      for filename in filenames if valid_extension(filename))

    def iter_folder(folder):
        return chain(*(
            iter_files(dirname, filenames)
                                for dirname, _, filenames in os.walk(folder)
        ))

    return chain(chain(*(iter_folder(folder) for folder in invenio_path)),
                [os.path.join(config.INSTALL_PATH, 'etc/invenio-local.conf')])


def select_destination_path(filename, install_path=config.INSTALL_PATH,
                                                            dests=config.DIRS):
    dest = None

    rel_path = filename
    for src_path in config.SRC_PATH:
        if rel_path.startswith(src_path):
            rel_path = rel_path.replace(src_path, '')
            break

    ext = get_extension(filename)
    lib_dir = dests[ext]
    if lib_dir:
        if ext == 'py':
            if RE_BIBFORMAT_ELEMENTS.match(rel_path):
                lib_dir = os.path.join(lib_dir, 'bibformat_elements')
        dest = os.path.join(install_path,
                            lib_dir,
                            os.path.basename(filename))
    return dest


def update_conf():
    _log('info', ' * Updating configuration')
    ret = os.system('%s/bin/inveniocfg --update-config-py'
                                                         % config.INSTALL_PATH)
    if ret == 0:
        _log('info', 'done updating')
    else:
        _log('info', 'failed updating')


def reloader_loop(files, reloader=None, interval=1):
    """Monitor files, copies files to invenio install when they change and
    eventually restart our worker process"""
    mtimes = {}
    while 1:
        has_changes = False
        has_conf_changes = False

        for filename in set(files):
            try:
                stats = os.stat(filename)
            except AttributeError:
                continue
            except OSError:
                continue

            mtime = stats.st_mtime
            old_time = mtimes.get(filename)
            if old_time is None:
                mtimes[filename] = mtime
                continue
            elif mtime > old_time:
                mtimes[filename] = mtime
                # Sleep for a while to wait for the texteditor to
                # finish writing the file
                time.sleep(0.1)

                if os.path.basename(filename) == config.LOCAL_CONFIG_FILENAME:
                    dest = None
                else:
                    dest = select_destination_path(filename)

                if dest:
                    _log('info', ' * Detected change in %r, '
                                        'copying to %s' % (filename, dest))
                    shutil.copyfile(filename, dest)
                else:
                    _log('info', ' * Detected change in %r' % filename)

                if os.path.basename(filename) in (config.CONFIG_FILENAME,
                                                 config.LOCAL_CONFIG_FILENAME):
                    has_conf_changes = True

                has_changes = True

        if has_conf_changes:
            update_conf()

        if has_changes and reloader:
            reloader()
            if not reloader.worker_pid:
                return
            time.sleep(1)

        time.sleep(interval)


class Reloader(object):
    """Function object that reloads the worker when called"""

    def __init__(self, options, server_socket):
        """Reloader initializer

        Saves:
        * worker pid to be able to kill it
        * server socket that should be given to the worker
                        to accept connections
        """
        self.options = options
        self.worker_pid = None
        self.server_socket = server_socket

    def __call__(self):
        """Called to reload the worker"""
        if self.worker_pid:
            kill_worker(self.worker_pid)
        self.worker_pid = spawn_server(self.options, self.server_socket)


def print_traceback(sig, frame):
    traceback.print_stack(frame)


def start_server(options, server_socket, static_files=config.STATIC_FILES):
    """Start a new http server

    Called by the worker
    """
    # We only import wsgi here because this import some invenio components
    # and we do not want anything imported from invenio in the parent
    import wsgi

    wsgi.replace_error_handler()
    wsgi.wrap_warn()

    signal.signal(signal.SIGUSR1, print_traceback)

    # Hook debugging console
    if config.USE_CONSOLE or options.use_console:
        from rfoo.utils import rconsole
        rconsole.spawn_server()

    static = dict([(k, config.INSTALL_PATH + v) for k, v in static_files.items()])

    wsgi_app = wsgi.application

    if options.use_pdb:
        import pdb

        def pdb_on_error(f, *args, **kwargs):
            try:
                return f(*args, **kwargs)
            except:
                pdb.post_mortem()

        wsgi_app = partial(pdb_on_error, wsgi_app)

    def timed_out_request(f, *args, **kwargs):
        def handler(signum, frame):
            _log('info', "\033[01;31mYour request took more than %s"
                         " seconds to process\033[0m" % config.REQUEST_TIMEOUT)
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(config.REQUEST_TIMEOUT)
        try:
            return f(*args, **kwargs)
        finally:
            signal.alarm(0)

    wsgi_app = partial(timed_out_request, wsgi_app)

    run_simple(server_socket,
               wsgi_app,
               use_debugger=True,
               use_evalex=True,
               static_files=static)


def spawn_server(options, server_socket):
    """Create a new worker"""
    _log('info', ' * Spawning worker')
    pid = os.fork()
    if pid == 0:
        try:
            start_server(options, server_socket)
        except:
            print traceback.format_exc()[:-1]
            _log('info', ' * Worker crashed')
            # We do not want to free this pid because it will be killed
            while True:
                time.sleep(6000)
    return pid


def parse_cli_options():
    """Parse command line options"""
    parser = optparse.OptionParser(description=DESCRIPTION,
                                   usage=USAGE_MESSAGE)
    # Display help and exit
    parser.add_option('-b', dest='bind_address', default='localhost',
                                                    help='Address to bind to')
    parser.add_option('-p', dest='bind_port', type='int', default=4000,
                                    help='Port to bind to')
    parser.add_option('--no-reload', action='store_false', dest='auto_reload',
                      default=True, help='Disable automatic reloading\n'
                      'when a source file is changed')
    parser.add_option('--no-http', action='store_false', dest='serve_http',
                      default=True, help='Disable http server, only update '
                      'invenio install')
    parser.add_option('--pdb', dest='use_pdb', default=False,
                      action='store_true', help='Drop to python debugger\n'
                      'on errors')
    parser.add_option('-s', action='append', dest='src_path', metavar='SRC_PATH',
                      default=[], help='Source folder (one or more)')
    parser.add_option('-o', dest='install_path', metavar='INSTALL_PATH',
                      default=[], help='Path to Invenio installation.')
    parser.add_option('--use-console', action='store_true', dest='use_console',
                      default=False, help='Ability to open a remote console on worker')
    return parser.parse_args()


def kill_worker(pid):
    """Kill worker with <pid>"""
    _log('info', ' * Killing worker %r' % pid)
    os.kill(pid, signal.SIGTERM)
    _log('info', ' * Waiting for worker to stop')
    os.waitpid(pid, 0)


def create_socket(server_address, server_port):
    """Bind socket"""
    s = socket.socket(socket.AF_INET,
                           socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((server_address, server_port))
    return s


def bind_socket(options, ssl_context=None):
    server_address, server_port = options.bind_address, options.bind_port
    server_socket = create_socket(server_address, server_port)
    display_hostname = server_address != '*' and server_address or 'localhost'
    if ':' in display_hostname:
        display_hostname = '[%s]' % display_hostname
    _log('info', ' * Running on %s://%s:%d/', ssl_context is None
                         and 'http' or 'https', display_hostname, server_port)
    return server_socket


def start_reloading_server(options, ssl_context=None):
    """Prepare http server

    First binds the socket to accept connections from,
    then create a worker that will start a http server
    """
    server_socket = bind_socket(options, ssl_context)

    reloader = None
    # Create a new process group
    # Used for cleanup when quiting
    os.setpgrp()
    try:
        reloader = Reloader(options, server_socket)
        # Start first worker
        reloader()
        if reloader.worker_pid:
            invenio_files = list(generate_invenio_files_list())
            # Our infinite loop is here
            reloader_loop(invenio_files, reloader)
    except BaseException:
        if reloader and reloader.worker_pid:
            kill_worker(reloader.worker_pid)
        raise


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    logger = logging.getLogger('werkzeug')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    logger.propagate = False


def _main():
    """Script entrance"""
    setup_logging()
    (options, args) = parse_cli_options()

    # Override config SRC_PATH and INSTALL_PATH
    if options.src_path:
        config.SRC_PATH = [os.path.expanduser(x) for x in options.src_path]
    if options.install_path:
        config.INSTALL_PATH = os.path.expanduser(options.install_path)

    if options.serve_http and options.auto_reload:
        print 'HTTP Server mode with reload mode'
        start_reloading_server(options)
    elif options.serve_http:
        print 'Simple HTTP Server mode'
        start_server(options, bind_socket(options))
    elif options.auto_reload:
        print 'Copy-file only mode'
        invenio_files = list(generate_invenio_files_list())
        reloader_loop(invenio_files)


def main():
    try:
        _main()
    except KeyboardInterrupt:
        print 'Exiting'


if __name__ == '__main__':
    main()
