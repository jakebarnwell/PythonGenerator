#!/usr/bin/env python

# This is the only entry point into the python generation portion
#  of this project. The first argument is the number of files you
#  want to create. e.g.
#     ./main.py 5
#  generates 5 python files.

import sys
import generate_python

if __name__=='__main__':
	"""
	Usage:
		./main.py <number of files to generate>
	"""
	generate_python.main(sys.argv[1:])