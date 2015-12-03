import sys

import httplib
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from reviewboard.accounts.backends import AuthBackend

from auth_api import auth, get_user_info_by_username
from auth_api import db_auth_account_field_name, db_auth_email_field_name

from forms import DatabaseAuthBackendSettingsForm


class DatabaseAuthBackend(AuthBackend):
    name = _("Database Authentication")

    settings_form = DatabaseAuthBackendSettingsForm
    supports_registration = False
    supports_change_name = False
    supports_change_email = False
    supports_change_password = False

    def authenticate(self, username = None, password = None):
        resp = auth(username, password)

        if resp == httplib.OK:
            return self.get_or_create_user(username)

    def get_or_create_user(self, username):
        username = username.strip()

        try:
            user = User.objects.get(username = username)
        except User.DoesNotExist:
            data = get_user_info_by_username(username)
            username = data[db_auth_account_field_name]

            # set it for email notification in ReviewBoard
            email = data[db_auth_email_field_name]

            user = User.objects.create_user(username = username, email = email)
            user.is_activate = True
            user.is_staff = False
            user.is_superuser = False
            user.set_unusable_password()

            user.save()

        return user

