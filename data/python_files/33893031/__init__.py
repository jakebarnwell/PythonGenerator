import colander
from urllib import urlencode
import venusian
from lxml import etree, html, builder
from persistent import Persistent
from pyramid.httpexceptions import WSGIHTTPException, HTTPFound
from pyramid.registry import (
    predvalseq,
    Deferred,
    )
from pyramid.request import Request
from pyramid.router import Router
from pyramid.security import has_permission
from substanced.schema import Schema
from substanced.interfaces import IFolder
from substanced.folder import Folder
from substanced.form import FormView
from substanced.property import PropertySheet
from substanced.sdi import mgmt_view
from substanced.sdi import MANAGE_ROUTE_NAME
from repoze.xmliter.utils import getHTMLSerializer

import inspect
from pyramid.config.views import viewdefaults # XXX not an API
from pyramid.config.util import action_method # XXX not an API
from pyramid.interfaces import IView


class Tile(Persistent):
    
    def __init__(self, _type):
        self._type = _type

    def get_properties(self):
        return getattr(self, 'data', {})

    def set_properties(self, struct):
        self.data = struct


def persistent_tile(view):
    def render_tile(request):
        if hasattr(request, 'tile_data'):
            data = request.tile_data
            name = data.pop('name')
        else:
            name = request.GET.get('name')
        if name is None:
            raise ValueError('Tile name must be specified')

        try:
            if '__tiles__' in request.context:
                tile = request.context['__tiles__'].get(name)
                if tile is not None:
                    data = tile.get_properties()
        except TypeError:
            pass
        return view(request, data)
    return render_tile


class tile(object):
    """ Use as a decorator for a tile view.  Accepts a name and a colander schema. """
    venusian = venusian
    def __init__(self, **settings):
        self.__dict__.update(settings)

    def __call__(self, wrapped):
        settings = self.__dict__.copy()
        def callback(context, name, ob):
            config = context.config.with_package(info.module)
            config.add_tile(ob, **settings)
        info = self.venusian.attach(wrapped, callback, category='pyramid_tiles')
        return wrapped


@viewdefaults
@action_method
def add_tile(
    config,
    view=None,
    name="",
    schema=colander.Schema(),
    permission=None,
    request_type=None,
    request_method=None,
    request_param=None,
    containment=None,
    attr=None,
    renderer=None, 
    wrapper=None,
    xhr=None,
    accept=None,
    header=None,
    path_info=None, 
    custom_predicates=(),
    context=None,
    decorator=None,
    mapper=None, 
    http_cache=None,
    match_param=None,
    tab_title=None,
    tab_condition=None,
    **predicates
    ):
    
    view = config.maybe_dotted(view)
    context = config.maybe_dotted(context)
    containment = config.maybe_dotted(containment)
    mapper = config.maybe_dotted(mapper)
    decorator = config.maybe_dotted(decorator)

    name = 'tile:' + name
    view = persistent_tile(view)

    pvals = predicates.copy()
    pvals.update(
        dict(
            xhr=xhr,
            request_method=request_method,
            path_info=path_info,
            request_param=request_param,
            header=header,
            accept=accept,
            containment=containment,
            request_type=request_type,
            match_param=match_param,
            custom=predvalseq(custom_predicates),
            )
        )

    predlist = config.get_predlist('view')
    
    def view_discrim_func():
        # We need to defer the discriminator until we know what the phash
        # is.  It can't be computed any sooner because thirdparty
        # predicates may not yet exist when add_view is called.
        order, preds, phash = predlist.make(config, **pvals)
        return ('view', context, name, None, phash)

    view_discriminator = Deferred(view_discrim_func)

    if inspect.isclass(view) and attr:
        view_desc = 'method %r of %s' % (attr, config.object_description(view))
    else:
        view_desc = config.object_description(view)

    config.add_view(
        view=view,
        name=name,
        permission=permission,
        request_method=request_method,
        request_param=request_param,
        containment=containment,
        attr=attr,
        renderer=renderer, 
        wrapper=wrapper,
        xhr=xhr,
        accept=accept,
        header=header, 
        path_info=path_info,
        custom_predicates=custom_predicates, 
        context=context,
        decorator=decorator,
        mapper=mapper, 
        http_cache=http_cache,
        match_param=match_param, 
        request_type=request_type,
        **predicates
        )
    
    discriminator = ('tile', name[5:])
    intr = config.introspectable('tiles', discriminator, view_desc, 'tile')
    intr['schema'] = schema
    intr.relate('views', view_discriminator)
    config.action(discriminator, introspectables=(intr,))


TILE_XPATH = etree.XPath("/html/body//tile")


def append_text(element, text):
    if text:
        element.text = (element.text or '') + text


def append_tail(element, text):
    if text:
        element.tail = (element.tail or '') + text


