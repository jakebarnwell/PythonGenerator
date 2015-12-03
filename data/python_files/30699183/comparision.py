import csv
import logging
import pylab
import operator
from pprint import pprint
f = open('data/databank.csv', "rb")
rox = []
country_list = []
num = 0
GDP = []
country_id = []
sortex = {}
for count, content in enumerate(csv.DictReader(f)):
    rox.append(content)
for row in rox:
    if row['Country Name'] not in country_list:
        country_list.append(row['Country Name'])
#print "Country List %s" % (country_list)
logging.basicConfig(filename='warning.log', level=logging.INFO)
for count, country in enumerate(country_list):
    temp_gdp = []
    for row in rox:
        if row['Country Name'] == country:
            if row['Indicator Name'] == 'GDP (current US$)':
                for year in range(1963, 2010):
                    try:
                        temp_gdp.append(float(row[str(year)]))
                    except:
                        logging.info("No info on %s about %s in %s" %  \
                        (row['Country Name'], row['Indicator Name'], year))
                if temp_gdp:
                    temp_gdp.sort()
                    GDP.append(temp_gdp[-1])
                    country_id.append(count)
                    sortex[row['Country Name']] = temp_gdp[-1]
#               import ipdb; ipdb.set_trace();
#               from matplotlib import pyplot
#               fig = pyplot.figure()
#               ax = fig.add_subplot(111)
#               ax.plot(years, GDP, 'g')
#               fig.savefig('GDP_1963_2010_%s.png' % (row['Country Name']))
#               print 'GDP_1963_2010_%s.png saved.' % (row['Country Name'])
#
                #import ipdb; ipdb.set_trace();
pl = pylab
fig = pl.figure()
ax = fig.add_subplot(1, 1, 1)
ax.bar(GDP, country_id, facecolor='#00AA00', width=0.5, align='center')
ax.set_title('Highest GDP by country', fontstyle='italic')
#ax.set_xlim(0, 48)
#ax.set_xticks([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24])
ax.set_xticklabels(country_list)
ax.set_ylabel("Trillions of $")
ax.set_xlabel("Countries")
#pylab.savefig("compare_GDP.png")
sorted_gdp = sorted(sortex.iteritems(), key=operator.itemgetter(1))
print "GDP in Sorted order"
for country, gdp in sorted_gdp:
    print country, ":\t\t", gdp
pl.draw()
