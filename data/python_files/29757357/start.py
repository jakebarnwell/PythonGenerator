import wx
import time
from threading import Thread
import os
import glob
import sys
from datetime import datetime
from pysqlite2 import dbapi2 as sqlite
import atexit
import sys
# get the platfrom type
ostype = sys.platform


# store the main process id
g_processid = os.getpid()
# print " pid=> "+str(g_processid)

# check for windows
if 'win' in ostype:
    import win32api
    import win32con
    
def terminateparentprocess():
    print "terminating process id on exit"
    handle = win32api.OpenProcess( win32con.PROCESS_TERMINATE, 0, g_processid)
    win32api.TerminateProcess( handle, 0 )
    win32api.CloseHandle( handle )
    
atexit.register(terminateparentprocess)        

def close_connection(some_con):
    some_con.commit()
    some_con.close()
    
class MyFrame(wx.Frame):

    #global value to store index
    g_fileclickedindex=0 
    mypath = "";
    
    def OnDelete(self, event):
        filename = self.lc.GetItemText(self.g_fileclickedindex)
        # display the text
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM filenames')
        for row in cursor:
            extn = row[4]
            if extn == "chars":
                fullfilename = row[1]+row[2]
                if fullfilename == filename:
                    cursor = connection.cursor()
                    connection.commit()
                    cursor.execute('delete from filenames where filename = ? and modifiedFilename = ?'
                                   ,(row[1], row[2]))
                    dlg = wx.MessageDialog( self, "filename deleted from database", "Important",wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    self.lc.DeleteItem(self.g_fileclickedindex)
            if extn == "exact":
                if row[1] == filename:
                    cursor = connection.cursor()
                    connection.commit()
                    cursor.execute('delete from filenames where filename = ?',[row[1]])
                    dlg = wx.MessageDialog( self, "filename deleted from database", "Important",wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    self.lc.DeleteItem(self.g_fileclickedindex)
            if extn == "extn":
                if row[2] == filename:
                    cursor = connection.cursor()
                    connection.commit()
                    cursor.execute('delete from filenames where filename = ?',[row[1]])
                    dlg = wx.MessageDialog( self, "filename deleted from database", "Important",wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    self.lc.DeleteItem(self.g_fileclickedindex)
                    
    def OnSelect(self, event):
        window = self.FindWindowByName('Filenames')
        index = event.GetIndex()
        self.g_fileclickedindex = index
        filename = self.lc.GetItemText(index)
        # display the text
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM filenames')
        bDeleteButton=False;
        wx.StaticText(self.pnl3, -1, "                                                             ",
                                  (10, 25), style=wx.ALIGN_LEFT)
        
        for row in cursor:
            extn = row[4]
            if extn == "chars":
                fullfilename = row[1]+row[2]
                if fullfilename == filename:
                    bDeleteButton=True;
                    fulldisplaytext = "File name: "+str(filename)
                    wx.StaticText(self.pnl3, -1, fulldisplaytext,
                                  (10, 25), style=wx.ALIGN_LEFT)
                    wx.StaticText(self.pnl3, -1,
                                  "Your file will be deleted every : "+str(row[3])+" minutes",
                                  (10, 65), style=wx.ALIGN_LEFT)
            if extn == "exact":
                if row[1] == filename:
                    bDeleteButton=True;
                    wx.StaticText(self.pnl3, -1, "File name: "+str(filename),
                                  (10, 25), style=wx.ALIGN_LEFT)
                    wx.StaticText(self.pnl3, -1,
                                  "Your file will be deleted every : "+str(row[3])+" minutes",
                                  (10, 65), style=wx.ALIGN_LEFT)
            if extn == "extn":
                if row[2] == filename:
                    bDeleteButton=True;
                    wx.StaticText(self.pnl3, -1, "File name: "+str(filename),
                                  (10, 25), style=wx.ALIGN_LEFT)
                    wx.StaticText(self.pnl3, -1,
                                  "Your file will be deleted every : "+str(row[3])+" minutes",
                                  (10, 65), style=wx.ALIGN_LEFT)
        if bDeleteButton==True:
            self.bbutton = wx.Button(self.pnl3, 1, 'I no longer want to delete this file.', (30, 85), (200, -1))
            self.bbutton.Bind(wx.EVT_BUTTON, self.OnDelete, id=1)
        
    def __init__(self, parent, id, title):          
        wx.Frame.__init__(self, parent, id, title)
        menubar = wx.MenuBar()
        file = wx.Menu()
        edit = wx.Menu()
        help = wx.Menu()

        file.Append(101, '&Open', 'Open a new document')
        self.fileReset = file.Append(102, '&Reset Database', 'Reset the database')
        self.Bind(wx.EVT_MENU, self.menuFileReset, self.fileReset)
        file.AppendSeparator()
        quit = wx.MenuItem(file, 105, '&Quit\tCtrl+Q', 'Quit the Application')
        wx.EVT_MENU(self, 105, self.OnQuit )

        self.about = help.Append(102, '&About', 'About')
        self.Bind(wx.EVT_MENU, self.OnAbout, self.about)
        
        file.AppendItem(quit)
        
        menubar.Append(file, '&File')
        menubar.Append(edit, '&Edit')
        menubar.Append(help, '&Help')
        self.SetMenuBar(menubar)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.pnl1 = wx.Panel(self, -1, style=wx.SIMPLE_BORDER)
        self.pnl2 = wx.Panel(self, -1, style=wx.SIMPLE_BORDER)
        self.pnl3 = wx.Panel(self, -1, style=wx.SIMPLE_BORDER)

        wx.StaticBox(self.pnl3, -1, 'File Information', (5, 5), size=(240, 170))
        
        # add the list field to display file names
        self.lc = wx.ListCtrl(self.pnl2, id=-1, size=(280,400),style=wx.LC_REPORT)
        self.lc.InsertColumn(0, 'Files 2 be deleted')
        self.lc.SetColumnWidth(0, 400)
        self.lc.SetName('Filenames')
        
        # display the file names in the list
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM filenames')
        for row in cursor:
            localfname = row[1]
            extn = row[4]
            if extn == "chars":
                localfname = row[1]+row[2]
            num_items = self.lc.GetItemCount() 
            self.lc.InsertStringItem(num_items, localfname)
            self.lc.SetStringItem(num_items, 1, localfname)
            
        # on selecting an item in the list control
        self.lc.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelect)
            
        # add the button
        m_addfiles = wx.Button(self.pnl1, 1, "Browse", (40, 30))
        m_addfiles.Bind(wx.EVT_BUTTON, self.openfile)
        
        m_text = wx.StaticText(self.pnl1, -1, label="File: ",pos=(10,10),name="File: ")
        m_text.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL))
        m_text.SetSize(m_text.GetBestSize())

        # text to write the file name
        self.m_filename = wx.TextCtrl(self.pnl1, -1, pos=(38, 8), size=(150, 20))

        # checkbox for comparing exact filename
        self.cb = wx.CheckBox(self.pnl1, -1, 'Delete exact filename', (38, 60))
        self.cb.SetValue(True)
        wx.EVT_CHECKBOX(self, self.cb.GetId(), self.uncheckothers1)
        
        # checkbox for extensions
        self.cb1 = wx.CheckBox(self.pnl1, -1, 'Delete extensions. (*.txt)', (38, 80))
        self.cb1.SetValue(False)
        wx.EVT_CHECKBOX(self, self.cb1.GetId(), self.uncheckothers2)
         
        # checkbox for number of chars to delete
        self.cb2 = wx.CheckBox(self.pnl1, -1, "Delete with "+
                               "number of chars. (vc*.txt) ",
                               (38, 100))
        self.cb2.SetValue(False)
        wx.EVT_CHECKBOX(self, self.cb2.GetId(), self.showText)

        # set the radio button
        self.rb1 = wx.RadioButton(self.pnl1, -1, 'Hourly', (40, 180), style=wx.RB_GROUP)
        self.rb2 = wx.RadioButton(self.pnl1, -1, '24 Hour', (40, 200))
        self.rb3 = wx.RadioButton(self.pnl1, -1, 'Every 30 minutes', (40, 220))

        # add slider
        self.sld = wx.Slider(self.pnl1, -1, value=1, minValue=1, maxValue=50,
                             pos=(38,120), size=(150, -1),
                             style = wx.SL_HORIZONTAL | wx.SL_LABELS)
        
        # button for adding the files to the list
        self.m_finaladdfiles = wx.Button(self.pnl1, 1, "ADD FILE", (40, 240))
        self.m_finaladdfiles.Bind(wx.EVT_BUTTON, self.addtodb)
        
        hbox.Add(self.pnl1, 1, wx.EXPAND | wx.ALL, 3)
        hbox.Add(self.pnl2, 1, wx.EXPAND | wx.ALL, 3)
        hbox.Add(self.pnl3, 1, wx.EXPAND | wx.ALL, 3)
        self.SetSize((800, 400))
        self.SetSizer(hbox)
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText('Welcome to SpaceClaimer. Please refer help.')
        self.Centre()

    def OnAbout(self, event):
        dlg = wx.MessageDialog(self, 'K M Darshan\t\n' '2011\t', 'About',
                 wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
            
    def OnQuit(self, event):
        close_connection(connection)
        # self.tskic.Destroy()
        self.Close()
        handle = win32api.OpenProcess( win32con.PROCESS_TERMINATE, 0, g_processid)
        win32api.TerminateProcess( handle, 0 )
        win32api.CloseHandle( handle )
        
    def menuFileReset(self,event):
        dlg = wx.MessageDialog( self, "Database will be reset", "Important",wx.OK)
        dlg.ShowModal()
        dlg.Destroy()
        cursor = connection.cursor()
        # dont drop the db, you will have problems
        # creating the database table
        # cursor.execute('drop table if exists filenames')
        cursor.execute('delete from filenames')
        self.lc.DeleteAllItems()
        # cursor.execute('SELECT * FROM filenames')
        # print cursor.fetchall()
        connection.commit()
        # close_connection(connection)
        
    def uncheckothers1(self,event):
        self.cb2.SetValue(False)
        self.cb1.SetValue(False)
        
    def uncheckothers2(self,event):
        self.cb.SetValue(False)
        self.cb2.SetValue(False)
        
    def showText(self,event):
        # fonts = ['1','2','3','4','5','6','7','8','9']
        # self.chars = wx.ComboBox(self.pnl1, -1, value = '1',
        #                        pos=(38,120),
        #                       choices=fonts, size=(100, -1),
        #                      style=wx.CB_DROPDOWN)
        
        # self.sld = wx.Slider(self.pnl1, -1, value=1, minValue=1, maxValue=50,
        #                     pos=(38,120), size=(150, -1),
        #                     style = wx.SL_HORIZONTAL | wx.SL_LABELS)
                        
                             # style = wx.SL_AUTOTICKS | wx.SL_HORIZONTAL |
                             # wx.SL_LABELS)
        self.cb.SetValue(False)
        self.cb1.SetValue(False)
        self.statusbar.SetBackgroundColour("RED")
        self.statusbar.SetStatusText('Eg: file name-> apple.txt. If you select 2 using the slider, it will be ap*.txt. All files starting with \'ap\' and with extensions .txt will be deleted.')
        
    def openfile(self, event):
         dlg = wx.FileDialog(self, "Choose a file", os.getcwd(), "", "*.*", wx.OPEN)
         if dlg.ShowModal() == wx.ID_OK:
              path = dlg.GetPath()
              mypath = os.path.basename(path)
              fullname = dlg.GetDirectory() + "\\" +dlg.GetFilename()
              self.m_filename.SetValue(fullname)
              #self.m_filename.write(fullname)
         dlg.Destroy()

    def addtodb(self, event):
        localfilename = ""
        cursor = connection.cursor()
        localfilename = self.m_filename.GetValue()
        if len(localfilename) < 1:
            return
        bfilename = self.cb.GetValue()
        bextn = self.cb1.GetValue()
        bchars = self.cb2.GetValue()

                
        # check the radio buttons
        brb1 = self.rb1.GetValue()
        brb2 = self.rb2.GetValue()
        brb3 = self.rb3.GetValue()
        timelimit = 60
        if brb1 == True:
            timelimit=60 # hourly
        if brb2 == True:
            timelimit=24 # daily
        if brb3 == True:
            timelimit=30 # weekly
                
        # check for what type of file you need to delete
        if bfilename == True:
            cursor.execute('SELECT * FROM filenames')
            for row in cursor:
                if row[1] == localfilename and row[4] == "exact":
                    dlg = wx.MessageDialog( self, "Exact filename already in database, try different option",
                                            "Important",wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    return
            valtype = "exact"
            cursor.execute('INSERT INTO filenames VALUES (null, ?, ?, ?, ?)',
                           (localfilename, localfilename, timelimit,valtype))
            connection.commit()
            # close_connection(connection)
            num_items = self.lc.GetItemCount() 
            self.lc.InsertStringItem(num_items, localfilename)
            # self.lc.SetStringItem(num_items, 1, localfilename)

        if bextn == True:
            # split extension
            valtype = "extn"
            fileName, fileExtension = os.path.splitext(localfilename)
            pos = unicode.rfind(localfilename, u"\\")
            tempfilename = fileName[0:pos+1]
            
            # we get the full filename and extn
            tempfilename = tempfilename+"*"+fileExtension
            cursor.execute('SELECT * FROM filenames')
            for row in cursor:
                if row[1] == localfilename and row[4] == "extn":
                    dlg = wx.MessageDialog( self, "Exact extension filename already in database, try different option",
                                            "Important",wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    return
           
            cursor.execute('INSERT INTO filenames VALUES (null, ?, ?, ?,?)',
                           (localfilename, tempfilename, timelimit, valtype))
            connection.commit()
            num_items = self.lc.GetItemCount() 
            self.lc.InsertStringItem(num_items, tempfilename)
            # close_connection(connection)
            
        if bchars == True:
            valtype = "chars"
            nchars = self.sld.GetValue()
            # split extension
            fileName, fileExtension = os.path.splitext(localfilename)
            pos = unicode.rfind(localfilename, u"\\")
            posextn = unicode.rfind(localfilename, fileExtension)
            tempfilename = fileName[pos+1: posextn]
            tempfulldir = fileName[0:pos+1]
            # print tempfulldir
            # must be less than the size of filename
            if nchars < len(tempfilename)-1 :
                tempfilename = tempfilename[0:nchars]
                tempfilenameExtn = tempfilename + "*" + fileExtension
                tempFullfilename = tempfulldir + tempfilenameExtn
                cursor.execute('SELECT * FROM filenames')
                bEmptydb = True

                for row in cursor:
                    bEmptydb = False
                    tempdbname = row[1] + row[2]
                    if tempdbname == tempFullfilename:
                        # we really dont want the same values
                        dlg = wx.MessageDialog( self, "Exact filename already in database, try different option",
                                            "Important",wx.OK)
                        dlg.ShowModal()
                        dlg.Destroy()
                        return
                cursor.execute('INSERT INTO filenames VALUES (null, ?,?,?,?)',
                           (tempfulldir, tempfilenameExtn, timelimit,valtype))
                connection.commit()
                num_items = self.lc.GetItemCount() 
                self.lc.InsertStringItem(num_items,
                                         tempfulldir+tempfilenameExtn)
                # incase of empty db
                if bEmptydb == True:
                    cursor.execute('INSERT INTO filenames VALUES (null, ?, ?, ?, ?)',
                           (tempfulldir, tempfilenameExtn, timelimit, valtype))
                    connection.commit()
                    num_items = self.lc.GetItemCount() 
                    self.lc.InsertStringItem(num_items,
                                             tempFullfilename)
                    
        # close_connection(connection)       
        #cursor.execute('SELECT * FROM filenames')
        #print cursor.fetchall()

# helper method to delete the files with extensions
# typeDeletion etxn/chars
def helper_delete_files(typeDeletion, tempfilenamewithextn, localfilename):
    listExtn = []
    # delete the extn
    fileName, fileExtension = os.path.splitext(localfilename)
    pos = unicode.rfind(localfilename, "\\")
    tempfilename = fileName[0:pos+1]
    # get the extension
    if typeDeletion == "extn":
        fileExtension = "*"+fileExtension
    elif typeDeletion == "chars": 
        fileExtension = tempfilenamewithextn
    listExtn.append(fileExtension)
    print listExtn
    # delete all files in this directory
    files_removed = 0
    file_list = []
    for root, dirs, files in os.walk(tempfilename):
        for trace in listExtn:
            win_trace_path = os.path.join(root, trace)
            for filename in glob.glob(win_trace_path):
                if os.path.exists(filename):
                    print filename
                    file_list.append(filename)
                else:
                    print 'No files found'
        for file in file_list:
            print "removing " + file
            if os.path.isfile(file):
                os.remove(file)
                files_removed += 1
    
# query database and delete the files
def querydb():
    while True:
        localtime = datetime.now()
        localmin = localtime.minute
        local24 = localtime.hour
        # print localmin
        print " "
        # deletion every half an hour
        if localmin == 30 or localmin == 59:
            connection = sqlite.connect('spaceclaimer.db')
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM filenames')
            for row in cursor:
                if row[3] == 60:
                    localfilename = row[1]
                    # get the deletion type of the file
                    deletiontype = row[4]
                    print deletiontype
                    if deletiontype == "exact":
                        if os.path.exists(localfilename):
                            os.remove(localfilename)
                    elif deletiontype == "extn":
                        print "deleting files with extension"
                        helper_delete_files("extn", "",localfilename)
                    elif deletiontype == "chars":
                        # test*.txt
                        tempfilenamewithextn = row[2]
                        print "deleting files with chars"
                        helper_delete_files("chars", tempfilenamewithextn, localfilename)
        # deletion every hour
        if localmin == 58:
            connection = sqlite.connect('spaceclaimer.db')
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM filenames')
            for row in cursor:
                if row[3] == 60:
                    localfilename = row[1]
                    # get the deletion type of the file
                    deletiontype = row[4]
                    print deletiontype
                    if deletiontype == "exact":
                        if os.path.exists(localfilename):
                            os.remove(localfilename)
                    elif deletiontype == "extn":
                        print "deleting files with extension"
                        helper_delete_files("extn", "",localfilename)
                    elif deletiontype == "chars":
                        # test*.txt
                        tempfilenamewithextn = row[2]
                        print "deleting files with chars"
                        helper_delete_files("chars", tempfilenamewithextn, localfilename)
        if local24 == 24 and localmin > 55:
            listExtn = []
            connection = sqlite.connect('spaceclaimer.db')
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM filenames')
            for row in cursor:
                if row[3] == 24:
                    localfilename = row[1]
                    # get the deletion type of the file
                    deletiontype = row[4]
                    print deletiontype
                    if deletiontype == "exact":
                        if os.path.exists(localfilename):
                            os.remove(localfilename)
                    elif deletiontype == "extn":
                        print "deleting files with extension"
                        helper_delete_files("extn", "",localfilename)
                    elif deletiontype == "chars":
                        # test*.txt
                        tempfilenamewithextn = row[2]
                        print "deleting files with chars"
                        helper_delete_files("chars", tempfilenamewithextn, localfilename)
        time.sleep(3)
        
                        
# create a dummy thread
def createdummythread():
    while True:
        time.sleep(20)
        t = Thread(target=querydb)
        t.start()

class MyTaskBarIcon(wx.TaskBarIcon):
    def __init__(self, frame):
        wx.TaskBarIcon.__init__(self)

        self.frame = frame
        self.SetIcon(wx.Icon('refresh-icon.png', wx.BITMAP_TYPE_PNG), 'mytaskbaricon.py')
        #self.Bind(wx.EVT_MENU, self.OnTaskBarActivate, id=1)
        #self.Bind(wx.EVT_MENU, self.OnTaskBarDeactivate, id=2)
        self.Bind(wx.EVT_MENU, self.OnTaskBarClose, id=1)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        # menu.Append(1, 'Show')
        # menu.Append(2, 'Hide')
        menu.Append(1, 'Close')
        return menu

    def OnTaskBarClose(self, event):
        handle = win32api.OpenProcess( win32con.PROCESS_TERMINATE, 0, g_processid)
        win32api.TerminateProcess( handle, 0 )
        win32api.CloseHandle( handle )

    def OnTaskBarActivate(self, event):
        if not self.frame.IsShown():
            self.frame.Show()

    def OnTaskBarDeactivate(self, event):
        if self.frame.IsShown():
            self.frame.Hide()
            
class MyApp(wx.App):
    def OnInit(self):
        # init the database
        cursor = connection.cursor()
        cursor.execute('CREATE TABLE if not exists filenames \
                        (id INTEGER PRIMARY KEY, \
                        filename VARCHAR(500), modifiedFilename VARCHAR(500), \
                        timelimit INT, typeofdeletion VARCHAR(10))')
        self.tskic = MyTaskBarIcon(self)
        connection.commit()
        self.frame = MyFrame(None, -1, 'space claimer')
        self.frame.Show(True)
        t = Thread(target=querydb)
        t.start()
        return True

# create the database
connection = sqlite.connect('spaceclaimer.db')     
app = MyApp(0)
app.MainLoop()
