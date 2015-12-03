import os
import sys
import glob


import objc
from Cocoa import *
from Foundation import (
    NSPredicate,
    NSMetadataQuery,
    )

from livelauncher.locating import LiveSearcher, LiveAppDescriptor, LiveAppNotFound


# (name, (services_host, web_host))
PRE_DEFINED_CONFIGURATIONS = [
    ("Select a Configuration", ("", "")),
    ("default", ("http://services.ableton.com/", "www.ableton.com")),
    ("client8131:8080 (Diez' Machine)", ("http://client8131:8080/services/", "client8131:8080")),
    ("demo-branch master", ("http://webdev.office.ableton.com/services/", "webdev.office.ableton.com")),
    ("demo-branch generic", ("http://webdev.office.ableton.com:<port>/services/", "webdev.office.ableton.com:<port>")),
    ]


class LiveLauncherDelegate(NSObject):

    # outlets
    window = objc.IBOutlet("window")
    configurationPanel = objc.IBOutlet("configurationPanel")

    # observed values
    versions = objc.ivar("versions")
    """
    List of located live-versions
    """

    live_running = objc.ivar("live_running")
    """
    Is the started application still running? Checked
    inside a watchdog routine periodically.
    """

    main_button_text = objc.ivar("main_button_text")
    """
    What to display on the main button. It depends
    on the existence of Unlock.cfg and Live running.
    """

    working = objc.ivar("working")
    """
    True if we found Live-Configurations to manipulate
    """
    services_host = objc.ivar("services_host")
    web_host = objc.ivar("web_host")
    """
    The two values for the hosts of the currently selected
    Options.txt
    """

    configuration_services_host = objc.ivar("configuration_services_host")
    configuration_web_host = objc.ivar("configuration_web_host")

    _pre_defined_entry = PRE_DEFINED_CONFIGURATIONS[0][0]

    launched_live = objc.ivar("launched_live")


    def pre_defined_entries(self):
        return [name for name, _ in PRE_DEFINED_CONFIGURATIONS]


    def pdentry(self):
        return self._pre_defined_entry


    def setPdentry_(self, value):
        self._pre_defined_entry = value
        for name, (sh, wh) in PRE_DEFINED_CONFIGURATIONS:
            if name == value:
                self.configuration_web_host = wh
                self.configuration_services_host = sh


    def observeValueForKeyPath_ofObject_change_context_(
        self,
        path,
        ud,
        _change,
        _context):
        if path == "remove_unlocks":
            self.set_button_text()
        elif path == "selected_version":
            self.version_changed(
                ud.stringForKey_(path)
                )


    def init(self):
        self = super(LiveLauncherDelegate, self).init()
        self.start_spotlight_query()
        # establish a kv-observer for the defaults
        defaults = {
                "selected_version" : "",
                "remove_unlocks" : False,
                "found_versions" : [],
                }

        ud = NSUserDefaults.standardUserDefaults()
        ud.registerDefaults_(
            defaults
            )
        for key in defaults:
            ud.addObserver_forKeyPath_options_context_(
                self,
                key,
                0,
                None,
                )


        # instance variables
        self.launched_live = None
        self.working = True
        self.live_running = False
        self.live_descriptors = set()

        return self


    def applicationDidFinishLaunching_(self, _):
        ud = NSUserDefaults.standardUserDefaults()
        for path in ud.objectForKey_("found_versions"):
            try:
                ld = LiveAppDescriptor(path)
                self.add_live_desc(ld)
            except LiveAppNotFound:
                pass
        self.version_changed(self.selected_version)



    @property
    def selected_version(self):
        ud = NSUserDefaults.standardUserDefaults()
        version = ud.stringForKey_("selected_version")
        if version:
            return version
        return None


    def applicationWillTerminate_(self, _):
        ud = NSUserDefaults.standardUserDefaults()
        ud.setObject_forKey_(
            [ld.path for ld in self.live_descriptors],
             "found_versions",
            )
        ud.synchronize()


    def start_spotlight_query(self):
        self.live_searcher = LiveSearcher.alloc().init()
        nc = NSNotificationCenter.defaultCenter()
        nc.addObserver_selector_name_object_(
            self,
            self.foundLive_,
            LiveSearcher.FOUND_LIVE,
            self.live_searcher,
            )
        self.live_searcher.start_spotlight_query()


    def foundLive_(self, notification):
        live_desc = notification.live()
        self.add_live_desc(live_desc)


    def add_live_desc(self, live_desc):
        # this is done because the version might
        # be the same, but not the path. So we
        # want the latest and greatest
        if live_desc in self.live_descriptors:
            self.live_descriptors.remove(live_desc)
        self.live_descriptors.add(live_desc)
        self.versions = sorted(ld.version for ld in self.live_descriptors)
        if self.selected_version is None and self.versions:
            ud = NSUserDefaults.standardUserDefaults()
            ud.setObject_forKey_(self.versions[0], "selected_version")
            self.version_changed(self.selected_version)




    def live_desc_for_version(self, version):
        for ld in self.live_descriptors:
            if ld.version == version:
                return ld


    def version_changed(self, version):
        ld = self.live_desc_for_version(version)
        if ld is None:
            self.working = False
            self.services_host = None
            self.web_host = None
        else:
            self.services_host = ld.services_host
            self.web_host = ld.web_host
            self.working = True

        self.set_button_text()


    def set_button_text(self):
        # true if the file exists, and our options tell us to actually
        # use it.
        if self.live_running:
            text = "Stop Live"
        elif self.remove_unlock_file():
            text = "Remove Unlock.cfg and start Live"
        else:
            text = "Start Live"

        self.main_button_text = text


    def remove_unlock_file(self):
        ud = NSUserDefaults.standardUserDefaults()
        if ud.boolForKey_("remove_unlocks"):
            ld = self.live_desc_for_version(self.selected_version)
            if ld is not None:
                return ld.has_unlock_file
        return False



    def live_watchdog(self):
        try:
            if self.launched_live is None or self.launched_live.valueForKey_("terminated"):
                self.launched_live = None
                self.live_running = False
                return
            self.live_running = True
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                .250,
                self,
                self.live_watchdog,
                None,
                False,
                )
        finally:
            self.set_button_text()


    def launch_live(self):
        """
        Tries to launch the Live for the current version.
        """
        self.launched_live = None
        ws = NSWorkspace.sharedWorkspace()
        ld = self.live_desc_for_version(self.selected_version)
        if ld is None:
            return
        url = NSURL.fileURLWithPath_(ld.path)
        rapp, error = ws.launchApplicationAtURL_options_configuration_error_(
            url,
            0,
            None,
            None,
            )
        self.launched_live = rapp
        self.live_watchdog()


    def terminate_live(self):
        if self.launched_live is None:
            return
        self.launched_live.forceTerminate()
        self.launched_live = None

    # actions

    def unlockConfiguration_(self, _):
        if self.live_running:
            self.terminate_live()
        else:
            if self.remove_unlock_file():
                ld = self.live_desc_for_version(self.selected_version)
                if ld is not None:
                    ld.remove_unlock_file()

            self.terminate_live()
            self.launch_live()



    def configureHosts_(self, _):
        self.configuration_web_host = self.web_host
        self.configuration_services_host = self.services_host

        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.configurationPanel,
            self.window,
            self,
            None,
            None,
            )

        code = NSApp.runModalForWindow_(self.configurationPanel)
        # clean up the sheet
        NSApp.endSheet_(self.configurationPanel)
        self.configurationPanel.orderOut_(None)

        if code:
            web_host = self.configuration_web_host
            services_host = self.configuration_services_host
            ld = self.live_desc_for_version(self.selected_version)
            if ld is not None:
                ld.write_host_options(services_host, web_host)
            self.version_changed(self.selected_version)



    def acceptConfiguration_(self, _):
        NSApp.stopModalWithCode_(1)


    def rejectConfiguration_(self, _):
        NSApp.stopModalWithCode_(0)


