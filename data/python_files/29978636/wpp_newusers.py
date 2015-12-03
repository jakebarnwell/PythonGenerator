import codecs
import datetime
import functools
import httplib2
import itertools
import logging
from lxml import html
import mwclient
from pprint import pprint
import time
import unittest
import urllib
import urlparse

import MySQLdb
import MySQLdb.cursors

from wpp_settings import WPPRY_USER, WPPRY_PW, WPPRY_DB, WPPRY_HOST, WPPRY_PORT

# http://stackoverflow.com/questions/2348317/how-to-write-a-pager-for-python-iterators/2350904#2350904        
def grouper(iterable, page_size):
    page= []
    for item in iterable:
        page.append( item )
        if len(page) == page_size:
            yield page
            page= []
    if len(page):
        yield page
        
def filter_none_value(d):
    return dict([(k,v) for (k,v) in d.items() if v is not None])
    
# http://stackoverflow.com/questions/390250/elegant-ways-to-support-equivalence-equality-in-python-classes    
class CommonEqualityMixin(object):

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

class EndOfUserToken(CommonEqualityMixin):
    def __init__(self,user_name,timestamp):
        self.user_name = user_name
        self.timestamp = timestamp
    def __repr__(self):
        return u"EndOfUserToken: " + unicode(self.user_name) + u"|" +  unicode(self.timestamp)
        
def st_cmp(x,y):
    if x is None and y is not None:
        return -1  # x < y
    elif y is None and x is not None:
        return 1 # x > y
    elif x is None and y is None:
        return 0
    elif x < y:
        return -1
    elif x == y:
        return 0
    else:
        return 1

def et_cmp(x,y):
    if x is None and y is not None:
        return 1  # x > y
    elif y is None and x is not None:
        return -1 # x < y
    elif x is None and y is None:
        return 0
    elif x < y:
        return -1
    elif x == y:
        return 0
    else:
        return 1

def dt_in_range(dt, start, end):
    """ is dt within the range from start to end (equality with start or end is considered in range; None for start or end means unspecified
        Make sure all arguments are datetime.datetime"""
    
    logging.debug("in dt_in_range...")
    logging.debug("dt, start, end: %s | %s | %s " % (dt,start,end))
    (dt2, start2, end2) = map(struct_time_to_datetime,(dt,start,end))
    logging.debug("dt2, start2, end2: %s | %s | %s " % (dt2,start2,end2))
    if start2 is not None:
        start_condition = (dt2 >= start2)
    else:
        start_condition = True
    
    if end2 is not None:
        end_condition = (dt2 <= end2)
    else:
        end_condition = True
        
    logging.debug("start_condition, end_condition: %s | %s " % (start_condition, end_condition))    
    return start_condition and end_condition
    
key_st_cmp = functools.cmp_to_key(st_cmp)
key_et_cmp = functools.cmp_to_key(et_cmp)

def struct_time_to_datetime(timestamp):
    # don't touch None but allow it
    if isinstance(timestamp, time.struct_time):
        return datetime.datetime(*timestamp[:6])
    else:
        return timestamp

