import copy
import datetime
from django.contrib.localflavor.us.models import USPostalCodeField
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q, Max, F
from django.utils.timezone import now, utc

from .conceptq import concept

class Address(models.Model):
    """
    Mailing addresses of individuals, entities, or prisons.
    """
    address1 = models.CharField(max_length=255, blank=True)
    address2 = models.CharField(max_length=255, blank=True)
    address3 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255, blank=True)
    state = USPostalCodeField(blank=True)
    zip = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=255, blank=True,
            help_text=u"Leave blank for USA.")

    def get_address_lines(self):
        lines = []
        for field in ('address1', 'address2', 'address3'):
            if getattr(self, field):
                lines.append(getattr(self, field))
        if self.city and self.state and self.zip:
            lines.append(u"{0}, {1}  {2}".format(
                self.city, self.state, self.zip
            ))
        if self.country:
            lines.append(self.country)
        return lines

    def format_address(self):
        return u"\n".join(self.get_address_lines())
    
    def __unicode__(self):
        return u", ".join(self.get_address_lines())

    class Meta:
        verbose_name_plural = "Addresses"

class PrisonType(models.Model):
    """
    The prison type -- e.g. prison, work release, jail, halfway house
    """
    name = models.CharField(max_length=50,
            help_text="Type of prison -- e.g. prison, jail, halfway house")
    def __unicode__(self):
        return self.name

class PrisonAdminType(models.Model):
    """
    Prison administration type -- e.g. Bureau of Prisons, State prison, CCA
    """
    name = models.CharField(max_length=50,
            help_text="Name of organization that administers prisons -- e.g. CCA, BOP")
    def __unicode__(self):
        return self.name

class Prison(models.Model):
    """
    Administrative, address, and other details about a prison.
    """
    name = models.CharField(max_length=50,
            help_text="The name of this institution")
    type = models.ForeignKey(PrisonType, blank=True, null=True,
            help_text="The type of institution -- e.g. prison, jail, halfway house")
    address = models.ForeignKey(Address,
            help_text="Mailing address for people housed here.")
    admin_type = models.ForeignKey(PrisonAdminType, blank=True, null=True,
            help_text="Organization administering this prison (e.g. CCA, BOP).")
    admin_name = models.CharField(max_length=50, blank=True,
            help_text="Name of institution administering this prison (e.g. 'Salinas Valley State Prison' administers 'Salinas Valley State Prison -- A'.")
    admin_address = models.ForeignKey(Address, blank=True, null=True,
            help_text="Administration's address for this prison, if different from the main address.",
            related_name="prison_admin_set")
    admin_phone = models.CharField(max_length=20, blank=True)
    warden = models.CharField(max_length=50, blank=True)
    men = models.NullBooleanField()
    women = models.NullBooleanField()
    juveniles = models.NullBooleanField()
    minimum = models.NullBooleanField()
    medium = models.NullBooleanField()
    maximum = models.NullBooleanField()
    control_unit = models.NullBooleanField()
    death_row = models.NullBooleanField()

    def get_address_lines(self):
        return self.address.get_address_lines()

    def format_address(self):
        return u"\n".join(self.get_address_lines())

    def format_list_display(self):
        if self.admin_type:
            name = u"%s (%s)" % (self.name, self.admin_type)
        else:
            name = self.name
        return u"\n".join((name, self.format_address()))

    def __unicode__(self):
        if self.admin_type is not None:
            return u"%s: %s (%s)" % (self.name, self.type, self.admin_type.name)
        else:
            return u"%s: %s" % (self.name, self.type)

