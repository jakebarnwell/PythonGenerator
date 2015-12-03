import transaction

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Text

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from zope.sqlalchemy import ZopeTransactionExtension

from pyramid.security import Allow
from pyramid.security import Everyone

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

class RootFactory(object):
    """
    a factory added for the security portion of the tutorial
    """
    __acl__ = [
        (Allow, Everyone, 'view'),
        (Allow, 'group:editors', 'edit')
    ]
    
    def __init__(self, request):
        pass
    

class Page(Base):
    """
    The SQLAlchemy declaritive model class for a wiki Page
    """
    __tablename__ = 'pages'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    data = Column(Text)
    
    def __init__(self, name, data):
        self.name = name
        self.data = data


def populate():
    transaction.begin()
    session = DBSession()

    page = Page('FrontPage', 'This is the front page! Welcome!')
    session.add(page)

    session.flush()
    transaction.commit()

def initializeSQL(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    try:
        populate()
    except IntegrityError:
        transaction.abort()
