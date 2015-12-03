import copy
from zend import *
import read_apc_dump as rad
import objects

def Z_TYPE(zval):
    assert isinstance(zval, rad.APCFile.ZEND_zval)
    return zval.get_type()

def Z_TYPE_P(zval_p):
    assert isinstance(zval_p, objects.zval_ptr)
    return Z_TYPE(zval_p.deref())

def Z_TYPE_PP(zval_pp):
    assert isinstance(zval_pp, objects.zval_ptr_ptr)
    return Z_TYPE(zval_pp.deref().deref())

def zval_isref_p(pz):
    assert isinstance(pz, objects.zval_ptr)
    return pz.deref().is_ref__gc

def Z_ISREF_P(pz):
    assert isinstance(pz, objects.zval_ptr)
    return zval_isref_p(pz)

def Z_ISREF_PP(ppz):
    assert isinstance(ppz, objects.zval_ptr_ptr)
    return zval_isref_p(ppz.deref())

def PZVAL_IS_REF(pz):
    assert isinstance(pz, objects.zval_ptr)
    return Z_ISREF_P(pz)

def zval_delref_p(pz):
    assert isinstance(pz, objects.zval_ptr)
    pz.deref().refcount__gc -= 1
    return pz.deref().refcount__gc

def Z_DELREF_P(pz):
    assert isinstance(pz, objects.zval_ptr)
    return zval_delref_p(pz)

def Z_DELREF_PP(pz):
    assert isinstance(pz, objects.zval_ptr_ptr)
    return zval_delref_p(pz.deref())

def zval_set_isref(z):
    assert isinstance(z, rad.APCFile.ZEND_zval)
    z.is_ref__gc = 1

def Z_SET_ISREF(z):
    assert isinstance(z, rad.APCFile.ZEND_zval)
    zval_set_isref(z)

def Z_SET_ISREF_P(z):
    assert isinstance(z, objects.zval_ptr)
    zval_set_isref(z.deref())

def Z_SET_ISREF_PP(z):
    assert isinstance(z, objects.zval_ptr_ptr)
    zval_set_isref(z.deref().deref())

def zval_unset_isref(z):
    assert isinstance(z, rad.APCFile.ZEND_zval)
    z.is_ref__gc = 0

def Z_UNSET_ISREF_P(pz):
    assert isinstance(pz, objects.zval_ptr)
    zval_unset_isref(pz.deref())

def Z_UNSET_ISREF_PP(ppz):
    assert isinstance(ppz, objects.zval_ptr_ptr)
    Z_UNSET_ISREF_P(ppz.deref())

def zval_set_refcount(z, rc):
    assert isinstance(z, rad.APCFile.ZEND_zval)
    z.refcount__gc = rc

def Z_SET_REFCOUNT(z, rc):
    assert isinstance(z, rad.APCFile.ZEND_zval)
    zval_set_refcount(z, rc)

def zval_set_refcount_p(pz, rc):
    assert isinstance(pz, objects.zval_ptr)
    pz.deref().refcount__gc = rc

def Z_SET_REFCOUNT_P(pz, rc):
    assert isinstance(pz, objects.zval_ptr)
    zval_set_refcount_p(pz, rc)

def Z_SET_REFCOUNT_PP(pz, rc):
    assert isinstance(pz, objects.zval_ptr_ptr)
    zval_set_refcount_p(pz.deref(), rc)

def zval_refcount_p(pz):
    assert isinstance(pz, objects.zval_ptr)
    return pz.deref().refcount__gc

def Z_REFCOUNT_P(pz):
    assert isinstance(pz, objects.zval_ptr)
    return zval_refcount_p(pz)

def Z_REFCOUNT_PP(ppz):
    assert isinstance(ppz, objects.zval_ptr_ptr)
    return zval_refcount_p(ppz.deref())

def Z_UNSET_ISREF(zval):
    assert isinstance(zval, rad.APCFile.ZEND_zval)
    zval.is_ref__gc = 0

def Z_SET_REFCOUNT(zval, rc):
    assert isinstance(zval, rad.APCFile.ZEND_zval)
    zval.refcount__gc = rc

def Z_SET_TYPE(zval, zval_type):
    assert isinstance(zval, rad.APCFile.ZEND_zval)
    zval.type = zval_type

def Z_SET_TYPE_P(zval, zval_type):
    assert isinstance(zval, objects.zval_ptr)
    zval.deref().type = zval_type

def Z_ADDREF_P(zval):
    assert isinstance(zval, objects.zval_ptr)
    zval.deref().refcount__gc += 1

def Z_ADDREF_PP(zval):
    assert isinstance(zval, objects.zval_ptr_ptr)
    zval.deref().deref().refcount__gc += 1

