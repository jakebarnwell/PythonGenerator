#!/usr/bin/env python

# This is the only entry point into the python generation portion
#  of this project. The only option is the default: process everything
#  in the data/ folder

import sys
import generate_python

if __name__=='__main__':
	generate_python.main(sys.argv[1:])