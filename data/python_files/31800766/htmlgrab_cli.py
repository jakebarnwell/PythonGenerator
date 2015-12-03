import os
import settings
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.core.management import setup_environ
from optparse import OptionParser
from urlparse import urlparse
setup_environ(settings)

from InetRequest import ProxyServer, Link
from htmlgrab.models import HTMLRequest

usage = "usage: %prog URL [options]"
parser = OptionParser(usage)
url=''
p = None

parser.set_defaults(https=True)

parser.add_option("-p","--proxy",action="store",type="string",dest="proxy",help="If using a proxy, the proxy_name field of the proxy in the database")
#parser.add_option("-H","--https",action="store_false",dest="https",help="If using a proxy, disable HTTPS")

(options, args) = parser.parse_args()

#Make sure they actually entered a URL
if len(args) == 0:
    print "You must enter a URL to scan"
else:
    cli_url = urlparse(args[0])
    l = Link()
    l.title=cli_url.netloc
    l.link=cli_url.geturl()
    if options.proxy:
        #Set up the proxy server if specified
        pserver = ProxyServer.objects.filter(proxy_name=options.proxy)
        if len(pserver) > 0:
            p = pserver[0]
        else:
            print "Proxy not found in database"
            exit()
#        if options.https == False:
#            p.https = False
#            print "In CLI, https disabled"
#        else:
#            p.https = True
#            print "In CLI, https enabled"
    else:
        p=None
    try:
        v = URLValidator(args[0])
        print "URL %s is valid" % args[0]
        links = Link.objects.filter(link=cli_url.geturl())
        if len(links) == 0:
            l.save()
        else:
            l = links[0]
        htmr = HTMLRequest(proxy_info=p)
        htmr.set_uri(link=l)
        htmr.perform()
    except ValidationError:
        print "Invalid URL"



#    htmr = HTMLRequest(proxy_info=p)
#		htmr.set_uri()



