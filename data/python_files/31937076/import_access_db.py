import os
import re
import json
import codecs
import xmltodict
import unicodedata
from collections import defaultdict
from collections import Counter
from pprint import pprint
from django.db import transaction
from django.utils.timezone import now, utc
from .update_autoinc_indexes import commit_sql_sequence_reset

from django.core.management.base import BaseCommand

from subscribers.models import *

# Regular expression to match control characters.
# See http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
# Control chars: the all ascii codes from 0 to 160 other than tab, newlines,
# and printable characters.
control_char_codes = set(range(0, 160)) ^ set([9, 10, 13] + range(32, 127))
control_chars = ''.join(map(unichr, control_char_codes))
control_chars_re = re.compile('([%s])' % re.escape(control_chars))

def prettyprint(dct):
    print(json.dumps(dct, indent=2))

def null_boolify(obj, key):
    if key in obj:
        if obj[key] == '1':
            return True
        elif obj[key] == '0':
            return False
    return None

def xmliter(xmldir):
    for filename in os.listdir(xmldir):
        if not filename.endswith(".xml"):
            continue
        yield os.path.join(xmldir, filename)

def corruption_hunt(xmldir):
    for path in xmliter(xmldir):
        with codecs.open(path, 'rU', 'utf-8') as fh:
            for i,line in enumerate(fh):
                match = control_chars_re.search(line)
                if match:
                    print "Control char found in:", os.path.basename(path), "line", i + 1
                    print line.strip()
                    print match.groups()
                    print "Cleaned:"
                    print control_chars_re.sub('', line)
                    print
                    break

def clean_and_parse_xml(xmlpath):
    with codecs.open(xmlpath, 'rU', 'utf-8') as fh:
        orig = fh.read()
        cleaned = control_chars_re.sub('', orig)
        if len(orig) != len(cleaned):
            print "Stripped {0} corrupted characters from {1}".format(
                    len(orig) - len(cleaned), os.path.basename(xmlpath))
    return xmltodict.parse(cleaned.encode('utf-8'))

def convert_xml_to_dct(xml_path):
    """
    Convert all the XML files using xmltodict, and remove any corrupted
    characters encountered along the way.
    """
    json_path = os.path.splitext(xml_path)[0] + ".json"
    if os.path.exists(json_path):
        with open(json_path) as fh:
            return json.load(fh)

    print "converting", os.path.basename(xml_path)
    dct = clean_and_parse_xml(xml_path)
    with open(json_path, 'w') as fh:
        json.dump(dct, fh)
    return dct

