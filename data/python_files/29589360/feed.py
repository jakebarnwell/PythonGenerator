
import webapp2
from controllers.base import BaseController
from library.models.snips import findSnipsByDeveloperId
from library.models.developers import registerDeveloper, listDevelopers, findDeveloperByUsername, findUrlsByDeveloperId 
from library.urls import buildUrl

class DeveloperFeedController( BaseController ):

	def get( self, username ):
		developer = findDeveloperByUsername( username )
		if not developer:
			self.response.set_status( 404 )
			self.renderResponse( 'errors/404.html' )
			return
		snippets = findSnipsByDeveloperId( developer['developer_id'] )

		from pyatom import AtomFeed
		import datetime

		feed = AtomFeed(
			title = '%s\'s code snippets' % developer['username'],
			subtitle = '(most recent code snippets from this developer)',
			feed_url = buildUrl( 'dev-feed', username = developer['username'], _full = True ),
			url = buildUrl( 'dev-username', username = developer['username'], _full = True ),
			author = developer['username']
		)

		for snip in snippets:
			feed.add(
				title = snip['title'],
				content = snip['description'],
				content_type = 'html',
				author = developer['username'],
				url = buildUrl( 'snip-index', lang = snip['lang'], cat = snip['cat'], title = snip['sanitized_title'] ),
				updated = snip['creation_date'] # datetime.datetime.utcnow()
			)

		self.response.headers['Content-type'] = 'text/xml;charset=utf-8'
		self.response.write( feed.to_string() )

