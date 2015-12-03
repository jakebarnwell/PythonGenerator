import web
import json
import re
import base64
import validators

from ..common import model
from ..common import pybsc


if not hasattr(web, 'nocontent'):
    def _noContent():
        web.ctx.status = '204 No Content'
    web.nocontent = _noContent



def renderJSON(data):
    return json.dumps(data, indent=4) + '\n'


def renderHTML(data):
    # TODO FIXME XXX
    # really ugly hack!
    # write a real html generator
    import re

    l = ['<html><body>']

    data = json.dumps(data, indent=4).replace('\n', '<br />').replace('    ', '&nbsp;' * 4)
    for i in range(0, len(urls), 2):
        urlRegEx = '"' + urls[i] + '"'
        if urlRegEx == r'/':
            continue
        data = re.sub(urlRegEx, r'<a href=\g<0>>\g<0></a>', data)


    l.append(data)

    l.append('</body></html>')
    return '<br />'.join(l)


def mimerender(targetFunction):
    def wrapper(*args, **kwargs):
        acceptString = web.ctx.env.get('HTTP_ACCEPT', '')

        idxHTML = acceptString.find('text/html')
        idxJSON = acceptString.find('application/json')

        if idxHTML == -1:
            idxHTML = 2 ** 30
        if idxJSON == -1:
            idxJSON = 2 ** 29

        data = targetFunction(*args, **kwargs)
        if web.ctx.status == '204 No Content':
            return ''

        if idxHTML < idxJSON:
            web.header('Content-Type', 'text/html')
            return renderHTML(data)
        else:
            web.header('Content-Type', 'application/json')
            return renderJSON(data)
    return wrapper


#
# basic idea:
#     GET returns a resource
#     POST modifies a resource, usually creating a new path
#     PUT updates a resource in place
#     DELETE removes a resource
#


urls = (
    r'/', 'Index',

    r'/images', 'AllImages',
    r'/images/(\d+)', 'Image',

    r'/sshkeys', 'AllSSHKeys',
    r'/sshkeys/(\d+)', 'SSHKey',

    r'/networks', 'AllNetworks',
    r'/networks/(\d+)', 'Network',

    r'/vms', 'AllVMs',
    r'/vms/(\d+)', 'VM',
    r'/vms/(\d+)/actions', 'AllVMActions',
    r'/vms/(\d+)/actions/([a-z]+)', 'VMAction',
    r'/vms/(\d+)/state', 'VMState',
    r'/vms/(\d+)/settings', 'AllVMSettings',
    r'/vms/(\d+)/settings/([a-z]+)', 'VMSetting',

    r'/jobs/(\d+)', 'Job',
)


class Index(object):
    @mimerender
    def GET(self):
        result = [
            {'images': '/images'},
            {'networks': '/networks'},
            {'sshkeys': '/sshkeys'},
            {'vms': '/vms'},
        ]
        return result


class AllImages(object):
    @mimerender
    def GET(self):
        imageIDs = model.getImageIDs(web.ctx.veerezoDB)

        result = []
        for id in imageIDs:
            d = {}
            d['image'] = '/images/{0}'.format(id)

            result.append(d)

        return result


class Image(object):
    @mimerender
    def GET(self, id):
        try:
            id = int(id)

            return model.getImage(web.ctx.veerezoDB, id)
        except (ValueError, KeyError):
            web.notfound()
            return None


class AllSSHKeys(object):
    @mimerender
    def GET(self):
        sshKeyIDs = model.getSSHKeyIDs(web.ctx.veerezoDB, web.ctx.username)

        result = []
        for x in sshKeyIDs:
            d = {}
            d['sshkey'] = '/sshkeys/{0}'.format(x)

            result.append(d)
        return result


    @mimerender
    def POST(self):
        try:
            data = json.loads(web.data())
            validators.validate(data, validators.AddSSHKey)
        except ValueError as e:
            web.badrequest()
            return {'error': 'ValueError: {0}'.format(e)}

        key = data['key']
        id = model.addSSHKey(web.ctx.veerezoDB, key, web.ctx.username)

        url = '/sshkeys/{0}'.format(id)
        web.header('Content-Location', url)
        web.created()

        d = {}
        d['sshkey'] = url
        return d


