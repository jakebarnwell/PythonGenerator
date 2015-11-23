import fetch_python_ids as ids

import os
import requests
import json

PYTHON_FILES_DIR = "python_files"
if not os.path.exists(PYTHON_FILES_DIR):
    os.mkdir(PYTHON_FILES_DIR)

API_BASE = "https://searchcode.com/api/result/"

with open(ids.IDS_STORE, "r") as f:
    for line in f:
        l = line.split("\t")
        l[-1] = l[-1].split("\n")[0] # removes trailing \n
        newdir = "{}/{}".format(PYTHON_FILES_DIR,str(l[0]))
        if not os.path.exists(newdir):
            url = API_BASE + "{}/".format(l[0])
            response = requests.get(url)
            data = json.loads(response.content)

            os.mkdir(newdir)
            outfile = open("{}/{}".format(newdir,l[1]), "w")
            outfile.write(data["code"])
            outfile.close()
