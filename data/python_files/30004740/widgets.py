import os.path
import itertools
import pkg_resources
from turbogears.widgets import Widget, TextField
from turbogears.widgets import CSSSource, JSSource, register_static_directory
from turbogears import config
from turbojson import jsonify
from util import CSSLink, JSLink

__all__ = ['YUIBaseCSS', 'YUIResetCSS', 'YUIFontsCSS', 'YUIGrids', 'YUIResetFontsGrids',
           'YUIAnimation', 'YUIMenuBar', 'YUIAutoComplete', 'YUITreeView',
           'yuibasecss', 'yuiresetcss', 'yuifontscss', 'yuigridscss', 'yui_reset_fonts_grids',
           'YUIMenuLeftNav',
          ]

pkg_path = pkg_resources.resource_filename(__name__, os.path.join("static", "yui"))
register_static_directory("TGYUI", pkg_path)

skin = config.get('app.yui.skin', None)
skin_method = config.get('app.yui.skin_method', 'minimized')

idcounter = itertools.count()
def unique_id(prefix='tgyui'):
    """This function lets us have a new unique id each time a widget is rendered,
    to be used by generated css & javascript snippets (e.g. initializing functions,
    or instance-specific appearance).

    If you have no widgets that are fetched by XMLHttpRequest and inserted into
    the document at runtime (e.g. with innerHTML or MochiKit.DOM.swapDOM()), you
    can stop reading here.

    If you have such widgets, please note:
     - if a page retrieves a new widget after the server has been restarted,
       the idcounter variable will be reset and an old id could potentially
       be recycled.
       In order to avoid this, for widgets that are sent by XMLHttpRequest,
       you should specify an id.
     - CSSLink and JSLink directives will not be processed: you must make sure
       the exising page already contains those (i.e. by returing another widget
       instance from the controller, even if the page does not display it at first).
     - CSSSource and JSSource will be inserted in the HTML fragment as usual,
       but the browser will not run the javascript fragment. If the widget needs
       to be initialized, you might want to do that in the code that retrives and
       inserts the fragment.
       There are ways to parse the HTML fragment, extract the <script> tags and execute them,
       but it's outside the scope of this module."""

    return '%s_%d' % (prefix, idcounter.next())

def skinned(pth, resource_name):
    if not skin:
        return [
            CSSLink("TGYUI", '%s/assets/%s' % (pth, resource_name)),
            ]
    base, ext = resource_name.rsplit('.', 1)
    skin_methods = {
        'minimized': [
            CSSLink("TGYUI", '%s/assets/skins/%s/%s' % (pth, skin, resource_name)),
            ],
        'core': [
            CSSLink("TGYUI", '%s/assets/%s-core.%s' % (pth, base, ext)),
            CSSLink("TGYUI", '%s/assets/skins/%s/%s-skin.%s' % (pth, skin, base, ext)),
            ],
        'uber': [
            CSSLink("TGYUI", '%s/assets/%s-core.%s' % (pth, base, ext)),
            CSSLink("TGYUI", 'assets/skins/%s/skin.css' % skin),
            ],
    }
    if skin_method in skin_methods:
        return skin_methods[skin_method]
    else:
        raise ValueError("app.yui.skin_method must be one of '%s'" % "', '".join(skin_methods.keys()))

class YUIBaseCSS(Widget):
    css             = [CSSLink("TGYUI", "base/base-min.css")]
yuibasecss = YUIBaseCSS()

class YUIResetCSS(Widget):
    css             = [CSSLink("TGYUI", "reset/reset-min.css")]
yuiresetcss = YUIResetCSS()

class YUIFontsCSS(Widget):
    css             = [CSSLink("TGYUI", "fonts/fonts-min.css")]
yuifontscss = YUIFontsCSS()

class YUIGrids(Widget):
    css             = [CSSLink("TGYUI", "grids/grids-min.css")]
yuigridscss = YUIGrids()

class YUIResetFontsGrids(Widget):
    """Use this in place of using all the three YUIResetCSS, YUIFontsCSS,
    YUIGrids. You might want to explicitly include all three if you use other
    widgets that depend on one of them, to avoid duplications."""
    css             = [CSSLink("TGYUI", "reset-fonts-grids/reset-fonts-grids.css")]
yui_reset_fonts_grids = YUIResetFontsGrids()

class YUIAnimation(Widget):
    javascript      = [JSLink("TGYUI", "yahoo-dom-event/yahoo-dom-event.js"),
                       JSLink("TGYUI", "animation/animation-min.js"),
                       JSLink("TGYUI", "thirdparty/effects-min.js"),
                      ]