class SSHKey(object):
    @mimerender
    def GET(self, id):
        try:
            id = int(id)

            sshkey = model.getSSHKey(web.ctx.veerezoDB, id)
            if sshkey['user'] != web.ctx.username:
                web.forbidden()
                return None

            return sshkey
        except (KeyError, ValueError):
            web.notfound()
            return None


    @mimerender
    def DELETE(self, id):
        try:
            id = int(id)

            sshkey = model.getSSHKey(web.ctx.veerezoDB, id)
            if sshkey['user'] != web.ctx.username:
                web.forbidden()
                return None

            model.deleteSSHKey(web.ctx.veerezoDB, id)
        except:
            web.notfound()
            return None

        web.nocontent()
        return None


class AllNetworks(object):
    @mimerender
    def GET(self):
        try:
            data = web.input(tag=[])

            if data.tag:
                tagFilter = data.tag
                # TODO validate
            else:
                tagFilter = None
        except (ValueError, KeyError):
            web.badrequest()
            return None

        networkIDs = model.getNetworkIDs(web.ctx.veerezoDB, web.ctx.username, tagFilter)

        result = []
        for id in networkIDs:
            d = {}
            d['network'] = '/networks/{0}'.format(id)

            result.append(d)

        return result


    @mimerender
    def POST(self):
        try:
            data = json.loads(web.data())
            validators.validate(data, validators.AddNetwork)
        except ValueError as e:
            web.badrequest()
            return {'error': 'ValueError: {0}'.format(e.message)}

        devices = data.get('devices', [])
        tags = data.get('tags', [])

        id = model.addNetwork(web.ctx.veerezoDB, devices, web.ctx.username, tags)
        jobID = web.ctx.postBackendJob('reconfigureNetworks')
        addJobIDsHeader([jobID])

        url = '/networks/{0}'.format(id)
        web.header('Content-Location', url)
        web.created()

        d = {}
        d['network'] = url
        return d


class Network(object):
    @mimerender
    def GET(self, id):
        try:
            id = int(id)

            network = model.getNetwork(web.ctx.veerezoDB, id)
            if network['user'] != web.ctx.username:
                web.forbidden()
                return None

            return network
        except (ValueError, KeyError):
            web.notfound()
            return None


    @mimerender
    def DELETE(self, id):
        try:
            id = int(id)

            network = model.getNetwork(web.ctx.veerezoDB, id)
            if network['user'] != web.ctx.username:
                web.forbidden()
                return None

            model.deleteNetwork(web.ctx.veerezoDB, id)
        except (ValueError, KeyError):
            web.notfound()
            return None

        jobID = web.ctx.postBackendJob('reconfigureNetworks')
        addJobIDsHeader([jobID])

        web.nocontent()
        return None


class AllVMs(object):
    @mimerender
    def GET(self):
        try:
            data = web.input(tag=[])

            if data.tag:
                tagFilter = data.tag
                # TODO validate
            else:
                tagFilter = None
        except (ValueError, KeyError):
            web.badrequest()
            return None

        vmIDs = model.getVMIDs(web.ctx.veerezoDB, web.ctx.username, tagFilter)

        result = []
        for id in vmIDs:
            d = {}
            d['vm'] = '/vms/{0}'.format(id)

            result.append(d)

        return result


    @mimerender
    def POST(self):
        try:
            config = json.loads(web.data())
            validators.validate(config, validators.AddVM)

            tags = config.get('tags', [])

            image = config['image']
            m = re.match('^/images/(\d+)$', image)
            if not m:
                raise ValueError('Invalid image definition')
            image = int(m.groups()[0])
            _ = model.getImage(web.ctx.veerezoDB, image) # check for image existance
            image = 'image-{0}'.format(image)

            ramMiB = config['ramMiB']
            networkConfiguration = config['networkConfiguration']

            networkCards = []
            validNetworkIDs = model.getNetworkIDs(web.ctx.veerezoDB, web.ctx.username) # TODO somehow support 'global' / 'shared' networks everyone may use
            validNetworkIDs.append(1) # TODO XXX FIXME temporary workaround to allow VMs access to the outside world without 'global' / 'share'd networks
            for x in config['networkCards']:
                if x is None:
                    networkCards.append(None)
                else:
                    m = re.match(r'^/networks/(\d+)$', x)
                    if not m:
                        raise ValueError('At least one networkCard has an invalid network definition.')
                    id = int(m.groups()[0])
                    if id not in validNetworkIDs:
                        raise ValueError('At least one networkCard is attached to an unknown network.')
                    networkCards.append(id)
        except (ValueError, KeyError) as e:
            web.badrequest()
            return {'error': 'ValueError: {0}'.format(e.message)}


        # we have to add the DB entry here so that we don't get confused by the async nature of the job queue
        id = model.addVM(web.ctx.veerezoDB, image, ramMiB, networkCards, networkConfiguration, web.ctx.username, tags)

        jobIDs = []
        jobIDs.append(web.ctx.postBackendJob('createDiskImages', id))
        jobIDs.append(web.ctx.postBackendJob('prepareDiskImages', id, ['root', 'swap', 'data']))

        addJobIDsHeader(jobIDs)

        url = '/vms/{0}'.format(id)
        web.header('Content-Location', url)
        web.created()

        d = {}
        d['vm'] = url
        return d



