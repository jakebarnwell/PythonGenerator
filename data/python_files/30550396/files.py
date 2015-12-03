import gzip
import atexit
import shutil
from tempfile import NamedTemporaryFile, mkdtemp
import datetime
from itertools import izip_longest, islice, product, izip, ifilter, imap
import os

from collections2.bigchain import retaining_bigchain
from core.raiseable import Base
from core.itertools2 import iterobj, slicepoints


def stripped_lines(input_file):
    if isinstance(input_file, basestring):
        fileobj = open(input_file)
    else:
        fileobj = input_file

    return imap(lambda x: x.rstrip(), fileobj)


def cut_file(input_file, num_files):
    lines = list(iter(input_file))

    s = slicepoints(len(lines), num_files)
    prev = None
    i = 0
    for i in s:
        if prev is not None:
            yield lines[prev:i]
        prev = i
    yield lines[i:]


def split(input_file, num_files, prefix):
    from string import ascii_letters
    for item in izip(cut_file(input_file, num_files),
            product(ascii_letters[:26], ascii_letters[:26])):
        FileWriter(prefix + ''.join(item[1])).write(''.join(item[0]))


def mkdirs(path):
    """ Make directories along path.  Each intermediate component, if it does
    not exist, is created. """

    if isinstance(path, Directory):
        path = unicode(path.path())
    elif isinstance(path, Path):
        path = unicode(path)

    if path.startswith('/'):
        cur = Path('/')
    else:
        cur = Path('.')

    for item in Path(path):
        cur += item
        if cur.exists():
            if not os.path.isdir(cur._url):
                raise IOError('%s is not a dir' % cur)
        else:
            os.mkdir(cur._url)


def verify_exists(f):
    def inner(*args):
        if not args[0].exists():
            raise OSError('File %s does not exist' % args[0])
        return f(*args)
    return inner


class closing_iterobj(iterobj):
    def next(self):
        try:
            return super(closing_iterobj, self).next()
        except StopIteration:
            self._itr.close()
            raise StopIteration()


class stripped_iterobj(closing_iterobj):
    def next(self):
        return super(closing_iterobj, self).next().rstrip()


class PathObject(Base):
    """ Base object of all things which have a path."""

    def __init__(self, path):
        super(PathObject, self).__init__()

        if isinstance(path, basestring):
            path = Path(path)
        else:
            if not isinstance(path, Path):
                raise TypeError('path needs to be basestring or Path object'
                              + ' (got %s)' % type(path))

        self._path = path

    def path(self):
        return self._path

    def name(self):
        return unicode(self.path())

    def __cmp__(self, other):
        return cmp(self.path(), other.path())


class FileObject(PathObject):
    """ Base class for File/Directory.

    Should not be used directly. """

    def __init__(self, path, codec=None, locked=False):
        super(FileObject, self).__init__(path)
        self._codec = codec
        self._locked = locked

    def is_directory(self):
        return isinstance(self, Directory)

    def __getitem__(self, index):
        return iter(self).__getitem__(index)

    def remove(self):
        raise NotImplementedError()
#
#    def url(self):
#        """ Gets the url for this file. """
#        return self.path().url()

    def set_locked(self, locked):
        """ Sets file to be locked. """
        self._locked = locked

    def is_locked(self):
        """ Returns if file is locked. """
        return self._locked

    def set_codec(self, codec):
        """ Sets the codec to be used when reading the file. """
        self._codec = codec

    def __cmp__(self, other):
        return cmp(self.path(), other.path())

    @verify_exists
    def move(self, directory):
        return self.rename(unicode(directory / self.path().basename()))

    @verify_exists
    def rename(self, other_name):
        """ Rename file. """
        os.rename(unicode(self.path()), other_name)
        return self.__class__(other_name)

    @verify_exists
    def size(self):
        """ Get file size. """
        return os.path.getsize(unicode(self.path()))

    def exists(self, ignore_links=False):
        """ Tells if this file exists or not. """
        if ignore_links:
            return self.path().exists()
        return os.path.lexists(unicode(self.path()))

    def remove_if_exists(self):
        """ Remove file if it exists.  Won't fail if file does not exist. """
        if self.exists():
            self.remove()

    @verify_exists
    def atime(self):
        """ Return access time of file. """
        return datetime.datetime.fromtimestamp(os.stat(self.path()._url)[-3])

    @verify_exists
    def mtime(self):
        """ Return modify time of file. """
        return datetime.datetime.fromtimestamp(os.stat(self.path()._url)[-2])

    @verify_exists
    def ctime(self):
        """ Return creation time of file. """
        return datetime.datetime.fromtimestamp(os.stat(self.path()._url)[-1])

    @verify_exists
    def __len__(self):
        """ Return size of url. """
        return os.stat(self.path()._url)[-4]

    def __list__(self):
        return list(iter(self))

    def __iter__(self):
        raise NotImplementedError()

    def soft_link(self, name):
        if isinstance(name, File):
            name = str(name.path())

        os.symlink(str(self.path()), name)


