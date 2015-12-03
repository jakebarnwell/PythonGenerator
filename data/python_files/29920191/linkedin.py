import random
import time
import hmac
import hashlib
import urllib
import urlparse
import httplib

from operator import itemgetter
import constants

LINKEDIN_BASE_URL = 'https://api.linkedin.com'
LINKEDIN_INSECURE_URL = 'http://api.linkedin.com'
LINKEDIN_OAUTH_REQUEST = '/uas/oauth/requestToken'
LINKEDIN_OAUTH_AUTHORIZE = '/uas/oauth/authorize'
LINKEDIN_OAUTH_AUTHENTICATE = '/uas/oauth/authenticate'
LINKEDIN_OAUTH_ACCESS_TOKEN = '/uas/oauth/accessToken'

generate_sorted_params = lambda k: sorted(k.iteritems(), key=itemgetter(0))
generate_timestamp = lambda: str(int(time.time()))
generate_nonce = lambda: hashlib.sha1(str(random.random())).hexdigest()

PARAMS = lambda: {
    'oauth_nonce': generate_nonce(),
    'oauth_timestamp': generate_timestamp(),
    'oauth_consumer_key': constants.LINKEDIN_KEY,
    'oauth_signature_method': 'HMAC-SHA1',
    'oauth_version': '1.0'
}

encode_tuple = lambda k, v: urllib.quote(k) + '%3D' + urllib.quote(urllib.quote(v, safe=''))

def generate_base_string(method, url, params):
    sorted_params = generate_sorted_params(params)
    encoded_params = '%26'.join([encode_tuple(k, v) for k, v in sorted_params])
    return '&'.join([method, urllib.quote_plus(url, safe="~"), encoded_params])

def generate_signature(base_string, oauth_token_secret=None):
    signing_key = constants.LINKEDIN_SECRET + '&'
    if oauth_token_secret:
        signing_key += oauth_token_secret

    hash = hmac.new(signing_key, base_string, hashlib.sha1)
    return hash.digest().encode('base-64')[:-1]

class LinkedIn():
    def __init__(self, token=None, secret=None, ssl=True, commas=False):
        self.token = token
        self.secret = secret
        self.ssl = ssl
        self.commas = commas

    def get(self, resource, params=None):
        return self.oauth_response('GET', resource, params)

    def post(self, resource, params=None):
        return self.oauth_response('POST', resource, params)

    def generate_access_token(self, oauth_verifier):
        params = {'oauth_verifier': oauth_verifier}
        response = self.post(LINKEDIN_OAUTH_ACCESS_TOKEN, params)
        return dict(urlparse.parse_qsl(response.read()))

    def generate_authorization_url(self, callback=None):
        if callback:
            params = {'oauth_callback': callback}
        else:
            params = {'oauth_callback': constants.LINKEDIN_REDIRECT_URL}

        response = self.post(LINKEDIN_OAUTH_REQUEST, params)

        data = dict(urlparse.parse_qsl(response.read()))
        return data

    def oauth_response(self, method, resource, params=None, oauth_params=None):
        if self.ssl:
            conn = httplib.HTTPSConnection('api.linkedin.com')
            url = LINKEDIN_BASE_URL
        else:
            conn = httplib.HTTPConnection('api.linkedin.com')
            url = LINKEDIN_INSECURE_URL
        url += resource

        signing_params = PARAMS()

        if params:
            signing_params.update(params)

        if self.token:
            signing_params['oauth_token'] = self.token

        base_string = generate_base_string(method, url, signing_params)

        header_params = {}
        query_params = {}
        for key, value in signing_params.iteritems():
            query_params[key] = urllib.quote(value)
            if key.startswith("oauth_"):
                header_params[key] = urllib.quote(value, safe='')

        signature = generate_signature(base_string, self.secret)
        header_params['oauth_signature'] = urllib.quote_plus(signature, safe='')
        query_params['oauth_signature'] = urllib.quote_plus(signature, safe='')

        if self.commas:
            auth_string = 'OAuth %s' % ', '.join(['%s="%s"' % (k, v)
                for k, v in header_params.iteritems()])
        else:
            auth_string = 'OAuth %s' % ' '.join(['%s="%s"' % (k, v)
                for k, v in header_params.iteritems()])

        encoded_params = "&".join("%s=%s" % (k, v) for k, v in query_params.iteritems())

        if method == 'POST':
            conn.request(method, resource, encoded_params, {'Authorization': auth_string})
        else:
            conn.request(method, resource + "?" + encoded_params, headers={'Authorization': auth_string})

        response = conn.getresponse()
        return response


