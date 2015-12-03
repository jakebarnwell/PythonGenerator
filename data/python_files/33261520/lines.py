import sqlite3 as sql
from collections import namedtuple
import os, os.path, types
import csv
import numpy as np

DEBUG=True

fields="Z, Line_Name, Comment, line_keV, tube_KV, Filter, Ref_Sample, Ref_Line, Calib, Collimator, Crystal, Detector, Peak_2th, Bkg_2th, LLD, ULD"

CSVLine=namedtuple('CSVLine', fields)
Line=namedtuple('Line', 'Z, element, name, keV, line, rel')
Element=namedtuple('Element', 'Z, Name')

def _float(x):
    print x
    try:
        x=float(x)
    except e:
        print e
    return x

class Lines(object):
    def __init__(self, csv=None, dbname=None, v=1):
        if csv == None and dbname==None:
            raise ValueError, 'one of csv or db should be supplied'

        if csv != None:
            if v==1:
                dbname=self.convert_csv(csv)
            else:
                dbname=self.convert_csv2(csv)

        if dbname == None:
            raise RuntimeError, "conversion error"

        self.dbname=dbname

        self.connect()
        self.db.create_function("float", 1, _float)

    def convert_csv(self,filename, debug = DEBUG):
        def _f(x):
            if x=='':
                return None
            if x.find(';')!=-1:
                return None
            try:
                return float(x.replace(',','.').replace('*',''))
            except ValueError, e:
                print "Error:", e
                return x
        reader=csv.reader(open(filename), delimiter=';')
        db_name=os.path.splitext(filename)[0]+'.sqlite3'
        conn=self.connect(dbname=db_name)
        conn.create_function("float", 1, _f)
        reader.next() # skip first row of fiels names
        cur = conn.cursor()
        cur.execute('DROP TABLE IF EXISTS tmp ;')
        cur.execute('DROP TABLE IF EXISTS lines ;')
        cur.execute('DROP TABLE IF EXISTS elements ;')
        self.create_db(conn)
        for row in map(CSVLine._make, reader):
            #params=['?'] * len(row)
            #params=', '.join(params)
            params='?, ?, ?, float(?), ?, ?, ?, ?, ?, float(?), ?, ?, float(?), float(?), ?, ?'
            cmd="""
                INSERT INTO tmp (%s)
                VALUES
                (%s);
            """ % (fields, params)
            cur.execute(cmd, row)
        #print cmd
        conn.commit()
        cur = conn.cursor()
        cur.execute('''SELECT DISTINCT Z, line_keV, Line_Name from tmp;''')
        c2=conn.cursor()
        lset=set()
        eset=set()
        for row in cur:
            Z, keV, ln = row
            ln_=ln.split()[1].split('-')[0]
            row=(Z, keV, ln_)
            if (Z, ln_) in lset:
                continue
            lset.add((Z, ln_))
            if debug:
                print row
            c2.execute("INSERT INTO lines (Z, keV, Name) VALUES (?, ?, ?);",
                row)
            if Z in eset:
                continue
            eset.add(Z)
            c2.execute("INSERT INTO elements (Z, Name) VALUES (?, ?);",
                (Z, ln.split()[0]))

        cur.execute('DROP TABLE IF EXISTS tmp ;')
        conn.commit()

        return db_name

    def convert_csv2(self,filename, debug = DEBUG):
        CONV={
            '_ALPHA':'A',
            '_BETA':'B',
            '_GAMMA':'G',
            '_ETA':'E',
            '_15':'',
            }
        LINE_LIST=['KA1', 'KA2', 'KB1', 'KB2', 'KB3', 'LA1', 'LA2', 'LB2', 'LB6', 'LB1','LG1',
            'LB3', 'LB4', 'LG2', 'LG3']
        def _f(x):
            if x=='':
                return None
            if x.find(';')!=-1:
                return None
            try:
                return float(x.replace(',','.').replace('*',''))
            except ValueError, e:
                print "Error:", e
                return x
        reader=csv.reader(open(filename), delimiter=';')
        db_name=os.path.splitext(filename)[0]+'.sqlite3'
        conn=self.connect(dbname=db_name)
        conn.create_function("float", 1, _f)
        header = reader.next() # skip first row of fiels names
        header=[h.split(',')[0] for h in header]
        def repl(x):
            for k,v in CONV.iteritems():
                x=x.replace(k,v)
            return x
        header=[repl(h) for h in header]
        #print "HEADER:", header
        cur = conn.cursor()
        cur.execute('DROP TABLE IF EXISTS tmp ;')
        cur.execute('DROP TABLE IF EXISTS lines ;')
        cur.execute('DROP TABLE IF EXISTS elements ;')
        self.create_db(conn)
        for row in reader:
            drow={k:v for k,v in zip(header, row)}
            #print drow
            cur.execute('INSERT INTO elements (Z, name, element) VALUES (?,?,?);',
                (drow['ATOMIC_NR'], drow['EL_SYMB'], drow['EL_NAME_EN']))
            c2=conn.cursor()
            for l in LINE_LIST:
                v=drow[l]
                v=v.strip()
                if v:
                    v=v.replace(',','.')
                    v=float(v)
                    c2.execute("INSERT INTO lines (Z, keV, Name) VALUES (?, ?, ?);",
                        (drow['ATOMIC_NR'], v, l))
        cur.execute('DROP TABLE IF EXISTS tmp ;')

        conn.commit()

        return db_name

    def connect(self, dbname=None):
        if dbname != None:
            return sql.connect(dbname)

        if type(self.dbname) in [type(''), type(u'')]:
            self.db = sql.connect(self.dbname)

        return self.db

    def create_db(self, db=None):
        if db == None:
            db = self.db
        c=db.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS tmp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Z INTEGER,
                Line_Name TEXT NULL,
                Comment TEXT NULL,
                line_keV REAL,
                tube_KV REAL,
                Filter TEXT NULL,
                Ref_Sample TEXT NULL,
                Ref_Line TEXT NULL,
                Calib TEXT NULL,
                Collimator REAL,
                Crystal TEXT NULL,
                Detector TEXT NULL,
                Peak_2th REAL NULL,
                Bkg_2th TEXT NULL,
                LLD REAL NULL,
                ULD REAL NULL
        );
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Z INTEGER,
                Name TEXT,
                keV REAL,
                Line Text,
                rel FLOAT
        );
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS elements (
                Z INTEGER PRIMARY KEY,
                name TEXT,
                element TEXT NULL
        );
        ''')

    def fetch_all(self, sql, params=tuple()):
        cur=self.db.cursor()
        sql='''SELECT DISTINCT %s from lines ''' % fields+" where "+sql+';'
        rows=cur.execute(sql,params)
        for row in map(Line._make, rows):
                yield row

    def select(self, Z=None, element=None, line=None, kev=None,
        where=None, order_by=None, analytical=False):
        def _expand(x, ex):
            if x == None :
                return ' 1 '
            if type(x) in [types.TupleType, types.ListType, types.GeneratorType, type(set())]:
                if len(x)==0:
                    return ' 1 '
                else:
                    rc=[ex % _ for _ in x]
            else:
                return " ( " + ex % x + " ) "
            return ' ( '+' or '.join(rc)+' ) '

        if line:
            line=line.upper()
        c=["1"]
        c.append(_expand(Z, "e.Z=%i"))
        c.append(_expand(element, "e.name='%s'"))
        c.append(_expand(line, "l.name='%s'"))
        c.append(_expand(kev, "l.kev=%f"))
        if analytical:
            c.append("((e.Z<=50 and l.name like 'KA%') or (e.Z>50 and l.name like 'LA%'))")
        stmt="""
        SELECT e.Z, e.Name as element, l.Name as line, l.keV as kev, l.line as line, l.rel as rel
        FROM elements e INNER JOIN lines l ON e.Z=l.Z
        WHERE
        %s
        """ % ' and '.join(c)
        if where:
            stmt+=" and "+where
        if order_by:
            stmt+=" ORDER BY "+order_by

        stmt+=" ;"
        cur = self.db.cursor()
        if DEBUG:
            print "STMT:", stmt
        cur.execute(stmt)
        for row in cur:
            yield Line._make(row)

    def as_deltafun(self, **kwargs):
        ls = self.select(**kwargs)
        print ls
        return ls

    def update_rel(self, filename):
        cur=self.db.cursor()
        cur.execute("DELETE FROM lines;")
        self.db.commit();
        reader=csv.reader(open(filename), delimiter=';')
        header = reader.next()
        for row in reader:
            (ev, el, line, rel, name) = row
            ev=ev.replace(' ','').replace(',','.')
            ev=ev.decode('utf8').replace(u'\xa0',u'')
            #print repr(ev)
            ev=float(ev)
            Z, symbol=el.split()
            rel=int(rel)
            line=line.decode('utf-8')
            nrow=(Z, name, ev*1e-3, line, rel)
            cur.execute('INSERT INTO lines (Z, Name, keV, line, rel) VALUES (?,?,?,?,?)', nrow)

        self.db.commit();
        print "Update succsessful."




if 0 and __name__=='__main__':
    import os
    import pylab as pl
    import pprint as pp
    import numpy as np

    if os.name!="nt":
        ldb=Lines(dbname='/home/eugeneai/Development/codes/dispersive/data/lines.sqlite3')
    else:
        ldb=Lines(dbname='C:\\dispersive\\data\\lines.sqlite3')

    #ldb.update_rel('/home/eugeneai/Development/codes/dispersive/data/rel_lines.csv')

    lines=ldb

    L1={'A':0.8, "B":0.8/6.}
    L2={'K':(0,0,0), "L":(1,0,0)}

    elements=["V", "Mo", "W", "Cl", "Se","Zr", "Si", "As"]
    elements=['Mo']

    ls=list(lines.as_deltafun(order_by="keV", element=elements,
        where="not l.name like 'M%' and keV<20.0"))
    pp.pprint(ls)
    print len(ls)
    x=np.array([0, ls[-1].keV*1.03])
    y=np.array([1, 1.])
    pl.plot(x,y)
    y=np.array([0, 0.])
    pl.plot(x,y)

    pl.axvline(0.0, color=(0,1,0))
    pl.axvline(0.0086, color=(0,1,0))
    for l in ls:
        ln=l.name[0]
        ln2=l.name[1]
        pl.axvline(l.keV, color=L2.get(ln, (1,0,0)), ymax=L1.get(ln2, 0.4))

    pl.show()
