import logging
from fnmatch import fnmatch
import os
import os.path as op
from pkg_resources import resource_listdir, resource_isdir, resource_filename
from django_assets import Bundle, register
import coffeescript

#import cssutils

# to get rid of all the CSS compiling output
#cssutils.log.setLevel(logging.WARN)

def list_files(dir_, filter_=None, recurse=True):
    '''Returns a list of the resource files within the dir, relative to
    krum.webui:static/'''
    ret = []

    files = resource_listdir('krum.webui', 'static/'+dir_)
    for f in files:
        rel_p = op.join(dir_,f)
        if resource_isdir('krum.webui', 'static/'+rel_p):
            # do it again!
            if recurse:
                ret.extend(list_files(rel_p))
        # make sure it matches the filter
        elif not filter_ or fnmatch(rel_p, filter_):
            ret.append(rel_p)
    return ret

def py_coffeescript(_in, out, **kw):
    out.write(coffeescript.compile(_in.read()))


files = ['js/lib/'+x for x in ['jquery-1.8.3.js','jquery-ui-1.9.2.custom.js','underscore.js','backbone-0.9.9.js','handlebars-1.0.rc.2.js','bootstrap.js']]
js = Bundle(*files,output='gen/lib.js')
register('js_lib', js)

files = ['js/common/'+x for x in ['selecttable.js','util.js']]
js = Bundle(*files,output='gen/common.js')
register('js_common', js)

js = Bundle('js/library/library.js.coffee',
              filters=(py_coffeescript), output='gen/mod_library.js')
register('js_mod_library', js)

files = list_files('css', '*.css')
#files.append(Bundle(*list_files('css', '*.scss'), filters='pyscss'))
css = Bundle(*files,
             output='gen/common.css')

register('css_common', css)

# set up JS template gear
os.environ['JST_COMPILER'] = 'Handlebars.compile'
os.environ['JST_NAMESPACE'] = 'window.HBT'
os.environ['JST_BARE'] = 'True'
hbt = Bundle(*list_files('js_templates', '*.hb'),
             filters='jst', output='gen/templates.js')

register('hbt', hbt)
