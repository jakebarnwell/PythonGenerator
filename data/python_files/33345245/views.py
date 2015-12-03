import os
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from apps.admin.save_utils import save_xml, save_all
from apps.admin.load_data import load_all
from libs.annoying.decorators import render_to
from django.contrib import messages

def load(request):
    file = settings.PATH_TO_MOD
    if not os.path.exists(file):
        return  HttpResponse('No file found. Please set correct path to base.wz in user settings.')
    time = load_all()
    messages.success(request, 'Stats loaded in %s seconds' % time)
    return  HttpResponseRedirect('/')


@render_to('save.html')
def save(request, format):
    if format == 'xml':
        res = save_xml()
    else:
        res = save_all()
    return {'diff': res}


@render_to('table_info.html')
def table_info(request):
    from apps.weapon.models import Weapon, ECM, Sensor, Repair, Construction, Brain, WeaponSound
    from apps.structure.models import Structure, Feature
    from apps.function.models import StructureFunction, Function
    from apps.body.models import Body, Propulsion, PropulsionSound, PropulsionType, BodyPropulsion
    from apps.templates.models import Template, TemplateWeapon
    from apps.research.models import (Research_Cam1, ResearchFunctions_Cam1, ResearchPreRequisites_Cam1, ResultStructure_Cam1,
                                      ResearchStructure_Cam1, ResultComponent_Cam1,
                                      ResearchObsoleteComponent_Cam1, ResearchObsoletStructure_Cam1)

    tables = [Weapon, ECM, Sensor, Repair, Construction, Brain, WeaponSound,
              Structure, Feature,
              StructureFunction, Function,
              Body, Propulsion, PropulsionSound, PropulsionType, BodyPropulsion,
              Template, TemplateWeapon,
              Research_Cam1, ResultComponent_Cam1, ResearchFunctions_Cam1,
              ResearchObsoleteComponent_Cam1, ResearchObsoletStructure_Cam1,
              ResearchPreRequisites_Cam1, ResearchStructure_Cam1, ResultStructure_Cam1,
    ]
    return {'tables': tables}



@render_to('researches.html')
def researches(request):
    from apps.research.models import Research
    return {'researches': Research.objects.all()}


@render_to('data_mining.html')
def data_mining(request):
    from apps.body.inspection import body_disignable_inspector
    blobs = [x() for x in [body_disignable_inspector]]

    return {'blobs': blobs}


def save_graviz_tree(request):
    from apps.research.views import create_graviz_tree
    create_graviz_tree()
    return HttpResponse('research.gv saved')





