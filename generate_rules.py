from nltk import CFG

import sys
import ast
import Unparser
import json
import os

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

def process_all():
	FILESDIR = "data/python_files"
	n = 0
	with open("errors.log", "w") as errorsfile:
		for file_tuple in os.walk(FILESDIR):
			n += 1
			print "Processing file {}".format(n)
			try:
				filename = "{}/{}".format(file_tuple[0],file_tuple[2][0])
				with open(filename, "r") as pyfile:
					source = pyfile.read()
				tree = ast.parse(source)
				process(tree)
			except Exception as e:
				errorsfile.write(str(e) + "\n");
	return (all_heads, all_rules, all_objects)

def main(args):
	if len(args) > 0 and args[0] == "all":
		process_all()
	else:
		with open(PARSE_FILENAME, "r") as srcfile:
			source = srcfile.read()

		tree = ast.parse(source)
		process(tree)
			
	with open("all-rules.txt", "w") as outrules:
		outrules.write(json.dumps(all_rules))

	with open("all-heads.txt", "w") as heads:
		heads.write(json.dumps(all_heads))

	# outfilename = "{}{}".format(filename, OUTPUT_FILENAME_STEM)
	# with open(outfilename, "w") as outfile:
		# Unparser.Unparser(tree, outfile)
		# pass

if __name__=='__main__':
	main(sys.argv[1:])