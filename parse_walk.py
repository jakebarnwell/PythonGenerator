import ast
import sys

def doParse(infile, outfile):
	with open(infile, "r") as fdin:
		source = fdin.read()
	with open(outfile, "w") as fdout:
		tree = compile(source, infile, "exec", ast.PyCF_ONLY_AST)
		walk(tree)

def walk(tree):

def main(args):
	infile = args[0]
	outfile = args[1]
	doParse(infile, outfile)

if __name__=='__main__':
    main(sys.argv[1:])