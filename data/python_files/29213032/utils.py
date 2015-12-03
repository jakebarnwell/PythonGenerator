import uuid
import gzip
import shutil
import tempfile
import urllib
import os
import tarfile
import logging
import random
import time
from subprocess import Popen, PIPE, STDOUT
from datetime import datetime

from django.db import IntegrityError
from django.utils.translation import ugettext as _
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site

try:
    from debian.deb822 import Packages, Sources
    from debian.changelog import Changelog
except ImportError:
    from debian_bundle.deb822 import Packages, Sources
    from debian_bundle.changelog import Changelog

def create_build_task_param(spec):
    from irgsh.data import Specification as BuildSpecification
    from irgsh.data import Distribution as BuildDistribution

    spec_id = spec.id
    build_spec = BuildSpecification(spec.source, spec.source_type,
                                    spec.source_opts, spec.orig,
                                    spec.extraorig_set.all().values_list('orig', flat=True))

    dist = spec.distribution
    build_dist = BuildDistribution(dist.name, dist.mirror, dist.dist,
                                   dist.components, dist.extra)

    return spec_id, build_spec, build_dist

def get_package_description(text):
    lines = text.splitlines()
    if len(lines) == 0:
        return None, None

    desc = lines[0]

    long_desc = None
    long_list = []
    for line in lines[1:]:
        line = line.strip()
        if line == '.':
            line = ''
        long_list.append(line)
    if len(long_list) > 0:
        long_desc = '\n'.join(long_list)

    return desc, long_desc

def get_package_info(packages):
    from .models import Package, SOURCE, BINARY

    items = []
    name = None
    priority = None
    section = None
    for info in packages:
        try:
            pkg = {}
            if info.has_key('Source'):
                pkg['name'] = info['Source']
                pkg['type'] = SOURCE

                name = info['Source']
                priority = info.get('Priority', None)
                section = info.get('Section', None)

            elif info.has_key('Package'):
                pkg['name'] = info['Package']
                pkg['type'] = BINARY
                pkg['architecture'] = info['Architecture']

            else:
                continue

            desc, long_desc = None, None
            if info.has_key('Description'):
                desc, long_desc = get_package_description(info['Description'])
            pkg['desc'] = desc
            pkg['long_desc'] = long_desc

            items.append(pkg)

        except KeyError:
            pass

    result = {'name': name,
              'priority': priority,
              'section': section,
              'packages': items}

    return result

def validate_packages(packages):
    from .models import Package, SOURCE, BINARY

    has_source = any([pkg['type'] == SOURCE for pkg in packages])
    has_binary = any([pkg['type'] == BINARY for pkg in packages])
    return has_source and has_binary

def store_package_info(spec, info):
    from .models import Package, BINARY

    for data in info['packages']:
        pkg = Package()
        pkg.specification = spec
        pkg.name = data['name']
        pkg.type = data['type']
        pkg.description = data['desc']
        pkg.long_description = data['long_desc']
        if pkg.type == BINARY:
            pkg.architecture = data['architecture']
        try:
            pkg.save()
        except IntegrityError:
            pass

def build_source_opts(source_type, source_opts):
    from .models import TARBALL, BZR

    if source_opts is None:
        source_opts = ''
    source_opts = source_opts.strip()

    if source_type == TARBALL:
        return None

    elif source_type == BZR:
        '''
        valid opts:
        - tag=a-tag
        - rev=a-rev
        '''
        if source_opts == '':
            return None

        try:
            key, value = source_opts.split('=', 1)
            key = str(key.strip())
            value = str(value.strip())
            if key in ['tag', 'rev']:
                return {key: value}

        except ValueError:
            pass

        raise ValueError(_('Invalid source options for Bazaar'))