class Path(object):
    """ Encapsulates file path. """
    def __init__(self, url):
        if not isinstance(url, basestring):
            raise TypeError('url must be basestring')
        self._url = os.path.normpath(url)

    @classmethod
    def join(cls, components):
        return cls(os.path.sep.join(components))

    def abs(self):
        return Path(os.path.abspath(self._url))

    def __truediv__(self, other):
        return self.__div__(other)

    def __div__(self, other):
        return self + other

    def exists(self):
        return os.path.exists(self._url)

    def __repr__(self):
        return 'Path(url=%s)' % self._url

    def __unicode__(self):
        if isinstance(self._url, unicode):
            return self._url

        return unicode(self._url, 'utf-8')

    def __str__(self):
        return self._url

    def real(self):
        return os.path.realpath(self._url)

    def __hash__(self, other):
        return hash(str(self))

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __eq__(self, other):
        if not isinstance(other, Path):
            other = Path(other)

        return self.real() == other.real()
        #return os.path.samefile(self.url, other)

    def components(self):
        toks = self._url.split(os.path.sep)
        if self._url[0] == '/':
            toks[0] = '/%s' % toks[0]
        return toks
#
#    def url(self):
#        from web import Url
#        return Url('file://' + self.real())

    def __radd__(self, component):
        if isinstance(component, basestring):
            return Path(component) + self

    def __add__(self, component):
        if isinstance(component, Path):
            component = component._url

        return Path(self._url + os.path.sep + component)

    def __mod__(self, path):
        p = Path('')
        for a, b in izip_longest(self, path, fillvalue=None):
            if a != b:
                p += a

        return p

    def __getitem__(self, index):
        return self.components()[index]

    def without_extention(self):
        return self._name_extension()[0]

    def extension(self):
        return self._name_extension()[1]

    def _name_extension(self):
        b = self.basename()
        if b is not None:
            toks = b.split('.')
            if len(toks) > 1:
                return '.'.join(toks[:-1]), toks[-1]
        return None, None

    def __iter__(self):
        return iter(self.components())

    def leaf(self):
        return self.basename()

    def basename(self):
        c = self.components()
        if c:
            return c[-1]
        return None

    def branch(self):
        return os.path.dirname(str(self))
#        c = self.components()
#        if c:
#            return os.path.sep.join(c[:-1])
#        return None

    def compress(self):
        return os.path.normpath(self._url)

    def add_extension(self, extension):
        return self.__class__(self._url + extension)


class DirectoryIterator(retaining_bigchain):
    NAME = 0
    DATE = 1
    SIZE = 2

    def __init__(self, path):
        super(DirectoryIterator, self).__init__()
        self.path = path
        self.comparator = None
        self._return = None
        self._ignore_dot = False
        self._descending = False
        self.run_yet = False
        self._leaves = False
        self._deep = False

    def _copy(self):
        import copy
        return copy.copy(self)

    def _itr_variant(self, variant, value=True):
        d = self._copy()
        setattr(d, variant, value)
        return d

    def by_date(self):
        return self._itr_variant('comparator', DirectoryIterator.DATE)

    def by_name(self):
        return self._itr_variant('comparator', DirectoryIterator.NAME)

    def by_size(self):
        return self._itr_variant('comparator', DirectoryIterator.SIZE)

    def descending(self):
        return self._itr_variant('_descending')

    def ignore_dot(self):
        return self._itr_variant('_ignore_dot')

    def paths(self):
        return self._itr_variant('_return', Path)

    def files(self):
        return self._itr_variant('_return', File)

    def deep(self):
        return self._itr_variant('_deep')

    def leaves(self):
        return self._itr_variant('_leaves')._itr_variant('_deep')

    def __iter__(self):
        if not self.run_yet:
            self.extend(self._list_names())
            self.run_yet = True

        return super(DirectoryIterator, self).__iter__()

    def _list_names(self):
        try:
            files = (self.path.abs() / path for path in listdir(self.path._url,
                self._deep, self._leaves))

            if self._ignore_dot:
                files = (x for x in files if not x.basename().startswith('.'))

            comparator = None
            if self.comparator is DirectoryIterator.DATE:
                comparator = atime_comparator
            elif self.comparator is DirectoryIterator.SIZE:
                comparator = size_comparator
            elif self.comparator is DirectoryIterator.NAME:
                comparator = cmp

            if comparator:
                if self.comparator in (DirectoryIterator.DATE, DirectoryIterator.SIZE):
                    files = (File(x) for x in files)

                files = sorted(files, comparator, reverse=self._descending)

                if self.comparator in (DirectoryIterator.DATE, DirectoryIterator.SIZE):
                    files = (x.path() for x in files)

            if self._return == File:
                files = (open_path(x) for x in files)
            elif self._return == Path:
                pass
            else:
                files = (unicode(x) for x in files)

            return files
        except OSError:
            return []


