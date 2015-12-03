import json
import urllib
import datetime
from collections import defaultdict, OrderedDict
from cStringIO import StringIO

from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.timezone import now, make_aware, utc
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.utils.html import linebreaks

from subscribers.models import *
from subscribers import forms
from subscribers.utils import UnicodeWriter, contact_csv_response, \
        contact_pdf_response
from subscribers import mail_rules, inquiry_response_actions
        
CONTACT_SEARCH_DEFAULTS = {
    'deceased': False,
    'lost_contact': False,
    "sort": "last_name",
    'exclude_missing_names': True,
    'exclude_addressless': True,
    'search_addresses_current_on_date': now().strftime("%Y-%m-%d"),
}


def _paginate(request, object_list, per_page=50):
    paginator = Paginator(object_list, per_page)
    try:
        paged = paginator.page(request.GET.get('page'))
    except PageNotAnInteger:
        paged = paginator.page(1)
    except EmptyPage:
        paged = paginator.page(paginator.num_pages)

    queryargs = {}
    for key in request.GET:
        queryargs[key] = request.GET.get(key)
    queryargs.pop('page', None)
    if queryargs:
        querystr = '?%s&' % urllib.urlencode(queryargs)
    else:
        querystr = '?'
    paged.querystr = querystr
    show_numbers = sorted(list(set(
        range(1, min(6, paginator.num_pages + 1)) +
        range(max(1, paged.number - 3), min(paged.number + 3, paginator.num_pages + 1)) +
        range(max(1, paginator.num_pages - 5), paginator.num_pages + 1)
    )))
    pageiter = []
    prev = 0
    for number in show_numbers:
        if number != prev + 1:
            pageiter.append(("", "..."))
        pageiter.append((True, number))
        prev = number

    paged.pageiter = pageiter

    return paged

def _date_aggregate(queryset, date_field, precision='week'):
    return queryset.extra(
            select={precision: """DATE_TRUNC('%s', %s)""" % (precision, date_field)}
        ).values(
            precision
        ).annotate(count=Count('pk')).order_by(precision)

#
# Contacts
#

@login_required
def contacts(request):
    form_params = {}
    form_params.update(CONTACT_SEARCH_DEFAULTS)
    for key in request.GET:
        form_params[key] = request.GET.get(key)
    form = forms.ContactSearch(form_params)
    contacts = Contact.objects.all().order_by('last_name').select_related('address')
    if form.is_valid():
        contacts = form.constrain(contacts)
        if request.GET.get('csv', None):
            return contact_csv_response(contacts)
        if request.GET.get('pdf', None):
            return contact_pdf_response(contacts)
    return render(request, "contacts/list.html", {
        'form': form,
        'contacts': _paginate(request, contacts.select_related("address").distinct()),
    })

