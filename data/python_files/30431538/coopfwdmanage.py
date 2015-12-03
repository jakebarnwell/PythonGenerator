import sys
import re
import datetime
todaystr = datetime.date.today().strftime("%d-%b-%Y")
from config import *
from crypto import encrypt, decrypt

## Cal Henderson: http://iamcal.com/publish/articles/php/parsing_email/pdf/
qtext = '[^\\x0d\\x22\\x5c\\x80-\\xff]'
dtext = '[^\\x0d\\x5b-\\x5d\\x80-\\xff]'
atom = '[^\\x00-\\x20\\x22\\x28\\x29\\x2c\\x2e\\x3a-\\x3c\\x3e\\x40\\x5b-\\x5d\\x7f-\\xff]+'
quoted_pair = '\\x5c[\\x00-\\x7f]'
domain_literal = "\\x5b(?:%s|%s)*\\x5d" % (dtext, quoted_pair)
quoted_string = "\\x22(?:%s|%s)*\\x22" % (qtext, quoted_pair)
domain_ref = atom
sub_domain = "(?:%s|%s)" % (domain_ref, domain_literal)
word = "(?:%s|%s)" % (atom, quoted_string)
domain = "%s(?:\\x2e%s)*" % (sub_domain, sub_domain)
local_part = "%s(?:\\x2e%s)*" % (word, word)
addr_spec = "%s\\x40%s" % (local_part, domain)
email_address = re.compile('\A%s\Z' % addr_spec)

def validEmail(email):
    return email_address.match(email) != None

def error(msg):
    return "<span style='color:red;'>{0}</span>".format(msg)

def process(uname="", passwd="", fwd=""):
    if uname=="" or passwd=="":
        return error("invalid username or password")
    #Verify credentials
    import imaplib
    M = imaplib.IMAP4_SSL("farley2.cooper.edu", 993)
    try:
	M.login(uname, passwd)
    except:
        return error("username/password rejected by cooper's mail server")
    M.select("INBOX")
    M.close()

    #Look in database
    import sqlite3
    
    conn = sqlite3.connect(INSTALL_DIR+"coopfwd.db")
    c = conn.cursor()
    
    c.execute('select * from users where username=?', (uname,))
    u = c.fetchall()

    if len(u) == 0:
        # new user
        if not validEmail(fwd):
            return error("Invalid forward email")
        c.execute('insert into users (username, password, fwd, date) values (?, ?, ?, ?)', (uname, encrypt(passwd), fwd, todaystr))
        conn.commit()
        c.close()
        return "Added forwarding for {0}@cooper.edu -> {1}".format(uname, fwd)
        
    #user exists, they must want to update or delete email:
    if validEmail(fwd):
        #they want to update
        c.execute("update users set fwd=? where username=? and password=?", (fwd, uname, encrypt(passwd)))
        conn.commit()
        c.close()
        return "Updated forwarding for {0}@cooper.edu to {1}".format(uname, fwd)

    else:
        #they want to delete
        c.execute("delete from users where username=? and password=?", (uname, encrypt(passwd)))
        conn.commit()
        c.close()
        return "Deleted forwarding for {0}@cooper.edu".format(uname)

