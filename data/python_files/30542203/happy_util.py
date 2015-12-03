import os

from zend import *
import zval_utils
import read_apc_dump as rad
import happy_hash
import objects


def zend_write(str, str_length):
    assert not str is None
    assert isinstance(str, objects.MutableString)
    str_raw = str.to_str()
    assert not str_raw is None
    os.write(1, str_raw)

def zend_make_printable_zval(expr, expr_copy):
    if zval_utils.Z_TYPE_P(expr) == IS_STRING:
        return False
    if zval_utils.Z_TYPE_P(expr) == IS_NULL:
        zval_utils.Z_SET_STRVAL_P(expr_copy, objects.MutableString(''))
    elif zval_utils.Z_TYPE_P(expr) == IS_BOOL:
        if zval_utils.Z_LVAL_P(expr):
            zval_utils.Z_SET_STRVAL_P(expr_copy, objects.MutableString('1'))
        else:
            zval_utils.Z_SET_STRVAL_P(expr_copy, objects.MutableString(''))
    elif zval_utils.Z_TYPE_P(expr) == IS_RESOURCE:
        raise Exception('Not implemented yet')
    elif zval_utils.Z_TYPE_P(expr) == IS_ARRAY:
        raise Exception('Not implemented yet')
    elif zval_utils.Z_TYPE_P(expr) == IS_OBJECT:
        raise Exception('Not implemented yet')
    elif zval_utils.Z_TYPE_P(expr) == IS_DOUBLE:
        expr_copy.assign(expr.deref())
        from happy_variables import zval_copy_ctor
        from happy_operators import zend_locale_sprintf_double
        zval_copy_ctor(expr_copy)
        zend_locale_sprintf_double(expr_copy)
    else:
        expr_copy.assign(expr.deref())
        from happy_variables import zval_copy_ctor
        zval_copy_ctor(expr_copy)
        from happy_operators import convert_to_string
        convert_to_string(expr_copy)
    zval_utils.Z_SET_TYPE_P(expr_copy, IS_STRING)
    return True

def zend_print_zval_ex(write_func, expr, indent):
    expr_copy = zval_utils.make_empty_zval()
    expr_copy_ptr = zval_utils.zp_stack(expr_copy)

    use_copy = zend_make_printable_zval(expr, expr_copy_ptr)
    if use_copy:
        expr = expr_copy_ptr
    if not zval_utils.Z_STRLEN_P(expr):
        if use_copy:
            zval_utils.zval_dtor(expr)
        return 0
    write_func(zval_utils.Z_STRVAL_P(expr), zval_utils.Z_STRLEN_P(expr))
    if use_copy:
        zval_utils.zval_dtor(expr)
    return zval_utils.Z_STRLEN_P(expr)

def zend_print_zval(expr, indent):
    return zend_print_zval_ex(zend_write, expr, indent)

def array_init(arg):
    zv = zval_utils.make_empty_zval()
    from happy_variables import zval_ptr_dtor
    zv.happy_ht = happy_hash.zend_hash_init(None, 0, None, zval_ptr_dtor, False)
    zval_utils.Z_SET_TYPE(zv, IS_ARRAY)
    arg.assign(zv)
    return 0

def is_null_struct(x):
    return (x is None) or isinstance(x, rad.APCFile.NullStruct)

def ZEND_NORMALIZE_BOOL(n):
    if not n:
        return 0
    return 1 if n > 0 else -1
