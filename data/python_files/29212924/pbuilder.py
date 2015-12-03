import logging
import os
from subprocess import Popen, STDOUT
try:
    import simplejson as json
except ImportError:
    import json

from . import BaseBuilder, BuildFailedError

class Pbuilder(BaseBuilder):
    def __init__(self, distribution, pbuilder_path, **opts):
        super(Pbuilder, self).__init__(distribution, **opts)

        self.pbuilder_path = os.path.abspath(pbuilder_path)
        self.path = os.path.join(self.pbuilder_path, self.distribution.name)
        self.configfile = os.path.join(self.path, 'pbuilder.conf')
        self.keyring = opts['keyring']

        self.log = logging.getLogger('irgsh.builders.pbuilder')

    def init(self):
        self.log.debug('Initializing pbuilder directory structure and settings')

        # Create directory structure
        paths = [self.path]
        paths += [os.path.join(self.path)
                  for path in ['aptcache', 'result', 'build', 'hook']]

        for path in paths:
            if not os.path.exists(path):
                os.makedirs(path)

        # Create distribution configuration
        fname = os.path.join(self.path, 'distribution.json')
        if not os.path.exists(fname):
            f = open(fname, 'w')
            f.write(json.dumps({'name': self.distribution.name,
                                'mirror': self.distribution.mirror,
                                'dist': self.distribution.dist,
                                'components': self.distribution.components,
                                'extra': self.distribution.extra}))
            f.close()

        # Create pbuilder configuration
        if not os.path.exists(self.configfile):
            def join(*name):
                return os.path.join(self.path, *name)
            def escape(value):
                if ' ' in value:
                    return '"%s"' % value
                return value

            components = ' '.join(self.distribution.components)
            othermirror = ' | '.join(self.distribution.extra)

            config = {'BASETGZ': join('base.tgz'),
                      'APTCACHE': join('aptcache'),
                      'BUILDRESULT': join('result'),
                      'BUILDPLACE': join('build'),
                      'HOOKDIR': join('hook'),
                      'MIRRORSITE': self.distribution.mirror,
                      'DISTRIBUTION': self.distribution.dist,
                      'COMPONENTS': components,
                      'OTHERMIRROR': othermirror}

            f = open(self.configfile, 'w')
            f.write('\n'.join(['%s=%s' % (key, escape(value))
                               for key, value in config.items()]))
            f.close()

    def reinit(self):
        self.log.debug('Resetting pbuilder')

        fname = os.path.join(self.path, 'distribution.json')
        if os.path.exists(fname):
            os.unlink(fname)

        if os.path.exists(self.configfile):
            os.unlink(self.configfile)

        self.init()

    def create(self, logger=None):
        self.log.debug('Creating base.tgz')

        # TODO: check if pbuilder.conf exists
        cmd = ['sudo', 'pbuilder', '--create',
               '--configfile', self.configfile,
               '--debootstrapopts', '--keyring=%s' % self.keyring]

        p = Popen(cmd, stdout=logger, stderr=STDOUT,
                  preexec_fn=os.setsid)
        p.communicate()

        return p.returncode

    def update(self, logger=None):
        self.log.debug('Updating base.tgz')

        # TODO: check if pbuilder.conf exists
        cmd = ['sudo', 'pbuilder', '--update',
               '--configfile', self.configfile,
               '--debootstrapopts', '--keyring=%s' % self.keyring]

        p = Popen(cmd, stdout=logger, stderr=STDOUT,
                  preexec_fn=os.setsid)
        p.communicate()

        return p.returncode

    def build(self, dsc, resultdir, logger=None):
        self.log.debug('Building %s to %s' % (dsc, resultdir))

        # Check if base.tgz exists, if not initialize the builder
        if not os.path.exists(os.path.join(self.path, 'base.tgz')):
            self.init()
            self.create(logger)

        else:
            self.update(logger)

            # TODO
            # - add file locking so other process won't try to
            #   initialize the builder again
            # - the lock contains pid so the its validity
            #   can be checked

        # TODO: check if pbuilder.conf exists
        cmd = ['sudo', 'pbuilder', '--build',
               '--configfile', self.configfile,
               '--buildresult', resultdir,
               '--debootstrapopts', '--keyring=%s' % self.keyring,
               dsc]

        p = Popen(cmd, stdout=logger, stderr=STDOUT,
                  preexec_fn=os.setsid)
        p.communicate()

        if p.returncode != 0:
            self.log.error('Error building package %s: %s' % (dsc, p.returncode))
            raise BuildFailedError(dsc)
        else:
            return self.get_changes_file(dsc)

def _test_run():
    import tempfile
    import shutil
    from urllib import urlretrieve
    from ..distribution import Distribution
    spec = dict(name='lucid',
                mirror='http://mirror.liteserver.nl/pub/ubuntu/',
                dist='lucid',
                components=['main', 'universe'])
    distribution = Distribution(**spec)

    def download(target, urls):
        for url in urls:
            fname = os.path.join(target, os.path.basename(url))
            tmp, dummy = urlretrieve(url)
            shutil.move(tmp, fname)

    def lsdir(path):
        cmd = 'find %s -ls' % path
        p = Popen(cmd.split())
        p.communicate()

    try:
        logger = None

        resultdir = tempfile.mkdtemp()
        spath = tempfile.mkdtemp()
        download(spath, ['http://archive.ubuntu.com/ubuntu/pool/universe/n/nginx/nginx_0.7.65-1ubuntu2.dsc',
                         'http://archive.ubuntu.com/ubuntu/pool/universe/n/nginx/nginx_0.7.65.orig.tar.gz',
                         'http://archive.ubuntu.com/ubuntu/pool/universe/n/nginx/nginx_0.7.65-1ubuntu2.debian.tar.gz'])
        dsc = os.path.join(spath, 'nginx_0.7.65-1ubuntu2.dsc')
        print '# Sources'
        lsdir(spath)

        path = tempfile.mkdtemp()
        builder = Pbuilder(distribution, path)
        builder.init()
        print '# pbuilder directory'
        lsdir(path)

        builder.create(logger=logger)
        print '# base.tgz'
        lsdir(path)

        changes = builder.build(dsc, resultdir, logger=logger)
        print 'Changes:', changes
        lsdir(resultdir)

    except Exception, e:
        print e
        raise

    finally:
        shutil.rmtree(spath)
        print 'Please remove the following directories using sudo/root:'
        print '-', path
        print '-', resultdir

if __name__ == '__main__':
    _test_run()

