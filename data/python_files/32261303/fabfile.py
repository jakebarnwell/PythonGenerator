import StringIO
import getpass
import hashlib
import os.path
import socket
import string
import tempfile
import time

from fabric.api import *
from fabric.network import disconnect_all
from fabric.colors import green

env.user = 'root'

content = StringIO.StringIO

HOSTS = '''
127.0.0.1 localhost
127.0.0.1 %(fqdn)s %(host)s

::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
'''

ROOT_CRED_BAG = '''
{
  "id": "root-credentials",
  "password": "%(password)s",
  "ssh-keys": [%(keys)s]
}
'''

def _get_credentials(root_password, ssh_keys):
    if not root_password:
        root_password = getpass.getpass('Root password for infrastructure: ')
    if ssh_keys is None:
        ssh_keys = []
        while True:
            key = prompt('Enter a root ssh pubkey line (empty line when done):').strip()
            if not key:
                break
            ssh_keys.append(key)
    ssh_keys = ','.join('"%s"' % k for k in ssh_keys)
    print "KEYS", ssh_keys
    root_password = local('openssl passwd -1 "%s"' % root_password, capture=True)
    return root_password, ssh_keys

#
# Reconfigure the hostname/mailname of a machine. Step zero of
# bootstrapping VMs.
#
@task
def hostname(fqdn=None):
    run('hostname')  # Just to force a connection
    if not fqdn:
        q = 'New FQDN for host:'
        if env.host[0] in string.digits:
            fqdn = prompt(q)
        else:
            fqdn = prompt(q, default=env.host)
    host, domain = fqdn.split('.', 1)
    put(content(host), '/etc/hostname')
    put(content(fqdn), '/etc/mailname')
    put(content(HOSTS % {'fqdn': fqdn, 'host': host}), '/etc/hosts')
    #run('reboot')
    #disconnect_all()

@task
def bootstrap():
    run('hostname')
    local('knife bootstrap %s -x root --template-file ./debian-ubuntu-apt.erb' % env.host)
    run('chef-client')
    run('chef-client')

#
# Push all chef respository data to the chef server.
#
@task
def sync():
    local('knife cookbook upload -a')
    for line in local('find roles -name \'*.rb\' -or -name \'*.json\'',
                      capture=True).strip().split('\n'):
        local('knife role from file ' + line.strip())
    bags = set()
    for line in local('find data_bags -mindepth 1 -maxdepth 1 -type d',
                      capture=True).split('\n'):
        bag = line.strip()[10:]
        local('knife data bag create %s' % bag)
    for line in local('find data_bags -name \'*.json\'',
                      capture=True).strip().split('\n'):
        line = line.split('/')
        if len(line) != 3:
            continue
        _, bag, item = line
        local('knife data bag from file %s %s' % (bag, item))

#
# Update the root credentials data bag.
#
@task
def change_root_credentials(root_password=None,
                            ssh_keys=None):
    if not root_password:
        root_password, ssh_keys = _get_credentials(root_password, ssh_keys)
    with tempfile.NamedTemporaryFile(suffix='.json') as f:
        print ROOT_CRED_BAG % {'password': root_password,
                               'keys': ssh_keys}
        f.write(ROOT_CRED_BAG % {'password': root_password,
                                 'keys': ssh_keys})
        f.flush()
        local('knife data bag create common')
        local('knife data bag from file common ' + f.name)
