import json

def fieldValue2className(val):
	className = val.__class__.__name__

	if className == "list":
		return [fieldValue2className(e) for e in val]
	else:
		return className

def write_dict(d, filename):
	with open(filename, "w") as outfile:
		outfile.write(json.dumps(d))
