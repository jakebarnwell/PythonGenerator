from nltk import CFG

GRAMMAR_FILENAME = "cfg_grammar.txt"
SIMPLEFILE_FILENAME = "file.py"



def grammar():
	f = open(GRAMMAR_FILENAME, "r")
	file_contents_str = f.read()
	f.close()

	grammar = CFG.fromstring(file_contents_str)
	return grammar

def s1():
	with open(SIMPLEFILE_FILENAME, "r") as f:
		return f.read().split(" ")