import sqlite3

class SavingsBond:
	def __init__(self):
		__series =''
		redemption_year=0
		redemption_month=0
		issue_year=0
		issue_month=0
		values = []

	@property
	def series(self):
		if self.__series == 'I':
			return 1
		elif self.__series == 'E':
			return 2
		elif self.__series == 'N':
			return 3
		elif self.__series == 'S':
			return 4
	
	def getvalue(self,line):
		try:
			floatval =  float(line[0:4] + "." + line[4:6])
			return floatval
		except ValueError:
			return 0.0

	#Contructor to parse a line into the object
	def __init__(self,line):
		self.__series = line[0]
		self.redemption_year = int(line[1:5])
		self.redemption_month = int(line[5:7])
		self.issue_year = int(line[7:11])
		self.values = [self.getvalue(line[11:17]),
				self.getvalue(line[17:23]),
				self.getvalue(line[23:29]),
				self.getvalue(line[29:35]),
				self.getvalue(line[35:41]),
				self.getvalue(line[41:47]),
				self.getvalue(line[47:53]),
				self.getvalue(line[53:59]),
				self.getvalue(line[59:65]),
				self.getvalue(line[65:71]),
				self.getvalue(line[71:77]),
				self.getvalue(line[77:83])]

	#Returns a list of bond data by month for insertion into the database	
	def importdata(self):
		val = []
		for i in range(len(self.values)):
			val.append((self.series,int(self.redemption_year),int(self.redemption_month),int(self.issue_year),i,self.values[i]))
			
		return val


conn = sqlite3.connect('bonds.db')

c = conn.cursor()

f = open('sb201212.asc')
for line in f:
	print line
	bond = SavingsBond(line)
	
	try:
		c.executemany('INSERT INTO savings_bond_interest_data VALUES(?,?,?,?,?,?)', bond.importdata())
	
	except sqlite3.Error, e:
		print "Error %s:" % e.args[0]
	
#	print "Series:" + str(bond.series)
#	print "Redeption Year:" + str(bond.redemption_year)
#	print "Redeption Month:" + str(bond.redemption_month)
#	print "issue year:" + str(bond.issue_year)
#	print "Jan:" + str(bond.jan)
#	print "Feb:" + str(bond.feb)
#	print "MAR:" + str(bond.mar)
#	print "APR:" + str(bond.apr)
#	print "MAY:" + str(bond.may)
#	print "JUN:" + str(bond.jun)
#	print "JUL:" + str(bond.jul)
#	print "AUG:" + str(bond.aug)
#	print "SEP:" + str(bond.sep)
#	print "oct:" + str(bond.oct)
#	print "nov:" + str(bond.nov)
#	print "dec:" + str(bond.dec)
	
	
f.close()
conn.commit()
conn.close()
