import logging
import urlparse
import re
import socket
import datetime
import hashlib
import os.path

import bencode

from django.conf import settings
from custom.functions import *

from celery.task import Task
from celery.registry import tasks

from app.trackers.models import *
from app.torrents.models import *
from app.common.models import *

logger = logging.getLogger('scraper')
socket.setdefaulttimeout(5)

class ScrapeRecord(Task):
    """
    Task class for use with Celery
    """
    def run(self, name, link, file, **kwargs):
        """
        Adds a torrent and trackers to the system
        """
        logger.info('Dequeing %s [%s]' % (name, link))

        try:
            logger.debug("Decoding the torrent file")
            content = bencode.bdecode(fetch_page(file))
            open(os.path.join(settings.TORRENT_DIR, hashlib.sha1(bencode.bencode(content['info'])).hexdigest() + '.torrent'), 'wb+').write(bencode.bencode(content))
        except Exception, e:
            logger.error("Error decoding torrent file. %s" % str(e))
            return

        logger.debug("Initializing the torrent and tracker records")
        trackers = []
        torrent = None


        try:

            for tracker in content['announce-list'] + [[content['announce']]]:

                try:

                    logger.info("Found tracker: ""%s""" % (tracker[0]))
                    record, was_created = Tracker.objects.get_or_create(url=tracker[0])

                    if was_created:
                        logger.info("Adding tracker: ""%s""" % (tracker[0]))

                        record.protocol = 'UDP' if urlparse.urlparse(tracker[0]).scheme == 'udp' else 'TCP'
                        record.secured = True if urlparse.urlparse(tracker[0]).scheme == 'https' else False
                        record.private = bool(re.match(r'.*?[a-z0-9]{16,}.*?', tracker[0]))
                        record.date = datetime.date.today()
                        record.save()

                    trackers.append(record)

                except Exception, e:
                    logger.error("Error saving the tracker. %s" % (str(e)))
                    continue

        except Exception, e:
            logger.error("Error saving the trackers. %s" % (str(e)))
            return


        try:

            for something in range(1,2):

                try:

                    logger.info("Found torrent: ""%s""" % (name))
                    record, was_created = Torrent.objects.get_or_create(hash=hashlib.sha1(bencode.bencode(content['info'])).hexdigest())

                    if was_created:
                        logger.info("Adding torrent: ""%s""" % (name))

                        record.name = name
                        record.private = False
                        record.path = file[0]
                        record.date = datetime.date.fromtimestamp(content['creation date']) if content.has_key('creation date') else datetime.date.today()
                        record.save()

                    torrent = record

                except Exception, e:
                    logger.error("Error saving the torrent. %s" % (str(e)))
                    raise

        except Exception, e:
            logger.error("Error saving the torrent. %s" % (str(e)))
            return


        logger.debug("Linking the torrent and tracker records")
        torrent.tracker_set.add(*trackers)
        [tracker.torrent_set.add(torrent) for tracker in trackers]

        try:
            if torrent.date > datetime.date.today():
                logger.error("Torrent paramaters seem invalid.")
                torrent.delete()
        except Exception, e:
            logger.error("Error verifying file. %s" % str(e))
            return

        logger.info("Done.")

        return True
