import sys
sys.path.append( '../ObjectCube' )
from ObjectCubePython import *
import wx
import time
#import direct
import os
#from direct.task import *
#from dialogs import *
from panels import ObjectPanel, CoordinatePanel, FilterPanel
from tagsets.panels import TagsetPanel
from dimensions import DimensionPanel,AddNewHierarchyDialog
#from browser.common import *
from tagsets.dialogs import AddNewTagsetDialog
from objects.dialogs import AddNewObjectDialog, AddNewObjectDialogDir
from constants import *
from objectcube import objectCubeService



from filter import AddNewNumericalRangeFilterDialog, AddNewDateRangeFilterDialog, AddNewTimeRangeFilterDialog

class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title="Control box", size=(600,500))
        
        # Create a panel and a notebook on the panel
        notebook_panel = wx.Panel(self)
        self.nb = wx.Notebook( notebook_panel )

        # Create tagset page for the notebook.
        self.pageTagset = TagsetPanel(self.nb)
        self.nb.AddPage(self.pageTagset, "Tagsets")
        
        self.dimensionPanel = DimensionPanel( self.nb ) 
        
        # Create object page for the notebook
        self.objectPanel = ObjectPanel(self.nb)
        self.nb.AddPage(self.objectPanel, "Objects")
        
        #self.nb.AddPage(self.coordinatePanel, "Coordinate")
        #self.nb.AddPage(self.filterPanel, 'Filters')
        self.nb.AddPage(self.dimensionPanel, 'Hierarchies')

        # Put the notebook in a sizer for the panel to manage the layout
        sizer = wx.BoxSizer()
        sizer.Add(self.nb, 1, wx.EXPAND)
        notebook_panel.SetSizer(sizer)

        # Crete tagset menu.
        tagset_menu = wx.Menu()
        tagset_menu.Append(MENU_TAGSET_CREATE, '&Create new tagset', '')

        # Create object menu.
        object_menu = wx.Menu()
        object_menu.Append(MENU_OBJECT_ADD, '&Add new object', '')
        object_menu.Append(MENU_OBJECT_ADD_DIR, '&Add objects from directory', '')
        
        # Create hirachy menu.
        hirachy_menu = wx.Menu()
        hirachy_menu.Append(MENU_OBJECT_ADD_HIRACHY, '&Add new hierarchies', '')
        
        # Create menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(tagset_menu, '&Tagsets')
        menuBar.Append(object_menu, '&Objects')
        menuBar.Append(hirachy_menu, 'Hierarchy')
        self.SetMenuBar(menuBar)
        
        # Bind events to the menu items.
        self.Bind(wx.EVT_MENU, self.new_tagset, id=MENU_TAGSET_CREATE)
        self.Bind(wx.EVT_MENU, self.add_object, id=MENU_OBJECT_ADD)
        self.Bind(wx.EVT_MENU, self.add_object_dir, id=MENU_OBJECT_ADD_DIR)
        self.Bind(wx.EVT_MENU, self.add_object_hirachy, id=MENU_OBJECT_ADD_HIRACHY)

    
    def new_tagset(self, event):
        """
        Event function for MENU_TAGSET_CREATE. This event
        is called when this menu object is clicked.
        """
        # Change the notebook selection to the object tab.
        self.nb.SetSelection(0)
        
        dia = AddNewTagsetDialog(self, -1, 'Add new tagset')
        dia.ShowModal()
        if dia.ReturnCode == wx.ID_OK:
            
            # Get the tagset name and type from the dialog.
            tagset_name = dia.text_name.GetValue()
            tagset_type = dia.drop_down_type.GetValue()

            # Get the id of the tagset that will be created. Might be a better
            # way of finding this id from the framework.
            tagset_type_id = objectCubeService.get_tagset_type_id_by_name(tagset_type)
            
            tagset = None
            
            if tagset_type_id == TagSet.TYPE.ALPHANUMERICAL:
                tagset = AlphanumericalTagSet(tagset_name.encode('utf-8'))
            
            if tagset_type_id == TagSet.TYPE.NUMERICAL:
                tagset = NumericalTagSet( str(tagset_name) )
                
            if tagset_type_id == TagSet.TYPE.DATE:
                tagset = DateTagSet( str(tagset_name) )

            if tagset_type_id == TagSet.TYPE.DATE:
                tagset = DateTagSet( str(tagset_name) )
            
            if tagset_type_id == TagSet.TYPE.TIME:
                tagset = TimeTagSet( str(tagset_name) )

            try:
                tagset.create()
                self.pageTagset.reload_tagset_list()
            except:
                wx.MessageBox('Unable to create tagset.', 'Error' , wx.ICON_ERROR)
    
    

    def add_object(self, event):
        """
        Event function. This function is called when we select
        create new object in the main menu.
        """
        # Change the notebook selection to the object tab.
        self.nb.SetSelection(1)

        # Create object add dialog and show it modal.
        dialog = AddNewObjectDialog(self, -1, 'Add new object')
        dialog.ShowModal()
        if dialog.ReturnCode == wx.ID_OK:
            object_url = str(dialog.dirname + '/' + dialog.filename)
            new_object = Object(object_url)
            try:
                new_object.create()
            except:
                print '-- error while creating new object.'
                
            for tag in dialog.addedTags:
                objectCubeService.add_tag_to_object(tag.tagSetId, tag.id, new_object.id)

            self.objectPanel.refresh_object_list()
            
   
    def add_object_dir(self, event):
        """
        Event function. This function is called when we select
        create new object in the main menu.
        """
        # Change the notebook selection to the object tab.
        self.nb.SetSelection(1)

        # Create object add dialog and show it modal.
        dialog = AddNewObjectDialogDir(self)
        dialog.ShowModal()
        if dialog.ReturnCode == wx.ID_OK:
            path = str(dialog.path)
            dirList=os.listdir(path)
            for fname in dirList:
                # Why are we only allowing .jpg.
                if fname.lower().endswith('.jpg'):
                    new_object = Object(path + '/' + fname)
                    try:
                        new_object.create()
                    except:
                        print '-- error while creating new object:', fname
                    
                    for tag in dialog.addedTags:
                        objectCubeService.add_tag_to_object(tag.tagSetId, tag.id, new_object.id)
 
            # refresh the object list.
            self.objectPanel.refresh_object_list()
            


    def add_object_hirachy(self, event):
        dlg = AddNewHierarchyDialog(self)
        dlg.ShowModal()
        # reload the dimensional panel.
        self.dimensionPanel.reload()



class MainApp(wx.App):
    def OnInit(self):
        frame = MainFrame()
        frame.Show(True)
        self.SetTopWindow(frame)
        return True
