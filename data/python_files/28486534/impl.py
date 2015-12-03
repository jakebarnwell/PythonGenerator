import sys as _sys
import os as _os
import re as _re
import codecs as _codecs

from pyrem_strs._base_origined import *
from pyrem_strs.config import _SLOTS_VALID_IN_UNICODE_DERIVED
import pyrem_strs.utility.rowcol as _ut
from pyrem_strs.utility.unoverwritabledict import UnoverwritableDict

if hasattr((), "to_rowcol"):
    raise ImportError, "module pyrmics assumes that tuple type doesn't have a method to_rowcol"

def named_str(name, value):
    """
    A helper function to generate a NamedStr instance.
    """
    return NamedStr(name, value)

if _sys.platform == 'cli':
    import System.Text.Encoding as _ste
    def _getfilesystemencoding(): return "%d" % _ste.Default.CodePage
else:
    _getfilesystemencoding = _sys.getfilesystemencoding

class NamedStr(unicode):
    """
    class NamedStr is a string with a name.
    A struct whose instance variables are: name and value.
    Immutable, you can't any assign instance variable after initialized.
    """
    
    if _SLOTS_VALID_IN_UNICODE_DERIVED: __slots__ = [ '__value', '__rowIndicesTuple', '__name' ]
    
    def __getvalue(self): return self.__value
    value = property(__getvalue, None, None)
    
    def __get_rowIndicesTuple(self): return self.__rowIndicesTuple
    rowIndicesTuple = property(__get_rowIndicesTuple, None, None)
    
    def __getname(self): return self.__name
    name = property(__getname, None, None)
    
    def __new__(cls, name, s):
        """
        A Constructor. Generates a NamedStr from name and content (text).
        """
        
        assert isinstance(s, unicode)
        self = unicode.__new__(cls, s)
        self.__name = name
        self.__value = s
        self.__rowIndicesTuple = tuple(_ut.calc_row_index_list(s))
        return self
    
    @staticmethod
    def new_from_file(filePath, mode=None, encoding=None):
        """
        A helper function to generate a NamedStr instance from a file.
        """
        
        if mode is None: mode = 'rb'
        if not encoding: encoding = _getfilesystemencoding()
        f = _codecs.open(filePath, mode, encoding)
        try:
            return NamedStr(filePath, f.read())
        finally: f.close()
    
    def __repr__(self):
        return "NamedStr('%s', *)" % self.__name
    
    def __str__(self):
        return self.__value.__str__()
    
    def __eq__(self, right):
        return isinstance(right, NamedStr) and \
            self.__name == right.name and unicode.__eq__(self, right)
    
    def __ne__(self, right):
        return not (isinstance(right, NamedStr) and \
                    self.__name == right.name and unicode.__eq__(self, right))
    
    def __ge__(self, right):
        assert isinstance(right, NamedStr)
        rn = right.name
        if self.__name > rn:
            return True
        elif self.__name == rn:
            return unicode.__ge__(self, right)
        
    def __gt__(self, right):
        assert isinstance(right, NamedStr)
        rn = right.name
        if self.__name > rn:
            return True
        elif self.__name == rn:
            return unicode.__gt__(self, right)

    def __lt__(self, right):
        assert isinstance(right, NamedStr)
        rn = right.name
        if self.__name < rn:
            return True
        elif self.__name == rn:
            return unicode.__lt__(self, right)

    def __le__(self, right):
        assert isinstance(right, NamedStr)
        rn = right.name
        if self.__name < rn:
            return True
        elif self.__name == rn:
            return unicode.__le__(self, right)
    
    def __hash__(self):
        return self.__name.__hash__() + self.__value.__hash__()
    
    #def __len__(self):
    #    return unicode.__len__(self)
    
    def __getitem__(self, index):
        return NamedStr(self.__name, unicode.__getitem__(self, index))

    def __getslice__(self, beg, end):
        return NamedStr(self.__name, unicode.__getslice__(self, beg, end))
    
    def __add__(self, right):
        raise NamedStrAttributeError("__add__ is not supported in NamedStr")
    
    def __mul__(self, right):
        raise NamedStrAttributeError("__mul__ is not supported in NamedStr")
    
    def __rmul__(self, left):
        raise NamedStrAttributeError("__rmul__ is not supported in NamedStr")
    
    def lower(self):
        raise NamedStrAttributeError("lower is not supported in NamedStr")
    
    def upper(self):
        raise NamedStrAttributeError("upper is not supported in NamedStr")
    
    def swapcase(self):
        raise NamedStrAttributeError("swapcase is not supported in NamedStr")
    
    def strip(self):
        raise NamedStrAttributeError("strip is not supported in NamedStr")
    
    def lstrip(self):
        raise NamedStrAttributeError("lstrip is not supported in NamedStr")
    
    def rstrip(self):
        raise NamedStrAttributeError("rstrip is not supported in NamedStr")
    
    def get_rowcols(self):
        """
        Returns an array of Rowcol, which contains row and col info 
        for each character of this string.
        """
        return _ut.row_index_list_to_row_col_table( \
                self.__rowIndicesTuple, self.__value)
    
    def get_rowcol_at(self, index):
        """
        Return a Rowcol instance, which contains row and col of 
        the index'th character of this string.
        """
        return Rowcol(*_ut.get_row_col_at(self.__rowIndicesTuple, index))
    
    def get_row_at(self, index):
        """
        Return a Rowcol instance, which contains row and col of 
        the index'th character of this string.
        """
        return _ut.get_row_at(self.__rowIndicesTuple, index)
    
    def to_origined_str(self):
        return OriginedStr(self)

