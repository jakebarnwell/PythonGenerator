import json
import urllib
import urllib2
import constants
import logging

from ecl_tools.utils import Objectifier

logger = logging.getLogger(__name__)

class GoogleCall(object):
    def __init__(self, path_components=[], token=None, name=None):
        self.token = token
        self.path_components = path_components
        version = getattr(constants, "GOOGLE_%s_VERSION" % name.upper(), None)
        data = {'name': name,
                'version': version }
        if version:
            self.base = constants.GOOGLE_API_BASE % data
        elif name == 'geocode':
            self.base = "https://maps.googleapis.com/maps/geo"
        elif name == 'places':
            self.base = "https://maps.googleapis.com/maps/api/place/"
        elif name == 'maps':
            self.base = "https://maps.googleapis.com/maps/api/"
        elif name == 'shopping':
            self.base = "https://www.googleapis.com/shopping/search/v1/"
        elif name == 'analytics':
            self.base = "https://www.googleapis.com/analytics/v3/data/ga"
        elif name == 'prediction':
            self.base = "https://www.googleapis.com/prediction/{}/".format( \
                    constants.GOOGLE_PREDICTION_VERSION)

        self.name = name

    def __getattr__(self, k):
        self.path_components.append(urllib.quote(k))
        return GoogleCall(self.path_components, token=self.token,
                name=self.name)

    def __getitem__(self, k):
        self.path_components.append(urllib.quote(k))
        return GoogleCall(self.path_components, token=self.token,
                name=self.name)

    def __call__(self, method='GET', data=None, **kwargs):
        path = "/".join(self.path_components)

        headers = { 'Content-Type': "application/json" }

        if self.token:
            headers['Authorization'] = "OAuth " + self.token
            # headers['Host'] = 'accounts.google.com'
            # kwargs['oauth_token'] = self.token
        else:
            ignore_key = kwargs.get('ignore_key', False)
            if not ignore_key:
                kwargs['key'] = constants.GOOGLE_API_KEY

        url = self.base + path

        if len(kwargs) > 0:
            url += "?" + urllib.urlencode(kwargs)

        logger.debug(url)
        if data:
            encoded_data = json.dumps(data)
            request = urllib2.Request(url, encoded_data, headers=headers)
        else:
            request = urllib2.Request(url, headers=headers)
        request.get_method = lambda: method

        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            return e

        return Objectifier(json.load(response))


class Google(object):
    def __init__(self, token=None, refresh_token=None,
            redirect_uri=constants.GOOGLE_OAUTH_REDIRECT):
        self.token = token
        self.refresh_token = refresh_token
        self.redirect_uri = redirect_uri
        self.key = constants.GOOGLE_OAUTH_KEY
        self.secret = constants.GOOGLE_OAUTH_SECRET
        self.readonly = False

    @property
    def geo(self):
        """ https://maps.googleapis.com/maps/geo?output=json&q=34.02062,-118.39713&sensor=false&key=XXX """
        self.name = "geocode"
        return self

    @property
    def analytics(self):
        self.name = "analytics"
        return self

    @property
    def prediction(self):
        self.name = "prediction"
        return self

    @property
    def moderator(self):
        self.name = "moderator"
        return self

    @property
    def books(self):
        self.name = "books"
        return self

    @property
    def tasks(self, readonly=False):
        self.name = "tasks"
        self.readonly = readonly
        return self

    @property
    def latitude(self):
        self.name = "latitude"
        return self

    @property
    def maps(self):
        """ https://maps.googleapis.com/maps/api/geocode/json?latlng=34.02062,-118.39713&sensor=false """
        self.name = "maps"
        return self

    @property
    def site_verification(self):
        self.name = "siteVerification"
        return self

    @property
    def url_shortener(self):
        self.name = "urlshortener"
        return self

    @property
    def custom_search(self):
        """ https://code.google.com/apis/customsearch/v1/reference.html """
        self.name = "customsearch"
        return self

    @property
    def shopping(self):
        """ http://code.google.com/apis/shopping/search/v1/reference-overview.html """
        self.name = "shopping"
        return self

    @property
    def buzz(self):
        """ http://code.google.com/apis/buzz/v1/using_rest.html
        TODO: Implement readonly and photo scopes """
        self.name = "buzz"
        return self

    def __getitem__(self, k):
        k = urllib.quote(k)
        return GoogleCall([k], token=self.token, name=self.name)

    def __getattr__(self, k):
        k = urllib.quote(k)
        return GoogleCall([k], token=self.token, name=self.name)

    def __call__(self, method='GET', data=None, **kwargs):
        return GoogleCall([], token=self.token, name=self.name)(method, data, **kwargs)

    def generate_oauth_dialog_url(self, state=None):
        scope = "https://www.googleapis.com/auth/" + self.name
        if self.readonly:
            scope += ".readonly"

        params = {
            'client_id': self.key,
            'redirect_uri': self.redirect_uri,
            'scope': scope,
            'response_type': 'code'
        }

        if state:
            params['state'] = state

        encoded_params = urllib.urlencode(params)
        return constants.GOOGLE_OAUTH_ENDPOINT + "?" + encoded_params

    def generate_access_token(self, code=None, refresh_token=None):
        params = {
            'client_id': self.key,
            'client_secret': self.secret,
            'redirect_uri': self.redirect_uri
        }

        if code:
            params['code'] = code
            params['grant_type'] = 'authorization_code'
        elif refresh_token:
            params['refresh_token'] = refresh_token
            params['grant_type'] = 'refresh_token'

        encoded_params = urllib.urlencode(params)
        request = urllib2.Request(constants.GOOGLE_OAUTH_TOKEN_ENDPOINT, encoded_params)
        response = urllib2.urlopen(request)
        data = json.load(response)
        self.token = data['access_token']
        self.refresh_token = data['refresh_token']
        return data


# import webbrowser
# print webbrowser.open(google.url_shortener.generate_oauth_dialog_url())

