import logging
logging.basicConfig(level=logging.DEBUG)
import web
from web.form import notnull
from google.appengine.ext import ndb
from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.api import memcache

from palimpsest.models import World, get_default_void, world_exists, Property, PropertyValue, Room, User, UserPending, Moderator, get_google_user_key, user_exists_bykey
from palimpsest.logins import get_current_user, user_exists, add_user_to_cache_list, flush_caches

from palimpsest.pages import Page, render, encode, make_world_slug
from palimpsest.utils.form import Form, CombinedForm, Submit, display_input_warning, display_form_warning

class CreatePage(Page):
    require_login = True

    """ Menus """

    def menu_key(self, world, access):
        return "%s-%s" % (world.key.id(), access)

    def get_menu(self, world, access):
        key = self.menu_key(world, access)
        data = memcache.get(key)
        return data

    def put_menu(self, world, access):
        key = self.menu_key(world, access)
        data = self.make_menu(world)
        memcache.add(key, data)

        try:
            """ If access can be an int, it's a user_id(), so add to list of users with personal menus. """
            int(access)
            add_user_to_cache_list("", world, access)
        except ValueError:
            pass

        return data

    def get_or_put_menu(self, world, access):
        data = self.get_menu(world, access)
        if data is not None:
            return data
        else:
            return self.put_menu(world, access)

    def replace_menu(self, world, access):
        key = self.menu_key(world, access)
        data = self.make_menu(world)
        return memcache.replace(key, data)

    def replace_or_put_and_get_menu(self, world, access):
        data = self.replace_menu(world, access)
        if data:
            return self.get_menu(world, access)
        else:
            return self.put_menu(world, access)

    def set_menu(self, world, access):
        key = self.menu_key(world, access)
        data = self.make_menu(world)

        try:
            """ If access can be an int, it's a user_id(), so add to list of users with personal menus. """
            int(access)
            add_user_to_cache_list("", world, access)
        except ValueError:
            pass

        return memcache.set(key, data)

    def set_and_get_menu(self, world, access):
        if self.set_menu(world, access):
            return self.get_menu(world, access)
        else:
            return False

    def replace_or_put_menu(self, world, access):
        if not self.replace_menu(world, access):
            self.put_menu(world, access)

    empty_menu = {
                 "properties":[["Properties", "", "disabled", "[+]"]]
                ,"texts":[["Texts", "", "disabled", "[+]"]]
                ,"contributors":[["Moderators", "", "disabled", ">"]]
                ,"moderation":[]
        }

    def make_menu(self, cur_world):

        world_menu = {
                     "properties":[["Properties", "/%s/property" % cur_world.key.id(), "", "icon-plus-sign"]]
                    ,"texts":[["Texts", "/%s/text" % cur_world.key.id(), "", "icon-plus-sign"]]
                    ,"contributors":[]
                    ,"moderation":[]
        }
        if cur_world.is_admin(self.page_user):
            world_menu['contributors'].append(["Moderators", "/%s/mods" % cur_world.key.id(), "", "icon-chevron-right"])
            if cur_world.is_open:
                world_menu['moderation'].append(("Pending contributions", "/%s/mod" % cur_world.key.id(), "", "icon-chevron-right"))
        
        world_stuff = cur_world.get_everything_allowed(self.page_user).get_result()
        properties = world_stuff[0]
        rooms = world_stuff[1]

        for pr in properties:
            if pr.visible == False:
                name = "%s (pending)" % pr.name
            else:
                name = pr.name
            world_menu['properties'].append((name, "/%s/property/%s" % (cur_world.key.id(), pr.key.id()), ""))

        for r in rooms:
            if r.visible == False:
                name = "%s (pending)" % r.name
            else:
                name = r.name
            world_menu['texts'].append((name, "/%s/text/%s" % (cur_world.key.id(), r.key.id()), ""))

        return world_menu

    """ Forms """
    def_world = World._get_default_world()

    world_form = Form(
           web.form.Textbox('title', notnull, description='Give your experience a title', required='true')
          ,web.form.Textarea('blurb', description='Write a blurb for your experience')
          ,web.form.Textarea('void_text', notnull, description='The void text is what will appear when a user has been outside of any text areas for more than ten seconds.', required='true')
          ,web.form.Checkbox('is_open', value=True, description='Allow anyone to submit texts to this world (for moderation by you and your contributors)?')
          ,web.form.Checkbox('publish', value=True, description='Publish, for all the word to see')
          ,Submit('save_new', value='Save')
          , pre_input=display_input_warning
          , pre_form=display_form_warning
      )

    properties_form = Form(
             web.form.Textbox('name', notnull, description='Property name. Eg. Author, Weather, Genre...', required='true')
            ,web.form.Dropdown('valid_values', [('|text|', 'Anything: text, numbers, etc'), ('|num|', 'Number/Date only'), (0, 'From a fixed list (that you can specify next) >')], description='What kind of property is this?', id="p_opts")
            ,web.form.Textbox('fixed_values', description='What are the fixed set of values the property can be? Separate them with the pipe character: | I.e. "Summer|Winter|Autumn|Spring"', id="p_vals")
            ,web.form.Checkbox('sorter', value=True, description='This is a property that the user can filter texts by.')
            ,web.form.Checkbox('info', value=True, description='This is a property that shows up as extra information about a text.')
            ,web.form.Dropdown('discrete', [(True, 'checkboxes'), (False, 'a sliding scale')], description='User can filter by this property with ')
            ,Submit('save_properties', value='Save')
            , pre_input=display_input_warning
            , pre_form=display_form_warning
      )

    text_form = Form(
             web.form.Textbox('name', notnull, description="Title of the text", required='true')
            ,web.form.Textarea('short_desc', notnull, description="The shorter extract, which is what will come up first", required='true')
            ,web.form.Textarea('long_desc', description="A longer extract, if applicable")
            , pre_input=display_input_warning
            , pre_form=display_form_warning
      )

    delete_form = Form(
             Submit('delete', value='Delete Permanently')
            , pre_input=display_input_warning
            , pre_form=display_form_warning
      )

    vemail = web.form.regexp(r".*@.*", "must be a valid email address")
    moderator_form = Form(
             web.form.Textbox('add_contrib', notnull, vemail, description="Email address")
            ,Submit('save_contrib', value='Send invitation')
            , pre_input=display_input_warning
            , pre_form=display_form_warning
      )

    def redirect_if_not_admin(self, cur_world):
        """ Can add/edit/mod everything """
        self.redirect_if_not_exists(cur_world, "/yours/new")
        if not cur_world.is_admin(self.page_user):
            raise web.seeother('/yours')

    def redirect_if_not_create(self, cur_world):
        """ Current user can't add new things to cur_world. """
        """ Things can be added by anyone if the world is open, or only moderators when the world is closed. """
        self.redirect_if_not_exists(cur_world, "/yours/new")
        if not (cur_world.is_open or cur_world.is_mod(self.page_user)):
            raise web.forbidden()

    def redirect_if_not_edit(self, world, thing):
        self.redirect_if_not_exists(world, "/yours/new")
        self.redirect_if_not_exists(thing)
        self.redirect_if_not_create(world) # Things can only be edited by moderators unless the world is open (when people can edit their own)
        if thing.world != world.key:
            raise web.notfound()
        if not world.is_mod(self.page_user):
            """ If they're a moderator, can edit anything, they don't get to here. """
            if thing.visible:
                """ If it's visible, non-mods see read-only version. """
                thing_class = thing.__class__.__name__.lower()
                if thing_class == "room":
                    thing_type = "text"
                else:
                    thing_type = thing_class
                raise web.seeother("/%s/%s/%s?r=1" % (world.key.id(), thing_type, thing.key.id()))
            else:
                """ If it's not visible, they can edit it if they made it. """
                if not thing.useable_by(self.page_user):
                    raise web.forbidden()

    def reset_text_page(self, world, form, access, world_menu, text=None):
        
        js = self.js_all_rooms_on_map(world)
        world_properties = world.get_properties_allowed(self.page_user)

        if text is not None:
            del_form = CombinedForm([self.delete_form()], **{'method':'post'})
            edit = True
            title = "Edit %s in %s on Palimpsest" % (text.name, world.title)
            js+= self.js_editable_room_on_map(text)
            post = ['/js/editroomcoords.js']

            propvals = {}
            allowed_ftr = text.get_allowed_property_values(self.page_user)
            if world.is_mod(self.page_user):
                pending_ftr = text.get_pending_property_values()
            propvals['visible'] = allowed_ftr.get_result()
            if world.is_mod(self.page_user):
                propvals['pending'] = pending_ftr.get_result()
            else:
                propvals['pending'] = []

        else:
            del_form = None
            edit = False
            propvals = []
            title = "Add a new text to %s on Palimpsest" % world.title
            post = ['/js/addroomcoords.js']

        try:
            js += self.js_add_properties(world_properties, world)
            properties_available = True
        except IndexError:
            properties_available = False

        pre = ['http://maps.google.com/maps/api/js?sensor=false', '/js/add_text_properties.js']
        section = render().section_texts(form, properties_available, del_form, edit, propvals)

        return render().admin(world, 
                              section, 
                              world_menu, 
                              title=title,
                              pre=pre,
                              js=js, 
                              post=post
                            )    


    """ JS """
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

    def js_editable_room_on_map(self, text):
        lats = text.latitudes
        lons = text.longitudes
        if len(lats) > 0:
            js = "var toEdit = ["
            for index, lat in enumerate(lats):
                js += "new google.maps.LatLng(%s, %s)," % (encode(lat), encode(lons[index]))
            js = js[:-1] + "];"
        else:
            js = "var toEdit = [];"
        return js

    def js_one_room_on_map(self, text):
        lats = text.latitudes
        lons = text.longitudes
        if len(lats) > 0:
            js = "var aRoom = ["
            for index, lat in enumerate(lats):
                js += "new google.maps.LatLng(%s, %s)," % (encode(lat), encode(lons[index]))
            js = js[:-1] + "];"
        else:
            js = "var aRoom = [];"
        return js

    def js_add_properties(self, properties, world):

        if world.is_mod(self.page_user):
            key = "_properties-%s-global" % world.key.id()
        else:
            key = "_properties-%s-%s" % (world.key.id(), self.page_user.user.user_id())

        js = memcache.get(key)
        if js is not None:
            return js

        world_properties = properties.get_result()
        js = ""
        values_list = ""
        properties_select = "<p id=\"prop_change\"><select id=\"prop_name\" name=\"prop_name\" class=\"prop_name\">"
        first_property_input = world_properties[0].get_input_type()
        for w_p in world_properties:
            properties_select += "<option value=\"%i\">%s</option>" % (w_p.key.id(), w_p.name)

            if w_p.discrete and w_p.valid_values != "|text|" and w_p.valid_values != "|num|":
                #split, sort, rejoin and append
                raw_vals = w_p.valid_values.split("|")
                sorted_vals = sorted(raw_vals)
                sorted_str = "|".join(sorted_vals)
                values_list += "<p id=\"%i\">%s</p>" % (w_p.key.id(), sorted_str)
            else:
                values_list += "<p id=\"%i\">%s</p>" % (w_p.key.id(), str(w_p.valid_values))

        properties_select += "</select>"
        properties_select += first_property_input
        properties_select += "</p>"

        values_js = "\njQuery('#validValues').append('%s');" % values_list
        properties_js = "\njQuery('#propertyBtn').click(function() {"
        properties_js += "\n\tjQuery('#propertyBtns').prepend('%s');" % properties_select
        properties_js += "\n\tjQuery('#prop_change select').change(function() {"
        properties_js += "\n\t\tvar optval = jQuery(this).find('option:selected').val();"
        properties_js += "\n\t\tvar valid = jQuery('#'+optval).text();"
        properties_js += "\n\t\tjQuery(this).next('#prop_val').replaceWith(get_input_type(valid));"
        properties_js += "\n\t\tjQuery(this).next('input').val(valid);"
        properties_js += "\n\t});"
        properties_js += "});"
        
        js += values_js
        js += properties_js

        memcache.add(key, js)
        add_user_to_cache_list("_properties-", world, self.page_user.user.user_id())

        return js

