import os
import sys
import time
import yaml

import numpy.numarray as na
from pylab import *
from matplotlib.backends.backend_agg import FigureCanvasAgg

font = {
        'fontsize'   : 21,
	"color"	: "black",
}

def getMean(data):
	_out = []
	_pointCount = 20
	_delta = _pointCount / 2
	for _pos in xrange(len(data)):
		_from = _pos - (_delta + 1)
		_to = _pos + _delta
		if _from < 0:
			_from = 0
		if _to > len(data) - 1:
			_to = len(data) - 1
		_items = data[_from:_to]
		_out.append(mean(_items))
	return _out
		

def drawGraph(data, outFname):
	_time = []
	_best = []
	_world = []
	_fig = Figure(figsize=(8,8))
	_ax = _fig.add_subplot(111)
	for _hist in data["pheromoneHistory"]:
		_t = _hist["iterNo"]
		_time.append(_t)
		_best.append(_hist["curBest"])
		_world.append(_hist["worldAmount"])

	_ax.legend((r"best", r"total"), shadow = True, loc = 0)
	dir(_ax)
	ltext = _ax.get_legend().get_texts()
	setp(ltext[0], fontsize = 20, color = 'black')
	setp(ltext[1], fontsize = 20, color = 'gray')

	_ax.plot(_time, _best, "-", color="black")
	_ax.plot(_time, _world, ",", color="gray")
	_ax.plot(_time, getMean(_world), "-", color="gray")

	_ax.set_xlabel('iterations', font)
	_ax.set_ylabel('pheromone', font)
	_canvas = FigureCanvasAgg(_fig)
    	_canvas.print_figure(outFname, dpi=80)
    

if __name__ == "__main__":
    _inFname = sys.argv[1]
    assert os.path.isfile(_inFname)
    _outDir = os.path.split(os.path.realpath(__file__))[0]
    _outDir = os.path.split(_outDir)[0]
    _outDir = os.path.join(_outDir, "report", "img", "plots")
    _fname = os.path.splitext(os.path.split(_inFname)[1])[0]
    (_fname, _ext) = os.path.splitext(_fname)
    assert _ext == ".stat"
    _outFile = os.path.join(_outDir, _fname + ".png")
    if os.path.isfile(_outFile):
	# if output file exists and is younger than input, do nothing
	_inS = os.stat(_inFname)
	_outS = os.stat(_outFile)
	_inTime = max(_inS.st_mtime, _inS.st_ctime)
	_outTime = min(_outS.st_mtime, _outS.st_ctime)
	if _inTime < _outTime and 0:
	    exit(1)
    _data = yaml.load(file(_inFname))
    drawGraph(_data, _outFile)
 


# vim: set et sts=4 sw=4 :
