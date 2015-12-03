import re
from datetime import datetime

from BeautifulSoup import BeautifulSoup
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.contrib.syndication.views import add_domain
from django.utils.safestring import mark_safe
from tagging.models import Tag
from tagging.fields import TagField

BLOG_READMORE_CAPTION = getattr(settings, "BLOG_READMORE_CAPTION", "Read More...")
BLOG_USE_FEED_INTRO = getattr(settings, "BLOG_USE_FEED_INTRO", True)
BLOG_USE_BLOG_INTRO = getattr(settings, "BLOG_USE_BLOG_INTRO", True)

FIND_MORE = re.compile("(<[^>]>)?(<!--[\s]*pagebreak[\s]*-->)(</[^>]>)?")
RELATIVE_LINKS = re.compile('href="/')
RELATIVE_MEDIA = re.compile('src="/')

class Category(models.Model):
    name = models.CharField(max_length=128)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ("name",)

    def __unicode__(self):
        return self.name

class Post(models.Model):
    author = models.ForeignKey(User)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    body = models.TextField(help_text="Use the page break button, to insert a 'Read More...' link.")
    pub_date = models.DateTimeField("Date", default=datetime.now)
    published = models.BooleanField(default=True)
    categories = models.ManyToManyField(Category, related_name="post", blank=True)
    tags = TagField(help_text="Tags for to this post, separated by either spaces or commas.")
    allow_comments = models.BooleanField(default=True)
    allow_trackbacks = models.BooleanField(default=True)
    allow_pingbacks = models.BooleanField(default=True)

    class Meta:
        ordering = ("title",)

    def categories_col(self):
        """
        Helper method that returns a comma separated list of the categories
        for this post (as a single string).  Used for prettifying the
        categories column in list view in admin.
        """
        return ", ".join([str(category) for category in self.categories.all()])
    categories_col.short_description = "Categories"

    def tags_col(self):
        """
        Helper method that returns a comma separated list of the tags for this
        post (as a single string).  Used for prettifying the tags column in
        list view in admin.
        """
        return ", ".join([tag.name for tag in Tag.objects.get_for_object(self)])
    tags_col.short_description = "Tags"

    def readmore_replace(self, match):
        openTag = match.group(1)
        closeTag = match.group(3)
        if openTag and closeTag is not None:
            return ""
        elif openTag is None:
            return closeTag
        else:
            return openTag

    def author_name(self):
        if self.author.first_name:
            return self.author.get_full_name()
        else:
            return str(self.author)

    def get_absolute_url(self):
        domain = Site.objects.get(pk=settings.SITE_ID).domain
        return add_domain(domain, reverse("blog-post", args=[self.slug]))

    def full_post(self):
        """
        Returns the full post, stripping the special <!-- pagebreak --> tag.
        """
        return mark_safe(FIND_MORE.sub(self.readmore_replace, self.body, 1))

    def intro(self, full_url=False):
        """
        Returns only the part before the <!-- pagebreak --> tag (intro).
        If the BLOG_READMORE_CAPTION settings variable is set, a hyperlink
        to the full post will be included. If full_url is True, the URL to
        the full post will contain the domain of the site as well. When
        full_url is False, it will be an URL without the domain.
        """
        pieces = FIND_MORE.split(self.body)
        post = pieces[0]
        if len(pieces) > 1:
            if pieces[3] is not None:
                # Fixes possible unclosed tags after splitting the HTML in two parts
                pieces[3] = BeautifulSoup(pieces[3]).prettify()
                post += pieces[3]
            if pieces[2] is not None:
                post += '<p><a href="' + reverse("blog-post", args=[self.slug]) + '">' + BLOG_READMORE_CAPTION + "</a></p>"
        return mark_safe(post)

    def get_feed_intro(self, request_url):
        """
        If BLOG_USE_FEED_INTRO is set to True, returns only the part before the
        <!-- pagebreak --> tag (intro), with a hyperlink to the remainder of the
        post.  If BLOG_USE_FEED_INTRO is False, returns the full post
        (but with the special <!-- pagebreak --> tag stripped).  Used by
        feeds.py.
        """
        if BLOG_USE_FEED_INTRO:
            content = self.intro(True)
        else:
            content = self.full_post()
        content = RELATIVE_LINKS.sub('href="%s/' % request_url, content)
        content = RELATIVE_MEDIA.sub('src="%s/' % request_url, content)
        return mark_safe(content)

    def get_blog_intro(self):
        """
        If BLOG_USE_BLOG_INTRO is set to True, only returns the part before the
        <!-- pagebreak --> tag (intro), with a hyperlink to the remainder of the
        post.  If BLOG_USE_BLOG_INTRO is False, returns the full post
        (but with the special <!-- pagebreak --> tag stripped).
        """
        if BLOG_USE_BLOG_INTRO:
            return mark_safe(self.intro())
        else:
            return mark_safe(self.full_post())

    def has_categories(self):
        return self.categories.count() > 0

    def __unicode__(self):
        return self.title