class ReloadMenu(CreatePage):
    def GET(self):
        raise web.notfound()
    def POST(self):
        d = web.input()
        if d.reload:
            w = world_exists(d.world)
            a = w.get_access_string(self.page_user)
            self.set_menu(w, a)
        return web.seeother(d.refer)

class WorldCreate(CreatePage):

    formargs = {'method':'post'}

    def GET(self):

        f = self.world_form()
        form = CombinedForm([f], **self.formargs)
        f.fill(**{'void_text':get_default_void()})

        section = render().section_world(form)

        return render().admin(self.def_world, section, self.empty_menu, "Palimpsest: Create an experience")

    def POST(self):
        f = self.world_form()
        form = CombinedForm([f], **self.formargs)
        if not f.validates():
            section = render().section_world(form)
            return render().admin(self.def_world, section, self.empty_menu, "Palimpsest: Create an experience")
        else:
            slug = make_world_slug(f.d.title)
            new_world = World(id=slug,
                              title=f.d.title, 
                              blurb=f.d.blurb, 
                              creator=self.page_user.key, 
                              publish=f.d.publish, 
                              void_text=f.d.void_text,
                              is_open=f.d.is_open
                        )
            new_world.put()
            #f.fill(**{'title':new_world.title,'blurb':new_world.blurb,'publish':new_world.publish,'is_open':new_world.is_open,'void_text':new_world.void_text})
            return web.seeother('/%s/edit' % new_world.key.id())

