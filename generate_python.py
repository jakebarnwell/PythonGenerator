# This file takes care of actually generating the fake python code,
#  given the PCFG and other data has already been calculated.

from dict import prepare_primitives
from util import log 
import postprocess
import generate_rules
import util
import Unparser

import copy
import random
import ast

# Change this to change the number of fake .py files to generate.
# This value should also be overridden when calling
#   python main.py <number>
NUMBER_FILES_TO_GENERATE = 5

heads = {}
pcfg = {}
objects = {}
primitives = {}

def makeNode(className, lvl, context):
	"""
	Given a string className, for example "FuncDef", creates
	and returns a full AST node generated using the PCFG. All 
	fields and children are recursively populated as necessary.
	"""
	log("makeNode({})".format(className),lvl)
	node = copy.copy(objects[className])
	possible_rules = heads[className]
	probabilities = [pcfg[rule] for rule in possible_rules]
	sRule = util.random_draw(possible_rules, probabilities)

	(head, constituent) = util.sRule2tRule(sRule)
	log("rule: {}".format(sRule),lvl)
	if constituent != "<NULL>":
		for attrPair in constituent:
			newContext = context + [(className, attrPair[0])]
			populatedField = populateField(field=attrPair[1], lvl=lvl+1, context=newContext)
			setattr(node, attrPair[0], populatedField)

	return node

def populateField(field, lvl, context):
	"""
	Populates a field entry from the rules dictionary. For example, 
	if a rule says that body=[FuncDef, Expr, ClassDef], then this method
	attempts to populate each of the three elements in the list with 
	a full AST node. This is done recursively as needed.
	"""
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
		populated = make_primitive(field, context)

	log("populatedField = {}".format(populated),lvl)
	return populated

def make_primitive(primitive_className, context):
	"""
	Given the class name of a primitive, as well as the context stack,
	returns a randomly chosen primitive of the correct type following
	the correct restrictions.
	"""
	# Recall primitives dict is of the form:
	#  primitives[pcn]["normal"|"special"]["vals"|"freqs"]
	style = "special" if is_special(primitive_className, context) else "normal"

	vals = primitives[primitive_className][style]["vals"]
	frequencies = primitives[primitive_className][style]["freqs"]

	return util.random_draw(vals, frequencies)

def is_special(className, context):
	"""
	Returns true if this primitive className, given the context, is 
	deemed to be "special," that is, the returned primitive must match
	some set of restrictions outlined in prepare_primitives(.)

	Args:
	 className The class name of the primitive value, e.g. "str" or "long"
	 context The context stack (list of tuples) for this step in the generation process
	"""
	parent = context[-1]
	if len(context) > 1:
		grandpa = context[-2]
	else:
		grandpa = None

	if className in util.INTY:
		return parent == ("ImportFrom", "level")

	if className in util.STRINGY:
		if parent in [("ImportFrom", "module"),("Name", "id"),("FunctionDef", "name"),("Attribute", "attr"),("ClassDef", "name"),("Assign", "targets"),("keyword", "arg")]:
			return True
		elif grandpa and grandpa in [("FunctionDef", "args"),("ImportFrom","names"),("Import","names")]:
			return True

	return False

def main(args):
	global NUMBER_FILES_TO_GENERATE
	if args and len(args) > 0:
		try:
			NUMBER_FILES_TO_GENERATE = int(args[0])
		except:
			raise ValueError("The first argument to main.py must be an integer!")

	util.init()

	global heads
	global pcfg
	global objects
	global primitives

	# Call the main rule-parsing/generation module first to get our pcfg
	#  and other data ready to go
	(heads, pcfg, objects, raw_primitives) = generate_rules.process_all();
	
	# Prepare primitives dictionaries by doing some pre-processing on them
	#  so that future stuff is accessible much quicker:
	primitives = prepare_primitives(raw_primitives)

	print "\nStarting generation process. Don't be alarmed if it takes awhile."
	numGenerated = 0
	while True:
		try:
			print "Attempting to generate artificial Python file {}/{}".format(numGenerated+1, NUMBER_FILES_TO_GENERATE)
			tree = makeNode("Module", 0, [])
			outcode = "generated/code{}.py".format(numGenerated+1)
			outast = "generated/AST{}.txt".format(numGenerated+1)
			with open(outcode, "w") as out:
				Unparser.Unparser(tree, out)
			with open(outcode, "r") as in_f:
				text = in_f.read()
			with open(outcode, 'w') as out:
				out.write(postprocess.postprocess(text))
			with open(outast, "w") as out:
				out.write(ast.dump(tree))
			print "Successfully created {} and {}".format(outcode, outast)
			numGenerated += 1
			if numGenerated >= NUMBER_FILES_TO_GENERATE:
				break
		except Exception as e:
			pass # The Fifth Amendment allows me to do this. Shhh...
