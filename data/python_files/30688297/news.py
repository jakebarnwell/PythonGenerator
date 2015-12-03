import itertools

import lxml.html
import re
import urllib2
import os
import sys

import feedparser


def source1():
    root = 'http://www.belcanto.ru/'
    page = lxml.html.parse(root)
    links = [link.get('href') for link in  page.xpath("//td[@bgcolor='#EE9955']/a[@class='small']")]
    for link in links:
        page = lxml.html.parse('%s%s'%(root, link))
        news = {}
        news['title'] = page.xpath("//p/b/font[@color='#FFCC99']")[0].text

        content = urllib2.urlopen('%s%s'%(root, link)).read()
        content = re.findall('<img src="(?:im|pi).+?>(?P<text>.+?)</P>', content, re.S)
        if not content:
            print '%s%s'%(root, link)
            continue
        else:
            try:                
                content = lxml.html.fromstring(content[0].decode('cp1251')).text_content()
            except:
                continue
        
        element = page.xpath("//td[@width='96%']/div/p[@class='big']")
        news['text'] = '<p>%s</p> <p>%s</p> <p>%s</p>'%(content, element[1].text, element[2].text)
        news['source'] = u'http://www.belcanto.ru/'
        yield news

def feed(rss):
    feed = feedparser.parse(rss)
    for item in feed.entries:
        news = {}
        news['title'] = item.title
        news['text'] = item.summary_detail.value
        news['source'] = item.link
        yield news
                
        
def generate(model):
    rss = ['http://www.novoteka.ru/rss/Culture.Music.Classic', 'http://www.novoteka.ru/r/Culture/Opera']
    for news in itertools.chain(*(map(feed, rss))):
        model.News(news['title'], news['text'], news['source']).db_add()
        
def hosting():
    import os
    os.chdir('/home/mylokin/guidem/src')
    sys.path.append("/home/mylokin/guidem/src")
    
    from paste.deploy import appconfig
    from pylons import config
        
    from guidem.config.environment import load_environment
    
    conf = appconfig('config:/home/mylokin/guidem/src/production.ini')
    load_environment(conf.global_conf, conf.local_conf)
    
    import guidem.model
    generate(guidem.model)

def local():
    sys.path.append("/home/andrew/workspace/new_guidem/guidem")

    from paste.deploy import appconfig
    from pylons import config
        
    from guidem.config.environment import load_environment
    
    conf = appconfig('config:/home/andrew/workspace/new_guidem/guidem/development.ini')
    load_environment(conf.global_conf, conf.local_conf)
    
    import guidem.model
    generate(guidem.model)
    
if __name__=="__main__":
    commands = {'hosting':hosting, 'local':local}
    if commands.has_key(sys.argv[1]):
        commands[sys.argv[1]]()
    else:
        print 'hosting or local?'
