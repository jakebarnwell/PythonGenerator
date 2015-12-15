# Stores my dictionary files, and contains methods that interact
#  with these dictionaries.

import re
import util

# stores all individual rules with their frequency counts
all_rules = {}
# stores all possible AST nodes mapped to a list containing
#  every possible rule with given AST node (head) as a lhs
all_heads = {}
# stores each AST node (head) mapped to all possible constituent
#  field types
all_fields = {}
# Maps each AST node (head), in className form, to an object
#  (true AST node) of that type. This allows for easy access to
#  such nodes so I can easily generate objects of a given class
#  name on the fly
all_objects = {}
# Maps each of the seven primitive class names to a list of
#  unique occurrences with their frequencies
all_primitives = {}

def update_primitives(fields):
	"""
	Given fields, a list of field-tuples like [('id', 'segment'), ...]
	updates the usage of any primitive ones in a frequency map so
	we can re-use them later
	"""
	def do_update_primitive(className, val):
		if className in all_primitives:
			_primitives = all_primitives[className]
			if val in _primitives:
				_primitives[val] += 1
			else:
				_primitives[val] = 1
			all_primitives[className] = _primitives
		else:
			all_primitives[className] = {val: 1}

	for f in fields:
		className = util.fieldValue2className(f[1])
		if className in util.PRIMITIVE_CLASSNAMES:
			do_update_primitive(className, f[1])

def update_rules(rule):
	"""
	Given a new string-version rule, adds it to the
	frequency dictionary or increments the count
	"""
	if rule in all_rules:
		all_rules[rule] += 1
	else:
		all_rules[rule] = 1

def update_objects(head, node):
	"""
	Given a head, adds an AST node to the dictionary unless
	such an entry for head already exists
	"""
	if head not in all_objects:
		all_objects[head] = node

def update_heads(head, rule):
	"""
	Given a head and a rule, adds the rule to the list of entries
	under this head, or creates a new entry for head if it doesn't
	exist and initializes the entry to the singleton list with that
	rule for this entry
	"""
	if head in all_heads:
		current = all_heads[head]
		if rule in current:
			pass
		else:
			current.append(rule)
			all_heads[head] = current
	else:
		all_heads[head] = [rule]

def update_fields(head, fields):
	"""
	Updates the listing of fields under this type of head, as
	necessary.
	"""
	if len(fields) > 0:
		if head in all_fields:
			_currentfields = all_fields[head]
			for field in fields:
				if field not in _currentfields:
					_currentfields.append(field)
					
			all_fields[head] = _currentfields
		else:
			all_fields[head] = fields

def prepare_primitives(raw_primitives):
	"""
	Pre-processes the primitives dictionary so that we can 
	quickly use its special features later. In particular, sets up
	specific sub-dictionaries that are needed when supplying
	certain values that are special in Python, like function 
	names or attribute names.
	"""
	p = {}

	nameRE = r"^[a-zA-Z_]+\w+$"

	for pcn in raw_primitives:
		p[pcn] = {}
		p[pcn]["normal"] = {}
		p[pcn]["special"] = {}

		vals = []
		freqs = []
		for val in raw_primitives[pcn]:
			freqs.append(raw_primitives[pcn][val])
			vals.append(val)
		p[pcn]["normal"]["vals"] = vals
		p[pcn]["normal"]["freqs"] = freqs

		if pcn in util.STRINGY:
			filtered_vals = []
			filtered_freqs = []
			for i in range(len(vals)):
				# Just get rid of string representations of True and False, because
				#  they are rarely good news. Unfortunately, this means that we will
				#  basically never see True or False in the generated code, but thankfully
				#  most code files don't have those anyway so they won't be missed too much.
				if re.search(nameRE, vals[i]) != None and vals[i] not in ["True","False"]:
					filtered_vals.append(vals[i])
					filtered_freqs.append(freqs[i])
			p[pcn]["special"]["vals"] = filtered_vals
			p[pcn]["special"]["freqs"] = filtered_freqs
		elif pcn in util.INTY:
			filtered_vals = []
			filtered_freqs = []
			for i in range(len(vals)):
				if vals[i] >= 0 and vals[i] <= 1:
					filtered_vals.append(vals[i])
					filtered_freqs.append(freqs[i])
			p[pcn]["special"]["vals"] = filtered_vals
			p[pcn]["special"]["freqs"] = filtered_freqs
	return p

def write_dict(d, filename):
	"""
	Writes a JSON-serializable dictionary to
	file.
	"""
	try:
		with open(filename, "w") as outfile:
			outfile.write(json.dumps(d))
	except Exception as e:
		with open("logs/write_dicts.log","a") as out:
			out.write(filename + ": " + str(e) + "\n")