def resolve_keys(data):
    """
    Reorganize the XML data so that it is a mapping of primary key (as a
    string) to record, rather than a list of records.  Next, replace all
    foreign keys with references to the relevant data, to ease the import
    process.
    """

    # Arrange by primary key.
    by_pk = defaultdict(dict)
    fail = False
    for table, records in data.iteritems():
        try:
            records[0]
        except KeyError:
            records = [records]
        first = records[0]
        if table == "taDonation":
            ids = ["DonationID"]
        else:
            ids = [k for k in first if k.endswith("ID")]
        if len(ids) == 0:
            for i, record in enumerate(records):
                by_pk[table][str(i)] = record
        elif len(ids) == 1:
            pk = ids[0]
            for record in records:
                by_pk[table][record[pk]] = record
        else:
            fail = True
            print "Multiple ID fields found for {}: {}".format(table, ids)

        # Verify that all IDs are unique.
        if len(by_pk[table]) != len(records):
            fail = True
            dups = [(k, v) for k in Counter(r[ids[0]] for r in records).iteritems() if v > 1]

            print "Duplicate IDs found: {}".format(
                    ", ".join("{0} ({1})".format(k, v) for k, v in dups))

    assert not fail

    # Specific foreign key mappings...
    table_foreign_key_map = {
        "taDonation": { "fkReason": "tlDonationPurpose" },
        "taPrisonAdmin": { "fkType": "tlFacilityType" },
        "taSubscriber": {"fkSource": "tlSource" },
        "taInquiry": {"fkResponseType": "tlInquiryResponseSpecific",
                      "fkType": "tlInquiryTypeSpecific"},
        "taPhone": {"fkType": "tlPhoneType"},
        "taMailingArchive": {"fkType": "tlArchiveType"},
        "taMailingArchiveOld": {"fkType": "tlArchiveType"},
        "taAddress": {"State": "tlState"},
        "taAddressInstitution": {"State": "tlState"},
        "taPrisonAdmin": {"State": "tlState",
                      "fkType": "tlFacilityType"},
    }
    # Common foreign key mappings.  For all others, expect the foreign key to
    # map to a table that has the same name as the foreign key
    # (e.g. `fkType` => `tlType`, etc).
    global_foreign_key_map = {
        'fkSub': 'taSubscriber',
        "fkAdmin": "taPrisonAdmin",
        "fkInstitution": "taInstitution", # distinct from 'thInstitution'
        "fkVersion": "tlCensorshipVersion",
        "fkOrigin": "tlAddressOrigin",
        "fkGeneralType": "tlInquiryTypeGeneral",
        "fkSourceCategory": "tlSourceGeneral",
        "fkGrant": "tlGrantSubs",
        "fkInquirer": "taSubscriber",
        "fkResponseType": "tlInquiryResponseGeneral",
        "fkReason": "tlStopReason",
        "fkReasonIneligible": "tlIneligibleReason",
        "fkOrder": "taOrders",
        "fkMethod": "tlPayMethod",
        "fkResponseCategory": "tlInquiryResponseGeneral",
        "fkEndMonth": "tlMonth",
        "fkStartMonth": "tlMonth",
        "fkPacer": "Pacer",
        "SubID1": "taSubscriber",
        "SubID2": "taSubscriber",
    }

    table_names = by_pk.keys()
    missing = defaultdict(lambda: {'ref': '', 'keys': set(), 'count': 0})
    for table, records in by_pk.iteritems():
        if table == "taNotDups":
            fks = set(["SubID1", "SubID2"])
        else:
            fks = set()
            for pk, record in records.iteritems():
                for k in record:
                    if k.startswith("fk"):
                        fks.add(k)
            if table in ("taMailingArchive", "taMailingArchiveOld"):
                fks.remove("fkIssueClosed") # Is a date, not a fk
            elif table == "taCensorshipLetter":
                fks.remove("fkCirc") # Is a date, not a fk
            elif table == "taBackIssueSingle":
                fks.remove("fkYear") # Is a year, not a fk
            elif table == "taBackIssueSet":
                fks.remove("fkYear") # Is a year, not a fk
            elif table == "taBackIssueRange": # Dates, not fk's.
                fks.remove("fkEndYear")
                fks.remove("fkStartYear")
            elif table in ("taAddress", "taPrisonAdmin", "taAddressInstitution"):
                fks.add("State") # States are fk's.

        for fk in fks:
            # Find the referred table name.
            if fk in table_foreign_key_map.get(table, {}):
                ref = table_foreign_key_map[table][fk]
            elif fk in global_foreign_key_map:
                ref = global_foreign_key_map[fk]
            else:
                match = [t for t in table_names if t[2:] == fk[2:]]
                if len(match) != 1:
                    assert False, "Unmatched foreign key: {0}, {1}".format(
                            table, fk)
                ref = match[0]

            # Resolve the foreign keys.
            for pk, record in records.iteritems():
                if fk in record:
                    try:
                        record[fk] = by_pk[ref][record[fk]]
                    except KeyError:
                        table_fk = ".".join((table, fk))
                        missing[table_fk]['ref'] = ref
                        missing[table_fk]['keys'].add(record[fk])
                        missing[table_fk]['count'] += 1
                        record[fk] = None

    # Report missing:
    if len(missing) > 0:
        count = dict([(k, Counter(v)) for k,v in missing.iteritems()])
        for table_fk, details in missing.iteritems():
            total_count = len(by_pk[table_fk.split(".")[0]])
            print
            print table_fk, "=>", details['ref'], "missing", details['count'], "records out of", total_count, "total. ({0:.2f}%)".format(details['count'] / float(total_count) * 100.)
            print len(details['keys']), "missing keys:", 
            if len(details['keys']) < 100:
                print sorted(list(int(k) for k in details['keys']))
            else:
                print "(too many to print)"
        print
        print

    return dict(by_pk)

