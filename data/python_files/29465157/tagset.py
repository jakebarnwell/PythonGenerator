import sys
sys.path.append( '../ObjectCube' )
from ObjectCubePython import *

import wx.calendar as cal
import wx


from objectcube import objectCubeService
from tagsets.popups import TagsetListPopupMenu


############################################################################
class TagsetList(wx.ListCtrl):
    """
    ListCtrl for Tagsets.
    """
    def __init__(self, parent, id=-1):
        # Member variables.
        self.columns = ['Tagset name', 'Tagset type']
        self.items = []
        self.parent = parent

        wx.ListCtrl.__init__(self, parent, id, style = wx.LC_REPORT | wx.LC_SINGLE_SEL)
        
        for col, text in enumerate(self.columns):
            self.InsertColumn(col, text)
        
        self.load_data()
        self.bind_events()
           
    
    def load_data(self):
        """
        Function for loading data for this list.
        """
        self.DeleteAllItems()
        self.items = []
        for n in objectCubeService.getAllTagsets():
            self.items.append(n.id)
            self.add_line([n.name, n.typeAsString()])

    
    def add_line(self, line):
        # add the line to the list
        self.Append(line)

        # resize columns
        for i in range(len(self.columns)):
            self.SetColumnWidth(i, wx.LIST_AUTOSIZE)

    
    def bind_events(self):
        self.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.event_list_item_activated, self)
        self.Bind(wx.EVT_RIGHT_DOWN, self.event_on_right_mouse_button_down)

    
    def event_on_right_mouse_button_down(self, event):
        self.PopupMenu(TagsetListPopupMenu(self))
    
    
    def event_list_item_activated(self, event):
        # get the tagset that we are clickin on, and open up a dialog to view it.
        tagset_id = self.items[event.GetIndex()]
        dialog = ViewTagsetDialog(self, -1, tagset_id)
        dialog.Show()
############################################################################



############################################################################
class ViewTagsetDialog(wx.Dialog):
    def __init__(self, parent, id, tagset_id): 
        # Member variables.
        #self.tagset_id = tagset_id
        self.tagset = objectCubeService.get_tagset_by_id(tagset_id)
        
        wx.Dialog.__init__(self, parent, id, self.tagset.name, size=(400,500))
        self.CenterOnScreen()
        self.__initalize_components()
        #self.__bind_events()
        self.parent = parent

    def __initalize_components(self):
        # Create tagset tag list
        self.tagset_tag_list = TagsetTagList(self, self.tagset)
############################################################################



