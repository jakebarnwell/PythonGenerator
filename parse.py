from nltk import CFG

import sys
import ast
import Unparser

PARSE_FILENAME = "parse.py"
OUTPUT_FILENAME_STEM = ".out.py"

def main(args):
	if len(args) > 0:
		filename = args[0]
	else:
		filename = PARSE_FILENAME

	with open(filename, "r") as srcfile:
		source = srcfile.read()

	tree = compile(source, filename, "exec", ast.PyCF_ONLY_AST)

	outfilename = "{}{}".format(filename, OUTPUT_FILENAME_STEM)
	with open(outfilename, "w") as outfile:
		Unparser.Unparser(tree, outfile)

if __name__=='__main__':
	main(sys.argv[1:])