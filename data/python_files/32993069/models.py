import datetime
import urlparse

import requests
import caching.base

from django.db import models
from django.db.models import *

from app.trackers.backends import *
from app.trackers.managers import *

class Tracker(caching.base.CachingMixin, models.Model):
    """
    Model for storing the trackers
    """
    url = models.URLField(max_length= 200)
    protocol = models.CharField(null=False, max_length=3)
    secured = models.BooleanField(default=False)
    private = models.BooleanField(default=False)
    date = models.DateField(auto_now_add=True)
    torrents = models.ManyToManyField('torrents.Torrent', verbose_name="Torrents")
    latitude = models.DecimalField(null=True, decimal_places=3, max_digits=6)
    longitude = models.DecimalField(null=True, decimal_places=3, max_digits=6)
    country = models.CharField(null=True, max_length=64)

    objects = TrackerManager()

    def __unicode__(self):
        """
        String representation method.
        """
        return self.url

    class Meta:
        """
        Meta.
        """
        unique_together = ('url', 'secured')
        ordering = ['-id']

    def save(self, *args, **kwargs):
        """
        Save method which saves the record.
        """
        try:
            if self.id is None:
                self.latitude, self.longitude, self.country = LocationInformation.process(self.url)
            super(Tracker, self).save(*args, **kwargs)
        except Exception, e:
            raise e

    @property
    def host(self):
        """
        Returns the hotname of the tracker.
        """
        try:
            url = urlparse.urlparse(self.url)
            host = url.netloc
            return host
        except Exception, e:
            return None

    @property
    def latency_times(self):
        """
        Returns the latency times of the tracker over the period.
        """
        try:
            queries = Query.objects.filter(success=True, tracker=self)
            latency_times = [query.latency for query in queries]
            return latency_times
        except Exception, e:
            return None

    @property
    def average_latency(self):
        """
        Average latency of tracker over the period.
        """
        try:
            queries = Query.objects.filter(success=True, tracker=self)
            latency = queries.aggregate(Avg('latency')).values()[0]
            return latency
        except Exception, e:
            return None

    @property
    def uptime_percentage(self):
        """
        Returns the amount of time this tracker has been available.
        """
        try:
            total_queries = Query.objects.filter(tracker=self).aggregate(Count('id')).values()[0]
            successful_queries = Query.objects.filter(success=True, tracker=self).aggregate(Count('id')).values()[0]
            return  (successful_queries / (total_queries if total_queries > 0 else 1) ) * 100
        except Exception, e:
            return None

    @property
    def last_checked(self):
        """
        Returns the last time this tracker was checked.
        """
        try:
            query = Query.objects.filter(tracker=self).latest('date')
            last_checked = query.date
            return last_checked
        except Exception, e:
            return None

    @property
    def first_few_tries(self):
        """
        Returns whether this tracker has only been checked a few times
        """
        try:
            tries = Query.objects.filter(tracker=self).count()
            first_few_tries = False if tries > 10 else True
            return first_few_tries
        except Exception, e:
            return False

    @property
    def is_working(self):
        """
        Returns whether this tracker is working or not.
        """
        try:
            queries = Query.objects.filter(tracker=self).order_by('-date')
            if len(queries) < 3:
                return True
            else:
                return not all(query['success'] == False for query in queries.values('success')[:3])
        except Exception, e:
            return False


from app.torrents.models import *

class Query(models.Model):
    """
    Model for storing the queries
    """
    torrent = models.ForeignKey(Torrent)
    tracker = models.ForeignKey(Tracker)
    date = models.DateTimeField(auto_now_add=True)
    latency = models.FloatField(null=True)
    peers = models.BigIntegerField(null=True)
    success = models.BooleanField(default=False)
    message = models.CharField(max_length=256, null=True)

    def __unicode__(self):
        """
        String representation method.
        """
        return str(self.date)

    class Meta:
        """
        Meta.
        """
        unique_together = ('tracker', 'torrent', 'date')
        ordering = ['-date']
