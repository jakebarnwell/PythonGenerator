import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect

from argonaut.lib.base import BaseController, render
import argonaut.lib.helpers as h

import webhelpers.paginate as paginate
from webhelpers.html.tags import *
from formencode import htmlfill

from repoze.what.predicates import has_permission
from repoze.what.plugins.pylonshq import ActionProtector

log = logging.getLogger(__name__)

class BlogController(BaseController):
    
    def latest(self):
        c.posts_count = h.post.get_many(amount=10, active_only=True, count_only=True)
        c.posts = h.post.get_many(amount=10, active_only=True, order='desc')
        c.post = None
        if c.posts is None:
            abort(404)
        page_id = int(h.page.get_page_id_with_type('blog'))
        return render('/blog/view.mako', extra_vars={'page_id':page_id, 'post_count':c.posts_count, 'page':'latest', 'show_comment_form':'false'})
        
    def view(self,id):
        c.post = h.post.get(int(id))
        c.posts = None
        if c.post is None:
            abort(404)
        page_id = int(h.page.get_page_id_with_type('blog'))
        return render('/blog/view.mako', extra_vars={'page_id':page_id, 'post_count':1, 'page':'view', 'show_comment_form':'false'})
        
    def archives(self):
        try:
            if request.params.get('filter'):
                if h.forms.validate(h.forms.FilterForm()):
                    posts = h.post.get_many(filter=request.params.get('filter'), amount=100, active_only=True, order='desc')
                else:
                    raise Exception
            else:
                raise Exception
        except Exception, error:
            posts = h.post.get_many(active_only=True, order='desc', amount=100)
        if posts is None:
            abort(404)
        c.paginator = paginate.Page(
            posts,
            page=int(request.params.get('page', 1)),
            items_per_page = 20,
            )
        page_id = int(h.page.get_page_id_with_type('archives'))
        if request.params.get('filter'):
            html = render('/blog/archives.mako', extra_vars={'page_id':page_id})  
            return htmlfill.render(html,defaults=c.form_result,errors=c.form_errors)
        else:
            return render('/blog/archives.mako', extra_vars={'page_id':page_id})      

    @ActionProtector(has_permission('Write post'))
    def write(self, id=None):
        if id is None:
            c.post = None
            return render('/blog/write.mako')
        else:
            c.post = h.post.get(int(id))
            if c.post is None:
                abort(404)
            html = render('/blog/write.mako')
            tags = h.tag_post.get_tags(c.post.id)
            tag_list = []
            for tag in tags:
                tag_list.append(tag.name)
            values = {'subject':c.post.subject,'body':c.post.body,'tags':';'.join(tag_list)}
            return htmlfill.render(html,defaults=values)

    def _create_and_link_tags(self,tags,post_id):
        for name in tags.split(';'):
            tag = h.tag.get_tag(name)
            if not tag:
                h.tag.save_tag(name)
                tag = h.tag.get_tag(name)
            h.tag_post.add_to_post(tag.id,post_id)
            
    @ActionProtector(has_permission('Write post'))
    def save(self, id=None):
        if id is None:
            abort(404)
        if h.forms.validate(h.forms.PostForm()):
            if id == '0':
                # new post
                new = h.post.new()
                for k, v in c.form_result.items():
                    if k <> 'tags':
                        setattr(new, k, v)
                new.posted = h.timehelpers.now()
                identity = request.environ.get('repoze.who.identity')
                new.author = h.auth.get_user_id(identity['repoze.who.userid'])
            else:
                # edit
                new = h.post.get(int(id))
                new.body = request.POST['body']
                new.subject = request.POST['subject']
            # save to db
            h.post.save(new)
            # tags
            self._create_and_link_tags(request.POST['tags'],new.id)
            # flash message
            session['flash'] = 'Post successfully saved.'
            session.save()
            # redirect to post
            c.post = new
            redirect(url(controller='blog', action='view', id=new.id, subject=h.urlify(new.subject)), code=303)
        else:
            session['flash'] = 'Erros in the submitted post, please correct and try again.'
            session.save()
            c.post = None
            html = render('/blog/write.mako')
            return htmlfill.render(html,defaults=c.form_result,errors=c.form_errors)
