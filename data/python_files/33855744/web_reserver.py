#import web
import tornado.web
import tornado.ioloop
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
import logging
import json
import twisted.python.failure
from onsa_jeroen import createClient, getNSA
import signal
import sys

render_xml = lambda result: "<result>%s</result>"%result
render_json = lambda **result: json.dumps(result,sort_keys=True,indent=4)
render_html = lambda result: "<html><body>%s</body></html>"%result
render_txt = lambda result: result

@Singleton
class onsaClient():
    def __init__(self, topology):
        print topology
        self.topo = opennsa.topology.gole.parseTopology([open(topology)])
        self.client,self.client_nsa = createClient()
        self.result=None
        self.error=None
        self.requests={}

    def request(func):
        result=None
        def sync_func(*args, **kwargs):
            rid=str(uuid.uuid1())
            args[0].requests[rid]=None
            def _err(e):
                print e
                args[0].requests[rid]=e
            kwargs['rid']=rid
            d=defer.maybeDeferred(func, *args, **kwargs)
            d.addErrback(_err)
            return rid
        return sync_func


    @request
    @defer.inlineCallbacks
    def query (self, nsa, cid=None, gid=None, rid=None):
        nsa = getNSA(nsa)
        if cid and gid:
            print "cid and gid isn't good defaulting to cid"
        if cid:
            qr = yield self.client.query(self.client_nsa, nsa, None, "Summary", connection_ids = [ cid ] )
        elif gid:
            qr = yield self.client.query(self.client_nsa, nsa, None, "Details", connection_ids = [] )
            #qr = yield self.client.query(self.client_nsa, nsa, None, "Details", global_reservation_ids = [ gid ] )
        else:
            qr = yield self.client.query(self.client_nsa, nsa, None, "Summary", connection_ids = [] )
        print qr
        self.requests[rid]=self._queryToList(qr)

    @request
    @defer.inlineCallbacks
    def reserve(self, srcNet, srcSTP, dstNet, dstSTP, start_time=None, length=None, gid=None, nsa=None, rid=None):
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
            start_time = datetime.datetime.utcfromtimestamp(time.time() + 10 )
        if length:
            end_time   = start_time + datetime.timedelta(minutes=length)
        else:
            end_time   = start_time + datetime.timedelta(minutes=999999)
        if gid:
            global_reservation_id = gid
        else:
            global_reservation_id = 'opennsa-cli:gid-%s' % random.randrange(1000,10000)
        connection_id = "urn:uuid:%s" % uuid.uuid1()
        bwp = opennsa.nsa.BandwidthParameters(20000)
        service_params  = opennsa.nsa.ServiceParameters(start_time, end_time, srcSTP, dstSTP, bandwidth=bwp)
        # Send the reservation and wait for response
        r = yield self.client.reserve(self.client_nsa, provider_nsa, None, global_reservation_id, description, connection_id, service_params)
        print type(r)
        print r
        print "Reservation created.\nReservation ID: %s\nConnection ID: %s" % (global_reservation_id,connection_id)
        self.requests[rid]={ 'global_reservation_id' : global_reservation_id, 'connection_id' :  connection_id}

    def getresponse(self, rid):
        if rid in self.requests.keys():
            print type(self.requests[rid])
            if isinstance(self.requests[rid], TypeError):
                raise self.requests[rid]
            else:
                return self.requests[rid]
        else:
            return None

    @request
    @defer.inlineCallbacks
    def terminate(self,nsa, cid, rid=None):
        if not "http" in nsa:
            nsa = getNSA(nsa)
        print "Terminating %s at %s" % (cid, nsa)
        qr = yield self.client.terminate(self.client_nsa, nsa, None , connection_id =  cid )
        self.requests[rid]=qr

    @request
    @defer.inlineCallbacks
    def provision(self,nsa, cid, rid=None):
        if not "http" in nsa:
            nsa = getNSA(nsa)
        print "Provisioning %s at %s" % (cid, nsa)
        qr = yield self.client.provision(self.client_nsa, nsa, None , connection_id =  cid )
        self.requests[rid]=qr

    def _queryToList(self, qr):
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
                        store = {}
                        for stp in res.path.stpList.stp:
                            store[stp._order] = stp.stpId
                        keys = store.keys()
                        keys.sort()
                        result = []
                        for k in keys:
                            stp = store[k]
                            result.append(stp)
                        resdict['stpList'] = result
                    else:
                       resdict["stpList"] = [res.path.sourceSTP.stpId,res.path.destSTP.stpId]
                reslist.append(resdict)
            return reslist
        return None


class Querier (tornado.web.RequestHandler):
    def initialize(self, topology):
        self.topology = topology

    def get(self,name):
        self.set_header("Content-Type", "application/json")
        callback=self.get_argument("callback", default=None)
        result=""
        try:
            ocli=onsaClient.Instance(self.topology)
            if name == "terminate":
                nsa=self.get_argument("nsa")
                cid=self.get_argument("cid", default="")
                result={'request_id' : str(ocli.terminate(nsa,cid))}
            elif name == "provision":
                nsa=self.get_argument("nsa")
                cid=self.get_argument("cid", default="")
                result={'request_id' : str(ocli.provision(nsa,cid))}
            elif name == "query":
                nsa=self.get_argument("nsa")
                gid=self.get_argument("gid", default="")
                result={'request_id' : str(ocli.query(nsa, gid=gid))}
            elif name == "result":
                rid=self.get_argument("rid")
                result=ocli.getresponse(rid)
                if result=="":
                    return self._respond("request_id unknown", callback=callback, success=False, status=404)
            elif name == "reserve":
                fromNSA=self.get_argument("fromNSA")
                fromSTP=self.get_argument("fromSTP")
                toNSA=self.get_argument("toNSA")
                toSTP=self.get_argument("toSTP")
                print "Reserving (%s, %s) to (%s, %s)"  % (fromNSA,fromSTP,toNSA ,toSTP)
                result={'request_id' : str(ocli.reserve(fromNSA, fromSTP, toNSA, toSTP))}
            else:
                return self._respond(result, callback=callback, success=False, status=404)
            return self._respond(result, callback=callback, success=True)
        except twisted.python.failure.Failure, e:
            return self._respond(e, success=False)

    def _respond(self, data, callback=None, success=False, status=400):
        if success:
            if status==400:
                status=200
            result={"success": True, "result" : data}
        else:
            result={"success": False, "message" : str(data)}
            result=json.dumps(result, indent=4)
        self.set_status(status)
        if callback:
            self.write(callback + '(' + result + ');')
        else:
            self.write(result)

if __name__ == "__main__":
    topo="/home/ralph/pwl-topo.owl"
    topo="/home/ralph/src/nordunet/opennsa/test-topology.owl"
    ocli=onsaClient.Instance(topo)
    app = tornado.web.Application([
        (r"/(.*)", Querier, {'topology':topo}),
    ])
    app.listen(8080)
    io=tornado.ioloop.IOLoop.instance()
    reactor.startRunning(installSignalHandlers=0)
    tornado.ioloop.PeriodicCallback(reactor.iterate,10).start()
    io.start()
    io.stop()
    reactor.stop()
