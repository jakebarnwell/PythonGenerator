
import math, os, sys, time
from pypy.rlib import jit
from pypy.rlib.objectmodel import specialize
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython import annlowlevel
from pypy.translator.tool.cbuild import ExternalCompilationInfo

from zend import *
import objects
import zval_utils
import global_state
import read_apc_dump
import hphp_kinds
import happy_hash
import happy_util

ZEND_zval = read_apc_dump.APCFile.ZEND_zval

def define_ptr(type_name):
  type = lltype.OpaqueType(type_name)
  ptr = lltype.Ptr(type)
  null = lltype.nullptr(ptr.TO)
  return type, ptr, null

zval_type, zval_ptr, zval_null             = define_ptr('zval')
ht_type, ht_ptr, ht_null                   = define_ptr('HashTable')
hash_pos_type, hash_pos_ptr, hash_pos_null = define_ptr('HashPosition')

_API_FUNCS = []

def _trace_api_func(fn):
    def tracer_fn(*args):
        res = fn(*args)
        print "Fn: %s Args:%s Res:%s" % (fn.func_name, repr(args), repr(res))
        return res
    return tracer_fn

def api_func(res_type, arg_types):
    def decorate(fn):
        fn_name = fn.func_name
        fn_ll_type = lltype.Ptr(lltype.FuncType(arg_types, res_type))
        # Enable for API tracing
        #fn = _trace_api_func(fn)
        _API_FUNCS.append((fn_name, fn, fn_ll_type, res_type, arg_types))
        fn._always_inline_ = True
        return fn

    return decorate

class ExtensionFrame(object):
    def __init__(self):
        self.zvals = []
        self.zval_pos = {}
        self.hts = []
        self.ht_pos = {}
        self.hash_poses = []
        self.hash_pos_pos = {}

# TODO: find a better/more flexible encoding
_FRAME_MASK  = 0xff000000
_FRAME_SHIFT = 24
_LIST_MASK   = 0x00ffffff
_LIST_SHIFT  = 0

def _decode_frame_idx(idx):
    idx -= 1
    return ((idx & _FRAME_MASK) >> _FRAME_SHIFT), ((idx & _LIST_MASK) >> _LIST_SHIFT)

def _encode_frame_idx(frame_idx, list_idx):
    return ((frame_idx << _FRAME_SHIFT) | (list_idx << _LIST_SHIFT)) + 1

def _get_curr_frame():
    frame_idx = len(global_state.EG.ext_frames) - 1
    assert frame_idx >= 0, "No extension frame on stack"
    return frame_idx, global_state.EG.ext_frames[frame_idx]

def _cast_ptr_to_zval(ptr):
    if not ptr:
        return None
    frame_idx, list_idx = _decode_frame_idx(rffi.cast(lltype.Signed, ptr))
    return global_state.EG.ext_frames[frame_idx].zvals[list_idx]

def _cast_ptr_to_ht(ptr):
    if not ptr:
        return None
    frame_idx, list_idx = _decode_frame_idx(rffi.cast(lltype.Signed, ptr))
    return global_state.EG.ext_frames[frame_idx].hts[list_idx]

def _cast_ptr_to_hash_pos(ptr):
    if not ptr:
        return None
    frame_idx, list_idx = _decode_frame_idx(rffi.cast(lltype.Signed, ptr))
    return global_state.EG.ext_frames[frame_idx].hash_poses[list_idx]

def _cast_to_zval_ptr(val):
    if val is None:
        return zval_null

    assert isinstance(val, ZEND_zval)
    frame_idx, frame = _get_curr_frame()
    if val in frame.zval_pos:
        return rffi.cast(zval_ptr, frame.zval_pos[val])

    list_idx = len(frame.zvals)
    zval_idx = _encode_frame_idx(frame_idx, list_idx)
    frame.zvals.append(val)
    frame.zval_pos[val] = zval_idx
    return rffi.cast(zval_ptr, zval_idx)

def _cast_to_ht_ptr(val):
    if val is None:
        return ht_null

    frame_idx, frame = _get_curr_frame()
    if val in frame.ht_pos:
        return rffi.cast(ht_ptr, frame.ht_pos[val])

    list_idx = len(frame.hts)
    ht_idx = _encode_frame_idx(frame_idx, list_idx)
    frame.hts.append(val)
    frame.ht_pos[val] = ht_idx
    return rffi.cast(ht_ptr, ht_idx)

