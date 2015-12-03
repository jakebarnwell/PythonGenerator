import re
import os
from datetime import datetime

from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ValidationError

from picklefield.fields import PickledObjectField

from irgsh_web.repo.models import Distribution as RepoDistribution
from irgsh_web.repo.models import Package as RepoPackage
from irgsh_web.repo.models import Architecture

SOURCE = 0
BINARY = 1

TARBALL = 'tarball'
BZR = 'bzr'
PATCH = 'patch'

SPECIFICATION_STATUS = (
    ( -2, _('Rejected')),
    ( -1, _('Failed')),
    (  0, _('Waiting for initialization')),
    (100, _('Initializing build specification')),
    (101, _('Downloading source file')),
    (102, _('Downloading orig file')),
    (103, _('Building source package')),
    (104, _('Build task distributed')),
    (105, _('Building packages')),
    (200, _('Building repository')),
    (999, _('Finished')),
)

BUILD_TASK_STATUS = (
    ( -2, _('Cancelled')),
    ( -1, _('Failed')),
    (  0, _('Waiting for builder')),
    (100, _('Preparing builder')),
    (101, _('Downloading source file')),
    (102, _('Downloading orig file')),
    (103, _('Building package')),
    (104, _('Package built')),
    (201, _('Uploading package')),
    (202, _('Package uploaded')),
    (999, _('Finished')),
)

PACKAGE_CONTENT_TYPE = (
    (SOURCE, _('Source')),
    (BINARY, _('Binary')),
)

SOURCE_TYPE = (
    (TARBALL, _('Tarball')),
    (BZR, _('Bazaar Repository')),
    (PATCH, _('Diff/Patch')),
)

WORKER_TYPES = (
    (1, _('Task Init Worker')),
    (2, _('Repository Builder')),
    (3, _('Upload Handler')),
)

# TODO ORIG_FORMATS = '(gz|bz2|lzma|xz)'
ORIG_FORMATS = '(gz)'
re_orig = re.compile(r'.+\.orig\.tar\.%s$' % ORIG_FORMATS)
re_orig_extra = re.compile(r'.+\.orig-[a-z0-9-]+\.tar\.%s$' % ORIG_FORMATS)

class Distribution(models.Model):
    '''
    List of distributions, e.g. ombilin, ombilin-updates, pattimura, etc
    '''
    repo = models.ForeignKey(RepoDistribution, unique=True)
    active = models.BooleanField(default=True)

    mirror = models.CharField(max_length=255,
                              help_text=_('e.g. http://arsip.blankonlinux.or.id/blankon/'))
    dist = models.CharField(max_length=50,
                            help_text=_('e.g. ombilin, pattimura, etc'))
    components = models.CharField(max_length=255,
                                  help_text=_('e.g. main universe. Separate multiple components by a space'))
    extra = models.TextField(blank=True, default='',
                             verbose_name=_('Additional repositories'),
                             help_text=_('Use sources.list syntax'))

    def __unicode__(self):
        return unicode(self.name())

    def name(self):
        return self.repo.name

class WorkerBase(models.Model):
    '''
    Base class for all workers
    '''
    name = models.SlugField(max_length=50, unique=True)
    active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(null=True, default=None, blank=True)
    cert_subject = models.CharField(max_length=1024, unique=True,
                                    verbose_name=_('Certificate subject'),
                                    help_text=_('e.g. /C=ID/ST=Jakarta/L=Jakarta/O=BlankOn/OU=IrgshBuilder/CN=Cendrawasih/emailAddress=cendrawasih@example.com'))

    class Meta:
        abstract = True

    def status_code(self):
        if self.last_activity is None:
            return 'unknown'

        delta = datetime.now() - self.last_activity

        if not self.active:
            status = 'dormant'
        elif delta.days > 1:
            status = 'unreachable'
        elif delta.seconds > 3600:
            status = 'unresponsive'
        else:
            status = 'active'

        return status

    def status(self):
        status_list = {'unknown': _('Unknown'),
                       'dormant': _('Dormant'),
                       'unreachable': _('Unreachable'),
                       'unresponsive': _('Not responsive'),
                       'active': _('Active')}
        code = self.status_code()
        return status_list.get(code, _('Unknown'))

