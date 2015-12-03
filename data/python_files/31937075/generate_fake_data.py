import os
import csv
import random
import datetime

from django.core.management.base import BaseCommand
from django.utils.timezone import now, utc
from django.db import transaction

from subscribers.utils import UnicodeReader, localtime
from subscribers.models import Prison, Address, Contact, PrisonerAddress, Subscription, Issue, Mailing, MailingBatch, PrisonAdminType, ContactSource, SubscriptionSource

FAKE_DATA = os.path.join(os.path.dirname(__file__), "_fake_data.csv")


class FakeDataRow(object):
    # Data obtained from http://www.fakenamegenerator.com/
    fields = [ 'number', 'gender', 'first', 'middle', 'last', 'street', 'city', 'state', 'zip', 'country', 'email', 'password', 'telephone', 'mother', 'birthday', 'cctype', 'ccnumber', 'cvv2', 'ccexpires', 'nationalid', 'ups', 'occupation', 'company', 'domain', 'bloodtype', 'pounds', 'kilograms', 'feetinches', 'centimeters', 'guid', 'latitude', 'longitude']

    def __init__(self, row):
        for field, value in zip(self.fields, row):
            setattr(self, field, value)
        self.gender = self.gender[0].upper()

class Command(BaseCommand):
    def handle(self, *args, **options):
        with transaction.commit_manually():
            self.generate_data()
            transaction.commit()

    def generate_data(self):
        fh = open(FAKE_DATA)
        reader = UnicodeReader(fh)
        rowiter = iter(reader)
        rowiter.next() # skip header

        contact_sources = list(ContactSource.objects.all())
        contact_sources.append(None)
        subscription_sources = list(SubscriptionSource.objects.all())
        subscription_sources.append(None)

        # Prison Admin types
        admin_types = [
                PrisonAdminType.objects.create(
                    name="Bureau of Prisons",
                    short_name="BoP"),
                PrisonAdminType.objects.create(
                    name="Corrections Corporation of America",
                    short_name="CCA"),
                PrisonAdminType.objects.create(
                    name="GEO Group, Inc.",
                    short_name="GEO"),
                None,
        ]
        
        # Prisons: 100
        print "Generating prisons..."
        for i in range(100):
            fdr = FakeDataRow(rowiter.next())
            address = Address.objects.create(
                address1=fdr.street,
                city=fdr.city,
                state=fdr.state,
                zip=fdr.zip,
            )
            prison = Prison.objects.create(
                name="Fake prison %i" % i,
                admin_type=random.choice(("federal", "state", "jail")),
                type=random.choice(("prison", "work_release", "jail", "military", "juvenile")),
                address=address,
                admin_types=random.choice(admin_types),
            )
            # Subscribers in prison: 10 each
            for j in range(10):
                person = FakeDataRow(rowiter.next())
                contact = Contact.objects.create(
                    first_name=person.first,
                    middle_name=person.middle,
                    last_name=person.last,
                    gender=person.gender,
                    type='prisoner',
                    source=random.choice(contact_sources)
                )
                PrisonerAddress.objects.create(
                    contact=contact,
                    prisoner_number="#%08x" % random.randint(0, 0xffffffff),
                    start_date=(
                        now() - 
                        datetime.timedelta(days=random.randint(100, 5000))
                    ),
                    unit=random.choice(("up-C1", "down C2", "SEG3", "", "", "", "")),
                    prison=prison,
                )

        # People who have been moved around a bit: 10
        contacts = Contact.objects.filter(
                prisonaddress__start_date__lte=now() - datetime.timedelta(days=1000)
        ).order_by('?')
        for contact in contacts[:10]:
            # Change every year, until we're close to present.
            end_date = contact.current_prisonaddress().start_date + \
                        datetime.timedelta(days=365)
            while end_date < now():
                paddy = contact.current_prisonaddress()
                paddy.end_date = end_date
                paddy.save()
                PrisonerAddress.objects.create(
                    contact=contact,
                    start_date=paddy.end_date,
                    unit=paddy.unit,
                    prison=Prison.objects.exclude(pk=paddy.prison.pk).order_by('?')[0]
                )
                end_date += datetime.timedelta(days=365)

        # Other subscribers: 100 of each type.
        print "Generating contacts..."
        for contact_type in ('individual', 'entity', 'advertiser', 'fop'):
            print "  ", contact_type
            for i in range(100):
                fdr = FakeDataRow(rowiter.next())
                if random.random() < 0.1:
                    organization = "Fake Org %i" % i
                    gender = fdr.gender
                else:
                    organization = ""
                    gender = fdr.gender 

                contact = Contact.objects.create(
                    organization_name=organization,
                    first_name=fdr.first,
                    middle_name=fdr.middle,
                    last_name=fdr.last,
                    gender=gender,
                    type=contact_type,
                    opt_out=random.random() < 0.1,
                    address=Address.objects.create(
                        address1=fdr.street,
                        city=fdr.city,
                        state=fdr.state,
                        zip=fdr.zip,
                    ),
                    donor=random.random() < 0.25,
                )

        # Subscriptions: 50% of users.
        print "Generating subscriptions..."
        for contact in Contact.objects.all():
            if random.random() < 0.5:
                start = now() - datetime.timedelta(
                        days=random.randint(0, 1000)
                )
                # 10% of subscribers have a different payer.
                if random.random() < 0.1:
                    sources = list(Contact.objects.exclude(type="prisoner"))
                    if sources:
                        payer = random.choice(sources)
                    else:
                        payer = contact
                else:
                    payer = contact
                Subscription.objects.create(
                        payer=payer,
                        contact=contact,
                        start_date=start,
                        end_date=start + datetime.timedelta(days=365),
                        type='subscription',
                        source=random.choice(subscription_sources),
                )
        # Resubscriptions: 50% of possible.
        print "Generating re-subscriptions..."
        for contact in Contact.objects.filter(subscription__isnull=False).exclude(
                                              subscription__end_date__gte=now()):
            if random.random() < 0.5:
                last_sub = contact.subscription_set.order_by('-end_date')[0]
                if last_sub.end_date < now():
                    start = now() - datetime.timedelta(
                            days=random.randint(0, (now() - last_sub.end_date).days)
                    )
                else:
                    start = last_sub.end_date
                Subscription.objects.create(
                        payer=last_sub.payer,
                        contact=contact,
                        start_date=start,
                        end_date=start + datetime.timedelta(days=365),
                        type='subscription',
                )

        # Trials: 10.
        print "Generating trials..."
        for contact in Contact.objects.filter(subscription__isnull=True):
            Subscription.objects.create(
                    contact=contact,
                    payer=contact,
                    start_date=now() - datetime.timedelta(days=15),
                    end_date=now() + datetime.timedelta(days=16),
                    type='trial',
            )

        # Mailings on the first of every month.
        issue_date = Subscription.objects.order_by('start_date')[0].start_date
        print "Generating mailings..."
        n = 1
        while True:
            print " ", issue_date
            # Overshoot the month, then correct.
            issue_date += datetime.timedelta(days=32)
            issue_date = localtime(issue_date.year, issue_date.month, 1, 0, 0, 0)
            issue = Issue.objects.create(
                    number=n,
                    date=issue_date
            )
            n += 1
            recipients = Contact.objects.filter(subscription__start_date__lte=issue_date,
                                                subscription__end_date__gte=issue_date)

            batches = {}
            for mtype in ('issue', 'zero_left', 'one_left', 'two_left'):
                batches[mtype] = MailingBatch.objects.create(date=issue.date, issue=issue)
            for contact in recipients:
                batches['issue'].mailing_set.add(Mailing.objects.create(
                        type='issue',
                        issue=issue,
                        contact=contact,
                        date=issue.date,
                ))
                remaining_types = ['', 'zero_left', 'one_left', 'two_left']
                remaining = contact.issues_remaining(issue.date)
                if 0 < remaining <= 3:
                    mtype = remaining_types[remaining]
                    batches[mtype].mailing_set.add(Mailing.objects.create(
                            type=mtype,
                            issue=issue,
                            contact=contact,
                    ))

            if issue_date > now():
                break

        # Censored: 1%
        print "Marking censored..."
        for mailing in Mailing.objects.all():
            if random.random() < 0.01:
                mailing.censored = True
                mailing.save()

        print "Marking deceased and lost contact..."
        for contact in Contact.objects.all():
            rand = random.random()
            # Deceased: 1%.
            if rand < 0.01:
                contact.deceased = True
                contact.save()
            # lost contact: 5%
            elif rand < 0.05:
                contact.lost_contact = True
                contact.save()

        fh.close()
