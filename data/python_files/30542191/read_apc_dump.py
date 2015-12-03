
import os
import py

from pypy.rlib.rarithmetic import intmask, r_uint, r_longlong,\
     r_ulonglong, longlongmask
from pypy.rlib.rstruct.error import StructError
from pypy.rlib.rstruct.formatiterator import FormatIterator,\
     CalcSizeFormatIterator
from pypy.rlib.objectmodel import specialize

from zend import *

class Wrapper(object):
  pass

class NullWrapper(Wrapper):
  pass

class IntWrapper(Wrapper):
  def __init__(self, value):
    self.int_value = intmask(value)

class UIntWrapper(Wrapper):
  def __init__(self, value):
    self.int_value = intmask(value)

class LongLongWrapper(Wrapper):
  def __init__(self, value):
    self.int_value = value

class ULongLongWrapper(Wrapper):
  def __init__(self, value):
    self.int_value = intmask(value)

class FloatWrapper(Wrapper):
  def __init__(self, value):
    self.float_value = value

@specialize.argtype(0)
def wrap_value(value):
  if isinstance(value, int):
    return IntWrapper(value)
  elif isinstance(value, r_uint):
    return UIntWrapper(value)
  elif isinstance(value, r_longlong):
    return LongLongWrapper(value)
  elif isinstance(value, r_ulonglong):
    return ULongLongWrapper(value)
  elif isinstance(value, float):
    return FloatWrapper(value)
  else:
    # TODO: error
    return Wrapper()

class UnpackFormatIterator(FormatIterator):
    def __init__(self, input):
        self.input = input
        self.inputpos = 0
        self.result = []     # list of wrapped objects

    def operate(self, fmtdesc, repetitions):
        if fmtdesc.needcount:
            fmtdesc.unpack(self, repetitions)
        else:
            for i in range(repetitions):
                fmtdesc.unpack(self)
    operate._annspecialcase_ = 'specialize:arg(1)'
    _operate_is_specialized_ = True

    def align(self, mask):
        self.inputpos = (self.inputpos + mask) & ~mask

    def finished(self):
        if self.inputpos != len(self.input):
            raise StructError('unpack str size too long for format')

    def read(self, count):
        end = self.inputpos + count
        if end > len(self.input):
            raise StructError('unpack str size too short for format')
        s = self.input[self.inputpos : end]
        self.inputpos = end
        return s

    def appendobj(self, value):
        self.result.append(wrap_value(value))
    appendobj._annspecialcase_ = 'specialize:argtype(1)'

def calcsize(fmt):
  fmtiter = CalcSizeFormatIterator()
  fmtiter.interpret(fmt)
  return fmtiter.totalsize

def unpack(fmt, input):
  fmtiter = UnpackFormatIterator(input)
  fmtiter.interpret(fmt)
  return fmtiter.result

class APCFile:
  def __init__(self, name):
    self.os_file = os.open(name, 0666, os.O_RDONLY)
    self.offset_struct_dict = {}
    self.apc_bd = self.read_ptr(0, APCFile.build_APC_bd, read_null = True)
    os.close(self.os_file)
    #self.os_file = None

  def read_struct(self, offset, fmt_str, read_null = False):
    if offset == 0 and not read_null:
      return []
    size = calcsize(fmt_str)
    os.lseek(self.os_file, intmask(offset), os.SEEK_SET)
    struct_bin = os.read(self.os_file, size)
    return unpack(fmt_str, struct_bin)

  @specialize.arg(2, 5)
  def read_ptr(self, offset, builder, padding = '', args = (),
      const_args = (), read_null = False):
    if offset == 0 and not read_null:
      return self.NullStruct()

    obj = builder(self, padding)
    dict_key = offset, obj.get_dict_key()
    if dict_key in self.offset_struct_dict:
      # TODO: use this for all other read_XXX functions
      return self.offset_struct_dict[dict_key]

    os.lseek(self.os_file, intmask(offset), os.SEEK_SET)
    self.offset_struct_dict[dict_key] = obj
    obj.read(self, offset, args, const_args)
    return obj

  @specialize.arg(3)
  def read_count_elements(self, offset, count, builder, padding = '',
      args = ()):
    if offset == 0:
      return []

    tmp_element = builder(self, '')
    element_padding = tmp_element.get_padding_suffix()

    result = []
    for i in range(count):
      # This assumes that the elements in the array are properly aligned
      # and we can just get the next one by using += sizeof(element)
      if i == count - 1:
        element_padding = padding

      element = self.read_ptr(offset, builder, 
          element_padding, args)
      result.append(element)
      offset += element.calc_size()
    return result

  def read_len_string(self, offset, length):
    if offset == 0:
      return ''
    os.lseek(self.os_file, intmask(offset), os.SEEK_SET)
    return os.read(self.os_file, intmask(length))

  def read_asciiz_string(self, offset):
    if offset == 0:
      return ''
    BLOCK_SIZE = 32
    asciiz_str = ''
    os.lseek(self.os_file, intmask(offset), os.SEEK_SET)
    while True:
      buf = os.read(self.os_file, BLOCK_SIZE)
      if len(buf) == 0:
        return asciiz_str

      pos_null = buf.find('\x00')
      if pos_null < 0:
        asciiz_str += buf
        continue
      # Found NULL terminator
      if pos_null > 0:
        asciiz_str += buf[0:pos_null]
      return asciiz_str

  def read_uint(self, offset):
    if offset == 0:
      return NullWrapper() # Has to be an integer in RPython
    fmt_str = '@I'
    size = calcsize(fmt_str)
    os.lseek(self.os_file, intmask(offset), os.SEEK_SET)
    struct_bin = os.read(self.os_file, size)
    return unpack(fmt_str, struct_bin)[0]

  class CStruct(object):
    def calc_size(self):
      fmtiter = CalcSizeFormatIterator()
      fmtiter.interpret(self._fmt_str)
      return fmtiter.totalsize
      
    def get_padding_suffix(self):
      best = (1, 'c')
      for field in self._fmt_str[1:]:
        if field == '0':
          break
        size = calcsize('@' + field)
        if size > best[0]:
          best = (size, field)
      return '0' + best[1]

    def get_dict_key(self):
      return 'CStruct'

    def __nonzero__(self):
      raise Exception('use happy_util.is_null_struct() for casting to bool')

  class NullStruct(CStruct):
    def read(self):
      pass

    def get_padding_suffix(self):
      return '0c'

    def calc_size(self):
      return 0

    def get_dict_key(self):
      return 'NullStruct'

