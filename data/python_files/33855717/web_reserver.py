import web
import json
from twisted.internet import reactor, defer
from util import Singleton
import time, datetime
import opennsa.topology
import opennsa.setup
import opennsa.nsa
import opennsa.cli.commands
import opennsa.cli.options
import random
import uuid
import json 
import twisted.python.failure
from onsa_jeroen import createClient, getNSA, parseStpList

render_xml = lambda result: "<result>%s</result>"%result
render_json = lambda **result: json.dumps(result,sort_keys=True,indent=4)
render_html = lambda result: "<html><body>%s</body></html>"%result
render_txt = lambda result: result

@Singleton
class onsaClient():
    def __init__(self, topology):
        self.topo = opennsa.topology.gole.parseTopology([open(topology)])
        reactor.startRunning(installSignalHandlers=0)
        self.client,self.client_nsa = createClient()
        self.result=None
        self.error=None

    def syncCall(func):
        def sync_func(self, *args, **kwargs):
            self.result=None
            self.error=None
            d=defer.maybeDeferred(func,self, *args, **kwargs)
            self._runDefer(d,10)
            res=self.result
            if self.error:
                raise self.error
            return res 
        return sync_func

    def _runDefer(self,d, timeout):
        def handleError(x):
            self.error=x
        d.addErrback(handleError)
        count=0 
        while self.result == None and self.error == None and count<timeout:
            reactor.runUntilCurrent()
            reactor.doSelect(0.01)
            count=count+0.01
        if self.error: 
            raise self.error

    @syncCall
    def stop(self):
        reactor.stop()
        
    @syncCall
    @defer.inlineCallbacks
    def query (self, nsa, cid=None, gid=None):
        nsa = getNSA(nsa)
        if cid and gid: 
            print "cid and gid isn't good defaulting to cid"
        if cid:
            qr = yield self.client.query(self.client_nsa, nsa, None, "Summary", connection_ids = [ cid ] )
        elif gid:
            qr = yield self.client.query(self.client_nsa, nsa, None, "Summary", global_reservation_ids = [ gid ] )
        else:
            qr = yield self.client.query(self.client_nsa, nsa, None, "Summary", connection_ids = [] )
        self.result = qr

    @syncCall
    @defer.inlineCallbacks
    def reserve(self, srcNet, srcSTP, dstNet, dstSTP, start_time=None, length=None, gid=None, nsa=None):
        srcNet = self.topo.getNetwork(srcNet)
        srcSTP = srcNet.getEndpoint(srcSTP)
        dstNet = self.topo.getNetwork(dstNet)
        dstSTP = dstNet.getEndpoint(dstSTP)
        if nsa:
            provider_nsa = getNSA(nsa)
        else:
            provider_nsa = srcNet.nsa
        print "Reserving (%s,%s) to (%s,%s) \n at %s (%s)" % (srcNet,srcSTP,dstNet,dstSTP, provider_nsa,provider_nsa.url())
        # Setting some defaults for now, to fill in later
        start_time=None
        end_time=None
        description='CLI Test Connection'
        # Constructing the ServiceParamaters
        if not start_time:
            start_time = datetime.datetime.utcfromtimestamp(time.time() + 10 ) # two minutes from now
        if length:
            end_time   = start_time + datetime.timedelta(minutes=length) # two minutes later
        else:
            end_time   = start_time + datetime.timedelta(minutes=3) # two minutes later
        if gid:
            global_reservation_id = gid
        else:
            global_reservation_id = 'opennsa-cli:gid-%s' % random.randrange(1000,10000)
        connection_id = "urn:uuid:%s" % uuid.uuid1()
        bwp = opennsa.nsa.BandwidthParameters(200)
        service_params  = opennsa.nsa.ServiceParameters(start_time, end_time, srcSTP, dstSTP, bandwidth=bwp)
        # Send the reservation and wait for response
        r = yield self.client.reserve(self.client_nsa, provider_nsa, None, global_reservation_id, description, connection_id, service_params)
        print "Reservation created.\nReservation ID: %s\nConnection ID: %s" % (global_reservation_id,connection_id)
        self.result={ 'global_reservation_id' : global_reservation_id, 'connection_id' :  connection_id}


    @syncCall
    @defer.inlineCallbacks
    def terminate(self,nsa, cid):
        if not "http" in nsa:
            nsa = getNSA(nsa)
        print "Terminating %s at %s" % (cid, nsa)
        qr = yield self.client.terminate(self.client_nsa, nsa, None , connection_id =  cid )
        self.result=qr

    @syncCall
    @defer.inlineCallbacks
    def provision(self,nsa, cid):
        if not "http" in nsa:
            nsa = getNSA(nsa)
        print "Provisioning %s at %s" % (cid, nsa)
        qr = yield self.client.provision(self.client_nsa, nsa, None , connection_id =  cid )
        self.result=qr



