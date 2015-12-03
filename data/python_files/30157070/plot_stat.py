import os
import sys
import time
import syck

import numpy.numarray as na
from pylab import *
from matplotlib.backends.backend_agg import FigureCanvasAgg

import paths
import colors
import math

font = {
        'fontsize'   : 21,
	"color"	: "black",
}

def readData(files):
    global inputData
    global dataOrder
    def _getVal(name):
    	_v = name.rsplit("_", 1)[1]
	_v = _v.rsplit(".", 2)[0]
	return float(_v)
    _inputData = dict((_getVal(_f), syck.load(file(_f)))
    	for _f in _dataFiles
    )
    # return inputData, dataOrder
    return (_inputData, sorted(_inputData.keys()))

def needToUpdate(fname, minTime):
    _rv = True
    if os.path.isfile(fname):
	# if output file exists and is younger than input, do nothing
	_outS = os.stat(fname)
	_outTime = min(_outS.st_mtime, _outS.st_ctime)
	if minTime < _outTime:
	    _rv = False
    return _rv

def saveFig(fig, outFile):
	_canvas = FigureCanvasAgg(fig)
	_canvas.print_figure(outFile, dpi=80)

def getFig():
	_fig = Figure(figsize=(8,8))
	_ax = _fig.add_subplot(111)
	return (_fig, _ax)

def translate(paramName):
	return {
		"maxAntCount": ("pheromone", "ant count"),
		"evaporation": ("pheromone", "evaporation coificent"),
		"pheromoneInfluence": ("pheromone", "pheromone influence coificent"),
		"desirabilityInfluence": ("pheromone", "desirability influence coificent"),
		"sol_qual": ("Solution quality", "Node count"),
		"sol_time": ("Solution time prior best solution finding (seconds)", "Node count"),
		"sol_found": ("Solutions found prior best", "Node count"),
	}[paramName]

def drawWithError(pl, time, data, err, title, color):
	pl.plot(time, data, ".-", label=title.title(), color=color)
	if not err:
		return
	_errD = dict(zip(time, err))
	_data = dict(zip(time, data))
	_step = (time[1] - time[0]) / 5.0
	for _time in time:
		_disp = _errD[_time]
		_val = _data[_time]
		_x = _time - _step, _time + _step
		_y = _val - _disp, _val + _disp
		_x = list(_x) + list(reversed(_x))
		_y = list((_y[0], _y[0], _y[1], _y[1]))
		pl.fill(_x, _y, facecolor=color, alpha=0.2, edgecolor='r')

def drawPlot(name, files, minTime, outMask, func, type, appendType=True):
	if appendType:
		_elems = (outMask, type, "multi_error.png")
	else:
		_elems = (outMask, "multi_error.png")
	_outFile = "_".join(_elems)
	if not needToUpdate(_outFile, minTime):
		return
	(_data, _time) = readData(files)
	(_fig, _ax) = getFig()
	##########
	func(name, _ax, _data, _time)
	##########
	_ax.legend(shadow=True, loc=0)
	_ax.set_ylabel((translate(type)[0]).lower(), font)
	_ax.set_xlabel((translate(type)[1]).lower(), font)
	saveFig(_fig, _outFile)

def plotCoef(name, ax, inputData, time):
	_items = [inputData[_i]["minPathStat"][-1] for _i in time]
	for (_key, _name, _color) in (
		("worldAmount", "World", colors.color1),
		("curBestPheromone", "Best", colors.color2)
	):
		_data = [_i[_key + "_average"] for _i in _items]
		_err = [_i[_key + "_error"] for _i in _items]
		_time = time
		if name in ("evaporation", ): # values whith evaporation == 0 are too high (screws the graph)
			_data = _data[1:]
			_err = _err[1:]
			_time = _time[1:]
		drawWithError(ax, _time, _data, _err, _name, _color)

def plotSolQual(name, ax, inputData, time):
	drawWithError(ax, time, [
		_o["topDicts"]["quality_average"] for _o in inputData.itervalues()
	], [
		_o["topDicts"]["quality_error"] for _o in inputData.itervalues()
	], "Quality", colors.color1)

def plotSolTime(name, ax, input, time):
	_dataArr = [input[_t]["stepStat"] for _t in time]
	_data = []
	_err = []
	for _val in _dataArr:
		_data.append(_val["runTime_average"])
		_err.append(_val["runTime_error"])
	drawWithError(ax, time, _data, _err, "time", colors.color1)

def plotSolFound(name, ax, input, time):
	_dataArr = [input[_t]["stepStat"] for _t in time]
	_data = []
	_err = []
	for _val in _dataArr:
		_data.append(_val["solutionsFound_average"])
		_err.append(_val["solutionsFound_error"])
	drawWithError(ax, time, _data, _err, "Solutions", colors.color1)

if __name__ == "__main__":
    _name = sys.argv[1]
    _inDir = os.path.join(paths.dataDir, "stat", _name)
    if not os.path.isdir(_inDir):
    	print "Dir '%s' not found" % _inDir
	exit(1)
    _outDir = os.path.join(paths.imgDir, "plots")
    _dataFiles = [
    	os.path.join(_inDir, _f) 
    	for _f in os.listdir(_inDir)
	if os.path.splitext(_f)[1] == ".yaml"
    ]
    _minTime = min(os.stat(_f).st_mtime for _f in _dataFiles)
    if "graphs" in _name:
    	_origName = _name
	_fname = _origName.replace(".", "_")
	drawPlot(_name, _dataFiles, _minTime, os.path.join(_outDir, _fname), plotSolQual, "sol_qual")
	drawPlot(_name, _dataFiles, _minTime, os.path.join(_outDir, _fname), plotSolTime, "sol_time")
	drawPlot(_name, _dataFiles, _minTime, os.path.join(_outDir, _fname), plotSolFound, "sol_found")
    else:
	_fname = _name.replace(".", "_")
	drawPlot(_name, _dataFiles, _minTime, os.path.join(_outDir, _fname), plotCoef, _name, False)

# vim: set et sts=4 sw=4 :