class TestComparison(unittest.TestCase):
    def test_st_cmp(self):
        self.assertEqual(st_cmp(datetime.datetime(2010,9,10,0,0,0), datetime.datetime(2010,9,10,0,0,1)), -1)
        self.assertEqual(st_cmp(datetime.datetime(2010,9,10,0,0,2), datetime.datetime(2010,9,10,0,0,1)), 1)
        self.assertEqual(st_cmp(datetime.datetime(2010,9,10,0,0,0), datetime.datetime(2010,9,10,0,0,0)), 0)
        self.assertEqual(st_cmp(None, datetime.datetime(2010,9,10,0,0,1)), -1)
        self.assertEqual(st_cmp(datetime.datetime(2010,9,10,0,0,1), None), 1)
        self.assertEqual(st_cmp(None, None), 0)
    def test_start_times_sort(self):
        start_times = [datetime.datetime(2010,9,10,0,0,0), datetime.datetime(2010,9,10,0,0,1), None]
        sorted_start_times = sorted(start_times,cmp=st_cmp)
        self.assertEqual(sorted_start_times, [None,datetime.datetime(2010,9,10,0,0,0), datetime.datetime(2010,9,10,0,0,1)])
    def test_start_times_w_key(self):
        start_times = [datetime.datetime(2010,9,10,0,0,0), datetime.datetime(2010,9,10,0,0,1), None]
        sorted_start_times = sorted(start_times,key=key_st_cmp)
        self.assertEqual(sorted_start_times, [None,datetime.datetime(2010,9,10,0,0,0), datetime.datetime(2010,9,10,0,0,1)])
    def test_st_cmp_min_max(self):
        start_times = [datetime.datetime(2010,9,10,0,0,0), datetime.datetime(2010,9,10,0,0,1), None]
        self.assertEqual(min(start_times,key=key_st_cmp),None)
        self.assertEqual(max(start_times,key=key_st_cmp),datetime.datetime(2010,9,10,0,0,1))
    def test_et_cmp(self):
        self.assertEqual(et_cmp(datetime.datetime(2010,9,10,0,0,0), datetime.datetime(2010,9,10,0,0,1)), -1)
        self.assertEqual(et_cmp(datetime.datetime(2010,9,10,0,0,2), datetime.datetime(2010,9,10,0,0,1)), 1)
        self.assertEqual(et_cmp(datetime.datetime(2010,9,10,0,0,0), datetime.datetime(2010,9,10,0,0,0)), 0)
        self.assertEqual(et_cmp(None, datetime.datetime(2010,9,10,0,0,1)), 1)
        self.assertEqual(et_cmp(datetime.datetime(2010,9,10,0,0,1), None), -1)
        self.assertEqual(et_cmp(None, None), 0)
    def test_end_times_sort(self):
        end_times = [datetime.datetime(2010,9,10,0,0,0), None, datetime.datetime(2010,9,10,0,0,1)]
        sorted_end_times = sorted(end_times,cmp=et_cmp)
        self.assertEqual(sorted_end_times, [datetime.datetime(2010,9,10,0,0,0), datetime.datetime(2010,9,10,0,0,1), None])
    def test_end_times_w_key(self):
        end_times = [datetime.datetime(2010,9,10,0,0,0), None, datetime.datetime(2010,9,10,0,0,1)]
        sorted_end_times = sorted(end_times,key=key_et_cmp)
        self.assertEqual(sorted_end_times, [datetime.datetime(2010,9,10,0,0,0), datetime.datetime(2010,9,10,0,0,1), None])
    def test_et_cmp_min_max(self):
        end_times = [datetime.datetime(2010,9,10,0,0,0), None, datetime.datetime(2010,9,10,0,0,1)]
        self.assertEqual(min(end_times,key=key_et_cmp),datetime.datetime(2010,9,10,0,0,0))
        self.assertEqual(max(end_times,key=key_et_cmp),None)
    def test_dt_in_range(self):
        # firmly in middle
        self.assertEqual(dt_in_range(dt=datetime.datetime(2010,9,10,0,0,0),start=datetime.datetime(2010,8,10,0,0,0),end=datetime.datetime(2010,10,10,0,0,0)),
            True)
        # dt = start
        self.assertEqual(dt_in_range(dt=datetime.datetime(2010,8,10,0,0,0),start=datetime.datetime(2010,8,10,0,0,0),end=datetime.datetime(2010,10,10,0,0,0)),
            True)
        # dt = end
        self.assertEqual(dt_in_range(dt=datetime.datetime(2010,10,10,0,0,0),start=datetime.datetime(2010,8,10,0,0,0),end=datetime.datetime(2010,10,10,0,0,0)),
            True)
        # dt < start
        self.assertEqual(dt_in_range(dt=datetime.datetime(2009,9,10,0,0,0),start=datetime.datetime(2010,8,10,0,0,0),end=datetime.datetime(2010,10,10,0,0,0)),
            False)
        # dt > end
        self.assertEqual(dt_in_range(dt=datetime.datetime(2011,9,10,0,0,0),start=datetime.datetime(2010,8,10,0,0,0),end=datetime.datetime(2010,10,10,0,0,0)),
            False)
        # start = None and dt < end
        self.assertEqual(dt_in_range(dt=datetime.datetime(2010,9,10,0,0,0),start=None,end=datetime.datetime(2010,10,10,0,0,0)),
            True)
        # end = None and dt > start
        self.assertEqual(dt_in_range(dt=datetime.datetime(2010,9,10,0,0,0),start=datetime.datetime(2009,9,10,0,0,0),end=None),
            True)
        # start, end None
        self.assertEqual(dt_in_range(dt=datetime.datetime(2010,9,10,0,0,0),start=None,end=None),
            True)

