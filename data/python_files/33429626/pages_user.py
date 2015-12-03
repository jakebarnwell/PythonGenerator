import web
import copy

from google.appengine.ext import ndb
from google.appengine.api import users

from palimpsest.models import get_everything_by, Feedback, SavePath, get_saves_by, world_exists
from palimpsest.logins import get_current_user, get_logout_url

from palimpsest.pages import Page, render
from palimpsest.utils.form import Form, CombinedForm, Submit, display_input_warning, display_form_warning

class Account(Page):
    require_login = True

    u_form = Form(
          web.form.Checkbox('contact', value=True, description='May we contact you?')
          ,web.form.Textbox('realname', description='Your real name')
          ,web.form.Textbox('penname', description='Penname / pseudonym / byline')
          ,Submit('save_you', value='Save')
          , pre_input=display_input_warning
          , pre_form=display_form_warning
      )

    del_form = Form(
           web.form.Textarea('whydel', description='Would you mind telling us why you are deleting your account?')
          ,Submit('del_you', value='Delete account, creations and journeys')
          , pre_input=display_input_warning
          , pre_form=display_form_warning
      )
    formargs = {'method':'POST'}
    delformargs = {'method':'POST', 'action':'/you/delete'}

    delform = CombinedForm([del_form], **delformargs)

    def GET(self):
        user = self.page_user
        f = self.u_form()
        form = CombinedForm([f], **self.formargs)
        f.fill(**{'penname':user.penname, 'realname':user.name, 'contact':user.contact})

        return render().user(form, self.delform)

    def POST(self):
        f = self.u_form()
        form = CombinedForm([f], **self.formargs)
        if not f.validates():
            return render().user(form, self.delform)
        else:
            user_ftr = self.page_user.set_info(**{'penname':f.d.penname, 'realname':f.d.realname, 'contact':f.d.contact})
            page = render().user(form, self.delform, "Saved.")
            user_ftr.get_result()
            return page

class AccountSaves(Page):
    require_login = True

    def GET(self):
        user_saves = get_saves_by(self.page_user)
        return render().saves(user_saves)

class AccountSave(Page):

    def can_access_save(self, save):
        if save is not None:
            if save.publish:
                return
            if self.page_user:
                if save.user == self.page_user.key:
                    return
        raise web.notfound()

    def can_modify_save(self, save):
        if save is not None:
            if self.page_user:
                if save.user == self.page_user.key:
                    return
        raise web.notfound()

    def GET(self, save):
        save = SavePath.get_by_id(int(save))
        self.can_access_save(save)
        texts = []
        ftrs = []
        prev = None
        for text in save.texts:
            ftrs.append(text.get_async())
        for ftr in ftrs:
            t = ftr.get_result()
            if prev is None or t.key != prev.key:
                texts.append(t)
            prev = t

        if self.page_user:
            access = save.user == self.page_user.key
        else:
            access = False

        return render().save(save, texts, access)

    def POST(self, save):
        save = SavePath.get_by_id(int(save))
        self.can_modify_save(save)

        i = web.input()
        try:
            p = i.pub
            save.publish = True
        except AttributeError:
            save.publish = False
        save.put()

        web.seeother("/journey/%s" % save.key.id())

class AccountDelete(Page):
    require_login = True
    def GET(self):
        return web.seeother('/you')

    def POST(self):
        f = Account.del_form()
        if not f.validates():
            return web.seeother('/you')
        else:
            self.page_user.delete_self(f.d.whydel)
            web.seeother(get_logout_url())

class AccountWorlds(Page):
    require_login = True

    menu = {
           "yours":[["New experience", "/yours/new", "", "icon-plus-sign"]]
          ,"unmod":[["Closed experiences", "/yours/contributions", "", "icon-chevron-right"]]
          ,"contr":[["Open experiences", "/yours/contributions#open", "", "icon-chevron-right"]]
        }

    def GET(self):

        everything = self.page_user.get_works().get_result()
        
        bys = everything[0]
        mods = everything[1]
        opens = everything[2]

        yours_menu = copy.deepcopy(self.menu)

        for by in bys:
            yours_menu['yours'].append((by.title, "/%s/edit" % by.key.id(), ""))

        for mod in mods:
            w = mod.world.get()
            yours_menu['unmod'].append((w.title, "/%s/texts" % w.key.id(), ""))
        if len(mods) < 1:
            yours_menu['unmod'][0][2] = "disabled"

        for o in opens:
            yours_menu['contr'].append((o.title, "/%s/texts" % o.key.id(), ""))
        if len(opens) < 1:
            yours_menu['contr'][0][2] = "disabled"

        return render().yours(yours_menu, "Palimpsest: Your experiences")

class ModeratorAuth(Page):
    require_login = True

    def GET(self, world, auth_key):
        cur_world = world_exists(world)
        try:
            user_pending = ndb.Key(urlsafe=auth_key).get()
            pending_mods = user_pending.get_pending_mods().get_result()

            for m in pending_mods:
                m.user_pending = None
                m.user = get_current_user().key
                m.put()
            user_pending.key.delete()

        except:
            return web.seeother("/")

        return web.seeother("/%s/texts" % world)
