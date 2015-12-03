import tempfile
import os
import shutil
import tarfile
import gzip
import logging
import re
from subprocess import Popen, PIPE, STDOUT

import lzma
try:
    from debian.deb822 import Sources
except ImportError:
    from debian_bundle.deb822 import Sources

from irgsh.utils import find_debian, get_package_version, retrieve
from .error import SourcePackageBuildError, SourcePackagePreparationError

re_extra_orig = re.compile(r'.+\.orig-([a-z0-9-]+)\.tar')

def extract_tarball(fname, target):
    tmp = None
    try:
        if fname.endswith('.tar.xz'):
            __, tmp = tempfile.mkstemp('-irgsh-xz.tar')

            d = lzma.LZMADecompressor()
            fin = open(fname, 'rb')
            fout = open(tmp, 'wb')
            fout.write(d.decompress(fin.read()))
            fout.close()

            fname = tmp

        tar = tarfile.open(fname)
        tar.extractall(target)
        tar.close()
    finally:
        if tmp is not None:
            os.unlink(tmp)

class SourcePackageBuilder(object):
    def __init__(self, source, source_type='tarball',
                 source_opts=None, orig=None, extra_orig=None):
        if source_opts is None:
            source_opts = {}
        self.source = source
        self.source_type = source_type
        self.source_opts = source_opts
        self.orig = orig
        if orig is None or extra_orig is None:
            extra_orig = []
        self.extra_orig = extra_orig

        if not source_type in ['patch', 'tarball', 'bzr']:
            raise ValueError, 'Unsupported source type: %s' % source_type
        if source_type == 'patch' and orig is None:
            raise ValueError, \
                  'A patch has to be accompanied with an orig file'

        self.log = logging.getLogger('irgsh.source.packager')

    def build(self, target, logger=None):
        '''Build source package.

        This function returns the .dsc filename
        '''
        try:
            cwd = os.getcwd()
            build_path = tempfile.mkdtemp('-irgsh-srcpkg')

            # Prepare source directory
            self.slog(logger, '# Preparing source code directory')
            package, version = self.prepare_source(build_path, logger)
            source = '%s-%s' % (package, version)
            self.slog(logger)

            os.chdir(build_path)

            self.slog(logger, '# File listing')
            cmd = 'find -ls'
            p = Popen(cmd.split(), stdout=logger, stderr=STDOUT,
                      preexec_fn=os.setsid)
            out, err = p.communicate()
            self.slog(logger)

            # Build
            self.log.debug('Building source package: ' \
                           'source=%s type=%s opts=%s orig=%s extra_orig=%s' % \
                           (self.source, self.source_type, \
                            self.source_opts, self.orig, self.extra_orig))

            self.slog(logger, '# Building source package')
            cmd = 'dpkg-source -b %s' % source
            self.slog(logger, '# Command:', cmd)
            p = Popen(cmd.split(), stdout=logger, stderr=STDOUT,
                      preexec_fn=os.setsid)
            out, err = p.communicate()
            self.slog(logger, '# Return code:', p.returncode, '\n')

            if p.returncode != 0:
                raise SourcePackageBuildError(p.returncode, out, err)

            # Move result to the given target directory,
            # existing files will be replaced
            dsc = '%s_%s.dsc' % (package, version)
            files = [dsc]

            dsc_path = os.path.join(build_path, dsc)
            src = Sources(open(dsc_path))
            if not src.has_key('Files'):
                raise KeyError, 'Invalid source package'
            files += [item['name'] for item in src['Files']]

            self.log.debug('Moving source package files: %s' % ', '.join(files))

            for fname in files:
                target_path = os.path.join(target, fname)
                if os.path.exists(target_path):
                    os.unlink(target_path)
                shutil.move(os.path.join(build_path, fname), target_path)
                os.chmod(target_path, 0644)

            self.log.debug('Source package built: %s' % dsc)

            return dsc

        finally:
            shutil.rmtree(build_path)
            os.chdir(cwd)

    def prepare_source(self, target, logger=None):
        try:
            tmp = tempfile.mkdtemp('-irgsh-srcpkg-prepare')

            self.log.debug('Preparing source code directory')

            # Download and extract source
            source_path = os.path.join(tmp, 'source')
            os.makedirs(source_path)
            self.log.debug('Downloading source code, type: %s' % self.source_type)
            source = self.download_source(source_path, logger)
            self.log.debug('Source code downloaded')

            # Download orig
            orig = None
            orig_path = os.path.join(tmp, 'orig')
            os.makedirs(orig_path)
            if self.orig is not None:
                self.log.debug('Downloading original file')
                orig = self.download_orig(orig_path, logger)
                self.log.debug('Original file downloaded')

            # Download additional orig
            extra_orig = []
            if len(self.extra_orig) > 0:
                self.log.debug('Downloading additional original files')
                extra_orig = self.download_extra_orig(orig_path, logger)
                self.log.debug('additional original files downloaded')

            # Combine source and orig(s)
            combined_path = os.path.join(tmp, 'combine')
            os.makedirs(combined_path)
            self.log.debug('Combining source and orig, type: %s' % self.source_type)
            combined_path = self.combine(source, orig, extra_orig, combined_path, logger)
            self.log.debug('Source and orig combined')

            # Check for debian directory
            combined_path = find_debian(combined_path)
            if combined_path is None:
                raise ValueError, 'Unable to find debian directory'

            # Get version information
            package, version = get_package_version(combined_path)

            self.log.debug('Package: %s_%s' % (package, version))

            # Move source directory
            self.log.debug('Moving source code directory')

            final_path = os.path.join(target, '%s-%s' % (package, version))
            shutil.move(combined_path, final_path)

            # Move and rename orig file, if available
            if orig is not None:
                upstream = version.split('-')[0]
                fname, ext = os.path.splitext(self.orig)
                orig_path = os.path.join(target, '%s_%s.orig.tar%s' % \
                                                 (package, upstream, ext))
                shutil.move(orig, orig_path)

            # Move additional orig files
            for orig in extra_orig:
                shutil.move(orig, target)

            return package, version

        except Exception, e:
            raise SourcePackagePreparationError(e)

        finally:
            shutil.rmtree(tmp)

    def download_orig(self, target, logger=None):
        self.slog(logger, '# Downloading', self.orig)
        fname = retrieve(self.orig)
        orig_name = os.path.basename(self.orig)
        orig_path = os.path.join(target, orig_name)
        shutil.move(fname, orig_path)
        return orig_path

    def download_extra_orig(self, target, logger=None):
        items = []
        for url in self.extra_orig:
            self.slog(logger, '# Downloading', url)
            fname = retrieve(url)
            orig_name = os.path.basename(url)
            orig_path = os.path.join(target, orig_name)
            shutil.move(fname, orig_path)
            items.append(orig_path)
        return items

    def download_source(self, target, logger=None):
        func = getattr(self, 'download_source_%s' % self.source_type)
        return func(target, logger)

    def download_source_patch(self, target, logger=None):
        self.slog(logger, '# Downloading patch:', self.source)
        fname = retrieve(self.source)
        patch_name = os.path.basename(self.source)
        patch_path = os.path.join(target, patch_name)
        shutil.move(fname, patch_path)
        return patch_path

    def download_source_tarball(self, target, logger=None):
        try:
            tmp = tempfile.mkdtemp('-irgsh-tarball')

            self.slog(logger, '# Downloading tarball:', self.source)
            tmpname = retrieve(self.source)

            source_name = os.path.basename(self.source)
            source_path = os.path.join(tmp, source_name)
            shutil.move(tmpname, source_path)

            extract_tarball(source_path, target)

            return target
        except tarfile.ReadError, e:
            raise StandardError(e)

        finally:
            shutil.rmtree(tmp)

    def download_source_bzr(self, target, logger=None):
        self.slog(logger, '# Downloading bazaar tree:', self.source, self.source_opts)

        from .bazaar import BazaarExporter
        bzr = BazaarExporter(self.source, **self.source_opts)
        bzr.export(target)

        return target

    def extract_orig(self, orig, target, logger=None):
        self.log.debug('Extracting orig file')
        self.slog(logger, '# Extracting', os.path.basename(orig))

        extract_tarball(orig, target)

        return self.find_orig_path(target)

    def extract_extra_orig(self, extra_orig, target, logger=None):
        self.log.debug('Extracting additional orig files')

        for orig in extra_orig:
            fname = os.path.basename(orig)
            m = re_extra_orig.match(fname)
            component = m.groups()[0]

            try:
                tmp = tempfile.mkdtemp('-extra-orig')
                extra = os.path.join(tmp, component)
                os.makedirs(extra)

                self.slog(logger, '# Extracting', os.path.basename(orig))

                extract_tarball(orig, extra)

                subdir = os.path.join(extra, component)
                if os.path.exists(subdir) and os.path.isdir(subdir):
                    extra = subdir

                if os.path.exists(os.path.join(target, component)):
                    shutil.rmtree(os.path.join(target, component))

                shutil.move(extra, target)

            finally:
                shutil.rmtree(tmp)

    def combine(self, source, orig, extra_orig, target, logger=None):
        self.log.debug('Combining source and orig, type: %s' % self.source_type)
        func = getattr(self, 'combine_%s' % self.source_type)
        return func(source, orig, extra_orig, target)

    def combine_patch(self, source, orig, extra_orig, target, logger=None):
        if orig is None:
            raise ValueError, 'A patch has to be accompanied with an orig file'

        # Extract orig
        orig_path = self.extract_orig(orig, os.path.join(target, 'build'), logger)
        self.extract_extra_orig(extra_orig, orig_path, logger)

        # Apply patch
        try:
            cwd = os.getcwd()
            patch_path = os.path.abspath(source)
            patch = gzip.open(patch_path, 'rb')

            self.slog(logger, '# Patching orig file(s)')

            os.chdir(orig_path)
            cmd = 'patch -p1'
            p = Popen(cmd.split(), stdin=PIPE, stdout=logger, stderr=STDOUT,
                      preexec_fn=os.setsid)
            p.stdin.write(patch.read())
            p.communicate()

            if p.returncode != 0:
                raise ValueError, 'Patch application failed'

            return orig_path
        finally:
            os.chdir(cwd)

    def combine_tarball(self, source, orig, extra_orig, target, logger=None):
        if orig is not None:
            return self.combine_tarball_orig(source, orig, extra_orig, target, logger)
        return source

    def combine_tarball_orig(self, source, orig, extra_orig, target, logger=None):
        # Extract orig
        orig_path = self.extract_orig(orig, target, logger)
        self.extract_extra_orig(extra_orig, orig_path, logger)

        # Remove existing debian directory
        if os.path.exists(os.path.join(orig_path, 'debian')):
            shutil.rmtree(os.path.join(orig_path, 'debian'))

        # Copy all files inside source
        self.slog(logger, '# Combining source and orig file(s)')
        cmd = 'cp -a %s/* %s/' % (source.rstrip('/'), orig_path.rstrip('/'))
        p = Popen(cmd, shell=True, stdout=logger, stderr=STDOUT,
                  preexec_fn=os.setsid)
        p.communicate()

        return find_debian(orig_path)

    def combine_bzr(self, source, orig, extra_orig, target, logger=None):
        return self.combine_tarball(source, orig, extra_orig, target, logger)

    def find_orig_path(self, dirname):
        # Find the correct orig directory
        # Rule: if orig directory contains only one directory,
        #       then that directory is the real orig directory
        #       otherwise, the orig directory is already real
        items = os.listdir(dirname)
        if len(items) == 1:
            if os.path.isdir(os.path.join(dirname, items[0])):
                dirname = os.path.join(dirname, items[0])

        return dirname

    def slog(self, logger, *msgs):
        if logger is not None:
            logger.write('%s\n' % ' '.join(map(str, msgs)))
            logger.flush()