class Worker(WorkerBase):
    '''
    List of workers that are not package builder
    '''
    type = models.IntegerField(choices=WORKER_TYPES)
    ssh_public_key = models.CharField(max_length=2048, null=True, default=None, blank=True)

class Builder(WorkerBase):
    '''
    List of package builders
    '''
    architecture = models.ForeignKey(Architecture)
    location = models.CharField(max_length=255, null=True, default=None,
                                blank=True)
    ssh_public_key = models.CharField(max_length=2048)
    remark = models.TextField(default='', blank=True)

    class Meta:
        ordering = ('-active', 'name')

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.architecture)

    def get_absolute_url(self):
        return reverse('build_builder_show', args=[self.name])

class Specification(models.Model):
    '''
    List of submitted package specifications
    '''
    distribution = models.ForeignKey(Distribution)
    submitter = models.ForeignKey(User)
    status = models.IntegerField(choices=SPECIFICATION_STATUS, default=0)

    source = models.CharField(max_length=1024)
    orig = models.CharField(max_length=1024, null=True, default=None,
                            blank=True)
    source_type = models.CharField(max_length=25, choices=SOURCE_TYPE)
    source_opts_raw = models.TextField(null=True, default=None)
    source_opts = PickledObjectField(null=True, default=None)

    package = models.ForeignKey(RepoPackage, null=True, default=None)
    version = models.CharField(max_length=255, null=True, default=None)
    changelog = models.TextField(null=True, default=None)

    priority = models.CharField(max_length=255, null=True, default=None)
    section = models.CharField(max_length=255, null=True, default=None)

    source_uploaded = models.DateTimeField(null=True, default=None)

    created = models.DateTimeField(default=datetime.now)
    updated = models.DateTimeField(auto_now=True)
    finished = models.DateTimeField(null=True, default=None)

    class Meta:
        ordering = ('-created',)
        permissions = (
            ('submit', _('Can submit a new job')),
        )

    def __unicode__(self):
        param = {'dist': self.distribution}
        if self.package is None:
            return _('Unknown package (%(dist)s)') % param
        else:
            param.update({'package': self.package})
            return _('%(package)s (%(dist)s)') % param

    def save(self):
        if self.finished is None and \
           (self.status < 0 or self.status == 999):
            self.finished = datetime.now()
        super(Specification, self).save()

    def clean(self):
        if self.orig is not None:
            if not re_orig.match(self.orig):
                raise ValidationError(_('Invalid original tarball filename'))

    def dsc(self):
        if self.package is None:
            return None
        return '%s_%s.dsc' % (self.package.name, self.version.split(':')[-1])

    def add_log(self, message):
        log = SpecificationLog(spec=self)
        log.log = message
        log.save()
        return log

    def get_absolute_url(self):
        return reverse('build_spec_show', args=[self.id])

    def repo_log_path(self):
        return os.path.join(settings.LOG_PATH, 'build',
                            str(self.id), 'repo.log.gz')

    def has_repo_log(self):
        return os.path.exists(self.repo_log_path())

    def repo_log_url(self):
        return reverse('build_repo_log', args=[self.id])

    def repo_log_name(self):
        return 'repo.log.gz'

    def source_log_path(self):
        return os.path.join(settings.LOG_PATH, 'build',
                            str(self.id), 'source.log.gz')

    def has_source_log(self):
        return os.path.exists(self.source_log_path())

    def source_log_url(self):
        return reverse('build_source_log', args=[self.id])

    def source_log_name(self):
        return 'source.log.gz'

    def is_arch_independent(self):
        return all([pkg.architecture == 'all'
                    for pkg in Package.objects.filter(specification=self,
                                                      type=BINARY)])

class ExtraOrig(models.Model):
    specification = models.ForeignKey(Specification)
    orig = models.CharField(max_length=1024)

    def clean(self):
        if not re_orig_extra.match(self.orig):
            raise ValidationError(_('Invalid additional original tarball filename'))