##########################################################
class TagsetDialogPopupMenu( wx.Menu ):
    def __init__(self, parent):
        wx.Menu.__init__(self)
        self.parent = parent
        
        item1 = wx.MenuItem(self, wx.NewId(),"Add new tag")
        item2 = wx.MenuItem(self, wx.NewId(),"Delete selected tags")
        
        self.AppendItem(item1)
        self.AppendItem(item2)
        
        # Bind new event.
        self.Bind(wx.EVT_MENU, self.on_new_tag, item1)
        self.Bind(wx.EVT_MENU, self.on_delete_selected_tags, item2)
        
    def on_new_tag(self, event):   
        if self.parent.tagset.typeId == AlphanumericalTagSet.TYPE.ALPHANUMERICAL:
             dlg = AddNewAlphanumericalTagDialog(self.parent, -1, self.parent.tagset)
             if dlg.ShowModal() == wx.ID_OK:
                 self.parent.reload_data()
        
        elif self.parent.tagset.typeId == NumericalTagSet.TYPE.NUMERICAL:
            dlg = AddNewNumericalTagDialog(self, -1, self.parent.tagset)
            if dlg.ShowModal() == wx.ID_OK:
                self.parent.reload_data()


        elif self.parent.tagset.typeId == DateTagSet.TYPE.DATE:
            dlg = AddNewDateTagDialog(self, -1, self.parent.tagset)
            if dlg.ShowModal() == wx.ID_OK:
                self.parent.reload_data()


        elif self.parent.tagset.typeId == TimeTagSet.TYPE.TIME:
            dlg = AddNewTimeTagDialog(self, -1, self.parent.tagset)
            if dlg.ShowModal() == wx.ID_OK:
                self.parent.reload_data()

        else:
            #print 'Tagset not supported.'
            pass
    
    def on_delete_selected_tags(self, event):
        if self.parent.has_selected():
            dial = wx.MessageDialog(None, 'Are you sure you want to delete selected tags?', 'Question', 
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            
            if dial.ShowModal() == wx.ID_YES:
                delete_tags = self.parent.get_selected_tags()
                
                for key in delete_tags.keys():
                    self.parent.tagset.deleteTag( delete_tags[key] )

                # reload the list after we have delete
                self.parent.reload_data()
        else:
            pass
            wx.MessageBox('No tag was selected.', 'Info')
        
##########################################################



##########################################################
class TagsetTagList(wx.ListCtrl):
    """
    ListCtrl component that is used to view tags within a given
    Tagset. The class constructor receives a tagset id.
    """
    def __init__(self, parent, tagset, id=-1):
        # Member variables
        self.tagset = tagset
        self.columns = ['Tag id','Tag name']
        self.tags = [] 
        
        self.init_base(parent, id)
        self.load_data()
        self.bind_events()
        
        self.selected_tags = {}
        self.selected_items = []


    def init_base(self, parent, id):
        wx.ListCtrl.__init__(self, parent, id, style=wx.LC_REPORT)
        
        for col, text in enumerate(self.columns):
            self.InsertColumn(col, text)

        self.SetColumnWidth(0,40)
        self.SetColumnWidth(1,360)
   

    # Should the list be implementing event's or the parent of the list?
    def bind_events(self):
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.event_item_selected, self)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.event_item_deselected, self)
        self.Bind(wx.EVT_RIGHT_DOWN, self.event_right_mouse_button_down)
    
    def reload_data(self):
        self.DeleteAllItems()
        self.load_data()
        self.selected_items = []
        self.selected_tags = {}
    
    
    def load_data(self):
        """
        Function for loading data from the framework
        and add them to the this listctrl.
        """
        self.tags = []
        for tag in self.tagset.getTags():
            self.add_line([tag.id, tag.valueAsString()])
            self.tags.append(tag) 
    
    
    def add_line(self, line):
        self.Append(line)
    
    
    def event_item_selected(self, event):
        self.selected_tags[event.GetIndex()] = self.tags[event.GetIndex()]
        self.selected_items.append( event.GetIndex() )
    
    
    def event_item_deselected(self, event):
        self.selected_items.remove( event.GetIndex() )
        del self.selected_tags[ event.GetIndex() ]
       

    def get_selected_tags(self):
        return self.selected_tags


    def has_selected(self):
        if len(self.selected_tags) > 0: return True
        return False
    

    def event_right_mouse_button_down(self, event):
        self.PopupMenu(TagsetDialogPopupMenu(self))
##########################################################