class wpp_db(object):
    def __init__(self, user=WPPRY_USER, pw=WPPRY_PW, db=WPPRY_DB, host=WPPRY_HOST, port=WPPRY_PORT):
        self.user = user
        self.pw = pw
        self.db = db
        self.host = host
        self.port = port
        self.conn = MySQLdb.connect(host=self.host, port=self.port, user=self.user, passwd=self.pw, db=self.db, cursorclass=MySQLdb.cursors.DictCursor, use_unicode=True,
                           charset = "utf8")
    def get_wpp_newusers(self):
        GET_USERS_SQL = "SELECT * from wpp_newusers;"
        cur = self.conn.cursor()
        cur.execute(GET_USERS_SQL)
        for user in cur:
            yield user
    def get_users_without_registration(self):
        NO_REGISTRATION_SQL = "SELECT name FROM wpp_newusers WHERE registration is  null and missing <> 1;"
        cur = self.conn.cursor()
        cur.execute(NO_REGISTRATION_SQL)
        for user in cur:
            yield user
    def get_users_by_last_updated(self,dir="ASC"):
        LAST_UPDATED_SQL = "SELECT name, last_updated, editcount FROM wpp_newusers WHERE missing <> 1 ORDER BY last_updated %s;" % (dir)
        cur = self.conn.cursor()
        cur.execute(LAST_UPDATED_SQL)
        for user in cur:
            yield user
    def put_wpuser(self, name, emailable=None, blockedby=None, blockreason=None, missing=False, gender=None, editcount=None, registration=None, groups=None, record_created=None, last_updated=None,
                   rev_id=None, rev_title=None, rev_timestamp=None, invalid=False):
        # check whether name already exists -- can this be done in SQL?
        wpuser_fields = ["name", "emailable", "blockedby", "blockreason", "missing", "gender", "registration", "groups", "record_created", "last_updated", "editcount", "rev_id",
                         "rev_title", "rev_timestamp", "invalid"]
        if record_created is None:
            #record_created = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            record_created = datetime.datetime.utcnow()
        if last_updated is None:
            last_updated = record_created
        # convert registration to datetime.datetime
        if registration is not None:
            registration = datetime.datetime.strptime(registration,"%Y-%m-%dT%H:%M:%SZ")

        wpuser_values = [name, emailable, blockedby, blockreason, missing, gender, registration, groups, record_created, last_updated, editcount, rev_id, rev_title, rev_timestamp, invalid]
        
        # I don't allow for the updating of rev_id, rev_title, or rev_timestamp -- a bit of kludge 
        update_fields = ["emailable", "blockedby", "blockreason", "missing", "gender", "registration", "groups", "last_updated", "editcount", "invalid"]
        update_values = [emailable, blockedby, blockreason, missing, gender, registration, groups, last_updated, editcount, invalid]
        
        #print wpuser_values
        INSERT_USER_SQL = u"INSERT INTO wpp_newusers (%s) VALUES (%s) " % ( ", ".join(wpuser_fields), ", ".join(["%s" for k in range(len(wpuser_fields))]))
        UPDATE_CLAUSE = "ON DUPLICATE KEY UPDATE " + ", ".join(map (lambda x: x+"=%s", update_fields))
        INSERT_UPDATE_USER_SQL = INSERT_USER_SQL + UPDATE_CLAUSE + ";"
        #print INSERT_UPDATE_USER_SQL
        #print wpuser_values + update_values
        
        cur = self.conn.cursor()
        cur.execute(INSERT_UPDATE_USER_SQL, wpuser_values + update_values)
    def get_stats(self):
        GET_STATS_SQL = "SELECT count(*) as count, sum(editcount) as sum_editcount, sum(editcount)/count(*) as mean_edits_per_user, sum(emailable) as sum_emailable, min(rev_timestamp) as min_rev_timestamp , max(rev_timestamp) as max_rev_timestamp, max(editcount) as max_editcount, sum(timestampdiff(SECOND,registration,last_updated)) as sum_active_time, sum(timestampdiff(SECOND,registration,last_updated)) / sum(editcount)/(60*60*24) as mean_days_between_edit FROM wpp_newusers where missing<>1;"
        cur = self.conn.cursor()
        cur.execute(GET_STATS_SQL)
        return cur.fetchone()
    
