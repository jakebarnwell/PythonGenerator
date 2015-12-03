import logging
import socket
import datetime

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from celery.task import Task
from celery.registry import tasks

from app.torrents.models import Torrent, Check
from app.trackers.helpers import *
from app.trackers.models import Tracker, Query

logger = logging.getLogger('checker')
socket.setdefaulttimeout(5)

class CheckTorrent(Task):
    """
    Task class for use with Celery
    """
    def run(self, id, **kwargs):
        """
        Gets information for a torrent from it's trackers
        """
        torrent = Torrent.objects.get(pk=id)

        for tracker in [tracker for tracker in torrent.trackers.filter(private=False).order_by('?') if tracker.is_working]:

            try:

                logger.info("Getting information for torrent %s." % (torrent.hash))
                peers, latency = scrape(tracker.url, torrent.hash)

            except Exception, e:
                logger.warn("Encountered an error: %s" % (str(e)))

                try:
                    Check.objects.get_or_create(
                        tracker=tracker,
                        torrent=torrent,
                        date=datetime.date.today(),
                        defaults={'peers': None, 'success': False, 'latency': None, 'message': None}
                    )
                except Exception, e:
                    logger.warn("Error saving record: %s" % (str(e)))

                continue

            else:
                logger.info("Checked. (%s %s)" % (peers, latency))

                try:
                    Check.objects.get_or_create(
                        tracker=tracker,
                        torrent=torrent,
                        date=datetime.date.today(),
                        defaults={'peers': peers, 'success': True, 'latency': latency, 'message': None}
                    )
                except Exception, e:
                    logger.warn("Error saving record: %s" % (str(e)))

                continue

        return True  
