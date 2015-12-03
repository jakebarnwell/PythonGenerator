import threading
import sys
import yaml
import os
import networkx as NX
import time
import copy

from cStringIO import StringIO

import genTemplate

class WorkerThread(threading.Thread):

    data = runCount = minPath = outMask = iterCount = antAlg = None
    _runStr = r'python "%(pyFile)s" "%(dataFile)s" "%(iterCount)i" "%(minPath)i" "%(outFname)s" "%(antAlg)s"'

    def __init__(self, data, minPath, runCount, outMask, iterCount, antAlg):
        super(WorkerThread, self).__init__()
        self.setDaemon(True)
	self.data = data
	self.runCount = runCount
	self.minPath = minPath
	self.outMask = outMask
	self.iterCount = iterCount
	self.antAlg = antAlg

    def run(self):
    	_iter = 0
	_curDir = os.path.split(os.path.realpath(__file__))[0]
	_trgFile = os.path.join(_curDir, "run_single.py")
	_tmpFile = os.path.join(_curDir, "tmp", ".".join(("data", self.outMask % 42, "yaml")))
	_f = file(_tmpFile, "w")
	yaml.dump(self.data, _f)
	_f.close()
	while _iter < self.runCount:
		_outFname = self.outMask % _iter
		_exStr = self._runStr % {
			"pyFile": _trgFile,
			"dataFile": _tmpFile,
			"iterCount": self.iterCount,
			"minPath": self.minPath,
			"outFname": _outFname,
			"antAlg": self.antAlg,
		}
		os.system(_exStr)
	    	_iter += 1
	os.unlink(_tmpFile)

outDir = os.path.split(os.path.realpath(__file__))[0]
outDir = os.path.join(outDir, "out")

def run(data, prefix, count, iterCount, antAlg="reversePrice"):
	_workerCount = 4
	_g = NX.XGraph()
	for _obj in data["nodes"]:
		_g.add_node(_obj["name"])
	for _obj in data["edges"]:
		(_from , _to) = _obj["nodes"]
		_g.add_edge(_from, _to, _obj["price"])
	_targets = [_o["node"] for _o in data["foods"]]
	_srcs = [_o["node"] for _o in data["lairs"]]
	assert len(_targets) == len(_srcs) == 1
	_minPath = NX.dijkstra_path_length(_g, _targets[0], _srcs[0])
	_workers = []
	for _x in xrange(_workerCount):
	    	_outMask = prefix + ".worker" + str(_x) + ".iter%i"
		_worker = WorkerThread(copy.deepcopy(data), _minPath, count/_workerCount, _outMask, iterCount, antAlg)
		_workers.append(_worker)
	_startTime = time.time()
	[_t.start() for _t in _workers]
	_finished = False
	while not _finished:
		_finished = True
		for _th in _workers:
			if _th.isAlive():
				_finished = False
				_th.join(1)
	[_t.join() for _t in _workers]
	print "Time elapsed: %s" % (time.time() - _startTime)

def hideResults(outDuir, paramName, paramValue):
	_paramDir = os.path.join(outDir, "param_%s_%s" % (paramName, paramValue))
	os.mkdir(_paramDir)
	for _fname in os.listdir(outDir):
		if os.path.splitext(_fname)[1] == ".yaml":
			os.rename(os.path.join(outDir, _fname), os.path.join(_paramDir, _fname))
	

def checkParam(data, prefix, paramName, minParam, maxParam, step):
	_curVal = minParam
	while _curVal < (maxParam+step):
		print "%s=%s" % (paramName, _curVal)
		data[paramName] = _curVal
		run(copy.deepcopy(data), prefix)
		hideResults(outDir, paramName, paramValue)
		_curVal += step

def checkVals(data, prefix, paramName, paramVals):
	for _curVal in paramVals:
		print "%s=%s" % (paramName, _curVal)
		_args = {paramName: _curVal}
		run(copy.deepcopy(data), paramName, 200, 10000, **_args)
		hideResults(outDir, paramName, _curVal)

def doParamCheck(inFname):
	assert os.path.isfile(inFname)
	_data = yaml.load(file(inFname))
	_outFname = os.path.splitext(os.path.split(inFname)[1])[0]
	_outFname = _outFname + ".multi"
	#checkParam(copy.deepcopy(_data), _outFname, "evaporation", 0, 1, 0.05)
	#checkParam(copy.deepcopy(_data), _outFname, "maxAntCount", 1, 100, 4)
	#checkParam(copy.deepcopy(_data), _outFname, "pheromoneInfluence", 0, 3, 0.2)
	#checkParam(copy.deepcopy(_data), _outFname, "desirabilityInfluence", 0, 3, 0.2)
	checkVals(copy.deepcopy(_data), _outFname, "antAlg", ("reverseSolPrice", "reversePrice", "constMul"))

def doGraphCheck(minNodes, maxNodes, step):
	_curNodes = minNodes
	_stepCount = (maxNodes - minNodes*1.0)/step
	_totalGraphs = 20
	while _curNodes < (maxNodes + step):
		print _stepCount
		_prefix = "graph.multi"
		for _grNo in xrange(_totalGraphs):
			_prefix_internal = _prefix + ".graph_%i" % _grNo
			_data = genTemplate.genGraph(_curNodes, _curNodes*1.5)
			_f = StringIO(_data)
			_f.seek(0,0)
			_data = yaml.load(_f)
			run(copy.deepcopy(_data), _prefix_internal, 16, _curNodes*2)
		hideResults(outDir, "edges", _curNodes)
		print "pass"
		_curNodes += step
		_stepCount -= 1

if __name__ == "__main__":
	_inFname = os.path.realpath(sys.argv[1])
	doParamCheck(_inFname)
	#doGraphCheck(10, 300, 10)

# vim: set et sts=4 sw=4 :
