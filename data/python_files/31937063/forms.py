import datetime
import re
from django import forms
from django.db.models import Q, Max
from django.contrib.localflavor.us.forms import USPSSelect
from django.utils.timezone import now, utc
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse

from subscribers.models import *


#
# Utilities
#
def null_model_choices(Model, null_label='[Unknown]'):
    """
    We want model choice fields that have both a blank ("unconstrained"), and
    null ("value is null in database"). So we use a ChoiceField instead of
    ModelChoiceField, and append two different blank values, "---------" and
    "Unknown". This function returns the choices for a Model.
    """
    return [('', '----------'), ('None', null_label)] + [
            (m.id, unicode(m)) for m in Model.objects.all()
    ]

class BlankNullBooleanSelect(forms.Select):
    """
    This is copied from NullBooleanSelect, and altered to change the Null value
    from "Unknown" to "-------". NullBooleanSelect doesn't allow overriding
    choices, so we have to copy the whole class. Semantically, we're using
    NullBooleanField's as ("unconstrained", True, False), so "Unknown" is
    confusing.
    """
    def __init__(self, attrs=None):
        choices = (("1", "------"), ("2", "Yes"), ("3", "No"))
        super(BlankNullBooleanSelect, self).__init__(attrs, choices)

    def render(self, name, value, attrs=None, choices=()):
        try:
            value = {True: u'2', False: u'3', u'2': u'2', u'3': u'3'}[value]
        except KeyError:
            value = u'1'
        return super(BlankNullBooleanSelect, self).render(name, value, attrs, choices)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        return {u'2': True,
                True: True,
                'True': True,
                u'3': False,
                'False': False,
                False: False}.get(value, None)

    def _has_changed(self, initial, data):
        # For a NullBooleanSelect, None (unknown) and False (No)
        # are not the same
        if initial is not None:
            initial = bool(initial)
        if data is not None:
            data = bool(data)
        return initial != data

class ModelSelectWithAdminLink(forms.Select):
    def __init__(self, admin_url_name=None):
        self.admin_url_name = admin_url_name
        super(ModelSelectWithAdminLink, self).__init__()

    def render(self, *args, **kwargs):
        return mark_safe("%s <a href='%s'>Edit choices</a>" % (
            super(ModelSelectWithAdminLink, self).render(*args, **kwargs),
            reverse(self.admin_url_name)
        ))

#
# Forms
#

class USPSSelectWithEmpty(USPSSelect):
    def __init__(self, *args, **kwargs):
        super(USPSSelectWithEmpty, self).__init__(*args, **kwargs)
        self.choices.insert(0, ('', '-------'))