def _cast_to_hash_pos_ptr(val):
    if val is None:
        return hash_pos_null

    frame_idx, frame = _get_curr_frame()
    if val in frame.hash_pos_pos:
        return rffi.cast(hash_pos_ptr, frame.hash_pos_pos[val])

    list_idx = len(frame.hash_poses)
    hash_pos_idx = _encode_frame_idx(frame_idx, list_idx)
    frame.hash_poses.append(val)
    frame.hash_pos_pos[val] = hash_pos_idx
    return rffi.cast(hash_pos_ptr, hash_pos_idx)

_zval_kind_dict = {
    IS_NULL:     hphp_kinds.KindOfNull,
    IS_LONG:     hphp_kinds.KindOfInt64,
    IS_DOUBLE:   hphp_kinds.KindOfDouble,
    IS_BOOL:     hphp_kinds.KindOfBoolean,
    IS_ARRAY:    hphp_kinds.KindOfArray,
    IS_OBJECT:   hphp_kinds.KindOfObject,
    IS_STRING:   hphp_kinds.KindOfString,
    IS_CONSTANT: hphp_kinds.KindOfString, # FIXME: correct?
    IS_CONSTANT_ARRAY: hphp_kinds.KindOfArray,
    IS_HPHP_REF: hphp_kinds.KindOfVariant,
}

@api_func(lltype.Signed, [zval_ptr])
def get_type(ptr):
    zval = _cast_ptr_to_zval(ptr)
    zval_ptr = zval_utils.Z_TYPE(zval)
    assert zval_ptr in _zval_kind_dict, "Unknown zval type: %d" % zval_ptr
    return _zval_kind_dict[zval_ptr]

@api_func(zval_ptr, [zval_ptr])
def deref(ext_obj):
    return ext_obj

@api_func(zval_ptr, [])
def new_zval():
    new_zval = zval_utils.make_empty_zval()
    return _cast_to_zval_ptr(new_zval)

@api_func(zval_ptr, [zval_ptr])
def copy_zval(ptr):
    zval = zval_utils.Z_ZVAL(_cast_ptr_to_zval(ptr))
    new_zval = zval_utils.zval_copy(zval)
    return _cast_to_zval_ptr(new_zval)

@api_func(lltype.Signed, [zval_ptr, lltype.Signed])
def to_int(ptr, base):
    assert base == 10
    zval = zval_utils.Z_ZVAL(_cast_ptr_to_zval(ptr))
    assert zval_utils.Z_TYPE(zval) in [IS_LONG, IS_BOOL]
    return zval_utils.Z_LVAL(zval)

@api_func(lltype.Float, [zval_ptr])
def to_double(ptr):
    zval = zval_utils.Z_ZVAL(_cast_ptr_to_zval(ptr))
    assert zval_utils.Z_TYPE(zval) == IS_DOUBLE
    return zval_utils.Z_DVAL(zval)

@api_func(rffi.VOIDP, [zval_ptr])
def to_string(ptr):
    zval = zval_utils.Z_ZVAL(_cast_ptr_to_zval(ptr))
    assert zval_utils.Z_TYPE(zval) == IS_STRING
    return zval_utils.Z_STRVAL(zval).get_string_data()

@api_func(ht_ptr, [zval_ptr])
def to_hash_table(ptr):
    zval = zval_utils.Z_ZVAL(_cast_ptr_to_zval(ptr))
    assert zval_utils.Z_TYPE(zval) == IS_ARRAY
    return _cast_to_ht_ptr(zval.happy_ht)

@api_func(zval_ptr, [zval_ptr])
def to_zval_ref(ptr):
    zval = _cast_ptr_to_zval(ptr)
    assert zval_utils.Z_TYPE(zval) == IS_HPHP_REF
    return _cast_to_zval_ptr(zval.zval) # FIXME: use accessor

@api_func(zval_ptr, [zval_ptr])
def set_null(ptr):
    zval = zval_utils.Z_ZVAL(_cast_ptr_to_zval(ptr))
    zval_utils.Z_SET_TYPE(zval, IS_NULL)
    return ptr

