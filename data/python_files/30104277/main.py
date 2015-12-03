import json
import urllib
import re
import os
from json import loads as parse_json

from webcall import webcall

from flask import Flask
from flask import render_template
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

def load_dictionary(dictionary):
    data_geiriadur = open(dictionary)
    geiriadur = json.load(data_geiriadur)
    data_geiriadur.close()
    return geiriadur

def process_html(data, regex, word):
    data = re.sub(r'(\n|\r|\t)', '', data)
    regex = regex.replace('[word]', word)
    matches = re.findall(regex, data)
    if matches:
        result = "".join(matches)
        strip_regex = "(<a.*?>|<\/a>|<A.*?>|<\/A>|<hr \/>|<img.*?>|<IMG.*?>|<h2>.*?<\/h2>|<\/h1>)"
        result = re.sub(strip_regex, '', result)
    else:
        result = "No results found"
    return result

def process_json(data, json, word):
    data = parse_json(data)
    return render_template(json, items=data['items'])

def get_result(geiriadur, word):
    url = geiriadur['url'].replace('[word]', word)
    @webcall(url=url, method=geiriadur['type'])
    def data_closure(): pass
    params = geiriadur['data'].replace('[word]', word).replace(' ', '+')
    data = data_closure(params=params)
    if geiriadur.has_key('regex'):
        return process_html(data, geiriadur['regex'], word)
    if geiriadur.has_key('json'):
        return process_json(data, geiriadur['json'], word)
    return "No results found"
    

@app.route("/dictionary/<lang>/<word>")
def dictionary(lang, word):
    data_geiriaduron = load_dictionary('geiriaduron.json')
    geiriaduron = []
    for geiriadur in data_geiriaduron['riadur']['geiriadur']:
        if geiriadur['lang'] == lang:
            geiriaduron.append({
                'name': geiriadur['name'],
                'result': get_result(geiriadur, word)
            })
    return render_template('dictionary.html', geiriaduron=geiriaduron, lang=lang)

if __name__ == "__main__":
    app.debug = True
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