class Directory(FileObject):
    """ A directory.

    Encapsulates common directory functions. """

    @staticmethod
    def from_dir(directory, name):
        return Directory(directory.path() + name)

    def __contains__(self, other):
        return unicode(other) in list(self.list_names().deep())
#        return other in list(self.list_names().deep())
#        return Path(other) in self.walk()
#
#    def walk(self):
#        return listdir(self, True)

    def __truediv__(self, other):
        return self.__div__(other)

    def __div__(self, other):
        do_dir = False

        if isinstance(other, FileObject):
            path = unicode(other.path())
            if isinstance(other, Directory):
                do_dir = True
        elif isinstance(other, Path):
            path = unicode(other)
        else:
            path = other

        path = self.path() + path
        if do_dir:
            return Directory(path)
        return open_path(unicode(path))

    def __repr__(self):
        return '%s(path=%s)' % (self.__class__.__name__, self.path())

    def __str__(self):
        return '%s' % self.path()

    def list_names(self):
        return DirectoryIterator(self.path())

    def __iter__(self):
        return iter(self.list_names().files())
#        return imap(open_path, self.list_names())

    @verify_exists
    def size(self):
#        return 0 + sum(x.size() for x in ifilter(lambda x: x.exists(True),
#            self))
        return 0 + sum(x.size() for x in self)

    def create(self):
        # XXX won't work if intermediate dir works
#        mkdirs(self.path()._url)
        os.makedirs(self.path()._url)
        return self

    def create_unless_exists(self):
        if not self.exists():
            self.create()
        return self

    @verify_exists
    def remove(self, recursive=True):
        if recursive:
            for f in list(self):
                f.remove_if_exists()

        os.rmdir(self._path._url)

    def subdirectory(self, name):
        return Directory.from_dir(self, name)

    def open_within(self, filename):
        return open_path_from_dir(self, filename)


class File(FileObject):
    """ A file.

    Encapsulates common file functions. """

    @staticmethod
    def from_dir(directory, name):
        """ Create from directory and name.

        :param directory: directory in which a file by the name exists
        :type directory: Directory
        :param name: name of file
        :type name: str
        """

        return File(directory.path() + name)

    def __str__(self):
        return self.path()._url

    def __repr__(self):
        return '%s(name=%s)' % (self.__class__.__name__, self.path()._url)

    @staticmethod
    def _opener_by_path(path):
        opener = open

        key = path.extension()

        if key:
            key = key.lower()

        if key == 'gz':
            opener = gzip.open
        if key == '7z':
            import plyny.io.p7zip as p7zip
            opener = p7zip.open
        if key == 'bz2':
            import bz2

            class dummy_wrap(bz2.BZ2File):
                def flush(self):
                    pass

            opener = dummy_wrap

        return opener

    def _opener(self):
        opener = self._opener_by_path(self.path())
        if self._codec:
            import codecs
            return lambda x: codecs.getreader(self._codec)(opener(x))

        return opener

    @verify_exists
    def open(self):
        """ Opens this file for reading.  Can handle gz and 7z files; discovers
        by extension.

        :returns: fd of open file.

        """
        return self._opener()(self.path()._url)

    @verify_exists
    def read(self):
        """ Reads file.

        :returns: str of file data
        """

        f = self.open()
        content = f.read()
        f.close()
        return content

    def write(self, data, overwrite=False):
        """ Writes data to file. """

        if self.is_locked():
            raise IOError('locked')

        if not overwrite and self.exists():
            raise ValueError('%s already exists' % self.path()._url)

        o = open(self.path()._url, 'w')
        o.write(data)
        o.close()

    def writer(self, **kwargs):
        """ Opens :class:`FileWriter` for this file.  Useful for multiple write
        requests, `write` opens the file for each write. """

        return FileWriter(self, **kwargs)

    def create(self):
        return self

    @verify_exists
    def __iter__(self):
        return closing_iterobj(self.open())

    @verify_exists
    def remove(self):
        """ Deletes this file. """
        if self.is_link():
            os.unlink(str(self.path()))
        else:
            os.remove(self.path()._url)

    def is_link(self):
        return os.path.islink(str(self.path()))

    def stripped(self):
        return stripped_iterobj(self)