@api_func(zval_ptr, [zval_ptr, lltype.Signed])
def set_int(ptr, lval):
    zval = zval_utils.Z_ZVAL(_cast_ptr_to_zval(ptr))
    zval_utils.Z_SET_TYPE(zval, IS_LONG)
    zval.lval = lval
    return ptr

@api_func(zval_ptr, [zval_ptr, lltype.Float])
def set_double(ptr, dval):
    zval = zval_utils.Z_ZVAL(_cast_ptr_to_zval(ptr))
    zval_utils.Z_SET_TYPE(zval, IS_DOUBLE)
    zval.dval = dval
    return ptr

@api_func(zval_ptr, [zval_ptr, rffi.VOIDP])
def set_string(ptr, sd):
    zval = zval_utils.Z_ZVAL(_cast_ptr_to_zval(ptr))
    zval_utils.Z_SET_TYPE(zval, IS_STRING)
    zval.str = objects.MutableString.from_string_data(sd)
    return ptr

@api_func(zval_ptr, [zval_ptr, ht_ptr])
def set_hash(ptr, ptr2):
    zval = zval_utils.Z_ZVAL(_cast_ptr_to_zval(ptr))
    ht = _cast_ptr_to_ht(ptr2)
    zval_utils.Z_SET_TYPE(zval, IS_ARRAY)
    zval.happy_ht = ht
    return ptr

@api_func(zval_ptr, [zval_ptr, zval_ptr])
def set_zval_ref(ptr, ptr2):
    zval  = _cast_ptr_to_zval(ptr)
    zval2 = _cast_ptr_to_zval(ptr2)
    # FIXME: set refcount???
    zval_utils.Z_SET_TYPE(zval, IS_HPHP_REF)
    zval.zval = zval2
    return ptr

@api_func(lltype.Signed, [zval_ptr])
def get_refcount(ptr):
    zval = zval_utils.Z_ZVAL(_cast_ptr_to_zval(ptr))
    return zval.refcount__gc

@api_func(zval_ptr, [zval_ptr])
def promote_to_ref(ptr):
    zval = _cast_ptr_to_zval(ptr)
    if zval_utils.Z_TYPE(zval) == IS_HPHP_REF:
      return _cast_to_zval_ptr(zval.zval)

    new_zval = zval_utils.zval_copy(zval)
    zval_utils.Z_SET_TYPE(zval, IS_HPHP_REF)
    zval.zval = new_zval
    return _cast_to_zval_ptr(new_zval)

@api_func(zval_ptr, [zval_ptr, zval_ptr])
def assign_zval(ptr, ptr2):
    zval = _cast_ptr_to_zval(ptr)
    zval2 = _cast_ptr_to_zval(ptr2)
    return _cast_to_zval_ptr(zval_utils.zval_copy(zval2, zval))

@api_func(rffi.CCHARP, [lltype.Signed])
def lltype_malloc(size):
    assert size >= 0
    return lltype.malloc(rffi.CCHARP.TO, size, flavor='raw')

@api_func(rffi.VOIDP, [rffi.CCHARP])
def lltype_free(ptr):
    lltype.free(ptr, flavor='raw')
    return lltype.nullptr(rffi.VOIDP.TO)

@api_func(lltype.Bool, [rffi.CCHARP])
def print_cstr(s):
    ss = rffi.charp2str(s)
    os.write(1, ss)
    return True

@api_func(ht_ptr, [])
def hash_new():
    ht = happy_hash.zend_hash_init(None, 0, None, None, False)
    return _cast_to_ht_ptr(ht)

@api_func(lltype.Signed, [ht_ptr])
def hash_get_size(ptr):
    ht = _cast_ptr_to_ht(ptr)
    return ht.size()

@api_func(lltype.Bool, [ht_ptr, lltype.Signed, rffi.VOIDP, lltype.Bool])
def hash_exists(ptr, ikey, skey, key_is_str):
    ht = _cast_ptr_to_ht(ptr)
    if key_is_str:
      ms = objects.MutableString.from_string_data(skey)
      return happy_hash.zend_hash_exists(ht, ms, 1)
    else:
      return happy_hash.zend_hash_index_exists(ht, ikey)

def _return_retval(retval_ptr):
    assert isinstance(retval_ptr, objects.zval_ptr_ptr_ptr)
    return _cast_to_zval_ptr(retval_ptr.deref().deref().deref())