class ContactManager(models.Manager):
    @concept
    def reachable(self):
        stays = MailingStay.objects.stayed().values_list('id', flat=True)
        return Q(~Q(id__in=stays), deceased=False, lost_contact=False)

    @concept
    def unreachable(self):
        stays = MailingStay.objects.stayed().values_list('id', flat=True)
        return Q(id__in=stays) | Q(deceased=True) | Q(lost_contact=True)

    def issue_needed(self, issue):
        issue_mailings = Mailing.objects.issue_exists(issue).values_list('id', flat=True)
        return self.filter(self.reachable().q,
                Subscription.objects.current(issue.date).via("subscription"),
        ).exclude(
                mailing__id__in=issue_mailings
        ).distinct()

    def issue_unreachable(self, issue):
        issue_mailings = Mailing.objects.issue_exists(issue).values_list('id', flat=True)
        return self.filter(self.unreachable().q,
            Subscription.objects.current(issue.date).via("subscription"),
        ).exclude(
                mailing__id__in=issue_mailings
        ).distinct()

    def issue_enqueued(self, issue):
        mailings = Mailing.objects.issue_enqueued(issue).values_list('id', flat=True)
        return self.filter(mailing__id__in=mailings).distinct()

    def issue_sent(self, issue):
        mailings = Mailing.objects.issue_sent(issue).values_list('id', flat=True)
        return self.filter(mailing__id__in=mailings).distinct()

    def notice_needed(self, when, remaining, mtype, rel):
        recent_mailings = Mailing.objects.notice_type_near(
                mtype, when).values_list('id', flat=True)
        return self.filter(
                self.reachable().q,
                self.with_remaining_issues_at(when, remaining, rel).q,
        ).exclude(
                mailing__id__in=recent_mailings
        ).distinct()

    def notice_unreachable(self, when, remaining, mtype, rel):
        recent_mailings = Mailing.objects.notice_type_near(
                mtype, when).values_list('id', flat=True)
        return self.filter(
            self.unreachable().q,
            self.with_remaining_issues_at(when, remaining, rel).q,
        ).exclude(
            mailing__id__in=recent_mailings
        ).distinct()

    def notice_enqueued(self, when, remaining, mtype, rel):
        mailings = Mailing.objects.notice_type_near(
                mtype, when, sent=False).values_list('id', flat=True)
        return self.filter(
            self.reachable().q,
            self.with_remaining_issues_at(when, remaining, rel).q,
            mailing__id__in=mailings,
        ).distinct()

    def notice_sent(self, when, remaining, mtype, rel):
        mailings = Mailing.objects.notice_type_near(
                mtype, when, sent=True).values_list('id', flat=True)
        return self.filter(
            self.reachable().q,
            self.with_remaining_issues_at(when, remaining, rel).q,
            mailing__id__in=mailings,
        ).distinct()


    def similar_to(self, first, middle, last, min_score=0):
        select = {}
        select_params = []
        order_by = []
        where = ""
        params = []
        fields = ((first, "first_name"), (middle, "middle_name"), (last, "last_name"))
        used_fields = [f for f in fields if f[0]]
        for name, key in used_fields:
            select['{0}_sim'.format(key)] = "similarity({0}, %s)".format(key)
            select_params.append(name)
            order_by.append('-{0}_sim'.format(key))
            if where:
                where += " OR "
            where += 'similarity({0}, %s) > %s'.format(key)
            params.append(name)
            params.append(min_score)
        order_by.append('last_name')
        return self.extra(
            select=select,
            select_params=select_params,
            order_by=order_by,
            where=[where],
            params=params,
        )

    def subscribed_at(self, date=None):
        return self.filter(
            Subscription.objects.current(date).via("subscription")
        ).distinct()

    @concept
    def with_remaining_issues_at(self, when, num, rel='recipient'):
        """
        Return all the contacts who have the specified number of issues
        remaining at the time of the specified issue.  Assume that issues are
        always on the same day of the month.

        If rel is 'payer', return contacts who pay for the subscriptions
        (whether they receive them or not).
        """
        rel_prefix = {
            'recipient': 'subscription',
            'payer': 'subscriptions_payed_for',
        }.get(rel)

        SO = Subscription.objects
        if rel == "payer":
            self_payer_q = SO.not_self_payer().via(rel_prefix)
        else:
            self_payer_q = Q()
        return Q(
            # Constrain to only those contacts we can reach.
            self.reachable().q,
            # Exclude perpetual subscriptions.
            ~SO.perpetual().via(rel_prefix),
            # Constrain by number of issues remaining.
            SO.issues_left_at(when, num).via(rel_prefix),
            # Constrain by self-payer-ness.
            self_payer_q,
        )
        
    def shareable_with(self, partner):
        # We can only share people who have opted out, and whom we learned
        # about via an info request.
        return self.filter(self.reachable().q,
                source__name='Inquiry', opt_out=False,
            ).exclude(sharingbatch__partner=partner)