@login_required
@transaction.commit_on_success
def show_contact(request, contact_id):
    contact = get_object_or_404(Contact, pk=contact_id)
    #
    # Bind forms to POST only if the appropriate submit button was pressed.
    #
    if request.POST.get("edit_contact", None):
        contact_form = forms.ContactAddForm(request.POST, instance=contact)
        address_form = forms.AddressForm(request.POST, instance=contact.address)
    else:
        contact_form = forms.ContactAddForm(None, instance=contact)
        address_form = forms.AddressForm(None, instance=contact.address)
    if request.POST.get("add_prisonaddress", None):
        prisonaddress_form = forms.PrisonerAddressForm(request.POST)
    else:
        prisonaddress_form = forms.PrisonerAddressForm(None)
    if request.POST.get("add_subscription", None):
        subscription_form = forms.SubscriptionForm(request.POST)
    else:
        subscription_form = forms.SubscriptionForm(None)

    mailing_stay_instance = MailingStay(contact=contact)
    if request.POST.get("add_mailing_stay", None):
        mailing_stay_form = forms.MailingStayForm(request.POST, prefix="mailingstay",
                instance=mailing_stay_instance)
    else:
        mailing_stay_form = forms.MailingStayForm(None, prefix="mailingstay",
                instance=mailing_stay_instance)

    inquiry_instance = Inquiry(contact=contact)
    if request.POST.get("add_inquiry", None):
        inquiry_form = forms.InquiryForm(request.POST,
                instance=inquiry_instance)
    else:
        inquiry_form = forms.InquiryForm(None,
                instance=inquiry_instance)

    mailing_instance = Mailing(contact=contact)
    if request.POST.get("add_mailing", None):
        mailing_form = forms.MailingForm(request.POST,
                prefix="mailing", instance=mailing_instance)
    else:
        mailing_form = forms.MailingForm(None,
                prefix="mailing", instance=mailing_instance)

    #
    # Handle form posting.
    #

    if request.method == 'POST':
        right_now = now()
        if prisonaddress_form.is_valid():
            try:
                pad = contact.current_prisoner_address()
                pad.end_date = right_now
                pad.save()
            except PrisonerAddress.DoesNotExist:
                pass
            prisonaddress_form.create_for(contact)
            return redirect(request.path)
        if inquiry_form.is_valid():
            inquiry = inquiry_form.save()
            inquiry_response_actions.handle(inquiry)
            return redirect(request.path)
        if mailing_stay_form.is_valid():
            mailing_stay_form.save()
            return redirect(request.path)
        if subscription_form.is_valid():
            subscription_form.create_for(contact)
            return redirect(request.path)
        if mailing_form.is_valid():
            mailing = mailing_form.save()
            return redirect(request.path)
        if contact_form.is_valid():
            contact = contact_form.save()
            if contact.type == 'prisoner':
                contact.address = None
                contact.save()
            else:
                if address_form.is_valid():
                    contact.address = address_form.save()
                    contact.save()
            return redirect(request.path)


    return render(request, "contacts/show.html", {
        'contact': contact,
        'contact_form': contact_form,
        'address_form': address_form,
        'mailing_form': mailing_form,
        'prisonaddress_form': prisonaddress_form,
        'subscription_form': subscription_form,
        'inquiry_form': inquiry_form,
        'mailing_stay_form': mailing_stay_form,
        'payed_for': contact.subscriptions_payed_for.exclude(contact=contact),
    })

@login_required
def end_subscription_early(request, subscription_id):
    subscription = get_object_or_404(Subscription, pk=subscription_id)
    stop_form = forms.StopReasonForm(request.POST or None)
    if stop_form.is_valid():
        subscription.end_early(stop_form.cleaned_data['reason'])
        subscription.save()
        return redirect(subscription.contact.get_absolute_url())
    return render(request, "contacts/stop_subscription.html", {
        'subscription': subscription,
        'stop_form': stop_form,
        'now': now(),
    })

@login_required
def restart_subscription(request, subscription_id):
    if request.method == 'POST':
        subscription = get_object_or_404(Subscription, pk=subscription_id)
        subscription.end_date = subscription.original_end_date
        subscription.stop_reason = None
        subscription.save()
        return HttpResponse("success")
    return HttpResponseBadRequest()

@login_required
@transaction.commit_on_success
def add_contact(request):
    contact_form = forms.ContactAddForm(request.POST or None)
    address_form = forms.AddressForm(request.POST or None)
    prisonaddress_form = forms.PrisonerAddressForm(request.POST or None)
    # Hack to prevent making subscription_form 'bound' if fields are empty.
    sub_form_binding = None
    if request.method == 'POST':
        for field in ("start_date", "source", "number_of_months", "payer"):
            if request.POST.get("subscription-{0}".format(field)) != "":
                sub_form_binding = request.POST
                break
    subscription_form = forms.SubscriptionForm(sub_form_binding, prefix="subscription")
    if contact_form.is_valid() and \
            (prisonaddress_form.is_valid() or address_form.is_valid()) and \
            ((request.POST.get("subscription-start_date") == "" and
              request.POST.get("subscription-number_of_months") == "") or
             subscription_form.is_valid()):
        contact = contact_form.save()
        if prisonaddress_form.is_valid():
            # Easier to just manually create than bash the form in.
            prisonaddress_form.create_for(contact)
        elif address_form.is_valid():
            address = address_form.save()
            contact.address = address
            contact.save()
        if subscription_form.is_valid():
            subscription_form.create_for(contact)
        return redirect("subscribers.contacts.show", contact.pk)
    return render(request, "contacts/add.html", {
        'contact_form': contact_form,
        'address_form': address_form,
        'prisonaddress_form': prisonaddress_form,
        'subscription_form': subscription_form,
    })