class VMBase(object):
    @mimerender
    def GET(self, id, *args):
        if not hasattr(self, '_get'):
            web.nomethod()
            return None

        try:
            id = int(id)

            vm = model.getVM(web.ctx.veerezoDB, id)
            if vm['user'] != web.ctx.username:
                web.forbidden()
                return None
        except (ValueError, KeyError):
            web.notfound()
            return None

        return self._get(id, vm, *args)


class VM(VMBase):
    def _get(self, id, vm):
        l = [
            {'actions': '/vms/{0}/actions'.format(id)},
            {'state': '/vms/{0}/state'.format(id)},
            {'settings': '/vms/{0}/settings'.format(id)},
        ]

        return l


    @mimerender
    def DELETE(self, id):
        try:
            id = int(id)
            vm = model.getVM(web.ctx.veerezoDB, id)

            if vm['user'] != web.ctx.username:
                web.forbidden()
                return None
        except ValueError:
            web.notfound()
            return None

        # we must not delete the DB entry here so that we don't get confused by the async nature of the job queue
        jobID = web.ctx.postBackendJob('deleteVM', id)
        addJobIDsHeader([jobID])

        web.nocontent()
        return None


class AllVMActions(VMBase):
    def _get(self, id, vm):
        l = [
            {'start': '/vms/{0}/actions/start'.format(id)},
            {'stop': '/vms/{0}/actions/stop'.format(id)},
            {'kill': '/vms/{0}/actions/kill'.format(id)},
            {'rebuild': '/vms/{0}/actions/rebuild'.format(id)},
        ]

        return l


class VMAction(VMBase):
    @mimerender
    def POST(self, id, action):
        try:
            id = int(id)
            vm = model.getVM(web.ctx.veerezoDB, id)

            if vm['user'] != web.ctx.username:
                web.forbidden()
                return None
        except (ValueError, KeyError):
            web.notfound()
            return None

        args = [id]
        kwargs = {}
        jobIDs = []

        if action == 'start':
            method = 'startVM'
        elif action == 'stop':
            method = 'stopVM'
        elif action == 'kill':
            method = 'killVM'
        elif action == 'rebuild':
            # TODO in the long term we would like to keep 'data'...
            jobIDs.append(web.ctx.postBackendJob('removeDiskImages', id))
            jobIDs.append(web.ctx.postBackendJob('createDiskImages', id))

            method = 'prepareDiskImages'
            args.append(['root', 'swap', 'data'])
        else:
            web.notfound()
            return None

        jobIDs.append(web.ctx.postBackendJob(method, *args, **kwargs))
        addJobIDsHeader(jobIDs)

        web.accepted()
        return None


class VMState(VMBase):
    def _get(self, id, vm):
        try:
            return model.getVMState(web.ctx.veerezoDB, id)
        except (ValueError, KeyError):
            web.notfound()
            return None