#    def __str__(self):
#      public_dict = [(k, v) for k, v in self.__dict__.items() if k[0] != '_'
#          and k != 'scope']
#      return str(self.__dict__)

#    def __repr__(self):
#      public_dict = [(k, v) for k, v in self.__dict__.items() if k[0] != '_']
#      return repr(public_dict)

# ===== APC_bd =====
  class APC_bd(CStruct):
    def __init__(self, padding):
      self._fmt_str = '@IiccccccccccccccccccccIPiP' + padding

    def read(self, apc_file, offset, args, const_args):
      bd_struct = apc_file.read_struct(offset, self._fmt_str, read_null = True)
      self.entries = apc_file.read_count_elements(bd_struct[23].int_value,
          bd_struct[22].int_value, APCFile.build_APC_bd_entry)

    def get_dict_key(self):
      return 'APC_bd'

  def build_APC_bd(self, padding):
    return self.APC_bd(padding)

# ===== APC_bd_entry =====
  class APC_bd_entry(CStruct):
    APC_CACHE_ENTRY_FILE = 1
    APC_CACHE_ENTRY_USER = 2
    APC_CACHE_ENTRY_FPFILE = 3

    def __init__(self, padding):
      self._fmt_str = '@BII' + padding

    def read(self, apc_file, offset, args, const_args):
      entry_struct = apc_file.read_struct(offset, self._fmt_str)
      self.type = entry_struct[0].int_value
      self.num_func = entry_struct[1].int_value
      self.num_classes = entry_struct[2].int_value
      if self.type == self.APC_CACHE_ENTRY_FPFILE:
        builder = APCFile.build_APC_cache_fpfile_entry_value
        self.value = apc_file.read_ptr(offset, builder,
            args = (IntWrapper(self.num_func), IntWrapper(self.num_classes)))
      elif self.type == self.APC_CACHE_ENTRY_USER:
        builder = APCFile.build_APC_cache_user_entry_value
        self.value = apc_file.read_ptr(offset, builder,
            args = (IntWrapper(self.num_func), IntWrapper(self.num_classes)))
      else:
        # TODO: throw exception
        print 'Got invalid type: ' + str(self.type)
        class_name = 'ERROR'

    def get_dict_key(self):
      return 'APC_bd_entry'

  def build_APC_bd_entry(self, padding):
    return self.APC_bd_entry(padding)

# ===== APC_cache_fpfile_entry_value =====
  class APC_cache_fpfile_entry_value(CStruct):
    def __init__(self, padding):
      self._fmt_str = '@BIIPPPPl' + padding

    def read(self, apc_file, offset, args, const_args):
      num_func = args[0].int_value
      num_classes = args[1].int_value
      entry_struct = apc_file.read_struct(offset, self._fmt_str)
      self.filename = apc_file.read_asciiz_string(entry_struct[3].int_value)
      self.op_array = apc_file.read_ptr(entry_struct[4].int_value,
          APCFile.build_ZEND_op_array)
      self.functions = apc_file.read_count_elements(entry_struct[5].int_value,
          num_func, APCFile.build_APC_function)
      self.classes = apc_file.read_count_elements(entry_struct[6].int_value,
          num_classes, APCFile.build_APC_class)
      self.halt_offset = entry_struct[7].int_value

    def get_dict_key(self):
      return 'APC_bd_cache_fpfile_entry_value'

  def build_APC_cache_fpfile_entry_value(self, padding):
    return self.APC_cache_fpfile_entry_value(padding)

# ===== APC_cache_user_entry_value =====
  class APC_cache_user_entry_value(CStruct):
    _fmt_str = '@'
    def __init__(self, padding):
      # We don't care about these
      pass

    def read(self, apc_file, offset, args, const_args):
      pass

    def get_dict_key(self):
      return 'APC_bd_cache_user_entry_value'

  def build_APC_cache_user_entry_value(self, padding):
    return self.APC_cache_user_entry_value(padding)

