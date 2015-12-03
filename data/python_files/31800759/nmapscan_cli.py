import os
import settings
from optparse import OptionParser
from urlparse import urlparse
from django.core.management import setup_environ


setup_environ(settings)

from NMapScan.models import NMapScan, NMapResult
from NMapScan.tasks import nmap_scan_job

usage = "usage: %prog SCANNER [options]"
parser = OptionParser(usage)

#parser.add_option("-p","--proxy",action="store",type="string",dest="proxy",help="If using a proxy, the proxy_name field of the proxy in the database")
#parser.add_option("-H","--https",action="store_false",dest="https",help="If using a proxy, disable HTTPS")

(options, args) = parser.parse_args()

#Make sure they actually entered a URL
if len(args) == 0:
    print "You must enter an IP address to scan and the name of a scanner object"
else:
    scanner = args[0]
    print 'Beginning scan with scanner %s' % scanner
    nmap_scan_job(scanner)