class SpecInit(object):
    '''
    Prepare and distribute specification
    '''

    def __init__(self, spec):
        self.spec_id = spec.id
        self.spec = spec

        self.description_sent = False
        self.distributed = False

        self.source_name = None
        self.orig_name = None

        self.log = logging.getLogger('irgsh_web.specinit')

    def start(self):
        from .models import Specification
        from irgsh.source.error import SourcePackageBuilderException

        self.log.debug('[%s] Initializing specification' % self.spec_id)
        self.set_status(100)

        try:
            self.init()
            files = self.download()
            self.distribute()
            self.upload(files)
        except StandardError, e:
            self.log.error('[%s] Error! %s' % (self.spec_id, e))
            self.spec.add_log('Specification initialization failed: %s' % str(e))
            current_status = Specification.objects.get(pk=self.spec_id).status
            if current_status >= 0:
                self.set_status(-1)

    def init(self):
        # Prepare source directory
        self.target = os.path.join(settings.DOWNLOAD_TARGET, str(self.spec_id))
        if not os.path.exists(self.target):
            os.makedirs(self.target)

        self.log.debug('[%s] Resource directory: %s' % (self.spec_id, self.target))

    def download(self):
        # Prepare source package builder
        from irgsh.source import SourcePackageBuilder

        spec = self.spec
        srcpkg = SourcePackageBuilder(spec.source, spec.source_type,
                                      spec.source_opts, spec.orig,
                                      spec.extraorig_set.all().values_list('orig', flat=True))

        orig_path = None
        logger = None

        try:
            # Download source and build source package
            build_dir = tempfile.mkdtemp('-irgsh-build')
            source_dir = tempfile.mkdtemp('-irgsh-build-source')

            # Prepare logger
            logdir = os.path.dirname(self.spec.source_log_path())
            if not os.path.exists(logdir):
                os.makedirs(logdir)
            logname = os.path.join(logdir, 'source.log')
            logger = open(logname, 'wb')

            # Build source package
            spec.add_log(_('Downloading source code'))
            self.log.debug('[%s] Downloading source code' % (self.spec_id,))

            self.set_status(101)
            self.dsc = srcpkg.build(build_dir, logger)

            spec.add_log(_('Source code downloaded'))
            self.log.debug('[%s] Source code downloaded' % (self.spec_id,))

            # Extract source package and send package description
            dsc_file = os.path.join(build_dir, self.dsc)
            source = os.path.join(source_dir, 'source')

            cmd = 'dpkg-source -x %s %s' % (dsc_file, source)
            logger.write('# Extracting source package\n')
            logger.write('# Command: %s\n' % cmd)
            logger.flush()
            p = Popen(cmd.split(), stdout=logger, stderr=STDOUT)
            p.communicate()
            logger.write('\n')

            changelog = os.path.join(source, 'debian', 'changelog')
            control = os.path.join(source, 'debian', 'control')
            self.send_description(changelog, control)

            # Copy source packages
            logger.write('# Copying source files:\n')
            src = Sources(open(dsc_file))
            files = [self.dsc] + [info['name'] for info in src['Files']]
            for fname in files:
                logger.write('# - %s\n' % os.path.basename(fname))
                target = os.path.join(self.target, fname)
                if os.path.exists(target):
                    os.unlink(target)
                shutil.move(os.path.join(build_dir, fname), target)
                os.chmod(target, 0644)

            return files

        except StandardError, e:
            logger.write('# Exception happened: %s: %s' % (type(e), str(e)))
            raise

        finally:
            shutil.rmtree(build_dir)
            shutil.rmtree(source_dir)

            if logger is not None:
                logger.close()

                logger = open(logname, 'rb')
                gzlogname = os.path.join(logdir, 'source.log.gz')
                gz = gzip.open(gzlogname, 'wb')
                gz.write(logger.read())
                gz.close()
                logger.close()

                os.unlink(logname)

    def send_description(self, changelog, control):
        '''
        Send package description to the manager

        Depending on the response, this will determine whether
        this specification is allowed to proceed or not.
        '''
        from . import manager

        if self.description_sent:
            return

        self.log.debug('[%s] Sending description' % (self.spec_id,))

        try:
            tmpdir = tempfile.mkdtemp()
            gzchangelog = os.path.join(tmpdir, 'changelog.gz')
            gzcontrol = os.path.join(tmpdir, 'control.gz')

            gz = gzip.GzipFile(gzchangelog, 'wb')
            gz.write(open(changelog, 'rb').read())
            gz.close()

            gz = gzip.GzipFile(gzcontrol, 'wb')
            gz.write(open(control, 'rb').read())
            gz.close()

            res = manager.send_spec_description(self.spec.id,
                                                gzchangelog, gzcontrol)
            if res['status'] != 'ok':
                self.log.debug('[%s] Package is rejected: %s' % (self.spec_id, res))

                # Package is rejected
                raise ValueError(_('Package rejected: %(msg)s') % \
                                 {'msg': res['msg']})

            self.log.debug('[%s] Package is accepted: %s' % \
                           (self.spec_id, res['package']))

        finally:
            self.description_sent = True
            shutil.rmtree(tmpdir)

    def get_archs(self, spec):
        '''
        List all architectures associated to this specification
        '''
        from .models import BINARY

        available_archs = spec.distribution.repo.architectures.all()
        if spec.is_arch_independent():
            return available_archs

        archs = set()
        packages = spec.content.filter(type=BINARY)
        for package in packages:
            archs = archs | set(package.architecture.split())

        if 'any' in archs:
            return available_archs

        return [arch for arch in available_archs
                     if arch.name in archs]

    def distribute(self):
        '''
        Distribute specification to builders
        '''
        self.log.debug('[%s] Distributing tasks' % self.spec_id)

        from celery.task.sets import subtask

        from .models import BuildTask
        from irgsh_node.tasks import BuildPackage
        from irgsh.data import Specification as BuildSpecification
        from irgsh.data import Distribution as BuildDistribution

        if self.distributed:
            return

        spec = self.spec
        spec_id = self.spec_id

        # Prepare arguments
        task_name = BuildPackage.name
        args = create_build_task_param(spec)

        # build_spec = BuildSpecification(spec.source, spec.source_type,
        #                                 spec.source_opts, spec.orig,
        #                                 spec.extraorig_set.all().values_list('orig', flat=True))
        path = reverse('build_spec_source', args=[self.spec_id, self.dsc])
        url_dsc = 'http://%s%s' % (Site.objects.get_current().domain, path)
        build_spec = BuildSpecification(url_dsc, 'dsc')

        dist = spec.distribution
        build_dist = BuildDistribution(dist.name(), dist.mirror, dist.dist,
                                       dist.components, dist.extra)

        args = [self.spec_id, build_spec, build_dist]
        kwargs = None

        spec_id, s, d = args

        # Distribute to builder of each architecture
        subtasks = []
        archs = self.get_archs(spec)

        if len(archs) == 0:
            raise ValueError, _('No suitable builders found.')

        for arch in archs:
            # store task info
            task = BuildTask()
            task.specification = spec
            task.architecture = arch
            task.save()

            # declare exchange, queue, and binding
            routing_key = 'builder.%s' % arch.name

            # create build package task
            opts = {'exchange': 'builder',
                    'exchange_type': 'topic',
                    'routing_key': routing_key,
                    'task_id': task.task_id}

            # execute build task asynchronously
            s = subtask(task_name, args, kwargs, opts)
            subtasks.append(s)

        self.set_status(104)
        self.spec.add_log(_('Distributing build tasks to %(archs)s') % \
                          {'archs': ' '.join([arch.name for arch in archs])})

        for s in subtasks:
            s.apply_async()

        self.distributed = True

    def set_status(self, status):
        from .models import Specification
        updates = {'status': status,
                   'updated': datetime.now()}
        if status < 0:
            updates['finished'] = updates['updated']
        Specification.objects.filter(pk=self.spec.id).update(**updates)

    def upload(self, files):
        self.log.debug('[%s] Scheduling source package upload' % self.spec_id)

        from .tasks import UploadSource
        UploadSource.apply_async(args=(self.spec_id, files))