@api_func(zval_ptr, [ht_ptr, lltype.Signed, rffi.VOIDP, lltype.Bool])
def hash_get(ptr, ikey, skey, key_is_str):
    ht = _cast_ptr_to_ht(ptr)
    zval = zval_utils.make_empty_zval()
    retval_ptr = zval_utils.zppp_stack(global_state.null_zval_ptr_ptr)
    if key_is_str:
        ms = objects.MutableString.from_string_data(skey)
        res = happy_hash.zend_hash_find(ht, ms, 1, retval_ptr)
    else:
        res = happy_hash.zend_hash_index_find(ht, ikey, retval_ptr)
    if res == happy_hash.FAILURE:
        return zval_null
    return _return_retval(retval_ptr)

@api_func(lltype.Bool, [ht_ptr, lltype.Signed, rffi.VOIDP, lltype.Bool, zval_ptr])
def hash_update(ptr, ikey, skey, key_is_str, ptr2):
    ht = _cast_ptr_to_ht(ptr)
    zval = _cast_ptr_to_zval(ptr2)
    zval_ptr = zval_utils.zp_stack(zval)
    zval_ptr_ptr = zval_utils.zpp_stack(zval)
    # TODO: ADDREF on zval???
    if key_is_str:
        ms = objects.MutableString.from_string_data(skey)
        res = happy_hash.zend_hash_update(ht, ms, 1, zval_ptr_ptr, 0,
            global_state.null_zval_ptr_ptr_ptr)
    else:
        res = happy_hash.zend_hash_index_update(ht, ikey, zval_ptr_ptr, 0,
            global_state.null_zval_ptr_ptr_ptr)
    return res == happy_hash.SUCCESS

@api_func(zval_ptr, [ht_ptr, lltype.Signed, rffi.VOIDP, lltype.Bool, zval_ptr])
def hash_add(ptr, ikey, skey, key_is_str, ptr2):
    ht = _cast_ptr_to_ht(ptr)
    zval = _cast_ptr_to_zval(ptr2)
    if not zval:
        zval = zval_utils.make_empty_zval()
    zval_ptr = zval_utils.zp_stack(zval)
    zval_ptr_ptr = zval_utils.zpp_stack(zval_ptr)
    retval_ptr = zval_utils.zppp_stack(global_state.null_zval_ptr_ptr)
    # TODO: ADDREF on zval???
    if key_is_str:
        ms = objects.MutableString.from_string_data(skey)
        res = happy_hash.zend_hash_add(ht, ms, 1,
                zval_ptr_ptr, 0, retval_ptr)
    else:
        res = happy_hash.zend_hash_index_update(ht, ikey,
                zval_ptr_ptr, 0, retval_ptr)
    if res == happy_hash.FAILURE:
        return zval_null
    return _return_retval(retval_ptr)

@api_func(lltype.Bool, [ht_ptr, zval_ptr])
def hash_next_insert(ptr, ptr2):
    ht = _cast_ptr_to_ht(ptr)
    zval = _cast_ptr_to_zval(ptr2)
    zval_ptr = zval_utils.zp_stack(zval)
    zval_ptr_ptr = zval_utils.zpp_stack(zval_ptr)
    res = happy_hash.zend_hash_next_index_insert(ht, zval_ptr_ptr, 0,
        global_state.null_zval_ptr_ptr_ptr)
    return res == happy_hash.SUCCESS

@api_func(lltype.Bool, [ht_ptr, lltype.Signed, rffi.VOIDP, lltype.Bool])
def hash_del(ptr, ikey, skey, key_is_str):
    ht = _cast_ptr_to_ht(ptr)
    # TODO: DELREF on zval???
    if key_is_str:
        ms = objects.MutableString.from_string_data(skey)
        res = happy_hash.zend_hash_del(ht, ms, 1)
    else:
        res = happy_hash.zend_hash_index_del(ht, ikey)
    return res == happy_hash.SUCCESS

@api_func(ht_ptr, [ht_ptr])
def hash_copy(ptr):
    ht = _cast_ptr_to_ht(ptr)
    new_ht = happy_hash.zend_hash_init(None, 0, None, None, False)
    # FIXME: use add_ref here?
    from happy_variables import zval_add_ref
    happy_hash.zend_hash_copy(new_ht, ht, zval_add_ref, None, 0)
    return _cast_to_ht_ptr(new_ht)