class ContactSourceCategory(models.Model):
    """
    General category for source info about contacts (e.g. Letter, Flyer,
    Internet, etc).
    """
    name = models.CharField(max_length=255)
    def __unicode__(self):
        return self.name

class ContactSource(models.Model):
    """
    Specific source for a contact (e.g. Web Sale, Book Order, Info Request)
    """
    name = models.CharField(max_length=255)
    category = models.ForeignKey(ContactSourceCategory, null=True)
    def __unicode__(self):
        if self.category:
            return "%s: %s" % (self.name, self.category)
        return self.name
    class Meta:
        ordering = ['-category', 'name']

class OrganizationType(models.Model):
    """
    Type of entity -- e.g. Library, University, Foundation
    """
    type = models.CharField(max_length=50)
    def __unicode__(self):
        return self.type

class Contact(models.Model):
    """
    Individuals, entities, and all other people with whom we're in contact.
    """
    MISSING_NAME = "[name missing]"

    first_name = models.CharField(max_length=255, blank=True, db_index=True,
            help_text="Individual, or contact within organization")
    middle_name = models.CharField(max_length=255, blank=True, db_index=True)
    last_name = models.CharField(max_length=255, blank=True, db_index=True)
    organization_name = models.CharField(max_length=255, blank=True,
            help_text="Leave blank for individuals.", db_index=True)
    organization_type = models.ForeignKey(OrganizationType,
            blank=True, null=True,
            help_text="Leave blank for individuals.")
    email = models.EmailField(blank=True)
    gender = models.CharField(max_length=1, choices=(
        ('M', "Male"),
        ('F', 'Female'),
        ('T', 'Transgender'),
    ), blank=True)
    type = models.CharField(max_length=50, choices=(
        ('individual', 'Individual'),
        ('prisoner', 'In prison'),
        ('entity', 'Entity'),
        ('advertiser', 'Advertiser'),
        ('fop', 'Friend of PLN'),
    ))
    source = models.ForeignKey(ContactSource, blank=True, null=True,
            help_text="How did we find out about this contact? Leave blank if unknown.")
    opt_out = models.BooleanField(default=False,
            help_text="Opt out from appeals.")
    address = models.ForeignKey(Address, blank=True, null=True,
            help_text="Non-prison addresses only")
    created = models.DateTimeField(default=now)
    deceased = models.BooleanField()
    lost_contact = models.BooleanField(
        help_text="Check this if the last known address for this contact no longer works.")
    donor = models.BooleanField(verbose_name="Is a donor",
            help_text="Check if this contact should be included in donor appeals.")

    objects = ContactManager()

    def show_name(self):
        return self.organization_name or self.get_full_name()

    def current_prisoner_address(self):
        if not self.type == 'prisoner':
            return None
        try:
            return self.prisoneraddress_set.select_related('prison__address').get(end_date__isnull=True)
        except PrisonerAddress.DoesNotExist:
            return None

    def current_subscription(self, when=None):
        when = when or now()
        subs = self.subscription_set.filter(
                Q(end_date__gte=when) | Q(end_date__isnull=True),
                start_date__lte=when,
        )
        if len(subs) == 0:
            return None
        return subs[0]

    def issues_remaining(self, when=None):
        sub = self.current_subscription(when)
        if not sub:
            return 0
        return sub.issues_remaining()

    def subscription_type(self, when=None):
        sub = self.current_subscription(when)
        if not sub:
            return None
        return sub.type

    def first_subscribed(self):
        try:
            return self.subscription_set.order_by('start_date')[0].start_date
        except IndexError:
            return None

    def renewals(self):
        return self.subscription_set.count() - 1

    def get_full_name(self):
        name = u" ".join(
            n for n in (self.first_name, self.middle_name, self.last_name) if n
        )
        if name == "":
            name = self.MISSING_NAME
        return name

    def get_address_lines(self):
        lines = []
        pad = self.current_prisoner_address()
        if pad:
            lines = pad.get_address_lines()
        else: 
            if self.organization_name:
                lines.append(self.organization_name)
                full_name = self.get_full_name()
                if full_name and full_name != self.MISSING_NAME:
                    lines.append(u"c/o %s" % full_name)
            else:
                lines.append(self.get_full_name())
            if self.address:
                lines += self.address.get_address_lines()
        return lines

    def format_address(self):
        return u"\n".join(self.get_address_lines())

    def get_absolute_url(self):
        return reverse("subscribers.contacts.show", args=[self.pk])

    def __unicode__(self):
        try:
            return u", ".join(self.get_address_lines())
        except PrisonerAddress.DoesNotExist:
            return u"%s: %s" % (self.get_full_name(), self.type)

    class Meta:
        ordering = ['last_name', 'organization_name']

