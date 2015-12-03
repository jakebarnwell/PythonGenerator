import subprocess as sp
import os
import logging
import time
import glob
from lowleveltools import *
from inject import inject as injectIntoRootDisk


_logger = logging.getLogger('image')


def createDiskImages(vg, id, rootSize, swapSize, dataSize, source):
    try:
        t0 = time.time()

        rootDisk = '{0}_root'.format(id)
        swapDisk = '{0}_swap'.format(id)
        dataDisk = '{0}_data'.format(id)

        lvcreateSnapshot(vg, source, rootSize, rootDisk)
        lvcreate(vg, swapSize, swapDisk)
        lvcreate(vg, dataSize, dataDisk)

        waitForUdev()

        dt = time.time() - t0
        _logger.info('Created disk images for "vm{0}" ({1:.1f}s).'.format(id, dt))
    except:
        _logger.error('Failed to create disk images for "vm{0}". Cleaning up...'.format(id))
        removeDiskImages(vg, id)
        raise


def getMapperPath(vg, id, disk=None, partition=None):
    p = '/dev/mapper/{0}-{1}'.format(vg, id)

    if disk is not None:
        p += '_' + disk

    if partition:
        assert disk is not None

        p += str(partition)

    return p


def removeDiskImages(vg, id):
    rootDisk = '{0}_root'.format(id)
    swapDisk = '{0}_swap'.format(id)
    dataDisk = '{0}_data'.format(id)

    waitForUdev() # some udev trigger sometimes prevents us from removing the logical volumes. This should avoid the internal retries of lvremove.

    for disk in [rootDisk, swapDisk, dataDisk]:
        _removeDiskImage(vg, id, disk)


def _removeDiskImage(vg, id, disk):
    try:
        _removeDiskImage_recoverFromFailure_kpartx(vg, id, disk)
        lvremove(vg, disk)

        _logger.info('Removed disk "{0}" of "vm{1}".'.format(disk, id))
    except:
        msg = 'Could not remove disk "{0}" of "vm{1}". This may lead to other errors later.'.format(disk, id)
        _logger.error(msg)


def _removeDiskImage_recoverFromFailure_kpartx(vg, id, disk):
    diskPath = getMapperPath(vg, disk)
    if not glob.glob(diskPath + '?'):
        return

    msg = 'Trying to remove disk "{0}" of "vm{1}" even though there is still at least one partition entry there. Something is broken... Trying to recover.'.format(disk, id)
    _logger.error(msg)

    retries = 5
    for i in range(retries):
        try:
            kpartxRemove(diskPath)
            return
        except:
            pass
        time.sleep(0.5)

    msg = 'Failed to recover from kpartx error. Giving up on disk "{0}" of "vm{1}".'.format(disk, id)
    _logger.error(msg)


def prepareRootDisk(vg, id, injectorName, authorizedKeys, networkConfig):
    expectedPathsOnRootDisk = ['bin', 'etc', 'lib', 'root']

    try:
        t0 = time.time()
        disk = 'root'
        blockDev = getMapperPath(vg, id, disk)
        with kpartx(blockDev):
            for x in glob.glob(getMapperPath(vg, id, disk, '?')):
                with mount(x, mountPoint=None) as mountPoint:
                    checks = [os.path.exists(os.path.join(mountPoint, y)) for y in expectedPathsOnRootDisk]
                    if not all(checks):
                        continue

                    # TODO return finger prints of public keys
                    injectIntoRootDisk(injectorName, mountPoint, id, authorizedKeys, networkConfig)
                    break

        dt = time.time() - t0
        _logger.info('Prepared root disk of "vm{0}" ({1:.1f}s).'.format(id, dt))
    except:
        _logger.error('Failed to prepare root disk of "vm{0}".'.format(id))
        raise


def prepareSwapDisk(vg, id):
    try:
        t0 = time.time()
        disk = 'swap'
        blockDev = getMapperPath(vg, id, disk)

        partedCreateLabel(blockDev)
        partedCreatePartition(blockDev)

        with kpartx(blockDev):
            formatPartition(getMapperPath(vg, id, disk, 1), 'swap')

        dt = time.time() - t0
        _logger.info('Prepared swap disk of "vm{0}" ({1:.1f}s).'.format(id, dt))
    except:
        _logger.error('Failed to prepare swap disk of "vm{0}".'.format(id))
        raise


def prepareDataDisk(vg, id):
    try:
        t0 = time.time()
        disk = 'data'
        blockDev = getMapperPath(vg, id, disk)

        partedCreateLabel(blockDev)
        partedCreatePartition(blockDev)

        with kpartx(blockDev):
            formatPartition(getMapperPath(vg, id, disk, 1), 'ext4')

        dt = time.time() - t0
        _logger.info('Prepared data disk of "vm{0}" ({1:.1f}s).'.format(disk, dt))
    except:
        _logger.error('Failed to prepare data disk of "vm{0}".'.format(id))
        raise


