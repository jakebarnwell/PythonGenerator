import os
import time
import signal
import logging
import network
from kvmcommand import KVMCommand, KVM
from kvmmonitor import KVMMonitor
from lowleveltools import checkedSystemCall


_RunPath = '/var/run/veerezo'
_logger = logging.getLogger('vserver')
_TerminationTimeout = 15.0


def startVServer(id, ramMiB, disks, networkCards):
    if isVServerRunning(id):
        _logger.warning('Tried to start vserver "vm{0}" even though it was already running. Doing nothing instead.'.format(id))
        return

    cleanupVServer(id)

    name = _getVMName(id)
    try:
        kvm = KVMCommand()

        kvm.setDaemon(_getPIDFilename(name))
        kvm.enableMonitor(_getMonitorFilename(name))
        kvm.setName(name)
        kvm.setRAM(ramMiB)
        kvm.setCPUCount(1)
        kvm.disableVGAAndSetupSerialConsole(_getSerialFilename(name))
        #kvm.enableVNC(_getVNCFilename(name))

        for i, x in enumerate(disks):
            if i == 0:
                boot = True
            else:
                boot = False
            kvm.addDisk(x['path'], i, boot, x.get('model', 'ide'))

        networks = [x['network'] for x in networkCards]
        taps = network.configureVServerTaps(id, networks)
        for i, x in enumerate(taps):
            kvm.addNIC(x, i, networkCards[i].get('model', 'e1000'), _createLocalUniqueMACAddress(id, i))

        checkedSystemCall(kvm.getCommand())
        _logger.info('Started vserver "{0}".'.format(name))
    except:
        _logger.error('Could not start vserver "{0}".'.format(name))
        network.removeVServerTaps(name)
        raise


def _createLocalUniqueMACAddress(id, networkCardIndex):
    assert 0 <= id <= 0xFFFFFF
    assert 0 <= networkCardIndex < 256

    l = [
        0x52,
        0x54,
        (id >> 16) & 0xFF,
        (id >> 8) & 0xFF,
        id & 0xFF,
        networkCardIndex
    ]

    for i in range(6):
        l[i] = '{0:02x}'.format(l[i])

    return ':'.join(l)



def stopVServer(id):
    '''
    Asks the vserver to shutdown itself.
    '''
    name = _getVMName(id)
    try:
        if not isVServerRunning(id):
            return

        kvmMonitor = KVMMonitor(_getMonitorFilename(name))
        kvmMonitor.commandSimple('system_powerdown')
        kvmMonitor.close()

        _logger.info('Told vserver "{0}" to shutdown itself.'.format(name))
    except:
        _logger.error('Failed to tell vserver "{0}" to shutdown itself.'.format(name))
        raise


def killVServer(id):
    '''
    Kills a running vserver and makes sure it's really dead.
    '''
    name = _getVMName(id)
    if not isVServerRunning(id):
        return

    pid = _getVServerPID(name)
    os.kill(pid, signal.SIGTERM) # use kvm monitor instead of this

    _logger.warning('Terminated vserver "{0}".'.format(name))

    t0 = time.time()
    while isVServerRunning(id):
        if time.time() - t0 > _TerminationTimeout:
            try:
                os.kill(pid, signal.SIGKILL)
                msg = '''Kill -9 'ed vserver "{0}" because it did not shutdown itself or survied a kill.'''.format(name)
                _logger.warning(msg)
            except:
                pass
            break

        time.sleep(0.1)

    if isVServerRunning(id):
        msg = 'Kill -9 did not kill vserver "{0}". Manual intervention needed.'.format(name)
        _logger.error(msg)


def cleanupVServer(id):
    '''
    Cleans up any unused files and network devices
    '''
    name = _getVMName(id)
    network.removeVServerTaps(id)

    _cleanupRunFiles(name)



def isVServerRunning(id):
    name = _getVMName(id)
    try:
        pid = _getVServerPID(name)
    except:
        # lets hope nobody removed the PID file...
        _logger.debug('isVServerRunning: could not find pid for "{0}".'.format(name))
        return False

    procPath = os.path.join('/proc', str(pid), 'cmdline')
    if not os.path.exists(procPath):
        _logger.debug('isVServerRunning: did not find process in /proc for "{0}".'.format(name))
        return False

    try:
        with open(procPath) as f:
            cmdline = f.read()
    except IOError:
        # probably race condition: process died since we checked if the procPath existed...
        _logger.debug('isVServerRunning: found process in /proc but could not read cmdline file for "{0}"'.format(name))
        return False

    if not cmdline.startswith('{0}\x00'.format(KVM)):
        _logger.debug('isVServerRunning: wrong process name for "{0}".'.format(name))
        return False

    if not '\x00-name\x00{0}\x00'.format(name) in cmdline:
        _logger.debug('isVServerRunning: wrong vm name for "{0}".'.format(name))
        return False

    _logger.debug('isVServerRunning: "{0}" is running.'.format(name))
    return True


def _getVServerPID(name):
    pidFilename = _getPIDFilename(name)
    if not os.path.exists(pidFilename):
        raise RuntimeError('could not find PID file')

    with open(pidFilename) as f:
        pid = f.read()
        return int(pid)


def _cleanupRunFiles(name):
    for p in [_getPIDFilename(name),
              _getMonitorFilename(name),
              _getSerialFilename(name),
              _getVNCFilename(name),
             ]:
        if os.path.exists(p):
            os.unlink(p)


def _getVMName(id):
    return 'vm{0}'.format(id)


def _getPIDFilename(name):
    return os.path.join(_RunPath, '{0}.pid'.format(name))


def _getMonitorFilename(name):
    return os.path.join(_RunPath, '{0}.monitor'.format(name))


def _getSerialFilename(name):
    return os.path.join(_RunPath, '{0}.serial'.format(name))


def _getVNCFilename(name):
    return os.path.join(_RunPath, '{0}.vnc'.format(name))



