import hashlib
from markdown import markdown
from textile import textile
from docutils.core import publish_parts

from django.db import models
from django.core.cache import cache
from django.conf import settings
from django.utils.safestring import mark_safe
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.contrib.syndication.views import add_domain
from tagging.models import Tag
from tagging.fields import TagField

# imports specific to django tree menus
from itertools import chain
from django.utils.translation import ugettext_lazy, ugettext as _

REDIRECT_CHOICES = (
    ("P", "Permanent"),
    ("T", "Temporary"),
)

SITEMAP_CHANGE_FREQ = (
    ("A", "Always"),
    ("H", "Hourly"),
    ("D", "Daily"),
    ("W", "Weekly"),
    ("M", "Monthly"),
    ("Y", "Yearly"),
    ("N", "Never"),
)

SITEMAP_PRIORITY = (
    (0.0, "0.0"),
    (0.1, "0.1"),
    (0.2, "0.2"),
    (0.3, "0.3"),
    (0.4, "0.4"),
    (0.5, "0.5"),
    (0.6, "0.6"),
    (0.7, "0.7"),
    (0.8, "0.8"),
    (0.9, "0.9"),
    (1.0, "1.0"),
)

EDITOR_TYPE = (
    ("H", "HTML (WYSIWYG)"),
    ("R", "HTML (Raw)"),
    ("M", "Markdown"),
    ("T", "Textile"),
    ("S", "reStructuredText"),
)

USER_TYPE = (
    ("E", "Everybody"),
    ("A", "Anonymous Only"),
    ("L", "Logged In"),
    ("S", "Staff"),
    ("X", "Superuser"),
)

