import sys
import copy
import random
import ast
import Unparser
import json
import util
from util import log 
import re

import generate_rules

MODULE = "Module"

heads = {}
pcfg = {}
objects = {}
primitives = {}

def main(args):
	util.init()

	global heads
	global pcfg
	global objects
	global primitives

	# Be sure to copy the object every time you make a new one
	#  using copy.copy(object)
	(heads, pcfg, objects, primitives) = generate_rules.process_all();

	tree = makeNode(MODULE, 0, [])

	with open("generated_AST.py", "w") as out:
		out.write(ast.dump(tree))

	with open("primitive-fields.txt", "w") as out:
		out.write(json.dumps(all_primitive_fields))

	with open("generated_code.py", "w") as out:
		Unparser.Unparser(tree, out)


def sRule2tRule(sRule):
	"""
	Transforms a string rule, e.g.
	 "Module -> [('body', ['Import', 'ImportFrom', 'ImportFrom', 'ClassDef'])]"
	into a tuple of the form, e.g.,
	 ("Module", [('body', ['Import', 'ImportFrom', 'ImportFrom', 'ClassDef'])])
	i.e. a tuple of the form (String, List) or, in rare cases, (String, "<NULL>")
	"""
	(sRule_head, sRule_constituent) = map(lambda s: s.strip(), sRule.split("->"))
	
	# The standard case where sRule_constituent is like "[...]", a list of stuff
	try:
		rule_constituent = eval(sRule_constituent)
	except: # Catches the case where sRule_constituent is "<NULL>"
		rule_constituent = sRule_constituent

	return (sRule_head, rule_constituent)

def makeNode(className, lvl, context):
	log("makeNode({})".format(className),lvl)
	node = copy.copy(objects[className])
	possible_rules = heads[className]
	probabilities = [pcfg[rule] for rule in possible_rules]
	sRule = util.random_draw(possible_rules, probabilities)

	(head, constituent) = sRule2tRule(sRule)
	log("rule: {}".format(sRule),lvl)
	if constituent != "<NULL>":
		for attrPair in constituent:
			newContext = context + [(className, attrPair[0])]
			populatedField = populateField(field=attrPair[1], lvl=lvl+1, context=newContext)
			setattr(node, attrPair[0], populatedField)

	return node


all_primitive_fields = {}
def populateField(field, lvl, context):
	log("populateField({})".format(field),lvl)
	log("context: {}".format(context),lvl)

	# Handles the case where field is a list of things, like Module(body=[...])
	if isinstance(field, list):
		populated = [populateField(thing,lvl+1,context) for thing in field]

	# Handles the case of a single Node, like Expr(...) or FuncDef(...)
	elif field in objects:
		populated = makeNode(field, lvl+1, context)

	# Handles the case of a field "NoneType" which means the value is None:
	elif field == "NoneType":
		populated = None

	# Handles the case of a primitive field, like 'str' or 'float' or 'int':
	else:
		if field not in all_primitive_fields:
			all_primitive_fields[field] = 1
		else:
			all_primitive_fields[field] += 1
		populated = make_primitive(field, context)

	log("populatedField = {}".format(populated),lvl)
	return populated

# This function as well as special_filter(.) can be greatly sped up
#  by doing any number of caching or pre-processing, but the wait isn't
#  too bad for the size of files we're creating and I was too lazy to
#  figure out a pythonic way to speed it up.
def make_primitive(primitive_className, context):
	"""
	Given the class name of a primitive, as well as the context stack,
	returns a randomly chosen primitive of the correct type following
	the correct restrictions.
	"""
	frequencies_dict = primitives[primitive_className]
	vals = []
	frequencies = []
	for val in frequencies_dict:
		if special_filter(val, primitive_className, context):
			vals.append(val)
			frequencies.append(frequencies_dict[val])

	return util.random_draw(vals, frequencies)

def special_filter(val, className, context):
	"""
	Returns true if this value 'val' passes certain special filters
	defined in this function. These predefined filters have been empirically
	set to return 'better' options for randomly-generated python code.

	Args:
	 val The proposed primitive value, e.g. 128 or "foo"
	 className The class name of the primitive value, e.g. "str" or "long"
	 context The context stack (list of tuples) for this step in the generation process
	"""
	parent = context[-1]
	if len(context) > 1:
		grandpa = context[-2]
	else:
		grandpa = None

	nameRE = r"^[a-zA-Z_]+\w+$"

	stringy = ["str", "unicode"]
	inty = ["int", "long"]
	if className in stringy:
		pass

	if className in inty:
		if parent == ("ImportFrom", "level"):
			return val >= 0 and val <= 1

	if className in stringy:
		# Just get rid of string representations of True and False, because
		#  they are rarely good news. Unfortunately, this means that we will
		#  basically never see True or False in the generated code, but thankfully
		#  most code files don't have those anyway so they won't be missed too much.
		if val in ["True", "False"]:
			return False

		# Make sure import module names are proper
		if parent == ("ImportFrom", "module"):
			return re.search(nameRE, val) != None
		if grandpa and grandpa[1] == "names" and grandpa[0] in ["ImportFrom","Import"]:
			return re.search(nameRE, val) != None

		# Ensure variable names are proper:
		if parent == ("Name", "id"):
			return re.search(nameRE, val) != None

		# Ensure function names are proper
		if parent == ("FunctionDef", "name"):
			return re.search(nameRE, val) != None

		# Ensure attribute names (like object.attribute) are proper
		if parent == ("Attribute", "attr"):
			return re.search(nameRE, val) != None

		# Protect against bad class names:
		if parent == ("ClassDef", "name"):
			return re.search(nameRE, val) != None

		# Protect against stupid assignments like:  foo bar cat = ... 
		if parent == ("Assign", "targets"):
			return re.search(nameRE, val) != None

		# Protect against pad arguments to a function, like func(this is a bad arg):
		if parent == ("keyword", "arg"):
			return re.search(nameRE, val) != None

	return True

if __name__=='__main__':
	main(sys.argv[1:])