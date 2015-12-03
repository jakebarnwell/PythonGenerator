import logging
import httplib
import urllib2
from django.contrib.auth.models import User
from django.conf import settings
import reviewboard

class RBHTTPAuthBackend(reviewboard.accounts.backends.AuthBackend):
    name = 'RBHTTPAuthBackend'
    the_url = "http://localhost"
    def authenticate(self, username, password):

        username = username.strip()

        try:
            passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None, self.the_url, username, password)
            authhandler = urllib2.HTTPBasicAuthHandler(passman)
            opener = urllib2.build_opener(authhandler)
            urllib2.install_opener(opener)
            pagehandle = urllib2.urlopen(self.the_url)
            return self.get_or_create_user(username, password)
        except Exception, e:
            return None

    def get_or_create_user(self, username, passwd=None):
        import nis

        username = username.strip()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                first_name = username
                last_name = None

                email = u'%s@%s' % (username, settings.EMAIL_DOMAIN)

                user = User(username=username,
                            password='',
                            first_name=first_name,
                            last_name=last_name or '',
                            email=email)
                user.is_staff = True
                user.is_superuser = False
                user.set_unusable_password()
                user.save()
            except nis.error:
                pass
        return user
