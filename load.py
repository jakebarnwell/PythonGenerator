import json

RULES_FILE = "all-rules.txt"
HEADS_FILE = "all-heads.txt"

def rules():
	with open(RULES_FILE, "r") as rulesfile:
		rules = json.loads(rulesfile.read())
		return rules

def heads():
	with open(HEADS_FILE, "r") as headfile:
		heads = json.loads(headfile.read())
		return heads