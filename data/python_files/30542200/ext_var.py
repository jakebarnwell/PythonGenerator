import math
from zend import *
import zval_utils
import happy_hash
import happy_operators
from happy_util import zend_write
from objects import zval_ptr, MutableString

def php_array_element_dump(zv, num_args, args, hash_key):
    level = args[0]

    if isinstance(hash_key, happy_hash.HashTableIntKey):
        zend_write(MutableString((level + 1) * ' ' + ('[%d]' % hash_key.intval) + '=>\n'), 0)
    elif isinstance(hash_key, happy_hash.HashTableStringKey):
        zend_write(MutableString((level + 1) * ' ' + ('["%s"]' % hash_key.strval.to_str()) + '=>\n'), 0)
    else:
        assert False
    php_var_dump(zv.deref(), level + 2)
    return 0

def PHP_FUNCTION_var_dump(ht, return_value, return_value_ptr, this_ptr, return_value_used):
    assert isinstance(return_value, zval_ptr)
    import global_state
    EG = global_state.EG

    argc = EG.argument_stack.top_elem().deref().lval
    top_idx = EG.argument_stack.top()
    assert top_idx - 1 - argc >= 0
    stack_base = top_idx - 1 - argc

    for i in range(0, argc):
        php_var_dump(EG.argument_stack.getItem(stack_base + i), 1)

def COMMON(struc):
    return '&' if zval_utils.Z_ISREF_P(struc) else ''

# TODO: remove this when we have the native zend_dtoa
def formatted_as_float(param):
    result = '%f' % param
    off = 0
    for off in range(len(result) - 1, -1, -1):
        if result[off] != '0':
            if result[off] == '.':
                off -= 1
            break
    if off < 0:
        return ''
    return result[:off + 1]

def php_var_dump(struc, level):
    zval_element_dump_func = None

    if level > 1:
        zend_write(MutableString((level - 1) * ' '), 0)

    if zval_utils.Z_TYPE_P(struc) == IS_LONG:
        zend_write(MutableString('%sint(%d)\n' % (COMMON(struc), zval_utils.Z_LVAL_P(struc))), 0)
    elif zval_utils.Z_TYPE_P(struc) == IS_BOOL:
        zend_write(MutableString('%sbool(%s)\n' % (COMMON(struc), 'true' if zval_utils.Z_LVAL_P(struc) else 'false')), 0)
    elif zval_utils.Z_TYPE_P(struc) == IS_DOUBLE:
        zend_write(MutableString('%sfloat(%s)\n' % (COMMON(struc), formatted_as_float(zval_utils.Z_DVAL_P(struc)))), 0)
    elif zval_utils.Z_TYPE_P(struc) == IS_STRING:
        zend_write(MutableString('%sstring(%d) "%s"\n' %
            (COMMON(struc), zval_utils.Z_STRLEN_P(struc), zval_utils.Z_STRVAL_P(struc).to_str())), 0)
    elif zval_utils.Z_TYPE_P(struc) == IS_ARRAY:
        myht = happy_operators.Z_ARRVAL_P(struc)
        # TODO: check nApplyCount
        zend_write(MutableString('%sarray(%d) {\n' %
            (COMMON(struc), happy_hash.zend_hash_num_elements(happy_operators.Z_ARRVAL_P(struc)))), 0)
        php_element_dump_func = php_array_element_dump
        if myht:
            happy_hash.zend_hash_apply_with_arguments(myht, php_element_dump_func, 1, level)
            # TODO: dec nApplyCount
        if level > 1:
            zend_write(MutableString((level - 1) * ' '), 0)
        zend_write(MutableString('}\n'), 0)
    elif zval_utils.Z_TYPE_P(struc) == IS_NULL:
        zend_write(MutableString('NULL\n'), 0)
    else:
        raise Exception('Not implemented yet')
