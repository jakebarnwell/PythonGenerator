import wx
import sys
import calendar
import threading
import datetime
import sqlite3
import traceback
import logging
from dateutil import rrule

class MonthStrategy(object):
    def __init__(self, name, fnoType, buyWeek, sellWeek, priceTarget):
        self.name = name
        self.buyWeek = buyWeek # 0 = no buy, 1 = 1st week of month , 2, 3, 4th week of month
        self.sellWeek = sellWeek # 0 = no sell, 1 = 1st week, 2, 3, 4 etc
        self.fnoType = fnoType # future, put, call
        self.priceTarget = priceTarget # percentage from future price on buy or sell date
        
        self._price = None # will be set once bought or sold based on priceTarget
        self._bought = False
        self._sold = False
        
        self.check()
        
    def __str__(self):
        values = []
        for displayName, name in [('Name', 'name'), ('Buy Week', 'buyWeek'), ('Sell Week', 'sellWeek'),
                     ('Fno Type', 'fnoType'), ('Price Target', 'priceTarget')]:
            values.append("%s: %s"%(displayName, getattr(self, name)))
        return "\n".join(values)
    
    def check(self):
        self.name = self.name.strip()
        if not self.name.strip():
            raise Exception("Name can not be empty")
        
        self.buyWeek = int(self.buyWeek)
        if 0 > self.buyWeek > 4:
            raise Exception("Buy Week should be between 0-4")
            
        self.sellWeek = int(self.sellWeek)
        if 0 > self.sellWeek > 4:
            raise Exception("Sell Week should be between 0-4")
            
        self.fnoType = self.fnoType.strip()
        if self.fnoType not in ['future', 'call', 'put']:
            raise Exception("FnO Type must be future, call or put")
        
        self.priceTarget = int(self.priceTarget)
        if -20 > self.priceTarget > 20:
            raise Exception("Price Target must be between -20% to 20%")
        
    def analyze_month_data(self, monthsDates, expiryDateTag, weekDates, futureData, callData, putData, logFunc):
        logFunc("  strategy %s"%self.name)
        results = []
        
        for timestamp in monthsDates:
        
            if not self._bought and self.buyWeek > 0 and timestamp >= weekDates[self.buyWeek-1] and timestamp < weekDates[self.buyWeek]:
                price = self._buy_sell(True, timestamp, futureData, callData, putData)
                if price is not None:
                    self._bought = True
                    if self.fnoType == 'future':
                        results.append((timestamp, price))
                    else:
                        results.append((timestamp, -price)) # buy of call is loss
                        
                    
            if not self._sold and self.sellWeek > 0 and timestamp >= weekDates[self.sellWeek-1] and timestamp < weekDates[self.sellWeek]:
                price = self._buy_sell(False, timestamp, futureData, callData, putData)
                if price is not None:
                    self._sold = True
                    if self.fnoType == 'future':
                        results.append((timestamp, -price))
                    else:
                        results.append((timestamp, price)) # sell of call is profit
                    
        # if put or call check if requested action happend
        if self.fnoType != 'future':
            if self.buyWeek > 0 and not self._bought:
                raise AnalyzeException("%s could not be bought"%self)
            
            if self.sellWeek > 0 and not self._sold:
                raise AnalyzeException("%s could not be sold"%self)
            
            futurePrice = futureData[expiryDateTag]
            # if squareoff was not set do expiry
            if self._price is not None and self.sellWeek == 0:
                # only profit matters
                if self.fnoType == 'put' and futurePrice < self._price:
                    results.append((expiryDateTag, self._price - futurePrice))
                   
                if self.fnoType == 'call' and futurePrice > self._price:
                    results.append((expiryDateTag, futurePrice - self._price))
                    
            if self._price is not None and self.buyWeek == 0:
                # only loss matters
                if self.fnoType == 'put' and futurePrice < self._price:
                    results.append((expiryDateTag, futurePrice-self._price))
                   
                if self.fnoType == 'call' and futurePrice > self._price:
                    results.append((expiryDateTag, self._price - futurePrice))
        
        return results
                    
    def _buy_sell(self, buy, timestamp, futureData, callData, putData):
        strike_price = (futureData[timestamp]['OPEN'] +futureData[timestamp]['CLOSE'])/2.0
        if self.fnoType == 'future':
            return strike_price
    
        if self._price is not None: # means we already executed one buy or sell
            strike_price = self._price
        else:
            if self.fnoType == 'put':
                # for put set strike price below by priceTarget
                strike_price = strike_price - strike_price*self.priceTarget/100.0
            else:
                # for call set strike price above by priceTarget
                strike_price = strike_price + strike_price*self.priceTarget/100.0
            
        if self.fnoType == 'put':
            day_data = putData[timestamp]
        else:
            day_data = callData[timestamp]
            
        # check if any put or call matches on that day
        for data in day_data:
            price = data['STRIKE_PR']
            # both high low open close should be non zero also change_oi
            for var in ['OPEN', 'CLOSE', 'HIGH', 'LOW', 'CHANGE_OI']:
                if data[var] == 0:
                    continue
                
            premium = (data['OPEN'] + data['CLOSE'])/2.0
            
            if self.fnoType == 'put' and strike_price <= price:
                return premium
            
            if self.fnoType == 'call' and strike_price >= price:
                return premium
        
        return None

    
    
class AnalyzeException(Exception): pass

