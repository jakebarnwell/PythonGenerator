import logging
import socket
import datetime
import sys

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from celery.task import Task
from celery.registry import tasks

from app.torrents.models import Torrent, Check
from app.trackers.helpers import *
from app.trackers.models import Tracker, Query

logger = logging.getLogger('querier')
socket.setdefaulttimeout(5)

class QueryTracker(Task):
    """
    Task class for use with Celery
    """
    def run(self, id, **kwargs):
        """
        Checks the status of the trackers
        """
        tracker = Tracker.objects.get(pk=id)

        for torrent in [torrent for torrent in tracker.torrents.filter(private=False).order_by('?') if torrent.is_popular]:

            try:

                logger.info("Getting information for tracker %s." % (tracker.url))
                peers, latency = scrape(tracker.url, torrent.hash)

            except Exception, e:
                logger.warn("Encountered an error: %s" % (str(e)))

                try:
                    Query.objects.get_or_create(
                        tracker=tracker,
                        torrent=torrent,
                        date=datetime.date.today(),
                        defaults={'peers': None, 'success': False, 'latency': None, 'message': None}
                    )
                except Exception, e:
                    logger.warn("Error saving record: %s" % (str(e)))

                return

            else:
                logger.info("Queried. (%s %s)" % (peers, latency))

                try:
                    Query.objects.get_or_create(
                        tracker=tracker,
                        torrent=torrent,
                        date=datetime.date.today(),
                        defaults={'peers': peers, 'success': True, 'latency': latency, 'message': None}
                    )
                except Exception, e:
                    logger.warn("Error saving record: %s" % (str(e)))

                return

        return True

tasks.register(QueryTracker)
