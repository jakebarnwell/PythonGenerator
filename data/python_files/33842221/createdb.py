import os
import glob
import zipfile
import csv
import sqlite3
import cStringIO
import logging
import datetime

def save_db(nse_folder, dbfile, stock_symbol):
    columns = [('INSTRUMENT', 'text'),
               ('SYMBOL', 'text'),
               ('EXPIRY_DT', 'text'),
               ('STRIKE_PR', 'real'),
               ('OPTION_TYP', 'text'),
               ('OPEN', 'real'),
               ('HIGH', 'real'),
               ('LOW', 'real'),
               ('CLOSE', 'real'),
               ('SETTLE_PR', 'real'),
               ('CONTRACTS', 'real'),
               ('VAL_INLAKH', 'real'),
               ('OPEN_INT', 'real'),
               ('CHG_IN_OI', 'real'),
               ('TIMESTAMP', 'text')]
    
    column_names = [c for c, t in columns]
    
    conn = sqlite3.connect(dbfile)
    cursor = conn.cursor()
    # Create table
    logging.info("creating table %s"%stock_symbol)
    columns_str = ','.join(["%s %s"%(c,t) for c, t in columns])
    cursor.execute('create table %s (%s)'%(stock_symbol, columns_str))

    param_str = ['?']*len(columns)
    param_str = ','.join(param_str)
    insert_sql = 'insert into nifty values (%s)'%param_str
    count = 0
    for csvzipfile in glob.glob(nse_folder+"/*.csv.zip"):
        if not csvzipfile.endswith(".csv.zip"):
            continue
        
        logging.info("loading %s"%csvzipfile)
        
        zfile = zipfile.ZipFile(open(csvzipfile, "rb"))
        sz = 0
        data = ""
        for name in zfile.namelist():
            data += zfile.read(name)
        zfile.close()
        indexEXPIRY_DT = column_names.index('EXPIRY_DT')
        indexTIMESTAMP = column_names.index('TIMESTAMP')
        for i, row in enumerate(csv.reader(cStringIO.StringIO(data))):
            # nse data has , at end, so skip last element
            if not row:
                continue
            if row[-1] == '':
                row = row[:-1]
            if i == 0:#header
                # some csv hav OPTIONTYPE instead of OPTION_TYP
                row = ','.join(row).replace('OPTIONTYPE', 'OPTION_TYP').split(",")
                if row != column_names:
                    print row
                    print column_names
                    raise Exception("Column header mismatch")
                continue
            
            symbol = row[1]
            if symbol != stock_symbol:
                continue
            
            count+=1
            
            # convert dates from dd-mmm-yyyy -> yyyy-mm-dd which is text sortable
            for dateIndex in [indexEXPIRY_DT, indexTIMESTAMP]:
                value = row[dateIndex]
                value = datetime.datetime.strptime(value, "%d-%b-%Y")
                row[dateIndex] = value.strftime("%Y-%m-%d")
                
            cursor.execute(insert_sql, row)
                
    conn.commit()
    cursor.close()
    
    logging.info("%s records of %s saved."%(count, stock_symbol))
    
def set_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    fileHandler = logging.FileHandler("createdb.log", mode='w')
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
    
    parser = OptionParser("%prog [options]\nuse -h to see options")
    parser.add_option("-f", "--folder", dest="folder",
                      help="folder where nse data is", metavar="folder")
    parser.add_option("-s", "--symbol", dest="symbol",
                      help="data for which stock", metavar="symbol")
    
    (options, args) = parser.parse_args()
    
    if not options.folder:
        parser.error("No folder passed")
        
    if not options.symbol:
        parser.error("No symbol passed")
        
    if not os.path.isdir(options.folder):
        parser.error("Folder %s doesn't exists or isn't a folder"%options.folder)
    
    if len(args) != 1:
        parser.error("please pass the db file path")
        
    dbfile = args[0]
    if os.path.exists(dbfile):
        raw_input("db file %s exists, overwrite? Cntr-C to exit")
        os.remove(dbfile)
        
    save_db(options.folder, dbfile, options.symbol)