import datetime
import urlparse

import requests
import caching.base

from django.db import models
from django.db.models import *

from app.torrents.backends import *
from app.torrents.managers import *

class Torrent(caching.base.CachingMixin, models.Model):
    """
    Model for storing the torrents
    """
    hash = models.CharField(max_length=40)
    path = models.CharField(max_length=512)
    name = models.CharField(max_length=256)
    private = models.BooleanField(default=False)
    date = models.DateField(auto_now_add=True)
    trackers = models.ManyToManyField('trackers.Tracker', verbose_name="Trackers")
    size = models.PositiveIntegerField()
    files = models.CharField(max_length=65535, null=True)
    type = models.CharField(max_length=256)

    objects = TorrentManager()

    def __unicode__(self):
        """
        String representation method.
        """
        return self.hash

    class Meta:
        """
        Meta.
        """
        unique_together = ('hash',)
        ordering = ['-id']

    def save(self, *args, **kwargs):
        """
        Save method which saves the record.
        """
        try:
            if self.id is None:
                self.size, self.type, self.files = TorrentInformation.process(self.hash)
            super(Torrent, self).save(*args, **kwargs)
        except Exception, e:
            raise e

    @property
    def recent_checks(self):
        """
        Returns the recent checks for the torrent.
        """
        try:
            checks = self.check_set.extra(select={'date': 'DATE(date)'}, order_by=['-date'])
            checks = checks.filter(success=True).values('date').annotate(peers=Sum('peers'))
            return checks
        except Exception, e:
            return None

    @property
    def gigs(self):
        """
        Returns the filesize (GB) of the torrent.
        """
        try:
            megs = self.size
            gigs = round(float(megs) / 1024 / 1024, 2)
            return gigs
        except Exception, e:
            return None

    @property
    def peer_quantities(self):
        """
        Returns the number of peers of the torrent over the period.
        """
        try:
            checks = Check.objects.filter(success=True, torrent=self)
            peer_quantities = [check.seeds + check.peers for check in checks]
            return peer_quantities
        except Exception, e:
            return None

    @property
    def latest_peers(self):
        """
        Latest number of peers of the torrent over the period.
        """
        try:
            checks = Check.objects.filter(success=True, torrent=self)
            peers = checks.order_by('-date')[0].peers
            return peers
        except Exception, e:
            return 0

    @property
    def days_since(self):
        """
        Returns the number of days sice this torrent has been found.
        """
        try:
            timedelta = datetime.date.today() - self.date
            days = timedelta.days
            return days
        except Exception, e:
            return None

    @property
    def not_recently_checked(self):
        """
        Returns whether this torrent was recently checked.
        """
        try:
            check = Check.objects.filter(torrent=self).latest('date')
            last_checked = check.date
            return last_checked
        except Exception, e:
            return None

    @property
    def is_gaining_popularity(self):
        """
        Returns whether this torrent is gaining popularity or not.
        """
        try:
            checks = Check.objects.filter(success=True, torrent=self)
            return True
        except Exception, e:
            return None

    @property
    def is_popular(self):
        """
        Returns whether this torrent is popular or not.
        """
        #TODO: Fix this popular thing.
        try:
            check = Check.objects.filter(torrent=self).order_by('-date')[0]
            is_popular = check.success
            return True
        except Exception, e:
            return True


from app.trackers.models import *

class Check(models.Model):
    """
    Model for storing the checks
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
