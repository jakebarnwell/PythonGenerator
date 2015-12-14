import json
import copy
import random

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


def random_draw(eles, probs):
	assert len(eles) == len(probs)
	sumProbs = sum(probs)
	assert sumProbs > 0
	probs = map(lambda p: p / sumProbs, probs)
	# CDF = reduce()

	r = random.random()
	cumsum = 0
	for i in range(len(eles)):
		cumsum += probs[i]
		if r <= cumsum:
			return eles[i]

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