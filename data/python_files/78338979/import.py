import os, random, csv
import sys
sys.path.append('../..')
os.environ['DJANGO_SETTINGS_MODULE'] = 'tsa.settings'
from tsa.config import *

from tsa.events.models import Event, EventSet

#EventSet.objects.all().delete()
#Event.objects.all().delete()

#hs = EventSet(level='HS', state='PA', region='Region 8')
#hs.save()
#ms = EventSet(level='MS', state='PA', region='Region 8')
#ms.save()

hs = EventSet.objects.get(level='HS', region='Region 8')
ms = EventSet.objects.get(level='MS', region='Region 8')


def perform_import(fname, es):
    reader = csv.reader(file(fname))
    reader.next()
    for line in reader:
        print line
        
        raw_min_n, raw_max_n, name, raw_reg, raw_sta, raw_nat, short_name = line
        
        n = int(raw_max_n)
        team = n != 1
        if raw_reg == '?':
            reg = -1
        elif raw_reg == ' ' or raw_reg == '':
            reg = 0
        else:
            reg = int(raw_reg)
        if raw_sta.strip() == 'Q':
            state = -1
        elif raw_sta == ' ':
            state = 0
        else:
            state = int(raw_sta)
        if len(line) < 5:
            nation = 0
        elif raw_nat == ' ' or raw_nat == '':
            nation = 0
        elif len(raw_nat) > 2:
            nation = -int(raw_nat[0])
        else:
            nation = int(raw_nat)
        e = Event(event_set = es, name=name, is_team = team, team_size=n, max_region=reg, max_state=state, max_nation=nation, short_name=short_name)
        e.save()
   
 
hs.events.all().delete()
  
perform_import('events_hs.csv', hs)
#perform_import('events_ms.csv', ms)
