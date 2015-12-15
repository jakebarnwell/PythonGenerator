# Handles select post-processing of generated python files.

import re
import random

def postprocess(text):
	"""
	Post-processes the text from a generated python file, applying
	various quality-of-life improvements to make the code look
	better.
	"""
	text = remove_singleLineStrings(text)
	text = remove_trailingCommas(text)
	text = add_randomLineBreaks(text)
	return text

def remove_singleLineStrings(text):
	"""
	Removes single lines that are entirely just a string, e.g.
		'foo'
	since they are pretty common, for some reason.
	"""
	lines = text.split('\n')
	rgx1 = re.compile(r"^\s*'[^']*'\s*$")
	rgx2 = re.compile(r'^\s*"[^"]*"\s*$')
	new_lines = []
	for line in lines:
		if re.match(rgx1, line) or re.match(rgx2, line):
			continue
		new_lines.append(line)
	new_text = '\n'.join(new_lines)
	return new_text

def remove_trailingCommas(text):
	"""
	Removes trailing commas from argslists and so on, but not for 
	tuples.
	"""
	lines = text.split('\n')
	rgx = re.compile(r"^(.*),\s*(\):.*)$")
	new_lines = []
	for line in lines:
		m = re.match(rgx, line)
		if m:
			new_line = m.groups()[0] + m.groups()[1]
			new_lines.append(new_line)
		else:
			new_lines.append(line)
	new_text = '\n'.join(new_lines)
	return new_text

def add_randomLineBreaks(text):
	"""
	Adds random line breaks throughout the text to make it look 
	more human-like.
	"""
	def blank(line):
		return re.search(r"^\s*$", line) != None
	lines = text.split('\n')

	new_lines = []
	i = 0
	while True:
		if i >= len(lines):
			break
		new_lines.append(lines[i])
		if i >= 3:
			if not (blank(new_lines[-1]) or blank(new_lines[-2]) or blank(new_lines[-3])):
				if random.random() < 0.15:
					new_lines.insert(-1, "")
		i += 1
	new_text = '\n'.join(new_lines)
	return new_text