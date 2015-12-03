
import json
import jsonrpc
import os
import re
import shutil
import urlparse
import uuid

from BaseHTTPServer import BaseHTTPRequestHandler


class JsonRpcRequestHandler(BaseHTTPRequestHandler):
    def setup(self):
        BaseHTTPRequestHandler.setup(self)
        self.__sessionid = None
        self.redirects = {}
        self.scripts = {}
        self.sessions = {}
        self.jsonrpcurl = '/request'
        self.webroot = './webroot'

    def do_GET(self):
        urlcomponents = urlparse.urlparse(self.path)
        mappedpath = self.redirects.get(urlcomponents.path, urlcomponents.path)
        webrootpath = self.getpage(mappedpath)
        if webrootpath:
            self.send_response(200)
            self.end_headers()

            f = file(webrootpath, 'r')
            shutil.copyfileobj(f, self.wfile)
            f.close()
        elif urlcomponents.path in self.scripts:
            method = self.scripts[urlcomponents.path]
            query = urlparse.parse_qs(urlcomponents.query)
            method("GET", "", query)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == self.jsonrpcurl:
            jsonstr = self.getdata()
            response = jsonrpc.jsonrpc(jsonstr, self)

            jsonstr = json.dumps(response, default=jsonrpc.extended_json_transform)
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(jsonstr)

        elif self.path in self.scripts:
            method = self.scripts[self.path]
            data = self.getdata()
            query = {}
            method("POST", data, query)

        else:
            self.send_error(404)

    def getdata(self):
        data = ""
        contentlengthstr = self.headers.getheader('content-length')
        if contentlengthstr:
            contentlength = int(contentlengthstr)
            data = self.rfile.read(contentlength)
        return data

    def getsession(self):
        sessionid = self.getsessionid()
        s = self.sessions[sessionid]
        return s

    def getsessioncookie(self):
        cookiestr = self.headers.getheader('cookie')
        if cookiestr:
            match = re.match(".*sessionid=([^;]*)", cookiestr)
            if match:
               sessionid = match.group(1)
               if sessionid in self.sessions:
                   return sessionid

        return None

    def sendsessioncookie(self, sessionid):
        self.send_header("Set-Cookie", "sessionid={0}; Secure; HttpOnly".format(sessionid))
        self.sessions[sessionid] = {}

    def getsessionid(self):
        if not self.__sessionid:
            self.__sessionid = self.getsessioncookie()
            if not self.__sessionid:
                self.__sessionid = str(uuid.uuid4())

        return self.__sessionid

    def end_headers(self):
        if not self.getsessioncookie():
            sessionid = self.getsessionid()
            self.sendsessioncookie(sessionid)
        BaseHTTPRequestHandler.end_headers(self)

    def getpage(self, path):
        p = os.path.join(self.webroot, path[1:])
        if os.path.isfile(p) and \
                os.path.exists(p) and \
                issubpath(self.webroot, p):
            return p

def issubpath(parentpath, subpath):
    p1 = os.path.realpath(parentpath)
    p2 = os.path.realpath(subpath)
    stem = os.path.commonprefix([p1, p2])
    return os.path.samefile(parentpath, stem)

