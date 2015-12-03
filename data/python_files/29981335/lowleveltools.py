import subprocess
import os
import time
import logging
import re
import tempfile
from contextlib import contextmanager


LVCREATE = '/sbin/lvcreate'
LVREMOVE = '/sbin/lvremove'
VGS = '/sbin/vgs'
KPARTX = '/sbin/kpartx'
MOUNT = '/bin/mount'
UMOUNT = '/bin/umount'
PARTED = '/sbin/parted'
UDEVADM = '/sbin/udevadm'
MKSWAP = '/sbin/mkswap'
MKFSEXT4 = '/sbin/mkfs.ext4'
BRCTL = '/sbin/brctl'
IP = '/sbin/ip'
FREE = '/usr/bin/free'


_logger = logging.getLogger('lowleveltools')

def checkedSystemCall(cmd):
    #_logger.info('checkedSystemCall: {0}'.format(' '.join(cmd)))

    t0 = time.time()
    p = subprocess.Popen(cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=False,
                         close_fds=True)
    stdout, stderr = p.communicate()
    stdout = stdout.strip()
    stderr = stderr.strip()
    dt = time.time() - t0

    msg = 'checkedSystemCall: {0} returned {1} ({2:.1f}s).'.format(str(cmd), p.returncode, dt)
    _logger.info(msg)

    if stdout:
        _logger.debug('checkedSystemCall: stdout of {0}: {1}'.format(cmd[0], stdout))
    if stderr:
        _logger.debug('checkedSystemCall: stderr of {0}: {1}'.format(cmd[0], stderr))

    if p.returncode != 0:
        msg = '{0} returned {1}'.format(cmd[0], p.returncode)
        raise RuntimeError(msg)

    return stdout, stderr


########################################
# LVM
########################################

def lvremove(vg, lv, retries=20, waitAfterFail=0.5):
    p = '/dev/{0}/{1}'.format(vg, lv)

    if not os.path.exists(p):
        return

    cmd = [LVREMOVE,
            '-f',
            p]

    i = 0
    while i < retries:
        i += 1
        try:
            checkedSystemCall(cmd)
            break
        except:
            if i == retries:
                raise
        time.sleep(waitAfterFail)


def lvcreateSnapshot(vg, source, sizeMB, name):
    cmd = [LVCREATE,
            '--snapshot',
            '--size', '{0}M'.format(sizeMB),
            '--name', name,
            '/dev/{0}/{1}'.format(vg, source)]
    checkedSystemCall(cmd)


def lvcreate(vg, sizeMB, name):
    cmd = [LVCREATE,
            '--size', '{0}M'.format(sizeMB),
            '--name', name,
            vg]
    checkedSystemCall(cmd)


def vgfree(vg):
    '''
    returns tuple (freeMiB, sizeMiB)
    '''
    cmd = [VGS,
           '--noheadings',
           '-o', 'vg_name,vg_free,vg_size',
           '--units', 'b',
           vg]
    stdout, _ = checkedSystemCall(cmd)

    stdout = stdout.strip()
    if '\n' in stdout:
        raise RuntimeError('vgfree: vgs should return exactly one line')

    stdout = stdout.split()
    if stdout[0] != vg:
        raise RuntimeError('vgfree: vgs returned data about wrong volume group')

    if stdout[1][-1] != 'B' or stdout[2][-1] != 'B':
        raise RuntimeError('vgfree: vgs did not return data in Bytes')

    free = int(stdout[1][:-1])
    size = int(stdout[2][:-1])

    free = free // (1024 * 1024)
    size = size // (1024 * 1024)

    if free > size:
        raise RuntimeError('vgfree: size is unexpectedly smaller than free')

    return (free, size)


########################################
# host memory
########################################
def memfree():
    '''
    returns (freeMiB, totalMiB)
    '''
    cmd = [FREE, '-m']
    stdout, _ = checkedSystemCall(cmd)

    lines = stdout.splitlines()

    total = int(lines[1].split()[1])
    free = int(lines[2].split()[3])

    return (free, total)


########################################
# partitioning, filesystem creation
########################################

def partedCreateLabel(path):
    cmd = [PARTED,
           '-s',
           path,
           'mklabel',
           'msdos']
    checkedSystemCall(cmd)


def partedCreatePartition(path):
    cmd = [PARTED,
            '-s',
            path,
            'mkpart', 'primary', '0%', '100%']
    checkedSystemCall(cmd)

    waitForUdev()

    # some newer versions of parted tell the kernel that a device was created
    # the outside code does not expect that the device is created by this function
    if os.path.exists(path + '1'):
        kpartxRemove(path)


def formatPartition(path, fs):
    if fs == 'swap':
        cmd = [MKSWAP, '-f', path]
    elif fs == 'ext4':
        cmd = [MKFSEXT4, '-F', path]
    else:
        raise NotImplementedError('Unsupported filesystem type: {0}.'.format(fs))

    checkedSystemCall(cmd)