@api_func(hash_pos_ptr, [ht_ptr, lltype.Signed, rffi.VOIDP, lltype.Bool])
def hash_get_pos(ptr, ikey, skey, key_is_str):
    ht = _cast_ptr_to_ht(ptr)
    if key_is_str:
        ms = objects.MutableString.from_string_data(skey)
        key = happy_hash.HashTableStringKey(ms)
    else:
        key = happy_hash.HashTableIntKey(ikey)
    pkey = ht.get_perm_key(key)
    return _cast_to_hash_pos_ptr(pkey)

@api_func(hash_pos_ptr, [ht_ptr])
def hash_reset(ptr):
    ht = _cast_ptr_to_ht(ptr)
    key = ht.get_perm_key(ht.first_key)
    return _cast_to_hash_pos_ptr(key)

@api_func(hash_pos_ptr, [ht_ptr])
def hash_end(ptr):
    ht = _cast_ptr_to_ht(ptr)
    key = ht.get_perm_key(ht.last_key)
    return _cast_to_hash_pos_ptr(key)

@api_func(hash_pos_ptr, [ht_ptr, hash_pos_ptr])
def hash_move_forward(ptr, ptr2):
    ht = _cast_ptr_to_ht(ptr)
    key = _cast_ptr_to_hash_pos(ptr2)
    assert key in ht.dict
    _, _, _, nkey = ht.dict[key]
    ret_key = ht.get_perm_key(nkey)
    return _cast_to_hash_pos_ptr(ret_key)

@api_func(hash_pos_ptr, [ht_ptr, hash_pos_ptr])
def hash_move_backward(ptr, ptr2):
    ht = _cast_ptr_to_ht(ptr)
    key = _cast_ptr_to_hash_pos(ptr2)
    assert key in ht.dict
    _, pkey, _, _ = ht.dict[key]
    ret_key = ht.get_perm_key(pkey)
    return _cast_to_hash_pos_ptr(ret_key)

@api_func(zval_ptr, [ht_ptr, hash_pos_ptr])
def hash_get_pos_data(ptr, ptr2):
    ht = _cast_ptr_to_ht(ptr)
    key = _cast_ptr_to_hash_pos(ptr2)
    if not key in ht.dict:
      return zval_null
    pData, _, _, _ = ht.dict[key]
    assert isinstance(pData, objects.zval_ptr_ptr)
    return _cast_to_zval_ptr(pData.deref().deref())

@api_func(rffi.VOIDP, [ht_ptr, hash_pos_ptr])
def hash_get_string_key(ptr, ptr2):
    ht = _cast_ptr_to_ht(ptr)
    key = _cast_ptr_to_hash_pos(ptr2)
    if isinstance(key, happy_hash.HashTableStringKey):
      return key.strval.get_string_data()
    return lltype.nullptr(rffi.VOIDP.TO)

@api_func(lltype.Signed, [ht_ptr, hash_pos_ptr])
def hash_get_int_key(ptr, ptr2):
    ht = _cast_ptr_to_ht(ptr)
    key = _cast_ptr_to_hash_pos(ptr2)
    assert isinstance(key, happy_hash.HashTableIntKey)
    return key.intval

@api_func(lltype.Bool, [ht_ptr])
def hash_renumber(ptr):
    ht = _cast_ptr_to_ht(ptr)
    ht.renumber()
    return True

@api_func(lltype.Bool, [ht_ptr])
def hash_is_vector(ptr):
    ht = _cast_ptr_to_ht(ptr)
    return ht.is_vector()

@api_func(lltype.Bool, [ht_ptr, hash_pos_ptr])
def hash_del_pos(ptr, ptr2):
    ht = _cast_ptr_to_ht(ptr)
    key = _cast_ptr_to_hash_pos(ptr2)
    ht.delete(key)
    return True

@api_func(lltype.Bool, [ht_ptr, zval_ptr])
def hash_prepend(ptr, ptr2):
    ht = _cast_ptr_to_ht(ptr)
    zval = _cast_ptr_to_zval(ptr2)
    ht.prepend(zval)
    return True

