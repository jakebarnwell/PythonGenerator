import os
import sys
import time
import yaml

import numpy.numarray as na
from pylab import *
from matplotlib.backends.backend_agg import FigureCanvasAgg

import paths
import colors

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

def drawWithAvg(pl, time, data, legend, color):
	pl.plot(time, data, ",", label=legend, color=color)
	pl.plot(time, getMean(data), label=legend + " average", color=color)
		

def drawGraph(data, outFname):
	_time = []
	_best = []
	_world = []
	_fig = Figure(figsize=(8,8))
	_ax = _fig.add_subplot(111)
	_timeNames = ("iterNo", "worldIterNo_average")
	_bestNames = ("curBest", "curBestPheromone_average")
	_worldNames = ("worldAmount", "worldAmount_average")
	def _getVal(dict, names):
		for _name in names:
			if dict.has_key(_name):
				return dict[_name]
		raise Exception(":(")
	for _hist in data["pheromoneHistory"]:
		_time.append(_getVal(_hist, _timeNames))
		_best.append(_getVal(_hist, _bestNames))
		_world.append(_getVal(_hist, _worldNames))

	drawWithAvg(_ax, _time, _best, "Best", colors.color1)
	drawWithAvg(_ax, _time, _world, "World", colors.color2)

	_ax.legend(shadow = True, loc = 0)

	_ax.set_xlabel('solutions found', font)
	_ax.set_ylabel('pheromone', font)
	_canvas = FigureCanvasAgg(_fig)
    	_canvas.print_figure(outFname, dpi=80)
    

if __name__ == "__main__":
    _name = sys.argv[1]
    _inFname = os.path.join(paths.dataDir, _name+".stat.yaml")
    if not os.path.isfile(_inFname):
    	print "file '%s' not found" % _inFname
	exit(1)
    _outDir = os.path.join(paths.imgDir, "plots")
    _outFile = os.path.join(_outDir, _name + ".png")
    if os.path.isfile(_outFile):
	# if output file exists and is younger than input, do nothing
	_inS = os.stat(_inFname)
	_outS = os.stat(_outFile)
	_inTime = max(_inS.st_mtime, _inS.st_ctime)
	_outTime = min(_outS.st_mtime, _outS.st_ctime)
	if _inTime < _outTime:
	    exit(1)
    _data = yaml.load(file(_inFname))
    drawGraph(_data, _outFile)
 


# vim: set et sts=4 sw=4 :