class PropertyCreate(CreatePage):

    formargs = {'method':'post'}

    def GET(self, world):
        cur_world = world_exists(world)
        self.redirect_if_not_create(cur_world)

        access = cur_world.get_access_string(self.page_user)
        world_menu = self.get_or_put_menu(cur_world, access)
        world_menu['properties'][0][2] = "active"

        logging.warning(access)

        f = self.properties_form()
        form = CombinedForm([f], **self.formargs)
        section = render().section_property(form)
        return render().admin(cur_world, section, world_menu, title="Add a new property to %s on Palimpsest" % cur_world.title, pre=["/js/showhide_form_fields.js"])

    def POST(self, world):
        cur_world = world_exists(world)
        self.redirect_if_not_create(cur_world)

        f = self.properties_form()
        form = CombinedForm([f], **self.formargs)

        if not f.validates():
            access = cur_world.get_access_string(self.page_user)
            world_menu = self.get_or_put_menu(cur_world, access)
            section = render().section_properties(form)
            return render().admin(cur_world, section, world_menu, title="Add a new property to %s on Palimpsest" % cur_world.title, pre=["/js/showhide_form_fields.js"])
        else:

            access = cur_world.get_access_string(self.page_user)

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

            if cur_world.is_mod(self.page_user):
                visible = True
                """ Flush menus and available properties for everyone so they get reset"""
                # TODO: Fix this
                memcache.delete("%s-admin" % cur_world.key.id())
                memcache.delete("%s-closed" % cur_world.key.id())
            else:
                visible = False

            new_property = Property(name=f.d.name,
                                    sorter=f.d.sorter,
                                    info=f.d.info,
                                    discrete=discrete,
                                    valid_values=valid_values,
                                    world=cur_world.key,
                                    added_by=self.page_user.key,
                                    visible=visible,
                                    rejected=False
                )
            new_property.put()

            self.set_menu(cur_world, access)
            memcache.delete("_properties-%s-global" % cur_world.key.id())

            return web.seeother('/%s/property/%s' % (cur_world.key.id(), new_property.key.id()))

