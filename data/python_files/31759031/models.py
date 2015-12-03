import random
import re

from datetime import datetime
import urllib
import hashlib

from sqlalchemy.ext.declarative import AbstractConcreteBase
from flaskext.mail import Message

from flask import url_for, abort, render_template, g

from btnfemcol import db, cache, mail

from btnfemcol.utils import Hasher


class SiteEntity(object):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(120), unique=True, nullable=False)
    status = db.Column(db.String(255))
    order = db.Column(db.Integer)

    def __init__(self, title=None, slug=None, body=None, order=0,
        status='draft'):

        self.slug = slug
        self.title = title
        self.status = status
        self.order = order

    def __unicode__(self):
        return unicode(self.title)


class Displayable(SiteEntity):
    body = db.Column(db.Text, nullable=False)

    def __init__(self, body=None, *args, **kwargs):
        self.body = body
        super(Displayable, self).__init__(*args, **kwargs)

    @property
    @cache.memoize(60)
    def excerpt(self):
        if not self.body:
            return ''
        excerpt = self.body[:440]

        patterns = [
            r'!?\[(.*)\]\((.*)\)',
            r'\*',
            r'#(.+)',
        ]

        for pattern in patterns:
            excerpt = re.sub(pattern, '', excerpt)

        if len(excerpt) > 140:
            ellip = u'\u2026'
        else:
            ellip = ''

        return excerpt[:140] + ellip


class Category(SiteEntity, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    @property
    def url(self):
        top_cat = Category.query.filter_by(
            status='live').order_by(Category.order.asc()).first()
        if self == top_cat:
            return url_for('frontend.show_category')
        return url_for('frontend.show_category', category_slug=self.slug)


class Section(SiteEntity, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    @property
    @cache.memoize(20)
    def url(self):
        if self.slug == 'articles':
            top_cat = Category.query.filter_by(status='live').first()
            if top_cat:
                return top_cat.url

        db.session.add(self)
        first = self.pages.first()
        if not first:
            return '#'
        return self.pages.first().url

    def __repr__(self):
        return '<Section: %s>' % self.title

    def __unicode__(self):
        return self.title

    @classmethod
    def get_live(cls):
        return cls.query.filter_by(status='live') \
            .order_by(Section.order).all()


class Page(Displayable, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'))
    section = db.relationship('Section',
        backref=db.backref('pages', lazy='dynamic'), order_by='Page.order')

    def __init__(self, section=None, *args, **kwargs):

        if section:
            self.section = section

        super(Page, self).__init__(*args, **kwargs)

    @property
    @cache.memoize(300)
    def url(self):
        if self.slug == 'welcome' and self.section.slug == 'home':
            return url_for('frontend.home')

        elif self.section.pages.filter_by(status='live').first() == self:
            return url_for('frontend.show_section', slug=self.section.slug)
        
        return url_for('frontend.show_page',
            section_slug=self.section.slug,
            page_slug=self.slug)

    def __repr__(self):
        return '<Page: %r>' % self.title

    def __unicode__(self):
        return unicode(self.title)


    @property
    @cache.memoize(5)
    def json_dict(self, exclude=[]):
        """This is a form of serialisation but specifically for the output to
        JSON for asyncronous requests."""
        d = {
            'id': self.id,
            'title': '%s &mdash; %s' % (self.section.title, self.title),
            'urls': {
                'edit': url_for('admin.edit_page', id=self.id),
                'bin': '#',
                'view': self.url
            },
            'status': self.status
        }
        for key in exclude:
            del d[key]
        return d

tags = db.Table('tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')),
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'))
)
 
class Article(Displayable, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User',
        backref=db.backref('articles', lazy='dynamic'),
        order_by='Article.pub_date.desc()')
    pub_date = db.Column(db.DateTime)
    subtitle = db.Column(db.Text)
    revision = db.Column(db.Integer)

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category',
        backref=db.backref('articles', lazy='dynamic'),
        order_by='Article.pub_date.desc()')

    tags = db.relationship('Tag', secondary=tags, 
        backref=db.backref('articles', lazy='dynamic'))

    def __init__(self, pub_date=None, author=None, subtitle=None,
        category=None, *args, **kwargs):

        if pub_date is None:
            pub_date = datetime.utcnow()
        self.pub_date = pub_date
        self.author = author
        self.subtitle = subtitle
        self.category = category
        super(Article, self).__init__(*args, **kwargs)

    @property
    @cache.memoize(300)
    def url(self):
        return url_for('frontend.show_article',
            category_slug=self.category.slug,
            article_slug=self.slug
        )

    @property
    @cache.memoize(5)
    def json_dict(self, exclude=[]):
        """This is a form of serialisation but specifically for the output to
        JSON for asyncronous requests."""
        d = {
            'id': self.id,
            'title': self.title,
            'revision': self.revision,
            'pub_date': self.pub_date.strftime('%c'),
            'urls': {
                'edit': url_for('admin.edit_article', id=self.id),
                'bin': '#'
            },
            'status': self.status,
            'author': {
                'username': self.author.username,
                'fullname': '%s %s' % (self.author.firstname, self.author.surname),
                'url': url_for('admin.edit_user', id=self.author.id)
            }
        }
        for key in exclude:
            del d[key]
        return d


