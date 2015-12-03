import oauth2 as oauth
import sher.settings as settings
import cgi
import urlparse
import urllib
import gdata.youtube
import gdata.youtube.service
import twitter


class TwitterService(object):
    def __init__(self, consumer_key, consumer_secret):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.consumer = oauth.Consumer(self.consumer_key, self.consumer_secret)
        self.client = oauth.Client(self.consumer)
        self.access_token_url = "https://api.twitter.com/oauth/access_token"
        self.request_token_url = "https://api.twitter.com/oauth/request_token"
        self.authorize_url = "https://api.twitter.com/oauth/authorize"

    def get_request_token(self):
        request_token_url = self.request_token_url
        resp, content = self.client.request(request_token_url, "POST")

        if resp['status'] != '200':
            raise Exception("Invalid Response from Twitter")

        request_token = dict(cgi.parse_qsl(content))
        self.request_token = request_token['oauth_token']
        self.request_token_secret = request_token['oauth_token_secret']

        return self.request_token

    def get_access_token(self, oauth_verifier):
        access_token_url = self.access_token_url

        token = oauth.Token(self.request_token, self.request_token_secret)
        token.set_verifier(oauth_verifier)

        client = oauth.Client(self.consumer, token)

        resp, content = client.request(access_token_url, "POST")

        if resp['status'] != '200':
            raise Exception("Invalid Response from Twitter")

        access_token = dict(cgi.parse_qsl(content))
        self.access_token = access_token['oauth_token']
        self.access_token_secret = access_token['oauth_token_secret']

        return access_token

    def get_oauth_url(self, request_token):
        return "%s?oauth_token=%s" % (self.authorize_url, request_token)

    def authenticated(self, account):
        """Return an authenticated twitter API instance (python-twitter)"""

        return twitter.Api(consumer_key=self.consumer_key,
                            consumer_secret=self.consumer_secret,
                            access_token_key=account.oauth_token,
                            access_token_secret=account.oauth_secret)

twitter_service = TwitterService(settings.TWITTER_CONSUMER_KEY, settings.TWITTER_CONSUMER_SECRET)


class YouTubeService(object):
    def __init__(self, developer_key, client_id):
        self.developer_key = developer_key
        self.client_id = client_id
        self.yt_service = gdata.youtube.service.YouTubeService()

    def get_authsub_url(self, callback):
        next = callback
        scope = "http://gdata.youtube.com"
        secure = False
        session = True

        return self.yt_service.GenerateAuthSubURL(next, scope, secure, session)

    def upgrade_to_session(self, token):
        """
        Takes an authsub token and upgrades to session token then returns that token for storing.
        """
        self.yt_service.SetAuthSubToken(token)
        self.yt_service.UpgradeToSessionToken()

        return self.yt_service.GetAuthSubToken()

    def authenticated(self, account):
        self.yt_service.SetAuthSubToken(account.authsub_token)
        self.yt_service.developer_key = self.developer_key
        self.yt_service.client_id = self.client_id
        return self.yt_service

youtube_service = YouTubeService(settings.YOUTUBE_DEVELOPER_KEY, settings.YOUTUBE_CLIENT_ID)


class FacebookService(object):
    def __init__(self, app_id, app_key, app_secret):
        self.app_id = app_id
        self.app_key = app_key
        self.app_secret = app_secret

    def get_oauth_url(self):
        """Offline access gets a long-lasting token."""

        return "https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s&scope=read_stream,publish_stream,offline_access"

    def get_access_token_url(self, callback, code):
        self.access_token_url = "https://graph.facebook.com/oauth/access_token?client_id=%s&redirect_uri=%s&client_secret=%s&code=%s" % (self.app_id, callback, self.app_secret, code)
        return self.access_token_url

    def authenticated(self, account):
        from apis import facebook
        graph = facebook.GraphAPI(account.oauth_token)
        return graph

facebook_service = FacebookService(settings.FACEBOOK_APP_ID, settings.FACEBOOK_APP_KEY, settings.FACEBOOK_APP_SECRET)


class FlickrService(object):
    def __init__(self, api_key, secret):
        self.api_key = api_key
        self.secret = secret
        self.auth_url = "http://flickr.com/services/auth/?"
        self.rest_url = "http://flickr.com/services/rest/?"

    def gen_sig(self, base_url, **kwargs):
        from md5 import md5
        params = {}
        for kwarg in kwargs:
            params.update({kwarg: kwargs[kwarg]})

        pkeys = params.keys()
        pkeys.sort()

        sigstring = self.secret + ""
        for k in pkeys:
            sigstring += k + str(params[k])

        params['api_sig'] = md5(sigstring).hexdigest()

        return base_url + urllib.urlencode(params)

    def get_oauth_url(self):
        """Generates oauth url with 'delete' permission which provides both read and write permissions."""
        url = self.gen_sig(self.auth_url, api_key=self.api_key, perms="delete")
        return url

    def get_auth_token(self, token):
        """Calls flickrs getToken to obtain a persistent auth token."""
        url = self.gen_sig(self.rest_url, api_key=self.api_key, method="flickr.auth.getToken", frob=token)
        return url

    def authenticated(self, account, format="etree"):
        import flickrapi
        return flickrapi.FlickrAPI(settings.FLICKR_KEY, secret=settings.FLICKR_SECRET, token=account.oauth_token, format=format)


flickr_service = FlickrService(settings.FLICKR_KEY, settings.FLICKR_SECRET)
