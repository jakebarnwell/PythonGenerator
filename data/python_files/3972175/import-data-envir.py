import sys
import serial
from time import sleep

# parses the XML
from currentcostparser    import CurrentCostDataParser
from currentcostdb import CurrentCostDB 
from tracer import CurrentCostTracer


def run(s, db):
    trc = CurrentCostTracer()
    trc.EnableTrace(True)
    trc.InitialiseTraceFile()

    myparser = CurrentCostDataParser()
    while True:
        try:
            line = s.readline()
        except Exception, why:
            print why
            sleep(1)
        else:
            if line:
                line = line.strip()
                currentcoststruct = myparser.parseCurrentCostXML(line)
                if currentcoststruct:
                    print currentcoststruct
                    if currentcoststruct["msg"].has_key("ch1"):
                        w1 = int(currentcoststruct["msg"]["ch1"]["watts"])
                        w2 = int(currentcoststruct["msg"]["ch2"]["watts"])
                        w3 = int(currentcoststruct["msg"]["ch3"]["watts"])
                        t = (w1**2 + w2**2 + w3**2 ) **0.5
                        print "watts are :", t
                    if currentcoststruct["msg"].has_key("hist"):
                        print "storing history data"
                        myparser.storeTimedCurrentCostData(db)
    
def usage():
    print "usage: "
    print sys.argv[0], " device [dbfile]"
    print "device is for example /dev/ttyUSB0 on linux and com1 on windows" 
    print "dbfile is the path to the db file you want to use, the default is to use the file last used by currentcostgui"
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
    else:
        dev = sys.argv[1]
        if len(sys.argv) > 2:
            dbfile = sys.argv[2]
        else:
            #use file from currentcostgui
            c = open("currentcost.dat")
            dbfile = c.readline()
    db = CurrentCostDB()
    db.InitialiseDB(dbfile)
    s = serial.Serial(dev,  baudrate=57600)
    try:
        run(s, db)
    finally:
        #print db.GetMonthDataCollection()
        #print db.GetDayDataCollection()
        #print db.GetHourDataCollection()
        db.CloseDB()
        s.close()
   

