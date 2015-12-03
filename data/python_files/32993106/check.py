import logging
import datetime

from custom.functions import *
from custom.core.management.base import *
from django.conf import settings

from lxml.html import *

from app.torrents.tasks import *
from app.torrents.models import *

logger = logging.getLogger('checker')

class Command(CustomBaseCommand):
    """
    Django management class for enqueuing the torrents
    """
    args = ''
    help = 'enqueue each of the torrents for checking'

    def process(self, *args, **options):
        """
        Procedure that calls the engine and enqueues the torrents
        """
        logger.info("Enqueuing the torrents. %s torrents to enqueue." % (Torrent.objects.filter(date__lte=datetime.date.today()).count()))

        for exek in range(0, 1):

            for runs in range(0, 1):

                logger.info("Enqueuing torrents.")

                try:

                    torrents = Torrent.objects.filter(date__lte=datetime.date.today())

                    for torrent in torrents:

                        try:

                            if not torrent.is_popular or not torrent.is_gaining_popularity:
                                logger.info("Found a torrent but it isn't popular.")
                                continue

                            name = torrent.name
                            hash = torrent.hash

                            logger.debug("Adding torrent %s %s." % (name, hash))

                            checks = Check.objects.filter(date=datetime.date.today(), torrent=torrent).count()

                            if checks:
                                logger.info("Torrent already checked today.")
                                continue

                            CheckTorrent.delay(torrent.id)

                        except Exception, e:
                            logger.warn("Error processing the torrent. %s" % str(e))
                            continue

                except Exception, e:

                    logger.warn("Error enqueuing torrents. %s" % str(e))
                    raise e

        logger.info("All torrents enqueued.")