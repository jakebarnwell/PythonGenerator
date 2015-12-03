import os
import sys
import logging

from timetables.utils.Json import JsonCodec
from timetables.superadministrator.service import SuperAdmin
from timetables.model.management import dataset
from timetables.administrator import tests
from timetables.superadministrator import views

from django.test import TestCase
from django.http import HttpRequest
from django.contrib.auth.models import AnonymousUser
from django.utils import simplejson as json
from django.core.urlresolvers import reverse

logger = logging.getLogger("timetables.test")

class SimpleTest(TestCase):
    def testTimetableView(self):
        try:
            dataset.loadTestData()
        except:
            pass

        request = HttpRequest()
        request.user = AnonymousUser()

        sa = SuperAdmin(request);
        logger.debug("SuperAdmin page_overview_data %s " % json.dumps(sa.page_overview_data(), cls=JsonCodec, indent=4))
        logger.debug("SuperAdmin administrators %s " % json.dumps(sa.administrators(), cls=JsonCodec, indent=4))
        logger.debug("SuperAdmin administrators_add %s " % json.dumps(sa.administrators_add(), cls=JsonCodec, indent=4))
        logger.debug("SuperAdmin faculties %s " % json.dumps(sa.faculties(), cls=JsonCodec, indent=4))
        logger.debug("SuperAdmin faculties_add %s " % json.dumps(sa.faculties_add(), cls=JsonCodec, indent=4))
        logger.debug("SuperAdmin faculties_edit %s " % json.dumps(sa.faculties_edit(), cls=JsonCodec, indent=4))
        logger.debug("SuperAdmin timetables %s " % json.dumps(sa.timetables(), cls=JsonCodec, indent=4))

class SamplePagesTest(tests.SamplePagesTest):
    "Checks that requesting each of our views results in a 200 response."
    PAGES = [
        reverse(views.view_overview),
        reverse(views.view_administrators),
        reverse(views.view_administrators_add),
        reverse(views.view_administrators_edit),
        reverse(views.view_faculties),
        reverse(views.view_faculties_add),
        reverse(views.view_faculties_edit),
        reverse(views.view_timetables),
    ]
