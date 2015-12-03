
import configparser 
import os
import csv
import logging

import ricoraweb.configs as configs
import ricoraweb.context as context
import ricoraweb.logger as logger
import ricoraweb.render as render
import ricoraweb.worker as worker
from ricoraweb.container import Container
import ricoraweb.context.manager as contextmanager

app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

DEFAULT_CONFIG  = os.path.abspath(os.path.join(app_root, "config/app.cfg"))
DEFAULT_SECTION = None #obey config file

def start(activename=DEFAULT_SECTION, conffile=DEFAULT_CONFIG, log_level=logging.DEBUG):
    container = bootstrap(activename, log_level)
    applogger = logging.getLogger('app')
    applogger.info("Collecting user data")
    context.load(container)
    applogger.info("Rendering pages")
    render.start(container)
    worker.start(container)
    applogger.info("Complete.")

def bootstrap(mode, log_level):
    il = InitLoader(mode)
    container = il.load()
    logger.init(container.config, lvl=log_level)
    logging.getLogger('app').info("Application started")
    il.report_status()
    return container

# Load list
#   Config file (configs/app.cfg)
#   Member list (configs/memberlist.txt)
#   Exec log    (configs/exec.log)
#
# Check List
#   Log output location


# memberlist loading depends on config information,
# so, config loading must be executed before memberlist loading.
class InitLoader:
    """Application Initial Load Sequence"""
    isloaded = False
    memberlist = None 
    config = None

    def __init__(self, mode=None):
        self.load(mode)

    def authorize(self, login):
        return login in self.memberlist

    def load(self, mode=None):
        if not self.isloaded:
            self.mode = mode
            self._load_config()
            self._load_memberlist()
            self._load_sequence()
            self.isloaded = True
        return self.container

    def _load_sequence(self):
        self.manager = self.create_contextmanager()
        self.container = self.create_container()
        self._init_container(self.container)

    def report_status(self):
        apl = logging.getLogger('app')
        self.config.report_status(apl)
        apl.debug("{0} members loaded".format(len(self.memberlist)))

    def create_container(self):
        cnt = Container()
        return cnt

    def _init_container(self, cnt):
        cnt.config = self.config
        cnt.manager = self.manager
        cnt.manager["memberlist"] = self.memberlist

    def create_contextmanager(self):
        val = contextmanager.Manager()
        return val

    def create_locator(self):
        return configs.Locator(self.config)

    def _load_config(self, path=DEFAULT_CONFIG):
        self.config = configs.load(path, self.mode)

    def _load_memberlist(self):
        path = self._memberlist_path()
        self.memberlist = MemberList(path)
        self.config.locator = self.create_locator()

    def _memberlist_path(self):
        return os.path.join(app_root, self.config.memberlist)


class MemberList(dict):
    def __init__(self, path):
        if not os.path.exists(path):
            raise IOError("Memberlist file not found at {0}".format(path))
        self.path = path
        self.load()

    def load(self):
        path = self.path
        self._load_fromfile(path)

    def _load_fromfile(self, path):
        with open(path) as f:
            reader = csv.reader(f)
            stripped = [[ s.strip() for s in row] for row in reader ]
            
            for row in stripped:
                if len(row) < 2:
                    self[row[0]] = None
                else:
                    self[row[0]] = row[1:]