# ===== ZEND_op_array =====
  class ZEND_op_array(CStruct):
    def __init__(self, padding):
      self._fmt_str = '@BPPIPIIPBBBPPIIPiiIPiiPiPPiIPIIPIIPPPP' + padding

    def read(self, apc_file, offset, args, const_args):
      op_array_struct = apc_file.read_struct(offset, self._fmt_str)
      self.type = op_array_struct[0].int_value
      self.function_name = apc_file.read_asciiz_string(
          op_array_struct[1].int_value)
      self.scope = apc_file.read_ptr(
          op_array_struct[2].int_value,
          APCFile.build_ZEND_class_entry)
      self.fn_flags = op_array_struct[3].int_value
      self.prototype = apc_file.read_ptr(
          op_array_struct[4].int_value,
          APCFile.build_ZEND_function)
      self.num_args = op_array_struct[5].int_value
      self.required_num_args = op_array_struct[6].int_value
      self.arg_info = apc_file.read_ptr(
          op_array_struct[7].int_value,
          APCFile.build_ZEND_arg_info)
      self.pass_rest_by_reference = op_array_struct[8].int_value
      self.return_reference = op_array_struct[9].int_value
      self.done_pass_two = op_array_struct[10].int_value
      self.refcount = apc_file.read_uint(op_array_struct[11].int_value)
      self.opcodes = apc_file.read_count_elements(
          op_array_struct[12].int_value,
          op_array_struct[13].int_value,
          APCFile.build_ZEND_op)
      self.last = op_array_struct[13].int_value
      self.size = op_array_struct[14].int_value
      self.vars = apc_file.read_count_elements(
          op_array_struct[15].int_value,
          op_array_struct[16].int_value,
          APCFile.build_ZEND_compiled_variable)
      self.last_var = op_array_struct[16].int_value
      self.size_var = op_array_struct[17].int_value
      self.T = op_array_struct[18].int_value
      self.brk_cont_array = apc_file.read_count_elements(
          op_array_struct[19].int_value,
          op_array_struct[20].int_value,
          APCFile.build_ZEND_brk_cont_element)
      self.last_brk_cont = op_array_struct[20].int_value
      self.current_brk_cont = op_array_struct[21].int_value
      self.try_catch_array = apc_file.read_count_elements(
          op_array_struct[22].int_value, 
          op_array_struct[23].int_value,
          APCFile.build_ZEND_try_catch_element)
      self.last_try_catch = op_array_struct[23].int_value

      import happy_hash
      import global_state
      import zval_utils
      from objects import MutableString
      static_variables = apc_file.read_ptr(
          op_array_struct[24].int_value,
          APCFile.build_ZEND_HashTable,
          const_args = (APCFile.build_ZEND_zval, True))
      self.static_variables = None
      if not isinstance(static_variables, APCFile.NullStruct):
        self.static_variables = happy_hash.zend_hash_init(None, 0, None, None, False)
        for static_var in static_variables.members():
          varname = static_var.arKey[:-1]
          happy_hash.zend_hash_add(self.static_variables, MutableString(varname), len(varname),
            zval_utils.zpp_stack(zval_utils.zp_stack(static_var.pData)),
            0, global_state.null_zval_ptr_ptr_ptr)

      self.start_op = apc_file.read_ptr(
          op_array_struct[25].int_value,
          APCFile.build_ZEND_op)
      self.backpatch_count = op_array_struct[26].int_value
      self.this_var = op_array_struct[27].int_value
      self.filename = apc_file.read_asciiz_string(op_array_struct[28].int_value)
      self.line_start = op_array_struct[29].int_value
      self.line_end = op_array_struct[30].int_value
      self.doc_comment = apc_file.read_len_string(
          op_array_struct[31].int_value,
          op_array_struct[32].int_value)
      self.doc_comment_len = op_array_struct[32].int_value
      self.early_binding = op_array_struct[33].int_value
      # 4 more reserved fields we don't care about

    def get_dict_key(self):
      return 'ZEND_op_array'

  def build_ZEND_op_array(self, padding):
    return self.ZEND_op_array(padding)

# ===== APC_function =====
  class APC_function(CStruct):
    def __init__(self, padding):
      self._fmt_str = '@PiP' + padding

    def read(self, apc_file, offset, args, const_args):
      function_struct = apc_file.read_struct(offset, self._fmt_str)
      from objects import MutableString
      self.name = MutableString(apc_file.read_len_string(function_struct[0].int_value,
          function_struct[1].int_value))
      self.name_len = function_struct[1].int_value
      self.function = apc_file.read_ptr(function_struct[2].int_value,
          APCFile.build_ZEND_function)

    def get_dict_key(self):
      return 'APC_function'

  def build_APC_function(self, padding):
    return self.APC_function(padding)

# ===== APC_class =====
  class APC_class(CStruct):
    def __init__(self, padding):
      self._fmt_str = '@PiPP' + padding

    def read(self, apc_file, offset, args, const_args):
      class_struct = apc_file.read_struct(offset, self._fmt_str)
      from objects import MutableString
      self.name = MutableString(apc_file.read_len_string(class_struct[0].int_value,
          class_struct[1].int_value))
      self.name_len = class_struct[1].int_value
      self.parent_name = MutableString(apc_file.read_asciiz_string(class_struct[2].int_value))
      self.class_entry = apc_file.read_ptr(class_struct[3].int_value,
          APCFile.build_ZEND_class_entry)

    def get_dict_key(self):
      return 'APC_class'

  def build_APC_class(self, padding):
    return self.APC_class(padding)

