import os
import time
import traceback

import pythoncom
import win32serviceutil
import win32service
import win32event
import servicemanager

import jagteraho


class JagteRahoService (win32serviceutil.ServiceFramework):
    _svc_name_ = "JagteRaho"
    _svc_display_name_ = "JagteRaho (KeepAlive) Service"
    _svc_description_ = "Used for keeping important services e.g. broadband connection up"

    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.stop = False

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.log('stopping')
        self.stop = True

    def log(self, msg):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_,msg))
        
    def SvcDoRun(self):
        self.log('folder %s'%os.getcwd())
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self.start()

    def shouldStop(self):
        return self.stop

    def start(self):
        try:
            configFile = os.path.join(jagteraho.getAppFolder(), "jagteraho.cfg")
            jagteraho.start_config(configFile, self.shouldStop)
        except Exception,e:
            self.log(" stopped due to eror %s [%s]" % (e, traceback.format_exc()))
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AppServerSvc)