def origined_str(something):
    """
    A helper function to convert something into an OriginedStr instance.
    An argument "something" should be one of follows: 
    u'', NamedStr, OriginedStr, ReferenceRange, or list of ReferenceRange.
    """
    if something == u"":
        return OriginedStr(u"")
    if isinstance(something, OriginedStr):
        return something
    if isinstance(something, NamedStr):
        return OriginedStr(something)
    if isinstance(something, ReferenceRange):
        return OriginedStr.from_origin([ something ])
    if isinstance(something, ( list, tuple )):
        for item in something:
            assert isinstance(item, ReferenceRange)
        return OriginedStr.from_origin(something)
    raise TypeError, "Can't cast to pyrem_strs.originedunicode.OriginedStr"

_ReferenceRange_optimized = ReferenceRange.optimized

class OriginedStr(unicode): # immutable
    """
    OriginedStr is a string which knows its origin(s).
    A struct who has properties: value, origin0.
    Immutable, you can't assign any instance variable after initialized.
    
    The read-only property "value" contains a value as a string.
    The read-only property "origin0" is the first element of origin data.
    """
    
    if _SLOTS_VALID_IN_UNICODE_DERIVED: __slots__ = [ '__references' ]
    
    def get_origin(self):
        """
        Returns origins, that is, a list of ReferenceRange.
        """
        
        if hasattr(self.__references, "to_rowcol"):
            return ( self.__references, )
        else:
            return self.__references
    
    def origin_iter(self):
        if hasattr(self.__references, "to_rowcol"):
            yield self.__references
        else:
            for r in self.__references:
                yield r
    
    def __getvalue(self): return unicode(self)
    value = property(__getvalue, None, None)
    
    def __getorigin0(self):
        if not self.__references: 
            return None
        elif hasattr(self.__references, "to_rowcol"):
            return self.__references
        else:
            return self.__references[0]
    origin0 = property(__getorigin0, None, None)
    
    def __new__(cls, *args):
        """
        A Constructor. Generates a OriginedStr from a NamedStr, or u'' (empty unicode)
        """
        
        if len(args) == 1:
            s = args[0]
            if not s:
                self = unicode.__new__(cls, u'')
                self.__references = None
            else:
                assert isinstance(s, NamedStr)
                self = unicode.__new__(cls, s.value)
                self.__references = ReferenceRange(s, 0, len(s))
        else:
            # the following code is supposed to be used internally in this class, so not documented in the document string.
            s, refs = args
            assert isinstance(s, unicode)
            self = unicode.__new__(cls, s)
            self.__references = refs
        return self
    
    @staticmethod
    def from_origin(referenceRanges):
        """
        A factory method to generate an OriginedStr instance from a list of ReferenceRange.
        """
        referenceRanges = _ReferenceRange_optimized(referenceRanges)
        if not referenceRanges:
            return OriginedStr(u"")
        elif len(referenceRanges) == 1:
            return OriginedStr(referenceRanges[0].to_string(), referenceRanges[0])
        else:
            return OriginedStr(u"".join(rr.to_string() for rr in referenceRanges), tuple(referenceRanges))
    
    def __repr__(self):
        return "OriginedStr(%s)" % repr(self.get_origin())
    
    #def __str__(self):
    #    return self.__str__()
    
    #def __eq__(self, right):
    #    return unicode.__eq__(self, right)
    
    #def __ne__(self, right):
    #    return unicode.__ne__(self, right)
    
    #def __ge__(self, right):
    #    return unicode.__ge__(self, right)
        
    #def __gt__(self, right):
    #    return unicode.__gt__(self, right)

    #def __lt__(self, right):
    #    return unicode.__lt__(self, right)

    #def __le__(self, right):
    #    return unicode.__le__(self, right)
    
    #def __len__(self):
    #    return unicode.__len__(self)
    
    #def __hash__(self):
    #    return unicode(self).__hash__()
    
    def __getitem__(self, index):
        curLength = len(self)
        if index < 0:
            index = curLength + index
        if not (0 <= index < curLength):
            raise IndexError, "OriginedStr index out of range"
        
        for rr in self.origin_iter():
            index -= len(rr)
            if index < 0:
                relativeIndex = rr.end + index
                ostr = OriginedStr(rr.namedstr[relativeIndex])
                ostr.__references = ReferenceRange(rr.namedstr, relativeIndex, relativeIndex + 1)
                return ostr
        
        assert False

    def __getslice__(self, beg, end):
        curLength = len(self)
        if beg < 0:
            beg = curLength + beg
            if beg < 0: raise IndexError, "OriginedStr index out of range"
        if end < 0:
            end = curLength + end
            if end < 0: raise IndexError, "OriginedStr index out of range"
        if beg > end:
            return OriginedStr(u"")
        
        index = beg; reqlen = end - beg
        
        refiter = self.origin_iter()
        rrs = list()
        
        for rr in refiter:
            index -= len(rr)
            if index < 0:
                f = rr.extracted(index)
                rrs.append(f)
                reqlen -= len(f)
                break # for rr
        
        for rr in refiter:
            if reqlen <= 0: break # for rr
            rrs.append(rr)
            reqlen -= len(rr)
        
        if reqlen < 0:
            rrs.append(rrs.pop().trimed(reqlen))
        
        return OriginedStr.from_origin(rrs)
    
    def __add__(self, right):
        assert isinstance(right, OriginedStr)
        
        if not right: return self
        if not self: return right
        
        return OriginedStr.from_origin(self.get_origin() + right.get_origin())
    
    def to_index_str(self):
        """
        Returns a string which contains the indices of origins of this string.
        """
        return ",".join(rr.to_index_str() for rr in self.origin_iter())
    
    def to_rowcol_str(self):
        """
        Returns a string which contains the row-cols of origins of this string.
        """
        return ",".join(rr.to_rowcol_str() for rr in self.origin_iter())
    
    def to_row_str(self):
        """
        Returns a string which contains the rows of origins of this string.
        """
        return ",".join(rr.to_row_str() for rr in self.origin_iter())
    
    def __mul__(self, right):
        raise OriginedStrAttributeError("__mul__ is not supported in OriginedStr")
    
    def __rmul__(self, left):
        raise OriginedStrAttributeError("__rmul__ is not supported in OriginedStr")
    
    def expandtabs(self):
        raise OriginedStrAttributeError("expandtabs is not supported in OriginedStr")
    
    def lower(self):
        raise OriginedStrAttributeError("lower is not supported in OriginedStr")
    
    def upper(self):
        raise OriginedStrAttributeError("upper is not supported in OriginedStr")
    
    def swapcase(self):
        raise OriginedStrAttributeError("swapcase is not supported in OriginedStr")
    
    def strip(self):
        raise OriginedStrAttributeError("strip is not supported in OriginedStr")
    
    def lstrip(self):
        raise OriginedStrAttributeError("lstrip is not supported in OriginedStr")
    
    def rstrip(self):
        raise OriginedStrAttributeError("rstrip is not supported in OriginedStr")

    def ljust(self):
        raise OriginedStrAttributeError("ljust is not supported in OriginedStr")
    
    def rjust(self):
        raise OriginedStrAttributeError("rjust is not supported in OriginedStr")
    
    def title(self):
        raise OriginedStrAttributeError("title is not supported in OriginedStr")
    
    def translate(self):
        raise OriginedStrAttributeError("translate is not supported in OriginedStr")
    
    def join(self, strs):
        if not strs: return OriginedStr(u"")
        if self:
            self_references = self.get_origin()
            r = list(strs[0].get_origin())
            for right in strs[1:]:
                r.extend(self_references); r.extend(right.get_origin())
        else:
            r = []
            for right in strs: r.extend(right.get_origin())
        return OriginedStr.from_origin(r)
    
    def partition(self, sep):
        i = self.find(sep)
        if i >= 0:
            e = i + len(sep)
            return ( self[:i], self[i:e], self[e:] )
        else:
            return ( self, OriginedStr(u''), OriginedStr(u'') )

    def rpartition(self, sep):
        i = self.rfind(sep)
        if i >= 0:
            e = i + len(sep)
            return ( self[:i], self[i:e], self[e:] )
        else:
            return ( OriginedStr(u''), OriginedStr(u''), self )
    
    if _sys.platform == 'cli':
        def splitlines(self, keepends=False):
            if keepends:
                pat = _re.compile(r"[^\r\n]*(\r\n?|\n)|.+$", _re.DOTALL)
                r = []
                for m in pat.finditer(self):
                    b, e = m.group()
                    r.append(self[b:e])
                return r
            else:
                pat = _re.compile(r"\r\n?|\n")
                r = pat.split(self)
                if r and not r[-1]: del r[-1]
                return r
    else:
        def splitlines(self, keepends=False):
            if keepends:
                pat = _re.compile(r"[^\r\n]*(\r\n?|\n)|.+$", _re.DOTALL)
                return [m.group() for m in pat.finditer(self)]
            else:
                pat = _re.compile(r"\r\n?|\n")
                r = pat.split(self)
                if r and not r[-1]: del r[-1]
                return r

