from nltk import CFG

import sys
import ast
import Unparser
import json
import os
import load
import copy

import util

PARSE_FILENAME = "Unparser.py"
OUTPUT_FILENAME_STEM = ".out.py"

# stores all individual rules with their frequency counts
all_rules = {}
# stores all possible AST nodes mapped to a list containing
#  every possible rule with given AST node (head) as a lhs
all_heads = {}
# stores each AST node (head) mapped to all possible constituent
#  field types
all_fields = {}
# Maps each AST node (head), in className form, to an object
#  (true AST node) of that type. This allows for easy access to
#  such nodes so I can easily generate objects of a given class
#  name on the fly
all_objects = {}

def process(node):	
	record_fields(node)
	process_rule(node)

	for child_tree in ast.iter_child_nodes(node):
		process(child_tree)

# Given an AST node, processes the the rule that made it and its
#  children, storing the rule so it can be statistically analyzed later
def process_rule(node):
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

	# Store's relevant data from this node into all_rules,
	#  all_heads, and all_objects
	if nextLine in all_rules:
		all_rules[nextLine] += 1
	else:
		all_rules[nextLine] = 1
	
	if me in all_heads:
		current = all_heads[me]
		if nextLine in current:
			pass
		else:
			current.append(nextLine)
			all_heads[me] = current
	else:
		all_heads[me] = [nextLine]

	if me not in all_objects:
		all_objects[me] = node



def record_fields(tree):
	me = tree.__class__.__name__
	fields = tree._fields
	if len(fields) > 0:
		if me in all_fields:
			_currentfields = all_fields[me]
			for field in fields:
				_currentfields.add(field)
				all_fields[me] = _currentfields
		else:
			all_fields[me] = set(fields)

DEBUG = True
thresh = 100
def process_all():
	FILESDIR = "data/python_files"
	n = 0
	with open("errors.log", "w") as errorsfile:
		for file_tuple in os.walk(FILESDIR):
			n += 1
			if DEBUG and n > thresh:
				break
			print "Processing file {}".format(n)
			try:
				filename = "{}/{}".format(file_tuple[0],file_tuple[2][0])
				with open(filename, "r") as pyfile:
					source = pyfile.read()
				tree = ast.parse(source)
				process(tree)
			except Exception as e:
				errorsfile.write(str(e) + "\n");

	pcfg = rules2pcfg(all_rules, all_heads)

	return (all_heads, pcfg, all_objects)

def rules2pcfg(rules, heads):
	"""
	Given a dict of all rules and all heads, returns a PCFG for
	the rules.

	Args:
	 heads: dict, mapping from 'head' (e.g. 'FunctionDef') to a list of all
	 		possible (string-versioned) re-write rules for that head, e.g.
	 		FunctionDef -> [('name', 'str'), ('args', 'arguments'), ('body', ['For']), ('decorator_list', [])]
	 		where each tuple is a field-tuple of the form (fieldKeyClassName, fieldValueClassName)
	 rules: dict, mapping from each stringified-rule of the form listed in heads 
	 		to the number of occurrences (invocations) of that rule in the corpora
	"""
	pcfg = copy.copy(rules)

	for head in heads:
		head_rewrite_rules = heads[head]
		head_sum = 0
		for rule in head_rewrite_rules:
			head_sum += rules[rule]
		for rule in head_rewrite_rules:
			pcfg[rule] = rules[rule] * 1.0 / head_sum
	util.write_dict(pcfg, "pcfg.txt")
	return pcfg


def main(args):
	if len(args) > 0 and args[0] == "all":
		process_all()
	else:
		with open(PARSE_FILENAME, "r") as srcfile:
			source = srcfile.read()

		tree = ast.parse(source)
		process(tree)

	util.write_dict(all_rules, "all-rules.txt")
	util.write_dict(all_heads, "all-heads.txt")

	# outfilename = "{}{}".format(filename, OUTPUT_FILENAME_STEM)
	# with open(outfilename, "w") as outfile:
		# Unparser.Unparser(tree, outfile)
		# pass

if __name__=='__main__':
	main(sys.argv[1:])