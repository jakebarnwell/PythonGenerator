import os
import sys
import time

import logger
from DB.db import initDB

def _initDB():
    _path = os.path.realpath(__file__)
    _dir = os.path.split(_path)[0]
    _dbname = os.path.join(_dir, "DB", "sqlite.db")
    if 1 == 1:
        initDB(_dbname)
    else:
        initDB(":memory:")

if __name__ == "__main__":
    _initDB()
    logger.initLogging([sys.stdout, file("error.log", "w")])
    import app
    _app = app.AppRoot()
    from gui import gui, main
    _gui = gui.initGui(_app)
    _gui.MainLoop()
    print "=======END======="

# vim: set et sts=4 sw=4 :
