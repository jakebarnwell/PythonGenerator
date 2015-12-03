import urllib
import re
import os
import zipfile
import shutil
from datetime import date

from importxml import ImportLD12xml

class LD12Downloader:
    
    def __init__(self):
        self.download_directory = os.path.join(".", 'download')
        if not os.path.isdir(self.download_directory): 
            os.mkdir(self.download_directory)

    def checklist(self):
        
        html = urllib.urlopen('http://www.senate.gov/legislative/Public_Disclosure/database_download.htm').read()
        mask = r'<a href="http://soprweb.senate.gov/downloads/(\d{4})_(\d).zip">\S+</a></td><td align="center">(\d{1,2})/(\d{1,2})/(\d{4})</td>'
        matches = re.findall(mask,html)
        zipfiles = [{'year': x[0], 'q': x[1], 'updated': date(int(x[4]),int(x[2]),int(x[3]))} for x in matches]
        
        zipfiles = zipfiles[:16] #limit for testing
        
        for zipfile in zipfiles:
            zipfile['downloadthis'] = True
            zipfile['updatedstr'] = "%s%s%s" % (zipfile['updated'].year, zipfile['updated'].month, zipfile['updated'].day)
            zipfile['directory'] = os.path.join(self.download_directory, '%s_%s' % (zipfile['year'], zipfile['q']))
            if os.path.isdir(zipfile['directory']): 
                try:
                    fh = os.path.join(zipfile['directory'], "updateddate.txt")
                    olddownloaddate = open(fh,'r').read()
                    if olddownloaddate==zipfile['updatedstr']:
                        zipfile['downloadthis'] = False
                except IOError as e: #downloaddate doesn't exist
                    pass

        for zipfile in zipfiles:
            if zipfile['downloadthis']:
                self.download(zipfile)



    def download(self, info):
        if os.path.isdir(info['directory']):
            shutil.rmtree(info['directory'])
        os.mkdir(info['directory'])
        
        zip_name = "%s_%s.zip" % (info['year'], info['q'])
        baseurl = "http://soprweb.senate.gov/downloads/"
        
        zip_path = os.path.join(info['directory'], zip_name)
        urllib.urlretrieve(baseurl + zip_name, zip_path)
        print "Downloaded %s " % zip_name

        ##Unzip file
        try:
            zipf = zipfile.ZipFile(zip_path)
            for filename in zipf.namelist():
                print "Unzipping %s" % filename
                f = open(os.path.join(info['directory'], filename), 'wb')
                f.write(zipf.read(filename))
                f.close()
                
                #do this now or after successful extraction?
                datefile = open( os.path.join(info['directory'], "updateddate.txt"), 'w' )
                datefile.write( info['updatedstr'] )
                datefile.close()
        except:
            print "Failed to unzip %s" % zip_name

        ##Snatching XML files for parsing
        zip_index = os.listdir(info['directory'])
        info['xml_files'] = []

        for f in zip_index:
            if f.endswith(".xml"): 
                info['xml_files'].append( os.path.join(info['directory'],f) )
                
        #parse and insert each file into the db        
        for f in info['xml_files']:
            importer = ImportLD12xml(f)
            importer.parse()

    
    def go(self):
        self.checklist()
    
  

if __name__ == '__main__':
    downloader = LD12Downloader()
    downloader.go()
