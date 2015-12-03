import os
import urllib2
import datetime
import logging
import zipfile
import cStringIO
import time

NSE_URL="http://www.nseindia.com/content/historical/DERIVATIVES"

def which_holiday(date):
    # weekend
    if date.isoweekday() == 6:
        return 'Saturday'
    if date.isoweekday() == 7:
        return 'Sunday'
    
    mon = date.strftime("%b").upper()
    if mon == 'JAN' and date.day == 26:
        return 'Republic Day'
    
    if mon == 'AUG'  and date.day == 15:
        return 'Independence Day'
    
    if mon == 'OCT'  and date.day == 2:
        return 'Mahatma Gandhi Bday'
    
    if mon == 'DEC'  and date.day == 25:
        return 'XMas'
    
    return ""
    
def download_file(date, save_folder):        
    date_tag = date.strftime("%d%b%Y").upper()
    logging.debug("processing %s ..."%date_tag)
    
    hol = which_holiday(date)
    if hol:
        logging.debug("  skipping holiday %s on %s ..."%(hol,date_tag))
        return
    
    file_name = "fo%sbhav.csv.zip"%date_tag
    file_path = os.path.join(save_folder, "%s.csv.zip"%date.strftime("%Y-%m-%d"))
    if os.path.exists(file_path):
        logging.debug("    %s exists skipping"%file_name)
        return
    
    url = "%s/%s/%s/%s"%(NSE_URL, date.year, date.strftime("%b").upper(), file_name)
    logging.info("    downloading %s"%url)
    
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/8.0.552.224 Safari/534.10',
    'Accept': 'application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5'
    }
    
    time.sleep(2) # lets wait a bit for next download
    
    request = urllib2.Request(url, headers=headers)
    try:
        f = urllib2.urlopen(request)
        data = f.read()
        f.close()
    except urllib2.HTTPError, e:
        if e.code == 404: # not found skip
            logging.error("    skipping as data doesn't exists on server")
            return
        raise Exception(" skiping due to error: %s \n%s"%(e, e.fp.read()))
    
    try:
        zfile = zipfile.ZipFile(cStringIO.StringIO(data))
        sz = 0
        for name in zfile.namelist():
            sz += len(zfile.read(name))
        logging.debug("   unzip size %s files %s"%(sz, zfile.namelist()))
        zfile.close()
    except Exception,e:
        logging.error("    skipping as data can not be unzipped\n%s"%e)
        return
        
    f = open(file_path, "wb")
    f.write(data)
    f.close()
    logging.debug("    saved %s"%file_path)
    
def download_files(start_date, end_date, save_folder):
    current_date = start_date
    while current_date <= end_date:
        download_file(current_date, save_folder)
        current_date += datetime.timedelta(days=1)
        
def set_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    fileHandler = logging.FileHandler("nsedump.log", mode='w')
    fileHandler.setLevel(logging.DEBUG)

    streamHandler = logging.StreamHandler()
    streamHandler.setLevel(logging.INFO)
    
    # create formatter and add it to the handlers
    formatter = logging.Formatter("[%(asctime)s %(levelname)s] %(message)s ")
    streamHandler.setFormatter(formatter)
    fileHandler.setFormatter(formatter)
    
    logger.addHandler(streamHandler)
    logger.addHandler(fileHandler)
    
if __name__ == "__main__":
    from optparse import OptionParser

    set_logger()
    
    default_startdate = '01Jan2000'
    default_enddate = datetime.datetime.now().strftime("%d%b%Y")
    
    parser = OptionParser("%prog [options]\nuse -h to see options")
    parser.add_option("-f", "--f", dest="folder",
                      help="which folder to save files", metavar="folder")
    parser.add_option("-s", "--startdate", dest="startdate",
                      help="from which date to start downloading default: %s"%default_startdate, metavar="startdate", default=default_startdate)
    parser.add_option("-e", "--enddate", dest="enddate",
                      help="till which date to download default: %s"%default_enddate, metavar="enddate", default=default_enddate)
    (options, args) = parser.parse_args()
    
    if args:
        parser.error("No arguments are expected")
        
    if not options.folder:
        parser.error("No folder passed")
        
    if not os.path.isdir(options.folder):
        parser.error("Folder %s doesn't exists or isn't a folder"%options.folder)
    
    for varname in ['startdate', 'enddate']:
        try:
            date = datetime.datetime.strptime(getattr(options, varname), "%d%b%Y")
            setattr(options, varname, date)
            
        except ValueError,e:
            parser.error("%s should be in ddmonyear format e.g 01Jan2008"%varname)
            
    download_files(options.startdate, options.enddate, options.folder)