import tempfile
import shutil
import os
from subprocess import Popen, PIPE

from unittest import TestCase

__all__ = ['ArchitectureTestCase', 'FindDebianTestCase']

class ArchitectureTestCase(TestCase):
    def testArchitecture(self):
        from subprocess import Popen, PIPE
        from irgsh.utils import get_architecture

        arch = get_architecture()

        p = Popen('dpkg-architecture -qDEB_BUILD_ARCH'.split(),
                  stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()

        self.assertEqual(arch, out.strip())

class FindDebianTestCase(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp('-irgsh-test')

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def testNormal(self):
        from irgsh.utils import find_debian

        os.makedirs(os.path.join(self.tmp, 'debian'))

        res = find_debian(self.tmp)

        self.assertEqual(res, self.tmp)

    def testInsideDirectory(self):
        from irgsh.utils import find_debian

        os.makedirs(os.path.join(self.tmp, 'python-irgsh-0.5', 'debian'))

        res = find_debian(self.tmp)

        self.assertEqual(res, os.path.join(self.tmp, 'python-irgsh-0.5'))

    def testNoDebian(self):
        from irgsh.utils import find_debian

        res = find_debian(self.tmp)

        self.assertEqual(res, None)

    def testMultipleDirectories(self):
        from irgsh.utils import find_debian

        os.makedirs(os.path.join(self.tmp, 'python-irgsh-0.1', 'debian'))
        os.makedirs(os.path.join(self.tmp, 'python-irgsh-0.5', 'debian'))

        res = find_debian(self.tmp)

        self.assertEqual(res, None)

    def testInvalidDirectory(self):
        from irgsh.utils import find_debian

        tmp = os.path.join(self.tmp, 'invalid')

        res = find_debian(tmp)

        self.assertEqual(res, None)

    def testSingleFile(self):
        from irgsh.utils import find_debian

        fname = os.path.join(self.tmp, 'python-irgsh_0.5.orig.tar.gz')
        f = open(fname, 'wb')
        f.close()

        res = find_debian(self.tmp)

        self.assertEqual(res, None)

    def testSingleDirectoryNoDebian(self):
        from irgsh.utils import find_debian

        os.makedirs(os.path.join(self.tmp, 'python-irgsh-0.5'))

        res = find_debian(self.tmp)

        self.assertEqual(res, None)

class PackageVersionTestCase(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp('-irgsh-test')
        os.makedirs(os.path.join(self.tmp, 'debian'))
        self.changelog = os.path.join(self.tmp, 'debian', 'changelog')

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def testNormal(self):
        self._test('0.5', '0.5')

    def testEpoch(self):
        self._test('1:0.5', '0.5')

    def testDebian(self):
        self._test('0.5-0', '0.5-0')

    def testUbuntu(self):
        self._test('0.5-0ubuntu1', '0.5-0ubuntu1')

    def testBlankON(self):
        self._test('0.5-0ubuntu1+blankon0', '0.5-0ubuntu1+blankon0')

    def _test(self, version, expected):
        from irgsh.utils import get_package_version

        f = open(self.changelog, 'wb')
        f.write('''python-irgsh (%s) lucid; urgency=low

  * Next generation of IRGSH

 -- Fajran Iman Rusadi <fajran@gmail.com>  Sun, 27 Feb 2011 22:27:19 +0100''' % version)
        f.close()

        pkg, ver = get_package_version(self.tmp)
        self.assertEqual(pkg, 'python-irgsh')
        self.assertEqual(ver, expected)

