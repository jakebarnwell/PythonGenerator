import sys
import copy
import random
import ast
import Unparser
import json

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

	# tree = build_tree(heads, pcfg, objects)
	tree = makeNode(MODULE, 0)

	with open("generated_AST.py", "w") as out:
		out.write(ast.dump(tree))

	with open("primitive-fields.txt", "w") as out:
		out.write(json.dumps(all_field_types))

	with open("generated_code.py", "w") as out:
		Unparser.Unparser(tree, out)

def random_draw(eles, probs):
	assert len(eles) == len(probs)
	sumProbs = sum(probs)
	assert sumProbs > 0
	probs = map(lambda p: p / sumProbs, probs)
	# CDF = reduce()

	r = random.random()
	cumsum = 0
	for i in range(len(eles)):
		cumsum += probs[i]
		if r <= cumsum:
			return eles[i]
			

def build_tree(heads, pcfg, objects):
	# def do_build_tree(node):
	# 	possible_rules = heads[node.__class__.__name__]
	# 	probabilities = [pcfg[rule] for rule in possible_rules]
	# 	rule = random_draw(possible_rules, probabilities)
	# 	node = populateNode(node, rule)
	# 	print node
	# 	print ast.dump(node)
	# 	children = [populateNode(child) for child in ast.iter_child_nodes(node)]

	# startNode = copy.copy(objects[TREE_SEED])
	# return do_build_tree(startNode)

	return makeNode(MODULE, 0)

# def populateNode(node, rule):
# 	(sRule_head, sRule_constituent) = map(lambda s: s.strip(), rule.split("->"))
# 	rule_constituent = eval(sRule_constituent)

# 	for attrPair in rule_constituent:
# 		setattr(node, attrPair[0], attrPair[1])
# 	return node

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
	sRule = random_draw(possible_rules, probabilities)

	(head, constituent) = sRule2tRule(sRule)
	log("rule: {}".format(sRule),lvl)
	if constituent != "<NULL>":
		for attrPair in constituent:
			populatedField = populateField(field=attrPair[1], lvl=lvl+1)
			setattr(node, attrPair[0], populatedField)

	return node

def log(msg, lvl):
	with open("debug.log", "a") as debug:
		debug.write("  "*lvl + msg + "\n")

all_field_types = {}
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
		populated = populateFieldNode()

	# Handles the case of a field "NoneType" which means the value is None:
	elif field == "NoneType":
		populated = None

	# Handles the case of a primitive field, like 'str' or 'float' or 'int':
	else:
		if field not in all_field_types:
			all_field_types[field] = 1
		else:
			all_field_types[field] += 1
		populated = populateFieldPrimitive()

	log("populatedField = {}".format(populated),lvl)
	return populated

def make_primitive(primitive_className):
	p = {"int": 3, "float": 77.7, "bool": True, "unicode": u"66", "str": "foobar"}
	return p[primitive_className]

if __name__=='__main__':
	main(sys.argv[1:])