# ===== ZEND_function =====
  class ZEND_function(CStruct):
    ZEND_INTERNAL_FUNCTION = 1
    ZEND_USER_FUNCTION = 2
    ZEND_OVERLOADED_FUNCTION = 3
    ZEND_EVAL_CODE = 4
    ZEND_OVERLOADED_FUNCTION_TEMPORARY = 5

    def __init__(self, padding):
      self._fmt_str = '@B' + padding

    def read(self, apc_file, offset, args, const_args):
      function_struct = apc_file.read_struct(offset, self._fmt_str)
      self.type = function_struct[0].int_value
      if self.type in [self.ZEND_USER_FUNCTION, self.ZEND_EVAL_CODE]:
        self.op_array = apc_file.read_ptr(offset, APCFile.build_ZEND_op_array)
      else:
        assert False, "bytecode file contains internal function"
        self.op_array = None
      # TODO: add internal_function later

    def get_dict_key(self):
      return 'ZEND_function'

  def build_ZEND_function(self, padding):
    return self.ZEND_function(padding)

# ===== ZEND_op =====
  class ZEND_op(CStruct):
    def __init__(self, padding):
      self._header_str = '@P'
      self._suffix_str = 'LIB' + padding
      self._op2_padding = '0L'

    def read(self, apc_file, offset, args, const_args):
      tmp_znode = APCFile.ZEND_znode('')
      tmp_znode_padding_suffix = tmp_znode.get_padding_suffix()
      offset += calcsize(self._header_str +
          tmp_znode_padding_suffix)
      self.result = apc_file.read_ptr(offset, APCFile.build_ZEND_znode,
          tmp_znode_padding_suffix)
      offset += self.result.calc_size()
      self.op1 = apc_file.read_ptr(offset, APCFile.build_ZEND_znode,
          tmp_znode_padding_suffix)
      offset += self.op1.calc_size()
      self.op2 = apc_file.read_ptr(offset, APCFile.build_ZEND_znode,
          self._op2_padding)
      offset += self.op2.calc_size()
      suffix_struct = apc_file.read_struct(offset, self._suffix_str)
      self.extended_value = suffix_struct[0].int_value
      self.lineno = suffix_struct[1].int_value
      self.opcode = suffix_struct[2].int_value

    def calc_size(self):
      tmp_znode = APCFile.ZEND_znode('')
      tmp_znode_padding_suffix = tmp_znode.get_padding_suffix()
      tmp_result = APCFile.ZEND_znode(tmp_znode.get_padding_suffix())
      tmp_op1 = APCFile.ZEND_znode(tmp_znode.get_padding_suffix())
      tmp_op2 = APCFile.ZEND_znode(self._op2_padding)
      return (calcsize(self._header_str + tmp_znode_padding_suffix) +
              tmp_result.calc_size() +
              tmp_op1.calc_size() +
              tmp_op2.calc_size() +
              calcsize(self._suffix_str))

    def get_padding_suffix(self):
      # TODO: improve correctness
      return '0P'

    def get_dict_key(self):
      return 'ZEND_op'

    def get_opcode(self):
        return self.opcode

    def get_op1(self):
        return self.op1

    def get_op2(self):
        return self.op2

    def get_result(self):
        return self.result

    def get_extended_value(self):
        return self.extended_value

  def build_ZEND_op(self, padding):
    return self.ZEND_op(padding)

# ===== ZEND_znode =====
  class ZEND_znode(CStruct):
    IS_CONST   = (1<<0)
    IS_TMP_VAR = (1<<1)
    IS_VAR     = (1<<2)
    IS_UNUSED  = (1<<3)
    IS_CV      = (1<<4)

    EXT_TYPE_UNUSED = (1<<0)

    def __init__(self, padding):
      self._compute_formats(padding)

    def read(self, apc_file, offset, args, const_args):
      znode_struct = apc_file.read_struct(offset, self._fmt_str)
      self.op_type = znode_struct[0].int_value
      if self.op_type == self.IS_CONST:
        tmp_zval = APCFile.ZEND_zval('')
        op_type_fmt = '@i%s' % tmp_zval.get_padding_suffix()
        zval_offset = offset + calcsize(op_type_fmt)
        self.constant = apc_file.read_ptr(zval_offset, APCFile.build_ZEND_zval)
      elif self.op_type in [self.IS_VAR, self.IS_CV, self.IS_TMP_VAR]:
        pass
      elif self.op_type == self.IS_UNUSED:
        # TODO: figure out if this is correct or if we actually get jmp_addr
        pass
      else:
        # TODO: raise an error
        pass

      # Read var and EA.type
      zval_EA_struct = apc_file.read_struct(offset,
          self._struct_formats[5][0])
      self.var = zval_EA_struct[1].int_value
      self.EA_type = zval_EA_struct[2].int_value

      # Read jump-related stuff
      zval_opline_struct = apc_file.read_struct(offset,
          self._struct_formats[2][0])
      self.opline_num = zval_opline_struct[1].int_value
      zval_jmp_addr_struct = apc_file.read_struct(offset,
          self._struct_formats[4][0])
      self.jmp_addr = zval_jmp_addr_struct[1].int_value

    def _compute_formats(self, padding):
      _info_zval = APCFile.ZEND_zval('')
      self._union_formats = [('c' * _info_zval.calc_size()),
                              'I', 'I', 'P', 'P', 'II']
      self._struct_formats = [('@i%s%s%s' % (
        _info_zval.get_padding_suffix(), x, padding), x) 
        for x in self._union_formats]
      self._zipped_formats = [(calcsize(x), x, y) for x, y in
          self._struct_formats]
      self._actual_format = self._zipped_formats[0]
      for x in self._zipped_formats:
        if x[0] > self._actual_format[0]:
          self._actual_format = x
      self._fmt_str = self._actual_format[1]

    def get_padding_suffix(self):
      _info_zval = APCFile.ZEND_zval('')
      candidates = ['P', 'i', 'I']
      candidates.append(_info_zval.get_padding_suffix()[1])
      pairs = [(calcsize('@%s' % x), x) for x in candidates]
      best = pairs[0]
      for x in pairs:
        if x[0] > best[0]:
          best = x
      return '0%s' % best[1]

    def get_dict_key(self):
      return 'ZEND_znode'

    def get_op_type(self):
        return self.op_type

    def get_constant(self):
        return self.constant

  def build_ZEND_znode(self, padding):
    return self.ZEND_znode(padding)