@login_required
@transaction.commit_on_success
def inquiries(request):
    batches = InquiryBatch.objects.all()
    needed = Inquiry.objects.unmailed().select_related('contact', 'type')
    batch_form = forms.InquiryBatchForm(request.POST or None)

    if batch_form.is_valid():
        batch = batch_form.save()
        count = 0
        for inquiry in needed:
            inquiry.batch = batch
            inquiry.save()
            count += 1
        if count == 0:
            batch.delete()
        return redirect("subscribers.contacts.inquiries")
    return render(request, "contacts/inquiries.html", {
        'batches': batches,
        'needed': needed,
        'batch_form': batch_form,
    })

@permission_required("subscribers.delete_inquiry")
def delete_inquiry(request, inquiry_id):
    if request.method == 'POST':
        ir = get_object_or_404(Inquiry, pk=inquiry_id)
        url = ir.contact.get_absolute_url()
        ir.delete()
        return redirect(url)
    return HttpResponseBadRequest()

@login_required
def end_mailing_stay(request, mailingstay_id):
    if request.method == 'POST':
        ms = get_object_or_404(MailingStay, pk=mailingstay_id)
        ms.end_date = now()
        ms.save()
        return HttpResponse("success")
    return HttpResponseBadRequest()
    
@login_required
def donor_batches(request):
    batches = DonorBatch.objects.all()
    contacts = Contact.objects.filter(opt_out=False, donor=True)
    cutoff = (request.POST or request.GET).get("no_contact_since")
    if cutoff:
        contacts = contacts.filter(
                Q(donorbatch__isnull=True) | Q(donorbatch__date__lte=cutoff),
                donor=True,
        )
    if request.method == 'POST':
        if len(contacts) > 0:
            batch = DonorBatch.objects.create()
            batch.contacts = contacts
            batch.save()
        return redirect("subscribers.contacts.donor_batches")
    return render(request, "contacts/donor_batches.html", {
        "batches": batches,
        "contacts": contacts
    })

@login_required
def donor_batch_count(request):
    contacts = Contact.objects.filter(opt_out=False, donor=True)
    cutoff = (request.POST or request.GET).get("no_contact_since")
    if cutoff:
        contacts = contacts.filter(
                Q(donorbatch__isnull=True) | Q(donorbatch__date__lte=cutoff),
                donor=True,
        )
    response = HttpResponse(json.dumps({
        'count': contacts.count()
    }))
    response['Content-Type'] = 'application/json'
    return response

@login_required
def delete_donor_batch(request, donor_batch_id):
    if not request.user.has_perm("subscribers.delete_donorbatch"):
        raise PermissionDenied
    batch = get_object_or_404(DonorBatch, pk=donor_batch_id)
    batch.delete()
    return redirect("subscribers.contacts.donor_batches")

#
# Ajaxy
#

@login_required
def fuzzy_contact_search(request):
    first = request.GET.get('first')
    middle = request.GET.get('middle')
    last = request.GET.get('last')
    prisoner_number = request.GET.get('prisoner_number')
    if not any((first, middle, last, prisoner_number)):
        contacts = Contact.objects.none()
    else:
        if prisoner_number:
            num_contacts = Contact.objects.filter(
                prisonaddress__prisoner_number__icontains=prisoner_number)
        else:
            num_contacts = None
        if any((first, middle, last)):
            name_contacts = Contact.objects.similar_to(first, middle, last, 0.4)
        else:
            name_contacts = None

        # Combine the query sets.
        if num_contacts is not None and name_contacts is not None:
            keepers = set([c.id for c in num_contacts]) & set([c.id for c in name_contacts])
            all_contacts = dict((c.id, c) for c in num_contacts if c.id in keepers)
            all_contacts.update(dict((c.id, c) for c in name_contacts if c.id in keepers))
            contacts = all_contacts.values()
        else:
            contacts = num_contacts or name_contacts
        
    return render(request, "contacts/_fuzzy.html", {
        'contacts': contacts[0:6],
    })

