import tempfile
import shutil
import os
from datetime import datetime, timedelta
from subprocess import Popen, PIPE

from django.conf import settings

from celery.task import Task, PeriodicTask
from celery.worker.control import Panel

from . import utils, manager
from .models import Specification

class InitSpecification(Task):
    '''Initialize specification.

    Get all active architecture and create build task for each of them.
    '''

    ignore_result = True

    def run(self, spec_id):
        spec = Specification.objects.get(pk=spec_id)

        # Declare queues
        archs = spec.distribution.repo.architectures.all()
        self.declare_queues(archs)

        # Initialize spec
        init = utils.SpecInit(spec)
        init.start()

    def declare_queues(self, archs):
        '''
        Declare queues, exchanges, and routing keys to the builders
        '''
        for arch in archs:
            # declare exchange, queue, and binding
            routing_key = 'builder.%s' % arch.name
            consumer = self.get_consumer()
            consumer.queue = 'builder_%s' % arch.name
            consumer.exchange = 'builder'
            consumer.exchange_type = 'topic'
            consumer.routing_key = routing_key
            consumer.declare()
            consumer.connection.close()

class UploadSource(Task):
    '''Upload source package to repository.
    '''

    ignore_result = True

    def run(self, spec_id, files):
        spec = Specification.objects.get(pk=spec_id)

        path = os.path.join(settings.DOWNLOAD_TARGET, str(spec_id))
        files = [os.path.join(path, fname) for fname in files]

        spec.add_log('Uploading source package')

        try:
            self.upload(spec_id, files)

            self.set_source_uploaded(spec_id)
            spec.add_log('Source package uploaded')

        except StandardError, e:
            self.set_status(spec_id, -1)
            spec.add_log('Source package upload failed: %s' % e)

    def upload(self, spec_id, files):
        path = os.path.join(settings.SOURCE_UPLOAD_PATH, str(spec_id))
        target = '%s@%s:%s' % (settings.SOURCE_UPLOAD_USER,
                               settings.SOURCE_UPLOAD_HOST,
                               path)
        cmd = ['scp']
        if hasattr(settings, 'SOURCE_UPLOAD_PORT') and \
           settings.SOURCE_UPLOAD_PORT is not None:
            cmd.append('-P %s' % settings.SOURCE_UPLOAD_PORT)
        if hasattr(settings, 'SOURCE_UPLOAD_KEY') and \
           settings.SOURCE_UPLOAD_KEY is not None:
            cmd.append('-i %s' % settings.SOURCE_UPLOAD_KEY)
        cmd += files
        cmd.append(target)

        cmd = ' '.join(cmd)

        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        p.communicate()

        if p.returncode != 0:
            raise ValueError, 'Upload failed, return code: %s' % p.returncode

    def on_failure(self, exc, task_id, args, kwargs, einfo=None):
        spec_id = args[0]
        self.set_status(spec_id, -1)

    def set_status(self, spec_id, status):
        updates = {'status': status,
                   'updated': datetime.now()}
        if status < 0 or status == 999:
            updates['finished'] = updates['updated']
        Specification.objects.filter(pk=spec_id).update(**updates)

    def set_source_uploaded(self, spec_id):
        Specification.objects.filter(pk=spec_id) \
                             .update(source_uploaded=datetime.now(),
                                     updated=datetime.now())

class PingWorkers(PeriodicTask):
    '''Periodically send ping message to all workers
    '''

    ignore_result = True
    run_every = timedelta(minutes=15)

    def run(self):
        utils.ping_workers()

_ping_threshold = timedelta(minutes=5)
_last_ping = None

@Panel.register
def report_alive(panel):
    global _last_ping

    now = datetime.now()
    if _last_ping is None or now - _last_ping >= _ping_threshold:
        _last_ping = now
        manager.ping()

    return {'status': 'ok'}

