import hashlib
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import models
import admin.model as admin
import markdown
import markdown.inline
import markdown.html
import markdown.entire_doc

def escape_content(content):
    return ''.join(markdown.entire_doc.forge(content.split('\n')))

def escape_title(title):
    return markdown.inline.forge(markdown.html.escape(title))

def escape_preview(content):
    return ''.join(markdown.entire_doc.generate_preview(content.split('\n'),
                                                        1729))

def post_for_client(post):
    post.title = escape_title(post.title)
    post.preview = escape_preview(post.content)
    post.content = escape_content(post.content)
    return post

def posts_for_client(origin_posts):
    return map(lambda p: post_for_client(p), origin_posts)

def comments_for_client(comments):
    def forge_inline(text):
        from markdown.inline import esc_back_slash, img, sub, sup, italic, bold
        from markdown.inline import monospace
        return esc_back_slash(
            img(sub(sup(italic(bold(monospace(markdown.html.forge(text))))))))
    def client_comment(c):
        c.email_md5 = hashlib.md5(c.email).hexdigest()
        c.content = '<br>'.join(forge_inline(c.content).split('\n'))
        return c
    return [client_comment(c) for c in comments]

class BaseView(webapp.RequestHandler):
    def get(self):
        raise_not_found(self)

    def request_value(self, key, wanted_type):
        try:
            return wanted_type(self.request.get(key))
        except ValueError:
            return wanted_type()

    def post(self):
        raise_not_found(self)

    def put_page(self, template_file, template_value=dict()):
        import os
        usr = admin.User.get_by_session(self.request)
        template_value['usr'] = usr
        template_value['style'] = 'midnight'
        path = os.path.join(os.path.dirname(__file__), template_file)
        self.response.out.write(template.render(path, template_value))

class NotFound(BaseView):
    pass

def raise_not_found(view):
    view.error(404)
    view.put_page('templates/notfound.html', {
            'posts': posts_for_client(models.post.fetch(0, 5)),
        })

def raise_forbidden(view):
    view.error(403)
    view.put_page('templates/forbidden.html', {
            'posts': posts_for_client(models.post.fetch(0, 5)),
        })

class About(BaseView):
    def get(self):
        self.put_page('templates/about.html')