@login_required
def json_contact_search(request):
    q = request.GET.get('q')
    contacts = Contact.objects.all()
    if q:
        for word in q.split():
            contacts = contacts.filter(
                    Q(first_name__icontains=word) |
                    Q(middle_name__icontains=word) |
                    Q(last_name__icontains=word) |
                    Q(organization_name__icontains=word)
            )
    # Can't use django's built-in pagination here, because similar_to returns
    # an immutable queryset.
    count = contacts.count()
    try:
        per_page = int(request.GET.get('per_page', 50))
    except ValueError:
        return HttpResponseBadRequest("Invalid per_page number.")
    try:
        requested_page = int(request.GET.get('page', 1))
        if requested_page < 1 or (requested_page - 1) * per_page > count:
            raise Http404
    except ValueError:
        return HttpResponseBadRequest("Invalid page number.")
    results = contacts[(requested_page - 1) * per_page : requested_page * per_page]
    response = HttpResponse(json.dumps({
            'results': [{'id': c.pk, 'text': unicode(c)} for c in results],
            'page': requested_page,
            'count': count,
    }, indent=4))
    response['Content-type'] = "application/json"
    return response

@login_required
def json_prison_search(request):
    q = request.GET.get('q')
    pk = request.GET.get('id')
    prisons = Prison.objects.all()
    if pk:
        prisons = prisons.filter(pk=pk)
    elif q:
        for word in q.split():
            prisons = prisons.filter(
                    Q(name__icontains=word) |
                    Q(admin_name__icontains=word) |
                    Q(address__address1__icontains=word) |
                    Q(address__address2__icontains=word) |
                    Q(address__city__icontains=word) |
                    Q(address__zip__icontains=word))
    count = prisons.count()
    try:
        per_page = int(request.GET.get('per_page', 50))
    except ValueError:
        return HttpResponseBadRequest("Invalid per_page number.")
    try:
        requested_page = int(request.GET.get('page', 1))
        if requested_page < 1 or (requested_page - 1) * per_page > count:
            raise Http404
    except ValueError:
        return HttpResponseBadRequest("Invalid page number.")
    results = prisons[(requested_page - 1) * per_page : requested_page * per_page]
    response = HttpResponse(json.dumps({
            'results': [{
                'id': p.pk,
                'text': p.format_list_display().replace("\n", "<br />"),
            } for p in results],
            'page': requested_page,
            'count': count,
    }, indent=4))
    response['Content-type'] = "application/json"
    return response

@login_required
def mark_censored(request, mailing_id):
    if request.method != 'POST':
        raise Http404
    mailing = get_object_or_404(Mailing, pk=mailing_id)
    mailing.censored = request.POST.get("censored") == 'on'
    mailing.save()
    return redirect("subscribers.contacts.show", mailing.contact.pk)

@login_required
def delete_prisonaddress(request, prisonaddress_id):
    if not request.user.has_perm("subscribers.delete_prisonaddress"):
        raise PermissionDenied
    if request.method == 'POST':
        get_object_or_404(PrisonerAddress, pk=prisonaddress_id).delete()
        return HttpResponse("success")
    return HttpResponseBadRequest("POST required")

@login_required
def delete_subscription(request, subscription_id):
    if not request.user.has_perm("subscribers.delete_subscription"):
        raise PermissionDenied
    if request.method == 'POST':
        get_object_or_404(Subscription, pk=subscription_id).delete()
        return HttpResponse("success")
    return HttpResponseBadRequest("POST required")

@login_required
def list_notes(request, contact_id, note_id=None, contact=None):
    contact = contact or get_object_or_404(Contact, pk=contact_id)
    if request.method == 'POST':
        if note_id:
            note = get_object_or_404(Note, pk=note_id)
        else:
            note = Note(contact=contact)
        note.author = request.user
        note.text = request.POST.get("text")
        note.save()
        
    notes = Note.objects.filter(contact=contact)
    return render(request, "_notes_list.html", {
        'contact': contact,
        'notes': notes
    })