class wpp_db2(wpp_db):
    """ subclassing wpp_db for now to help in development -- don't want to break wpp_db"""
    def get_usercontribs(self):
        GET_USERCONTRIBS_SQL = "SELECT * from wpp_usercontribs;"
        cur = self.conn.cursor()
        cur.execute(GET_USERCONTRIBS_SQL)
        for contrib in cur:
            yield contrib
    def get_usercontrib_by_rev_id(self, rev_id):
        pass
    def put_usercontrib(self, rev_id, page_title=None, page_id=None, user_name=None, comment=None, parsedcomment=None,
                        minor=None, commenthidden=None, patrolled=None, timestamp=None, namespace=None, tags=None, record_created=None,
                        last_updated=None, missing=False):
        #wpp_usercontribs_fields = ['rev_id', 'page_title', 'page_id', 'user_name', 'comment', 'parsedcomment', 'minor', 'patrolled', 'timestamp', 'namespace', 'tags', 'record_created', 'last_updated', 'missing']
        if record_created is None:
            record_created = datetime.datetime.utcnow()
        if last_updated is None:
            last_updated = record_created
        
        # convert timestamp to datetime.datetime -- I think timestamp is a time.struct_time
        if timestamp is not None:
            if isinstance(timestamp,time.struct_time):
                timestamp = datetime.datetime(*timestamp[:6])
            
        wpp_usercontribs_dict = filter_none_value({'rev_id': rev_id, 'page_title': page_title, 'page_id': page_id, 'user_name': user_name,
                                 'comment': comment, 'parsedcomment': parsedcomment, 'minor': minor, 'commenthidden':commenthidden,
                                 'patrolled': patrolled, 'timestamp': timestamp, 'namespace': namespace, 'tags': tags, 'record_created': record_created,
                                 'last_updated': last_updated, 'missing': missing})
        
        # which fields are updatable: not rev_id, record_created
        
        wpp_usercontribs_update_fields = filter_none_value({'page_title': page_title, 'page_id': page_id, 'user_name': user_name,
                                 'comment': comment, 'parsedcomment': parsedcomment, 'minor': minor, 'commenthidden':commenthidden,
                                 'patrolled': patrolled, 'timestamp': timestamp, 'namespace': namespace, 'tags': tags,
                                 'last_updated': last_updated, 'missing': missing})
        INSERT_USER_SQL = u"INSERT INTO wpp_usercontribs (%s) VALUES (%s) " % ( ", ".join(wpp_usercontribs_dict.keys()),
                                                                               ", ".join(["%s" for k in range(len(wpp_usercontribs_dict.keys()))]))
        
        UPDATE_CLAUSE = "ON DUPLICATE KEY UPDATE " + ", ".join(map (lambda x: x+"=%s", wpp_usercontribs_update_fields.keys()))
        INSERT_UPDATE_USER_SQL = INSERT_USER_SQL + UPDATE_CLAUSE + ";"
        #print
        #print
        #print INSERT_UPDATE_USER_SQL
        #print wpp_usercontribs_dict.values() + wpp_usercontribs_update_fields.values()
        #print len(wpp_usercontribs_dict.values() + wpp_usercontribs_update_fields.values())
        
        cur = self.conn.cursor()
        cur.execute(INSERT_UPDATE_USER_SQL, wpp_usercontribs_dict.values() + wpp_usercontribs_update_fields.values())
    def get_users_by_latest_usercontribs_timestamp_checked (self):
        #LAST_UPDATED_SQL = "SELECT name, last_updated, latest_usercontribs_timestamp_checked from wpp_newusers WHERE missing <> 1 ORDER BY latest_usercontribs_timestamp_checked ASC;"
        #LAST_UPDATED_SQL = """SELECT name, latest_usercontribs_timestamp_checked, last_updated FROM wpp_newusers WHERE (latest_usercontribs_timestamp_checked IS NOT NULL) AND (latest_usercontribs_timestamp_checked < last_updated) AND (missing <> 1) UNION ALL SELECT name, latest_usercontribs_timestamp_checked, last_updated FROM wpp_newusers WHERE (latest_usercontribs_timestamp_checked IS NULL) AND (missing <> 1);"""
        LAST_UPDATED_SQL = """SELECT name, latest_usercontribs_timestamp_checked, last_updated FROM wpp_newusers WHERE (latest_usercontribs_timestamp_checked IS NULL) AND (missing <> 1) UNION ALL SELECT name, latest_usercontribs_timestamp_checked, last_updated FROM wpp_newusers WHERE (latest_usercontribs_timestamp_checked IS NOT NULL) AND (latest_usercontribs_timestamp_checked < last_updated) AND (missing <> 1);"""
        cur = self.conn.cursor()
        cur.execute(LAST_UPDATED_SQL)
        for user in cur:
            yield user
    def update_latest_usercontribs_timestamp_checked(self,user_name,timestamp):
        """write the timestamp to the database"""
        # timestamp has be of the form time.struct_time -- or I should check and allow both struct_time or datetime
        UPDATE_SQL = "UPDATE wpp_newusers SET latest_usercontribs_timestamp_checked=%s WHERE name=%s"
        cur = self.conn.cursor()
        # convert timestamp to datetime.datetime
        if isinstance(timestamp,time.struct_time):
            timestamp = datetime.datetime(*timestamp[:6])
        cur.execute(UPDATE_SQL, (timestamp,user_name))
    def get_users_by_name(self,user_names):
        """user_names is an iteration of Wikipedia user names to pull from the database"""
        GET_SQL = "SELECT * from wpp_newusers u WHERE u.name = %s;";
        cur = self.conn.cursor()
        for user_name in user_names:
            try:
                cur.execute(GET_SQL, user_name)
                for user in cur:
                    yield user
            except Exception, e:
                pass
    def get_users_with_editcount_fewer_contribs(self, limit=10000000):
        GET_SQL = """SELECT sb.user_name as name, u.editcount, sb.num_contribs, u.last_updated, u.latest_usercontribs_timestamp_checked from (SELECT c.user_name, count(*) as num_contribs from wpp_usercontribs c GROUP BY c.user_name) as sb LEFT JOIN wpp_newusers u on sb.user_name = u.name WHERE sb.num_contribs > u.editcount LIMIT %s;"""
        cur = self.conn.cursor()
        cur.execute(GET_SQL,limit)
        for user in cur:
            yield user
    def get_missing_users(self):
        MISSING_USERS_SQL = "SELECT name from wpp_newusers where missing = 1;"
        cur = self.conn.cursor()
        cur.execute(MISSING_USERS_SQL)
        for user in cur:
            yield user
    
def user_contribs(contribs="newbie",dir=None,limit=500, tagfilter=None,target=None,namespace=None,year=None,month=None,offset=None):
    # dir = None --> we start with the most recent and go back in time
    # dir=prev --> we start with oldest contributions and return them oldest->newest

    parameters = {"title":"Special:Contributions", "contribs":contribs, "limit":limit, "dir":dir, "tagfilter":tagfilter,
                  "target":target,"namespace":namespace,"year":year,"month":month, "offset":offset}
    # get rid of any parameters that are blank

    for (k,v) in parameters.items():
        if v is None:
            del parameters[k]

    base_url = "http://en.wikipedia.org"
    url = base_url + "/w/index.php?" + urllib.urlencode(parameters)
    #print url
    # now grab content of url
    h = httplib2.Http()
    
    #if dir is None: mw-nextlink holds the URL for the next page -- loop until no more mw-nextlink
    #if dir is prev: mw-prevlink holds the URL for the following page -- loop until no more mw-prevlink
    
    more_pages = True
    
    while more_pages:
            
        (resp, content) = h.request(url,"GET")
        root = html.fromstring(content)
        userlinks = userlinks = root.xpath("""//*[contains(concat( " ", @class, " " ), concat( " ", "mw-userlink", " " ))]""")
        
        if dir is None:
            following_page = root.xpath("//a[@class='mw-nextlink']")
        elif dir == "prev":
            following_page = root.xpath("//a[@class='mw-prevlink']")
            userlinks.reverse() # to get links in chronological order
            
        if len(following_page) > 0:
            url = base_url + following_page[0].attrib["href"]
        else:
            more_pages = False
            
        for user in userlinks:
            # get parent
            li = user.getparent()
            rev_data = dict()
            rev_data["li"] = li
            rev_data["name"] = user.text
            
            li_children = li.getchildren()
            a0 = li_children[0]
            
            # check whether the first child is an anchor -- if it isn't then a deleted rev is represented and we skip (for now)
            if (a0.tag == "a"):
            
                # have to check whether the rev has been deleted
                # e.g., <span class="history-deleted">07:25, 6 September 2010</span>
                # extract the timestamp, title, revid from the first anchor
                
                rev_data["timestamp"] = datetime.datetime.strptime(a0.text,"%H:%M, %d %B %Y")
                href = urlparse.urlparse(a0.attrib["href"]).query
                rev_data["title"] = urlparse.parse_qs(href)["title"][0]
                rev_data["revid"] = urlparse.parse_qs(href)["oldid"][0]

                yield rev_data
            else:
                continue # go to next user