class TextCreate(CreatePage):

    formargs = {'method':'POST'}

    def GET(self, world):
        cur_world = world_exists(world)
        self.redirect_if_not_create(cur_world)

        access = cur_world.get_access_string(self.page_user)
        world_menu = self.get_or_put_menu(cur_world, access)
        world_menu['texts'][0][2] = "active"

        logging.warning(access)

        form = self.text_form()
        return self.reset_text_page(cur_world, form, access, world_menu)

    def POST(self, world):
        cur_world = world_exists(world)
        self.redirect_if_not_create(cur_world)

        i = web.input(long=[], lat=[], prop_name=[], prop_val=[])
        coord = []
        new = []
        access = cur_world.get_access_string(self.page_user)
        form = self.text_form()

        if not form.validates():
            world_menu = self.get_or_put_menu(cur_world, access)
            return self.reset_text_page(cur_world, form, access, world_menu)
        else:

            if cur_world.is_mod(self.page_user):
                visible = True
                """ Flush menus for everyone so they get reset"""
                mrpc = memcache.create_rpc()
                m = flush_caches("", cur_world, mrpc)
                try:
                    m.get_result()
                except AssertionError: # There were no caches to flush - is this even the problem?
                    pass
            else:
                visible = False

            new_text = Room(world = cur_world.key,
                            name=form.d.name,
                            short_desc=form.d.short_desc,
                            long_desc=form.d.long_desc,
                            added_by=self.page_user.key,
                            latitudes=i.lat,
                            longitudes=i.long,
                            visible=visible,
                            rejected=False
                        )
            new_text.put()

            for index, name in enumerate(i.prop_name):
                p = Property.get_by_id(int(name))
                new.append(PropertyValue())
                new[index].value = i.prop_val[index]
                new[index].of_property = p.key
                new[index].room = new_text.key
                new[index].added_by = self.page_user.key
                new[index].visible = visible

            valftrs = ndb.put_multi_async(new)
            self.set_menu(cur_world, access)

            for ftr in valftrs:
                ftr.get_result()

            return web.seeother('/%s/text/%s' % (cur_world.key.id(), new_text.key.id()))