# ===== ZEND_zval =====
  class ZEND_zval(CStruct):
    def __init__(self, padding):
      self._compute_formats(padding)

    def read(self, apc_file, offset, args, const_args):
      zval_struct = apc_file.read_struct(offset, self._fmt_str)
      self.refcount__gc = zval_struct[-3].int_value
      self.type = zval_struct[-2].int_value
      self.is_ref__gc = zval_struct[-1].int_value
      masked_type = self.type & IS_CONSTANT_TYPE_MASK
      self.is_null = False
      if masked_type == IS_NULL:
        self.is_null = True
      elif masked_type == IS_LONG or masked_type == IS_BOOL:
        zval_lval_struct = apc_file.read_struct(offset,
            self._struct_formats[0][0])
        self.lval = zval_lval_struct[0].int_value
      elif masked_type == IS_DOUBLE:
        zval_dval_struct = apc_file.read_struct(offset,
            self._struct_formats[1][0])
        self.dval = zval_dval_struct[0].float_value
      elif masked_type in [IS_STRING, IS_CONSTANT, IS_OBJECT]:
        # We do this for IS_OBJECT, since APC serializes the object
        # into a string
        zval_str_struct = apc_file.read_struct(offset,
            self._struct_formats[2][0])
        import objects
        self.str = objects.MutableString(apc_file.read_len_string(zval_str_struct[0].int_value,
            zval_str_struct[1].int_value))
      elif masked_type in [IS_ARRAY, IS_CONSTANT_ARRAY]:
        zval_ht_struct = apc_file.read_struct(offset,
            self._struct_formats[3][0])
        self.ht = apc_file.read_ptr(zval_ht_struct[0].int_value,
            APCFile.build_ZEND_HashTable,
            const_args = (APCFile.build_ZEND_zval, True))
      elif masked_type == IS_RESOURCE:
        # TODO: figure this out later
        # update: uses lval somehow
        pass
      else:
        # TODO: raise error, invalid type
        pass

    def _compute_formats(self, padding):
      # zval is an union + 3 other members, so its' format is the longest
      # of all possible formats specified by the union
      self._union_formats = ['l', 'd', 'Pi', 'P', 'IP']
      self._struct_formats = [('@%sIBB%s' % (x, padding), x) for x in
          self._union_formats]
      self._zipped_formats = [(calcsize(y), x, y) for x, y in
          self._struct_formats]
      self._actual_format = self._zipped_formats[0]
      for x in self._zipped_formats:
        if x[0] > self._actual_format[0]:
          self._actual_format = x
      self._fmt_str = self._actual_format[1]

    def get_padding_suffix(self):
      candidates = ['l', 'd', 'P', 'i', 'B']
      pairs = [(calcsize('@%s' % x), x) for x in candidates]
      best = pairs[0]
      for x in pairs:
        if x[0] > best[0]:
          best = x
      return '0%s' % best[1]

    def get_dict_key(self):
      return 'ZEND_zval'

    def get_type(self):
        return self.type

  def build_ZEND_zval(self, padding):
    return self.ZEND_zval(padding)