def parse_xml(xmldir):
    """
    Parse the XML files, and serialize to JSON for faster better easier.
    """
    combined_path = os.path.join(xmldir, "combined.json")
    if os.path.exists(combined_path):
        with open(combined_path) as fh:
            return resolve_keys(json.load(fh))

    data = {}
    for xml_path in xmliter(xmldir):
        dct = convert_xml_to_dct(xml_path)
        for key in dct['dataroot']:
            if key[0] not in ("@", "#"):
                data[key] = dct['dataroot'][key]

    with open(combined_path, 'w') as fh:
        json.dump(data, fh)

    return resolve_keys(data)

class Command(BaseCommand):
    args = '<xml directory path>'
    help = 'Import the old access database from a directory of XML files.'

    def handle(self, *args, **options):
        if len(args) == 0:
            print "Requires one argument: the path to the directory of xml files."
            return
        # All the access table loaded for use. This consumes about 4GB of
        # memory, so watch out.
        self.data = parse_xml(args[0])
        # Cache maps { django_model_label: { id: model }
        self.model_cache = defaultdict(dict)
        self.mailing_types = {}

        # Now that the data is all intra-referenced, we can start from a couple
        # of entry points, and then clean up to find any dangling types.
        #
        # Entry points:
        #  - taAddress: Captures out-of-prison subscribers
        #  - taPrisoner: Captures in-prison subscribers, and current
        #                institution<->subscriber mappings
        #  - taName - fold into Contact
        #  - taEntity - fold into Contact
        #  - thInstitution -- history of address changes.
        #      along with thInstitution: historical institution<->subscriber mappings
        #  - taSubscription -- subscriptions
        #  - taMailingArchive -- issue, Mailing
        #  - taInquiry -- Inquiry
        #  - taEmail -- add to Contact
        #  - taPersonalLetter - fold in to Mailing
        #  - taCensorshipLetter -- [TBD]
        #  - taSubscriber (get subscription sources)
        
        # Cleanup: Get straggling entries not referred to by others

        # Ignore:
        #  - taMailingArchiveOld (is a subset of taMailingArchive)
        #  - taBackIssue*
        #  - taCancel*
        #  - taDupRemoval
        #  - taMakeup
        #  - taDonation 
        #  - taCirculation (duplicates count taMailingArchive)
        #  - taPrisonAdmin (ignore any not referenced by thInstitution)
        #  - taExpiration
        #  - taGrantSubs
        #  - taIneligible
        #  - taGrantSubs
        #  - taMatchingGrant
        with transaction.commit_manually():
            try:
                # 1. Import institutions.
                self.import_taInstitution()

                # 2. Import contacts. Needs institutions.
                self.import_taName()
                self.import_taEntity()

                # 3. Import prison addresses. Needs contacts, institutions.
                self.import_taPrisoner()

                # 4. Import addresses of individuals. Needs contacts.
                self.import_taAddress()

                # 5. Subscriptions, mailings, inquiries, etc.
                self.import_taSubscription()
                self.import_taMailingArchive()
                self.import_taInquiry()
                self.import_taEmail()
                self.import_taSubscriber()
                self.import_taPersonalLetter()
            except Exception:
                transaction.rollback()
                raise
            transaction.commit()
            #transaction.rollback()

        # Reset the SQL now that we've done a lot of inserting of otherwise
        # auto-incrementing ID's.
        commit_sql_sequence_reset()
        print "All done, success!"

    def _create_no_cache(self, model, **kwargs):
        obj, created = model.objects.get_or_create(**kwargs)
        return obj

    def _create(self, model, **kwargs):
        """
        General method for creating a model, and caching it.
        """
        mc = self.model_cache[model._meta.module_name]
        if 'id' not in kwargs or kwargs['id'] not in mc:
            obj = self._create_no_cache(model, **kwargs)
            mc[obj.id] = obj
            kwargs['id'] = obj.id
        return mc[kwargs['id']]

    def _get_by_id(self, model, pk):
        if int(pk) in self.model_cache[model._meta.module_name]:
            return self.model_cache[model._meta.module_name][int(pk)]
        try:
            obj = model.objects.get(pk=pk)
        except model.DoesNotExist:
            return None
        self.model_cache[int(pk)] = obj
        return obj

    def _create_contact(self, raw, parsed=None):
        # Discard: Copies, FirstClass, International, Writer, fkRate, fkPacer
        kwargs = {}
        if 'fkType' in raw:
            # >>> Counter([d['fkType']['Type'] for k,d in data['taSubscriber'].iteritems() if 'fkType' in d])
            # Counter({u'Prisoner': 57993, u'Individual': 5709, u'Entity': 5423, u'International': 1})

            if raw['fkType']['Type'] == 'International':
                kwargs['type'] = 'individual'
            elif raw['Advertiser'] == '1':
                kwargs['type'] = 'advertiser'
            else:
                kwargs['type'] = raw['fkType']['Type'].lower()
        else:
            # >>> len([d for k,d in data['taSubscriber'].iteritems() if 'fkType' not in d])
            # 8
            kwargs['type'] = 'prisoner'
        kwargs['created'] = raw['StartDate'] + 'Z'
        kwargs['id'] = int(raw['SubscriberID'])
        if 'fkSource' in raw and raw['fkSource']:
            kwargs['source'] = self._create_contact_source(raw['fkSource'])
        if parsed:
            kwargs.update(parsed)
        contact = self._create(Contact, **kwargs)
        if 'Notes' in raw:
            self._create(Note, contact=contact, author_id=1, text=raw['Notes'])
        return contact

    def _create_contact_source(self, raw):
        return self._create(ContactSource,
            id=int(raw['SourceID']),
            name=raw['Source'],
            category=self._create(ContactSourceCategory,
                id=int(raw['fkSourceCategory']['GeneralSourceID']),
                name=raw['fkSourceCategory']['SourceCategory']
            )
        )

    def _create_prison(self, raw):
        """
        Expects a dict with: {
            'Address1': ...
            'State': ...
            'Zip': ...
            ...
            'fkInstitution': {
                'Name': ...
                'fkAdmin': {
                    'Warden': ...
                    ...
                }
            }
        """
        address = self._create_address(raw)
        admin_doc = raw['fkInstitution']['fkAdmin']
        if 'fkAdministrator' in admin_doc and admin_doc['fkAdministrator']:
            admin_type = self._create(PrisonAdminType,
                id=int(admin_doc['fkAdministrator']['AdministratorID']),
                name=admin_doc['fkAdministrator']['AdminType'],
            )
        else:
            admin_type = None
        if 'fkType' in admin_doc:
            prison_type = self._create(PrisonType,
                id=int(admin_doc['fkType']['FacilityTypeID']),
                name=admin_doc['fkType']['FacilityType'],
            )
        else:
            prison_type = None
        if 'Address1' in admin_doc:
            admin_address = self._create_address(admin_doc)
        else:
            admin_address = None
        prison = self._create(Prison, 
            name=raw['fkInstitution'].get('Name', ''),
            type=prison_type,
            address=address,
            admin_type=admin_type,
            admin_name=admin_doc.get('Name', ''),
            warden=admin_doc.get('Warden', ''),

            men=null_boolify(admin_doc, 'Men'),
            women=null_boolify(admin_doc, 'Women'),
            minimum=null_boolify(admin_doc, 'Minimum'),
            medium=null_boolify(admin_doc, 'Medium'),
            maximum=null_boolify(admin_doc, 'Maximum'),
            control_unit=null_boolify(admin_doc, 'ControlUnit'),
            death_row=null_boolify(admin_doc, 'DeathRow'),
        )
        return prison

    def _create_address(self, raw):
        return self._create(Address, 
            address1=raw.get('Address1', ''),
            address2=raw.get('Address2', ''),
            city=raw.get('City', ''),
            state=raw.get('State', {}).get('Abbreviation', ''),
            zip=raw.get('Zip', ''),
        )

    def _create_mailing_type(self, name):
        if name not in self.mailing_types:
            self.mailing_types[name] = self._create(MailingType, type=name)
        return self.mailing_types[name]

    def _create_issue(self, date_string):
        match = re.match("^(\d{4})-(\d{2}).*$", date_string)
        year = int(match.group(1))
        month = int(match.group(2))
        volume = year - 1989
        number = month
        return self._create(Issue,
                number=number,
                volume=volume,
                date=date_string)

    def import_taName(self):
        print "import taName"
        def get_gender(d):
            if 'fkGender' not in d or not d['fkGender']:
                return ''
            return {
                'Male': 'M', 'Female': 'F', 'Unknown': '', None: ''
            }.get(d['fkGender'].get('Gender', None))

        for key, doc in self.data['taName'].iteritems():
            if 'fkSubscriber' in doc:
                self._create_contact(doc['fkSubscriber'], {
                    'first_name': doc.get('First', ''),
                    'last_name': doc.get('Last', ''),
                    'gender': get_gender(doc),
                    })

    def import_taEntity(self):
        print "import taEntity"
        for key, doc in self.data['taEntity'].iteritems():
            if 'fkSub' not in doc:
                continue
            if 'fkEntityType' in doc and doc['fkEntityType']:
                entity_type =  self._create(OrganizationType,
                    id=int(doc['fkEntityType']['EntityTypeID']),
                    type=doc['fkEntityType']['EntityType'])

            else:
                entity_type = None
            self._create_contact(doc['fkSub'], {
                'organization_name': doc.get('Entity', ''),
                'organization_type': entity_type
            })
    def import_taAddress(self):
        """
        Captures out-of-prison subscribers.
        """
        print "import taAddress"
        # Ignore fkOrigin
        for key, doc in self.data['taAddress'].iteritems():
            if 'Address1' not in doc and 'Address2' not in doc:
                continue
            contact = self._create_contact(doc['fkSub'])
            contact.address = self._create_address(doc)
            contact.save()

    def import_taInstitution(self):
        print "import taInstitution"
        # Ignore institutions not listed in taAddressInstitution.
        for key, doc in self.data['taAddressInstitution'].iteritems():
            self._create_prison(doc)

    def import_taPrisoner(self):
        """
        Captures in-prison subscribers, and current institution<->subscriber
        mappings
        """
        print "import taPrisoner"
        # Ignore fkOrigin field for thInstitution.

        # Build a map of institution<->contact history by subscriber (contact) ID.
        history_by_subid = defaultdict(list)
        for key, doc in self.data['thInstitution'].iteritems():
            # Keep only the history entries with a subscriber and an institution.
            if ('fkSub' in doc and doc['fkSub']) and \
                    ('fkInstitution' in doc and doc['fkInstitution']):
                history_by_subid[doc['fkSub']['SubscriberID']].append(doc)
        prisoner_by_subid = {}
        # Build a map of prisoners by subscriber (contact) ID.
        for key, doc in self.data['taPrisoner'].iteritems():
            # Keep only the prisoners with a referenced subscriber.
            if 'fkSub' in doc and doc['fkSub']:
                prisoner_by_subid[doc['fkSub']['SubscriberID']] = doc

        # Relate the prisoners to histories, and build PrisonerAddress models.
        for subid, docs in history_by_subid.iteritems():
            # Discard history items that don't refer to a known prisoner
            if subid not in prisoner_by_subid:
                continue
            prisoner = prisoner_by_subid[subid]
            contact = self._get_by_id(Contact, prisoner['fkSub']['SubscriberID'])
            # Discard any prisoner entries that dont have an existing contact
            # from taName or taEntity.
            if not contact:
                continue
            docs.sort(key=lambda o: o['Date'])
            
            for i, doc in enumerate(docs):
                prison = self._get_by_id(Prison, doc['fkInstitution']['InstitutionID'])
                # Discard institutions we haven't seen.
                if not prison:
                    continue
                kwargs = {
                    'contact': contact,
                    'prison': prison,
                }
                kwargs['start_date'] = doc['Date'] + 'Z'
                if i < len(docs) - 1:
                    kwargs['end_date'] = docs[i + 1]['Date'] + 'Z'
                    kwargs['prisoner_number'] = ''
                    kwargs['unit'] = ''
                    kwargs['death_row'] = None
                    kwargs['control_unit'] = None
                else:
                    kwargs['end_date'] = None
                    kwargs['prisoner_number'] = prisoner.get('DOCNumber', '')
                    kwargs['unit'] = prisoner.get('Unit', '')
                    kwargs['death_row'] = null_boolify(prisoner, 'DeathRow')
                    kwargs['control_unit'] = null_boolify(prisoner, 'ControlUnit')
                # Create w/o cache, bcause we won't use the prison address again. Save memory.
                self._create_no_cache(PrisonerAddress, **kwargs)

        # Create any prisoner addresses that don't have a history entry as
        # current, with an arbitrary date.
        for subid, doc in prisoner_by_subid.iteritems():
            if subid not in history_by_subid and 'fkInstitution' in doc and doc['fkInstitution']:
                start_date = now()
                contact = self._get_by_id(Contact, prisoner['fkSub']['SubscriberID'])
                if not contact:
                    continue
                contact.note_set.create(author_id=1, text="[Database Import] Due to database errors, there is no address history for this contact before %s." % start_date)
                prison = self._get_by_id(Prison, doc['fkInstitution']['InstitutionID'])
                if not prison:
                    continue
                # Create w/o cache, bcause we won't use the prison address again. Save memory.
                self._create_no_cache(PrisonerAddress,
                        start_date=start_date,
                        contact=contact,
                        prison=prison,
                        unit=doc.get('Unit', ''),
                        death_row=null_boolify(doc, 'DeathRow'),
                        control_unit=null_boolify(doc, 'ControlUnit'),
                )

    def import_taSubscription(self):
        print "import taSubscription"
        # NOTE: Assuming that payer == subscriber.
        # Past subscriptions.
        for key, doc in self.data['taSubscription'].iteritems():
            if 'fkReason' in doc and doc['fkReason'] and doc['fkReason']['StopReason'] != "Expired":
                reason = self._create(SubscriptionStopReason,
                        id=int(doc['fkReason']['StopReasonID']),
                        reason=doc['fkReason']['StopReason'])
            else:
                reason = None
            contact = self._get_by_id(Contact, doc['fkSubscriber']['SubscriberID'])
            if not contact:
                continue
            if 'StartDate' in doc:
                start_date = doc['StartDate'] + 'Z'
            elif 'EndDate' in doc:
                start_date = doc['EndDate'] + 'Z'
            else:
                continue
            if doc.get('EndDate', None):
                end_date = doc['EndDate'] + 'Z'
            else:
                end_date = None
            self._create_no_cache(Subscription,
                contact=contact,
                payer=contact,
                start_date=start_date,
                end_date=end_date,
                original_end_date=end_date,
                stop_reason=reason,
            )

        # Current subscriptions
        for key, doc in self.data['taExpiration'].iteritems():
            contact = self._get_by_id(Contact, doc['fkSub']['SubscriberID'])
            if not contact:
                continue
            try:
                sub = contact.subscription_set.filter(end_date__isnull=True)[0]
                sub.end_date=doc['ExpirationDate'] + 'Z'
                sub.original_end_date = sub.end_date
                sub.save()
            except IndexError:
                self._create_no_cache(Subscription,
                        contact=contact,
                        payer=contact,
                        start_date=now(),
                        end_date=doc['ExpirationDate'] + 'Z',
                        original_end_date=doc['ExpirationDate'] + 'Z',
                        stop_reason=None,
                )

    def import_taMailingArchive(self):
        # Ignoring fkAddress, fkState, fkType, as these duplicate fkSub.
        # Ignoring mailings with types other than the following:
        print "import taMailingArchive"
        issue_cache = {}
        total_count = len(self.data['taMailingArchive'])
        count = 0
        for key, doc in self.data['taMailingArchive'].iteritems():
            count += 1
