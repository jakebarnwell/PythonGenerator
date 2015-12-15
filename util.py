import json
import copy
import random
import os

PRIMITIVE_CLASSNAMES = ["str","unicode","bool","int","long","float","complex"]
STRINGY = ["str", "unicode"]
INTY = ["int", "long"]

def fieldValue2className(val):
	className = val.__class__.__name__

	if className == "list":
		return [fieldValue2className(e) for e in val]
	else:
		return className

def write_dict(d, filename):
	try:
		with open(filename, "w") as outfile:
			outfile.write(json.dumps(d))
	except Exception as e:
		with open("logs/write_dicts.log","a") as out:
			out.write(filename + ": " + str(e) + "\n")

def log(msg, lvl):
	with open("logs/generate.log", "a") as debug:
		debug.write("  "*lvl + msg + "\n")

def init():
	if not os.path.isdir("logs"):
		os.mkdir("logs")
	if not os.path.isdir("dicts"):
		os.mkdir("dicts")
	if not os.path.isdir("generated"):
		os.mkdir("generated")

	with open("logs/generate.log", "w") as out:
		out.write("")
	with open("logs/write_dicts.log","w") as out:
		out.write("")

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