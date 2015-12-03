
import webapp2
import os

from library.urls import buildUrl

from webapp2_extras import mako
from webapp2_extras import sessions

from google.appengine.api import memcache

from mako.template import Template
from mako.lookup import TemplateLookup

from datetime import datetime

class BaseController(webapp2.RequestHandler):

	@webapp2.cached_property
	def mako(self):
		# Returns a Mako renderer cached in the app registry.
		return mako.get_mako(app=self.app)

	def cacheGet( self, key ):
		return memcache.get( key )

	def cacheSet( self, key, data, expiration = 3600 ):
		return memcache.set( key, data, expiration )

	def cacheDelete( self, key ):
		return memcache.DELETE_SUCCESSFUL == memcache.delete( key )

	def __init__(self, request=None, response=None):
		webapp2.RequestHandler.__init__(self, request, response)

		self.titleSuffix = '. SNIPCAT'
		self.breadcrumb = [ { 'name': 'Code snippets', 'link': buildUrl('index') } ]
		self.pageConf = {
			'title': 'Code snippets and complete examples' + self.titleSuffix,
			'metaKeywords': '',
			'metaDescription': '',
		}
		self.javaScripts = [
			'https://ajax.googleapis.com/ajax/libs/jquery/1.6.4/jquery.min.js',
			'/scripts/common.js'
		]
		self.styleSheets = [ '/styles/default.css' ]

	def getContentType( self ): return 'text/html; charset=utf-8'

	def getCacheKey( self, key ): return None

	def get( self, **args ):
		self.response.headers['Content-Type'] = self.getContentType()

		cacheKey = self.getCacheKey()
		if cacheKey is not None:
			content = self.cacheGet( cacheKey )

		if content is None:
			content = self.requestGet( **args )
		
		if cacheKey is not None:
			self.cacheSet( cacheKey, content )

		self.response.out.write( content )

	def dispatch(self):
		self.session_store = sessions.get_store(request=self.request)

		try:
			webapp2.RequestHandler.dispatch(self)
		finally:
			self.session_store.save_sessions(self.response)

	@webapp2.cached_property
	def session(self):
		try:
			return self.session_store.get_session(backend='memcache')
		except:
			return {}

	def renderResponse(self, templateName, **templateValues):
		output = self.renderTemplate( templateName, **templateValues )
		self.response.write( output )

	def renderTemplate( self, name, **values ):
		sessionDeveloper = self.session.get('developer')

		defaultValues = {
			'appDomain': self.app.config.get('appDomain'),
			'buildUrl': buildUrl,
			'javaScripts': self.javaScripts,
			'styleSheets': self.styleSheets,
			'pageConf': self.pageConf,
			'sessionDeveloper': sessionDeveloper,
			'currentDatetime': datetime.now()
		}
		defaultValues.update( values )

		path = os.path.join( os.path.dirname( '..' ), 'views', name )

		templateLookup = TemplateLookup( directories = [ os.path.dirname( '..' ) ] )
		templ = Template( filename = path, lookup = templateLookup, input_encoding = 'utf-8', output_encoding = 'utf-8', encoding_errors = 'ignore', disable_unicode = False )

		try:
			output = templ.render( **defaultValues )
		except:
			from mako import exceptions
			output = exceptions.html_error_template().render()

		return output