#            if count % 1000 == 0:
#                print count, "/", total_count, "%0.2f%%" % (float(count) / total_count * 100)

            if not doc['fkSub']:
                continue
            if 'DateSent' not in doc or not doc['DateSent']:
                continue
            if doc['fkIssueClosed'] not in issue_cache:
                issue_cache[doc['fkIssueClosed']] = self._create_issue(
                        doc['fkIssueClosed'] + 'Z')
            issue = issue_cache[doc['fkIssueClosed']]
            if 'DateSent' in doc and doc['DateSent']:
                date = doc['DateSent'] + 'Z'
            else:
                date = issue.date
            mailing = self._create_no_cache(Mailing,
                    issue=issue,
                    contact=self._create_contact(doc['fkSub']),
                    created=date,
                    sent=date,
                    type=self._create_mailing_type(doc['fkLetterType']['LetterType']),
            )

    def import_taInquiry(self):
        print "import taInquiry"
        for key,doc in self.data['taInquiry'].iteritems():
            contact_doc = doc.get('fkInquirer', None) or doc.get('fkSubscriber', None)
            if contact_doc is None:
                continue
            contact = self._create_contact(contact_doc)
            req_type = self._create(InquiryType,
                    id=int(doc['fkType']['InquiryTypeSpecID']),
                    description=doc['fkType']['Type'])
            code = doc['fkResponseType'].get('LabelCode', '')
            res_type = self._create(InquiryResponseType,
                    id=int(doc['fkResponseType']['ResponseSpecID']),
                    description=doc['fkResponseType']['Response'],
                    code=code,
                    generate_mailing=bool(code),
            )
            irq = self._create_no_cache(Inquiry,
                    id=int(doc['InquiryID']),
                    date=doc['Date'] + 'Z',
                    request_type=req_type,
                    response_type=res_type,
                    contact=contact,
            )
            self._create_no_cache(Mailing,
                    type=self._create_mailing_type("Inquiry"),
                    contact=contact,
                    inquiry=irq,
                    created=doc['Date'] + 'Z',
                    sent=doc['Date'] + 'Z',
            )

    def import_taEmail(self):
        print "import taEmail"
        for key,doc in self.data['taEmail'].iteritems():
            if 'address' not in doc:
                continue
            contact = self._create_contact(doc['fkSub'])
            contact.email = doc['address']
            contact.save()

    def import_taSubscriber(self):
        print "import taSubscriber"
        # Get the contact sources.
        for key,doc in self.data['taSubscriber'].iteritems():
            if 'fkSource' in doc and doc['fkSource']:
                contact = self._get_by_id(Contact, doc['SubscriberID'])
                if not contact:
                    continue
                contact.source = self._create_contact_source(doc['fkSource'])
                contact.save()

    def import_taPersonalLetter(self):
        print "import taPersonalLetter"
        #XXX UI for authoring / sending personal letters?
        for key,doc in self.data['taPersonalLetter'].iteritems():
            if 'fkInquiry' not in doc or not doc['fkInquiry'] or 'fkInquirer' not in doc['fkInquiry']:
                continue
            contact = self._get_by_id(Contact,
                    doc['fkInquiry']['fkInquirer']['SubscriberID'])
            if not contact:
                continue
            self._create_no_cache(Mailing,
                    type=self._create_mailing_type("Personal Letter"),
                    contact=contact,
                    created=doc['fkInquiry']['Date'] + 'Z',
                    sent=doc['fkInquiry']['Date'] + 'Z',
                    custom_text=doc.get('LetterBody', ''),
                    notes="[Database Import] Text may be corrupted due to database issues. %s" % now()
                )

    def import_taCensorshipLetter(self):
        print "import taCensorshipLetter"
        pass
        #XXX How to interpret?  "fkVersion" refers to "Censorship" or "Confirmation"...
        # Points to an issue date -- are only issues censored?

