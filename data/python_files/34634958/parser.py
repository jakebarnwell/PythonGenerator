import hashlib
import re
from django.core import urlresolvers
import logging
import importlib
from django.core.cache import cache
from django.core.urlresolvers import resolve
from django.conf import settings

def import_parser(name, request):

  try:

    if not request:
        logging.error('Shortcodes no request information')

    # Search installed apps for the shortcode
    for app_name in settings.INSTALLED_APPS:
      if not "django" in app_name:
        module_name = app_name + '.editor.shortcodes.' + name
        try:
          mod = importlib.import_module(module_name)
        except ImportError:
          continue

        break

  except ValueError:
    logging.error('Shortcodes missing shortcode, please add shortcodes.py in [app name].shortcodes.parsers.[short code name]' + name)
    return None

  return mod

def parse(value, request):

  ex = re.compile(r'\[(.*?)\]')
  groups = ex.findall(value)
  pieces = {}
  parsed = value

  for item in groups:
    cache_key = memcached_safe_key(item)

    if ' ' in item:
      name, space, args = item.partition(' ')
      args = __parse_args__(args)
    else:
      name = item
      args = {}

    args['request'] = request
    try:

      module = import_parser(name, request)
      function = getattr(module, 'parse')
      result = function(args)
      try:
        parsed = re.sub(r'\[' + re.escape(item) + r'\]', result, parsed)
      except:
        pass
    except (ImportError, AttributeError):
      pass
  return parsed

def __parse_args__(value):
  ex = re.compile(r'[ ]*(\w+)=([^" ]+|"[^"]*")[ ]*(?: |$)')
  groups = ex.findall(value)
  kwargs = {}

  for group in groups:
    if group.__len__() == 2:
      item_key = group[0]
      item_value = group[1]

      if item_value.startswith('"'):
        if item_value.endswith('"'):
          item_value = item_value[1:]
          item_value = item_value[:item_value.__len__() - 1]

      kwargs[item_key] = item_value
  return kwargs

def memcached_safe_key(string, block_size=2**14):
  md5 = hashlib.md5()
  md5.update(string)
  return md5.hexdigest()
