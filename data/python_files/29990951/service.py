
import pickle
import base64
import logging

from sqlalchemy import create_engine
from common import StrippedContext, StrippedConnection, StrippedCursor
from sqlalchemy.schema import MetaData
from sqlalchemy.orm.session import sessionmaker
import sqlalchemy.ext.serializer as saser
from sqlalchemy.orm import scoped_session, mapper
from mappings import *     

class SQLAlchemyService:    
    def __init__(self, engine):
        self._engine = engine
        self.metadata = MetaData(bind = self._engine)
        self.loadMappings()
        self.session = scoped_session(sessionmaker())
    
    def _execute(self, engine, command, args, kwargs):
        kwargs['autocommit'] = True
        res =  self._engine.execute(command, *args, **kwargs)
        return res
            
    def loadMappings(self):
        updateMapper(self.metadata)        
    
    def encode(self, orig):
        p = pickle.dumps(orig)
        return base64.b64encode(p)
    
    def decode(self, orig, loads = pickle.loads):
        p = base64.b64decode(orig)
        return loads(p)
    
    def qloads(self, serialized):
        return saser.loads(serialized, self.metadata, self.session)
    
    def execute(self, command, args, kwargs):
        c = self.decode(command, self.qloads)
        a = self.decode(args)
        k = self.decode(kwargs)
        r = self._execute(self._engine, c, a, k)
        r.dialect = None
        r.context = StrippedContext( r.context )    
        r.cursor = StrippedCursor( r.cursor )
        r.connection = StrippedConnection( r.connection )
        if not r._saved_cursor.closed:
            try:
                r._saved_cursor.close()
            except Exception as ex:
                logging.warning("Could not properly close cursor, but proceeding... (%s)" % ex)
        r._saved_cursor = None
        return self.encode(r)
    

