import os
import sys
import transaction
from datetime import date
from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from ..models import (
    DBSession,
    MyModel,
    Base,
    Usuario,
    Tema,
    Noticia
    )


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    with transaction.manager:
        #model = MyModel(name='one', value=1)
        model = Usuario(nombre='Jorge M.', login='jorgem', password='hola')
        tsje = Tema(nombre='TSJE', descripcion='Noticias del TSJE', usuario = model)
        coloo = Tema(nombre='Partido Colorado', descripcion='Noticias de HC', usuario = model)
        libe = Tema(nombre='Partido Liberal', descripcion='holaa', usuario = model)
        n1 = Noticia(titulo='HC Gana Internas', tema = coloo, fecha=date(2012,11,15),contenido ='Contenido de La noticia 1')
        n3 = Noticia(titulo='Lalalallaa', tema = libe, fecha=date(2012,10,10),contenido ='Contenido de La noticia 3')
        [DBSession.add(e) for e in [n1, n3]]
        [DBSession.add(e) for e in [coloo, libe,tsje]]
        DBSession.add(model)