def sample_users(offset=None, dir="prev",page_size=500, max_revs=50000, continue_from_rev_timestamp=None,db=None):
    """
    if continue_from_wp_timestamp is not None, see whether it's max or min -- and set offset to the corresponding value
    """
    user_set = set()
    if db is None:
        db = wpp_db()
    stats = db.get_stats()
    if continue_from_rev_timestamp == "max":
        offset = stats["max_rev_timestamp"].strftime("%Y%m%d%H%M%S")
    elif continue_from_rev_timestamp == "min":
        offset = stats["min_rev_timestamp"].strftime("%Y%m%d%H%M%S")
    
    for (i,data) in enumerate(itertools.islice(user_contribs(limit=page_size, dir="prev", offset=offset),max_revs)):
      u = data["li"]
      print i, data["name"], data["timestamp"], data["title"], data["revid"]
      user_set.add(data["name"])
      db.put_wpuser(name=data["name"], rev_id=data["revid"], rev_title=data["title"], rev_timestamp=data["timestamp"])

class wpp_newusers_updater(object):
    def __init__(self, user="wppry", pw="wppry", db="wppry", host="127.0.0.1", port=3306):
        self.db = wpp_db(user=user,pw=pw,db=db,host=host,port=port)
        self.mw = mwclient.Site("en.wikipedia.org")
    def update_users(self,users,max_to_update=100000):
        page_size = 50  # the limit for the number of user ids to pass in.
        for page in grouper(itertools.islice(users,max_to_update),page_size):
            user_names = []
            for user in page:
                user_names.append(user["name"])
            # "blockinfo|groups|editcount|registration|emailable|gender"
            #print "user_names to query: ", user_names
            user_data = list(self.mw.users(user_names,prop="blockinfo|groups|editcount|registration|emailable|gender"))
            #pprint (user_data)
            for d in user_data:
                name = d["name"]
                if d.has_key("invalid"):
                    invalid = True
                    missing = True
                    print "INVALID: ", name
                    self.db.put_wpuser(name=name,missing=missing, invalid=invalid)
                elif d.has_key("missing"):
                    missing = True
                    print name, missing
                    self.db.put_wpuser(name=name,missing=missing)
                else:
                    try:
                        missing = False
                        registration = d["registration"]
                        gender = d["gender"]
                        editcount = d["editcount"]
                        if d.has_key("emailable"):
                            emailable = True
                        else:
                            emailable = False
                        if d.has_key("blockedby"):
                            blockedby = d["blockedby"]
                            blockreason = d["blockreason"]
                        else:
                            blockedby = None
                            blockreason = None
                        if d.has_key("groups"):
                            groups = ", ".join(d["groups"])
                        else:
                            groups = None
                        print name, registration, gender, editcount, emailable, blockedby, blockreason, groups, missing
                        self.db.put_wpuser(name=name,emailable=emailable,blockedby=blockedby,blockreason=blockreason, missing=missing,
                                           gender=gender,editcount=editcount,registration=registration,groups=groups)
                    except Exception, e:
                        print "ERROR: ", e
                        print name, d
                        raise e
    def update_users_without_registration(self,max_to_update=10000):
        users_without_reg = self.db.get_users_without_registration()
        self.update_users(users_without_reg,max_to_update)
    def update_users_by_lastupdate(self,max_to_update=10000):
        users = self.db.get_users_by_last_updated()
        self.update_users(users,max_to_update)
    
