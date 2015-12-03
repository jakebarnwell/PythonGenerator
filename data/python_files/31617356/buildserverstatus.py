import re
import feedparser
from trac.core import *
from trac.util.html import html
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
import urllib
import socket

class BuildServerStatus(Component):
    implements(INavigationContributor, IRequestHandler, ITemplateProvider)

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'buildserver'
    def get_navigation_items(self, req):
        yield ('mainnav', 'buildserver',
            html.A('Build Server', href= req.href.buildserver()))

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info == "/buildserver"

    def process_request(self, req):
	socket.setdefaulttimeout(10)
        req.hdf['title'] = 'Build Server'
	serverurl = self.config.get('buildserverstatus', 'server_url')
	rssurl = self.config.get('buildserverstatus', 'rss_url')
	if serverurl == '':
		raise Exception('server_url must be defined')
	elif rssurl == '':
		raise Exception('rss_url must be defined')
	else:
	        req.hdf['serverurl'] = serverurl
		req.hdf['rssurl'] = rssurl
		try:
			statuscode = urllib.urlopen(serverurl).info()['Status']
		except IOError:
			statuscode = "110 TIMED OUT"
		req.hdf['statuscode'] = statuscode
		online = statuscode == "200 OK"
		if online :
			req.hdf['serverstatus'] =  "ONLINE"
			d = feedparser.parse(rssurl)
			if d.entries:
				msg = d.entries[0].title
				parts = msg.split()
				req.hdf['project'] = parts[0]
				req.hdf['build'] = parts[2]
				req.hdf['laststatus'] = parts[3].upper()
		else:
			req.hdf['serverstatus'] =  "OFFLINE"
			req.hdf['laststatus'] = "UNKNOWN"

	return 'buildserver.cs', None


    # ITemplateProvider methods
    def get_templates_dirs(self):
        """Return a list of directories containing the provided ClearSilver
        templates.
        """

        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        return []