class ModeratorCreate(CreatePage):

    formargs = {'method':'POST','class':'inline'}
    epost = ["/js/validateemail.js"]

    def GET(self, world):
        cur_world = world_exists(world)
        self.redirect_if_not_admin(cur_world)

        mods_ftr = cur_world.get_moderators()

        access = cur_world.get_access_string(self.page_user)
        world_menu = self.get_or_put_menu(cur_world, access)
        world_menu['contributors'][0][2] = "active"

        f = self.moderator_form()
        form = CombinedForm([f], **self.formargs)
        cur_mods = mods_ftr.get_result()
        section = render().section_moderators(form, cur_mods)
        return render().admin(cur_world, section, world_menu, title="Moderators of %s on Palimpsest" % cur_world.title, post=self.epost)

    def POST(self, world):
        cur_world = world_exists(world)
        self.redirect_if_not_admin(cur_world)

        param = web.input()
        if hasattr(param, 'mod'):
            # Access rights form submitted
            edit_mod = ndb.Key("Moderator", int(param.userid)).get()
            if int(param.action) == 1:
                edit_mod.admin = True
            if int(param.action) == 2:
                edit_mod.admin = False
            if int(param.action) == 0:
                try:
                    edit_mod.user_pending.delete()
                except AttributeError:
                    # (no pending user)
                    pass
                edit_mod.key.delete()
            else:
                edit_mod.put()
            raise web.seeother("/%s/mods" % world)

        f = self.moderator_form()
        form = CombinedForm([f], **self.formargs)
        if not f.validates():
            mods_ftr = cur_world.get_moderators()

            access = cur_world.get_access_string(self.page_user)
            world_menu = self.get_or_put_menu(cur_world, access)
            world_menu['contributors'][0][2] = "active"

            f = self.moderator_form()
            form = CombinedForm([f], **self.formargs)
            cur_mods = mods_ftr.get_result()
            section = render().section_moderators(form, cur_mods)
            return render().admin(cur_world, section, world_menu, title="Moderators of %s on Palimpsest" % cur_world.title, post=self.epost)
        
        else:

            try_user = users.User(f.d.add_contrib)
            user_result = get_google_user_key(try_user).get_result()
            if len(user_result) > 0 and user_result[0] is not None:
                user = user_exists_bykey(user_result[0])
                m = Moderator(world=cur_world.key, user=user.key, admin=False)
                msg = """You've been added as a contributor to %s.
This means you can add texts and properties which are published straight away.  You can also approve or reject publicly submitted texts and properties.
Try it out: %s/%s/texts""" % (cur_world.title, web.ctx.host, cur_world.key.id())
            else:
                email = str(f.d.add_contrib).lower()
                # TODO: Check UserPending doesn't already exist with that email
                u_p = UserPending(email=email)
                u_p.put()
                m = Moderator(world=cur_world.key, user_pending=u_p.key, admin=False)
                msg = """You've been added as a contributor to %s.
This means you can add texts which bypass the moderation stage, and are published straight away.
Try it out: %s/%s/auth/%s""" % (cur_world.title, web.ctx.host, cur_world.key.id(), str(u_p.key.id()))
            
            m.put()
            
            to_addr = f.d.add_contrib
            if not mail.is_email_valid(to_addr):
                return "Could not send: invalid email. Press back and try again."

            message = mail.EmailMessage()
            message.sender = get_current_user().user.email()
            message.to = to_addr
            message.subject = "Palimpsest: You have been added as a moderator of %s!" % cur_world.title
            message.body = msg

            message.send()

        return web.seeother('/%s/mods' % cur_world.key.id())