class FileTable(UnoverwritableDict):
    """
    FileTable is a dict which contains NamedStr instances 
    that are generated from files.
    """
    
    def __init__(self, defaultMode=None):
        UnoverwritableDict.__init__(self)
        self.__defaultMode = defaultMode
    
    def __setdefaultmode(self, defaultMode): self.__defaultMode = defaultMode
    def __getdefaultmode(self): return self.__defaultMode
    defaultMode = property(__getdefaultmode, __setdefaultmode, None)
    
    def __setitem__(self, filePath, content):
        if not isinstance(content, NamedStr): raise TypeError
        UnoverwritableDict.__setitem__(self, filePath, content)
        
    def read(self, filePath, mode=None, encoding=None):
        """
        Reads a file and adds it as a new element of this.
        """
        assert filePath
        if mode is None: mode = self.__defaultMode
        if filePath not in self:
            self[filePath] = NamedStr.new_from_file(filePath, mode=mode, encoding=encoding)
        return self[filePath]
    
    def read_from_directory(self, dirPath, filePathPattern, recursive=False, mode=None, encoding=None):
        """
        Reads files from a directory and adds them as new elements of this.
        """
        if mode is None: mode = self.__defaultMode
        for root, dirs, files in _os.walk(dirPath):
            if not recursive:
                dirs[:] = []
            for f in files:
                path = _os.path.join(root, f)
                if filePathPattern.match(path):
                    self.read(path, mode=mode, encoding=encoding)
    
defaultFileTable = FileTable()
