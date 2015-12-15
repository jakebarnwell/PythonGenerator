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

def prepare(raw_primitives):
	p = {}

	nameRE = r"^[a-zA-Z_]+\w+$"

	for pcn in raw_primitives:
		p[pcn] = {}
		p[pcn]["normal"] = {}
		p[pcn]["special"] = {}

		vals = []
		freqs = []
		for val in raw_primitives[pcn]:
			# Earlier we did complex-->str, now undo that change
			if pcn == "complex":
				val = complex(val)
				freqs.append(raw_primitives[pcn][str(val)])
			else:
				freqs.append(raw_primitives[pcn][val])
			vals.append(val)
		p[pcn]["normal"]["vals"] = vals
		p[pcn]["normal"]["freqs"] = freqs

		if pcn in util.STRINGY:
			filtered_vals = []
			filtered_freqs = []
			for i in range(len(vals)):
				# Just get rid of string representations of True and False, because
				#  they are rarely good news. Unfortunately, this means that we will
				#  basically never see True or False in the generated code, but thankfully
				#  most code files don't have those anyway so they won't be missed too much.
				if re.search(nameRE, vals[i]) != None and vals[i] not in ["True","False"]:
					filtered_vals.append(vals[i])
					filtered_freqs.append(freqs[i])
			p[pcn]["special"]["vals"] = filtered_vals
			p[pcn]["special"]["freqs"] = filtered_freqs
		elif pcn in util.INTY:
			filtered_vals = []
			filtered_freqs = []
			for i in range(len(vals)):
				if vals[i] >= 0 and vals[i] <= 1:
					filtered_vals.append(vals[i])
					filtered_freqs.append(freqs[i])
			p[pcn]["special"]["vals"] = filtered_vals
			p[pcn]["special"]["freqs"] = filtered_freqs
	return p

def func(text):
        text = remove_single_line_string(text)
        text = remove_trailing_commas_unless_its_a_tuple_then_its_ok(text)
        return text

def remove_single_line_string(text):
        lines = text.split('\n')
        rgx1 = re.compile(r"^\s*'[^']*'\s*$")
        rgx2 = re.compile(r'^\s*"[^"]*"\s*$')
        new_lines = []
        for line in lines:
                if re.match(rgx1, line) or re.match(rgx2, line):
                        continue
                new_lines.append(line)
        new_text = '\n'.join(new_lines)
        return new_text

def remove_trailing_commas_unless_its_a_tuple_then_its_ok(text):
        lines = text.split('\n')
        rgx = re.compile(r"^(.*),\s*(\):.*)$")
        new_lines = []
        for line in lines:
                m = re.match(rgx, line)
                if m:
                        new_line = m.groups()[0] + m.groups()[1]
                        new_lines.append(new_line)
                else:
                        new_lines.append(line)
        new_text = '\n'.join(new_lines)
        return new_text

def main(args):
	util.init()

	global heads
	global pcfg
	global objects
	global primitives

	# Be sure to copy the object every time you make a new one
	#  using copy.copy(object)
	(heads, pcfg, objects, raw_primitives) = generate_rules.process_all();
	
	# Prepare primitives dictionaries by doing some pre-processing on them
	#  so that future stuff is accessible much quicker:
	primitives = prepare(raw_primitives)
	util.write_dict(primitives, "dicts/all-postprocessed-primitives.dict")

	while True:
		try:
			print "Attempting to generate artificial code..."
			tree = makeNode(MODULE, 0, [])
			print "Success! The generated AST and code are in the generated/ directory."
			break
		except:
			print "..."

	with open("generated/AST.txt", "w") as out:
		out.write(ast.dump(tree))

	with open("generated/code.py", "w") as out:
		Unparser.Unparser(tree, out)

        
	with open("generated/code.py") as in_f:
		text = in_f.read()
	with open("generated/code.py", 'w') as out:
		out.write(func(text))


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
	some set of restrictions outlined in prepare(.)

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
		elif grandpa and grandpa[1] == "names" and grandpa[0] in ["ImportFrom","Import"]:
			return True

	return False