class YUIMenuBar(Widget):
    template        = 'TGYUI.templates.menubar'
    params          = ['id', 'entries', 'as_bar']
    css             = ([CSSLink("TGYUI", "reset-fonts-grids/reset-fonts-grids.css"),
                        CSSLink("TGYUI", "menu/assets/menu.css"),
                       ] + skinned('menu', 'menu.css'))
    javascript      = [JSLink("TGYUI", "yahoo-dom-event/yahoo-dom-event.js"),
                       JSLink("TGYUI", "container/container_core-min.js"),
                       JSLink("TGYUI", "menu/menu-min.js"),
                      ]
    id              = unique_id(prefix='mbar')
    as_bar          = True  # set to False for e.g., leftNav
    entries         = [('Companies', '/companies', [
                            ('add new', '/companies/add_new', []),
                            ('browse', '/companies/browse', [
                                ('by name', '/companies/browse/by_name'),
                                ('by date', '/companies/browse/by_date'),
                                ]),
                            ('list', '/companies/list', []),
                            ]),
                       ('Contacts', '/contacts', []),
                       ('Queries', '/queries', []),
                       ('Mailings', '/mailings', []),
                       ('Search', '/search', []),
                      ]

    def __init__(self, entries=None, *args, **kw):
        super(YUIMenuBar, self).__init__(*args, **kw)
        if entries:
            self.entries = entries

class YUIMenuLeftNav(YUIMenuBar):
    as_bar          = False

class YUIAutoComplete(TextField):
    "A standard, single-line text field with YUI AutoComplete enhancements."
    template        = 'TGYUI.templates.autocomplete'
    params = ["attrs", "id", "search_controller", "result_schema", "search_param"]
    params_doc = {'attrs' : 'Dictionary containing extra (X)HTML attributes for'
                            ' the input tag',
                  'id'    : 'ID for the entire AutoComplete construct.'}
    attrs = {}
    id = 'noid'
    search_param = 'input'
    javascript      = [JSLink("TGYUI", "yahoo-dom-event/yahoo-dom-event.js"),
                       JSLink("TGYUI", "json/json-min.js"),
                       JSLink("TGYUI", "autocomplete/autocomplete-min.js"),
                      ]


class YUITreeView(Widget):
    css = (skinned('treeview', 'treeview.css') +
            (skin and [CSSSource(".ygtvitem td {padding:0}.ygtvitem table {margin-bottom: 0}")] or []))

    javascript = [
        JSLink('TGYUI','yahoo/yahoo-min.js'),
        JSLink('TGYUI','event/event-min.js'),
        JSLink('TGYUI','treeview/treeview-min.js'),
        JSSource("""
        function yui_tree_init(id, entries) {
            function yui_add_branch(node, branch) {
                var newnode = new YAHOO.widget.TextNode(branch.data, node, branch.expanded);
                if (branch.children) {
                  for (var i=0; i<branch.children.length; i++) {
                      yui_add_branch(newnode, branch.children[i]);
                  }
                }
            }
            tree = new YAHOO.widget.TreeView(id);
            yui_add_branch(tree.getRoot(), entries);
            tree.draw();
        }
        """)
        ]

    template = """
    <div xmlns:py="http://purl.org/kid/ns#"
         py:strip="True">
      <div id="${id}" />
      <script type="text/javascript">
          yui_tree_init('${id}', ${entries});
      </script>
    </div>
    """

    entries = {'expanded': True,
               'data': {'href': '/stuff/foo', 'label': 'Foo'},
               'children': [
                    {'expanded': True,
                     'data': {'href': '/stuff/foo/bar', 'label': 'Bar'},
                     'children': [
                        {'expanded': True,
                         'data': {'href': '/stuff/foo/baz', 'label': 'Baz'},
                         'children': []
                        }]
                    },
                    {'expanded': True,
                    'data': {'href': '/stuff/foo/gazonk', 'label': 'Gazonk'},
                    'children': []
                    }]}
    id = None

    params = ['entries', 'id']

    def update_params(self, d):
        super(YUITreeView, self).update_params(d)
        if d['id'] is None:
            d['id'] = unique_id()
        d['entries'] = jsonify.encode(d['entries'])

# Yahoo DP: http://developer.yahoo.com/ypatterns/pattern.php?pattern=moduletabs
class YUITabView(Widget):

    css = (skinned('tabview', 'tabview.css') +
            (skin and [CSSSource(".yui-navset .yui-nav a:hover {color: #000}")] or []) +
            [CSSLink('TGYUI','tabview/assets/border_tabs.css')]
            )

    javascript = [
        JSLink('TGYUI','yahoo-dom-event/yahoo-dom-event.js'),
        JSLink('TGYUI','element/element-beta-min.js'),
        JSLink('TGYUI','connection/connection-min.js'),
        JSLink('TGYUI','tabview/tabview-min.js'),
        ]

    id = 'tgyui_tabber'
    dynamic = []       # list of dictionaries with label (string), dataSrc (uri), cacheData (bool)
    params = ['id', 'dynamic']

    template = """
    <script language="JavaScript" type="text/JavaScript">
      (function() {
        var tabview = new YAHOO.widget.TabView("${id}");
        for each (var obj in ${dynamic}) {
          tabview.addTab(new YAHOO.widget.Tab(obj))
        }
      })();
    </script>
    """

    def update_params(self, d):
        super(YUITabView, self).update_params(d)
        d['dynamic'] = jsonify.encode(d['dynamic'])