class Event(Displayable, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)
    location = db.Column(db.String(255))

    def __init__(self, start=None, end=None, location=None, *args, **kwargs):
        if start is None:
            start = datetime.utcnow()
        if end is None:
            end = datetime.utcnow()
        self.start = start
        self.end = end
        self.location = location
        super(Event, self).__init__(*args, **kwargs)

    @property
    @cache.memoize(300)
    def url(self):
        return url_for('frontend.show_event', slug=self.slug)

    @property
    @cache.memoize(5)
    def json_dict(self, exclude=[]):
        """This is a form of serialisation but specifically for the output to
        JSON for asyncronous requests."""
        d = {
            'id': self.id,
            'title': self.title,
            'start': self.start.strftime('%B %d, %Y at %H%M'),
            'end': self.end.strftime('%B %d, %Y at %H%M'),
            'location': self.location,
            'urls': {
                'edit': url_for('admin.edit_event', id=self.id),
                'bin': '#'
            },
            'status': self.status
        }
        for key in exclude:
            del d[key]
        return d


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255), nullable=False)
    firstname = db.Column(db.String(80), nullable=False)
    location = db.Column(db.String(80))
    surname = db.Column(db.String(80), nullable=False)
    website = db.Column(db.String(255))
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(80))
    twitter = db.Column(db.String(80))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    group = db.relationship('Group',
        backref=db.backref('users', lazy='dynamic'))
    status = db.Column(db.String(10))
    reg_code = db.Column(db.String(255))

    def __init__(self, group=None, username=None, email=None, firstname=None,
        surname=None, password=None, website=None, phone=None, twitter=None,
        status='pending',
        *args, **kwargs):
        
        if password:
            h = Hasher()
            self.password = h.hash(password)

        if not group:
            group = Group.query.filter_by(name='User').first()

        self.username = username
        self.firstname = firstname
        self.surname = surname
        self.email = email
        self.group = group
        self.group_id = group.id
        self.website = website
        self.twitter = twitter
        self.phone = phone
        self.status = status
        super(User, self).__init__(*args, **kwargs)