@login_required
def delete_note(request, note_id=None):
    if not request.user.has_perm("subscribers.delete_note"):
        raise PermissionDenied
    note = get_object_or_404(Note, pk=note_id)
    note.delete()
    return HttpResponse("success")

#
# Mailings
#

@login_required
def mailings_sent(request):
    page = _paginate(request, MailingLog.objects.all())
    return render(request, "mailings/list_mailinglogs.html", {
        'page': page,
    })

@login_required
def show_mailinglog(request, mailinglog_id):
    log = get_object_or_404(MailingLog, id=mailinglog_id)
    contact_id_to_mailings = defaultdict(list)
    for mailing in log.mailings.all():
        contact_id_to_mailings[mailing.contact_id].append(mailing)
    recipients = Contact.objects.filter(mailing__mailinglog=log)
    search_form = forms.ContactSearch(request.GET or CONTACT_SEARCH_DEFAULTS)
    if search_form.is_valid():
        recipients = search_form.constrain(recipients)
    if request.GET.get("csv", False):
        return contact_csv_response(recipients)
    elif request.GET.get("pdf", False):
        return contact_pdf_response(recipients)
    return render(request, "mailings/show_mailinglog.html", {
        'log': log,
        'form': search_form,
        'contact_id_to_mailings': contact_id_to_mailings,
        'page': _paginate(request, recipients),
    })
    
@login_required
def delete_mailinglog(request, mailinglog_id):
    if not request.user.has_perm("subscribers.delete_mailinglog"):
        raise PermissionDenied
    if not request.method == 'POST':
        return HttpResponseBadRequest("POST required")
    log = get_object_or_404(MailingLog, id=mailinglog_id)
    log.mailings.all().update(sent=None)
    log.delete()
    return redirect("subscribers.mailinglogs.list")


@login_required
def mark_mailing_sent(request, mailing_id=None):
    if request.method == "POST":
        mailing = get_object_or_404(Mailing, id=mailing_id)
        mailing.sent = now()
        mailing.save()
        return HttpResponse("success")
    return HttpResponseBadRequest("POST required")

@login_required
@permission_required("subscribers.delete_mailing")
def delete_mailing(request, mailing_id=None):
    if request.method == "POST":
        mailing = get_object_or_404(Mailing, id=mailing_id)
        mailing.delete()
        return HttpResponse("success")
    return HttpResponseBadRequest("POST required")

