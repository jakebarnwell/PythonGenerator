import sys
sys.path.append("../")

import TemplateAPI
from photos import photoAPI, photoHTMLrenderer, photoUploader
from profile import profile_page, editprofile_page
from event import event
from user import usertools
from user import user_pages
from sessions import sessions
from search import searchAPI

def render_search(response):
    query = response.get_field("query")
    search_type = response.get_field("search_type")
    results = []
    if search_type == "user":
        results = searchAPI.search_users(query)
    elif search_type == "event":
        results = searchAPI.search_events(query)
    elif search_type == "photo":
        results = searchAPI.search_photos(query)
    response.write(TemplateAPI.render('search_page.html', response, {'results':results}))
    
def render_search_test(response):
    response.write(TemplateAPI.render('search_test.html', response, {}))
