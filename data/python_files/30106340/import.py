import sys, os
from sqlobject import *
import datetime
from model import MailItem
from email.utils import parsedate_tz
import mailbox

try:
    SCHEMA = 'sqlite://' + sys.argv[1]
except:
    SCHEMA = 'sqlite:///tmp/mail.db' # hardcoded because fuck you
    #SCHEMA = 'mysql://root:password@localhost/test'
try:
    MBOX = sys.argv[2]
except:
    MBOX = '/home/emil/torrent/gmail-backup.mbox'


connection = connectionForURI(SCHEMA)
sqlhub.processConnection = connection

MailItem.createTable(ifNotExists=True)

for e in mailbox.mbox(MBOX):
    try:
        date_tpl = parsedate_tz(e['date'])
        date = datetime.datetime(date_tpl[0], date_tpl[1], date_tpl[2], date_tpl[3], date_tpl[4], date_tpl[5])
        obj = MailItem(h_subject=e['subject'],h_from=e['from'],h_date=date)
    except TypeError:
        print "Can not convert date header into touple, skipping"