@login_required
@transaction.commit_on_success
def mailings_needed(request, issue_id=None):
    """
    Handle listing and creation of 3 types of things:
     - Issues
     - Last issue notices
     - Info requests
    Each of these things generate a Mailing object, and this Mailing object
    gets attached to a MailingLog object when sent.

    Each item has 3 states:
     - needed: policy dictates it should exist, but there's no Mailing object.
     - enqueued: a Mailing object exists, but it's not sent.
     - sent: the Mailing object is marked sent.

    MailingLog objects act as a convenient interface by which to group Mailing
    objects for printing labels en masse.  However, it's not considered "sent"
    until the Mailing object has been marked "sent", regardless of belonging
    to a MailingLog object or not.
    """
    if issue_id:
        issue = get_object_or_404(Issue, pk=issue_id)
    else:
        issue = Issue.objects.latest('date')


    mailings = [
            {
                'name': unicode("Issue: %s" % issue),
                'needed': mail_rules.IssuesNeeded(issue),
                'unreachable': mail_rules.IssuesUnreachable(issue),
                'enqueued': mail_rules.IssuesEnqueued(issue),
                'sent': mail_rules.IssuesSent(issue),
            },
            {
                'name': unicode("0 issues left, recipient"),
                'needed': mail_rules.NoticeNeeded(0, "recipient"),
                'unreachable': mail_rules.NoticeUnreachable(0, "recipient"),
                'enqueued': mail_rules.NoticeEnqueued(0, "recipient"),
                'sent': mail_rules.NoticeSent(0, "recipient"),
            },
            {
                'name': unicode("1 issues left, recipient"),
                'needed': mail_rules.NoticeNeeded(1, "recipient"),
                'unreachable': mail_rules.NoticeUnreachable(1, "recipient"),
                'enqueued': mail_rules.NoticeEnqueued(1, "recipient"),
                'sent': mail_rules.NoticeSent(1, "recipient"),
            },
            {
                'name': unicode("2 issues left, recipient"),
                'needed': mail_rules.NoticeNeeded(2, "recipient"),
                'unreachable': mail_rules.NoticeUnreachable(2, "recipient"),
                'enqueued': mail_rules.NoticeEnqueued(2, "recipient"),
                'sent': mail_rules.NoticeSent(2, "recipient"),
            },
            {
                'name': unicode("0 issues left, payer"),
                'needed': mail_rules.NoticeNeeded(0, "payer"),
                'unreachable': mail_rules.NoticeUnreachable(0, "payer"),
                'enqueued': mail_rules.NoticeEnqueued(0, "payer"),
                'sent': mail_rules.NoticeSent(0, "payer"),
            },
            {
                'name': unicode("1 issues left, payer"),
                'needed': mail_rules.NoticeNeeded(1, "payer"),
                'unreachable': mail_rules.NoticeUnreachable(1, "payer"),
                'enqueued': mail_rules.NoticeEnqueued(1, "payer"),
                'sent': mail_rules.NoticeSent(1, "payer"),
            },
            {
                'name': unicode("2 issues left, payer"),
                'needed': mail_rules.NoticeNeeded(2, "payer"),
                'unreachable': mail_rules.NoticeUnreachable(2, "payer"),
                'enqueued': mail_rules.NoticeEnqueued(2, "payer"),
                'sent': mail_rules.NoticeSent(2, "payer"),
            },
            {
                'name': unicode("Inquiry Responses"),
                'needed': mail_rules.InquiryResponseNeeded(),
                'unreachable': mail_rules.InquiryResponseUnreachable(),
                'enqueued': mail_rules.InquiryResponseEnqueued(),
                'sent': mail_rules.InquiryResponseSent(),
            },
            {
                'name': unicode("Other enqueued mail"),
                'needed': mail_rules.EmptyRule(),
                'unreachable': mail_rules.EmptyRule(),
                'enqueued': mail_rules.OtherEnqueuedMail(issue),
                'sent': mail_rules.EmptyRule(),
            },
    ]


    # Try to resolve the list of whom to show.
    path = request.GET.get("path")
    if path:
        matched_mailing = None
        for mailing_group in mailings:
            for key in ("needed", "unreachable", "enqueued", "sent"):
                if path == mailing_group[key].code:
                    matched_mailing = mailing_group[key]
                    break
            else:
                continue
            break
        else:
            raise Http404
        if request.method == "POST":
            if request.POST.get("action") == matched_mailing.action:
                matched_mailing.transition(request.user)
                return redirect(request.path)
            else:
                return HttpResponseBadRequest("Unmatched action")
        if path.startswith("inquiry"):
            recipients = None
            inquiries = _paginate(request, matched_mailing.qs.order_by('-date'))
        else:
            recipients = matched_mailing.qs
            inquiries = None
            if request.GET.get("csv"):
                return contact_csv_response(recipients)
            elif request.GET.get("pdf"):
                return contact_pdf_response(recipients)
    else:
        matched_mailing = None
        recipients = None
        inquiries = None

    if recipients is not None:
        search_form_vars = {}
        search_form_vars.update(CONTACT_SEARCH_DEFAULTS)
        for key in request.GET:
            search_form_vars[key] = request.GET.get(key)
        contact_search_form = forms.ContactSearch(search_form_vars)
        recipients = contact_search_form.constrain(recipients)
        recipients = recipients.select_related('address')
        page = _paginate(request, recipients)
    else:
        contact_search_form = None
        page = None

    return render(request, "mailings/needed.html", {
        'issue': issue,
        'path': path,
        'mailings': mailings,
        'matched_mailing': matched_mailing,
        'inquiries': inquiries,
        'contact_search_form': contact_search_form,
        'page': page,
        'logs': MailingLog.objects.all().order_by('-created')[0:10],
    })

#
# Issues
#

