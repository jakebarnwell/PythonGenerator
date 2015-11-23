import os
import requests
import json

IDS_STORE = "python_file_ids.store"
PYTHON_FILES_DIR = "python_files"
if not os.path.exists(PYTHON_FILES_DIR):
    os.mkdir(PYTHON_FILES_DIR)

API_BASE = "https://searchcode.com/api/result/"

lineNo = 0
with open(IDS_STORE, "r") as f:
    for line in f:
        lineNo = lineNo + 1
        l = line.split("\t")
        l[-1] = l[-1].split("\n")[0] # removes trailing \n
        newdir = "{}/{}".format(PYTHON_FILES_DIR,str(l[0]))
        if not os.path.exists(newdir):
            url = API_BASE + "{}/".format(l[0])
            response = requests.get(url)
            data = json.loads(response.content)
            

            os.mkdir(newdir)
            newfile = "{}/{}".format(newdir,l[1])
            try:
                outfile = open(newfile, "w")
                outfile.write(data["code"])
            except:
                print "Failed to write code:"
                print data["code"]
                if os.path.exists(newfile):
                    os.remove(newfile)
                os.rmdir(newdir)
            finally:
                outfile.close()
        print "Resolved resource #{}".format(str(lineNo))
