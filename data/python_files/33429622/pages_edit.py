import copy
import web
from web.form import notnull
from google.appengine.ext import ndb
from google.appengine.api import users, memcache
from google.appengine.api import mail

from palimpsest.models import World, get_default_void, world_exists, Property, property_exists, PropertyValue, Room, text_exists
from palimpsest.logins import get_current_user, user_exists, flush_caches

from palimpsest.pages import Page, render, CreatePage
from palimpsest.utils.form import Form, CombinedForm, Submit, display_input_warning, display_form_warning

class WorldEdit(CreatePage):

    formargs = {'method':'post'}

    def GET(self, world):

        cur_world = world_exists(world)
        self.redirect_if_not_admin(cur_world)

        world_menu = self.get_or_put_menu(cur_world, "admin")

        f = self.world_form()
        form = CombinedForm([f], **self.formargs)
        f.fill(**{'title':cur_world.title,'blurb':cur_world.blurb,'publish':cur_world.publish,'is_open':cur_world.is_open,'void_text':cur_world.void_text})

        section = render().section_world(form)

        return render().admin(cur_world, section, world_menu, "%s on Palimpsest" % cur_world.title)

    def POST(self, world):

        cur_world = world_exists(world)
        self.redirect_if_not_admin(cur_world)

        o = cur_world.is_open

        world_menu = self.get_or_put_menu(cur_world, "admin")

        f = self.world_form()
        form = CombinedForm([f], **self.formargs)

        if not f.validates():
            section = render().section_world(form)
            return render().admin(cur_world, section, world_menu, "%s on Palimpsest" % cur_world.title)
        else:
            edit_world = World.get_by_id(world)
            edit_world.title=f.d.title
            edit_world.blurb=f.d.blurb
            edit_world.publish=f.d.publish
            edit_world.void_text=f.d.void_text
            edit_world.is_open=f.d.is_open
            edit_world.put()

            if o != edit_world.is_open:
                # update menu
                world_menu = self.replace_or_put_and_get_menu(edit_world, "admin")
            
            section = render().section_world(form)
            return render().admin(edit_world, section, world_menu, "%s on Palimpsest" % cur_world.title)

class PropertyEdit(CreatePage):

    formargs = {'method':'post'}
    
    def GET(self, world, prop):
        
        cur_world = world_exists(world)
        cur_prop = property_exists(prop)

        a = cur_world.get_access_string(self.page_user)
        menu = self.get_or_put_menu(cur_world, a)
        menu['properties'][0][2] = "active"

        param = web.input()
        if hasattr(param, 'r'): # In read-only mode
            section = render().section_property_read(cur_prop)
            return render().admin(cur_world, section, menu, "%s's %s on Palimpsest" % (cur_world.title, cur_prop.name))

        self.redirect_if_not_edit(cur_world, cur_prop)

        if cur_prop.valid_values == "|text|" or cur_prop.valid_values == "|num|":
            valid_vals = cur_prop.valid_values
        else:
            valid_vals = 0

        f = self.properties_form()
        f.fill(**{'name':cur_prop.name,'valid_values':valid_vals,'fixed_values':cur_prop.valid_values,'sorter':cur_prop.sorter,'info':cur_prop.info,'discrete':cur_prop.discrete})
        edit_form = CombinedForm([f], **self.formargs)
        del_form = CombinedForm([self.delete_form()], **self.formargs)

        section = render().section_property(edit_form, del_form, True)
        return render().admin(cur_world, section, menu, "%s's %s on Palimpsest" % (cur_world.title, cur_prop.name), pre=["/js/showhide_form_fields.js"])

    def POST(self, world, prop):
        cur_world = world_exists(world)
        cur_prop = property_exists(prop)
        self.redirect_if_not_edit(cur_world, cur_prop)

        a = cur_world.get_access_string(self.page_user)

        post = web.input()
        if hasattr(post, 'delete'):
            
            PropertyValue.delete_all_for_property(cur_prop)
            cur_prop.key.delete()

            """ Flush menus and available properties for everyone so they get reset"""
            # TODO: Fix cache flushing for everyone else
            memcache.delete("_properties-%s-global" % cur_world.key.id())
            if a == "admin":
                memcache.delete("%s-closed" % cur_world.key.id())
            elif a == "closed":
                memcache.delete("%s-admin" % cur_world.key.id())
            self.replace_or_put_menu(cur_world, a)

            raise web.seeother("/%s/property" % cur_world.key.id())

        f = self.properties_form()
        if not f.validates():
            menu = self.get_or_put_menu(cur_world, a)
            edit_form = CombinedForm([f], **self.formargs)
            section = render().section_property(edit_form)
            return render().admin(cur_world, section, menu, "%s's %s on Palimpsest" % (cur_world.title, cur_prop.name), pre=["/js/showhide_form_fields.js"])
        else:

            try:
                if int(f.d.valid_values) == 0:
                    valid_values = f.d.fixed_values
                else:
                    valid_values = f.d.valid_values
            except ValueError:
                valid_values = f.d.valid_values

            if f.d.discrete == "True":
                discrete = True
            else:
                discrete = False

            to_edit = cur_prop
            to_edit.name=f.d.name
            to_edit.sorter=f.d.sorter
            to_edit.info=f.d.info
            to_edit.discrete=discrete
            to_edit.valid_values=valid_values
            to_edit.last_modified_by=self.page_user.key

            to_edit.put()

        return web.seeother("/%s/property/%s" % (cur_world.key.id(), cur_prop.key.id()))