##########################################################
class AddNewTimeTagDialog(wx.Dialog):
    def __init__(self, parent, id, tagset):
        # Member variables.
        self.tagset = tagset 
        self.txt_value = None 
        self.btnOk = None 
        self.btnCancel = None
        self.tag_id = None
        
        # call the parent constructor.
        wx.Dialog.__init__(self, parent.parent, id, 'Add new time tag', size=(310,100))
        
        # Center this dialog to the screen.
        self.CenterOnScreen()
        
        # Add the components to the window.
        self.__initialize_components()

        # Bind events for the components.
        self.__bind_events()

    def __initialize_components(self):
        
        from datetime import datetime
        dt_now = datetime.now().time()

        wx.StaticText(self, -1, "Hour:", (10, 10), style=wx.ALIGN_CENTRE)
        self.txt_hour = wx.TextCtrl(self, -1, "", pos=(45, 5), size=(30, -1))
        self.txt_hour.SetValue(str(dt_now.hour))
        
        wx.StaticText(self, -1, "Min:", (80, 10), style=wx.ALIGN_CENTRE)
        self.txt_min = wx.TextCtrl(self, -1, "", pos=(110, 5), size=(30, -1))
        self.txt_min.SetValue(str(dt_now.minute))
        
        wx.StaticText(self, -1, "Sec:", (145, 10), style=wx.ALIGN_CENTRE)
        self.txt_sec = wx.TextCtrl(self, -1, "", pos=(175, 5), size=(40, -1))
        self.txt_sec.SetValue(str(dt_now.second))

        wx.StaticText(self, -1, "MSec:", (220, 10), style=wx.ALIGN_CENTRE)
        self.txt_msec = wx.TextCtrl(self, -1, "", pos=(260, 5), size=(40, -1))
        self.txt_msec.SetValue(str(dt_now.microsecond))
        
        self.btnOk = wx.Button(self, -1, 'Create', (125, 35))
        self.btnCancel = wx.Button(self, 1, 'Cancel', (215, 35))


    def __bind_events(self):
        self.Bind(wx.EVT_BUTTON, self.event_btnOk_click, self.btnOk)
        self.Bind(wx.EVT_BUTTON, self.event_btnCancel_click, self.btnCancel)
 
    def event_btnOk_click(self, event):
        hour = int(self.txt_hour.GetValue())
        minutes = int(self.txt_min.GetValue())
        sec = int(self.txt_sec.GetValue())
        msec = int(self.txt_msec.GetValue())
        tag = TimeTag( hour, minutes, sec, msec )
        
        try:
            self.tagset.addTag(tag)
            self.EndModal ( wx.ID_OK )

        except:
            wx.MessageBox('Unable to create tag.', 'Info')

    def event_btnCancel_click(self, event):
        self.EndModal ( wx.ID_CANCEL )
        self.Destroy()
##########################################################



#######################################################################################
class AddNewDateTagDialog(wx.Dialog):
    def __init__(self, parent, id, tagset):
        # Member variables.
        self.tagset = tagset 
        self.txt_value = None 
        self.btnOk = None 
        self.btnCancel = None
        self.tag_id = None
        
        # call the parent constructor.
        wx.Dialog.__init__(self, parent.parent, id, 'Add new date tag', size=(290, 260))
        
        # Center this dialog to the screen.
        self.CenterOnScreen()
        
        # Add the components to the window.
        self.__initialize_components()

        # Bind events for the components.
        self.__bind_events()

    def __initialize_components(self):
        self.cal = cal.CalendarCtrl(self, -1, wx.DateTime_Now(), style = cal.CAL_SEQUENTIAL_MONTH_SELECTION, pos=(20, 20), size=(250, 150))
        self.btnOk = wx.Button(self, -1, 'Create', (120, 185))
        self.btnCancel = wx.Button(self, 1, 'Cancel', (200, 185))

    
    def __bind_events(self):
        self.Bind(wx.EVT_BUTTON, self.event_btnOk_click, self.btnOk)
        self.Bind(wx.EVT_BUTTON, self.event_btnCancel_click, self.btnCancel)
   
    def event_btnOk_click(self, event):
        selected_dt = self.cal.GetDate()
        year = selected_dt.GetYear()
        month = selected_dt.GetMonth()
        day = selected_dt.GetDay()

        tag = DateTag( year, month, day  )
        try:
            self.tagset.addTag(tag)
            self.EndModal ( wx.ID_OK )

        except:
            wx.MessageBox('Unable to create tag.', 'Info')


    def event_btnCancel_click(self, event):
        self.EndModal ( wx.ID_CANCEL )
        self.Destroy()
#######################################################################################



