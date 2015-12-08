from nltk import CFG

import sys
import ast
import Unparser
import json
import os
import load
import copy

PARSE_FILENAME = "Unparser.py"
OUTPUT_FILENAME_STEM = ".out.py"

rules = []
all_rules = {}
all_heads = {}
all_fields = {}
all_objects = {}

def process(tree):
	me = tree.__class__.__name__
	
	record_fields(tree)
	

	children = [c for c in ast.iter_child_nodes(tree)]
	childNames = [child.__class__.__name__ for child in children]
	childrenString = " ".join(childNames)

	# if len(children) > 0 or len(tree._fields) > 0:
	# 	cs = childrenString if len(children) > 0 else "X"
	# 	fs = [field+"="+str(getattr(tree, field)) for field in tree._fields]
		# print me + str(fs) + " -> " + cs

	# print "\n new tree for " + me + ":"
	# for f in ast.iter_fields(tree):
	# 	print f
	# for c in children:
	# 	print c

	process_rule(tree)

	for child_tree in children:
		# print ast.dump(child_tree)
		# print vars(child_tree)
		# print dir(child_tree)
		# print "attrs: " + str(child_tree._attributes)
		process(child_tree)


def process_rule(tree):
	me = tree.__class__.__name__
	fields = []
	for f in ast.iter_fields(tree):
		fields.append(f)
	if len(fields)  ==  0:
		rhs = "<NULL>"
	else:
		rhs = [(ftuple[0], fieldValue2className(ftuple[1])) for ftuple in fields]
	nextLine = "{} -> {}".format(me, str(rhs))
	rules.append(nextLine)
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
		all_objects[me] = tree

def fieldValue2className(val):
	className = val.__class__.__name__

	listlike = ["tuple","list"]
	if className in listlike:
		if className == "tuple":
			return tuple([rule_classType(e) for e in val])
		elif className == "list":
			return [fieldValue2className(e) for e in val]
	else:
		return className


# tree._attributes: lineno, col_offset
# tree._fields: e.g. lower, upper, step, n, id, ctx, s, etc.

# When doing the rules, couple the fields with the children. For example:
# Slice['lower=<_ast.Num object at 0x7f09e94bced0>', 'upper=None', 'step=None'] -> Num
# The children of Slice are directly linked to the fields (in this case, 'lower')
# In fact, I'm pretty sure the children only exist if the relevent fields are filled in

# I'm going to want rules like this
#  Node -> [field1notNull, field2notNull, ...]
#  Node -> '<NULL>'


# Num(n=1), Str(s='foo'), 

def write_dict(d, filename):
	with open(filename, "w") as outfile:
		outfile.write(json.dumps(d))


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
	print "here"
	return (all_heads, pcfg, all_objects)

def rules2pcfg(rules, heads):
	"""
	Given a dict of all rules and all heads, returns a PCFG for
	the rules.

	Args:
	 heads: dict, mapping from 'head' (e.g. 'FunctionDef') to a list of all
	 		possible (string-versioned) re-write rules for that head, e.g.
	 		FunctionDef -> [('name', 'str'), ('args', 'arguments'), ('body', ['For']), ('decorator_list', [])]
	 		where each tuple is a field-tuple of the form (fieldName, fieldValueClass)
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
	write_dict(pcfg, "pcfg.txt")
	return pcfg


def main(args):
	if len(args) > 0 and args[0] == "all":
		process_all()
	else:
		with open(PARSE_FILENAME, "r") as srcfile:
			source = srcfile.read()

		tree = ast.parse(source)
		process(tree)

	write_dict(all_rules, "all-rules.txt")
	write_dict(all_heads, "all-heads.txt")

	# outfilename = "{}{}".format(filename, OUTPUT_FILENAME_STEM)
	# with open(outfilename, "w") as outfile:
		# Unparser.Unparser(tree, outfile)
		# pass

if __name__=='__main__':
	main(sys.argv[1:])