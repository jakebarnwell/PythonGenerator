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
# Maps each of the seven primitive class names to a list of
#  *all* (not just unique) occurrences of that primitive
all_primitives = {}

def process(node):	
	"""
	Processes an AST node
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
				errorsfile.write("Error near {}: ".format(file_tuple[0]))
				errorsfile.write(str(e) + "\n");

	pcfg = util.rules2pcfg(all_rules, all_heads)

	util.write_dict(pcfg, "pcfg.txt")
	util.write_dict(all_fields, "all-fields.txt")
	util.write_dict(all_rules, "all-rules.txt")
	util.write_dict(all_heads, "all-heads.txt")
	util.write_dict(all_primitives, "all-primitives.txt")

	return (all_heads, pcfg, all_objects, all_primitives)

def update_primitives(fields):
	"""
	Given fields, a list of field-tuples like [('id', 'segment'), ...]
	stores the usage of any primitive ones so we can re-use them
	in code generation.
	"""
	primitives = ["str","unicode","bool","int","long","float","complex"]
	def do_update_primitive(className, val):
		# if className == "str":
		# 	pass
		# if className == "unicode":
		# 	pass
		# if className == "bool":
		# 	pass
		# if className == "int":
		# 	pass
		# if className == "long":
		# 	pass
		# if className == "float":
		# 	pass
		# if className == "complex":
		# 	pass
		if className in all_primitives:
			_primitives = all_primitives[className]
			_primitives.append(val)
			all_primitives[className] = _primitives
		else:
			all_primitives[className] = [val]

	for f in fields:
		className = util.fieldValue2className(f[1])
		if className in primitives:
			do_update_primitive(className, f[1])

def update_rules(rule):
	"""
	Given a new string-version rule, adds it to the
	frequency dictionary or increments the count
	"""
	if rule in all_rules:
		all_rules[rule] += 1
	else:
		all_rules[rule] = 1

def update_objects(head, node):
	"""
	Given a head, adds an AST node to the dictionary unless
	such an entry for head already exists
	"""
	if head not in all_objects:
		all_objects[head] = node

def update_heads(head, rule):
	"""
	Given a head and a rule, adds the rule to the list of entries
	under this head, or creates a new entry for head if it doesn't
	exist and initializes the entry to the singleton list with that
	rule for this entry
	"""
	if head in all_heads:
		current = all_heads[head]
		if rule in current:
			pass
		else:
			current.append(rule)
			all_heads[head] = current
	else:
		all_heads[head] = [rule]

def update_fields(head, fields):
	"""
	Updates the listing of fields under this type of head, as
	necessary.
	"""
	if len(fields) > 0:
		if head in all_fields:
			_currentfields = all_fields[head]
			for field in fields:
				if field not in _currentfields:
					_currentfields.append(field)
					
			all_fields[head] = _currentfields
		else:
			all_fields[head] = fields

def main(args):
	if len(args) > 0 and args[0] == "all":
		process_all()
	else:
		with open(PARSE_FILENAME, "r") as srcfile:
			source = srcfile.read()

		tree = ast.parse(source)
		process(tree)



	# outfilename = "{}{}".format(filename, OUTPUT_FILENAME_STEM)
	# with open(outfilename, "w") as outfile:
		# Unparser.Unparser(tree, outfile)
		# pass

if __name__=='__main__':
	main(sys.argv[1:])