import unittest
from nose.tools import eq_ as eq, ok_ as ok, raises, timed
import os, sys
import json

from genetix import Genetix, utils
from genetix.storage import JSONFiles
import genetix.stats

# create with json storage
#g = Genetix(JSONFiles('./json'))

class TestUtils(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def fn(self, *args, **kw):
        ''' dummy function '''
        pass

    def test_isType(self):
        eq(utils.isType('', str), True)
        eq(utils.isType('', int), False)
        eq(utils.isType(u'', unicode), True)
        eq(utils.isType(u'', str), False)
        eq(utils.isType('test', str), True)
        eq(utils.isType('test', int), False)
        eq(utils.isType('1', str), True)
        eq(utils.isType('1', int), False)
        eq(utils.isType('1.1', str), True)
        eq(utils.isType('1.1', int), False)
        eq(utils.isType([], list), True)
        eq(utils.isType([], str), False)
        eq(utils.isType({}, dict), True)
        eq(utils.isType({}, str), False)
        eq(utils.isType(1, int), True)
        eq(utils.isType(1, str), False)
        eq(utils.isType(1.1, float), True)
        eq(utils.isType(1.1, int), False)
        eq(utils.isType(tuple(), tuple), True)
        eq(utils.isType(tuple(), str), False)
        eq(utils.isType(set(), set), True)
        eq(utils.isType(set(), str), False)
        eq(utils.isType('', [ str, int, float ]), True)
        eq(utils.isType('', [ int, float ]), False)
        eq(utils.isType('', (str, int, float)), True)
        eq(utils.isType('', (int, float)), False)

    def test_isString(self):
        eq(utils.isString(''), True)
        eq(utils.isString(u''), True)
        eq(utils.isString('test'), True)
        eq(utils.isString('1'), True)
        eq(utils.isString('1.1'), True)
        eq(utils.isString([]), False)
        eq(utils.isString({}), False)
        eq(utils.isString(1), False)
        eq(utils.isString(1.1), False)
        eq(utils.isString(tuple()), False)
        eq(utils.isString(set()), False)
        eq(utils.isString(lambda x:x), False)
        eq(utils.isString(self.fn), False)

    def test_isSequence(self):
        eq(utils.isSequence(''), True)
        eq(utils.isSequence(u''), True)
        eq(utils.isSequence('test'), True)
        eq(utils.isSequence('1'), True)
        eq(utils.isSequence('1.1'), True)
        eq(utils.isSequence([]), True)
        eq(utils.isSequence({}), False)
        eq(utils.isSequence(1), False)
        eq(utils.isSequence(1.1), False)
        eq(utils.isSequence(tuple()), True)
        eq(utils.isSequence(set()), False)
        eq(utils.isSequence(lambda x:x), False)
        eq(utils.isSequence(self.fn), False)

    def test_isMapping(self):
        eq(utils.isMapping(''), False)
        eq(utils.isMapping(u''), False)
        eq(utils.isMapping('test'), False)
        eq(utils.isMapping('1'), False)
        eq(utils.isMapping('1.1'), False)
        eq(utils.isMapping([]), False)
        eq(utils.isMapping({}), True)
        eq(utils.isMapping(1), False)
        eq(utils.isMapping(1.1), False)
        eq(utils.isMapping(tuple()), False)
        eq(utils.isMapping(set()), False)
        eq(utils.isMapping(lambda x:x), False)
        eq(utils.isMapping(self.fn), False)

    def test_isCallable(self):
        eq(utils.isCallable(''), False)
        eq(utils.isCallable(u''), False)
        eq(utils.isCallable('test'), False)
        eq(utils.isCallable('1'), False)
        eq(utils.isCallable('1.1'), False)
        eq(utils.isCallable([]), False)
        eq(utils.isCallable({}), False)
        eq(utils.isCallable(1), False)
        eq(utils.isCallable(1.1), False)
        eq(utils.isCallable(tuple()), False)
        eq(utils.isCallable(set()), False)
        eq(utils.isCallable(lambda x:x), True)
        eq(utils.isCallable(self.fn), True)

    def test_isNumber(self):
        eq(utils.isNumber(''), False)
        eq(utils.isNumber(u''), False)
        eq(utils.isNumber('test'), False)
        eq(utils.isNumber('1'), False)
        eq(utils.isNumber('1.1'), False)
        eq(utils.isNumber([]), False)
        eq(utils.isNumber({}), False)
        eq(utils.isNumber(1), True)
        eq(utils.isNumber(1.1), True)
        eq(utils.isNumber(tuple()), False)
        eq(utils.isNumber(set()), False)
        eq(utils.isNumber(lambda x:x), False)
        eq(utils.isNumber(self.fn), False)

    def test_isNumeric(self):
        eq(utils.isNumeric(''), False)
        eq(utils.isNumeric(u''), False)
        eq(utils.isNumeric('test'), False)
        eq(utils.isNumeric('1'), True)
        eq(utils.isNumeric('1.1'), True)
        eq(utils.isNumeric([]), False)
        eq(utils.isNumeric({}), False)
        eq(utils.isNumeric(1), True)
        eq(utils.isNumeric(1.1), True)
        eq(utils.isNumeric(tuple()), False)
        eq(utils.isNumeric(set()), False)
        eq(utils.isNumeric(lambda x:x), False)
        eq(utils.isNumeric(self.fn), False)

    def test_toFloat(self):
        eq(utils.toFloat(''), None)
        eq(utils.toFloat(u''), None)
        eq(utils.toFloat('test'), None)
        eq(utils.toFloat('1'), 1.0)
        eq(utils.toFloat('1.1'), 1.1)
        eq(utils.toFloat([]), None)
        eq(utils.toFloat({}), None)
        eq(utils.toFloat(1), 1.0)
        eq(utils.toFloat(1.1), 1.1)
        eq(utils.toFloat(tuple()), None)
        eq(utils.toFloat(set()), None)
        eq(utils.toFloat(lambda x:x), None)
        eq(utils.toFloat(self.fn), None)

    def test_toInt(self):
        eq(utils.toInt(''), None)
        eq(utils.toInt(u''), None)
        eq(utils.toInt('test'), None)
        eq(utils.toInt('1'), 1)
        eq(utils.toInt('1.1'), None)
        eq(utils.toInt([]), None)
        eq(utils.toInt({}), None)
        eq(utils.toInt(1), 1)
        eq(utils.toInt(1.1), 1)
        eq(utils.toInt(tuple()), None)
        eq(utils.toInt(set()), None)
        eq(utils.toInt(lambda x:x), None)
        eq(utils.toInt(self.fn), None)

    def test_isList(self):
        eq(utils.isList(''), False)
        eq(utils.isList(u''), False)
        eq(utils.isList('test'), False)
        eq(utils.isList('1'), False)
        eq(utils.isList('1.1'), False)
        eq(utils.isList([]), True)
        eq(utils.isList({}), False)
        eq(utils.isList(1), False)
        eq(utils.isList(1.1), False)
        eq(utils.isList(tuple()), False)
        eq(utils.isList(set()), False)
        eq(utils.isList(lambda x:x), False)
        eq(utils.isList(self.fn), False)

    def test_isDict(self):
        eq(utils.isDict(''), False)
        eq(utils.isDict(u''), False)
        eq(utils.isDict('test'), False)
        eq(utils.isDict('1'), False)
        eq(utils.isDict('1.1'), False)
        eq(utils.isDict([]), False)
        eq(utils.isDict({}), True)
        eq(utils.isDict(1), False)
        eq(utils.isDict(1.1), False)
        eq(utils.isDict(tuple()), False)
        eq(utils.isDict(set()), False)
        eq(utils.isDict(lambda x:x), False)
        eq(utils.isDict(self.fn), False)

    def test_rm(self):
        path = '/tmp/rm_test_file'
        if not os.path.exists(path):
            # create the file
            open(path, 'a').close()
        eq(utils.rm(path), True)
        eq(os.path.exists(path), False)

    def test_cwd(self):
        pass

    def test_ls(self):
        pass

    def test_download(self):
        pass

    def test_methods(self):
        pass

    def test_html_info(self):
        pass

    def test_timeit(self):
        pass

    def test_sortby(self):
        lst = [ (1, 2, 'def'), (2, -4, 'ghi'), (3, 6, 'abc') ]
        expected = [ (3, 6, 'abc'), ( 1, 2, 'def'), (2, -4, 'ghi') ]
        utils.sortby(lst, 2)
        eq(lst, expected)
