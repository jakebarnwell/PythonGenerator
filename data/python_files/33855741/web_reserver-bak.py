import web
import json
import datetime
import time
import uuid
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
        while 1: 
            reactor.doSelect(1)
            print result 
            time.sleep(1)
            #return result
    return sync_func

@syncmyCall
@defer.inlineCallbacks
def query (nsa):
    global result
    client,client_nsa = createClient()
    nsa = getNSA(nsa)
    qr = yield client.query(client_nsa, nsa, None, "Summary", connection_ids = [] )
    #result = qr
    result = "blaaa"

print query("uva4k")
#if __name__ == "__main__":
