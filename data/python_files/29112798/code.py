import os, sys

ROOT_PATH = os.path.dirname(__file__)

sys.path = [ROOT_PATH, '%s/lib' % os.path.dirname(ROOT_PATH),] + sys.path

import web
import datetime

from google.appengine.api import users

from common.utils import render_template, admin_perm_required
from common.models import Post, Static
from common.forms import post_form, static_form


SITE_URL = 'http://www.sibande.com'
context = dict()


class index:
    def GET(self):
        context['posts'] = Post.all().filter('active =', True).order('-datetime')

        return render_template('index.html', **context)
    def POST(self):
        page = web.input().get('page')
        if page:
            return web.seeother(page, absolute=True)
        return web.seeother('/')


class add_edit:

    def __init__(self):
        self.form_class = post_form
    def init_data(self, post_id, action):
        try:
            self.post_id = int(post_id)
            self.post = Post.get_by_id(self.post_id)
            context['page_path'] = '/post/'+self.post.slug+'-'+str(self.post.key().id())+'/edit'
        except TypeError:
            self.post_id = 0
            context['page_path'] = '/post/add'
        self.form = self.form_class()
        if action == 'edit':
            self.form.get('title').value = self.post.title
            self.form.get('body').value = self.post.body
            self.form.get('active').value = self.post.active
    @admin_perm_required
    def GET(self, post_id=None, action='add'):
        self.init_data(post_id, action)
        context['form'] = self.form
        return render_template('add.html', **context)
    @admin_perm_required
    def POST(self, post_id=None, action='add'):
        self.init_data(post_id, 'update') #switch to "update" and lose "edit" state
        form = self.form_class()
        if form.validates():
            active = True if form.get('active').value else False
            title = form.get('title').value
            body = form.get('body').value
            if action == 'edit':
                post_data = self.post
                post_data.title=title
                post_data.body=body
            else:
                post_data = Post(title=title,
                                 body=body,)
            post_data.active=active
            post_data.put()

            return web.seeother('/post/'+post_data.slug+'-'+str(post_data.key().id()), absolute=True)

        context['form'] = form
        return render_template('add.html', **context)


class view:

    def init_data(self, slug, post_id):
        try:
            self.post_id = int(post_id)
        except TypeError:
            self.post_id = 0
        self.post = Post.get_by_id(self.post_id)
        context['post'] = self.post
    def GET(self, slug, post_id):
        self.init_data(slug, post_id)
        return render_template('view.html', **context)
    def POST(self, slug, post_id):
        self.init_data(slug, post_id)
        return web.seeother('/post/'+self.post.slug+'-'+str(self.post.key().id()), absolute=True)

class feed:
    def GET(self):
        import PyRSS2Gen as RSS2

        posts = Post.all().filter('active =', True).order('-datetime')
        items = list()
        for post in posts:
            link = SITE_URL+'/post/'+post.slug+'-'+str(post.key().id())
            items.append(
                RSS2.RSSItem(
                    title = post.title,
                    link = link,
                    description = post.body.split('\n')[0],
                    guid = RSS2.Guid(link),
                    pubDate = post.datetime))
            
            rss = RSS2.RSS2(
                title = "Sibande's feed",
                link = SITE_URL,
                description = "Random thoughs by Sibande_",
                lastBuildDate = datetime.datetime.now(),
                
                items = items)

        return rss.to_xml();
    def POST(self):
        return web.seeother('/', absolute=True)
        

class static_content:

    def init_data(self, name, action):
        self.content = Static.all().filter('name =', name).get()
        self.form_class = static_form
        form = self.form_class()
        if not self.content or action == 'edit':
            if not context['google_accounts'].get_current_user():
                raise web.notfound()
            context['form'] = form()
            context['add_or_edit'] = True
        else:
            context['add_or_edit'] = False
            context['content'] = self.content
        context['page_path'] = '/'+name
        if action == 'edit':
            form = form()
            form.get('position').value = self.content.position
            form.get('name').value = self.content.name
            form.get('label').value = self.content.label
            form.get('title').value = self.content.title
            form.get('content').value = self.content.content
            form.get('active').value=self.content.active
            context['form'] = form

    def GET(self, name, action='view'):
        self.init_data(name, action)
        return render_template('static_content.html', **context)
    @admin_perm_required
    def POST(self, name, action='view'):
        self.init_data(name, action)
        form = self.form_class()
        if form.validates():
            active = True if form.get('active').value else False
            if not self.content:
                static_data = Static(position=int(form.get('position').value),
                                     name=form.get('name').value.lstrip('/'),
                                     label=form.get('label').value,
                                     title=form.get('title').value,
                                     content=form.get('content').value,
                                     active=active,)
            else:
                self.content.position=int(form.get('position').value)
                self.content.name=form.get('name').value.lstrip('/')
                self.content.label=form.get('label').value
                self.content.title=form.get('title').value
                self.content.content=form.get('content').value
                self.content.active=active
                static_data = self.content
            static_data.put()
            return web.seeother('/'+static_data.name, absolute=True)
        context['form'] = form
        return render_template('static_content.html', **context)

def notfound():
    return web.notfound(render_template('404.html', **context))
    
def internalerror():
    return web.internalerror(render_template('500.html', **context))

#urls
mapper = ('/', 'index',
          '/post/add', 'add_edit',
          '/post/(.*)-(\d+)', 'view',
          '/post/.*-(\d+)/(edit)', 'add_edit',
          '/blog/feeds', 'feed',
          '/(\w+)/(edit)', 'static_content',
          '/(\w+)', 'static_content',)
    
def default_loadhook():
    web.google_accounts = users
    context['google_accounts'] = users
    
    context['static_pages'] = Static.all().filter('position <', 15)\
        .filter('active =', True).order('position')

app = web.application(mapper, globals())
app.notfound = notfound
app.internalerror = internalerror
app.add_processor(web.loadhook(default_loadhook))

if __name__ == "__main__":
    main = app.cgirun()
    