def replace_content_with_children(element, wrapper):
    parent = element.getparent()
    index = parent.index(element)
    if index == 0:
        previous = None
    else:
        previous = parent[index - 1]
    if wrapper is None:
        children = []
    else:
        if index == 0:
            append_text(parent, wrapper.text)
        else:
            append_tail(previous, wrapper.text)
        children = wrapper.getchildren()
    parent.remove(element)
    if not children:
        if index == 0:
            append_text(parent, element.tail)
        else:
            append_tail(previous, element.tail)
    else:
        append_tail(children[-1], element.tail)
        children.reverse()
        for child in children:
            parent.insert(index, child)


def tile_render_tween_factory(handler, registry):

    def tile_render_tween(request):
        response = handler(request)
        if response.content_type == 'text/html':
            if isinstance(response, WSGIHTTPException):
                # the body of a WSGIHTTPException needs to be "prepared"
                response.prepare(request.environ)

            serializer = getHTMLSerializer(response.app_iter)
            tree = serializer.tree
            head_node = tree.getroot().find('head')

            for tile_node in TILE_XPATH(serializer.tree):
                # determine tile path
                tile_path = tile_node.attrib.get('path')
                tile_type = tile_node.attrib.get('type')
                if tile_path and tile_type:
                    if tile_path == '/':
                        path = '/tile:' + tile_type
                    else:
                        path = '/'.join((tile_path, 'tile:' + tile_type))
                elif tile_path:
                    path = tile_path
                elif tile_type:
                    path = request.resource_path(request.context, 'tile:' + tile_type)
                else:
                    # XXX how can we show a useful line number?
                    raise Exception('Tile must have a path or type')

                # fetch tile contents
                subrequest = Request.blank(path)
                subrequest.registry = registry
                tile_data = dict(tile_node.attrib)
                tile_data['innerHTML'] = (tile_node.text or '') + ''.join([html.tostring(child) for child in tile_node.iterchildren()])
                if tile_path:
                    edit_url = request.route_path(MANAGE_ROUTE_NAME, 'edit_tile', traverse=tile_path)
                else:
                    edit_url = request.mgmt_path(request.context, 'edit_tile')
                edit_url += '?' + urlencode(tile_data)
                del tile_data['type']
                subrequest.tile_data = tile_data
                tile_response = handler(subrequest)
                tile_tree = getHTMLSerializer(tile_response.app_iter).tree
                tile_root = tile_tree.getroot()
                tile_body = tile_root.find('body')

                # add edit link
                if has_permission('Edit tile', subrequest.context, request):
                    edit_link = builder.E.a('', href=edit_url)
                    edit_link.append(etree.Entity('#9997'))
                    tile_body.append(edit_link)

                # insert tile content
                tile_head = tile_root.find('head')
                if tile_head is not None:
                    for child in tile_head:
                        head_node.append(child)
                if tile_tree is not None:
                    replace_content_with_children(tile_node, tile_body)

            response.app_iter = [serializer.serialize()]

        return response

    return tile_render_tween


@mgmt_view(context=Tile, name='properties', renderer='substanced.sdi:templates/form.pt',
           tab_title='Properties', permission='sdi.edit-properties', tab_condition=False)
class TilePropertiesView(FormView):

    buttons = ('save',)
    
    def __init__(self, request):
        self.request = request
        self.context = request.context
        intr = request.registry.introspector.get('tiles', ('tile', self.context._type))
        self.schema = intr['schema']

    def save_success(self, appstruct):
        self.context.set_properties(appstruct)
        return HTTPFound(self.request.mgmt_path(self.context, '@@properties'))

    def show(self, form):
        appstruct = self.context.get_properties()
        return {'form':form.render(appstruct=appstruct)}


@mgmt_view(context=IFolder, name='edit_tile', tab_title='Edit Tile', 
           permission='sdi.add-content',
           renderer='substanced.sdi:templates/form.pt', tab_condition=False)
class AddTileView(FormView):
    title = 'Add Tile'

    def __call__(self):
        if '__tiles__' not in self.request.context:
            self.request.context.add('__tiles__', Folder(), send_events=False)
        tiles = self.request.context['__tiles__']
        tile_name = self.request.GET.pop('name')
        if tile_name in tiles:
            tile = tiles[tile_name]
        else:
            tile_type = self.request.GET.pop('type')
            tiles[tile_name] = tile = Tile(tile_type)
            # XXX mass assignment vuln, need to validate
            tile.set_properties(dict(self.request.GET))
        return HTTPFound(self.request.mgmt_path(tile, '@@properties'))


def includeme(config):
    config.add_content_type(
        'tile', Tile, add_view='edit_tile',
        )
    config.add_directive('add_tile', add_tile)
    config.add_tween('pyramid_tiles.tile_render_tween_factory', over='MAIN')
    config.scan()

__all__ = ('Tile', 'tile',)
