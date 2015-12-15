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
	Given a string className, a tree-depth level, and a context
	stack, creates and returns a full AST node generated using
	the PCFG. All fields and children of this AST node are 
	recursively populated as necessary.

	Args:
	 className: string class name of the node that should be
	 			created, e.g. "Module" or "FuncDef"
	 lvl: current depth in the AST. The initial call to this 
	 	  function should have lvl=0. This is mainly used for
	 	  help printing out logs of the tree creation, but can
	 	  certainly be used in the future to do smarter generation
	 	  in a context-sensitive way.
	 context: a list, representing a stack, of ancestors in 
	 		  this AST call-chain. Each element of the stack
	 		  is of the form (className, fieldName), e.g.
	 		  ("FuncDef", "args") meaning that this current 
	 		  node is a child of FuncDef under its "args" field.
	"""
	log("makeNode({})".format(className),lvl)
	# copy object since `objects` just stores representative
	#  object types
	node = copy.copy(objects[className])
	# Get possible rules and draw a random rule from those given
	#  the probabilities of each rule in the PCFG
	possible_rules = heads[className]
	probabilities = [pcfg[rule] for rule in possible_rules]
	sRule = util.random_draw(possible_rules, probabilities)

	(head, constituent) = util.sRule2tRule(sRule)
	log("rule: {}".format(sRule),lvl)
	if constituent != "<NULL>":
		# For each RHS element in the rule, populate the element
		#  appropriately and set the attribute.
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

	Args:
	 field: string className or list of string classNames 
	 		comprising this field. For example, "Expr" or
	 		["Expr", "FuncDef", "Name"]. This className or
	 		list of classNames will be populated with the 
	 		appropriate AST nodes.
	 lvl: current depth in the AST.
	 context: context stack 
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
	certain restrictions if applicable.

	Args:
	 primitive_className: the classname of the primitive. Should be one 
	 					  of the seven class names given in
	 					  util.PRIMITIVE_CLASSNAMES
	 context: context stack
	"""
	# Recall primitives dict is of the form:
	#  primitives[pcn]["normal"|"special"]["vals"|"freqs"]
	style = "special" if is_namelike(primitive_className, context) else "normal"

	# Randomly draw one primitive 
	vals = primitives[primitive_className][style]["vals"]
	frequencies = primitives[primitive_className][style]["freqs"]

	return util.random_draw(vals, frequencies)

# Basically the issue is that some primitives in Python have to be 
# "names" like for variables, arguments, function names, and so on.
# Obviously, there are restrictions on the possible strings that are
# allowed to populate such names: in particular, a name must start
# with an underscore or letter, and can only contain underscores,
# letters, or digits. Note that dots are not allowed because Python
# takes care of those separately.
# The other case this is used is for the ImportFrom statement which
# has a field called 'level' which has to do with the import location
# in a package. This must be an int and can, in theory, be any non-
# negative integer. However, in practice, it's only ever 0 or, very
# occasionally, 1, and I haven't ever seen more than 1 dot.
def is_namelike(className, context):
	"""
	Returns true if this primitive className, given the context, is 
	required to be "namelike" in Python. For string-like primitives,
	this typically means that primitive will be used as the name of
	a function, variable, argument, or something similar, and hence 
	the primitive must be a string with only letters, underscores,
	and numbers, and it can't start with digits.
	This is where the context stack is used extensively.

	Args:
	 className: the class name of the primitive value, e.g. "str" or "long"
	 context: context stack
	"""
	# The 'parent' is the context entity on the top of the
	#  context stack. The grandparent is the second to top.
	parent = context[-1]
	if len(context) > 1:
		grandpa = context[-2]
	else:
		grandpa = None

	# These are the cases where we have to be careful when picking primitives.
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
