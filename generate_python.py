import sys
import copy
import random

import generate_rules


def main(args):
	# Be sure to copy the object every time you make a new one
	#  using copy.copy(object)
	(heads, pcfg, objects) = generate_rules.process_all();

	# rules = heads[heads.keys()[0]]
	# total = 0
	# for r in rules:
	# 	print pcfg[r]
	# 	total += pcfg[r]
	# print "total sum is: " + str(total)

	tree = build_tree(heads, pcfg, objects, copy.copy(objects["Module"]))

def random_draw(eles, probs):
	assert len(eles) == len(probs)
	sumProbs = sum(probs)
	assert sumProbs > 0
	probs = map(lambda p: p / sumProbs, probs)
	CDF = reduce()

	r = random.random()
	cumsum = 0
	for i in range(len(eles)):
		cumsum += probs[i]
		if r <= cumsum:
			return eles[i]
			

def build_tree(startNode, heads, pcfg, objects):
	def do_build_tree(node):
		possible_rules = heads[node.__class__.__name__]
		probabilities = [pcfg[rule] for rule in possible_rules]
		rule = random_draw(possible_rules, probabilities)

		populateNode(node, rule) 

	startNode = ... # do stuff to modify this Module node appropriately
	return do_build_tree(startNode)



if __name__=='__main__':
	main(sys.argv[1:])