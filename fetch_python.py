import requests
import json

api = "https://api.github.com"

url = api + "/repos/viswimmer1/PythonGenerator/readme"
url = api + "/users"

usernames = []

response = requests.get(url)
data = json.loads(response.content)

these_usernames = [d['login'] for d in data]
usernames.extend(these_usernames)

#print usernames

response = requests.get("https://api.github.com/search/code?q=do+user:viswimmer1+in:file+language:python")
print response.content
