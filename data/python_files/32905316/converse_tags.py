import datetime
import hashlib
from django import template
from django.utils.timesince import timesince
from django.utils.html import escape
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify

register = template.Library()

@register.filter
def reltime(date):
    """ Show relative time only for newish dates. Otherwise, show absolute """
    delta = datetime.datetime.today() - date
    if delta.days == 0:
        return timesince(date) + ' ago'
    else:
        return date.strftime('%Y-%m-%d %I:%M %p')

@register.simple_tag
def profile(user):
    return """<a class="username" href="%(url)s" title="View profile for %(username)s">%(username)s</a>""" % {
            'url': reverse('converse.views.user', args=(user.id, slugify(user.username))),
            'username': escape(user.username),
        }

@register.simple_tag
def gravatar(user):
    gravatar_url =  'http://www.gravatar.com/avatar/%s?d=identicon&size=60' % hashlib.md5(user.email.lower()).hexdigest()
    return """<img src="%(url)s" width="60px" height="60px" alt="%(username)s's gravatar" class="avatar" />""" % {
        'username': escape(user.username),
        'url': gravatar_url,
    }

@register.simple_tag
def new(item, user):
    if not user.is_authenticated():
        return ''
    return 'new' if item.has_new(user) else ''