class MailingStayManager(models.Manager):
    @concept
    def not_stayed(self):
        return Q(end_date__isnull=False, end_date__lte=now())

    @concept
    def stayed(self):
        return Q(Q(end_date__gte=now()) | Q(end_date__isnull=True),
                 start_date__lte=now())

class MailingStay(models.Model):
    contact = models.ForeignKey(Contact)
    start_date = models.DateTimeField(default=now)
    end_date = models.DateTimeField(blank=True, null=True,
            help_text="Leave blank to withold mail until further notice.")

    objects = MailingStayManager()
    
    class Meta:
        ordering = ['-end_date']

    def __unicode__(self):
        return ", ".join((unicode(self.contact), unicode(self.start_date),
                          unicode(self.end_date)))

class InquiryResponseType(models.Model):
    description = models.CharField(max_length=255)
    code = models.CharField(max_length=255, blank=True)
    generate_mailing = models.BooleanField()
    def __unicode__(self):
        return self.description

class InquiryType(models.Model):
    description = models.CharField(max_length=255)
    def __unicode__(self):
        return self.description

class InquiryManager(models.Manager):
    def unmailed(self):
        return self.filter(batch__isnull=True)

    def mailed(self):
        return self.filter(batch__isnull=False)

    def reverse_chronological(self):
        return self.order_by('-date')

    @concept
    def mailing_needed(self):
        return Q(response_type__generate_mailing=True, mailing__isnull=True)

    @concept
    def mailing_unreachable(self):
        return Q(Contact.objects.unreachable().via('contact'),
                 response_type__generate_mailing=True)

    @concept
    def mailing_enqueued(self):
        return Q(response_type__generate_mailing=True,
                 mailing__isnull=False, mailing__sent__isnull=True)

    @concept
    def mailing_sent(self):
        return Q(response_type__generate_mailing=True,
                 mailing__isnull=False, mailing__sent__isnull=False)

class Inquiry(models.Model):
    contact = models.ForeignKey('Contact')
    request_type = models.ForeignKey(InquiryType)
    response_type = models.ForeignKey(InquiryResponseType)
    date = models.DateTimeField(default=now)

    objects = InquiryManager()

    def __unicode__(self):
        return ": ".join((unicode(self.response_type), unicode(self.contact)))

    class Meta:
        ordering = ['date']

class DonorBatch(models.Model):
    date = models.DateTimeField(default=now)
    contacts = models.ManyToManyField('Contact')
    def __unicode__(self):
        return "%s: %s contacts" % (self.date, self.contacts.count())
    class Meta:
        ordering = ['-date']