class querier:
    def GET(self,name):
        try:
            if name == "terminate":
                ocli=onsaClient.Instance("/Users/ralph/4k-topo.owl")
                q = web.input(nsa="", cid="")
                return ocli.terminate(q.nsa, q.cid)
            elif name == "provision":
                ocli=onsaClient.Instance("/Users/ralph/4k-topo.owl")
                q = web.input(nsa="", cid="")
                return ocli.provision(q.nsa, q.cid)
            elif name == "query":
                ocli=onsaClient.Instance("/Users/ralph/4k-topo.owl")
                return self._queryToJSON(ocli.query("uva4k"))
            elif name == "reserve":
                ocli=onsaClient.Instance("/Users/ralph/4k-topo.owl")
                q = web.input(fromNSA="", fromSTP="", toNSA="", toSTP="")
                print "Reserving (%s, %s) to (%s, %s)"  % (q.fromNSA,q.fromSTP,q.toNSA ,q.toSTP)
                return json.dumps(ocli.reserve(q.fromNSA, q.fromSTP, q.toNSA, q.toSTP))
            else:
                return {"result":"Hello world!"}
        except twisted.python.failure.Failure, e:
            return json.dumps({'error' : str(e)}) 

    def POST(self,name):
        if name == "register":
            pass
        elif name == "unregister":
            pass

    def _queryToJSON(self, qr):
        if hasattr(qr,"reservationSummary"):
            reslist=[]
            for res in qr.reservationSummary:
                resdict={}
                resdict["global-reservation-id"] = str(res.globalReservationId)
                if hasattr(res,"description"):
                    resdict["description"] = str(res.description)
                resdict["startTime"] = res.serviceParameters.schedule.startTime
                resdict["endTime"] = res.serviceParameters.schedule.endTime
                resdict["bandwidth"] = str(res.serviceParameters.bandwidth.desired)
                resdict["status"] = str(res.connectionState)
                if hasattr(res,"path"):
                    if hasattr(res.path,"stpList"):
                       resdict['stplist'] =  (res.path.stpList.stp)
                       resdict["parsedList"] =  (parseStpList(res.path.stpList.stp))
                       pass
                    else:
                       resdict["stpList"] = [res.path.sourceSTP.stpId,res.path.destSTP.stpId]
                       pass
                reslist.append(resdict)
            return json.dumps(reslist,sort_keys=True, indent=4)
        return None

if __name__ == "__main__":
    ocli=onsaClient.Instance("/Users/ralph/4k-topo.owl")
    urls = (
        "/(.*)", "querier"
    )
    app = web.application(urls, globals())
    app.run()
    ocli.stop()
        

    #try:
    #    print ocli.queryToJSON(ocli.query("uva4k"))
    #    gid, cid = ocli.reserve("uva4k", "intopix", "uva4k", "display")
    #except twisted.python.failure.Failure, e:
    #    #print e
    #    pass
    #finally:
    #    ocli.stop()
