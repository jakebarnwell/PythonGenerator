import dbus
import sys
import daemon
import datetime
import subprocess

import settings

from time import strftime, localtime, sleep
from datetime import timedelta


def get_did_you_know():
    try:
        from bs4 import BeautifulSoup
        import urllib2
        from random import randrange
        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        infile = opener.open('http://en.wikipedia.org/wiki/Main_Page')
        soup = BeautifulSoup(infile)
        item = randrange(0, 5)
        dyk = soup.find(id="mp-dyk").find_all('li')[item].text.replace("(pictured)", "").\
                                                               replace("...", "")
        dyk = "Did you know %s" % dyk
        return dyk
    except:
        return ''


def notify_me(body='', app_name='', app_icon='',
                 timeout=int(settings.NOTIFICATION_DURATION), actions=[], hints=[], replaces_id=0):
    _bus_name = 'org.freedesktop.Notifications'
    _object_path = '/org/freedesktop/Notifications'
    _interface_name = _bus_name
    session_bus = dbus.SessionBus()
    obj = session_bus.get_object(_bus_name, _object_path)
    interface = dbus.Interface(obj, _interface_name)
    status = "C"
    timer = False
    first_time = True
    target_time = datetime.datetime.now()
    while 1:
        acpi_info = subprocess.check_output(["acpi", "-i"])
        splits = acpi_info.split(',')[2].split(' ')[1].split(':')

# Notifies if state changes
        if "Charging" in acpi_info:
            if status == "D":
                summary = "Charging (%s)" % (acpi_info.split(',')[1].split(' ')[1])
                interface.Notify(app_name, replaces_id, app_icon,
                                 summary, body, actions, hints, timeout)
            status = "C"
        else:
            if status == "C":
                summary = "I have got  %s battery" % \
                    (acpi_info.split(',')[1].split(' ')[1])
                interface.Notify(app_name, replaces_id, app_icon,
                                 summary, body, actions, hints, timeout)
            status = "D"

#Notifies if battery is less than settings time
        if splits[0] == settings.BATTERY_MIN_HOUR and splits[1] == settings.BATTERY_MIN_MI:
            percentage = "%s battery left" % (acpi_info.split(',')[1].split(' ')[1])
            summary = "%s, I'm starving!!! I'll die in 15 minutes" % (percentage)
            interface.Notify(app_name, replaces_id, app_icon,
                                 summary, body, actions, hints, timeout)

#Notifies about time and battery status in a preset time interval
        dt = datetime.datetime.now()
        if first_time or (dt.hour == next_time.hour and dt.minute == next_time.minute \
                      and dt.second == next_time.second):
            first_time = False
            acpi_info = subprocess.check_output(["acpi", "-i"])
            percentage = "%s battery left" % (acpi_info.split(',')[1].split(' ')[1])

            time_left = acpi_info.split(',')[2].split(' ')[1]
            if 'Charging' in acpi_info:
                if time_left:
                    time_left = ""  #buggy"%s hours for full charging" % (time_left)
                else:
                    time_left = "Fully Charged, Plugged In."
            else:
                if time_left:
                    time_left = "%s hours  of battery left " % (time_left)
                else:
                    time_left = ""

            if not first_time:
                news = "Its %s" % (strftime("%I:%M %p", localtime()))
            else:
                news = ''
            dyk = get_did_you_know()
            timer = True
            target_time = dt + timedelta(seconds=settings.BREAK_TIME)
            next_time = dt + timedelta(seconds=settings.NOTIFICATION_SPAN + settings.BREAK_TIME)
            summary = "%s \n %s \n %s, Time to take a short break \n%s" \
                                % (percentage, time_left, news, dyk)
            interface.Notify(app_name, replaces_id, app_icon,
                                 summary, body, actions, hints, timeout)

        # Notifies about end of break time
        if timer and dt > target_time:
            timer = False
            acpi_info = subprocess.check_output(["acpi", "-i"])
            percentage = "%s battery left" % (acpi_info.split(',')[1].split(' ')[1])

            time_left = acpi_info.split(',')[2].split(' ')[1]
            if 'Charging' in acpi_info:
                if time_left:
                    time_left = ""  # buggy"%s hours for full charging" % (time_left)
                else:
                    time_left = "Fully Charged, Plugged In."
            else:
                if time_left:
                    time_left = "%s hours  of battery left " % (time_left)
                else:
                    time_left = ""

            news = "Its %s" % (strftime("%I:%M %p", localtime()))
            summary = "%s \n %s \n %s, Break time is over, Time to Work dude !!!" \
                                % (percentage, time_left, news)
            interface.Notify(app_name, replaces_id, app_icon,
                                 summary, body, actions, hints, timeout)
        sleep(0.75)

if __name__ == '__main__':
    print "Sentience v1.1 Daemon Starting ...\n"
    print "Session Duration: %s\n" % (settings.NOTIFICATION_SPAN)
    print "Break Time: %s\n" % (settings.BREAK_TIME)
    with daemon.DaemonContext():
        notify_me()
