import requests
import json

IDS_STORE = "python_file_ids.store"

API_BASE = "https://searchcode.com/api/codesearch_I/?"

_QUERY = "import%20lang:python"
_PER_PAGE = 2 # this is the maximum
PARAMS = "q={}&per_page={}".format(_QUERY, _PER_PAGE)

ids = []
names = []

num_pages = 2
for p in range(num_pages):
    url = API_BASE + PARAMS + "&p={}".format(p)
    response = requests.get(url)
    
    data = json.loads(response.content)
    results = data["results"]
    ids.extend([r["id"] for r in results])
    names.extend([r["filename"] for r in results])
    print "Fetched {} results on page {}".format(_PER_PAGE, p)

with open(IDS_STORE, "w") as f:
    for i in xrange(len(ids)):
        f.write("{}\t{}\n".format(str(ids[i]),str(names[i])))

print "Wrote results fo file {}".format(IDS_STORE)