def rebuild_repo(spec):
    from celery.task.sets import subtask

    from .models import BuildTask
    from irgsh_repo.tasks import RebuildRepo

    package = spec.package
    dist = spec.distribution.repo
    pkgdist = package.packagedistribution_set.get(distribution=dist)

    tasks = BuildTask.objects.filter(specification=spec) \
                             .filter(status=999) \
                             .select_related()
    task_arch_list = [(task.task_id, task.architecture.name)
                      for task in tasks]

    task_name = RebuildRepo.name
    args = [spec.id, package.name, spec.version,
            dist.name,
            pkgdist.component.name,
            task_arch_list,
            spec.section, spec.priority]
    kwargs = None
    opts = {'exchange': 'repo',
            'exchange_type': 'direct',
            'routing_key': 'repo'}

    s = subtask(task_name, args, kwargs, opts)
    return s.apply_async()

def make_canonical(cert_subject):
    '''
    Create canonical version of a certificate subject
    '''
    # TODO
    return cert_subject.strip()

def verify_certificate(cert_subject):
    '''
    Verify a certificate subject
    '''
    from .models import Builder, Worker

    cert_subject = make_canonical(cert_subject)

    workers = Worker.objects.filter(active=True,
                                    cert_subject=cert_subject)
    if len(workers) == 1:
        return True

    builders = Builder.objects.filter(active=True,
                                      cert_subject=cert_subject)
    return len(builders) == 1

def ping_workers():
    from celery.task.control import broadcast
    broadcast('report_alive')

def cancel_other_tasks(spec, exception):
    from celery.task.control import revoke
    from .models import BuildTask

    tasks = BuildTask.objects.filter(specification=spec) \
                             .exclude(pk=exception.id)
    for task in tasks:
        now = datetime.now()
        total = BuildTask.objects.filter(pk=task.id) \
                                 .filter(status__gte=0) \
                                 .update(status=-2,
                                         updated=now,
                                         finished=now)

        if total > 0:
            spec.add_log(_('Task %(cancelled_task_id)s ' \
                           'is cancelled by task %(task_id)s') % \
                         {'cancelled_task_id': task.task_id,
                          'task_id': exception.task_id})
            revoke(task.task_id)

