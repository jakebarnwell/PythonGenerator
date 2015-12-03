

import hashlib
import os
import cgi
import re
import logging

from ricoraweb.model.profpage import ProfilePage
from ricoraweb.model.news import News

def _hasvalue(val):
    return val is not None and\
            len(val) > 0

def cache(f):
    def helper(self, *args, **kw):
        name = '__cache_of_' + f.__name__
        if hasattr(self, name):
            return getattr(self, name)
        else:
            val = f(self, *args, **kw)
            setattr(self, name, val)
            return val
    return helper

def cacheprop(f):
    return property(cache(f))

MemberDirFormat = ""
TrueExprs = set([ "true", "True", "TRUE", "Yes", "yes", "YES", "1", 1, True ])
FalseExprs = set([ "false", "False", "FALSE", "No", "no", "NO", "0", 0, False, None ])

class Member:
    """Exception: this class contains not "member" element but "ricora" element """
    def __init__(self, elem, studentid, path):
        if elem is None or studentid is None:
            raise TypeError()
        self.studentid = studentid
        self.elem = elem
        self.path = path

    @property
    def profile_filepath(self):
        return MemberDirFormat.format(self.studentid[:-4], self.studentid)

    @cacheprop
    def hashid(self):
        src = self.studentid
        return hashlib.md5(src.encode()).hexdigest()[:8]
    
    def check(self, out, strict=False):
        passed = self.isvalid(out) 
        if not passed:
            out.error("????????????????????????????")
        else:
            result = self._check_children(out) 
            if not result:
                out.warn("???????????????????????????????????")
            else:
                out.info("Validation passed.")
            if strict:
                passed = passed and result
        return passed

    def _check_children(self, out):
        result = True
        if not self.aboutme.isvalid(out):
            result = False
        if self.news:
            for n in self.news:
                if not n.isvalid(out):
                    result = False
        return result

    def isvalid(self, out=None):
        e = self.elem
        iv =  (e.aboutme is not None)  and _hasvalue(e.aboutme.name)
        if not iv and out is not None:
            out.warn("???????/ricora/aboutme/name??????? at /ricora/aboutme/name")
        return iv
    
    @property
    def name(self):
        n = self.aboutme.name
        if n is None:
            raise XmlFormatException("Name?????????", "Ricora")
        return n
    
    @cacheprop
    def aboutme(self):
        if self.elem.aboutme is not None:
            return AboutMe(self.elem.aboutme, self)

    @cacheprop
    def news(self):
        if self.elem.news is not None:
            return News.create(self.elem.news.post, self)

    def find_file(self, path):
        rel = os.path.join(os.path.dirname(self.path), path)
        return os.path.abspath(rel)

    @property
    def logger(self):
        try:
            return self._logger
        except AttributeError:
            self._logger = logging.getLoggerClass("member")\
                    .getChild(self.studentid)
            return self._logger

    def __str__(self):
        return "<Member id:{0}({1}) name:{2}>".format(self.studentid, self.hashid, self.name)

    def __repr__(self):
        return "<ricoraweb.model.member.Member id:{0}({1}) name:{2} at {3}>"\
                .format(self.studentid, self.hashid, self.name, hex(id(self)))

class AboutMe: #{{{
    def __init__(self, elem, member):
        self.elem = elem
        self.belongsto = member
    
    @property
    def name(self):
        return self.elem.name

    @property
    def dept(self):
        return self.elem.dept

    @property
    def comment(self):
        if self.elem.comment is not None:
            return self.elem.comment.text

    @property
    def grade(self):
        return self.elem.grade
    
    @cacheprop
    def twitter(self):
        if self.elem.twitter is not None:
            return Twitter(self.elem.twitter)
    
    @cacheprop
    def hatena(self):
        if self.elem.hatena is not None:
            return Hatena(self.elem.hatena)
    
    @cacheprop
    def profimage(self):
        value = self.elem.profimage or self.elem.profileimage
        if value is not None:
            return ProfileImage(value, self.belongsto)
    
    @cacheprop
    def profpage(self):
        if self.elem.profilepage is not None:
            return ProfilePage(self.elem.profilepage, self.belongsto)
    
    def isvalid(self, out=None):
        result = self._check_children(out)
        return result

    def _check_children(self, out):
        values = filter(lambda x: x is not None ,
                [ self.twitter, self.hatena, self.profimage, self.profpage ])
        result = True
        for v in values:
            if not v.isvalid(out):
                result = False
        return result

        
#}}}

class Twitter: #{{{
    def __init__(self, elem):
        self.elem = elem
    
    def isvalid(self, out=None):
        has_id = self.elem is not None and _hasvalue(self.elem.id)
        if not has_id and out is not None:
            out.warn("ID????????? at /aboutme/twitter")
        return has_id

    def _extract_id(self):
        v = self.elem.id
        if not _hasvalue(v):
            return None
        if v.startswith("@"):
            return v[1:]
        else:
            return v

    @property
    def url(self):
        return "http://twitter.com/{0}".format(self._extract_id())

    @property
    def id(self):
        return "@" + self._extract_id()
#}}}

