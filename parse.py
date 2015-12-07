from nltk import CFG

import sys
import ast
import Unparser
import json

PARSE_FILENAME = "parse.py"
OUTPUT_FILENAME_STEM = ".out.py"

def process(tree):
	me = tree.__class__.__name__
	
	record_fields(tree)
	

	children = [c for c in ast.iter_child_nodes(tree)]
	childNames = [child.__class__.__name__ for child in children]
	childrenString = " ".join(childNames)

	if len(children) > 0 or len(tree._fields) > 0:
		cs = childrenString if len(children) > 0 else "X"
		fs = [field+"="+str(getattr(tree, field)) for field in tree._fields]
		print me + str(fs) + " -> " + cs

	for child_tree in children:
		# print ast.dump(child_tree)
		# print vars(child_tree)
		# print dir(child_tree)
		# print "attrs: " + str(child_tree._attributes)

		process(child_tree)

# tree._attributes: lineno, col_offset
# tree._fields: e.g. lower, upper, step, n, id, ctx, s, etc.

# When doing the rules, couple the fields with the children. For example:
# Slice['lower=<_ast.Num object at 0x7f09e94bced0>', 'upper=None', 'step=None'] -> Num
# The children of Slice are directly linked to the fields (in this case, 'lower')
# In fact, I'm pretty sure the children only exist if the relevent fields are filled in

# I'm going to want rules like this
#  Node ->(fields not None)


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
			
	outfilename = "{}{}".format(filename, OUTPUT_FILENAME_STEM)
	with open(outfilename, "w") as outfile:
		# Unparser.Unparser(tree, outfile)
		pass

if __name__=='__main__':
	main(sys.argv[1:])