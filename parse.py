from nltk import CFG

GRAMMAR_FILENAME = "cfg_grammar.txt"

f = open(GRAMMAR_FILENAME, "r")
file_contents_str = f.read()
f.close()

grammar = CFG.fromstring(file_contents_str)
print grammar.productions()
