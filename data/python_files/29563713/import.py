import sys
from django.core.management import setup_environ
# sys.path.append("/home/nick/Dropbox/Personal/django/")
from two import settings
setup_environ(settings)

def import_blankpupils:
    from two.app.models import Pupil 

    import csv
    reader = csv.reader(open(somefile), dialect='excel')
       
    for row in reader:
       level = row[0]
       strand = row[1]
       order = row[2]
       description = row[3]
       
       strandobject = Strand.objects.get(code=strand)
                          
       Objective.objects.get_or_create(level=level, strand=strandobject, order=order, description=description)