def Z_ADDREF(zval):
    assert isinstance(zval, rad.APCFile.ZEND_zval)
    zval.refcount__gc += 1

def SEPARATE_ZVAL(ppzv):
    assert isinstance(ppzv, objects.zval_ptr_ptr)
    orig_ptr = ppzv.deref()
    if Z_REFCOUNT_P(orig_ptr) > 1:
        Z_DELREF_P(orig_ptr)
        ppzv.assign(zp_stack(zval_copy(orig_ptr.deref())))
        from happy_variables import zval_copy_ctor
        zval_copy_ctor(ppzv.deref())
        Z_SET_REFCOUNT_PP(ppzv, 1)
        Z_UNSET_ISREF_PP(ppzv)

def SEPARATE_ZVAL_TO_MAKE_IS_REF(ppzv):
    assert isinstance(ppzv, objects.zval_ptr_ptr)
    if not PZVAL_IS_REF(ppzv.deref()):
        SEPARATE_ZVAL(ppzv)
        Z_SET_ISREF_PP(ppzv)

def SEPARATE_ZVAL_IF_NOT_REF(ppzv):
    assert isinstance(ppzv, objects.zval_ptr_ptr)
    if not PZVAL_IS_REF(ppzv.deref()):
        SEPARATE_ZVAL(ppzv)

def Z_STRLEN(zval):
    assert isinstance(zval, rad.APCFile.ZEND_zval)
    return zval.str.length()

def Z_STRLEN_P(zval_p):
    assert isinstance(zval_p, objects.zval_ptr)
    return zval_p.deref().str.length()

def Z_STRLEN_PP(zval_pp):
    assert isinstance(zval_pp, objects.zval_ptr_ptr)
    return zval_pp.deref().deref().str.length()

def Z_STRVAL(zval):
    assert isinstance(zval, rad.APCFile.ZEND_zval)
    return zval.str

def Z_SET_STRVAL_P(zp, str):
    assert isinstance(zp, objects.zval_ptr)
    zp.deref().str = str

def Z_SET_OBJVAL_P(zp, obj):
    assert isinstance(zp, objects.zval_ptr)
    zp.deref().obj = obj

def Z_LVAL(zval):
    assert isinstance(zval, rad.APCFile.ZEND_zval)
    return zval.lval

def Z_LVAL_P(zval):
    assert isinstance(zval, objects.zval_ptr)
    return zval.deref().lval

def Z_LVAL_PP(zval):
    assert isinstance(zval, objects.zval_ptr_ptr)
    return zval.deref().deref().lval

def Z_ZVAL(zval):
    assert isinstance(zval, rad.APCFile.ZEND_zval)
    if Z_TYPE(zval) == IS_HPHP_REF:
        return zval.zval
    return zval

def Z_SET_LVAL(z, lval):
    assert isinstance(z, rad.APCFile.ZEND_zval)
    z.lval = lval

def Z_SET_LVAL_P(zp, lval):
    assert isinstance(zp, objects.zval_ptr)
    zp.deref().lval = lval

def Z_DVAL(zval):
    assert isinstance(zval, rad.APCFile.ZEND_zval)
    return zval.dval

def Z_DVAL_P(zval):
    assert isinstance(zval, objects.zval_ptr)
    return zval.deref().dval

def Z_DVAL_PP(zpp):
    assert isinstance(zpp, objects.zval_ptr_ptr)
    return zpp.deref().deref().dval

def Z_SET_DVAL(z, dval):
    assert isinstance(z, rad.APCFile.ZEND_zval)
    z.dval = dval

def Z_SET_DVAL_P(zp, dval):
    assert isinstance(zp, objects.zval_ptr)
    zp.deref().dval = dval

def Z_OBJVAL(zval):
    assert isinstance(zval, rad.APCFile.ZEND_zval)
    return zval.obj

def Z_OBJ_HT_P(zval_p):
    assert isinstance(zval_p, objects.zval_ptr)
    return Z_OBJVAL(zval_p.deref()).handlers

def Z_SET_OBJ_HT_P(zval_p, handlers):
    assert isinstance(zval_p, objects.zval_ptr)
    Z_OBJVAL(zval_p.deref()).handlers = handlers

def Z_OBJCE_P(zval_p):
    assert isinstance(zval_p, objects.zval_ptr)
    from zend_API import zend_get_class_entry
    return zend_get_class_entry(zval_p)

def Z_OBJCE_PP(zval_pp):
    assert isinstance(zval_pp, objects.zval_ptr_ptr)
    from zend_API import zend_get_class_entry
    return zend_get_class_entry(zval_pp.deref())

def Z_OBJ_HANDLE_P(zval_p):
    assert isinstance(zval_p, objects.zval_ptr)
    return Z_OBJVAL(zval_p.deref()).handle

