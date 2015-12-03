import csv

import swiss
cache = swiss.Cache('cache')

url = 'http://www.hm-treasury.gov.uk/d/cra_2009_db.csv'
url_xls = 'http://www.hm-treasury.gov.uk/d/cra_2009_db.xls'

dburi = 'sqlite:///%s' % cache.cache_path('ukgov_finances_cra.db')
# Dept Code,Dept Name,Function,Sub-function,Programme Object Group,Programme Object Group Alias,
# ID or Non-ID,CAP or CUR,CG or LA,NUTS 1 region
# 2003-04,2004-05,2005-06,2006-07,2007-08,2008-09,2009-10,2010-11

# object model
# Classifiers: cur/ap, id/non-id, CG or LA, region

class Loader(object):
    def retrieve(self):
        '''Retrieve the CRA data to cache (if not already there)'''
        fp = cache.retrieve(url)

    def demo(self):
        fp = cache.retrieve(url)
        for count,row in enumerate(csv.reader(open(fp))):
            print row
            if count > 10: break

    def investigate(self):
        '''check whether entries are unique.
        
        Results:
            pog/ident/caporcur/level/region: 8160 duplicates.
                Ex: row 2 and row 210 which are duplicates.
            pog/caporcur/region: 8176
             + subfunction: 6713

        Adding subfunction takes this down to 6698
        Adding function to this takes down to 6498

        Duplicates based on entire row: 1859
            * On visual inspection all of these have all zero or null amount values
        '''
        fp = cache.retrieve(url)
        reader = csv.DictReader(open(fp))
        idset = set()
        nonunique = {}
        for count,row in enumerate(reader):
            function = row['Function']
            subfunction = row['Sub-function']
            pog = row['Programme Object Group']
            ident = row['ID or Non-ID']
            caporcur = row['CAP or CUR']
            level = row['CG or LA']
            region = row['NUTS 1 region']
            uniqueid = (pog, caporcur, region, subfunction) #  subfunction, function)
            # uniqueid = tuple(row.values())
            if uniqueid in idset:
                nonunique[count] = uniqueid
            idset.add(uniqueid)
        print len(nonunique)
        for k,v in nonunique.items():
            print k, v
    
    def load(self):
        '''
        Looks like LA is very limited and is always associated with a given
        "department" -- so this is really a classifier for the account

        Simplest normalization:
            * years
            * dept FK

        Expenditure
            * subfunc 
            * year
            * caporcur
            * region: usuals ones ... (ID or Non-ID not needed ...)
            * programme FK
        
        # does the same programme ever occur within two differnet departments?
        Programme
            * department

        Department?


        What questions do i want to ask:
            * Basically we want to browse in by facets
            * Region, func, subfunc, ...
        '''
        import db
        fp = cache.retrieve(url)
        reader = csv.reader(open(fp))
        # theoretically we'd have distributions to dept from CG as well ...
        # acc = 'CG' acc = 'LA'
        
        # dept -> account

        # Tag accounts:
        # subfunc
        # Tags relate to other tags ...
        

        repo = db.Repository(dburi)
        # skip headings
        reader.next()
        _clean = lambda _str: unicode(_str.strip())
        for count,row in enumerate(reader):
            dept = _clean(row[1])
            # have some blank rows at end
            if not dept:
                continue
            subfunction = _clean(row[3])
            pog = _clean(row[5]) # take verbose one
            # pog = row['Programme Object Group']
            caporcur = _clean(row[7])
            region = _clean(row[9])
            exps = row[10:]
            area = db.Area(title=pog, department=dept, cap_or_cur=caporcur,
                    region=region)
            for ii,exp in enumerate(exps):
                amount = swiss.floatify(exp)
                if amount: # do not bother with null or zero amounts
                    area.expenditures.append(
                        db.Expenditure(amount=amount, year=2003+ii)
                        )
            if count % 5000 == 0:
                print 'Completed: %s' % count
                db.Session.commit()
                db.Session.remove()
        db.Session.commit()
        

import optparse
import os
import sys
import inspect
def _extract(obj):
    methods = inspect.getmembers(obj, inspect.ismethod)
    methods = filter(lambda (name,y): not name.startswith('_'), methods)
    methods = dict(methods)
    return methods

if __name__ == '__main__':
    _methods = _extract(Loader)

    usage = '''%prog {action}

    '''
    usage += '\n    '.join(
        [ '%s: %s' % (name, m.__doc__.split('\n')[0] if m.__doc__ else '') for (name,m)
        in _methods.items() ])
    parser = optparse.OptionParser(usage)

    options, args = parser.parse_args()
    if not args or not args[0] in _methods:
        parser.print_help()
        sys.exit(1)

    method = args[0]
    getattr(Loader(), method)()