class PrisonerAddress(models.Model):
    contact = models.ForeignKey(Contact)
    prisoner_number = models.CharField(max_length=50, blank=True)
    death_row = models.NullBooleanField()
    control_unit = models.NullBooleanField()
    start_date = models.DateTimeField(default=now)
    end_date = models.DateTimeField(blank=True, null=True)
    unit = models.CharField(max_length=255, blank=True)
    prison = models.ForeignKey('Prison')

    def contact_name(self):
        return self.contact.show_name()

    def is_current(self):
        n = now()
        return self.start_date <= n and (
            (self.end_date is None) or (self.end_date > n)
        )

    def get_address_lines(self):
        lines = []
        if self.prisoner_number:
            lines.append(u"{0}, #{1}".format(self.contact.show_name(), self.prisoner_number.lstrip('#')))
        else:
            lines.append(self.contact.show_name())
        if self.unit:
            lines.append(self.unit)
        lines += self.prison.get_address_lines()
        return lines

    def format_address(self):
        return u"\n".join(self.get_address_lines())

    def __unicode__(self):
        return unicode(self.prison)

    class Meta:
        verbose_name_plural = u"Addresses in prison"
        ordering = ['-end_date', 'contact']

class Note(models.Model):
    contact = models.ForeignKey(Contact)
    author = models.ForeignKey(User, related_name="notes_authored")
    text = models.TextField()
    created = models.DateTimeField(default=now)
    modified = models.DateTimeField()

    def contact_name(self):
        return self.contact.show_name()

    def save(self, *args, **kwargs):
        self.modified = now()
        super(Note, self).save()

    def __unicode__(self):
        return u"%s: %s" % (self.contact.show_name(), self.text[:15])

    class Meta:
        ordering = ['-created']

class SubscriptionSource(models.Model):
    name = models.CharField(max_length=255)
    def __unicode__(self):
        return self.name

class SubscriptionStopReason(models.Model):
    reason = models.CharField(max_length=50)
    def __unicode__(self):
        return self.reason

class SubscriptionManager(models.Manager):
    @concept
    def current(self, when=None):
        when = when or now()
        return Q(self.perpetual().q | Q(end_date__gte=when),
                start_date__lte=when)

    @concept
    def not_self_payer(self):
        return Q(contact__id__lt=F('payer__id')) | \
               Q(contact__id__gt=F('payer__id'))

    @concept
    def self_payer(self):
        return Q(contact__id=F('payer__id'))

    @concept
    def perpetual(self):
        return Q(end_date__isnull=True)

    @concept
    def issues_left_at(self, when, remaining):
        def add_months(dt, months):
            month = dt.month - 1 + months
            year = dt.year + month / 12
            month = month % 12 + 1
            return datetime.datetime(year, month, dt.day, 0, 0, 0, 0, utc)
        end_date_min = add_months(when, remaining)
        end_date_max = add_months(when, remaining + 1)
        return Q(start_date__lte=when,
                 end_date__lt=end_date_max,
                 end_date__gt=end_date_min)

class Subscription(models.Model):
    contact = models.ForeignKey(Contact)
    payer = models.ForeignKey(Contact, related_name="subscriptions_payed_for")
    type = models.CharField(max_length=20, choices=(
        ('trial', 'Trial'),
        ('subscription', 'Subscription'),
    ))
    source = models.ForeignKey(SubscriptionSource, blank=True, null=True,
            help_text="Leave blank if unknown.")
    paid_amount = models.IntegerField(default=0)
    start_date = models.DateTimeField(default=now, db_index=True)
    end_date = models.DateTimeField(blank=True, null=True, db_index=True,
        help_text="Leave blank for a perpetual subscription")
    original_end_date = models.DateTimeField(blank=True, null=True,
        help_text="End date before an early stop.")
    stop_reason = models.ForeignKey(SubscriptionStopReason,
        blank=True, null=True)

    objects = SubscriptionManager()

    def end_early(self, reason, when=None):
        self.original_end_date = self.end_date
        self.end_date = when or now()
        self.stop_reason = reason

    def contact_name(self):
        return self.contact.show_name()

    def is_current(self):
        n = now()
        return self.start_date <= n and (
            (self.end_date is None) or (self.end_date > n)
        )

    def issues_remaining(self, when=None):
        when = when or now()
        if self.end_date is None:
            return -1
        start = when or now()
        count = 0
        while True:
            start += datetime.timedelta(days=32)
            start = datetime.datetime(start.year, start.month, 1, 0, 0, 0, 0, utc)
            if start > self.end_date:
                break
            count += 1
        return count

    def __unicode__(self):
        return u"%s: %s, %s" % (self.contact, self.type, self.end_date)