# ===== ZEND_class_entry =====
  class ZEND_class_entry(CStruct):
    def __init__(self, padding):
      self._header_str = '@bPIPiBI'
      self._ptrs_str = '@PPPPPPPPPPPPPPPPPPPPPPPPPPPIPIIPIP' + padding

    def read(self, apc_file, offset, args, const_args):
      info_ht = APCFile.ZEND_HashTable('')
      header_struct = apc_file.read_struct(offset, self._header_str +
          info_ht.get_padding_suffix())
      offset += calcsize(self._header_str + info_ht.get_padding_suffix())

      import happy_hash
      import global_state
      import zval_utils
      from objects import MutableString
      function_table = apc_file.read_ptr(offset,
          APCFile.build_ZEND_HashTable, info_ht.get_padding_suffix(),
          const_args = (APCFile.build_ZEND_function, False))
      self.function_table = None
      if not isinstance(function_table, APCFile.NullStruct):
        self.function_table = happy_hash.zend_hash_init(None, 0, None, None, False)
        for class_method in function_table.members():
          methodname = class_method.arKey[:-1]
          happy_hash.zend_hash_add(self.function_table, MutableString(methodname), len(methodname),
            zval_utils.zp_stack(class_method.pData),
            0, global_state.null_zval_ptr_ptr)

      offset += function_table.calc_size()

      import happy_hash
      import global_state
      import zval_utils
      from objects import MutableString
      default_properties = apc_file.read_ptr(offset,
          APCFile.build_ZEND_HashTable, info_ht.get_padding_suffix(),
          const_args = (APCFile.build_ZEND_zval, True))

      offset += default_properties.calc_size()

      import happy_hash
      import global_state
      import zval_utils
      from objects import MutableString
      properties_info = apc_file.read_ptr(offset,
          APCFile.build_ZEND_HashTable, info_ht.get_padding_suffix(),
          const_args = (APCFile.build_ZEND_property_info, False))

      offset += properties_info.calc_size()
      self.default_static_members = apc_file.read_ptr(offset,
          APCFile.build_ZEND_HashTable, '0P',
          const_args = (APCFile.build_ZEND_zval, True))
      offset += self.default_static_members.calc_size()
      static_members_struct = apc_file.read_struct(offset,
          '@P' + info_ht.get_padding_suffix())
      static_members = apc_file.read_ptr(
          static_members_struct[0].int_value,
          APCFile.build_ZEND_HashTable,
          const_args = (APCFile.build_ZEND_zval, True))

      self.static_members = None
      if not isinstance(static_members, APCFile.NullStruct):
        self.static_members = happy_hash.zend_hash_init(None, 0, None, None, False)
        for static_member in static_members.members():
          member_name = static_member.arKey[:-1].replace('\0', '#')
          happy_hash.zend_hash_add(self.static_members, MutableString(member_name), len(member_name),
            zval_utils.zpp_stack(zval_utils.zp_stack(static_member.pData)),
            0, global_state.null_zval_ptr_ptr_ptr)

      offset += calcsize('@P' + info_ht.get_padding_suffix())
      self.constants_table = apc_file.read_ptr(offset,
          APCFile.build_ZEND_HashTable, '0P',
          const_args = (APCFile.build_ZEND_zval, True))
      offset += self.constants_table.calc_size()

      # Header info
      self.class_type = header_struct[0].int_value
      from objects import MutableString
      self.name = MutableString(apc_file.read_len_string(header_struct[1].int_value,
          header_struct[2].int_value))
      self.name_length = header_struct[2].int_value
      self.parent = apc_file.read_ptr(header_struct[3].int_value,
          APCFile.build_ZEND_class_entry)
      self.refcount = header_struct[4].int_value
      self.constants_updated = header_struct[5].int_value
      self.ce_flags = header_struct[6].int_value

      self.properties_info = None
      if not isinstance(properties_info, APCFile.NullStruct):
        self.properties_info = happy_hash.zend_hash_init(None, 0, None, None, False)
        for property_info in properties_info.members():
          propname = property_info.arKey[:-1]
          if property_info.pData.flags & ZEND_ACC_PRIVATE:
            property_info.pData.name = MutableString('#' + self.name.to_str() + '#' + propname)
          elif property_info.pData.flags & ZEND_ACC_PROTECTED:
            # TODO: implement zend_declare_property_ex properly in zend_API
            property_info.pData.name = MutableString('#' + '*' + '#' + propname)
          else:
            property_info.pData.name = MutableString(propname)
          happy_hash.zend_hash_add(self.properties_info, MutableString(propname), len(propname),
            zval_utils.zp_stack(property_info.pData),
            0, global_state.null_zval_ptr_ptr)

      self.default_properties = None
      if not isinstance(default_properties, APCFile.NullStruct):
        self.default_properties = happy_hash.zend_hash_init(None, 0, None, None, False)
        for default_prop in default_properties.members():
          propname = default_prop.arKey[:-1].replace('\0', '#')
          happy_hash.zend_hash_add(self.default_properties, MutableString(propname), len(propname),
            zval_utils.zpp_stack(zval_utils.zp_stack(default_prop.pData)), 0,
            global_state.null_zval_ptr_ptr_ptr)

      # TODO: read builtins
      self.create_object = None

      # Class methods
      ptrs_struct = apc_file.read_struct(offset, self._ptrs_str)
      self.constructor = apc_file.read_ptr(ptrs_struct[1].int_value,
          APCFile.build_ZEND_function)
      self.destructor = apc_file.read_ptr(ptrs_struct[2].int_value,
          APCFile.build_ZEND_function)
      self.clone = apc_file.read_ptr(ptrs_struct[3].int_value,
          APCFile.build_ZEND_function)
      self.uuget = apc_file.read_ptr(ptrs_struct[4].int_value,
          APCFile.build_ZEND_function)
      self.uuset = apc_file.read_ptr(ptrs_struct[5].int_value,
          APCFile.build_ZEND_function)
      self.uuunset = apc_file.read_ptr(ptrs_struct[6].int_value,
          APCFile.build_ZEND_function)
      self.uuisset = apc_file.read_ptr(ptrs_struct[7].int_value,
          APCFile.build_ZEND_function)
      self.uucall = apc_file.read_ptr(ptrs_struct[8].int_value,
          APCFile.build_ZEND_function)
      self.uucallstatic = apc_file.read_ptr(ptrs_struct[9].int_value,
          APCFile.build_ZEND_function)
      self.uutostring = apc_file.read_ptr(ptrs_struct[10].int_value,
          APCFile.build_ZEND_function)
      self.serialize_func = apc_file.read_ptr(ptrs_struct[11].int_value,
          APCFile.build_ZEND_function)
      self.unserialize_func = apc_file.read_ptr(ptrs_struct[12].int_value,
          APCFile.build_ZEND_function)
     
      # Iterator funcs
      self.zf_new_iterator = apc_file.read_ptr(ptrs_struct[14].int_value,
          APCFile.build_ZEND_function)
      self.zf_valid = apc_file.read_ptr(ptrs_struct[15].int_value,
          APCFile.build_ZEND_function)
      self.zf_current = apc_file.read_ptr(ptrs_struct[16].int_value,
          APCFile.build_ZEND_function)
      self.zf_key = apc_file.read_ptr(ptrs_struct[17].int_value,
          APCFile.build_ZEND_function)
      self.zf_next = apc_file.read_ptr(ptrs_struct[18].int_value,
          APCFile.build_ZEND_function)
      self.zf_rewind = apc_file.read_ptr(ptrs_struct[19].int_value,
          APCFile.build_ZEND_function)

      self.get_static_method = APCFile.NullStruct()

      # Interfaces
      self.num_interfaces = ptrs_struct[27].int_value
      iface_array_fmt_str = '@' + ('P' * self.num_interfaces)
      iface_array = apc_file.read_struct(ptrs_struct[26].int_value,
          iface_array_fmt_str)
      self.interfaces = [apc_file.read_ptr(x.int_value,
          APCFile.build_ZEND_class_entry) for x in iface_array]

      # Rest of stuff
      self.filename = apc_file.read_asciiz_string(ptrs_struct[28].int_value)
      self.line_start = ptrs_struct[29].int_value
      self.line_end = ptrs_struct[30].int_value
      self.doc_comment = apc_file.read_len_string(ptrs_struct[31].int_value,
          ptrs_struct[32].int_value)
      self.doc_comment_len = ptrs_struct[32].int_value

    def calc_size(self):
      # TODO: implement
      return 0

    def get_padding_suffix(self):
      # TODO: make better
      return '0P'

    def get_dict_key(self):
      return 'ZEND_class_entry'

  def build_ZEND_class_entry(self, padding):
    return self.ZEND_class_entry(padding)

