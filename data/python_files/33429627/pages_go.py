import web
import json
from web.form import notnull
from google.appengine.ext import ndb
from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.api import memcache

from palimpsest.models import World, get_default_void, world_exists, Room, Property, PropertyValue, SavePath, make_save_name, save_exists
from palimpsest.logins import get_current_user, user_exists

from palimpsest.pages import Page, render, encode, make_world_slug
from palimpsest.utils.form import Form, CombinedForm, Submit, display_input_warning, display_form_warning

class GoPage(Page):

    def can_access_world(self, world):
        if world is not None:
            if world.publish:
                return
            if get_current_user():
                if world.creator == self.page_user.key:
                    return
        raise web.notfound()

    def can_edit_save(self, save):
        if save is not None:
            if get_current_user():
                if save.user == self.page_user.key:
                    return
        raise web.notfound()

    def cache_get_or_put_room_keys(self, world):
        key = "roomkeys-%s" % world.key.id()
        cached_keys = memcache.get(key)
        if cached_keys is not None:
            return cached_keys
        else:
            #room_keys = world.get_room_keys().get_result()
            memcache.add(key, world.get_room_keys().get_result())
            return memcache.get(key)

    def cache_get_or_put_property_values(self, room):
        key = "values-%s" % room.key.id()
        cached = memcache.get(key)
        if cached is not None:
            return cached
        else:
            memcache.add(key, room.get_property_values().get_result())
            return memcache.get(key)

    def js_coords_list(self, world, postback, sofaurl):
        room_keys = self.cache_get_or_put_room_keys(world)

        js1 = "var roomIds = ["
        js = "\nvar rooms = ["

        for room_key in room_keys:

            room = room_key.get()

            if room.visible:
                lats = room.latitudes
                lons = room.longitudes

                js1 += "'" + encode(str(room.key.id())) + "',"
                if len(lats) > 0:
                    js += "["
                    for x in range(len(lats)):
                        js += "new google.maps.LatLng("+encode(lats[x])+", "+encode(lons[x])+"),"
                    js = js[:-1] + "],"

        js1 = js1[:-1] + "];"
        js = js[:-1] + "];"
        js = js1 + js

        js += "\nrooms.sort(function() { return 0.5 - Math.random() });"

        js += "\nvar postUrl = \"%s\";" % postback
        js += "\nvar sofaUrl = \"%s\";" % sofaurl
        js += "\nvar voidText = \"%s\";" % world.void_text

        return js

    def js_make_room_json(self, room):
        infostring = "<h3>More information about %s</h3>" % room.name
        values = self.cache_get_or_put_property_values(room)
        for value in values:
            prop = value.of_property.get()
            if prop.info:
                infostring += "<p>%s: <strong>%s</strong></p>" % (prop.name, value.value)
        if len(values) < 1:
            infostring += "<p>There's no additional information available about this text right now.</p>"

        s_d = room.short_desc.replace("\n", "<br/>")
        l_d = room.long_desc.replace("\n", "<br/>")

        out = {
            "room":"<h3>%s</h3><p class='short'>%s</p><p class='long'>%s</p><p class='btn color1-bg lighter show-long'>Read more</p>" % (room.name, s_d, l_d), 
            "roominfo": infostring
        }

        return json.dumps(out)

class WorldCover(GoPage):

    def js_all_rooms_on_map(self, world):
        rooms_ftr = world.get_rooms()
        rooms = rooms_ftr.get_result()
        
        if rooms == []:
            js = "var rooms=[];"
            return js

        js = "var rooms = ["

        for room in rooms:
            lats = room.latitudes
            lons = room.longitudes

            if len(lats) > 0 and len(lons) > 0:
                js += "["
                for x in range(len(lats)):
                    js += "new google.maps.LatLng("+encode(lats[x])+", "+encode(lons[x])+"),"
                js = js[:-1] + "],"

        js = js[:-1] + "];"

        return js
    
    def GET(self, worldkey):
        world = world_exists(worldkey)
        #self.can_access_world(world)
        self.redirect_if_not_exists(world, "/yours/new")
        try:
            if not world.publish:
                raise web.notfound()
        except AttributeError:
            web.seeother("/yours/new")

        js = self.js_all_rooms_on_map(world)

        return render().cover(world, pre=['http://maps.google.com/maps/api/js?sensor=false'], js=js, post=['/js/all_rooms_on_map.js'])

    def POST(self, worldkey):
        world = world_exists(worldkey)
        self.can_access_world(world)

        i = web.input()

        trimmed = i.savename.strip()
        if trimmed == "" or trimmed is None:
            if hasattr(i, 'saveandgo'):
                return web.seeother("%s/go" % worldkey)
            elif hasattr(i, 'sofago'):
                return web.seeother("%s/go?s=1" % worldkey)
            else:
                return web.seeother("%s" % worldkey)

        savename = make_save_name(i.savename, self.page_user)
        new_save = SavePath(name=savename, user=self.page_user.key, publish=False)
        save_ftr = new_save.put_async()
        s = save_ftr.get_result()

        if hasattr(i, 'saveandgo'):
            return web.seeother("%s/save/%s" % (worldkey, s.integer_id()))
        elif hasattr(i, 'sofago'):
            return web.seeother("/%s/save/%s?s=1" % (worldkey, s.integer_id()))


