import datetime
import sys
import os
import time
import socket
import logging
import logging.handlers
import ConfigParser
from ctypes import *
# reliance sometime takes too much time, so improve timeout
socket.setdefaulttimeout(60)
import urllib2
from optparse import OptionParser

from twill.commands import go, submit
from twill import get_browser

def is_frozen():
    return (hasattr(sys, "frozen") or # new py2exe
            hasattr(sys, "importers") # old py2exe
            or imp.is_frozen("__main__")) # tools/freeze

def getAppFolder():
    if is_frozen():
        thisFile = sys.executable
    else:
        thisFile = __file__

    thisFolder = os.path.abspath(os.path.dirname(thisFile))
    return thisFolder

class RelianceLogger(object):

    def __init__(self, url):
        self._browser = get_browser()
        self._browser.go(url)
        self._data = {'username':'', 'password':''}

    def _getForm(self, fieldNames):
        """
        check if login form is there, we could check for name=authenticateForm
        but what if Rel. changed name, so more stable would be field names, which anyway we will have to set
        """
        for form in self._browser.get_all_forms():
            for fieldName in fieldNames:
                isLoginForm = True
                try:
                    form.get_value('username')
                except Exception,e:
                    isLoginForm = False
                    break

            if isLoginForm:
                return form

    def _getLoginForm(self):
        return self._getForm(self._data.keys())

    def isLoggedIn(self):
        return self._getLoginForm() is None

    def login(self, userName, password):
        """
        return if was logged in or not
        """
        loginForm = self._getLoginForm()
        if loginForm is None:
            return True

        self._data['username']=userName
        self._data['password']=password

        for f, v in self._data.iteritems():
            loginForm.set_value(v, f)
        loginForm.click()
        submit()

        self._browser.showforms()

        return False

class LoginLoop(object):

    def __init__(self, url, username, password, delay, shouldStop=None):
        self._url = url
        self._username = username
        self._password = password
        self._delay = delay*60 # delay in min
        self.shouldStop = shouldStop
        if shouldStop is None:
            self.shouldStop = lambda:False
        self._log = self._setlogging()

    def _setlogging(self):
        logFile = os.path.join(getAppFolder(), "jagteraho.log")
        
        rootLogger = logging.getLogger('JAGTERAHO')
        rootLogger.setLevel(logging.DEBUG)

        # set log output
        logFileSize = 1024*1024*1024
        logBackupCount = 3
        fileHandler = logging.handlers.RotatingFileHandler(logFile, "a", logFileSize, logBackupCount)
        fileHandler.setLevel(logging.DEBUG)
        # set a format which is simpler for console use
        formatter = logging.Formatter('%(asctime)s %(name)s: %(levelname)s %(message)s')
        # tell the handler to use this format
        fileHandler.setFormatter(formatter)
        # add the handler to the root logger
        rootLogger.addHandler(fileHandler)

        return rootLogger

    def waitOrStop(self, delay):
        """
        instead of sleeping would N mins lets check every sec to stop
        """
        for i in range(delay):
            if self.shouldStop():
                return True
            time.sleep(1)
        return self.shouldStop()

    def run(self, twillOut):
        count = 0
        while 1:
            count += 1

            logger = None
            s=time.time()
            try:
                logger = RelianceLogger(self._url)
            except Exception,e:
                self._log.error("Unable to login to %s [%s]"%(self._url, e))
            else:
                self._log.debug("Already logged in :)")

            if logger is not None and not logger.isLoggedIn():
                try:
                    self._log.info("[%s] logging in..."%datetime.datetime.now().strftime("%d-%b %H:%M"))
                    logger.login(self._username, self._password)
                except Exception,e:
                    self._log.error("Error occured while logging in: %s"%e)

            if self.waitOrStop(self._delay):
                break

class Myout(object):
    def __init__(self):
        self._outList = []

    def write(self, data):
        self._outList.append(data)
        self._outList = self._outList[-10:]

def redirectTwillOut():
    import twill.commands
    import twill.browser

    # set OUT to our object and append output from twill in a list
    out = Myout()
    twill.commands.OUT = out
    twill.browser.OUT = out
    return out

def setConsoleColor(clr):
    colorMap = {'blue':1, 'green':2, 'cyan':3, 'red':4}
    windll.Kernel32.GetStdHandle.restype = c_ulong
    h = windll.Kernel32.GetStdHandle(c_ulong(0xfffffff5))
    windll.Kernel32.SetConsoleTextAttribute(h, colorMap[clr])

def start_config(configFile, shouldStopCallback=None):
    if not os.path.exists(configFile):
        raise Exception("Config file %s doesn't exist."%configFile)

    config = ConfigParser.ConfigParser()
    config.read(configFile)
    url = config.get("settings", "url")
    username = config.get("settings", "username")
    password = config.get("settings", "password")
    delay = float(config.get("settings", "delay"))

    start(url, username, password, delay, shouldStopCallback)

def start(url, username, password, delay, shouldStopCallback=None):
    twillOut = redirectTwillOut()

    loop = LoginLoop(url,username, password, delay, shouldStopCallback)
    loop.run(twillOut)

if __name__ == "__main__":

    parser = OptionParser()
    parser.add_option("-u", "--user", dest="username", help="user name for authentication", default='349174173366')
    parser.add_option("-p", "--pass", dest="password", help="password for authentication")
    parser.add_option("-l", "--link", dest="link", help="link for authentication", default='http://www.google.com')
    parser.add_option("-d", "--delay", dest="delay", help="Delay in mins, before checking website", default=2)
    parser.add_option("-c", "--config", dest="config", help="config file")
    (options, args) = parser.parse_args()
    if not options.password and not options.config:
        parser.error("Please provide a password, we have no defaults :)")

    if options.config:
        start_config(options.config)
    else:
        start(options.link, options.username, options.password, options.delay)