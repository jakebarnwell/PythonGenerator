import json
from datetime import date

from django import http
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from querystring_parser import parser

from models import *
from forms import *


def home(request):
    try:
        menu = MenuOfTheDay.published_objects.get(day=date.today())
        c = {
            'menu': menu,
            'courses': menu.courses.all(),
        }
    except MenuOfTheDay.DoesNotExist:
        c = {}

    return render(request, 'menu/show.html', c)


def menu_of_the_day(request, year, month, day):
    year, month, day = map(int, (year, month, day))

    menu = get_object_or_404(MenuOfTheDay.published_objects, day=date(year, month, day))

    return render(request, 'menu/show.html', {
        'menu': menu,
        'courses': menu.courses.all(),
    })


def cache_manifest(request):
    try:
        menu = MenuOfTheDay.published_objects.get(day=date.today())
    except MenuOfTheDay.DoesNotExist:
        menu = None

    return render(request, 'other/cache.manifest', {
        'menu': menu,
    }, content_type='text/cache-manifest')


# def add_menu(request):
#     form = MenuForm()
#     course_form = CourseForm()
#
#     return render(request, 'menu/add.html', {
#         'form': form,
#         'course_form': course_form,
#     })

def mailing_list_subscribe(request):
    if request.method == 'POST':
        form = MailingListForm(request.POST)
        if form.is_valid():
            form.save(request)
    else:
        form = MailingListForm()

    if request.session.get('subscribed'):
        return render(request, 'menu/subscribed.html')

    return render(request, 'menu/subscribe.html', {
        'form': form,
    })


@login_required
def save_courses(request):
    if not request.is_ajax():
        return http.HttpBadResponse("AJAX please.")

    data = parser.parse(request.POST.urlencode())

    for index in data['courses']:
        current = data['courses'][index]
        course = Course.objects.get(pk=current['pk'])

        course.name = current['name']
        course.description = current['description']
        course.save()

    return http.HttpResponse(json.dumps({
        'success': True,
    }))