class StaticPage(models.Model):
    """
    The StaticPage model holds a static HTML page for the cms application. It
    is much like Django's django.contrib.flatpages.FlatPage model, except that
    it uses a WYSIWYG editor (TinyMCE) in the place of a plain text editor, and
    also supports Markdown, Textile and reStructuredText.  It also supports
    more fields for defining different areas of the page, such as the sidebar,
    header and footer.

    You can also choose a different base template on a per-page basis, which
    defaults to 'static/default.html' if left blank.  Some of the template
    variables you can use are {{ page.main }}, {{ page.left }},
    {{ page.right }}, {{ page.header }} and {{ page.footer }}.  HTML template
    variables are escaped and rendered content such as Markdown is cached for
    speed before it is sent to the template layer.
    """
    url = models.CharField("URL", max_length=255, db_index=True, unique=True, help_text="Example: '/about/contact/', must have leading and trailing slashes and no spaces (will be automatically corrected if not).")
    title = models.CharField("Title", max_length=255, blank=True, null=True)
    editor = models.CharField(max_length=1, choices=EDITOR_TYPE, default="H")
    main = models.TextField("Main content", blank=True)
    header = models.TextField("Header", blank=True)
    left = models.TextField("Left sidebar", blank=True)
    right = models.TextField("Right sidebar", blank=True)
    footer = models.TextField("Footer", blank=True)
    css = models.TextField("Additional CSS", blank=True, help_text="Additional CSS styles for this page.")
    template = models.CharField("Template", max_length=255, blank=True, help_text="Override the default template for this page, default is 'static/default.html'.")
    user_type = models.CharField(max_length=1, choices=USER_TYPE, default="E", help_text="Users able to view this page.")
    groups = models.ManyToManyField(Group, verbose_name="Groups", related_name="staticpage", null=True, blank=True, help_text="Groups that can view this page (leave blank for all groups).")
    published = models.BooleanField(default=True)
    created = models.DateTimeField("Date created", auto_now_add=True, editable=False)
    modified = models.DateTimeField("Date modified", auto_now=True, editable=False)
    tags = TagField(help_text="Tags for this page, separated by either commas or spaces.")

    rendered = {
       "main": None,
       "header": None,
       "left": None,
       "right": None,
       "footer": None,
       "css": None,
    }

    class Meta:
        ordering = ("title",)

    def __unicode__(self):
        """
        Called when you print a page object or convert it to a string.
        """
        return self.title_col()

    def get_absolute_url(self):
        """
        Returns the full URL of the page, adds a "view on site" button
        to admin.
        """
        domain = Site.objects.get(pk=settings.SITE_ID).domain
        return add_domain(domain, self.url)

    def template_col(self):
        """
        Helper method that returns either the template name if present,
        otherwise it returns the text "(Default)".  Used for prettifying the
        template column in list view in admin.
        """
        return self.template or "(Default)"
    template_col.short_description = "Template"

    def title_col(self):
        """
        Helper method that returns either the page title if present, otherwise
        it returns the text "(Untitled Page)".  Used for prettifying the
        title column in list view in admin.
        """
        return self.title or "(Untitled Page)"
    title_col.short_description = "Title"

    def groups_col(self):
        """
        Helper method that returns either a comma separated list of the
        groups that can access this page (as a single string), otherwise
        it returns the text "(No Groups)".  Used for prettifying the groups
        column in list view in admin.
        """
        return ", ".join([str(group) for group in self.groups.all()]) or "(No Groups)"
    groups_col.short_description = "Groups"

    def tags_col(self):
        """
        Helper method that returns a comma separated list of the tags for this
        page (as a single string).  Used for prettifying the tags column in
        list view in admin.
        """
        return ", ".join([tag.name for tag in Tag.objects.get_for_object(self)])
    tags_col.short_description = "Tags"

    def save(self, **kwargs):
        """
        The main reason to override the save method, is to call render()
        so we render the content to html on save and cache it.  Although
        in the view the page will also be cached if needed, it is also
        nice to do it here, after a user has edited a page.
        """
        if not self.url.endswith("/"):
            self.url += "/"
        if not self.url.startswith("/"):
            self.url = "/" + self.url
        super(StaticPage, self).save(**kwargs)
        cache.delete("static_page_%s" % hashlib.md5(settings.SECRET_KEY + str(self.id)).hexdigest())  # delete old page from cache so render() recreates it.
        self.render()

    def render(self):
        """
        Render content fields to html, required for Markdown, Textile and
        reStructuredText.  Also takes care of caching rendered conent.
        For use, see views.py.
        """
        cached = cache.get("static_page_%s" % hashlib.md5(settings.SECRET_KEY + str(self.id)).hexdigest())
        if cached:
            self.rendered = cached
        else:
            if self.editor == "M":
                self.rendered["main"] = mark_safe(markdown(self.main))
                self.rendered["header"] = mark_safe(markdown(self.header))
                self.rendered["left"] = mark_safe(markdown(self.left))
                self.rendered["right"] = mark_safe(markdown(self.right))
                self.rendered["css"] = mark_safe(self.css)
            elif self.editor == "T":
                # textile doesn't like unicode strings, so we must convert to a string first
                self.rendered["main"] = mark_safe(textile(str(self.main)))
                self.rendered["header"] = mark_safe(textile(str(self.header)))
                self.rendered["left"] = mark_safe(textile(str(self.left)))
                self.rendered["right"] = mark_safe(textile(str(self.right)))
                self.rendered["css"] = mark_safe(self.css)
            elif self.editor == "S":
                overrides = {"file_insertion_enabled": 0, "raw_enabled": 0}
                parts = publish_parts(source=self.main, settings_overrides=overrides, writer_name="html")
                self.rendered["main"] = mark_safe(parts["html_body"])
                self.rendered["css"] = mark_safe(self.rendered["css"] + parts["stylesheet"])  # extra css generated by docutils
                parts = publish_parts(source=self.left, settings_overrides=overrides, writer_name="html")
                self.rendered["left"] = mark_safe(parts["html_body"])
                parts = publish_parts(source=self.right, settings_overrides=overrides, writer_name="html")
                self.rendered["right"] = mark_safe(parts["html_body"])
                parts = publish_parts(source=self.header, settings_overrides=overrides, writer_name="html")
                self.rendered["header"] = mark_safe(parts["html_body"])
                parts = publish_parts(source=self.footer, settings_overrides=overrides, writer_name="html")
                self.rendered["footer"] = mark_safe(parts["html_body"])
            else:
                self.rendered["main"] = mark_safe(self.main)
                self.rendered["header"] = mark_safe(self.header)
                self.rendered["left"] = mark_safe(self.left)
                self.rendered["right"] = mark_safe(self.right)
                self.rendered["css"] = mark_safe(self.css)
            cache.set("static_page_%s" % hashlib.md5(settings.SECRET_KEY + str(self.id)).hexdigest(), self.rendered)

# models specific to django tree menus follow