# ===== ZEND_property_info =====
  class ZEND_property_info(CStruct):
    def __init__(self, padding):
      self._fmt_str = '@IPiLPiP'

    def read(self, apc_file, offset, args, const_args):
      pi_struct = apc_file.read_struct(offset, self._fmt_str)
      self.flags = pi_struct[0].int_value
      from objects import MutableString
      self.name = MutableString(apc_file.read_len_string(pi_struct[1].int_value,
          pi_struct[2].int_value))
      self.name_len = pi_struct[2].int_value
      self.h = pi_struct[3]
      self.doc_comment = apc_file.read_len_string(pi_struct[4].int_value,
          pi_struct[5].int_value)
      self.doc_comment_len = pi_struct[5].int_value
      self.ce = apc_file.read_ptr(pi_struct[6].int_value,
          APCFile.build_ZEND_class_entry)

    def get_dict_key(self):
      return 'ZEND_property_info'

  def build_ZEND_property_info(self, padding):
    return self.ZEND_property_info(padding)

# ===== ZEND_HashTable =====
  class ZEND_HashTable(CStruct):
    def __init__(self, padding):
      self._inconsistent_str = ''
      self._fmt_str = '@IIILPPPPPBBB' + self._inconsistent_str + padding

    @specialize.arg(4)
    def read(self, apc_file, offset, args, const_args):
      ht_struct = apc_file.read_struct(offset, self._fmt_str)
      self.nTableSize = ht_struct[0].int_value
      self.nTableMask = ht_struct[1].int_value
      self.nNumOfElements = ht_struct[2].int_value
      self.nNextFreeElement = ht_struct[3].int_value
      # FIXME: APC 3.1.10 sets pInternalPointer without swizzling it
      # so we can't read it
      #self.pInternalPointer = apc_file.read_ptr(ht_struct[4].int_value,
      #    APCFile.build_ZEND_Bucket, const_args = const_args)
      self.pListHead = apc_file.read_ptr(ht_struct[5].int_value,
          APCFile.build_ZEND_Bucket, const_args = const_args)
      self.pListTail = apc_file.read_ptr(ht_struct[6].int_value,
          APCFile.build_ZEND_Bucket, const_args = const_args)
      # ht_struct[7] == arBuckets
      self.persistent = ht_struct[8].int_value
      self.nApplyCount = ht_struct[9].int_value
      self.bApplyProtection = ht_struct[10].int_value
      # For now, set pInternalPointer to the head manually
      self.pInternalPointer = self.pListHead
      
      bucket_array_fmt_str = '@' + ('P' * self.nTableSize)
      bucket_ptr_array = apc_file.read_struct(ht_struct[7].int_value,
          bucket_array_fmt_str)
      self.arBuckets = [apc_file.read_ptr(x.int_value,
        APCFile.build_ZEND_Bucket, const_args = const_args)
        for x in bucket_ptr_array]

    def get_dict_key(self):
      return 'ZEND_HashTable'

    @staticmethod
    def zend_hash(key):
      h = r_ulonglong(5381)
      for v in key:
        h = ((h << 5) + h + ord(v))
      return h

    def get(self, key):
      h = self.zend_hash(key)
      p = self.arBuckets[h & self.nTableMask]
      while isinstance(p, APCFile.ZEND_Bucket):
        if p.arKey == key:
          return p.pData
        p = p.pNext
      return APCFile.NullStruct()

    def contains(self, key):
      h = self.zend_hash(key)
      p = self.arBuckets[h & self.nTableMask]
      while isinstance(p, APCFile.ZEND_Bucket):
        if p.arKey == key:
          return True
        p = p.pNext
      return False

    class Iter(object):
      def __init__(self, ht):
        self._ht = ht
        self._p = ht.pListHead

      def __iter__(self):
        return self

      def next(self):
        if isinstance(self._p, APCFile.ZEND_Bucket):
          res = self._p
          self._p = self._p.pListNext
          return res 
        else:
          raise StopIteration

    def iter(self):
      return self.Iter(self)

    def members(self):
      result = []
      pHead = self.pListHead
      while isinstance(pHead, APCFile.ZEND_Bucket):
        result.append(pHead)
        pHead = pHead.pListNext
      return result

  def build_ZEND_HashTable(self, padding):
    return self.ZEND_HashTable(padding)