class AllVMSettings(VMBase):
    def _get(self, id, vm):
        l = []
        for k in VMSetting.Settings:
            d = {}
            d[k] = '/vms/{0}/settings/{1}'.format(id, k)
            l.append(d)

        return l


class VMSetting(VMBase):
    Settings = {
        'networkconfiguration': 'NetworkConfiguration',
        'networkcards': 'NetworkCards',
        'emulation': 'Emulation',
    }

    def _get(self, id, vm, setting):
        if setting not in self.Settings:
            web.notfound()
            return None

        fn = '_get' + self.Settings[setting]
        f = getattr(self, fn)
        return f(id, vm)


    def _getNetworkConfiguration(self, id, vm):
        return vm['networkConfiguration']


    def _getNetworkCards(self, id, vm):
        l = []
        for x in vm['networkCards']:
            d = dict(x)
            ref = d['networkRef']
            del d['networkRef']
            if ref is None:
                l.append(None)
            else:
                networkID = int(ref.split('-')[-1])
                d['network'] = '/networks/{0}'.format(networkID)
                l.append(d)

        return l


    def _getEmulation(self, id, vm):
        return vm['emulation']


    @mimerender
    def PUT(self, id, setting):
        if setting not in self.Settings:
            web.notfound()
            return None

        try:
            configData = json.loads(web.data())

            id = int(id)
            vm = model.getVM(web.ctx.veerezoDB, id)
            if vm['user'] != web.ctx.username:
                web.forbidden()
                return None
        except (ValueError, KeyError):
            web.notfound()
            return None

        fn = '_put' + self.Settings[setting]
        f = getattr(self, fn)
        try:
            f(id, vm, configData)
        except ValueError as e:
            web.badrequest()
            return {'error': 'ValueError: {0}'.format(e.message)}

        web.nocontent()
        return None


    def _putNetworkConfiguration(self, id, vm, configData):
        validators.validate(configData, validators.VMSettingsNetworkConfiguration)

        d = {}
        d['networkConfiguration'] = configData
        model.updateVM(web.ctx.veerezoDB, id, d)


    def _putNetworkCards(self, id, vm, configData):
        validators.validate(configData, validators.VMSettingsNetworkCards)

        d = {}
        d['networkCards'] = configData
        model.updateVM(web.ctx.veerezoDB, id, d)


    def _putEmulation(self, id, vm, configData):
        validators.validate(configData, validators.VMSettingsEmulation)

        d = {}
        d['emulation'] = configData
        model.updateVM(web.ctx.veerezoDB, id, d)


class Job(object):
    @mimerender
    def GET(self, id):
        try:
            id = int(id)
            job = model.getJob(web.ctx.veerezoDB, id)
        except (ValueError, KeyError):
            web.notfound()
            return None

        return job


def checkUserAuth():
    auth = web.ctx.env.get('HTTP_AUTHORIZATION', None)
    if not auth:
        raise ValueError()

    auth = re.sub('^Basic ', '', auth)
    username, password = base64.decodestring(auth).split(':')

    # TODO actually check credentials

    return username


def myProcessor(handler):
    web.ctx.veerezoDB = model.getDBConnection()
    try:
        username = checkUserAuth()
        web.ctx.username = username
    except ValueError:
        web.header('WWW-Authenticate', 'Basic realm="Veerezo"')
        web.unauthorized()
        return 'Access denied'

    web.ctx.beanstalk = pybsc.BeanstalkClient()

    def postBackendJob(method, *args, **kwargs):
        d = {}
        d['method'] = method
        d['args'] = args
        d['kwargs'] = kwargs

        jobID = web.ctx.beanstalk.put(json.dumps(d), ttr=60, tube='veerezo-backend')
        model.addJob(web.ctx.veerezoDB, jobID)

        return jobID
    web.ctx.postBackendJob = postBackendJob
    result = handler()
    return result


def addJobIDsHeader(jobIDs):
    k = 'X-Job-IDs'
    v = ', '.join([str(x) for x in jobIDs])

    web.header(k, v)


def main():
    app = web.application(urls, globals())
    app.add_processor(myProcessor)
    app.run()

