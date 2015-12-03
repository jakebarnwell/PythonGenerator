import os
from zipfile import ZipFile
from itertools import izip_longest
from django.conf import settings
from utils import save_to_file, save_to_zip, set_header, get_diff

from apps.weapon.models import Weapon, ECM, Sensor, Repair, Construction, Brain, WeaponSound
from apps.structure.models import Structure, StructureDefence, StructureWeapon, BodyDefence, Feature
from apps.function.models import StructureFunction, Function
from apps.body.models import Body, Propulsion, PropulsionSound, PropulsionType, BodyPropulsion
from apps.templates.models import Template, TemplateWeapon
from apps.research.models import (Research_Cam1, ResearchFunctions_Cam1, ResearchPreRequisites_Cam1, ResultStructure_Cam1,
                                  ResearchStructure_Cam1, ResultComponent_Cam1,
                                  ResearchObsoleteComponent_Cam1, ResearchObsoletStructure_Cam1, Research_Cam2, ResearchFunctions_Cam2, ResearchPreRequisites_Cam2, ResultStructure_Cam2,
                                  ResearchStructure_Cam2, ResultComponent_Cam2,
                                  ResearchObsoleteComponent_Cam2, ResearchObsoletStructure_Cam2,Research_Cam3, ResearchFunctions_Cam3, ResearchPreRequisites_Cam3, ResultStructure_Cam3,
                                  ResearchStructure_Cam3, ResultComponent_Cam3,
                                  ResearchObsoleteComponent_Cam3, ResearchObsoletStructure_Cam3,Research_Multiplayer, ResearchFunctions_Multiplayer, ResearchPreRequisites_Multiplayer, ResultStructure_Multiplayer,
                                  ResearchStructure_Multiplayer, ResultComponent_Multiplayer,
                                  ResearchObsoleteComponent_Multiplayer, ResearchObsoletStructure_Multiplayer)


classes = [
    Weapon,
    Feature,
    Construction,
    Structure,
    StructureFunction,
    Body,
    Propulsion,
    PropulsionSound,
    PropulsionType,
    StructureDefence,
    StructureWeapon,
    Function,
    BodyDefence,
    ECM,
    Sensor,
    Repair,
    BodyPropulsion,
    Brain,
    WeaponSound,
    Template,
    TemplateWeapon,
    Research_Cam1, ResearchFunctions_Cam1, ResearchPreRequisites_Cam1, ResultStructure_Cam1,
    ResearchStructure_Cam1, ResultComponent_Cam1,
    ResearchObsoleteComponent_Cam1, ResearchObsoletStructure_Cam1, Research_Cam2, ResearchFunctions_Cam2, ResearchPreRequisites_Cam2, ResultStructure_Cam2,
    ResearchStructure_Cam2, ResultComponent_Cam2,
    ResearchObsoleteComponent_Cam2, ResearchObsoletStructure_Cam2,Research_Cam3, ResearchFunctions_Cam3, ResearchPreRequisites_Cam3, ResultStructure_Cam3,
    ResearchStructure_Cam3, ResultComponent_Cam3,
    ResearchObsoleteComponent_Cam3, ResearchObsoletStructure_Cam3,Research_Multiplayer, ResearchFunctions_Multiplayer, ResearchPreRequisites_Multiplayer, ResultStructure_Multiplayer,
    ResearchStructure_Multiplayer, ResultComponent_Multiplayer,
    ResearchObsoleteComponent_Multiplayer, ResearchObsoletStructure_Multiplayer
]
classes = [x for x in classes if x.objects.count()]


def save_all():
    [set_header(x)  for x in classes if not x.load_from_first]

    texts = [cls.get_data() for cls in classes]

    diffs = [get_diff(cls, text) for cls, text in zip(classes, texts)]

    if settings.MOD_SOURCE:
        [save_to_file(cls, text) for cls, text in zip(classes, texts)]
    else:
        zf = ZipFile(settings.PATH_TO_MOD)
        names = set(zf.namelist()) - set([x.FILE_PATH for x in classes])
        data = [(path, zf.read(path)) for path in names]
        zf.close()

        zf = ZipFile(settings.PATH_TO_MOD, 'w')
        [save_to_zip(cls, zf, text) for cls, text in zip(classes, texts)]
        [zf.writestr(file, text) for file, text in data]
        zf.close()
    return diffs

def save_xml():
    'does not work with archive'
    texts = [cls.get_xml() for cls in classes]
    [save_to_file(cls, text, format='xml') for cls, text in zip(classes, texts)]
    return [['Saved to XML', [('green', 'ok')]]]