class ContactSearch(forms.Form):
    # Hidden fields for other searches.
    contact_id = forms.CharField(widget=forms.HiddenInput, required=False)
    donor_batch_id = forms.CharField(widget=forms.HiddenInput, required=False)

    # Name / details
    name = forms.CharField(required=False)
    first_name = forms.CharField(required=False)
    middle_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    prisoner_number = forms.CharField(required=False)
    email = forms.CharField(required=False)
    has_been_censored = forms.NullBooleanField(required=False, widget=BlankNullBooleanSelect)
    source = forms.ChoiceField(null_model_choices(ContactSource), required=False)
    source_category = forms.ChoiceField(null_model_choices(ContactSourceCategory),
            required=False)
    deceased = forms.NullBooleanField(required=False, widget=BlankNullBooleanSelect)
            
    # Address
    search_addresses_current_on_date = forms.CharField(required=False)
    state = forms.CharField(widget=USPSSelectWithEmpty(), required=False)
    zip = forms.CharField(max_length=10, required=False)
    contact_type = forms.ChoiceField(
            choices=[('', '--------')] + list(
                Contact._meta.get_field_by_name('type')[0].choices
            ),
            required=False)
    prison = forms.ModelChoiceField(
            queryset=Prison.objects.all(),
            widget=forms.TextInput(),
            required=False)
    prison_type = forms.ChoiceField(
            null_model_choices(PrisonType), required=False)
    prison_administrator = forms.ChoiceField(
            null_model_choices(PrisonAdminType), required=False)
    lost_contact = forms.NullBooleanField(required=False, widget=BlankNullBooleanSelect)

    # Subscription
    is_donor = forms.NullBooleanField(required=False, widget=BlankNullBooleanSelect)
    currently_subscribing = forms.NullBooleanField(required=False,
            widget=BlankNullBooleanSelect)
    with_perpetual_subscriptions = forms.NullBooleanField(required=False,
            widget=BlankNullBooleanSelect)
    subscription_source = forms.ChoiceField(null_model_choices(SubscriptionSource),
            required=False)

    sort = forms.ChoiceField((
        ("last_name", "Last Name"),
        ("join_date", "Date Joined"),
        #("issues_remaining", "Issues Remaining"), # Removed for poor performance
    ), required=False)

    exclude_missing_names = forms.BooleanField(required=False)
    exclude_addressless = forms.BooleanField(required=False)

    def constrain(self, contacts):
        if self.is_valid():
            cd = self.cleaned_data
            # Hidden fields
            if cd['contact_id'] != '':
                contacts = contacts.filter(pk=cd['contact_id'])
            if cd['donor_batch_id'] != '':
                contacts = contacts.filter(donorbatch__id=cd['donor_batch_id'])

            # Name and details
            if cd['name'] != '':
                words = [a.strip() for a in cd['name'].split(' ')]
                for word in words:
                    contacts = contacts.filter(
                            Q(first_name__icontains=word) |
                            Q(middle_name__icontains=word) |
                            Q(last_name__icontains=word) |
                            Q(organization_name__icontains=word) |
                            Q(email__icontains=word))
            if cd['first_name'] != '':
                contacts = contacts.filter(first_name__icontains=cd['first_name'])
            if cd['middle_name'] != '':
                contacts = contacts.filter(middle_name__icontains=cd['middle_name'])
            if cd['last_name'] != '':
                contacts = contacts.filter(last_name__icontains=cd['last_name'])
            if cd['prisoner_number'] != '':
                contacts = contacts.filter(
                        prisoneraddress__prisoner_number__icontains=cd['prisoner_number'])
            if cd['email'] != '':
                contacts = contacts.filter(email__icontains=cd['email'])
            if cd['has_been_censored'] is not None:
                if cd['has_been_censored']:
                    contacts = contacts.filter(mailing__censored=True)
                else:
                    contacts = contacts.exclude(mailing__censored=True)
            if cd['contact_type'] != '':
                contacts = contacts.filter(type=cd['contact_type'])
            if cd['source'] != '':
                if cd['source'] == "None":
                    contacts = contacts.filter(source__isnull=True)
                else:
                    contacts = contacts.filter(source_id=cd['source'])
            if cd['source_category'] != '':
                if cd['source_category'] == "None":
                    contacts = contacts.filter(source__category__isnull=True)
                else:
                    contacts = contacts.filter(source__category_id=cd['source_category'])
            if cd['deceased'] is not None:
                contacts = contacts.filter(deceased=cd['deceased'])

            # Addresses
            address_filter = Q()
            if cd['state'] != '':
                address_filter &= Q(address__state=cd['state']) | \
                          Q(prisoneraddress__prison__address__state=cd['state'])
            if cd['zip'] != '':
                zipcode = cd['zip'].strip()
                address_filter &= Q(address__zip__icontains=zipcode) | \
                      Q(prisoneraddress__prison__address__zip__icontains=zipcode)
            if cd['prison'] is not None:
                address_filter &= Q(prisoneraddress__prison=cd['prison'])
            if cd['prison_type'] != '':
                if cd['prison_type'] == 'None':
                    address_filter &= Q(prisoneraddress__isnull=False,
                            prisoneraddress__prison__type__isnull=True)
                else:
                    address_filter &= Q(prisoneraddress__prison__type_id=cd['prison_type'])
            if cd['prison_administrator'] != '':
                if cd['prison_administrator'] == 'None':
                    address_filter &= Q(prisoneraddress__isnull=False,
                            prisoneraddress__prison__admin_type__isnull=True)
                else:
                    address_filter &= Q(prisoneraddress__prison__admin_type_id=cd['prison_administrator'])
            if address_filter and cd['search_addresses_current_on_date'] != '':
                date = cd['search_addresses_current_on_date']
                if re.match('\d{4}-\d\d-\d\d', date):
                    address_filter &= Q(prisoneraddress__start_date__lte=date) & (
                            Q(prisoneraddress__end_date__isnull=True) |
                            Q(prisoneraddress__end_date__gte=date)
                    )
            contacts = contacts.filter(address_filter)
            if cd['lost_contact'] is not None:
                contacts = contacts.filter(lost_contact=cd['lost_contact'])

            # Subscription
            if cd['currently_subscribing'] is not None:
                if cd['currently_subscribing']:

                    contacts = contacts.filter(
                        Q(subscription__end_date__gte=now()) | 
                        Q(subscription__end_date__isnull=True),
                        subscription__start_date__lte=now()
                    )
                else:
                    contacts = contacts.filter(
                        Q(subscription__isnull=True) |
                        (Q(subscription__end_date__isnull=False) &
                         Q(subscription__end_date__lte=now()))
                    )

            if cd['is_donor'] is not None:
                if cd['is_donor']:
                    contacts = contacts.filter(donor=True)
                else:
                    contacts = contacts.filter(donor=False)
            if cd['subscription_source'] != '':
                if cd['subscription_source'] == "None":
                    contacts = contacts.filter(subscription__source__isnull=True)
                else:
                    contacts = contacts.filter(
                            subscription__source_id=cd['subscription_source'])
            if cd['exclude_addressless']:
                contacts = contacts.exclude(address__isnull=True,
                        prisoneraddress__isnull=True)
            if cd.get('exclude_missing_names', False):
                contacts = contacts.exclude(
                        first_name='', middle_name='', last_name='',
                        organization_name='')
            if cd['with_perpetual_subscriptions'] is not None:
                if cd['with_perpetual_subscriptions']:
                    contacts = contacts.filter(subscription__end_date__isnull=True)
                else:
                    contacts = contacts.exclude(subscription__end_date__isnull=True)
            contacts = contacts.distinct()
            if cd.get('sort', 'last_name') == 'last_name':
                contacts = contacts.order_by("last_name", "organization_name")
            elif cd['sort'] == "join_date":
                contacts = contacts.order_by("created")
            elif cd['sort'] == "issues_remaining":
                # This is hideously non-performant. Need a better strategy to
                # support this sort.
                contacts = contacts.annotate(
                    max_end_date=Max("subscription__end_date")
                ).order_by("-max_end_date")
            return contacts
        else:
            raise Exception("Constraining on invalid form.")