def Z_SET_OBJ_HANDLE_P(zval_p, handle):
    assert isinstance(zval_p, objects.zval_ptr)
    Z_OBJVAL(zval_p.deref()).handle = handle

def ZVAL_BOOL(z, b):
    assert isinstance(z, objects.zval_ptr)
    Z_SET_TYPE_P(z, IS_BOOL)
    z.deref().lval = 1 if b else 0

def ZVAL_DOUBLE(z, d):
    assert isinstance(z, objects.zval_ptr)
    Z_SET_TYPE_P(z, IS_DOUBLE)
    z.deref().dval = d

def ZVAL_LONG(z, l):
    assert isinstance(z, objects.zval_ptr)
    Z_SET_TYPE_P(z, IS_LONG)
    z.deref().lval = l

def ZVAL_STRING(z, str):
    assert isinstance(z, objects.zval_ptr)
    assert isinstance(str, objects.MutableString)
    Z_SET_TYPE_P(z, IS_STRING)
    z.deref().str = str

def ZVAL_DOUBLE(z, d):
    assert isinstance(z, objects.zval_ptr)
    Z_SET_TYPE_P(z, IS_DOUBLE)
    z.deref().dval = d

def Z_STRVAL_P(zval_p):
    assert isinstance(zval_p, objects.zval_ptr)
    return zval_p.deref().str

def Z_STRVAL_PP(zval_pp):
    assert isinstance(zval_pp, objects.zval_ptr_ptr)
    return zval_pp.deref().deref().str

def AI_SET_PTR(ai, val):
    assert isinstance(val, objects.zval_ptr)
    ai.set_ptr(val)
    ai.set_ptr_ptr(ai.address_of_ptr())

def PZVAL_LOCK(z):
    assert isinstance(z, objects.zval_ptr)
    Z_ADDREF_P(z)

def INIT_PZVAL(zp):
    assert isinstance(zp, objects.zval_ptr)
    zp.deref().refcount__gc = 1
    zp.deref().is_ref__gc = 0

def i_zval_copy_ctor(zvalue):
    assert isinstance(zvalue, objects.zval_ptr)
    from happy_variables import zval_copy_ctor
    zval_copy_ctor(zvalue)

def zval_dtor(zvalue):
    assert isinstance(zvalue, objects.zval_ptr)
    if zvalue.deref().type <= IS_BOOL:
        return
        # TODO
    import happy_variables
    happy_variables._zval_dtor_func(zvalue)

def i_zval_dtor(p):
    assert isinstance(p, rad.APCFile.ZEND_zval)
    zval_dtor(zp_stack(p))

def make_empty_zval():
    zv = rad.APCFile.ZEND_zval('')
    Z_SET_REFCOUNT(zv, 1)
    Z_UNSET_ISREF(zv)
    Z_SET_TYPE(zv, IS_NULL)
    zv.is_null = True
    return zv

def zval_copy(zv, zv_into=None):
    assert isinstance(zv, rad.APCFile.ZEND_zval)
    if zv_into is None:
      zv_copy = rad.APCFile.ZEND_zval('')
    else:
      zv_copy = zv_into
    zv_copy.refcount__gc = zv.refcount__gc
    zv_copy.is_ref__gc = zv.is_ref__gc
    zv_copy.type = zv.type
    zv_copy.is_null = zv.is_null
    masked_type = zv.type & ~IS_CONSTANT_INDEX
    if masked_type == IS_NULL:
        return zv_copy
    if masked_type == IS_LONG or masked_type == IS_BOOL:
        zv_copy.lval = zv.lval
    elif masked_type == IS_DOUBLE:
        zv_copy.dval = zv.dval
    elif masked_type == IS_STRING or masked_type == IS_CONSTANT:
        zv_copy.str = zv.str
    elif masked_type == IS_ARRAY or masked_type == IS_CONSTANT_ARRAY:
        # TODO: fix for constant array
        zv_copy.happy_ht = zv.happy_ht
    elif masked_type == IS_OBJECT:
        zv_copy.obj = zv.obj.get_copy()
    else:
        raise Exception('Not implemented yet')
    return zv_copy

# Helpers to take addresses from stack such that zval_ptr_* calls are easy to grep and reason about
def zp_stack(zv):
    assert isinstance(zv, rad.APCFile.CStruct)
    return objects.zval_ptr(zv, False)

def zpp_stack(zv):
    assert isinstance(zv, objects.zval_ptr)
    return objects.zval_ptr_ptr(zv, False)

def zppp_stack(zv):
    assert isinstance(zv, objects.zval_ptr_ptr)
    return objects.zval_ptr_ptr_ptr(zv, False)