#    @cache.memoize(20)
    def allowed_to(self, name):
        """This will check if a user can do a certain action."""
        if self.status != 'active':
            return False
        permission = Permission.query.filter_by(name=name).first()
        return permission in self.group.permissions.all()

    def send_activation_email(self):
        """Send the e-mail that allows a user to activate their account."""
        if not self.reg_code:
            self._gen_reg_code()
            db.session.commit()

        msg = Message("Account Activation",
            recipients=[self.email])

        print self.reg_code
        activate_url = url_for('frontend.activate', user_id=self.id,
            reg_code=self.reg_code, _external=True)
        msg.html = render_template('email_activate.html', user=self,
            activate_url=activate_url)
        msg.body = render_template('email_activate.txt', user=self,
            activate_url=activate_url)
        mail.send(msg)


    def _gen_reg_code(self):
        chrs = list(
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890')
        
        string = ''
        for i in range(20):
            string += random.choice(chrs)
        self.reg_code = string
    
    @property
    @cache.memoize(20)
    def gravatar_url(self, size=100):
        size = int(size)
        default = url_for('static', filename='images/av_def_%s.png' % size)
        gravatar_url = "http://www.gravatar.com/avatar/" + \
            hashlib.md5(self.email.lower()).hexdigest() + "?"
        gravatar_url += urllib.urlencode({
            'd': default,
            's': str(size)
        })
        return gravatar_url


    @property
    @cache.memoize(60)
    def displayed_name(self):
        return unicode(self.username)

    @property
    @cache.memoize(60)
    def fullname(self):
        return u'%s %s' % (self.firstname, self.surname)

    def __repr__(self):
        return '<User %r>' % self.username

    @cache.memoize(5)
    def __unicode__(self):
        return '%s (%s) <%s>' % (
            self.fullname,
            self.username,
            self.email
        )

    @property
    @cache.memoize(300)
    def url(self):
        return '#'

    @property
    @cache.memoize(5)
    def json_dict(self, exclude=[]):
        """This is a form of serialisation but specifically for the output to
        JSON for asyncronous requests."""
        d = {
            'id': self.id,
            'username': self.username,
            'firstname': self.firstname,
            'surname': self.surname,
            'location': self.location,
            'website': self.website,
            'twitter': self.twitter,
            'group': self.group.name,
            'status': self.status,
            'urls': {
                'edit': url_for('admin.edit_user', id=self.id),
                'bin': '#'
            }
        }
        for key in exclude:
            del d[key]
        return d


permissions = db.Table('permissions',
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'))
)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True)

    def __init__(self, name=None):
        self.name = name
    
    @cache.memoize(6000)
    def __unicode__(self):
        return u'%s' % self.name

    def __repr__(self):
        return '<Group %r>' % self.name


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True)
    title = db.Column(db.String(255))

    groups = db.relationship('Group', secondary=permissions,
        backref=db.backref('permissions', lazy='dynamic'))

    def __init__(self, name, title):
        self.name = name
        self.title = title
    
    def __repr__(self):
        return '<Permission %s:%r>' % (self.id, self.name)

class LogEntry(db.Model):
    __tablename__ = 'log_entry'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subject = db.relationship('User',
        backref=db.backref('actions', lazy='dynamic'))
    target_id = db.Column(db.Integer)
    verb = db.Column(db.String(255))
    when = db.Column(db.DateTime)
    class_name = db.Column(db.String(127))

    def __init__(self, verb, subject=None, class_name=None, target=None):
        if not subject:
            subject = g.user
        self.subject = subject
        self.verb = verb
        self.when = datetime.utcnow()
        self.class_name = class_name
        if target:
            self.class_name = target.__class__.__name__
            self.target_id = target.id


    @classmethod
    def log(cls, *args, **kwargs):
        log_entry = cls(*args, **kwargs)
        db.session.add(log_entry)
        try:
            db.session.commit()
        except Exception as e:            
            current_app.logger.critical(e)
            db.session.rollback()

    def __repr__(self):
        return '<LogEntry %s>' % self.id

    def __unicode__(self, date=True):
        if date:
            string = '[%s] ' % self.when
        else:
            string = ''

        if not self.subject_id:
            subject_name = "(not attributed)"
        else:
            subject_name = self.subject.username

        string += '%(subject)s %(verb)s' % {
            'when': self.when,
            'subject': subject_name,
            'verb': self.verb
        } 

        if self.target_id:
            string += ' %s #%s' % (self.class_name, self.target_id)
        return string


    @property
#    @cache.memoize(500)
    def json_dict(self, exclude=[]):
        """This is a form of serialisation but specifically for the output to
        JSON for asyncronous requests."""

        if not self.subject_id:
            subject_url = '#'
        else:
            subject_url = self.subject.url

        d = {
            'id': self.id,
            'entry': self.__unicode__(date=False),
            'when' : self.when.strftime('%Y/%m/%d %H:%m:%S'),
            'urls': {
                'user': subject_url
            }
        }
        for key in exclude:
            del d[key]
        return d