class ContactAddForm(forms.ModelForm):
    source = forms.ModelChoiceField(
            queryset=ContactSource.objects.all(),
            widget=ModelSelectWithAdminLink("admin:subscribers_contactsource_changelist")
    )
    class Meta:
        model = Contact
        exclude = ['address', 'created']

class PrisonerAddressForm(forms.ModelForm):
    prison = forms.ModelChoiceField(
            queryset=Prison.objects.all(),
            widget=forms.TextInput,
    )
    def create_for(self, contact):
        if self.is_valid():
            return PrisonerAddress.objects.create(
                    contact=contact,
                    prisoner_number=self.cleaned_data['prisoner_number'].lstrip('#'),
                    unit=self.cleaned_data['unit'],
                    prison=self.cleaned_data['prison'],
            )
        else:
            raise ValidationError

    class Meta:
        model = PrisonerAddress
        exclude = ['contact', 'start_date', 'end_date']

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address

class SubscriptionForm(forms.Form):
    start_date = forms.DateTimeField()
    type = forms.ChoiceField(choices=(('trial', 'Trial'), ('subscription', 'Subscription')))
    source = forms.ModelChoiceField(
            queryset=SubscriptionSource.objects.all(),
            widget=ModelSelectWithAdminLink("admin:subscribers_subscriptionsource_changelist")
    )
    number_of_months = forms.IntegerField(help_text="e.g. 1, 3, 12, 24.<br />Enter &ldquo;-1&rdquo; for a perpetual subscription.")
    payer = forms.ModelChoiceField(
        widget=forms.TextInput,
        queryset=Contact.objects.all(),
        help_text="Leave blank if self-paying",
        required=False
    )

    def create_for(self, contact):
        if self.is_valid():
            num_months = self.cleaned_data['number_of_months']
            start_date = self.cleaned_data['start_date']
            end_date = start_date
            while num_months > 0:
                end_date = end_date + datetime.timedelta(days=32)
                end_date = datetime.datetime(
                        end_date.year, end_date.month, start_date.day, 0, 0, 0, 0, utc)
                num_months -= 1
            return Subscription.objects.create(
                    payer=self.cleaned_data['payer'] or contact,
                    source=self.cleaned_data['source'],
                    contact=contact,
                    start_date=start_date,
                    end_date=end_date,
                    type=self.cleaned_data['type'],
            )
        else:
            raise ValidationError

class StopReasonForm(forms.Form):
    reason = forms.ModelChoiceField(
            queryset=SubscriptionStopReason.objects.all(),
            widget=ModelSelectWithAdminLink(
                "admin:subscribers_subscriptionstopreason_changelist"),
    )

class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue

class SharingBatchForm(forms.ModelForm):
    partner = forms.ModelChoiceField(
            queryset=SharingPartner.objects.all(),
            widget=ModelSelectWithAdminLink("admin:subscribers_sharingpartner_changelist")
    )
    class Meta:
        model = SharingBatch
        exclude = ['contacts', 'date']

class InquiryForm(forms.ModelForm):
    request_type = forms.ModelChoiceField(
            queryset=InquiryType.objects.order_by('description'),
            widget=ModelSelectWithAdminLink("admin:subscribers_inquirytype_changelist")
    )
    response_type = forms.ModelChoiceField(
            queryset=InquiryResponseType.objects.order_by('description'),
            widget=ModelSelectWithAdminLink("admin:subscribers_inquiryresponsetype_changelist")
    )
    class Meta:
        model = Inquiry
        exclude = ['date', 'batch', 'contact']

class MailingStayForm(forms.ModelForm):
    class Meta:
        model = MailingStay
        exclude = ['contact']

class MailingForm(forms.ModelForm):
    class Meta:
        model = Mailing
        exclude = ['contact', 'created', 'inquiry', 'censored',
                   'notes', 'sent', 'custom_text']
