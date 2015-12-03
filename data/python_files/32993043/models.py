import datetime
import urlparse

import requests
import lxml

from dynamic_scraper.models import Scraper, SchedulerRuntime
from scrapy.contrib_exp.djangoitem import DjangoItem
from django.db import models
from django.db.models import *

from app.common.backends import *
from app.common.managers import *

class Site(models.Model):
    """
    Model for storing the sites
    """
    title = models.CharField(max_length=2000)
    url = models.CharField(max_length=2000)
    feed = models.CharField(max_length=512, null=True)
    minimum = models.PositiveIntegerField(default=50, null=False)
    private = models.BooleanField(default=False)
    timezone = models.CharField(max_length=512, null=True)
    type = models.CharField(null=True, max_length=5, choices=(('MOVIE', 'Movies'), ('MUSIC', 'Music')))
    scraper = models.ForeignKey(Scraper, blank=True, null=True, on_delete=models.SET_NULL)
    scraper_runtime = models.ForeignKey(SchedulerRuntime, blank=True, null=True, on_delete=models.SET_NULL)

    objects = SiteManager()

    def __unicode__(self):
        """
        String representation method.
        """
        return self.title

    class Meta:
        """
        Meta.
        """
        unique_together = ("url",)
        ordering = ['-id']

    def save(self, *args, **kwargs):
        """
        Save method which saves the record.
        """
        try:
            if self.id is None:
                self.title, self.feed, self.enabled = WebsiteInformation.process(self.url)
            super(Site, self).save(*args, **kwargs)
        except Exception, e:
            raise e

    @property
    def recent_scrapes(self):
        """
        Returns the recent scrapes of the site.
        """
        try:
            scrapes = self.link_set.all().extra(select={'date': 'DATE(date)'}, order_by=['-date'])
            scrapes = scrapes.values('date').annotate(records=Count('id'))
            return scrapes
        except Exception, e:
            return None

    @property
    def host(self):
        """
        Returns the hostname of the site.
        """
        try:
            parts = urlparse(self.url)
            host = parts.netloc
            return host
        except Exception, e:
            print e
            return None

    @property
    def rows_listed(self):
        """
        Returns the number of rows in a page.
        """
        try:
            response = requests.get(self.url % str(1))
            records = fromstring(response.content).xpath(self.record)
            return len(records)
        except Exception, e:
            return None

    @property
    def latest_torrents(self):
        """
        Latest number of peers of the torrent over the period.
        """
        try:
            links = self.link_set.all()
            torrent = links.order_by('-date')[0].name
            return torrent
        except Exception, e:
            return None

    @property
    def days_since(self):
        """
        Returns the number of days sice this this site was checked.
        """
        try:
            difference = datetime.date.today() - self.link_set.all().latest('date').date.date()
            days = difference.days
            return days
        except Exception, e:
            return None

    @property
    def not_recently_checked(self):
        """
        Returns whether this site was recently checked.
        """
        try:
            scrape = self.link_set.all().latest('date')
            last_scraped = scrape.date
            return last_scraped
        except Exception, e:
            return None

#    @property
#    def is_gaining_popularity(self):
#        """
#        Returns whether this torrent is gaining popularity or not.
#        """
#        try:
#            checks = Check.objects.filter(success=True, torrent=self)
#            return True
#        except Exception, e:
#            return None

    @property
    def is_accessible(self):
        """
        Returns whether this site is accessible or not.
        """
        try:
            response = requests.get(self.url % str(1))
            is_accessible = True if response.content else False
            return is_accessible
        except Exception, e:
            return False


class Link(models.Model):
    """
    Model for storing the links
    """
    name = models.CharField(max_length=2000)
    url = models.CharField(max_length=2000)
    date = models.DateTimeField(auto_now_add=True)
    site = models.ForeignKey(Site)
    torrent = models.CharField(max_length=2000, null=True)
    seeders = models.PositiveSmallIntegerField(null=True)
    leechers = models.PositiveSmallIntegerField(null=True)

    def __unicode__(self):
        """
        String representation method.
        """
        return self.name

    class Meta:
        """
        Meta.
        """
        unique_together = ("url",)
        ordering = ['-date']

class LinkItem(DjangoItem):
    django_model = Link
