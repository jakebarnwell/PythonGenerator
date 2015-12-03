import locale
import calendar
import requests
import urlparse
from datetime import date
from optparse import make_option

from bs4 import BeautifulSoup

from django.conf import settings
from django.core.mail import mail_managers
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.core.management.base import BaseCommand  # , CommandError

from projectmensa.menu.models import MenuOfTheDay, Course
from projectmensa.menu.pdf_utils import pdf_to_courses, PDFParsingError

BASE = 'http://www.adisu.sa.it/fileadmin/user_upload/menu/'

try:
    locale.setlocale(locale.LC_ALL, "it_IT.UTF-8")
except locale.Error:
    pass

calendar.setfirstweekday(calendar.MONDAY)


def parse_pdf_url():
    url = 'http://www.adisu.sa.it/4/servizi-edisu/ristorazione/menu-del-giorno.html'

    page = requests.get(url).text

    soup = BeautifulSoup(page, 'html.parser')
    link = soup.find('div', attrs={'class': 'tx-damdownloadlist-pi1'}).select('a[href$=".pdf"]')

    if not len(link):
        return None

    link = urlparse.urljoin(url, '/' + link[0]['href'])

    r = requests.get(link)

    if r.status_code is not 200:
        return None

    return r


def get_pdf_url(day, month, year):
    filename = 'menu_del_giorno_%(day)s_%(month)s__%(year)s_img.pdf' % {
        'day': day,
        'month': month,
        'year': year,
    }

    return urlparse.urljoin(BASE, filename)


def get_pdf_url2(day, month, year):
    filename = 'menu_%(day)s_%(month)s_%(year)s.pdf' % {
        'day': day,
        'month': month.upper(),
        'year': year,
    }

    return urlparse.urljoin(BASE, filename)


def check_menu(get_url):
    today = date.today()

    month = today.strftime('%B').lower()

    url = get_url(today.day, month, today.year)

    r = requests.get(url)

    if r.status_code is not 200:
        return None

    return r


def already_downloaded():
    try:
        MenuOfTheDay.objects.get(day=date.today())

        return True
    except MenuOfTheDay.DoesNotExist:
        return False


def send_notification(title, message):
    token = getattr(settings, 'PUSHOVER_TOKEN', '')
    user = getattr(settings, 'PUSHOVER_USER', '')

    if token == '' or user == '':
        return

    url = 'https://api.pushover.net/1/messages.json'

    requests.post(url, data={
        'token': token,
        'user': user,
        'title': title,
        'message': message,
    })

    print 'notification sent'


class Command(BaseCommand):
    help = 'Downloads the menu of today, if it exists'
    option_list = BaseCommand.option_list + (
        make_option('--force',
            action='store_true',
            dest='force',
            default=False,
            ),
        make_option('--email',
            action='store_true',
            dest='send_mail',
            default=False,
            help='Sends an email when finished'),
        )

    def handle(self, *args, **options):
        if already_downloaded():
            self.stdout.write('Menu already downloaded\n')

            if options['force']:
                MenuOfTheDay.objects.get(day=date.today()).delete()
            else:
                return

        r = check_menu(get_pdf_url2)

        if r is None:
            r = check_menu(get_pdf_url)

        if r is None:
            r = parse_pdf_url()

        if r is not None:
            try:
                if not options['force']:
                    MenuOfTheDay.objects.get(downloaded_from=r.url)
                    self.stdout.write('Menu already downloaded\n')
                    send_notification('Menu already donwloaded', r.url)
                    return
            except MenuOfTheDay.DoesNotExist:
                pass

            m = MenuOfTheDay()
            m.day = date.today()

            f = ContentFile(r.content)

            m.pdf.save('temp', f)
            m.published = False
            m.downloaded_from = r.url
            m.save()

            try:
                courses = pdf_to_courses(f)
                f.close()

                for course in courses:
                    if not course['name']:
                        continue

                    try:
                        c = Course.objects.get(name=course['name'])

                        if c.description != course['description']:
                            c.description = course['description']
                            c.save()

                    except Course.DoesNotExist:
                        c = Course(name=course['name'], description=course['description'],
                                   type=course['type'])
                        c.save()

                    m.courses.add(c)

                m.published = True
                m.save()

                if options['send_mail']:
                    body = render_to_string('menu/mail_menu.mdown', {
                        'menu': m,
                        'courses': m.courses.all(),
                    })
                    mail_managers(u'[Unisa Menu] Menu caricato', body)

                send_notification('Done', 'Menu downloaded')
                self.stdout.write('Done.\n')

            except PDFParsingError:
                mail_managers(u'[Unisa Menu] Problema PDF', 'Mi scoccio')
                self.stdout.write('Problem while parsing the PDF.\n')

        else:
            send_notification('Not Found', 'Menu does not exist.')
            self.stdout.write('Menu does not exists.\n')