# ===== ZEND_Bucket =====
  class ZEND_Bucket(CStruct):
    def __init__(self, padding):
      self._fmt_str = '@LIPPPPPPh' + padding

    @specialize.arg(4)
    def read(self, apc_file, offset, args, const_args):
      bucket_struct = apc_file.read_struct(offset, self._fmt_str)
      self.h = bucket_struct[0].int_value
      self.nKeyLength = bucket_struct[1].int_value
      self.pListNext = apc_file.read_ptr(bucket_struct[4].int_value,
          APCFile.build_ZEND_Bucket, const_args = const_args)
      self.pListLast = apc_file.read_ptr(bucket_struct[5].int_value,
          APCFile.build_ZEND_Bucket, const_args = const_args)
      self.pNext = apc_file.read_ptr(bucket_struct[6].int_value,
          APCFile.build_ZEND_Bucket, const_args = const_args)
      self.pLast = apc_file.read_ptr(bucket_struct[7].int_value,
          APCFile.build_ZEND_Bucket, const_args = const_args)
      # FIXME: the key is read with a terminating NULL
      self.arKey = apc_file.read_len_string(
          offset + calcsize(self._fmt_str[0:9] + '0h'), self.nKeyLength)

      # Read data
      data_builder, is_ptr = const_args
      if is_ptr:
        # Indirect reference: pData points to a pointer to the data
        ptr_str = '@P'
        ptr_struct = apc_file.read_struct(bucket_struct[2].int_value, ptr_str)
        data_ptr = ptr_struct[0].int_value
      else:
        data_ptr = bucket_struct[2].int_value
      self.pData = apc_file.read_ptr(data_ptr, data_builder)

    def get_dict_key(self):
      return 'ZEND_Bucket'

  def build_ZEND_Bucket(self, padding):
    return self.ZEND_Bucket(padding)

# ===== ZEND_arg_info =====
  class ZEND_arg_info(CStruct):
    def __init__(self, padding):
      self._fmt_str = '@PIPIBBBBi' + padding

    def read(self, apc_file, offset, args, const_args):
      arg_struct = apc_file.read_struct(offset, self._fmt_str)
      from objects import MutableString
      self.name = MutableString(apc_file.read_len_string(arg_struct[0].int_value,
          arg_struct[1].int_value))
      self.name_len = arg_struct[1].int_value
      self.class_name = apc_file.read_len_string(arg_struct[2].int_value,
          arg_struct[3].int_value)
      self.class_name_len = arg_struct[3].int_value
      self.array_type_hint = arg_struct[4].int_value
      self.allow_null = arg_struct[5].int_value
      self.pass_by_reference = arg_struct[6].int_value
      self.return_reference = arg_struct[7].int_value
      self.required_num_args = arg_struct[8].int_value

    def get_dict_key(self):
      return 'ZEND_arg_info'

  def build_ZEND_arg_info(self, padding):
    return self.ZEND_arg_info(padding)

# ===== ZEND_compiled_variable =====
  class ZEND_compiled_variable(CStruct):
    def __init__(self, padding):
      self._fmt_str = '@PiL' + padding

    def read(self, apc_file, offset, args, const_args):
      cv_struct = apc_file.read_struct(offset, self._fmt_str)
      from objects import MutableString
      self.name = MutableString(apc_file.read_len_string(cv_struct[0].int_value,
          cv_struct[1].int_value))
      self.name_len = cv_struct[1].int_value
      self.hash_value = cv_struct[2].int_value

    def get_dict_key(self):
      return 'ZEND_compiled_variable'

  def build_ZEND_compiled_variable(self, padding):
    return self.ZEND_compiled_variable(padding)

# ===== ZEND_brk_cont_element =====
  class ZEND_brk_cont_element(CStruct):
    def __init__(self, padding):
      self._fmt_str = '@iiii' + padding

    def read(self, apc_file, offset, args, const_args):
      self.start, self.cont, self.brk, self.parent_elem = (
          apc_file.read_struct(offset, self._fmt_str))

    def get_dict_key(self):
      return 'ZEND_brk_cont_element'

  def build_ZEND_brk_cont_element(self, padding):
    return self.ZEND_brk_cont_element(padding)

# ===== ZEND_try_catch_element =====
  class ZEND_try_catch_element(CStruct):
    def __init__(self, padding):
      self._fmt_str = '@II' + padding

    def read(self, apc_file, offset, args, const_args):
      self.try_op, self.catch_op = (
          apc_file.read_struct(offset, self._fmt_str))

    def get_dict_key(self):
      return 'ZEND_try_catch_element'

  def build_ZEND_try_catch_element(self, padding):
    return self.ZEND_try_catch_element(padding)