class Package(models.Model):
    '''
    List of packages described in debian/control file
    '''
    specification = models.ForeignKey(Specification, related_name='content')
    name = models.CharField(max_length=1024)
    architecture = models.CharField(max_length=255)
    type = models.IntegerField(choices=PACKAGE_CONTENT_TYPE)
    description = models.CharField(max_length=1025, null=True, default=None)
    long_description = models.TextField(null=True, default=None)

    created = models.DateTimeField(default=datetime.now)

    class Meta:
        unique_together = ('specification', 'name', 'architecture', 'type',)

    def __unicode__(self):
        param = {'package': self.name, 'arch': self.architecture}
        if self.type == SOURCE:
            return _('%(package)s (source)') % param
        else:
            return _('%(package)s (%(arch)s)') % param

class BuildTask(models.Model):
    '''
    List of tasks assigned to package builders
    '''
    specification = models.ForeignKey(Specification)
    architecture = models.ForeignKey(Architecture)

    task_id = models.CharField(max_length=255, unique=True) # celery task_id
    builder = models.ForeignKey(Builder, null=True, default=None)
    assigned = models.DateTimeField(null=True, default=None)

    status = models.IntegerField(choices=BUILD_TASK_STATUS, default=0)
    build_log = models.DateTimeField(null=True, default=None)
    changes = models.DateTimeField(null=True, default=None)

    created = models.DateTimeField(default=datetime.now)
    updated = models.DateTimeField(auto_now=True)
    finished = models.DateTimeField(null=True, default=None)

    class Meta:
        ordering = ('-created',)
        unique_together = ('specification', 'architecture',)

    def __unicode__(self):
        return '%s (%s)' % (self.task_id, self.id)

    def save(self):
        if self.task_id is None or self.task_id == '':
            # Create temporary task id
            import uuid
            self.task_id = str(uuid.uuid4())
            super(BuildTask, self).save()

            # Update the task id again to a simpler one
            task_id = '%s.%s.%s' % (self.specification.id,
                                    self.architecture.id,
                                    self.id)
            self.task_id = task_id

        if self.finished is None and \
           (self.status < 0 or self.status == 999):
            self.finished = datetime.now()

        super(BuildTask, self).save()

    def add_log(self, message):
        log = BuildTaskLog(task=self)
        log.log = message
        log.save()
        return log

    def update_builder(self):
        if self.builder is not None:
            Builder.objects.filter(pk=self.builder.id) \
                           .update(last_activity=datetime.now())

    def changes_name(self):
        if self.specification.package is None:
            return None
        return '%s_%s_%s.changes' % (self.specification.package.name,
                                     self.specification.version,
                                     self.architecture.name)

    def changes_file_path(self):
        return os.path.join(settings.LOG_PATH, 'task',
                            self.task_id, self.changes_name())

    def has_changes_file(self):
        return os.path.exists(self.changes_file_path())

    def changes_file_url(self):
        changes = self.changes_name()
        return reverse('build_task_changes_file', args=[self.task_id, changes])

    def upload_path(self):
        return str(self.architecture.name)

    def get_absolute_url(self):
        return reverse('build_task_show', args=[self.task_id])

    def build_log_path(self):
        return os.path.join(settings.LOG_PATH, 'task',
                            self.task_id, 'build.log.gz')

    def has_build_log(self):
        return os.path.exists(self.build_log_path())

    def build_log_url(self):
        return reverse('build_task_build_log', args=[self.task_id])

    def build_log_name(self):
        return 'build.log.gz'

class BuildTaskLog(models.Model):
    '''
    List of messages (including status change) sent by builders during
    building a package
    '''
    task = models.ForeignKey(BuildTask)
    log = models.TextField()

    created = models.DateTimeField(default=datetime.now)

    class Meta:
        ordering = ('-created',)

    def __unicode__(self):
        return self.log

class SpecificationLog(models.Model):
    spec = models.ForeignKey(Specification)
    log = models.TextField()

    created = models.DateTimeField(default=datetime.now)

    class Meta:
        ordering = ('-created',)

    def __unicode__(self):
        return self.log

