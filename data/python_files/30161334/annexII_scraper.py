import os
import sys
import requests
from requests import async
from lxml.html import fromstring
import json
import datetime
from itertools import imap

ROOT_URL = 'http://ec.europa.eu/consumers/cosmetics/cosing/'

def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def parse_ingredient(ingredient):
    return ingredient

def parse_detail(response):
    content = response.content
        
    page = fromstring(content)
    cells = page.xpath("//td[@class='details']")
    
    substance_group = cells[0].text_content().strip()
    cas = cells[1].text_content().strip()
    inn = cells[3].text_content().strip()
    directive = cells[4].text_content().strip()
    ingredients = []

    # Check for identified ingredients in substance group.  Add all of them.
    identified_ingredients = cells[9]
    if identified_ingredients.text_content().strip() != "":
        ingredients.extend(
            [parse_ingredient(a.text_content().strip()) for a in identified_ingredients.xpath(".//a")]);

    # Check if chemical name is defined on substance group, use it as an ingredient
    # Otherwise, just use substance name as the ingredient name
    chemical_name = cells[8].text_content().strip()
    if chemical_name != "":
        ingredients.append(parse_ingredient(chemical_name))
    else:
        ingredients.append(substance_group)
    
    print json.dumps({
        'substance_group': substance_group,
        'cas': cas,
        'inn': inn,
        'directive': directive,
        'ingredients': ingredients,
    })
    sys.stdout.flush()

def fetch_detail(href):
    return requests.get(ROOT_URL + href)

def parse_annex(content):
    page = fromstring(content)
    cells = page.xpath(".//td[@class='results-last']")
    if len(cells) > 0:
        return [cell[0].get('href') for cell in cells]
    else:
        return None

def fetch_annex(start=1):
  return requests.post(ROOT_URL + 'index.cfm', data={
      'fuseaction': 'search.results',
      'search': 'true',
      'start': start,
      'part_no': 1,
      'search_simple_name': '',
      'search_type': 'SUB',
      'search_annex': 'II',
      'search_scope': 0,
      'search_status': 1,
      'search_advanced_name': '',
      'search_cas': '',
      'search_einecs_elincs': '',
      'search_inn': '',
      'search_ph_eur': '',
      'search_opinion': '',
      'search_ref_no': '',
      'search_iupac': '',
      'search_description': '',
      'search_restriction': '',
      'search_function': '',
      'search_proposed': 'N',
      'search_directive': '',
      'search_publication_date': '',
      'search_directiveOther': 0,
      'search_restrictionOther': '',
      'search_version_no': 1
    })

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]


    # Fetch ingredient detail URLs
    start = 1
    urls = []
    print '# Starting URL crawl'
    while (True):
        resp = fetch_annex(start)
        if resp.status_code != 200:
            continue
        
        page_urls = parse_annex(resp.content)
        if page_urls is None:
            break
        elif len(page_urls) > 0:
            urls.extend(page_urls)
            print '# Crawled %d urls' % len(urls)
            start += 100

    # Fetch detail pages, parse them on response

    requests = [async.get(ROOT_URL + u, hooks=dict(response=parse_detail)) for u in urls]
    responses = async.map(requests, size=10)

if __name__ == "__main__":
    sys.exit(main())
