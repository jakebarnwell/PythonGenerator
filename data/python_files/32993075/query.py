import logging
import datetime

from custom.functions import *
from custom.core.management.base import *
from django.conf import settings

from lxml.html import *

from app.trackers.tasks import *
from app.trackers.models import *

logger = logging.getLogger('querier')

class Command(CustomBaseCommand):
    """
    Django management class for enqueuing the trackers
    """
    args = ''
    help = 'enqueue each of the trackers for querying'

    def process(self, *args, **options):
        """
        Procedure that calls the engine and enqueues the trackers
        """
        logger.info("Enqueuing the trackers. %s trackers to enqueue." % (Tracker.objects.filter(date__lte=datetime.date.today()).count()))

        for exek in range(0, 1):

            for runs in range(0, 1):

                logger.info("Enqueuing trackers.")

                try:

                    trackers = Tracker.objects.filter(date__lte=datetime.date.today())

                    for tracker in trackers:

                        try:

                            if not tracker.is_working or not tracker.first_few_tries:
                                logger.info("Found a tracker but it isn't working.")
                                continue

                            url = tracker.url
                            country = tracker.country

                            logger.debug("Adding tracker %s [%s]." % (url, country))

                            queries = Query.objects.filter(date=datetime.date.today(), tracker=tracker).count()

                            if queries:
                                logger.info("Tracker already checked today.")
                                continue

                            QueryTracker.delay(tracker.id)

                        except Exception, e:
                            logger.warn("Error processing the tracker. %s" % str(e))
                            continue

                except Exception, e:

                    logger.warn("Error enqueuing trackers. %s" % str(e))
                    raise e

        logger.info("All trackers enqueued.")