class Hatena:
    def __init__(self, elem):
        self.elem = elem

    @property 
    def diary_url(self):
        return "http://d.hatena.ne.jp/{0}".format(self.elem.id)
    
    @property
    def diary_enabled(self):
        return self.elem.linkdiary in TrueExprs

    def isvalid(self, out=None):
        return True

class ProfileImage:
    def __init__(self, elem, member):
        self.elem = elem
        self.belongsto = member

    def isvalid(self, out=None):
        hasvalue = bool(self._url_direct or \
                self._url_twitter or \
                self._url_facebook) 
        valid_url = self._url_direct_issafety() 
        if out is not None:
            if not hasvalue:
                out.warn("??????????????URL???????Twitter????Facebook?ID????????????? at /ricora/aboutme/profimage")
            else:
                if not valid_url:
                    out.warn("?????URL??????????????http, https, ftp?200??????????????? at /ricora/aboutme/profimage/@url")
        return hasvalue and valid_url
    
    @property
    def path(self):
        if self.elem.path is not None:
            return self.belongsto.member_dir(self.elem.path)
        else:
            return None

    @property
    def alt(self):
        return self.elem.alt

    @property
    def url(self):
        return self._url_direct or \
                self._url_facebook or \
                self._url_twitter

    @cache
    def _url_direct_issafety(self):
        try:
            val = self.elem.url
            return len(val) < 200 and\
                    bool(HTTP_EXPR.match(val) or FTP_EXPR.match(val))
        except TypeError:
            return True

    @cacheprop
    def _url_direct(self):
        if not self._url_direct_issafety():
            return None
        return self.elem.url
    
    @cacheprop
    def _url_twitter(self):
        src = self.elem.twitter
        if src is None:
            return None
        val = cgi.escape(src)
        return "http://api.twitter.com/1/users/profile_image/{0}?size=bigger".format(val)
    
    @cacheprop
    def _url_facebook(self):
        src = self.elem.facebook
        if src is None:
            return None
        val = cgi.escape(src)
        return "http://graph.facebook.com/{0}/picture?type=large".format(val)
        
        
class Admin:
    def __init__(self):
        raise Exception("Not implemented")

class LinkInvoke:
    def __init__(self):
        raise Exception("Not implemented")

class Project:
    def __init__(self):
        raise Exception("Not implemented")


HTTP_EXPR = re.compile(r"""
\b(?:https?|shttp)://(?:(?:[-_.!~*'()a-zA-Z0-9;:&=+$,]|%[0-9A-Fa-f
][0-9A-Fa-f])*@)?(?:(?:[a-zA-Z0-9](?:[-a-zA-Z0-9]*[a-zA-Z0-9])?\.)
*[a-zA-Z](?:[-a-zA-Z0-9]*[a-zA-Z0-9])?\.?|[0-9]+\.[0-9]+\.[0-9]+\.
[0-9]+)(?::[0-9]*)?(?:/(?:[-_.!~*'()a-zA-Z0-9:@&=+$,]|%[0-9A-Fa-f]
[0-9A-Fa-f])*(?:;(?:[-_.!~*'()a-zA-Z0-9:@&=+$,]|%[0-9A-Fa-f][0-9A-
Fa-f])*)*(?:/(?:[-_.!~*'()a-zA-Z0-9:@&=+$,]|%[0-9A-Fa-f][0-9A-Fa-f
])*(?:;(?:[-_.!~*'()a-zA-Z0-9:@&=+$,]|%[0-9A-Fa-f][0-9A-Fa-f])*)*)
*)?(?:\?(?:[-_.!~*'()a-zA-Z0-9;/?:@&=+$,]|%[0-9A-Fa-f][0-9A-Fa-f])
*)?(?:#(?:[-_.!~*'()a-zA-Z0-9;/?:@&=+$,]|%[0-9A-Fa-f][0-9A-Fa-f])*
)?
""".replace('\n', ''))
FTP_EXPR = re.compile(r"""
\bftp://(?:(?:[-_.!~*'()a-zA-Z0-9;&=+$,]|%[0-9A-Fa-f][0-9A-Fa-f])*
(?::(?:[-_.!~*'()a-zA-Z0-9;&=+$,]|%[0-9A-Fa-f][0-9A-Fa-f])*)?@)?(?
:(?:[a-zA-Z0-9](?:[-a-zA-Z0-9]*[a-zA-Z0-9])?\.)*[a-zA-Z](?:[-a-zA-
Z0-9]*[a-zA-Z0-9])?\.?|[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)(?::[0-9]*)?
(?:/(?:[-_.!~*'()a-zA-Z0-9:@&=+$,]|%[0-9A-Fa-f][0-9A-Fa-f])*(?:/(?
:[-_.!~*'()a-zA-Z0-9:@&=+$,]|%[0-9A-Fa-f][0-9A-Fa-f])*)*(?:;type=[
AIDaid])?)?(?:\?(?:[-_.!~*'()a-zA-Z0-9;/?:@&=+$,]|%[0-9A-Fa-f][0-9
A-Fa-f])*)?(?:#(?:[-_.!~*'()a-zA-Z0-9;/?:@&=+$,]|%[0-9A-Fa-f][0-9A
-Fa-f])*)?
""".replace('\n', ''))