class MenuItem(models.Model):
    parent = models.ForeignKey("self", verbose_name=ugettext_lazy("Parent"), null=True, blank=True)
    caption = models.CharField(ugettext_lazy("Caption"), max_length=50)
    url = models.CharField(ugettext_lazy("URL"), max_length=200, blank=True)
    named_url = models.CharField(ugettext_lazy("Named URL"), max_length=200, blank=True)
    level = models.IntegerField(ugettext_lazy("Level"), default=0, editable=False)
    rank = models.IntegerField(ugettext_lazy("Rank"), default=0, editable=False)
    menu = models.ForeignKey("Menu", related_name="contained_items", verbose_name=ugettext_lazy("Menu"), null=True, blank=True, editable=False)
    static_page = models.ForeignKey(StaticPage, related_name="menu_items", verbose_name=ugettext_lazy("Static page"), null=True, blank=True)
    user_type = models.CharField(max_length=1, choices=USER_TYPE, default="E", help_text="Users able to view this menu item.")
    groups = models.ManyToManyField(Group, verbose_name="Groups", related_name="menu_items", null=True, blank=True, help_text="Groups that can see this menu item (leave blank for all groups).")

    def __unicode__(self):
        return self.caption

    def save(self, force_insert=False, **kwargs):
        from rvcms.cms.utils import clean_ranks

        # Calculate level
        old_level = self.level
        if self.parent:
            self.level = self.parent.level + 1
        else:
            self.level = 0

        if self.pk:
            new_parent = self.parent
            old_parent = MenuItem.objects.get(pk=self.pk).parent
            if old_parent != new_parent:
                # If so, we need to recalculate the new ranks for the item and its siblings (both old and new ones).
                if new_parent:
                    clean_ranks(new_parent.children()) # Clean ranks for new siblings
                    self.rank = new_parent.children().count()
                super(MenuItem, self).save(force_insert, **kwargs) # Save menu item in DB. It has now officially changed parent.
                if old_parent:
                    clean_ranks(old_parent.children()) # Clean ranks for old siblings
            else:
                super(MenuItem, self).save(force_insert, **kwargs) # Save menu item in DB

        else: # Saving the menu item for the first time (i.e creating the object)
            if not self.has_siblings():
                # No siblings - initial rank is 0.
                self.rank = 0
            else:
                # Has siblings - initial rank is highest sibling rank plus 1.
                siblings = self.siblings().order_by('-rank')
                self.rank = siblings[0].rank + 1
            super(MenuItem, self).save(force_insert, **kwargs)

        # If level has changed, force children to refresh their own level
        if old_level != self.level:
            for child in self.children():
                child.save() # Just saving is enough, it'll refresh its level correctly.

    def delete(self):
        from rvcms.cms.utils import clean_ranks
        old_parent = self.parent
        super(MenuItem, self).delete()
        if old_parent:
            clean_ranks(old_parent.children())

    def caption_with_spacer(self):
        spacer = ""
        for i in range(0, self.level):
            spacer += u"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        if self.level > 0:
            spacer += u"|-&nbsp;"
        return spacer + self.caption

    def get_flattened(self):
        flat_structure = [self]
        for child in self.children():
            flat_structure = chain(flat_structure, child.get_flattened())
        return flat_structure

    def siblings(self):
        if not self.parent:
            return MenuItem.objects.none()
        else:
            if not self.pk: # If menu item not yet been saved in DB (i.e does not have a pk yet)
                return self.parent.children()
            else:
                return self.parent.children().exclude(pk=self.pk)

    def has_siblings(self):
        return self.siblings().count() > 0

    def children(self):
        _children = MenuItem.objects.filter(parent=self).order_by("rank",)
        for child in _children:
            child.parent = self # Hack to avoid unnecessary DB queries further down the track.
        return _children

    def has_children(self):
        return self.children().count() > 0

class Menu(models.Model):
    name = models.CharField(ugettext_lazy("Name"), max_length=50)
    root_item = models.ForeignKey(MenuItem, related_name="is_root_item_of", verbose_name=ugettext_lazy('Root Item'), null=True, blank=True, editable=False)

    def save(self, force_insert=False, **kwargs):
        if not self.root_item:
            root_item = MenuItem()
            root_item.caption = _("Root")
            if not self.pk: # If creating a new object (i.e does not have a pk yet)
                super(Menu, self).save(force_insert, **kwargs) # Save, so that it gets a pk
                force_insert = False
            root_item.menu = self
            root_item.save() # Save, so that it gets a pk
            self.root_item = root_item
        super(Menu, self).save(force_insert, **kwargs)

    def delete(self):
        if self.root_item is not None:
            self.root_item.delete()
        super(Menu, self).delete()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _("Menu")
        verbose_name_plural = _("Menus")
