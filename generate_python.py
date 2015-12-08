import sys
import copy

import generate_rules


def main(args):
	# Be sure to copy the object every time you make a new one
	#  using copy.copy(object)
	(heads, rules, objects) = generate_rules.process_all();
	

if __name__=='__main__':
	main(sys.argv[1:])