###################################################################
class AddNewNumericalTagDialog(wx.Dialog):
    def __init__(self, parent, id, tagset):
        # Member variables.
        self.tagset = tagset 
        self.txt_value = None 
        self.btnOk = None 
        self.btnCancel = None
        self.tag_id = None
        
        # call the parent constructor.
        wx.Dialog.__init__(self, parent.parent, id, 'Add new numerical tag', size=(285, 150))
        
        # Center this dialog to the screen.
        self.CenterOnScreen()
        
        # Add the components to the window.
        self.__initialize_components()

        # Bind events for the components.
        self.__bind_events()

    
    def __initialize_components(self):
        # todo: only allow number into this box.
        wx.StaticText(self, -1, "Numerical tag value:", (20, 20), style=wx.ALIGN_CENTRE)
        self.txt_value = wx.TextCtrl(self, -1, "", pos=(20, 45), size=(240, -1))
        self.btnOk = wx.Button(self, -1, 'Create', (110, 80))
        self.btnCancel = wx.Button(self, 1, 'Cancel', (190, 80))

    
    def __bind_events(self):
        self.Bind(wx.EVT_BUTTON, self.event_btnOk_click, self.btnOk)
        self.Bind(wx.EVT_BUTTON, self.event_btnCancel_click, self.btnCancel)


    def event_btnOk_click(self, event):
        tag_txt_value = self.txt_value.GetValue()
        if len(tag_txt_value) == 0: 
            wx.MessageBox('Tagset name is missing.', 'Info')
        
        else:
            try:
                tag = NumericalTag( int( tag_txt_value ) )
                self.tagset.addTag(tag)
                self.EndModal ( wx.ID_OK )
                self.Destroy()

            except:
                wx.MessageBox('Unable to create tag.', 'Info')
    
    def event_btnCancel_click(self, event):
        self.EndModal ( wx.ID_CANCEL )
        self.Destroy()
###################################################################      


###################################################################
class AddNewAlphanumericalTagDialog(wx.Dialog):
    def __init__(self, parent, id, tagset):
        # Member variables.
        self.tagset = tagset 
        self.posCtrl = None 
        self.btnOk = None 
        self.btnCancel = None
        self.tag_id = None
        
        # call the parent constructor.
        wx.Dialog.__init__(self, parent, id, 'Add new alphanumerical tag', size=(285, 150))
        
        # Center this dialog to the screen.
        self.CenterOnScreen()
        
        self.__initalize_components()
        self.__bind_events() 
    
    def __initalize_components(self):
        wx.StaticText(self, -1, "Tag name:", (20, 20), style=wx.ALIGN_CENTRE)
        self.posCtrl = wx.TextCtrl(self, -1, "", pos=(20, 45), size=(240, -1))
        self.btnOk = wx.Button(self, -1, 'Create', (105, 80))
        self.btnCancel = wx.Button(self, 1, 'Cancel', (190, 80))

    def __bind_events(self):
        self.Bind(wx.EVT_BUTTON, self.event_btnOk_click, self.btnOk)
        self.Bind(wx.EVT_BUTTON, self.event_btnCancel_click, self.btnCancel)

    def event_btnOk_click(self, event):
        tagset_text_value = self.posCtrl.GetValue()
        if len(tagset_text_value) == 0: 
            wx.MessageBox('Tagset name is missing.', 'Info')
        
        else:
            # we might get exception... must get it.
            try:
                tag = AlphanumericalTag(str(tagset_text_value))
                self.tagset.addTag(tag)
                self.tag_id = tag.id
                self.EndModal ( wx.ID_OK )
            except:
                wx.MessageDialog(None, 'Unable to create tag.', 'Exception', wx.OK | wx.ICON_EXCLAMATION).ShowModal()


    def event_btnCancel_click(self, event):
        self.EndModal ( wx.ID_CANCEL )
        self.Destroy()
###################################################################

