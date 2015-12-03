import tornado
from tornado.options import define, options
import csv
import psycopg2
import sys


define("host", default="localhost")
define("user", default="konbit")
define("dbname", default="konbit")
define("port", default=5432, type=int)
define("password", default='')
tornado.options.parse_command_line()

db = psycopg2.connect(host=options.host, database=options.dbname, user=options.user, password=options.password)
cur = db.cursor()

callReader = csv.reader(open('translation.csv', 'rb'), delimiter=',', quotechar='"')
i = 0
for row in callReader:
  if row[0] == 'asteriskID': continue
  if row[0] == '': continue
  #if i > 99: break
  cur.execute("SELECT * FROM calls_from_gae WHERE key = %s",(row[6],))
  record = cur.fetchone()
  if not record:
    cur.execute("INSERT INTO calls_from_gae (key, asteriskid, person_column_name, language, text, csv_raw_data, is_male, phone_number,person) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",(row[6],row[0],row[7],row[1],row[3],str(row),row[2],row[5],row[4]))
    sys.stdout.write(".")
    #print "Adding %r : %r : %r" % (row[0],row[7],row[6])
    i += 1
print ''
print 'added %d records.' % i
db.commit()

#cur.execute("SELECT * FROM calls_from_gae")
#for record in cur:
#  print record[1]
#cur.close()



db.close()