class TextEdit(CreatePage):

    formargs = {'method':'post'}

    def GET(self, world, text):
        cur_world = world_exists(world)
        cur_text = text_exists(text)

        access = cur_world.get_access_string(self.page_user)
        world_menu = self.get_or_put_menu(cur_world, access)
        world_menu['texts'][0][2] = "active"

        param = web.input()
        if hasattr(param, 'r'): # In read-only mode
            world_properties = cur_world.get_properties_allowed(self.page_user).get_result()
            try:
                js = self.js_add_properties(world_properties, cur_world)
                properties_available = True
            except IndexError:
                properties_available = False
            property_values = cur_text.get_allowed_property_values(self.page_user).get_result()
            js += self.js_one_room_on_map(cur_text)
            section = render().section_texts_read(cur_text, cur_world.is_open, properties_available, property_values)
            return render().admin(cur_world, section, world_menu, "%s on Palimpsest" % cur_text.name, pre = ['http://maps.google.com/maps/api/js?sensor=false'], js=js, post=['/js/viewroomcoords.js', '/js/add_text_properties.js'])

        self.redirect_if_not_edit(cur_world, cur_text)

        form = self.text_form()
        form.fill(**{'name':cur_text.name, 'short_desc':cur_text.short_desc, 'long_desc':cur_text.long_desc})
        return self.reset_text_page(cur_world, form, access, world_menu, cur_text)


    def POST(self, world, text):
        cur_world = world_exists(world)
        cur_text = text_exists(text)
        self.redirect_if_not_edit(cur_world, cur_text)

        a = cur_world.get_access_string(self.page_user)

        post = web.input()
        if hasattr(post, 'delete'):
            
            PropertyValue.delete_all_for_text(cur_text)
            cur_text.key.delete()

            """ Flush menus for everyone so they get reset"""
            # TODO: Fix cache flushing for everyone else
            self.replace_or_put_menu(cur_world, a)
            if a == "admin":
                memcache.delete("%s-closed" % cur_world.key.id())
            elif a == "closed":
                memcache.delete("%s-admin" % cur_world.key.id())

            raise web.seeother("/%s/text" % cur_world.key.id())

        else:

            i = web.input(long=[], lat=[], prop_name=[], prop_val=[], del_property=[], action_val=[], mod_id=[])
            coord = []
            new = []

            form = self.text_form()
            if not form.validates():
                world_menu = self.get_or_put_menu(cur_world, a)
                return self.reset_text_page(cur_world, form, a, world_menu, cur_text)
        
            else:

                cur_text.world = cur_world.key
                cur_text.name = form.d.name
                cur_text.short_desc = form.d.short_desc
                cur_text.long_desc = form.d.long_desc
                cur_text.last_modified_by = self.page_user.key
                cur_text.latitudes = i.lat
                cur_text.longitudes = i.long

                text_ftr = cur_text.put_async()

                if cur_world.is_mod(self.page_user):
                    visible = True
                    """ Flush menus for everyone so they get reset"""
                    mrpc = memcache.create_rpc()
                    m = flush_caches("", cur_world, mrpc)
                    try:
                        m.get_result()
                    except AssertionError: # There were no caches to flush - this doesn't work
                        pass
                else:
                    visible = False

                for index, name in enumerate(i.prop_name):
                    p = ndb.Key('Property', int(name))
                    new.append(PropertyValue())
                    new[index].value = i.prop_val[index]
                    new[index].of_property = p
                    new[index].room = cur_text.key
                    new[index].added_by = self.page_user.key
                    new[index].visible = visible

                new_values_ftrs = ndb.put_multi_async(new)

                value_keys = []
                for index, p_id in enumerate(i.del_property):
                    value_keys.append(ndb.Key('PropertyValue', int(p_id)))
                ndb.delete_multi(value_keys)

                for ftr in new_values_ftrs:
                    ftr.get_result()

                text_ftr.get_result()

                self.set_menu(cur_world, a)

                return web.seeother("/%s/text/%s" % (cur_world.key.id(), cur_text.key.id()))
            