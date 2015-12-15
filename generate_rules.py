# This module looks through the data/ folder for python files, reads
#  them in, and processes each one to eventually generate a PCFG
#  and other data.

from dict import *
import util

import os
import ast

def process(node):	
	"""
	Processes an AST node.
	"""
	process_rule(node)

	for child_tree in ast.iter_child_nodes(node):
		process(child_tree)

def process_rule(node):
	"""
	Given an AST node, processes the the rule that made it and its
	children, storing the rule so it can be statistically analyzed later.
	Additionally updates dictionary files storing various data that will
	be used later.
	"""
	me = node.__class__.__name__

	# Fetch every field (i.e. Child) of this node
	fields = []
	for f in ast.iter_fields(node):
		fields.append(f)

	# Store each field as a tuple (key, valueClassName), and write to string the
	#  re-write rule in the form of "NodeClass -> [(key, valueClassName), ...] in
	#  a dict for later use.
	if len(fields) ==  0:
		rhs = "<NULL>"
	else:
		rhs = [(ftuple[0], util.fieldValue2className(ftuple[1])) for ftuple in fields]
	nextLine = "{} -> {}".format(me, str(rhs))

	# Store's relevant data from this node for later use
	update_rules(nextLine)
	update_objects(me, node)
	update_heads(me, nextLine)
	update_fields(me, node._fields)
	update_primitives(fields)

def process_all():
	"""
	Processes all data in the data/ folder.
	"""
	FILESDIR = "data/python_files"
	n = 0
	with open("logs/parse_files.log", "w") as errorsfile:
		for file_tuple in os.walk(FILESDIR):
			n += 1
			print "Processing file {}".format(n)
			try:
				filename = "{}/{}".format(file_tuple[0],file_tuple[2][0])
				with open(filename, "r") as pyfile:
					source = pyfile.read()
				tree = ast.parse(source)
				process(tree)
			except Exception as e:
				errorsfile.write("Error near {}: ".format(file_tuple[0]))
				errorsfile.write(str(e) + "\n");

	pcfg = util.rules2pcfg(all_rules, all_heads)

	write_dict(pcfg, "dicts/pcfg.dict")
	write_dict(all_fields, "dicts/all-fields.dict")
	write_dict(all_rules, "dicts/all-rules.dict")
	write_dict(all_heads, "dicts/all-heads.dict")

	# Do naive smoothing on primitives. This is more than sufficient to
	#  add a bit of variety into the dictionary. Conservation of frequency
	#  doesn't matter since it's all normalized later.
	for pcn in all_primitives:
		primSum = 0
		for key in all_primitives[pcn]:
			primSum += all_primitives[pcn][key]
		numEles = len(all_primitives[pcn].keys())
		mean = primSum * 1.0 / numEles
		
		for key in all_primitives[pcn]:
			freq = all_primitives[pcn][key]
			if freq > mean:
				all_primitives[pcn][key] = freq - ((freq-mean)/10)
			else:
				all_primitives[pcn][key] = freq + (1 + (mean-freq)/10)

	return (all_heads, pcfg, all_objects, all_primitives)
