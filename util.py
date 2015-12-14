import json
import copy
import random
import numpy

def fieldValue2className(val):
	className = val.__class__.__name__

	if className == "list":
		return [fieldValue2className(e) for e in val]
	else:
		return className

def write_dict(d, filename):
	with open(filename, "w") as outfile:
		outfile.write(json.dumps(d))

def log(msg, lvl):
	with open("debug.log", "a") as debug:
		debug.write("  "*lvl + msg + "\n")

# For whatever reason, using numpy is 1200 times slower so I just define
#  my own random_draw function
def random_draw(eles, probs=None):
	"""
	Given a list of elements, randomly draws one of them. If a
	probability distribution is provided (as an array), the element 
	from eles is randomly chosen with respect to that distribution.
	The probability distribution elements do not have to add to 1.
	"""
	if probs != None:
		assert len(eles) == len(probs)
		sumProbs = sum(probs)
		assert sumProbs > 0
		probs = map(lambda p: 1.0*p / sumProbs, probs)
		# CDF = reduce()

		r = random.random()
		cumsum = 0
		for i in range(len(eles)):
			cumsum += probs[i]
			if r <= cumsum:
				return eles[i]
		return eles[-1] #Fall-through, just in case weird floating error math
	else:
		ind = random.randint(0, len(eles) - 1)
		return eles[ind]

def test_random_draw():
	"""
	Tests my random_draw function to make sure I didn't
	screw it up too much.
	"""
	numDraws = 1000000
	numEles = 10
	li = range(numEles)
	frequencies = [0] * numEles
	for i in range(numDraws):
		frequencies[random_draw(li)] += 1
	frequencies = map(lambda x: 1.0*x / numDraws, frequencies)
	print "Uniform probability test."
	print "Frequencies of each element drawn:"
	print frequencies

	print "\n"

	li = [0, 1, 2, 3]
	probs = [0, 1, 2, 3]
	frequencies = [0, 0, 0, 0]
	for i in range(numDraws):
		frequencies[random_draw(li, probs)] += 1
	frequencies = map(lambda x: 1.0*x / numDraws, frequencies)
	print "Non-uniform probability test. Probability distribution is " + str(probs)
	print "Frequencies of each element drawn:"
	print frequencies

def rules2pcfg(rules, heads):
	"""
	Given a dict of all rules and all heads, returns a PCFG for
	the rules.

	Args:
	 heads: dict, mapping from 'head' (e.g. 'FunctionDef') to a list of all
	 		possible (string-versioned) re-write rules for that head, e.g.
	 		FunctionDef -> [('name', 'str'), ('args', 'arguments'), ('body', ['For']), ('decorator_list', [])]
	 		where each tuple is a field-tuple of the form (fieldKeyClassName, fieldValueClassName)
	 rules: dict, mapping from each stringified-rule of the form listed in heads 
	 		to the number of occurrences (invocations) of that rule in the corpora
	"""
	pcfg = copy.copy(rules)

	for head in heads:
		head_rewrite_rules = heads[head]
		head_sum = 0
		for rule in head_rewrite_rules:
			head_sum += rules[rule]
		for rule in head_rewrite_rules:
			pcfg[rule] = rules[rule] * 1.0 / head_sum

	return pcfg