class TemporaryFile(File):
    def __init__(self):
        self.obj = NamedTemporaryFile()
        super(TemporaryFile, self).__init__(self.obj.name)


class TemporaryDirectory(Directory):
    """ Creates a temporary directory.  Directory can be used as normal
    directory but is removed from the filesystem when the object goes out of
    scope. """

    def __init__(self):
        path = mkdtemp()
        super(TemporaryDirectory, self).__init__(path)
        self.close_called = False
        atexit.register(self.close)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if not self.close_called:
            self.close_called = True
            if os.path.exists(str(self._path)):
                shutil.rmtree(str(self._path))

    @verify_exists
    def rename(self, other_name):
        """ Rename file. """
        os.rename(unicode(self.path()), other_name)
        return Directory(other_name)


class stdio(object):
    def __init__(self, stdout=None):
        if stdout is None:
            import sys
            stdout = sys.stdout

        self.stdout = stdout

    def stripped(self):
        return (x.rstrip() for x in self)

    def set_locked(self, locked):
        """ Sets file to be locked. """
        # XXX here to appease args
        pass

    def __iter__(self):
        try:
            while True:
                yield raw_input()
        except EOFError:
            pass

    def read(self):
        return '\n'.join(iter(self))

    def write(self, data, overwrite=False):
        self.stdout.write(data)


def listdir(path='.', deep=False, leaves_only=False):
    if not isinstance(path, Directory):
        path = Directory(path)

    path = Directory(path.path().abs())
    for x in os.listdir(unicode(path.path().abs())):
        if deep:
            f = path.open_within(x)
            if isinstance(f, Directory):
                prefix = f.path() % path.path()

                for item in listdir(f.path()._url, deep, leaves_only):
                    yield prefix / item
            elif leaves_only:
                yield Path(x)

        if not leaves_only:
            yield Path(x)


class FileWriter(PathObject):
    def __init__(self, fileobj, overwrite=False, append=False):
        if isinstance(fileobj, basestring):
            path = Path(fileobj)
        elif isinstance(fileobj, File):
            path = fileobj.path()

        super(FileWriter, self).__init__(path)

        self.f = None

        if not (overwrite or append) and self.path().exists():
            raise IOError('%s exists and not overwriting' % self.path())

        self._append = append

    def _open(self):
        opener = File._opener_by_path(self.path())
        atexit.register(self.close)

        flag = 'w'
        if self._append:
            flag = 'a'

        return opener(self.path()._url, flag)

    def write(self, data, encoding=None):
        if self.f is None:
            self.f = self._open()

        if encoding is not None:
            data = data.encode(encoding)

        self.f.write(data)
        self.f.flush()

    def writeall(self, itr):
        for value in itr:
            self.write(value)

    def __del__(self):
        self.close()

    def close(self):
        if self.f is not None:
            self.f.flush()
            self.f.close()
            self.f = None


def get_path_from_dir(directory, path):
    return str(directory.path() + path)


def open_path_from_dir(directory, path):
    return open_path(get_path_from_dir(directory, path))


def open_path(path, require_exist=False):
    if isinstance(path, Path):
        path = unicode(path)

    if path == '-':
        return stdio()

    if path.startswith('~'):
        path = os.path.expanduser(path)

    path = os.path.abspath(path)

    if require_exist and not os.path.lexists(path):
        raise ValueError('%s does not exist' % path)
    if not os.path.isdir(path) or os.path.islink(path):
        return File(path)
    if os.path.isdir(path):
        return Directory(path)


def size_comparator(f1, f2):
    return cmp(f1.size(), f2.size())


def atime_comparator(f1, f2):
    return cmp(f1.atime(), f2.atime())


def ctime_comparator(f1, f2):
    return cmp(f1.ctime(), f2.ctime())


def _negate_comparator(c):
    return lambda x, y: c(y, x)


def _list_by_comparator(files, comparator, ascending):
    return sorted(files, comparator, reverse=not ascending)


def list_by_ctime(path, ascending=True):
    return _list_by_comparator(path, ctime_comparator, ascending)


def list_by_size(path, ascending=True):
    return _list_by_comparator(path, size_comparator, ascending)
