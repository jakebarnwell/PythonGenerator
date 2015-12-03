import os
import calendar
import logging

import wx
import wx.richtext
from wx.lib.intctrl import IntCtrl

from fno_strategy.strategy import MonthStrategy, AnalyzeThread
from fno_strategy.strategygraph import StrategyGraph

class StrategyEditor(wx.Dialog):
    def __init__(self, parent, strategy=None):
        wx.Dialog.__init__(self, parent)
        
        sizer = wx.GridSizer(5, 2)
        
        self.strategy = strategy
        
        if self.strategy is None:
            self.SetTitle("Add Strategy")
        else:
            self.SetTitle("Edit Strategy")
            
        self._name = wx.TextCtrl(self)
        self._fnoType = wx.ComboBox(self, choices=["future","call","put"])
        self._buyWeek = wx.ComboBox(self, choices=['0', '1', '2', '3', '4'])
        self._buyWeek.SetValue('0')
        self._sellWeek = wx.ComboBox(self, choices=['0', '1', '2', '3', '4'])
        self._sellWeek.SetValue('0')
        self._priceTarget = IntCtrl(self, min=-20, max=20)
        
        sizer.Add(wx.StaticText(self, label="Name:"))
        sizer.Add(self._name)
        
        sizer.Add(wx.StaticText(self, label="FnO Type:"))
        sizer.Add(self._fnoType)
        
        sizer.Add(wx.StaticText(self, label="Buy Week:"))
        sizer.Add(self._buyWeek)
        
        sizer.Add(wx.StaticText(self, label="Sell Week:"))
        sizer.Add(self._sellWeek)
        
        sizer.Add(wx.StaticText(self, label="Price Target %:"))
        sizer.Add(self._priceTarget)
        
        if self.strategy is None:
            label = "Add"
        else:
            label = "Edit"
        
        okBtn = wx.Button(self, id=wx.ID_OK, label=label)
        okBtn.Bind(wx.EVT_BUTTON, self._onOk)
        cancelBtn = wx.Button(self, id=wx.ID_CANCEL, label="Cancel")
        
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer.Add(okBtn)
        btnSizer.Add(cancelBtn)
        
        sizer.Add(btnSizer)
        
        self.update()
        self.SetSizerAndFit(sizer)
        
        self.Center()
        
    def update(self):
        if self.strategy is None:
            return
        
        for i, name in enumerate(['name', 'fnoType', 'buyWeek', 'sellWeek', 'priceTarget']):
            cntrl = getattr(self,  "_"+name)
            value = getattr(self.strategy, name)
            if isinstance(cntrl, IntCtrl):
                cntrl.SetValue(value)
            else:
                cntrl.SetValue(str(value))
            
    def getStrategy(self):
        strategy = MonthStrategy(self._name.GetValue(), 
                        buyWeek=self._buyWeek.GetValue(), 
                        sellWeek=self._sellWeek.GetValue(), 
                        fnoType=self._fnoType.GetValue(), 
                        priceTarget=self._priceTarget.GetValue())
        
        return strategy
    
    def _onOk(self, event):
        try:
            self.strategy = self.getStrategy()
        except Exception,e:
            wx.MessageBox(unicode(e), "Error")
            return
        
        self.EndModal(wx.ID_OK)
        
class StrategyPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        
        self._list = wx.ListView(self)
        self._list.InsertColumn(0,"Name")
        self._list.InsertColumn(1,"FnO Type")
        self._list.InsertColumn(2,"Buy Week")
        self._list.InsertColumn(3,"Sell Week")
        self._list.InsertColumn(4,"Price Target")
         
        self._log = wx.TextCtrl(self, size=(-1,200), style=wx.TE_MULTILINE)
        
        addBtn = wx.Button(self, label="Add Strategy")
        addBtn.Bind(wx.EVT_BUTTON, self._onAdd)
        editBtn = wx.Button(self, label="Edit Strategy")
        editBtn.Bind(wx.EVT_BUTTON, self._onEdit)
        delBtn = wx.Button(self, label="Delete Strategy")
        delBtn.Bind(wx.EVT_BUTTON, self._onDelete)
        
        self._dbFile = wx.TextCtrl(self, size=(300,-1))
        self._dbFile.Bind(wx.EVT_TEXT, self._updateModelWrapper('dbFile'))
        dbFileBtn = wx.Button(self, label="...")
        dbFileBtn.Bind(wx.EVT_BUTTON, self._onDbFileBtn)
        self._tableName = wx.TextCtrl(self)
        self._tableName.Bind(wx.EVT_TEXT, self._updateModelWrapper('tableName'))
        
        self._startMonth = wx.ComboBox(self, choices=list(calendar.month_abbr)[1:])
        self._startMonth.Bind(wx.EVT_COMBOBOX, self._updateModelWrapper('startMonth'))
        self._startYear = wx.ComboBox(self, choices=map(str,range(2001,2011)))
        self._startYear.Bind(wx.EVT_COMBOBOX, self._updateModelWrapper('startYear'))
        self._endMonth = wx.ComboBox(self, choices=list(calendar.month_abbr)[1:])
        self._endMonth.Bind(wx.EVT_COMBOBOX, self._updateModelWrapper('endMonth'))
        self._endYear = wx.ComboBox(self, choices=map(str,range(2001,2011)))
        self._endYear.Bind(wx.EVT_COMBOBOX, self._updateModelWrapper('endYear'))
        self.analyzeBtn = analyzeBtn = wx.Button(self, label="Start")
        analyzeBtn.Bind(wx.EVT_BUTTON, self._onAnalyze)
        
        border=4
        topSizer = wx.BoxSizer(wx.HORIZONTAL)
        topSizer.Add(addBtn, border=border, flag=wx.RIGHT)
        topSizer.Add(editBtn, border=border, flag=wx.RIGHT)
        topSizer.Add(delBtn)
        
        middleSizer = wx.BoxSizer(wx.HORIZONTAL)
        middleSizer.Add(wx.StaticText(self, label="DB File:"), border=border, flag=wx.RIGHT)
        middleSizer.Add(self._dbFile, border=border, flag=wx.RIGHT)
        middleSizer.Add(dbFileBtn, border=border, flag=wx.RIGHT)
        middleSizer.Add(wx.StaticText(self, label="symbol:"), border=border, flag=wx.RIGHT)
        middleSizer.Add(self._tableName, border=border)
        
        bottomSizer = wx.BoxSizer(wx.HORIZONTAL)
        bottomSizer.Add(wx.StaticText(self, label="Analyze From "), border=border, flag=wx.RIGHT)
        bottomSizer.Add(self._startMonth, border=border, flag=wx.RIGHT)
        bottomSizer.Add(self._startYear, border=border, flag=wx.RIGHT)
        bottomSizer.Add(wx.StaticText(self, label=" to "), border=border, flag=wx.RIGHT)
        bottomSizer.Add(self._endMonth, border=border, flag=wx.RIGHT)
        bottomSizer.Add(self._endYear, border=border, flag=wx.RIGHT)
        bottomSizer.Add(analyzeBtn)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(topSizer, border=border, flag=wx.ALL|wx.EXPAND,)
        sizer.Add(self._list, proportion=1, flag=wx.ALL|wx.EXPAND, border=border)
        sizer.Add(middleSizer, border=border, flag=wx.ALL|wx.EXPAND,)
        sizer.Add(bottomSizer, border=border, flag=wx.ALL|wx.EXPAND,)
        sizer.Add(self._log, border=border, flag=wx.ALL|wx.EXPAND,)
        self.SetSizer(sizer)
        
        self.model = None
        self._analysis_thread = None
        self._lastLogs = []
        
    def setModel(self, model):
        self.model = model
        self.updateFromModel()
        
    def updateFromModel(self):
        self._list.DeleteAllItems()
        for strategy in self.model.get_strategy_list():
            self.addStrategy(strategy)
            
        for name in ['startMonth', 'startYear', 'endMonth', 'endYear', 'dbFile', 'tableName']:
            cntrl = getattr(self, "_"+name)
            value = getattr(self.model, name)
            if hasattr(cntrl, 'ChangeValue'):
                cntrl.ChangeValue(str(value))
            else:
                cntrl.SetValue(str(value))
            
    def updateModel(self):
        strategy_list = []
        for i in range(self._list.GetItemCount()):
            strategy_list.append(self.getStrategy(i))
        self.model.set_strategy_list(strategy_list)
        
    def addStrategy(self, strategy):
        num_items = self._list.GetItemCount()
        self._list.InsertStringItem(num_items, strategy.name)
        self.updateStrategy(num_items, strategy) 
            
    def updateStrategy(self, item, strategy):
        for i, name in enumerate(['name', 'fnoType', 'buyWeek', 'sellWeek', 'priceTarget']):
            self._list.SetStringItem(item, i, str(getattr(strategy, name)))
            
    def getStrategy(self, item):
        strategy = self.model.get_strategy_list()[item]
        return strategy
    
    def _updateModelWrapper(self, varname):
        def _wrapper(event):
            cntrl = getattr(self, "_"+varname)
            value = cntrl.GetValue()
            setattr(self.model, varname, value)
            
        return _wrapper
    
    def _onDbFileBtn(self, event):
        dlg = wx.FileDialog(
                self, message="Set db file",
                defaultDir=".",
                defaultFile="",
                wildcard="sqlite3 db(*.db)|*.db",
                style=wx.OPEN |wx.CHANGE_DIR
                )
    
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return

        path = os.path.abspath(dlg.GetPath())
        self.model.dbFile=path
        self._dbFile.SetValue(path)
        dlg.Destroy()
        
    def _onAnalyze(self, event):
        if self._analysis_thread is not None and self._analysis_thread.isAlive():
            wx.MessageBox("Analysis already in progress", "Analyze Error")
            return
        
        if not self.model.get_strategy_list():
            wx.MessageBox("No strategies to evaluate.", "Analyze Error")
            return
        
        self._analysis_thread = AnalyzeThread(self.model, self.logFunc, self.onAnalysisDone)
        self._analysis_thread.start()
        self.analyzeBtn.Enable(False)
   
    def onAnalysisDone(self, model, strategy_data, error=None):
        self.analyzeBtn.Enable(True)
        if error:
            wx.MessageBox(error)
        else:
            stragtegygraph = StrategyGraph(self, model, strategy_data)
            stragtegygraph.Show()
        
    def logFunc(self, msg, severity=logging.INFO):
        colors = {"info": (0,0,200),
                  "debug": (200,200,200),
                  "error": ("200,0,0")}
                  
        try:
            clr = colors[severity]
        except KeyError:
            clr = (0,0,0)
            
        logging.log(severity, msg)
            
        if severity > logging.DEBUG:
            self._lastLogs.insert(0, "%s : %s\n"%(severity, msg))
            
            if len( self._lastLogs) > 200:
                self._lastLogs =  self._lastLogs[100:]
                
            curText = "\n".join( self._lastLogs)
            self._log.SetValue(curText)
        
    def _onAdd(self, event):
        dlg = StrategyEditor(self)
        if dlg.ShowModal() == wx.ID_OK:
            strategy = dlg.getStrategy()
            self.model.add_strategy(strategy)
            self.updateFromModel()
            
    def _onEdit(self, event):
        item = self._list.GetFocusedItem()
        if item < 0:
            wx.MessageBox("Select a strategy to edit", "Error")
            return
        
        strategy = self.getStrategy(item)
        
        dlg = StrategyEditor(self, strategy)
        if dlg.ShowModal() == wx.ID_OK:
            strategy = dlg.getStrategy()
            self.model.update_strategy(item, strategy)
            self.updateFromModel()
            
    def _onDelete(self, event):
        item = self._list.GetFocusedItem()
        if item < 0:
            wx.MessageBox("Select a strategy to delete", "Error")
            return
        
        self._list.DeleteItem(item)
        self.updateModel()
    