class WorldGo(GoPage):
    
    def GET(self, worldkey):
        world = world_exists(worldkey)
        #self.can_access_world(world)
        self.redirect_if_not_exists("/")
        if not world.publish:
            raise web.notfound()

        sofaUrl = "/%s/go?s=1" % world.key.id()

        param = web.input()
        if hasattr(param, 's'): # In sofa mode
            post = ['/js/maps.google.polygon.containsLatLng.js', '/js/page_scroll.js', '/js/text_queue.js', '/js/room_expand.js','/js/sofa_location.js', '/js/toggle_info.js']
        else:
            post = ['/js/maps.google.polygon.containsLatLng.js', '/js/page_scroll.js', '/js/text_queue.js', '/js/room_expand.js','/js/get_location.js', '/js/toggle_info.js']

        js = self.js_coords_list(world, "/%s/go" % world.key.id(), sofaUrl)

        return render().go(title="%s on Palimpsest" % world.title
                            ,navleft=[('Back to %s' % world.title,'/%s' % world.key.id())]
                            ,pre=['http://maps.google.com/maps/api/js?sensor=false', '/js/set_page_height.js']
                            ,js=js
                            ,post=post
                        )
    
    def POST(self, worldkey):
        world = world_exists(worldkey)
        self.redirect_if_not_exists("/")
        self.can_access_world(world)

        i = web.input()
        key = int(i.key)
        room = Room.get_by_id(key)

        return self.js_make_room_json(room)

class WorldSave(GoPage):
    require_login = True
    def GET(self, worldkey, save):
        world = world_exists(worldkey)
        save = save_exists(save)
        self.redirect_if_not_exists(world, "/yours/saves")
        self.redirect_if_not_exists(save, "/yours/saves")
        #self.can_access_world(world)
        self.can_edit_save(save)
        if not world.publish:
            raise web.notfound()

        sofaUrl = "/%s/save/%s?s=1" % (world.key.id(), save.key.id())

        param = web.input()
        if hasattr(param, 's'): # In sofa mode
            post = ['/js/maps.google.polygon.containsLatLng.js', '/js/page_scroll.js', '/js/text_queue.js', '/js/room_expand.js','/js/sofa_location.js', '/js/toggle_info.js']
        else:
            post = ['/js/maps.google.polygon.containsLatLng.js', '/js/page_scroll.js', '/js/text_queue.js', '/js/room_expand.js','/js/get_location.js', '/js/toggle_info.js']
        
        js = self.js_coords_list(world, "/%s/save/%s" % (world.key.id(), save.key.id()), sofaUrl)

        return render().go(title="%s on Palimpsest" % world.title
                        ,navleft=[('Back to %s' % world.title,'/%s' % world.key.id())]
                        ,pre=['http://maps.google.com/maps/api/js?sensor=false', '/js/set_page_height.js']
                        ,js=js
                        ,post=post
                    )

    def POST(self, worldkey, savekey):
        world = world_exists(worldkey)
        save = save_exists(savekey)
        self.redirect_if_not_exists(world, "/yours/saves")
        self.redirect_if_not_exists(save, "/yours/saves")
        #self.can_access_world(world)
        self.can_edit_save(save)
        if not world.publish:
            raise web.notfound()

        i = web.input()
        key = int(i.key)

        room_ftr = Room.get_by_id_async(key)
        save_ftr = SavePath.get_by_id_async(int(savekey))
        room = room_ftr.get_result()
        thesave = save_ftr.get_result()
        new_texts = thesave.texts
        new_texts.append(room.key)
        thesave.texts = new_texts
        new_save_ftr = thesave.put_async()
        json = self.js_make_room_json(room)
        new_save_ftr.get_result()

        return json