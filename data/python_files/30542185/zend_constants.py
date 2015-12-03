import happy_hash
import happy_variables
from objects import ptr, zval_ptr, MutableString
from zend import *
import read_apc_dump as rad
import zval_utils


CONST_CS = 1 << 0
CONST_PERSISTENT = 1 << 1
CONST_CT_SUBST = 1 << 2

PHP_USER_CONSTANT = 2 ** 31 - 1


class zend_constant(rad.APCFile.CStruct):
    def __init__(self, name, value, flags, module_number):
        assert isinstance(value, zval_ptr)
        assert (name is None or isinstance(name, MutableString))
        self.name = name
        self.value = value
        self.flags = flags
        self.module_number = module_number


class zend_constant_ptr(ptr):
    def __init__(self, c, null):
        assert isinstance(c, zend_constant)
        self.c = c
        self.null = null

    def is_null(self):
        return self.null

    def assign(self, c):
        assert isinstance(c, zend_constant)
        if self.null:
            raise Exception('null pointer assignment')

        import zval_utils
        self.c.value = zval_utils.zval_copy(c.value)

    def deref(self):
        if self.null:
            raise Exception('null pointer dereference')
        return self.c

    def __nonzero__(self):
        raise Exception('use is_null() for casting to bool')

    def copy(self):
        return zend_constant_ptr(self.c, self.null)


class zend_constant_ptr_ptr(ptr):
    def __init__(self, cp, null):
        assert isinstance(cp, zend_constant_ptr)
        self.__cp = cp
        self.null = null

    def is_null(self):
        return self.null

    def assign(self, cp):
        assert isinstance(cp, zend_constant_ptr)
        if self.null:
            raise Exception('null pointer assignment')
        self.__cp = cp

    def deref(self):
        if self.null:
            raise Exception('null pointer dereference')
        return self.__cp

    def __nonzero__(self):
        raise Exception('use is_null() for casting to bool')

    def copy(self):
        return zend_constant_ptr_ptr(self.__cp, self.null)


const_null_ptr = zend_constant_ptr(zend_constant(None, zval_ptr(zval_utils.make_empty_zval(), True),
    CONST_CS, PHP_USER_CONSTANT), True)
const_null_ptr_ptr = zend_constant_ptr_ptr(const_null_ptr, True)
const_null_ptr = zend_constant_ptr(zend_constant(None, zval_ptr(zval_utils.make_empty_zval(), True),
    CONST_CS, PHP_USER_CONSTANT), True)
const_null_ptr_ptr = zend_constant_ptr_ptr(const_null_ptr, True)


def zend_get_constant(name, name_len, result):
    # TODO: make it correct
    assert isinstance(name, MutableString)
    assert isinstance(result, zval_ptr)
    import global_state

    c_ptr = zend_constant_ptr_ptr(const_null_ptr, False)
    retval = True

    if happy_hash.zend_hash_find(global_state.EG.zend_constants, name, name_len + 1, c_ptr) == FAILURE:
        retval = False

    if retval:
        result.assign(c_ptr.deref().deref().value.deref())
        happy_variables.zval_copy_ctor(result)
        zval_utils.Z_SET_REFCOUNT_P(result, 1)
        zval_utils.Z_UNSET_ISREF_P(result)

    return retval


def zend_get_constant_ex(name, name_len, result, scope, flags):
    # TODO: make it correct
    return zend_get_constant(name, name_len, result)


def zend_register_constant(c):
    # TODO: make it correct
    name = c.name

    import global_state
    return happy_hash.zend_hash_add(global_state.EG.zend_constants, name, name.length(),
        zend_constant_ptr(c, False), 0, const_null_ptr_ptr)
