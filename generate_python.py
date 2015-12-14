import sys
import copy
import random
import ast
import Unparser
import json
import util
from util import log 

import generate_rules

MODULE = "Module"

heads = {}
pcfg = {}
objects = {}
primitives = {}

def main(args):
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

def make_primitive(primitive_className, context):
	# p = {"int": 3, "float": 77.7, "bool": True, "unicode": u"66", "str": "foobar", "long": 14L, "complex": 8+9j}
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
	stringy = ["str", "unicode"]
	inty = ["int", "long"]
	if className in stringy:
		pass

	if className in inty:
		if context[-1] == ("ImportFrom", "level"):
			return val >= 0 and val <= 1

	return True

if __name__=='__main__':
	main(sys.argv[1:])