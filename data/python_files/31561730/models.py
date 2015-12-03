import copy
import hashlib
from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from . import _registry
from .managers import RevisionManager
from .utils import dmp, diff_split_by_fields


class Revision(models.Model):
    """
    A single revision for an object.
    """
    object_id = models.CharField(max_length=255, db_index=True)
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey("content_type", "object_id")

    revision = models.IntegerField(_(u"Revision Number"), db_index=True)
    reverted = models.BooleanField(_(u"Reverted Revision"), default=False,
                                   db_index=True)
    sha1 = models.CharField(max_length=40, db_index=True)
    delta = models.TextField()

    created_at = models.DateTimeField(_(u"Created at"), default=datetime.now,
                                      db_index=True)
    comment = models.CharField(_(u"Editor comment"), max_length=255,
                               blank=True)

    editor = models.ForeignKey(User, verbose_name=_(u'Editor'),
                               blank=True, null=True)
    editor_ip = models.IPAddressField(_(u"IP Address of the Editor"),
                                      blank=True, null=True)

    objects = RevisionManager()

    class Meta:
        verbose_name = _(u'Revision')
        verbose_name_plural = _(u'Revisions')
        get_latest_by = 'created_at'
        ordering = ('-revision',)
        unique_together = (("object_id", "content_type", "revision"),)

    def __unicode__(self):
        return u"r{0} {1} {2}".format(self.revision, self.sha1,
                                      self.content_object)

    def save(self, *a, **kw):
        """ Saves the article with a new revision.
        """
        self.sha1 = hashlib.sha1(
            unicode(self.delta).encode("utf-8")
        ).hexdigest()
        if self.id is None:
            try:
                self.revision = Revision.objects.get_for_object(
                    self.content_object
                ).latest().revision + 1
            except self.DoesNotExist:
                self.revision = 1
        super(Revision, self).save(*a, **kw)

    def is_anonymous_change(self):
        """Returns True if editor is not authenticated."""
        return self.editor is None

    def reapply(self, editor_ip=None, editor=None):
        """
        Returns the Content object to this revision.
        """
        # Exclude reverted revisions?
        next_changes = Revision.objects.get_for_object(
            self.content_object
        ).filter(
            revision__gt=self.revision
        ).order_by('-revision')

        content_object = self.content_object

        model = self.content_object.__class__
        fields = _registry[model]
        for changeset in next_changes:
            diffs = diff_split_by_fields(changeset.delta)
            for key, diff in diffs.iteritems():
                model2, field = key.split('.')
                if model2 != model.__name__ or field not in fields:
                    continue
                content = getattr(content_object, field)
                patch = dmp.patch_fromText(diff)
                content = dmp.patch_apply(patch, content)[0]
                setattr(content_object, field, content)
            changeset.reverted = True
            changeset.save()

        content_object.revision_info = {
            'comment': u"Reverted to revision #%s" % self.revision,
            'editor_ip': editor_ip,
            'editor': editor
        }
        content_object.save()
        #self.save()

    def display_diff(self):
        """Returns a HTML representation of the diff."""
        # well, it *will* be the old content
        old = copy.copy(self.content_object)

        # newer non-reverted revisions of this content_object,
        # starting from this
        if not self.delta:
            return u""
        newer_changesets = Revision.objects.get_for_object(
            self.content_object
        ).filter(revision__gte=self.revision)

        model = self.content_object.__class__
        fields = _registry[model]
        # apply all patches to get the content of this revision
        for i, changeset in enumerate(newer_changesets):
            diffs = diff_split_by_fields(changeset.delta)
            if len(newer_changesets) == i + 1:
                # we need to compare with the next revision
                # after the change
                next_rev = copy.copy(old)
            for key, diff in diffs.iteritems():
                model2, field = key.split('.')
                if model2 != model.__name__ or field not in fields:
                    continue
                patches = dmp.patch_fromText(diff)
                setattr(old, field,
                        dmp.patch_apply(patches,
                                        getattr(old, field))[0])

        result = []
        for field in fields:
            result.append(u"<b>{0}</b>".format(field))
            diffs = dmp.diff_main(getattr(old, field),
                                  getattr(next_rev, field))
            result.append(dmp.diff_prettyHtml(diffs))
        return u"<br />\n".join(result)