########################################
# mounting partitions
########################################
@contextmanager
def kpartx(path, retries=20, waitAfterFail=0.5):
    '''
    intended to be used as follows:
    with kpartx(path):
        doSomething()
    '''

    # kpartx regularly fails with 'device or resource busy errors'. That is a
    # timing issue. If you know a better way to avoid that issue please fix it.
    def retry(f, *args, **kwargs):
        i = 0
        while i < retries:
            i += 1
            try:
                f(*args, **kwargs)
                break
            except:
                if i == retries:
                    raise
            time.sleep(waitAfterFail)

    try:
        retry(kpartxAdd, path)
        yield
    finally:
        retry(kpartxRemove, path)
        kpartxRemove(path)


def kpartxAdd(path):
    cmd = [KPARTX, '-a', path]

    _, stderr = checkedSystemCall(cmd)
    if stderr: # XXX kpartx bug?
        msg = 'kpartx -a seems to have failed: It wrote something to stderr.'
        _logger.error(msg)
        raise RuntimeError(msg)

    waitForUdev()


def kpartxRemove(path):
    cmd = [KPARTX, '-d', path]

    _, stderr = checkedSystemCall(cmd)
    if stderr: # XXX kpartx bug?
        msg = 'kpartx -d seems to have failed: It wrote something to stderr.'
        _logger.error(msg)
        raise RuntimeError(msg)

    waitForUdev()


def waitForUdev():
    cmd = [UDEVADM, 'settle']
    checkedSystemCall(cmd)


@contextmanager
def mount(path, mountPoint):
    '''
    if mountPoint is None a temporary directory is used for mounting
    '''

    if mountPoint is None:
        temp = True
        mountPoint = tempfile.mkdtemp()
    else:
        temp = False

    try:
        _mount(path, mountPoint)
        yield mountPoint
    finally:
        _umount(mountPoint)
        if temp:
            os.rmdir(mountPoint)


def _mount(path, mountPoint):
    cmd = [MOUNT,
            path,
            mountPoint]
    checkedSystemCall(cmd)


def _umount(mountPoint):
    cmd = [UMOUNT,
            mountPoint]
    checkedSystemCall(cmd)

    # TODO do not fail if mountPoint is not mounted anywhere


########################################
# network
########################################


def getBridges():
    bridges = {}

    basePath = '/sys/class/net'
    for devName in os.listdir(basePath):
        devPath = os.path.join(basePath, devName)
        bridgePath = os.path.join(devPath, 'bridge')

        if not os.path.exists(bridgePath):
            continue

        bridges[devName] = os.listdir(os.path.join(devPath, 'brif'))

    return bridges


def addBridge(name):
    cmd = [BRCTL,
        'addbr',
        name]
    checkedSystemCall(cmd)

    cmd = [BRCTL,
            'stp',
            name,
            'on']
    checkedSystemCall(cmd)

    cmd = [BRCTL,
            'setbridgeprio',
            name,
            '65535']
    checkedSystemCall(cmd)

    cmd = [IP, 'link', 'set', 'up', name]
    checkedSystemCall(cmd)

    # TODO do not fail if the bridge already exists, has stp and bridgeprio correctly set and no interfaces attached


def delBridge(name):
    if not os.path.exists('/sys/class/net/{0}'.format(name)):
        return

    cmd = [IP, 'link', 'set', 'down', name]
    checkedSystemCall(cmd)

    cmd = [BRCTL,
        'delbr',
        name]
    checkedSystemCall(cmd)


def addBridgeInterface(name, interface):
    flushIPAddresses(interface)

    if os.path.exists('/sys/class/net/{0}/brif/{1}'.format(name, interface)):
        return

    cmd = [BRCTL,
            'addif',
            name,
            interface]
    checkedSystemCall(cmd)


def delBridgeInterface(name, interface):
    if not os.path.exists('/sys/class/net/{0}/brif/{1}'.format(name, interface)):
        return

    cmd = [BRCTL,
            'delif',
            name,
            interface]
    checkedSystemCall(cmd)


def addTapDevice(name):
    cmd = [IP,
           'tuntap',
           'add', 'dev', name, 'mode', 'tap']
    checkedSystemCall(cmd)

    cmd = [IP,
           'link',
           'set', 'dev', name, 'up']
    checkedSystemCall(cmd)


def delTapDevice(name):
    cmd = [IP,
           'tuntap',
           'del', 'dev', name, 'mode', 'tap']
    checkedSystemCall(cmd)


def getTapDevices():
    cmd = [IP,
           'tuntap']

    stdout, _ = checkedSystemCall(cmd)

    taps = []

    pattern = re.compile(r'^([a-z0-9_\-]+): tap.*')
    for line in stdout.splitlines():
        m = pattern.match(line)
        if m:
            taps.append(m.groups()[0])

    return taps


def flushIPAddresses(interface):
    cmd = [IP, 'addr', 'flush', 'dev', interface]
    checkedSystemCall(cmd)


def setIPAddresses(interface, addrs):
    flushIPAddresses(interface)

    for x in addrs:
        cmd = [IP, 'addr', 'add', x, 'dev', interface]
        checkedSystemCall(cmd)


