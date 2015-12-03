import web
import json
import datetime
import time
import uuid
import twisted
#from mimerender import mimerender
#import mimerender
from onsa_jeroen import *

render_xml = lambda result: "<result>%s</result>"%result
render_json = lambda **result: json.dumps(result,sort_keys=True,indent=4)
render_html = lambda result: "<html><body>%s</body></html>"%result
render_txt = lambda result: result

def syncmyCall(func):
    global result
    result=None
    def sync_func(*args, **kwargs):
        global result
        d=defer.maybeDeferred(func, *args, **kwargs)
        runDefer(d)
        print result
        return result
    return sync_func

@syncmyCall
@defer.inlineCallbacks
def query (nsa):
    global result
    nsa = getNSA(nsa)
    client,client_nsa = createClient()
    qr = yield client.query(client_nsa, nsa, None, "Summary", connection_ids = [] )
    result = qr

class Registrations(object):
    def __init__(self):
        self.registrations = []
        self.restoreRegistrations()
    def register(self, res_id, nsa_id):
        if res_id and nsa_id:
            self.registrations.append((res_id,nsa_id))
            self.writeOut()
    def unregister(self,res_id,nsa_id):
        if not nsa_id:
            for resnsa in self.registrations[:]:
                if res_id == resnsa[0]:
                    print "Unregistering (%s,%s) from %s" % (res_id,resnsa[1], self.registrations)
                    self.registrations.remove(resnsa)
            self.writeOut()
        else:
            for resnsa in self.registrations[:]:
                if res_id == resnsa[0] and nsa_id == resnsa[1]:
                    self.registrations.remove(resnsa)
            self.writeOut()
    def getRegistrations(self):
        return self.registrations[:]
    def restoreRegistrations(self):
        try:
            self.registrations = json.load(open("reservationIDs.json",'r'))
        except ValueError:
            pass
    def writeOut(self):
        json.dump(self.registrations,open("reservationIDs.json",'w'))

urls = (
    "/(.*)", "querier"
)
app = web.application(urls, globals())

class querier:
    def GET(self,name):
        if name == "register":
            return ""
        elif name == "unregister":
            return ""
        elif name == "query":
            return query("uva4k")
            #return syncCall(query)
        elif name == "registrations":
            return ""
        else:
            return {"result":"Hello world!"}
    def POST(self,name):
        if name == "register":
            pass
        elif name == "unregister":
            pass

if __name__ == "__main__":
    setupDefer()
    app.run()
