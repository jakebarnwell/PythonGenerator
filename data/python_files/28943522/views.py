import re
from wiki.models import DBSession
from wiki.models import Page
from docutils.core import publish_parts

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.url import route_url

from pyramid.security import authenticated_userid


# regex used to find wiki words
wikiwords = re.compile(r"\[\[([A-Z]+\w+)\]\]", re.IGNORECASE)


def viewWiki(request):
    """
    Redirect to the wiki front page
    """
    return HTTPFound(
        location=route_url('viewPage', request, pagename='FrontPage')
    )


def viewPage(request):
    """
    Displays a specific wiki page.
    If the page requested is not found in the database then the user
    is redirected to the add page view
    """
    
    def check(match):
        """
        Checks if a given page exists and returns a link to it.
        If the page does not exist it returns a link to add the page.
        """
        word = match.group(1)
        exists = session.query(Page).filter_by(name=word).all()
        if exists:
            result = (route_url('viewPage', request, pagename=word), word)
        else:
            result = (route_url('addPage', request, pagename=word), word)

        return '<a href="%s">%s</a>' % result
    # end def check

    session = DBSession()
    pagename = request.matchdict['pagename']
    page = session.query(Page).filter_by(name=pagename).first()
    
    if page is not None:
        content = publish_parts(page.data, writer_name='html')['html_body']
        content = wikiwords.sub(check, content)
        result = {
            'page':page,
            'content':content,
            'edit_url':route_url('editPage', request, pagename=pagename),
            'logged_in':authenticated_userid(request)
        }
    else:
        # if you try to reach a page that doesn't exist then
        # hop over to the addPage view rather than get a 404
        result = HTTPFound(
            location=route_url('addPage', request, pagename=pagename)
        )

    return result


def addPage(request):
    """
    A view to create a new wiki page, or save an addition in progress
    """
    name = request.matchdict['pagename']
    if 'form.submitted' in request.params:
        session = DBSession()
        body = request.params['body']
        page = Page(name, body)
        session.add(page)
        result = HTTPFound(
            location=route_url('viewPage', request, pagename=name)
        )
    else:
        result = {
            'page':Page('',''),
            'save_url':route_url('addPage', request, pagename=name),
            'logged_in':authenticated_userid(request)
        }
    
    return result


def editPage(request):
    """
    Renders the page editor form.
    """
    name = request.matchdict['pagename']
    session = DBSession()
    page = session.query(Page).filter_by(name=name).one()
    
    if 'form.submitted' in request.params:
        page.data = request.params['body']
        session.add(page)
        result = HTTPFound(
            location=route_url('viewPage', request, pagename=name)
        )
    else:
        result = {
            'page':page,
            'save_url':route_url('editPage', request, pagename=name),
            'logged_in':authenticated_userid(request)
        }
    
    return result