def analyze(model, logFunc):
    months = list(calendar.month_abbr)
    startMonth = months.index(model.startMonth)
    startDate = datetime.datetime(int(model.startYear), startMonth, 1)
    
    endMonth = months.index(model.endMonth)
    firstWeekday, days = calendar.monthrange(int(model.endYear), endMonth)
    endDate = datetime.datetime(int(model.endYear), endMonth, days)
           
    if endDate < startDate:
        raise AnalyzeException("End date must > start date")
    
    if endDate.year == startDate.year and endDate.month - startDate.month < 2:
        raise AnalyzeException("Start and end date should be atleast 2 months apart")
        
    startDateStr = startDate.strftime("%Y-%m-%d")
    endDateStr = endDate.strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(model.dbFile)
    cursor = conn.cursor()
    
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
    column_str = ",".join(column_names)
    sql = "select %s from %s where TIMESTAMP >= ? and TIMESTAMP <= ? order by TIMESTAMP"%(column_str, model.tableName)
    
    count = 0
    logFunc("Analyzing...%s  - %s"%(startDateStr, endDateStr))
    
    expiryDates = list(rrule.rrule(rrule.MONTHLY, byweekday=rrule.TH(-1), dtstart=startDate).between(startDate, endDate, inc=True))
    expiryDatesTagMap = {}
    for expiryDate in expiryDates:
        expiryDatesTagMap[expiryDate.strftime("%Y-%m-%d")] = expiryDate
        
    monthsData = [] # keep each month's data, month is from expiry to expiry
    lastDateTag = None

    strategy_data = {}
    for i, strategy in  enumerate(model.get_strategy_list()):
        strategy_data[i] = []
            
    for row in cursor.execute(sql, [startDateStr, endDateStr]):
        count += 1
        data = dict(zip(column_names, row))

        curDateTag  = data['TIMESTAMP']
        if curDateTag not in expiryDatesTagMap and lastDateTag in expiryDatesTagMap: # expirty date passed
            analyze_month_data(monthsData, model, strategy_data, lastDateTag, logFunc)
            monthsData = []
            
        monthsData.append(data)
        lastDateTag =  curDateTag
    logFunc("read %s rows"%count)
    
    # strategy_data is map of index and data, just get data out in sequence
    strategy_data = strategy_data.items()
    strategy_data.sort()
    strategy_data = [item[1] for item in strategy_data]
    
    return strategy_data

def analyze_month_data(monthsData, model, strategy_data, expiryDateTag, logFunc):
    startDateTag = monthsData[0]['TIMESTAMP']
    endDateTag = monthsData[-1]['TIMESTAMP']
    logFunc("month:%s  expiry: %s "%(startDateTag, endDateTag))
    if endDateTag != expiryDateTag:
        raise AnalyzeException("Last day of month %s is not same as expiry %s"%(endDateTag, expiryDateTag))
    
    # calculate week dates by dividing month equally in 4 parts
    startDate = datetime.datetime.strptime(startDateTag, "%Y-%m-%d")
    endDate = datetime.datetime.strptime(endDateTag, "%Y-%m-%d")
    
    delta = endDate - startDate
    weekDays = (delta.days+1)/4
    weekDelta = datetime.timedelta(days=weekDays)
    
    # weekdates split month in four part where each part : weekStart <= day < weekEnd
    weekDates = [startDateTag]
    weekDate = startDate
    for i in range(3):
        weekDate = weekDate + weekDelta
        weekDates.append(weekDate.strftime("%Y-%m-%d"))
    # increment last day so that day >= start and day < end is valid
    endWeekDate = endDate + datetime.timedelta(days=1)
    weekDates.append(endWeekDate.strftime("%Y-%m-%d"))
    
    logFunc("weekDates: %s"%weekDates, logging.DEBUG)
    
    # make a map of month date and future, put, call data
    futureData = {}
    callData = {}
    putData = {}
    for data in monthsData:
        # only get current month data
        if data['EXPIRY_DT'] != expiryDateTag:
            continue
        
        timestamp = data['TIMESTAMP']
        if data['OPTION_TYP'] == 'PE':
            if timestamp not in putData:
                putData[timestamp] = []
            putData[timestamp].append(data)
        elif data['OPTION_TYP'] == 'CE':
            if timestamp not in callData:
                callData[timestamp] = []
            callData[timestamp].append(data)
        else:
            futureData[timestamp] = data
    
    monthsDates = list(set(futureData.keys()+callData.keys()+putData.keys()))
    monthsDates.sort()
    
    for i, strategy in  enumerate(model.get_strategy_list()):
        profit_data = strategy.analyze_month_data(monthsDates, expiryDateTag, weekDates, futureData, callData, putData, logFunc)
        if profit_data:
            strategy_data[i].extend(profit_data)
     
class AnalyzeThread(threading.Thread):
    def __init__(self, model, logFunc, onAnalysisDone):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.model = model
        self.logFunc = logFunc
        self.onAnalysisDone = onAnalysisDone
        
    def run(self):
        try:
            strategy_data  = analyze(self.model, self.logFunc)
            wx.CallAfter(self.onAnalysisDone, self.model, strategy_data)
        except AnalyzeException,e:
            self.logFunc(unicode(e), logging.ERROR)
            wx.CallAfter(self.onAnalysisDone, self.model, None, unicode(e))
        except Exception,e:
            self.logFunc(unicode(e), logging.ERROR)
            self.logFunc(traceback.format_exc(), logging.ERROR)
            wx.CallAfter(self.onAnalysisDone, self.model, None, unicode(e))
            
            
    
        