@login_required
def show_issue(request, issue_id=None):
    issue = get_object_or_404(Issue, id=issue_id)
    paths = {
        'needed': Contact.objects.issue_needed(issue),
        'unreachable': Contact.objects.issue_unreachable(issue),
        'enqueued': Contact.objects.issue_enqueued(issue),
        'sent': Contact.objects.issue_sent(issue),
    }
    whats = {
            'needed': "Contacts who still need this issue",
            'unreachable': "Contacts who should receive this, but can't be reached",
            'enqueued': "Contacts with this issue enqueued",
            'sent': "Contacts who've been sent this issue",
    }
    path = request.GET.get('path')
    if path:
        recipients = paths[path]
        form_params = {}
        form_params.update(CONTACT_SEARCH_DEFAULTS)
        for key in request.GET:
            form_params[key] = request.GET.get(key)
        form = forms.ContactSearch(form_params)
        if recipients is not None and form.is_valid():
            recipients = form.constrain(recipients)
        page = _paginate(request, recipients.select_related('address'))
        what = whats[path]
    else:
        page = None
        form = None
        what = None
    return render(request, "issues/show.html", {
        'paths': paths,
        'path': path,
        'what': what,
        'issue': issue,
        'page': page,
        'form': form,
    })
    

@login_required
def list_issues(request):
    issues = Issue.objects.all()
    form = forms.IssueForm(request.POST or None)
    if form.is_valid():
        issue = form.save()
        return redirect(request.path)
    return render(request, "issues/list.html", {
        'issues': issues,
        'form': form,
    })

@login_required
def delete_issue(request, issue_id):
    if not request.user.has_perm("subscribers.delete_issue"):
        raise PermissionDenied
    issue = get_object_or_404(Issue, pk=issue_id)
    if request.method == 'POST':
        for mailing in issue.mailing_set.all():
            mailing.delete()
        issue.delete()
        return redirect("subscribers.issues")
    return HttpResponseBadRequest("POST required")

@login_required
def mailinglog_csv(request, mailinglog_id):
    contacts = list(
            Contact.objects.filter(mailing__mailinglog_id=mailinglog_id)
    )
    if len(contacts) == 0:
        raise Http404
    return contact_csv_response(contacts)

@login_required
def mailinglog_pdf(request, mailinglog_id):
    contacts = list(
            Contact.objects.filter(mailing__mailinglog_id=mailinglog_id)
    )
    if len(contacts) == 0:
        raise Http404
    return contact_pdf_response(contacts)

@login_required
def stats(request):
    return redirect("subscribers.stats.subscriptions")

@login_required
def stats_map(request):
    # Map of where folks are from
    contacts = Contact.objects.all()
    form = forms.ContactSearch(request.GET or CONTACT_SEARCH_DEFAULTS)
    if form.is_valid():
        contacts = form.constrain(contacts)

    state_counts = defaultdict(int)

    when = form.cleaned_data.get('search_addresses_current_on_date')
    if when:
        pads = PrisonerAddress.objects.filter(
                Q(end_date__isnull=True) | Q(end_date__gte=when),
                start_date__lte=when,
        )
    else:
        pads = PrisonerAddress.objects.all()

    # Get the counts for those that have prison addresses.
    pad_havers = contacts.filter(address__isnull=True).values_list('id', flat=True)
    for pad in pads.select_related('prison', 'prison__address').filter(
            contact_id__in=pad_havers).distinct():
        if pad.prison.address.state:
            state_counts[pad.prison.address.state] += 1
    # Get the counts for those that have non-prison addresses.
    for contact in contacts.select_related('address').filter(
            address__isnull=False, prisoneraddress__isnull=True):
        if contact.address.state:
            state_counts[contact.address.state] += 1
        else:
            state_counts['international'] += 1

    # Pagination of all contacts.
    page = _paginate(request, contacts)
    return render(request, "stats/map.html", {
        'form': form,
        'state_counts': json.dumps(state_counts),
        'page': page,
    })