class wpp_usercontribs_updater(object):
    def __init__(self, user=WPPRY_USER, pw=WPPRY_PW, db=WPPRY_DB, host=WPPRY_HOST, port=WPPRY_PORT):
        self.db = wpp_db2(user=user,pw=pw,db=db,host=host,port=port)
        self.mw = mwclient.Site("en.wikipedia.org")
    def contribs_for_users(self,users, start='use_latest_usercontribs_timestamp_checked', end='use_wpp_newusers.last_updated',
                           add_EndOfUserToken=False):
        """iterator to produce usercontribs for users; if get_new_for_db is False, get contribs from beginning
        What options do we have here?
          * add_EndOfUserToken (default False) throw in EndOfUserToken into the stream to make it easier to recognize transition between users
          * start can be {None | a specific datetime.datetime | 'use_latest_usercontribs_timestamp_checked' (default)}
          * specify a common end for a search for all users (or none at all) or tie end for a search to the wpp_newusers.last_updated so
            we can compare wpp_newusers.editcount directly  end={None | a specific datetime.datetime | 'use_wpp_newusers.last_updated' (default)}
        """

        # have a shared end_time for all users 
        nowish = datetime.datetime(*datetime.datetime.utcnow().timetuple()[:6])
        
        for user in users:
            name = user["name"].decode("UTF-8")
            
            if start == 'use_latest_usercontribs_timestamp_checked':
                if user["latest_usercontribs_timestamp_checked"] is not None:
                    start_time = user["latest_usercontribs_timestamp_checked"]
                else:
                    start_time = None
            elif start is None:
                start_time = None
            else:
                start_time = start
                
            if end is None:
                # end_time = datetime.datetime.utcnow()
                # since mwclient uses str(dt) to convert parameters and mediawiki doesn't like subseconds, truncate the microseconds in utcnow()
                end_time = nowish
            elif end == 'use_wpp_newusers.last_updated':
                end_time = user["last_updated"]
            else:
                end_time = end
            time_params = filter_none_value({'start':start_time, 'end':end_time})
            contribs = self.user_contribs(user_name=name, **time_params)
            
            #print "contribs_for_users: ", name, start_time, end_time
            for contrib in contribs:
                yield contrib
            if add_EndOfUserToken:
                yield EndOfUserToken(user_name=name, timestamp=end_time)

    def normalize_contrib(self,contrib):

        rev_id = contrib["revid"]
        page_title = contrib["title"]
        page_id = contrib["pageid"]
        
        user_name = contrib["user"]
        
        if contrib.has_key("commenthidden"):
            comment = None
            parsedcomment = None
            commenthidden = True
        else:
            comment = contrib["comment"]
            parsedcomment = contrib["parsedcomment"]
            commenthidden = False
            
        if contrib.has_key("minor"):
            minor = True
        else:
            minor = False
        
        timestamp = contrib["timestamp"]
        # timestamp_formatted = datetime.datetime(*timestamp[:6]).isoformat()
        
        namespace = contrib["ns"]
        if contrib.has_key("tags"):  # actually an array -- should map to a comma-separated string
            tags = ", ".join(contrib["tags"])
        else:
            tags = None
        
        return {'rev_id':rev_id, 'page_title':page_title, 'page_id':page_id, 'user_name':user_name, 'comment':comment,
               'parsedcomment':parsedcomment, 'minor':minor, 'commenthidden':commenthidden, 'timestamp':timestamp,'namespace':namespace, 'tags':tags}        
        
        
    def contribs_for_users_2(self,users, start='use_latest_usercontribs_timestamp_checked', end='use_wpp_newusers.last_updated',
                           add_EndOfUserToken=False):
        """
        Rewrite to use the fact that we can pass along more than one user to the API at a time.
        
        iterator to produce usercontribs for users; if get_new_for_db is False, get contribs from beginning
        What options do we have here?
          * add_EndOfUserToken (default False) throw in EndOfUserToken into the stream to make it easier to recognize transition between users
          * start can be {None | a specific datetime.datetime | 'use_latest_usercontribs_timestamp_checked' (default)}
          * specify a common end for a search for all users (or none at all) or tie end for a search to the wpp_newusers.last_updated so
            we can compare wpp_newusers.editcount directly  end={None | a specific datetime.datetime | 'use_wpp_newusers.last_updated' (default)}
        """

        logging.debug("in contribs_for_users_2")
        
        # building this back up piece by piece
        # page through users
        page_size = 50  # the limit for the number of user ids to pass in.
        dir = 'newer'
        nowish = datetime.datetime(*datetime.datetime.utcnow().timetuple()[:6])
        logging.debug ("nowish is: " + str(nowish))
        
        for (page_num, page) in enumerate(grouper(users,page_size)):
            logging.debug("page_num: %s" %(page_num))
            user_names = []
            if add_EndOfUserToken:
                end_of_user_tokens = {}
            # need to calculate the start_times and end_times for individual accounts 
            # for each page of user accounts, also need to calculate a page start_time and end_time
            start_times = {}
            end_times = {}
            page_start_time = None
            page_end_time = None
            for user in page:
                user_name = user["name"].decode("UTF-8")
                user_names.append(user_name)
                # calculate the start_time / end_time for the user
                if start == 'use_latest_usercontribs_timestamp_checked':
                    if user["latest_usercontribs_timestamp_checked"] is not None:
                        start_times[user_name] = user["latest_usercontribs_timestamp_checked"]
                    else:
                        start_times[user_name] = None
                elif start is None:
                    start_times[user_name] = None
                else:
                    start_times[user_name] = start
                
                if end is None:
                    # end_time = datetime.datetime.utcnow()
                    # since mwclient uses str(dt) to convert parameters and mediawiki doesn't like subseconds, truncate the microseconds in utcnow()
                    end_times[user_name] = nowish
                elif end == 'use_wpp_newusers.last_updated':
                    end_times[user_name] = user["last_updated"]
                else:
                    end_times[user_name] = end
                    
                if add_EndOfUserToken:
                    end_of_user_tokens[user_name] = EndOfUserToken(user_name=user_name, timestamp=end_times[user_name])
                    
                                
            # calculate the page start_time and end_time 
            page_start_time = min(start_times.values(),key=key_st_cmp)
            page_end_time = max(end_times.values(),key=key_et_cmp)
            time_limits = filter_none_value({'start':page_start_time, 'end':page_end_time})
            user_names_string = "|".join(user_names)
            
            logging.debug("user_names_string: %s" % (user_names_string))
            logging.debug("time_limits: %s" % (time_limits))
            logging.debug("start_times: %s " % (start_times))
            logging.debug("end_times: %s " % (end_times))
            contribs = self.mw.usercontributions(user=user_names_string, prop="ids|title|timestamp|comment|parsedcomment|size|flags|tags",dir=dir, **time_limits)
            current_user = None  # track changes in users in the flow of contribs
            for (m,contrib) in enumerate(contribs):
                if current_user is None:  # take care of initialization
                    current_user = contrib["user"]
                    
                if add_EndOfUserToken:
                    if contrib["user"] != current_user:
                        logging.debug("m, EndOfUserToken for %s" % (current_user.encode("UTF-8")))
                        yield end_of_user_tokens[current_user]
                        del(end_of_user_tokens[current_user])
                        # yield EndOfUserToken(user_name=current_user, timestamp=end_times[current_user])
                        current_user = contrib["user"]
                        logging.debug("m, set (2) current_user: %s" % (current_user.encode("UTF-8")))
                        
                # check whether contrib fits in timeframe before yielding the contrib
                if dt_in_range(dt=contrib["timestamp"], start=start_times[current_user],end=end_times[current_user]):
                    logging.debug("m, contrib yielded %s %s %s %s %s" %(current_user, contrib["revid"], contrib["timestamp"], start_times[current_user], end_times[current_user]))
                    yield self.normalize_contrib(contrib)
            # yield up any other EndOfUserTokens
            if add_EndOfUserToken:
                for token in end_of_user_tokens.values():
                    yield token
                    #yield EndOfUserToken(user_name=current_user, timestamp=end_times[current_user])


    def update_contribs_of_users(self,users,max_to_update=1000000):
        #contribs = self.contribs_for_users(users,add_EndOfUserToken=True)
        contribs = self.contribs_for_users_2(users,add_EndOfUserToken=True)
        for (m,contrib) in enumerate(itertools.islice(contribs,max_to_update)):
            print m, 
            if isinstance(contrib,EndOfUserToken):
                #update the wpp_newusers table to hold the timestamp of the search for the user
                self.db.update_latest_usercontribs_timestamp_checked(contrib.user_name,contrib.timestamp)
            else:
                self.db.put_usercontrib(**contrib)
                self.db.update_latest_usercontribs_timestamp_checked(contrib["user_name"],contrib["timestamp"])
            
    def user_contribs(self,user_name,start=None,end=None,dir='newer'):
        # are there other props to look at?
        # if start is not specified, grab all the contribs
        time_limits = filter_none_value({'start':start, 'end':end})
        #print "in user_contribs (start,end): ", time_limits
        contribs = self.mw.usercontributions(user=user_name, prop="ids|title|timestamp|comment|parsedcomment|size|flags|tags",dir=dir, **time_limits)
        # ids, title, timestamp, comment, parsedcomment, size, flags, patrolled, tags
        # currently don't have permission to get patrolled flag
        for contrib in contribs:
            #print contrib
            rev_id = contrib["revid"]
            page_title = contrib["title"]
            page_id = contrib["pageid"]
            
            user_name = contrib["user"]
            
            if contrib.has_key("commenthidden"):
                comment = None
                parsedcomment = None
                commenthidden = True
            else:
                comment = contrib["comment"]
                parsedcomment = contrib["parsedcomment"]
                commenthidden = False
                
            if contrib.has_key("minor"):
                minor = True
            else:
                minor = False
            
            timestamp = contrib["timestamp"]
            # timestamp_formatted = datetime.datetime(*timestamp[:6]).isoformat()
            
            namespace = contrib["ns"]
            if contrib.has_key("tags"):  # actually an array -- should map to a comma-separated string
                tags = ", ".join(contrib["tags"])
            else:
                tags = None
            
            yield {'rev_id':rev_id, 'page_title':page_title, 'page_id':page_id, 'user_name':user_name, 'comment':comment,
                   'parsedcomment':parsedcomment, 'minor':minor, 'commenthidden':commenthidden, 'timestamp':timestamp,'namespace':namespace, 'tags':tags}
            
            
    def update_usercontribs_by_lastupdate(self,max_to_update=1000000):
        """update `wpp_usercontribs` grouped by users.  Generate a priority queue based on `latest_usercontribs_timestamp_checked`, starting with ones that
        are `null` value followed by chronological order of `wpp_usercontribs`."""
        user_queue = self.db.get_users_by_latest_usercontribs_timestamp_checked()
        self.update_contribs_of_users(user_queue,max_to_update)
        
            
    
