import datetime
from decimal import Decimal
import hashlib
import locale
import logging
import random
import re
from string import zfill
import traceback
from django.template.defaultfilters import slugify
import math
from django.utils.datastructures import SortedDict

logger = logging.getLogger(__name__)

POPULATION = [chr(x) for x in range(256)]
NULL = ''
UNDERSCORE_PATTERN = re.compile('(?<=[a-z])([A-Z])')


def md5_hash(txt):
    """ Quick md5 hash of any given txt """
    return hashlib.md5(txt).hexdigest()


def random_hash():
    rand = [random.choice(POPULATION) for x in range(25)]
    now = datetime.datetime.now()
    return md5_hash('%s#%s' % (now, rand))


def unique_string(length=None):
    if length is None:
        return random_hash()
    else:
        s = ""
        while len(s) < length:
            s += random_hash()
        return s[:length]


class XMLChoiceMap:
    def __init__(self, attr, choices, default=None):
        self.choices = choices
        self.attr = attr
        self.default = default

    def __call__(self, obj):
        value = self.get_choice(obj)
        setattr(obj, self.attr, value)

    def get_choice(self, obj):
        for key, value in self.choices:
            if key == obj:
                return value
        for value in self.choices.values():
            if value == obj:
                return value
        return self.default


def map_xml(obj, tree, map):
    """
    Takes a map of xml path -> attribute / callable and maps the
    attributes found in the tree to the object.  If the path
    doesn't exist, it skips the node.  If you map to a callable
    it passes the object and the tree node found to the
    callable, otherwise it just sets the text value of the node
    to the object attribute.
    """
    for path, attr in map.items():
        if tree.find(path) is not None:
            if callable(attr):
                attr(obj, tree.find(path))
            else:
                setattr(obj, attr, tree.find(path).text)


numbers = re.compile('\d+')


def increment(s):
    """ look for the last sequence of number(s) in a string and increment """
    if numbers.findall(s):
        lastoccr_sre = list(numbers.finditer(s))[-1]
        lastoccr = lastoccr_sre.group()
        lastoccr_incr = str(int(lastoccr) + 1)
        if len(lastoccr) > len(lastoccr_incr):
            lastoccr_incr = zfill(lastoccr_incr, len(lastoccr))
        return s[:lastoccr_sre.start()] + lastoccr_incr + s[lastoccr_sre.end():]
    return s


def get_unique_slug(text, qs, field_name='slug'):
    slug = slugify(text)
    i = 0
    while qs.filter(**{field_name: slug}).exists():
        if i is 0:
            slug += '_1'
        else:
            slug = increment(slug)
        i += 1
    return slug


def get_unique_username(email):
    """ Creates a unique username from a given email """
    username = email
    if len(username) > 30:
        username = username[:30]
    no_numbers_username = username
    # NOTE: even though this is bad practice, we need to do this import
    ## here instead of in the module namespace
    ## this module, and we don't want to require Django installation on
    ## client machines
    from django.contrib.auth.models import User

    if User.objects.filter(username=username):
        if len(username) == 30:
            username = username[:-4]
        first_username = username + '0000'
        if User.objects.filter(username=first_username):
            last_user = User.objects.filter(username__startswith=username).order_by('-username').exclude(
                username=no_numbers_username)[0]
            username = increment(last_user.username)
        else:
            username = first_username
    return username


def strip_underscores(str, **attribs):
    return str.replace('_', NULL)


def insert_underscores(str, **attribs):
    return UNDERSCORE_PATTERN.sub('_\\1', str)


def strip_dashes(str, **attribs):
    return str.replace('-', NULL)


def insert_dashes(str, **attribs):
    return UNDERSCORE_PATTERN.sub('-\\1', str)


def to_camel_case(str, **attribs):
    if is_magic(str):
        return str
    else:
        return strip_dashes(strip_underscores(from_camel_case(str).title()))


def is_magic(str):
    return str in ['self', 'cls'] or str.startswith('__') and str.endswith('__')


def from_camel_case(str, **attribs):
    if is_magic(str):
        return str
    else:
        return insert_underscores(str).lower()


def from_camel_case_dashes(str, **attribs):
    if is_magic(str):
        return str
    else:
        return insert_dashes(str).lower()


def unslugify(string):
    return string.replace('-', ' ').replace('_', ' ')


def make_shortname(first, last):
    """ Logic behind creating a short name given a first and last name """
    sname = ''
    if first:
        sname += first
    else:
        return last
    if len(last):
        sname += ' %s.' % last[0]
    return sname


def shortname(user):
    """ Returns a short name of a user.
    Example: Greg Doermann would be Greg D."""
    if user.is_anonymous():
        return None
    sname = user.email
    try:
        new_sname = make_shortname(user.first_name, user.last_name)
        if new_sname:
            sname = new_sname
    except:
        pass
    return sname


def clean_text(text):
    import unicodedata

    text = unicodedata.normalize('NFKD', unicode(text)).encode('ascii', 'ignore')
    return unicode(re.sub('[^\w\s-]', '', text).strip().lower())


def clean_hash(text):
    text = clean_text(text)
    text = unicode(re.sub('[^\w-]', '', text))
    return text, md5_hash(text)


def split_hosts_string(hosts_string):
    hosts = []
    for hoststring in [x.strip() for x in hosts_string.split(',')]:
        kwargs = {}
        try:
            host, port = hoststring.split(':')
            port = int(port)
        except ValueError:
            logger.error('Invalid ip:port value for SSH manhole: %r' % hoststring)
            logger.exception(traceback.format_exc())
            continue
        kwargs['interface'], kwargs['port'] = host, port
        hosts.append(kwargs)
    return hosts


BYTE_REGEX = re.compile('([\d]+)b', re.I)
KB_REGEX = re.compile('([\d]+)kb', re.I)
MB_REGEX = re.compile('([\d]+)mb', re.I)
GB_REGEX = re.compile('([\d]+)gb', re.I)
TB_REGEX = re.compile('([\d]+)tb', re.I)

SIZE_DICT = SortedDict((
    (BYTE_REGEX, 0),
    (KB_REGEX, 3),
    (MB_REGEX, 6),
    (GB_REGEX, 9),
    (TB_REGEX, 12),
))

LABEL_DICT = SortedDict((
    (0, 'B'),
    (3, 'kB'),
    (6, 'MB'),
    (9, 'GB'),
    (12, 'TB'),
))


def str_size_to_bytes(s):
    s = slugify(s).replace('-', '').replace('_', '')
    for regex, power in SIZE_DICT.items():
        if regex.match(s):
            return int(regex.match(s).groups()[0]) * math.pow(10, power)
    try:
        return int(s)
    except TypeError:
        pass


def number(value, digits=2):
    if value is None:
        return '-'
    try:
        if callable(value):
            value = value()
        return locale.format('%%.%if' % digits, value, grouping=True, monetary=False)
    except Exception:
        return value


def formatted_bytes(i):
    i = int(i)
    powers = SIZE_DICT.values()
    powers.reverse()
    for power in powers:
        if i / int(math.pow(10, power)):
            value = number(Decimal(i) / Decimal(str(math.pow(10, power))))
            return '%s %s' % (value, LABEL_DICT[power])