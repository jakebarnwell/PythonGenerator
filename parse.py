from nltk import CFG

import sys
import ast
import Unparser
import json

PARSE_FILENAME = "Unparser.py"
OUTPUT_FILENAME_STEM = ".out.py"

rules = []
def process(tree):
	me = tree.__class__.__name__
	
	record_fields(tree)
	

	children = [c for c in ast.iter_child_nodes(tree)]
	childNames = [child.__class__.__name__ for child in children]
	childrenString = " ".join(childNames)

	if len(children) > 0 or len(tree._fields) > 0:
		cs = childrenString if len(children) > 0 else "X"
		fs = [field+"="+str(getattr(tree, field)) for field in tree._fields]
		# print me + str(fs) + " -> " + cs

	print "\n new tree for " + me + ":"
	for f in ast.iter_fields(tree):
		print f
	for c in children:
		print c

	process_rule(tree)

	for child_tree in children:
		# print ast.dump(child_tree)
		# print vars(child_tree)
		# print dir(child_tree)
		# print "attrs: " + str(child_tree._attributes)

		process(child_tree)

all_rules = {}
all_heads = {}
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

all_fields = {}
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



def main(args):
	if len(args) > 0:
		filename = args[0]
	else:
		filename = PARSE_FILENAME

	with open(filename, "r") as srcfile:
		source = srcfile.read()

	tree = compile(source, filename, "exec", ast.PyCF_ONLY_AST)
	process(tree)

	# with open("fields.txt", "w") as fields_file:
	# 	for key in all_fields:
	# 		line = "{} : {}\n".format(key, list(all_fields[key]))
	# 		fields_file.write(line)

	with open("rules.txt", "w") as outrules:
		for r in rules:
			outrules.write(r + "\n")
			
	with open("all-rules.txt", "w") as outrules:
		outrules.write(json.dumps(all_rules))

	with open("all-heads.txt", "w") as heads:
		heads.write(json.dumps(all_heads))

	outfilename = "{}{}".format(filename, OUTPUT_FILENAME_STEM)
	with open(outfilename, "w") as outfile:
		# Unparser.Unparser(tree, outfile)
		pass

if __name__=='__main__':
	main(sys.argv[1:])