class Issue(models.Model):
    volume = models.IntegerField()
    number = models.IntegerField()
    date = models.DateTimeField()

    def save(self, *args, **kwargs):
        self.num_recipients_denormalized = self.num_recipients()
        return super(Issue, self).save(*args, **kwargs)

    def num_recipients(self):
        return self.mailing_set.filter(type__type='Issue', issue=self).count()

    def num_censored_recipients(self):
        return self.mailing_set.filter(censored=True).count()

    def __unicode__(self):
        return u"Volume %s Number %s" % (self.volume, self.number)

    class Meta:
        ordering = ['-date']

class MailingLog(models.Model):
    user = models.ForeignKey(User)
    type = models.ForeignKey('MailingType')
    note = models.CharField(max_length=50, blank=True, default="",
        help_text="Additional info identifying this mailing log.")
    created = models.DateTimeField(default=now)
    mailings = models.ManyToManyField('Mailing')

    def __unicode__(self):
        return u"%s: %s" % (self.user, self.created)

    def get_absolute_url(self):
        return reverse("subscribers.mailinglogs.show", args=[self.pk])

class MailingType(models.Model):
    type = models.CharField(max_length=50)
    def __unicode__(self):
        return self.type

class MailingManager(models.Manager):
    @concept
    def issue_exists(self, issue):
        return Q(issue=issue, type__type="Issue")

    @concept
    def issue_enqueued(self, issue):
        return Q(issue=issue, type__type="Issue", sent__isnull=True)

    @concept
    def issue_sent(self, issue):
        return Q(issue=issue, type__type="Issue", sent__isnull=False)

    @concept
    def notice_type_near(self, mtype, when, slop=20, sent=None):
        if sent == True:
            sent_q = Q(sent__isnull=False)
        elif sent == False:
            sent_q = Q(sent__isnull=True)
        else:
            sent_q = Q()
        return Q(sent_q, type=mtype,
                 created__gte=when - datetime.timedelta(days=slop),
                 created__lte=when + datetime.timedelta(days=slop))

    @concept
    def inquiry_enqueued(self, inquiry):
        return Q(inquiry=inquiry, sent__isnull=True)

    @concept
    def inquiry_sent(self, inquiry):
        return Q(inquiry=inquiry, sent__isnull=False)

class Mailing(models.Model):
    type = models.ForeignKey(MailingType, blank=True, null=True)
    issue = models.ForeignKey(Issue, blank=True, null=True)
    inquiry = models.ForeignKey(Inquiry, blank=True, null=True)
    custom_text = models.TextField(blank=True)
    contact = models.ForeignKey(Contact)
    censored = models.BooleanField(
        default=False,
        help_text="Check if this mailing was refused delivery due to censorship."
    )
    notes = models.TextField(
        help_text="Record any unusual details or special info about this mailing here"
    )
    created = models.DateTimeField(default=now)
    sent = models.DateTimeField(blank=True, null=True)

    objects = MailingManager()

    def contact_name(self):
        return self.contact.show_name()

    def __unicode__(self):
        if self.type == 'issue':
            return u"%s: %s" % (self.contact, self.issue)
        else:
            return u"%s: %s, %s" % (self.contact, self.type, 
                    self.created.strftime(u"%Y-%m-%d"))
    class Meta:
        ordering = ['-created', 'contact__last_name']

class SharingPartner(models.Model):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

class SharingBatch(models.Model):
    partner = models.ForeignKey(SharingPartner)
    contacts = models.ManyToManyField(Contact)
    date = models.DateTimeField(default=now)

    class Meta:
        ordering = ['-date']

    def __unicode__(self):
        return unicode(self.date)
