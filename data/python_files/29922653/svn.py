import os
import subprocess
import urlparse

from optparse import OptionParser
from xml.etree import ElementTree
from StringIO import StringIO

from mcommand import Abort
from .util import call_and_capture as _call_and_capture

SVNINFO_URL = 'URL'
SVNINFO_REPO_ROOT = 'Repository Root'
SVNINFO_REVISION = 'Revision'

SVNREL_DIR, SVNREL_REPO_ROOT, SVNREL_SCHEME, SVNREL_SERVER_ROOT = SVNREL_URLS_STARTS = ('../', '^/', '//', '/')
     
class SvnExternal(object):
    def __init__(self, target, source, source_rev=None, parent=''):
        self.parent = parent
        self.target = target
        self.source = source
        self.source_rev = source_rev

    def __str__(self):
        s = '{0} --> {1}'.format(os.path.join(self.parent, self.target), self.source)
        if self.source_rev:
            s += '@{0}'.format(self.source_rev)
        return s
        
    @property
    def full_target(self):
        t = self.parent + '/' + self.target if self.parent else self.target
        t = os.path.normpath(t).replace('\\', '/')
        return t
    
    def contains_revision(self):
        '''Checks whether external contains a revision definition
        (be it separate revision or peg revision as part of url)
        '''
        return self.source_rev or '@' in self.source

def is_svn_relative(s):
    return s.startswith(SVNREL_URLS_STARTS)
        
def is_svn_absolute(s):
    return '://' in s
       
def parse_external(ext):
    '''parses externals definition. Returns SvnExternal object
    '''
    def is_source_url(s):
        return is_svn_absolute(s) or is_svn_relative(s)
        
    parser = OptionParser(add_help_option=False)
    parser.add_option('-r', dest='rev', default=None)
    
    parts = [s.strip() for s in ext.split()] # TODO support quoatations
    
    opts, args = parser.parse_args(parts)
    assert len(args) == 2
    
    if is_source_url(args[1]):
        #old format
        target = args[0]
        source = args[1]
    else:
        # new format
        target = args[1]
        source = args[0]
        
    return SvnExternal(target=target, source=source, source_rev=opts.rev)
    
def resolve_external(ext, svninfo):
    if not is_svn_absolute(ext.source):
        schema, host, root_path, _, _ = urlparse.urlsplit(svninfo[SVNINFO_REPO_ROOT])
        
        if ext.source.startswith(SVNREL_REPO_ROOT): 
            path = '/'.join((root_path, ext.source[2:]))
        elif ext.source.startswith(SVNREL_SCHEME):
            host, path = ext.source[2:].split('/', 1)
        elif ext.source.startswith(SVNREL_SERVER_ROOT):
            path = ext.source
        else: # treat all the other schemes as dir realative urls
            repo_path = urlparse.urlsplit(svninfo[SVNINFO_URL]).path
            path = '/'.join((repo_path, ext.parent, ext.source))
            
        path = os.path.normpath(path).replace('\\', '/')
        ext.source = urlparse.urlunparse((schema, host, path, None, None, None))
        
    return ext
    
class SvnClient(object):
    def __init__(self, repo):
        self._svnexe = repo.get_config('svnext.svn-exe') or 'svn'

    def call(self, args, cwd=None):
        return self._execute(subprocess.call, args, cwd=cwd)
        
    def call_and_capture(self, args, cwd=None):
        return self._execute(_call_and_capture, args, cwd=cwd)
        
    def _execute(self, fn, svnargs, **kwargs):
        cmd = [self._svnexe] + list(svnargs)
        try:
            return fn(cmd, **kwargs)
        except OSError:
            raise Abort('failed to execute {0}.'.format(cmd[0]))
        except subprocess.CalledProcessError:
            raise Abort('svn command failed.')

    def read_property(self, name, targets, rev=None):
        cmd = ['propget', name, '--xml']
        if rev: cmd += ['-r', rev]
        cmd += targets
        
        out = self.call_and_capture(cmd)
        
        doc = ElementTree.parse(StringIO(out))
        for e in doc.getroot():
            assert len(e) == 1 and e[0].get('name') == name
            yield e.get('path'), e[0].text
        
    def retrieve_externals(self, targets, rev=None):
        for target, value in self.read_property('svn:externals', targets, rev=rev):
            yield target, value.splitlines()
            
    def read_info(self, target):
        cmd = ['info', target]
        out = self.call_and_capture(cmd).strip()
        vals = dict()
        for line in (l.strip() for l in out.split('\n')):
            if not ':' in line: continue
            k, v = line.split(':', 1)
            vals[k.strip()] = v.strip()
        return vals
