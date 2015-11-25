import os
import requests
import json

# Make sure to run fetch_python_ids first
# to generate the store file of ids of
# resources

IDS_STORE = "python_file_ids.store"
PYTHON_FILES_DIR = "python_files"
if not os.path.exists(PYTHON_FILES_DIR):
    os.mkdir(PYTHON_FILES_DIR)

API_BASE = "https://searchcode.com/api/result/"

success = 0
fail_ids = []
lineNo = 0
with open(IDS_STORE, "r") as f:
    for line in f:
        lineNo = lineNo + 1
        l = line.split("\t")
        l[-1] = l[-1].split("\n")[0] # removes trailing \n
        newdir = "{}/{}".format(PYTHON_FILES_DIR,str(l[0]))
        if not os.path.exists(newdir):
            url = API_BASE + "{}/".format(l[0])
            
            os.mkdir(newdir)
            newfile = "{}/{}".format(newdir,l[1])
            try:
                response = requests.get(url)
                data = json.loads(response.content)
           
                outfile = open(newfile, "w")
                outfile.write(data["code"])
                success = success + 1
            except:
                fail_ids.append(l[0])
                print "Failed to write code:"
                print data["code"]
                if os.path.exists(newfile):
                    os.remove(newfile)
                os.rmdir(newdir)
            finally:
                outfile.close()
        print "Resolved resource #{}".format(str(lineNo))
print("{} files successfully retrieved, {} failures"
      .format(success, len(fail_ids)))
print("IDs of failed retrievals:")
for fail in fail_ids:
    print(" {}".format(fail))