class mwclient_demo(object):
    def __init__(self, url="en.wikipedia.org"):
        self.site = mwclient.Site(url)
    def revisions_in_page(self, page_id, num_revs):
        page = self.site.Pages[page_id]
        revisions = page.revisions(diffto='prev',prop = 'ids|timestamp|flags|comment|user|content')
        for rev in itertools.islice(revisions,num_revs):
            pprint(rev)
    def users(self,user_list,prop="blockinfo|groups|editcount|registration|emailable|gender"):
        users_data = self.site.users(user_list,prop=prop)
        return users_data
    def user_contribs(self,user_id):
        # are there other props to look at?
        contribs = self.site.usercontributions(user=user_id, prop="ids|title|timestamp|comment|parsedcomment|size|flags|patrolled|tags")
        # ids, title, timestamp, comment, parsedcomment, size, flags, patrolled, tags
        for (m,contrib) in enumerate(contribs):
            rev_id = contrib["revid"]
            page_title = contrib["title"]
            page_id = contrib["pageid"]
            
            user_name = contrib["user"]
            
            comment = contrib["comment"]
            parsedcomment = contrib["parsedcomment"]
            if contrib.has_key("minor"):
                minor = True
            else:
                minor = False
            if contrib.has_key("patrolled"):
                patrolled = True
            else:
                patrolled = False
            
            timestamp = contrib["timestamp"]
            # timestamp_formatted = datetime.datetime(*timestamp[:6]).isoformat()
            
            namespace = contrib["ns"]
            tags = contrib["tags"]
            
            print m, contrib
 
    def user_contribs_html(self,user_id):
        # get contributions for user
        # usercontributions(self, user, start = None, end = None, dir = 'older', namespace = None, prop = None, show = None, limit = None)
        contribs = self.site.usercontributions(user=user_id, prop="ids|title|timestamp|flags|comment|parsedcomment|size|tags|user")
        f = codecs.open("mwclient_user_contrib.html",mode="wb", encoding="UTF-8")
        header = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"> 
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><meta http-equiv="content-type" content="text/html; charset=utf-8"/>
     <title>mwclient user contrib test</title>
  </head>"""
        f.write(header)
        f.write("<body>")
        f.write("<table>")
        for contrib in contribs:
            title = contrib["title"]
            revid = contrib["revid"]
            comment = contrib["comment"]
            parsedcomment = contrib["parsedcomment"]

            timestamp = contrib["timestamp"]
            timestamp_formatted = datetime.datetime(*timestamp[:6]).isoformat()
            ns = contrib["ns"]
            tags = contrib["tags"]
            pageid = contrib["pageid"]
            user = contrib["user"]
            
            if contrib.has_key("minor"):
                minor = True
            else:
                minor = False
                
            # revision link e.g., http://en.wikipedia.org/w/index.php?title=Bach-Werke-Verzeichnis&oldid=383129991
            rev_url = u"http://en.wikipedia.org/w/index.php?" + urllib.urlencode({"title":title.encode("UTF-8"), "oldid":revid})
            rev_link = u"<a href='%s'>%s</a>" % (rev_url, timestamp_formatted)
            
            # diff link http://en.wikipedia.org/w/index.php?title=Bach-Werke-Verzeichnis&diff=prev&oldid=383129991
            diff_url = u"http://en.wikipedia.org/w/index.php?" + urllib.urlencode({"title":title.encode("UTF-8"), "diff":"prev", "oldid":revid})
            diff_link = u"<a href='%s'>diff</a>" % (diff_url)
            
            # page link http://en.wikipedia.org/wiki/Bach-Werke-Verzeichnis
            page_url = "http://en.wikipedia.org/wiki/%s" % (title)
            page_link = u"<a href='%s'>%s</a>" % (page_url, title)
            
            # history link http://en.wikipedia.org/w/index.php?title=Bach-Werke-Verzeichnis&action=history
            
            history_url = "http://en.wikipedia.org/w/index.php?" + urllib.urlencode({"title":title.encode("UTF-8"), "action":"history"})
            history_link = "<a href='%s'>history</a>" % (history_url)
            
            try:
                #f.write(u"&nbsp;".join(map(str,[rev_link, diff_link, history_link, pageid, revid, page_link, user, minor, u"<i>%s</i>" % (parsedcomment), "<br>"])))
                f.write(u"&nbsp;".join(map(unicode,[rev_link, diff_link, history_link, pageid, revid, page_link, user, minor, u"<i>%s</i>" % (parsedcomment), "<br>"])))
            except Exception, e:
                f.write("error writing %s <br>" % diff_link + str(e))
            #can check for whether the contribution was minor
            #pprint(contrib)
        f.write("</body>")
        f.close()
        
def test_grouper():
    limit = 2002
    page_size = 100
    for page in grouper(range(1,limit), page_size):
        for m in page:
            print m,
        print

def test_db():
    db = wpp_db()
    stats = db.get_stats()
    print stats
    print 1/0
    for u in users:
        print u
        
class edit_history_tracker (object):
    def __init__(self):
        pass

if __name__ == "__main__":
    #test_grouper()
    db1 = wpp_db()
    #db1 = wpp_db(user="wpp_test", pw="wpp_test", db="wpp_test", host="127.0.0.1", port=3306)    
    sample_users(page_size=500,max_revs=100000,continue_from_rev_timestamp="max",db=db1)
    
    # granite db
    #db2 = wpp_db(user=WPPRY_USER, pw="3k3h1974", db="wppry", host="127.0.0.1", port=3307)
    #sample_users(page_size=500,max_revs=100000,continue_from_rev_timestamp="max",db=db2)

    # local updater
    updater = wpp_newusers_updater(user=WPPRY_USER, pw=WPPRY_PW, db=WPPRY_DB, host=WPPRY_HOST, port=WPPRY_PORT)
    #updater = wpp_newusers_updater(user="wpp_test", pw="wpp_test", db="wpp_test", host="127.0.0.1", port=3306)
    updater.update_users_without_registration(200000)
    updater.update_users_by_lastupdate(500000)
    
    #granite updater -- depends on a tunnel
    # ssh -fNg -L 3307:127.0.0.1:3306 raymond@granite.ischool.berkeley.edu
    # mysql -h 127.0.0.1 -P 3307 -u root -p

    #updater2 = wpp_newusers_updater(user="root", pw="3k3h1974", db="wppry", host="127.0.0.1", port=3307)
    #updater2.update_users_without_registration(10000)
    #updater2.update_users_by_lastupdate(5000)
        
    
    #new_user_page()
    #demo = mwclient_demo('en.wikipedia.org')
    #demo.users(["RaymondYee", 'Biggles1000', 'Delta Trine'])
    #demo.revisions_in_page("User:RaymondYee",10)
    #demo.user_contribs_html("RaymondYee")
    #test_db()
    #new_user_page()

        
