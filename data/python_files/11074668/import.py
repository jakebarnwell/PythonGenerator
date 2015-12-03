import sys
import csv

from django.core.management import setup_environ

import settings
setup_environ(settings)

from plan.models import Wykladowca, Przedmiot, Grupa, Pokoj, Zajecie

from datetime import timedelta, datetime

## musi byc poniedzialek
sem_start = datetime(2011, 10, 3)

def fix_start(x):
	# 33   8:00 ponieo
	# 129  8:00 wtorek
	# 153  14:00 wtorek
	# 225  8:00 sroda
	# 321  8:00 czwartek
	x -= 33

	day = x/96;
	x %= 96
	hour = 8 + x/4
	x %= 4
	mins = 15 * x

	return sem_start + timedelta(days = day, hours = hour, minutes = mins)

def fix_dur(x):
	return timedelta(minutes = 15*x)

def fix_week(x):
	if x:
		return 1 << x

	### XXX, odmaskuj swieta, przerwy swiateczne, itd...
	return (1 << 19)-1

wykladowcy = { }
przedmioty = { }
grupy = { }
sale = { }

reader = csv.reader(open("csv/wykladowcy.csv"), dialect='excel')
for row in reader:
	# SELECT surname,name,shortcut,title,room,mail,phone
	wykladowcy[row[7]] = Wykladowca.objects.get_or_create(
		nazwisko=row[0],
		imie=row[1],
		inicjaly=row[2],
		tytul=row[3],
		pokoj=row[4],
		mail=row[5],
		telefon=row[6])

wykladowcy["\\N"] = [ None ]

reader = csv.reader(open("csv/przedmioty.csv"), dialect='excel')
for row in reader:
	# SELECT name,shortcut,type,iNumberOfHours,comment 
	przedmioty[row[5]] = Przedmiot.objects.get_or_create(
		nazwa=row[0],
		skrot=row[1],
		typ=row[2],
		lgodzin=row[3]
		# komentarz=row[4]
		)

reader = csv.reader(open("csv/grupy.csv"), dialect='excel')
for row in reader:
	# SELECT shortcut
	grupy[row[1]] = Grupa.objects.get_or_create(
		nazwa=row[0]
		)

reader = csv.reader(open("csv/sale.csv"), dialect='excel')
for row in reader:
	# SELECT nr_room
	sale[row[1]] = Pokoj.objects.get_or_create(
		sala=row[0]
		)

sale["\\N"] = Pokoj.objects.get_or_create(sala="<<BRAK>>")

reader = csv.reader(open("csv/zajecia.csv"), dialect='excel')
for row in reader:
	# SELECT courses.id, id_cond, id_room, id_group, start, dur
	Zajecie.objects.get_or_create(
		przedmiot = przedmioty[row[0]][0],
		wykladowca = wykladowcy[row[1]][0],
		pokoj = sale[row[2]][0],
		grupa = grupy[row[3]][0],
		start = fix_start(int(row[4])),
		czas = fix_dur(int(row[5])),
		tydz_mask = fix_week(int(row[6]))
	)
