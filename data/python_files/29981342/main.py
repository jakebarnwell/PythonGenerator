import json
import logging
import os
import time
import traceback

from ..common import model
from ..common import pybsc

import image
import network
import vserver



VolumeGroup = 'veerezo'

_logger = logging.getLogger('main')



def exported(fn):
    fn.exported = True
    return fn


class API(object):
    def __init__(self, db):
        self.db = db


    @exported
    def reconfigureNetworks(self):
        networkConfig = model.getNetworkConfiguration(self.db)
        network.configureNetworks(networkConfig)


    @exported
    def createDiskImages(self, vmID):
        self._assertState(vmID, ['pending'])

        vmConfig = model.getVMConfiguration(self.db, vmID)
        disks = vmConfig['disks']

        rootDisk = filter((lambda x: x['type'] == 'root'), disks)[0]
        swapDisk = filter((lambda x: x['type'] == 'swap'), disks)[0]
        dataDisk = filter((lambda x: x['type'] == 'data'), disks)[0]

        image.createDiskImages(VolumeGroup, vmID, rootDisk['sizeMiB'], swapDisk['sizeMiB'], dataDisk['sizeMiB'], rootDisk['image'])


    @exported
    def prepareDiskImages(self, vmID, types):
        self._assertState(vmID, ['pending'])

        vmConfig = model.getVMConfiguration(self.db, vmID)

        for type in types:
            if type == 'root':
                rootDisk = filter((lambda x: x['type'] == 'root'), vmConfig['disks'])[0]
                image.prepareRootDisk(VolumeGroup, vmID, rootDisk['injector'], vmConfig['authorizedKeys'], vmConfig['networkConfiguration'])
            elif type == 'swap':
                image.prepareSwapDisk(VolumeGroup, vmID)
            elif type == 'data':
                image.prepareDataDisk(VolumeGroup, vmID)
            else:
                raise RuntimeError('Can\'t prepare disks of type "{0}".'.format(type))

        model.setVMState(self.db, vmID, 'stopped')


    @exported
    def removeDiskImages(self, vmID):
        self._assertState(vmID, ['stopped'])
        image.removeDiskImages(VolumeGroup, vmID)
        model.setVMState(self.db, vmID, 'pending')


    @exported
    def startVM(self, vmID):
        self._assertState(vmID, ['stopped'])

        vmConfig = model.getVMConfiguration(self.db, vmID)

        disks = vmConfig['disks']
        for x in disks:
            x['path'] = image.getMapperPath(VolumeGroup, vmID, x['type'])
            x['model'] = vmConfig['emulation']['diskModel']
        networkCards = vmConfig['networkCards']
        for x in networkCards:
            x['model'] = vmConfig['emulation']['nicModel']
        vserver.startVServer(vmID, vmConfig['emulation']['ramMiB'], disks, networkCards)

        model.setVMState(self.db, vmID, 'running')


    @exported
    def stopVM(self, vmID):
        self._assertState(vmID, ['stopped', 'stopping', 'running']) # stopped because then we are a NOOP, which is ok too.
        vserver.stopVServer(vmID)

        model.setVMState(self.db, vmID, 'stopping')


    @exported
    def killVM(self, vmID):
        self._assertState(vmID, ['stopped', 'stopping', 'running']) # stopped because then we are a NOOP, which is ok too.
        vserver.killVServer(vmID)
        model.setVMState(self.db, vmID, 'stopped')

        self.cleanupVM(vmID)


    @exported
    def cleanupVM(self, vmID):
        self._assertState(vmID, ['stopped'])
        vserver.cleanupVServer(vmID)


    @exported
    def deleteVM(self, vmID):
        # must work in all states.
        model.setVMState(self.db, vmID, 'stopped')

        try:
            self.killVM(vmID)
            self.cleanupVM(vmID)
            self.removeDiskImages(vmID)

            model.deleteVM(self.db, vmID)
        except:
            model.setVMState(self.db, vmID, 'pending')
            raise


    @exported
    def updateVMStates(self):
        running = set(model.getVMIDsInState(self.db, 'running'))
        stopping = set(model.getVMIDsInState(self.db, 'stopping'))
        for x in set.union(running, stopping):
            if not vserver.isVServerRunning(x):
                model.setVMState(self.db, x, 'stopped')
                self.cleanupVM(x) # works only in state 'stopped'


    def _assertState(self, vmID, validStates):
        vmState = model.getVMState(self.db, vmID)
        if vmState['state'] not in validStates:
            l = ['"{0}"'.format(x) for x in validStates]
            s = ', '.join(l)
            raise RuntimeError('Unexpected state "{0}" instead of one in: {1}.'.format(vmState['state'], s))


    def call(self, method, *args, **kwargs):
        fn = getattr(self, method)
        assert fn.exported

        fn(*args, **kwargs)



class WorkerApp(object):
    def __init__(self):
        self.db = model.getDBConnection()
        self.api = API(self.db)

        self.beanstalk = pybsc.BeanstalkClient()
        self.beanstalk.watch('veerezo-backend')
        self.beanstalk.ignore('default')

        self.shutdown = False

        model.updateDesign(self.db)
        if not os.path.exists('/var/run/veerezo'):
            os.mkdir('/var/run/veerezo')
            os.chmod('/var/run/veerezo', 0770)
        self.api.reconfigureNetworks()

        self.lastCleanup = time.time()
        self.cleanupInterval = 15.0


    def run(self):
        while not self.shutdown:
            if time.time() - self.lastCleanup > self.cleanupInterval:
                self.lastCleanup = time.time()

                self.api.updateVMStates()
                model.deleteOldJobs(self.db)

            try:
                jobID, job = self.beanstalk.reserve(timeout=1)
                _logger.info('got job with ID {0}: {1}.'.format(jobID, repr(job)))
            except pybsc.DeadlineSoonError:
                _logger.warning('beanstalkd warning: "DeadlineSoonError".')
                continue
            except pybsc.TimedOutError:
                continue
            except pybsc.ConnectionError:
                self.beanstalk.close()
                _logger.warning('lost connection to beanstalkd. Reconnecting in a few seconds...')
                time.sleep(5)
                self.beanstalk.connect()
                continue

            try:
                self._processJob(job)

                self.beanstalk.delete(jobID)
                try:
                    model.setJobState(self.db, jobID, 'suceeded')
                except KeyError:
                    # ignore missing job entry in database
                    # got job id from beanstalkd after loooooong pause?
                    pass
            except:
                s = traceback.format_exc()
                _logger.error('Encountered an error while processing job with ID {0}, data {1}: {2}.'.format(jobID, repr(job), s))

                self.beanstalk.bury(jobID)

                try:
                    model.setJobState(self.db, jobID, 'failed')
                except KeyError:
                    pass


    def _processJob(self, job):
        job = json.loads(job)

        method = job['method']
        args = job.get('args', [])
        kwargs = job.get('kwargs', {})

        self.api.call(method, *args, **kwargs)



    def close(self):
        self.beanstalk.close()


def setupLogging():
    logging.basicConfig(level=logging.DEBUG, filename='/var/log/veerezo-backend-worker.log')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(name)s:%(levelname)s: %(message)s'))
    logging.getLogger('').addHandler(console)

    class ConsoleFilter(object):
        def filter(self, record):
            if record.filename.endswith('lowleveltools.py'):
                return False
            return True
    console.addFilter(ConsoleFilter())


def main():
    setupLogging()

    worker = WorkerApp()
    worker.run()
    worker.close()



