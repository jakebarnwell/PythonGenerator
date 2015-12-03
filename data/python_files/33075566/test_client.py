import unittest
from dulwich.client import HttpGitClient, TCPGitClient
import mercurial
from mock import patch
import os
import requests
from client import SourceClient, _fetch_mercurial, ClientError, _fetch_git,\
    _fetch_github, _fetch_bitbucket
import client
from tests.util import SettingsOverride


def touch_test_files(out_dir, files):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    for name in files:
        new_file = os.path.join(out_dir, name)
        if not os.path.exists(os.path.dirname(new_file)):
            os.makedirs(os.path.dirname(new_file))
        with open(new_file, 'w') as f:
            f.write('')


class FakeRequestsSession(object):
    def __init__(self, content, status_code=200):
        self.args = None
        self.kwargs = None
        self.content = content
        self.status_code = status_code

    def request(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        response = requests.Response()
        response._content = self.content
        response.status_code = self.status_code
        return response


GITHUB_JEP_REPO = '''
{
  "watchers": 3,
  "pushed_at": "2012-03-10T18:53:30Z",
  "homepage": "http://jepp.sourceforge.net/",
  "svn_url": "https://github.com/mrj0/jep",
  "has_downloads": true,
  "updated_at": "2012-03-29T06:04:07Z",
  "mirror_url": null,
  "has_issues": true,
  "url": "https://api.github.com/repos/mrj0/jep",
  "forks": 1,
  "language": "Shell",
  "fork": false,
  "clone_url": "https://github.com/mrj0/jep.git",
  "ssh_url": "git@github.com:mrj0/jep.git",
  "html_url": "https://github.com/mrj0/jep",
  "has_wiki": true,
  "size": 191,
  "private": false,
  "created_at": "2011-02-18T01:30:05Z",
  "git_url": "git://github.com/mrj0/jep.git",
  "owner": {
    "login": "mrj0",
    "avatar_url": "https://secure.gravatar.com/avatar/745aaf5e0f5ae66dec0ebf6b6827b74f?d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-140.png",
    "url": "https://api.github.com/users/mrj0",
    "gravatar_id": "745aaf5e0f5ae66dec0ebf6b6827b74f",
    "id": 469704
  },
  "name": "jep",
  "description": "Embed Python in Java",
  "id": 1380748,
  "open_issues": 0
}
'''

BITBUCKET_SOUTH_REPO = '''
{
    "scm": "hg",
    "has_wiki": false,
    "last_updated": "2012-04-09 00:30:19",
    "created_on": "2009-05-05 11:32:37",
    "owner": "andrewgodwin",
    "logo": null,
    "email_mailinglist": "",
    "is_mq": false,
    "size": 1889004,
    "read_only": false,
    "fork_of": null,
    "mq_of": null,
    "state": "available",
    "utc_created_on": "2009-05-05 09:32:37+00:00",
    "website": "http://south.aeracode.org/",
    "description": "Migrations for Django",
    "has_issues": false,
    "is_fork": false,
    "slug": "south",
    "is_private": false,
    "name": "south",
    "language": "",
    "utc_last_updated": "2012-04-08 22:30:19+00:00",
    "email_writers": true,
    "main_branch": "default",
    "no_public_forks": false,
    "resource_uri": "/api/1.0/repositories/andrewgodwin/south"
}
'''


class TestClient(unittest.TestCase):
    @patch.object(client, 'hg_clone')
    def test_mercurial_fetch(self, mock):
        def make_test_files(*args, **kwargs):
            touch_test_files(kwargs['dest'], ['test_file', '.hg/somefile'])
        mock.side_effect = make_test_files

        client = SourceClient('ssh://hg@bitbucket.org/andrewgodwin/south', 'hg')
        _fetch_mercurial(client)
        self.assertTrue('test_file' in client.files)
        self.assertFalse('.hg/somefile' in client.files)

    @patch.object(HttpGitClient, 'fetch')
    def test_git_fetch(self, mock):
        def make_test_files(path, local):
            touch_test_files(local.path, ['test_file', '.git/somefile'])
        mock.side_effect = make_test_files

        client = SourceClient('https://github.com/mrj0/jep.git', 'git')
        _fetch_git(client)
        self.assertTrue('test_file' in client.files)
        self.assertFalse('.git/somefile' in client.files)

    @patch.object(TCPGitClient, 'fetch')
    def test_git_fetch_tcp(self, mock):
        def make_test_files(path, local):
            touch_test_files(local.path, ['test_file', '.git/somefile'])
        mock.side_effect = make_test_files

        client = SourceClient('git://github.com/mrj0/jep.git', 'git')
        _fetch_git(client)
        self.assertTrue('test_file' in client.files)
        self.assertFalse('.git/somefile' in client.files)

    def test_mercurial_no_local(self):
        with SettingsOverride(DEBUG=False):
            client = SourceClient('/some/local/url', 'hg')
            self.assertRaises(ClientError, _fetch_mercurial, client)

            client = SourceClient('/etc', 'hg')
            self.assertRaises(ClientError, _fetch_mercurial, client)

    def test_bitbucket(self):
        client = SourceClient('ssh://hg@bitbucket.org/andrewgodwin/south', 'hg')
        _fetch_bitbucket(client, session=FakeRequestsSession(BITBUCKET_SOUTH_REPO))
        self.assertEqual('andrewgodwin', client.discovered['author'])
        self.assertEqual(
            'http://south.aeracode.org/',
            client.discovered['url'])
        self.assertEqual(
            'Migrations for Django',
            client.discovered['description']
        )

    def test_git_no_local(self):
        with SettingsOverride(DEBUG=False):
            client = SourceClient('/some/local/url', 'git')
            self.assertRaises(ClientError, _fetch_git, client)

            client = SourceClient('/etc', 'git')
            self.assertRaises(ClientError, _fetch_git, client)

    def test_github_client_git(self):
        client = SourceClient('git@github.com:mrj0/jep.git', 'git')
        _fetch_github(client, session=FakeRequestsSession(GITHUB_JEP_REPO))
        self.assertEqual('mrj0', client.discovered['author'])
        self.assertEqual(
            'http://jepp.sourceforge.net/',
            client.discovered['url'])
        self.assertEqual(
            'Embed Python in Java',
            client.discovered['description']
        )

    def test_github_client_https(self):
        client = SourceClient('https://mrj0@github.com/mrj0/jep.git')
        _fetch_github(client, session=FakeRequestsSession(GITHUB_JEP_REPO))
        self.assertEqual('mrj0', client.discovered['author'])
        self.assertEqual(
            'http://jepp.sourceforge.net/',
            client.discovered['url'])
        self.assertEqual(
            'Embed Python in Java',
            client.discovered['description']
        )


if __name__ == '__main__':
    unittest.main()
