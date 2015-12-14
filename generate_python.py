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

def main(args):
	global heads
	global pcfg
	global objects

	# Be sure to copy the object every time you make a new one
	#  using copy.copy(object)
	(heads, pcfg, objects) = generate_rules.process_all();

	# rules = heads[heads.keys()[0]]
	# total = 0
	# for r in rules:
	# 	print pcfg[r]
	# 	total += pcfg[r]
	# print "total sum is: " + str(total)

	tree = makeNode(MODULE, 0)

	with open("generated_AST.py", "w") as out:
		out.write(ast.dump(tree))

	with open("primitive-fields.txt", "w") as out:
		out.write(json.dumps(all_primitive_fields))

	with open("generated_code.py", "w") as out:
		Unparser.Unparser(tree, out)

# Transforms a string rule, e.g.
#  "Module -> [('body', ['Import', 'ImportFrom', 'ImportFrom', 'ClassDef'])]"
# into a tuple of the form, e.g.,
#  ("Module", [('body', ['Import', 'ImportFrom', 'ImportFrom', 'ClassDef'])])
# i.e. a tuple of the form (String, List) or, in rare cases, (String, "<NULL>")
def sRule2tRule(sRule):
	(sRule_head, sRule_constituent) = map(lambda s: s.strip(), sRule.split("->"))
	
	# The standard case where sRule_constituent is like "[...]", a list of stuff
	try:
		rule_constituent = eval(sRule_constituent)
	except: # Catches the case where sRule_constituent is "<NULL>"
		rule_constituent = sRule_constituent

	return (sRule_head, rule_constituent)

def makeNode(className, lvl):
	log("makeNode({})".format(className),lvl)
	node = copy.copy(objects[className])
	possible_rules = heads[className]
	probabilities = [pcfg[rule] for rule in possible_rules]
	sRule = util.random_draw(possible_rules, probabilities)

	(head, constituent) = sRule2tRule(sRule)
	log("rule: {}".format(sRule),lvl)
	if constituent != "<NULL>":
		for attrPair in constituent:
			populatedField = populateField(field=attrPair[1], lvl=lvl+1)
			setattr(node, attrPair[0], populatedField)

	return node


all_primitive_fields = {}
def populateField(field, lvl):
	log("populateField({})".format(field),lvl)
	def populateFieldNode():
		return makeNode(field, lvl+1)
	def populateFieldPrimitive():
		return make_primitive(field)

	# Handles the case where field is a list of things, like Module(body=[...])
	if isinstance(field, list):
		populated = [populateField(thing,lvl+1) for thing in field]

	# Handles the case of a single Node, like Expr(...) or FuncDef(...)
	elif field in objects:
		populated = makeNode(field, lvl+1)

	# Handles the case of a field "NoneType" which means the value is None:
	elif field == "NoneType":
		populated = None

	# Handles the case of a primitive field, like 'str' or 'float' or 'int':
	else:
		if field not in all_primitive_fields:
			all_primitive_fields[field] = 1
		else:
			all_primitive_fields[field] += 1
		populated = make_primitive(field)

	log("populatedField = {}".format(populated),lvl)
	return populated

def make_primitive(primitive_className):
	p = {"int": 3, "float": 77.7, "bool": True, "unicode": u"66", "str": "foobar", "long": 14L, "complex": 8+9j}
	return p[primitive_className]

if __name__=='__main__':
	main(sys.argv[1:])