_api_struct_args = [(fn_name, fn_ll_type) for
        fn_name, _, fn_ll_type, _, _ in _API_FUNCS]
api_type = lltype.Struct('API', *_api_struct_args)
api_ptr_type = lltype.Ptr(api_type)

_API_FUNCS_iterable = unrolling_iterable(_API_FUNCS)
def _get_api_ptr():
    api_ptr = rffi.make(api_type)
    for fn_name, fn, fn_ll_type, _, _ in _API_FUNCS_iterable:
        setattr(api_ptr, fn_name, rffi.llhelper(fn_ll_type, fn))
    return api_ptr

# FIXME: use actual rffi types
_type_dict = {
        lltype.Signed: 'long',
        zval_ptr:      'zval',
        lltype.Float:  'double',
        rffi.VOIDP:    'void*',
        rffi.CCHARP:   'char*',
        ht_ptr:        'HashTable',
        lltype.Bool:   'bool',
        hash_pos_ptr:  'HashPosition',
        }

def get_api_struct():
    struct  = 'struct HappyAPI {\n'
    for fn_name, _, _, res_type, arg_types in _API_FUNCS:
        struct += '    %s (*%s)(%s);\n' % (_type_dict[res_type]
                , fn_name, ', '.join((_type_dict[arg_type] for arg_type in
                    arg_types)))
    struct += '};\n'
    return struct

_EXTENSION_LIBS = ['test1']
_EXTENSIONS_PATH = (os.path.realpath(os.path.dirname(__file__))
                    + '/extensions')
_ECI_LINK_FILES = [("%s/lib%s.so" % (_EXTENSIONS_PATH, lib))
                          for lib in _EXTENSION_LIBS]

_init_eci = ExternalCompilationInfo(
        #link_files = _ECI_LINK_FILES,
        libraries = ['test1', 'boost_system'],
        library_dirs = [_EXTENSIONS_PATH],
        post_include_bits = ['extern void *init_happy_api(void*);'],
        use_cpp_linker = True
        )
_init_ext_api_fn = rffi.llexternal('init_happy_api',
                        [api_ptr_type], rffi.VOIDP,
                        compilation_info=_init_eci, _nowrapper=True)

def init_ext_api():
    _init_ext_api_fn(_get_api_ptr())

extensions = {}

@specialize.arg(0)
def _add_extension(name):
    "NOT_RPYTHON"
    if name in extensions:
        return

    ext_name = 'happy_ext_%s' % name
    arg_array_type = rffi.CArrayPtr(zval_ptr)
    ll_fn = rffi.llexternal(ext_name,
            [zval_ptr, rffi.INT, arg_array_type], rffi.INT,
            compilation_info=_init_eci, _nowrapper=True)

    @jit.dont_look_inside
    def ext_fn(arg_count, return_value,
               return_value_ptr, this_ptr, return_value_used):
        #import global_state
        EG = global_state.EG
        EG.ext_frames.append(ExtensionFrame())
        if arg_count > 0:
            ll_args = lltype.malloc(arg_array_type.TO,
                    arg_count, flavor='raw')

            arg_end = EG.argument_stack.top() - 1
            arg_begin = arg_end - arg_count
            for arg_idx in xrange(arg_begin, arg_end):
                arg = EG.argument_stack.getItem(arg_idx)
                # FIXME: is deref() here correct???
                ll_args[arg_idx - arg_begin] = _cast_to_zval_ptr(arg.deref())
        else:
            ll_args = lltype.nullptr(arg_array_type.TO)

        if return_value_used:
            return_value_ll_ptr = _cast_to_zval_ptr(return_value.deref())
        else:
            return_value_ll_ptr = zval_null
        ll_fn(return_value_ll_ptr, rffi.cast(rffi.INT, arg_count), ll_args)
        if arg_count > 0:
            lltype.free(ll_args, flavor='raw')
        EG.ext_frames.pop()

    extensions[name] = ext_fn

def _add_all_functions(funcs):
  for func in funcs:
    _add_extension(func)

_add_extension('test1_fn1')
_add_extension('test1_fn2')
_add_extension('plus1')

# TODO: templatize this
sys.path.append("extensions/gen")
import math_functions
_add_all_functions(math_functions.functions)
import string_functions
_add_all_functions(string_functions.functions)

