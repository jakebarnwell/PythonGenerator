import os
import sys
import time
import yaml

import networkx as NX
import pygraphviz

import paths
import colors

def fixName(name):
    if name.startswith("NODE_"):
    	_rv = name[len("NODE_"):]
    else:
    	_rv = name
    return _rv

def drawGraph(data, outFname):
    _graph = pygraphviz.AGraph()
    _foodNodes = [_obj["node"] for _obj in data["foods"]]
    _lairNodes = [_obj["node"] for _obj in data["lairs"]]
    for _node in data["nodes"]:
	if _node["name"] in _foodNodes:
		_color = colors.color2
		_shape = "egg"
	elif _node["name"] in _lairNodes:
		_color = colors.color3
		_shape = "house"
	else:
		_color = colors.color1
		_shape = "ellipse"
        _graph.add_node(fixName(_node["name"]), color=_color, shape=_shape)
    for _edge in data["edges"]:
        (_from, _to) = (fixName(_nm) for _nm in _edge["nodes"])
	(_f1, _f2) = _edge["nodes"]
	_color = [colors.color1]
	_labelItems = []
	if "price" in _edge:
		_labelItems.append("%i" % _edge["price"])
	if "pheromone" in _edge:
		_labelItems.append("%.2f" % _edge["pheromone"])
	_label = r"\n".join(_labelItems)
	if "minPath" not in data:
		data["minPath"] = ()
	if _f1 in data["minPath"] and _f2 in data["minPath"]:
		_color.append(colors.color2)
	_graph.add_edge(_from, _to, color=":".join(_color), label=_label)
    _graph.layout(prog="dot")
    _graph.draw(outFname)
    

if __name__ == "__main__":
    _name = sys.argv[1]
    _inFname = os.path.join(paths.dataDir, _name + ".yaml")
    if not os.path.isfile(_inFname):
    	print "file '%s' not found" % _inFname
	exit(1)
    _outDir = os.path.join(paths.imgDir, "graphs")
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