@login_required
def stats_subscriptions(request):
    contact_types = Contact.objects.order_by().values_list('type', flat=True).distinct()
    sub_types = Subscription.objects.order_by().values_list('type', flat=True).distinct()
    out = {
        'label': [],
        'color': [
            #'rgb(47, 48, 48)', 'rgb(67, 68, 68, 1.0)',
            '#2f3030', '#434444',
            #'rgb(10, 99, 61)', 'rgb(40, 129, 91, 1.0)',
            '#0a633d', '#28815B',
            #'rgb(21, 202, 177)', 'rgb(51, 232, 207, 1.0)',
            '#15cab1', '#33e8cf',
            #'rgb(250, 159, 41)', 'rgb(255, 189, 71, 1.0)',
            '#fa9f29', '#ffbd47',
            #'rgb(120, 16, 17)', 'rgb(150, 46, 47, 1.0)',
            '#781011', '#962e2f',
        ],
        'values': [],
    }
    type_index = defaultdict(dict)
    for ctype in contact_types:
        for stype in sub_types:
            type_index[ctype][stype] = len(out['label'])
            out['label'].append("%s: %s" % (ctype, stype))
    
    # Get start and end, truncated to month.
    start = Issue.objects.order_by('date')[0].date
    start = datetime.datetime(start.year, start.month, 1, 0, 0, 0, 0, utc)
    end = now()
    end = datetime.datetime(end.year, end.month, 1, 0, 0, 0, 0, utc)

    time_cutoffs = {}
    cur = start
    label_count = 0
    while cur < end:
        cur = datetime.datetime(cur.year, cur.month, 1, 0, 0, 0, 0, utc)
        label = "%s-%s" % (cur.year, cur.month)
        #if label_count % 4 != 0:
        #    label = "."
        label_count += 1
        values_list = [0 for i in range(len(type_index))]
        out['values'].append({
            'label': label,
            'values': values_list
        })
        time_cutoffs[cur] = values_list
        cur += datetime.timedelta(days=31)

    # Massively more performant to do this raw query.
    subs = Subscription.objects.raw("""
        SELECT s.id,
               date_trunc('month', s.start_date) AS start_date,
               date_trunc('month', coalesce(s.end_date, current_date)) AS end_date,
               s.type AS type,
               c.type AS contact_type
           FROM subscribers_subscription s
           LEFT OUTER JOIN subscribers_contact c ON (s.contact_id = c.id)
    """)

    for sub in subs:
        sub_start = max(sub.start_date, start)
        sub_end = min(sub.end_date, end)
        cur = sub_start
        while cur < sub_end:
            time_cutoffs[cur][type_index[sub.contact_type][sub.type]] += 1
            # Add next month, and normalize to beginning.
            cur += datetime.timedelta(days=31)
            cur = datetime.datetime(cur.year, cur.month, 1, 0, 0, 0, 0, utc)

    return render(request, "stats/subscriptions.html", {
        'data': json.dumps(out)
    })

@login_required
def sharingbatch_count(request):
    partner = get_object_or_404(SharingPartner, pk=request.GET.get("partner_id"))
    response = HttpResponse(json.dumps({
        'count': Contact.objects.shareable_with(partner).count()
    }))
    response['Content-Type'] = 'application/json'
    return response

@login_required
def download_sharingbatch(request, sharingbatch_id, filetype):
    batch = get_object_or_404(SharingBatch, pk=sharingbatch_id)
    if filetype == "csv":
        return contact_csv_response(batch.contacts.all())
    elif filetype == "pdf":
        return contact_pdf_response(batch.contacts.all())
    else:
        raise Http404

@login_required
def delete_sharingbatch(request, sharingbatch_id):
    if not request.user.has_perm("subscribers.delete_sharingbatch"):
        raise PermissionDenied
    batch = get_object_or_404(SharingBatch, pk=sharingbatch_id)
    batch.delete()
    return redirect("subscribers.sharing")

@login_required
def sharing(request):
    form = forms.SharingBatchForm(request.POST or None)
    if form.is_valid():
        contacts = list(Contact.objects.shareable_with(form.cleaned_data['partner']))
        if len(contacts) > 0:
            batch = SharingBatch()
            batch.partner = form.cleaned_data['partner']
            batch.save()
            batch.contacts = contacts
            return redirect(request.path)
        else:
            form.errors['partner'] = [
                "There are no shareable contacts we haven't yet shared with this partner."
            ]

    return render(request, "sharing/share.html", {
        'form': form,
        'batches': SharingBatch.objects.all()
    })


