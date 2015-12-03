import markdown
import re
import ConfigParser
import os
import time
import glob
import datetime
_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')
def _slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    
    From Django's "django/template/defaultfilters.py".
    """
    import unicodedata
    if not isinstance(value, unicode):
        value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)
    
def get_config(section='', key=''):
    config = ConfigParser.ConfigParser()
    config.read("config.py")
    try:
        value = config.get(section, key).strip('\'').strip('\"')
    except:
        value = ''
    return value

ROOT_DIR = get_config('Basic', 'ROOT_DIR')    

def render(template, key, timer, time_list = [], content = {}, catagories = []):
    """
    render(get_config('Basic', 'TEMPLATE'), key, timer[key], time_list, data, categories)
    """
    title = re.findall(" (\w+)",key)
    filename = _slugify(title)
    directory = re.findall("(\w+) ",key)[0]
    template = open(template,"r").read()
    next = iter(re.split("({{|}})", template)).next
    data = []
    try:
        token = next()
        while 1:
            if token == "{{":
                data.append(variable(next(), key, timer, time_list, content, catagories))
                if next() != "}}":
                    raise SyntaxError("missing variable terminator")
            else:
                data.append(token) # literal
            token = next()
    except StopIteration:
        pass
    return data, directory, filename


def variable(name, key, timer, time_list, content, categories):
    title = re.findall(" (\w+)",key)
    head = " "
    for word in title:
        head += word + " "
    if name =='AUTHOR':
        return get_config('Basic', 'AUTHOR')
    if name == 'SIDELINK':
        side = '<ul>'
        for cat in categories:
            side += "<li><a href='%s' title='%s'>%s</a></li>" % (os.path.join(get_config("Basic", "SERVE_DIR"),cat,"index.html"), cat, cat)
        side+="</ul>"
        return side
    if name == 'CONTENT':
        return content[key]
    if name =='TITLE':
        return head.title()
    if name =='STATIC_URL':
        return get_config('Basic', 'STATIC_URL')
    if name =='BASE_URL':
        return get_config('Basic', 'BASE_URL')
    if name == 'NEXT':
        try:
            for count, times in enumerate(time_list):
                if timer[key] == times[0]:
                    if time_list[count+1] != time_list[0]:
                        next = time_list[count+1]
                        break
            next = os.path.join(next[1],next[2])+".html"
            return "<a href=\"%s%s\">NEXT</a>" % (get_config("Basic", "SERVE_DIR"), next)
        except:
            return
    if name == 'CURRENT_URL':
        try:
            for count, times in enumerate(time_list):
                if timer[key] == times[0]:
                    current = time_list[count]
                    break
            current = os.path.join(current[1], current[2])+".html"
            return "%s" % (get_config("Basic", "SERVE_DIR"), current)
        except:
            return
    if name == 'PREVIOUS':
        try:
            for count, times in enumerate(time_list):
                if timer[key] == times[0]:
                    if time_list[count-1] != time_list[len(time_list)-1]:
                        previous = time_list[count-1]
                        break
            previous = os.path.join(previous[1],previous[2])+".html"
            return "<a href=\"%s%s\">PREVIOUS</a>" % (get_config("Basic", "SERVE_DIR"), previous)
        except:
            return
        #for count, times in enumerate(time_list):
        #    if timer[key] == times:
        #        previous = time_list[count-1]
        #return "<a href=\"%s\">NEXT</a>" % (previous)
    if name == 'LINKS':
        #uses nltk to find related posts
        pass
    if name == 'TIME':
        return timer[key]
def engine_driver():
    pass

def coach(filename):
    markup = open(filename,"r").read()
    return markdown.markdown(markup)

def train_builder():
    start_time = time.time()
    data = {}
    timer = {}
    categories = []
    time_list = []
    path = get_config(section='Repository', key='CONTENT_DIR')
    print "Rendering ..."
    for infile in glob.glob( os.path.join(path, '*.post') ):
        filename = infile.split('/')[-1]
        category = re.findall(r'(\w+)_', filename)[0]
        title = filename.split("_")[1].split(".")[0]
        content = coach(infile)
        timer[category + " " + title] = time.strftime("%d/%m/%Y %I:%M:%S %p",time.localtime(os.path.getmtime(infile)))
        data[category + " " + title] = content
        time_list.append([time.strftime("%d/%m/%Y %I:%M:%S %p",time.localtime(os.path.getmtime(infile))), category, _slugify(title)])
        if category not in categories:
            categories.append(category)
    time_list.sort()
    for count, key in enumerate(data):
        html, directory, filename = render(get_config('Basic', 'TEMPLATE'), key, timer, time_list, data, categories)
        if not os.path.exists(os.path.join(get_config('Basic', 'SERVE_DIR'),directory)):
            os.makedirs(os.path.join(get_config('Basic', 'SERVE_DIR'),directory))
        os.chdir(os.path.join(get_config('Basic', 'SERVE_DIR'),directory))
        painter = open(filename+".html","w")
        for datum in html:
            if datum:
                painter.write(datum)
        print "%s.html" % (filename)
        painter.close()
        # generate index.html for each folder
        os.chdir(ROOT_DIR) 
    
    data = {}
    for category in categories:
        path = get_config(section='Repository', key='CONTENT_DIR')
        for infile in glob.glob( os.path.join(path, '*.post') ):
            filename = infile.split('/')[-1]
            title = filename.split("_")[1].split(".")[0]
            cat = re.findall(r'(\w+)_', filename)[0]
            indx = cat+" index"
            if category == cat:
                if indx in data:
                    data[indx] += "<a href = \""+get_config('Basic', 'SERVE_DIR')+category+"/"+_slugify(title)+".html\">"+title.title()+"</a><br>" # "["+title+"](/"+category+"/"+_slugify(title)+".html)\n\n"
                else:
                    data[indx] = ""
                    data[indx] += "<a href = \""+get_config('Basic', 'SERVE_DIR')+category+"/"+_slugify(title)+".html\">"+title.title()+"</a><br>"
            timer[indx] = str(datetime.datetime.now())
            time_list = [time.time(), category, "index"]
        html, directory, filename = render(get_config('Basic', 'TEMPLATE'), cat+" index", timer, time_list, data, categories)
        if not os.path.exists(os.path.join(get_config('Basic', 'SERVE_DIR'),cat)):
            os.makedirs(os.path.join(get_config('Basic', 'SERVE_DIR'),cat))
        os.chdir(os.path.join(get_config('Basic', 'SERVE_DIR'),cat))
        painter = open("index.html","w")
        for datum in html:
            if datum:
                painter.write(datum)
        print "%s.html" % (get_config('Basic', 'SERVE_DIR')+category+"/"+"index")
        painter.close()
        os.chdir(ROOT_DIR) 
    print "Took: %s seconds." % (time.time() - start_time)
        
train_builder()

    
