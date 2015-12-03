import tempfile
from dulwich.client import get_transport_and_path
from dulwich.repo import Repo
from gevent import Timeout
import os
from pip.exceptions import InstallationError
from pip.req import parse_requirements
import re
import requests
import simplejson as json
import cache
import settings
import logging
from urlparse import urlparse
from mercurial.commands import clone as hg_clone
from mercurial import ui


log = logging.getLogger(__name__)


class ClientError(Exception):
    pass


class ClientTimeoutError(ClientError):
    pass


class TemporaryDirectory(object):

    def __init__(self, name=None):
        self.name = name
        if not self.name:
            self.name = tempfile.mkdtemp()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass
        # do not delete the temp folder. this is a job for cron
        # shutil.rmtree(self.name)


def _temp_directory():
    tmp = settings.SOURCE_TEMP
    if not os.path.exists(tmp):
        os.mkdir(tmp, 0700)
    return TemporaryDirectory(tempfile.mkdtemp(dir=tmp))


class SourceClient(object):
    def __init__(self, url, repo_type=None):
        self.url = url
        self.files = []
        self.discovered = {}
        self.repo_type = repo_type
        self.default_vcs = repo_type

        if repo_type and repo_type not in ['hg', 'git']:
            raise ValueError('Invalid repository type')

        # options for parse_requirements
        self.skip_requirements_regex = '^(-r|--requirement)'

        log.info('%s with client URL "%s"', type(self), self.url)

    def cache(self):
        cache.set(cache.make_key(self.url), {
            'files': self.files,
            'discovered': self.discovered,
        })

    def fetch(self):
        if self.repo_type == 'hg':
            _fetch_mercurial(self)
        elif self.repo_type == 'git':
            _fetch_git(self)

        if 'github' in self.url:
            _fetch_github(self)

        if 'bitbucket' in self.url:
            _fetch_bitbucket(self)


def _find_requires(client, dir):
    """
    Look for a requirements file and discover ``requires``
    """

    pn = re.compile(r'.*require.*\.txt$', re.I)
    requires = []

    for root, dirs, files in os.walk(dir):
        for filename in files:
            if re.match(pn, filename):
                try:
                    for req in parse_requirements(
                            os.path.join(dir, root, filename),
                            options=client):
                        requires.append(str(req.req))
                except InstallationError:
                    log.exception('ignored')

    client.discovered['requires'] = requires


def _fetch_mercurial(client):
    if not settings.DEBUG:
        if client.url.startswith('/') or os.path.exists(client.url):
            raise ClientError('File urls not allowed')

    with _temp_directory() as tmpdir:
        out_dir = os.path.join(tmpdir.name, 'src')

        with Timeout(settings.CLONE_TIMEOUT):
            hg_clone(ui.ui(), client.url, dest=out_dir)

        for root, dirs, files in os.walk(out_dir):
            if '.hg' in dirs:
                dirs.remove('.hg')

            for file in files:
                client.files.append(os.path.join(root, file).replace(
                    out_dir, '', 1).lstrip('/'))

        _find_requires(client, out_dir)


def _fetch_bitbucket(client, session=None):
    if not session:
        session = requests.session()
        session.headers.update({'Accept': 'application/json'})

    path = urlparse(client.url).path
    if not path:
        raise ValueError('Invalid path')
    parts = path.lstrip('/').split('/')
    if not parts or len(parts) < 2:
        raise ValueError('Bitbucket url must include a username and repo')

    client.author = parts[0]
    client.name = parts[1]

    if not client.name or not client.author:
        raise ValueError('Error parsing URL. Ensure the URL contains the'
                         'username and repo on Bitbucket.')

    client.discovered['author'] = client.author
    client.discovered['name'] = client.name

    try:
        url = settings.BITBUCKET_URL + '/repositories/{}/{}'.format(
            client.author,
            client.name,
        )

        response = session.request(
            'get',
            url,
            timeout=settings.API_TIMEOUT,
        )
    except requests.Timeout:
        raise ClientTimeoutError('Timeout while reading from '
                                 'Bitbuckets\'s repo API')

    if response.status_code != 200:
        raise ClientError('Server error {0}'.format(response.status_code))

    repo = json.loads(response.content)

    client.discovered['description'] = repo['description']
    client.discovered['url'] = repo['website']

    if 'fork_of' in repo and repo['fork_of']:
        client.discovered['description'] = repo['fork_of']['description']
        client.discovered['url'] = repo['fork_of']['website']


def _fetch_git(client):
    if not settings.DEBUG:
        if client.url.startswith('/') or os.path.exists(client.url):
            raise ClientError('File urls not allowed')

    with _temp_directory() as temp_dir:
        out_dir = os.path.join(temp_dir.name, 'src')

        git, path = get_transport_and_path(client.url)
        local = Repo.init(out_dir, mkdir=True)

        with Timeout(settings.CLONE_TIMEOUT):
            git.fetch(path, local)

        for root, dirs, files in os.walk(out_dir):
            if '.git' in dirs:
                dirs.remove('.git')

            for file in files:
                client.files.append(os.path.join(root, file).replace(
                    out_dir, '', 1).lstrip('/'))

        _find_requires(client, out_dir)


def _fetch_github(client, session=None):
    if not session:
        session = requests.session()
        session.headers.update({'Accept': 'application/json'})

    if '://' in client.url:
        # handle urls with schemes

        path = urlparse(client.url).path
        if not path:
            raise ValueError('Invalid path')
        parts = path.lstrip('/').split('/')
        if not parts or len(parts) < 2:
            raise ValueError('Github url must include a username and repo')

        client.author = parts[0]
        client.name = parts[1]
    else:
        # no scheme, this breaks urlparse

        parts = client.url.split(':')[-1]
        if not parts or '/' not in parts:
            raise ValueError('Github url must include a username and repo')

        parts = parts.split('/')
        if len(parts) < 2:
            raise ValueError('Github url must include a username and repo')

        client.author = parts[0]
        client.name = parts[1]

    if client.name.endswith('.git'):
        client.name = client.name[:-4]

    if not client.name or not client.author:
        raise ValueError('Error parsing URL. Ensure the URL contains the'
                         'username and repo on Github.')

    client.discovered['author'] = client.author
    client.discovered['name'] = client.name

    try:
        url = settings.GITHUB_URL + '/repos/{}/{}'.format(
            client.author,
            client.name,
        )

        response = session.request(
            'get',
            url,
            timeout=settings.API_TIMEOUT,
        )
    except requests.Timeout:
        raise ClientTimeoutError('Timeout while reading from '
                                 'Github\'s repo API')

    if response.status_code != 200:
        raise ClientError('Server error {0}'.format(response.status_code))

    repo = json.loads(response.content)
    client.discovered['url'] = repo['homepage']
    client.discovered['description'] = repo['description']


class CachedClient(SourceClient):

    def __init__(self, url, cached):
        super(CachedClient, self).__init__(url)

        self.files = cached.get('files', [])
        self.discovered = cached.get('discovered', {})

    def fetch(self):
        pass

    def cache(self):
        pass
