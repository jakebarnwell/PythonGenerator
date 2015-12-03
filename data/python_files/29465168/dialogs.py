import wx
import sys
sys.path.append( '../ObjectCube' )
from ObjectCubePython import *

#from browser.objectcube import objectCubeService
from objectcube import objectCubeService
from contribute.checktree import *
from objects.lists import ObjectTagsList

import StringIO

#################################################################################
class AddNewObjectDialog(wx.Dialog):
    """
    Dialog for adding a new single object.
    """
    def __init__(self, parent, id, title):
        # call the parent constructor
        wx.Dialog.__init__(self, parent, id, title, size=(370, 340))
        
        # center this dialog when it is open
        self.CenterOnScreen()

        # Member variables.
        self.filename = ''
        self.dirname = ''
        
        self.addedTags = []

        self.__init_components()
        self.__bind_events()
        
    def __init_components(self):
        # create label for the file url.
        self.lbl_select_object = wx.StaticText(self, -1, 'Select object:', 
            style=wx.ALIGN_CENTRE, 
            pos=(20, 20))
        
        # create text label for the file url.
        self.text_location = wx.TextCtrl ( self, -1, pos=(20, 45), size=wx.Size(240, -1), style=wx.TE_READONLY )
    
        # create button for the file url.
        self.btn_browse = wx.Button(self, id=-1, label='Browse..', pos=(270, 45), size=wx.Size(80, 25))
        
        # create submit buttons.
        self.btn_ok = wx.Button(self, id=-1, label='Add', pos=(170, 290))
        self.btn_cancel = wx.Button(self, id=-1, label='Cancel', pos=(265, 290))
        
        # Create tagset tree for selecting tags for images that we are importing.
        self.tagset_tree = CheckTreeCtrl(self, -1, 
        style=CT_AUTO_CHECK_CHILD|wx.TR_DEFAULT_STYLE|wx.SUNKEN_BORDER, pos=(20,80), size=wx.Size(330,200))
        
        self.tag_nodes = {}
        
        tagset_root = self.tagset_tree.AddRoot("All tagsets")
        for tagset in serviceLayer.getAllTagsets():
            child = self.tagset_tree.AppendItem(tagset_root, tagset.name, False)
            for tag in tagset.getTags():
                tn = self.tagset_tree.AppendItem(child, tag.name, False)
                self.tag_nodes[tn] = tag

    
    def __bind_events(self):
        pass
        # Bind events for components on this frame. 
        self.Bind(wx.EVT_BUTTON, self.on_button_browse, self.btn_browse) 
        self.Bind(wx.EVT_BUTTON, self.on_button_ok, self.btn_ok) 
        self.Bind(wx.EVT_BUTTON, self.on_button_cancel, self.btn_cancel)

    # event function.
    def on_button_ok(self, event):
        # Go through the nodes in the tree and find the tags that we will add.
        for n in self.tag_nodes:
            if self.tagset_tree.IsItemChecked(n):
                #print self.tag_nodes[n].name
                self.addedTags.append(self.tag_nodes[n])

        # Close the window.
        self.EndModal ( wx.ID_OK )
        self.Close()
    
    # event function.
    def on_button_cancel(self, event):
        self.EndModal ( wx.ID_CANCEL )
        self.Close()
    
    # event function.
    def on_button_browse(self, event):
        dlg = wx.FileDialog(self, "Choose a file", "~/", "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename=dlg.GetFilename()
            self.dirname=dlg.GetDirectory()
            self.text_location.SetValue(self.dirname + '/' + self.filename)
#################################################################################



#################################################################################
class AddNewObjectDialogDir(wx.Dialog):
    """
    Dialog for adding a new object in a directory
    """
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, 'Add objects from directory', size=(370, 340))
        
        # center this dialog when it is open
        self.CenterOnScreen()

        # Member variables.
        self.path = ''
        self.addedTags = []

        self.__init_components()
        self.__bind_events()
        
    def __init_components(self):
        # create label for the file url.
        self.lbl_select_object = wx.StaticText(self, -1, 'Select directory:', 
            style=wx.ALIGN_CENTRE, 
            pos=(10,10))
        
        # create text label for the file url.
        self.text_location = wx.TextCtrl ( self, -1, pos=(20, 45), size=wx.Size(240, -1), style=wx.TE_READONLY )
    
        # create button for the file url.
        self.btn_browse = wx.Button(self, id=-1, label='Browse..', pos=(270, 45), size=wx.Size(80, 25))
        
        # create submit buttons.
        #self.btn_ok = wx.Button(self, id=-1, label='Add', pos=(110, 80))
        #self.btn_cancel = wx.Button(self, id=-1, label='Cancel', pos=(190, 80))
        self.btn_ok = wx.Button(self, id=-1, label='Add', pos=(170, 290))
        self.btn_cancel = wx.Button(self, id=-1, label='Cancel', pos=(265, 290))
        
        # Create tagset tree for selecting tags for images that we are importing.
        self.tagset_tree = CheckTreeCtrl(self, -1, 
        style=CT_AUTO_CHECK_CHILD|wx.TR_DEFAULT_STYLE|wx.SUNKEN_BORDER, pos=(20,80), size=wx.Size(330,200))
        
        self.tag_nodes = {}
        
        tagset_root = self.tagset_tree.AddRoot("All tagsets")
        for tagset in objectCubeService.getAllTagsets():
            child = self.tagset_tree.AppendItem(tagset_root, tagset.name, False)
            for tag in tagset.getTags():
                tn = self.tagset_tree.AppendItem(child, tag.valueAsString(), False)
                self.tag_nodes[tn] = tag

    def __bind_events(self):
        pass
        # Bind events for components on this frame. 
        self.Bind(wx.EVT_BUTTON, self.on_button_browse, self.btn_browse) 
        self.Bind(wx.EVT_BUTTON, self.on_button_ok, self.btn_ok) 
        self.Bind(wx.EVT_BUTTON, self.on_button_cancel, self.btn_cancel)

    # event function.
    def on_button_ok(self, event):
        # Go through the nodes in the tree and find the tags that we will add.
        for n in self.tag_nodes:
            if self.tagset_tree.IsItemChecked(n):
                self.addedTags.append(self.tag_nodes[n])

        # Close the window.
        self.EndModal ( wx.ID_OK )
        self.Close()
    
    # event function.
    def on_button_cancel(self, event):
        self.EndModal ( wx.ID_CANCEL )
        self.Close()
    
    # event function.
    def on_button_browse(self, event):
        #dlg = wx.DirDialog(self, "Choose a file", wx.OPEN)
        dlg = wx.DirDialog(wx.GetApp().GetTopWindow(), "Choose a directory:", style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.path = dlg.GetPath()
            self.text_location.SetValue(dlg.GetPath())
#################################################################################


class ViewObjectDialog(wx.Dialog):
    """
    Dialog for viewing tags that have been added to objects.
    """
    
    
    def scale_bitmap(self, bitmap, width, height):
        image = wx.ImageFromBitmap(bitmap)
        image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
        result = wx.BitmapFromImage(image)
        return result
    

    def __init__(self, parent, id, object_id):
        
        # We know the id... why don't we not just fetch the object right away?
        self.object = objectCubeService.get_object_by_id(object_id) 

        # Call the parent constructor.
        #wx.Dialog.__init__(self, parent, id, self.object.name, size=(400,500))
        wx.Dialog.__init__(self, parent, id, self.object.name, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        # Center the window when we open it.
        self.CenterOnScreen()


        # Create frame for the image.
        self.image_frame = wx.Frame(None, -1, "Test Frame", size=(400,300))
        self.image_frame.SetBackgroundColour(wx.WHITE)

        bitmap = wx.Bitmap(self.object.name)
        bitmap = self.scale_bitmap(bitmap, 400, 300)
        control = wx.StaticBitmap(self.image_frame, -1, bitmap)
        #control.SetPosition((0, 0))


        # Read the image data into buffer.    
        #buf = open(self.object.name, "rb").read()
        #self.image_buffer = StringIO.StringIO(buf)
        #self.raw_image = wx.ImageFromStream(self.image_buffer)
        
        #image = wx.ImageFromBitmap( self.raw_image.ConvertToBitmap() )
        #image = image.Scale(100, 100, wx.IMAGE_QUALITY_HIGH)
        #result = wx.BitmapFromImage(image)
        
        #bmp = self.raw_image.ConvertToBitmap()
        #DC = wx.PaintDC(self.image_frame)
        #DC.DrawBitmap(bmp, 0, 0)        
        
        
        
        
        
        #print 'raw image', dir(self.raw_image)
        #print self.raw_image.GetData()
        
        # Create frame for the image.
        #self.image_frame = wx.Frame(None, -1, "Test Frame", size=(400,300))
        #self.image_frame.SetBackgroundColour(wx.WHITE)
        

        #image_frame_menubar = wx.MenuBar()
        #file = wx.Menu()
        
        #file.Append(5000, 'Bigger', 'Quit application')
        
        
        #image_frame_menubar.Append(file, '&Size')
        #self.image_frame.SetMenuBar(image_frame_menubar)

        #self.image_frame.CenterOnScreen()
        self.image_frame.Show()
        
        # Create the object tags list.
        self.objectTagList = ObjectTagsList(self, self.object)

        # Create control buttons.
        self.btn_add_tag = wx.Button(self, id=-1, label='Add tag to object') 
        self.btn_remove_selected_tag = wx.Button(self, id=-1, label='Remove selected tags')
        self.btn_remove_object = wx.Button(self, id=-1, label='Delete this object')
        
        # Bind events to the control buttons.
        self.Bind(wx.EVT_BUTTON, self.on_button_add_tagset, self.btn_add_tag) 
        self.Bind(wx.EVT_BUTTON, self.on_button_remove_selected_tag, self.btn_remove_selected_tag)
        self.Bind(wx.EVT_BUTTON, self.on_button_remove_object, self.btn_remove_object)
        
        # Paing event
        #self.image_frame.Bind( wx.EVT_PAINT, self.OnPaint )
        #self.image_frame.Bind( wx.EVT_SIZE, self.OnResize )
        self.Bind( wx.EVT_CLOSE, self.OnClose )
        
        
                
        # Create horizontal box sizer for the buttons.
        self.button_box = wx.BoxSizer(wx.HORIZONTAL)
        self.button_box.Add(self.btn_add_tag,1,wx.EXPAND)
        self.button_box.Add(self.btn_remove_selected_tag,1,wx.EXPAND)
        self.button_box.Add(self.btn_remove_object,1,wx.EXPAND)

        # Create sizer for this dialog.
        self.sizer=wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.objectTagList,1,wx.EXPAND)
        self.sizer.Add(self.button_box,0,wx.EXPAND) 
        self.SetSizer(self.sizer)
    
    
    
    
    
    
    
    
    def OnClose(self, ev):
        try:
            self.image_frame.Close()
        except:
            print 'image was dead.'
        ev.Skip()
    
    
    
    def OnPaint(self, Event):
        print 'nice'
        #raw_image = wx.Image(self.image_buffer)
        #raw_image = wx.ImageFromStream(self.image_buffer)
        #print self.image_buffer
        #raw_image.Rescale(self.image_frame.GetSize()[0], self.image_frame.GetSize()[1]);
        #bmp = self.raw_image.ConvertToBitmap()
        #DC = wx.PaintDC(self.image_frame)
        #DC.DrawBitmap(bmp, 0, 0)
        #Event.Skip()
        pass
    
    def OnResize(self, Event):
        print 'resize event'
        #buf = open(self.object.name, "rb").read()
        #self.image_buffer = StringIO.StringIO(buf)
        #self.raw_image = wx.ImageFromStream(self.image_buffer)
        #self.raw_image.Rescale(self.image_frame.GetSize()[0], self.image_frame.GetSize()[1]);
        #Event.Skip()        
    
    
    
    def on_button_add_tagset(self, event):
        dlg = AddTagToObjectDialog(self, self.object.id)
        result = dlg.ShowModal()
        if result == wx.ID_OK:
            self.objectTagList.reload_data()

    
    def on_button_remove_selected_tag(self, event):
        if self.objectTagList.has_selected():
            dlg = wx.MessageDialog(self, 'Are you sure you want to remove tag from object?', 'Remove tag from object?', wx.YES | wx.NO | wx.ICON_ERROR)
            result = dlg.ShowModal()
            if result == wx.ID_YES:
                self.objectTagList.remove_selected()
        else:
            wx.MessageBox('Please select tags to remove.', 'Info')

    def on_button_remove_object(self, event):
        """
        Event function. This function is called when remove object button is
        clicked. Opens up MessageDialog and removes object if user presses yes.
        """
        dlg = wx.MessageDialog(self, 'Are you sure you want to delete this object?', 'Delete object?', wx.NO | wx.YES | wx.ICON_ERROR)
        result = dlg.ShowModal()
        if result == wx.ID_YES:
            self.Destroy()

###########################################

class AddTagToObjectDialog(wx.Dialog):
    
    def __init__(self, parent, object_id, id=-1):
        wx.Dialog.__init__(self, parent, id, 'Add tag to object', size=(400,500))
        self.CenterOnScreen()
        self.__create_components()
        self.__register_events()
        self.object_id = object_id
        
        # Variables used for selection of tagset and tag in this dialog.
        self.selected_tagset = None
        self.selected_tag = None
    
    def __create_components(self):
        label_select_tagset = wx.StaticText(self, -1, 'Select tagset', style=wx.ALIGN_CENTRE) 
        
        # Add the tagsets to the drop down.
        self.tagsets = objectCubeService.getAllTagsets()
        self.drop_down_type = wx.ComboBox(self, -1, choices=[t.name for t in self.tagsets ], style=wx.CB_READONLY) 
        
        # Select the first element in the dropdown. 
        # We must do this later so we trigger the select event.
        label_select_tag = wx.StaticText(self, -1, 'Select tag', style=wx.ALIGN_CENTRE)
        
        # Create listbox for the tags from the selection in the drop down.
        self.listBox1 = wx.ListBox(choices=[], id=-1, name='listBox1', parent=self, style=0)
        
        # Create buttons for this dialog.
        self.btn_ok = wx.Button(self, id=-1, label='Add', pos=(160, 150))
        self.btn_cancel = wx.Button(self, id=-1, label='Cancel', pos=(260, 150))

        # Create horizontal box sizer for the buttons.
        self.button_box = wx.BoxSizer(wx.HORIZONTAL)
        self.button_box.Add(self.btn_ok,0, wx.EXPAND)
        self.button_box.Add(self.btn_cancel,0,wx.EXPAND)
        
        # create a sizer for this dialog. 
        self.sizer=wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(label_select_tagset, 0, wx.ALL,5)
        self.sizer.Add(self.drop_down_type, 0, wx.ALL|wx.EXPAND, 5)
        self.sizer.Add(label_select_tag, 0, wx.ALL|wx.EXPAND, 5)
        self.sizer.Add(self.listBox1, 1, wx.ALL|wx.EXPAND,5)
        self.sizer.Add(self.button_box,0,wx.EXPAND, 5)
        self.SetSizer(self.sizer)

    def __register_events(self):
        self.Bind(wx.EVT_COMBOBOX, self.event_combobox_change_selection, self.drop_down_type)
        self.Bind(wx.EVT_LISTBOX, self.event_listbox_change_selection, self.listBox1)
        self.Bind(wx.EVT_BUTTON, self.on_button_ok, self.btn_ok)
        self.Bind(wx.EVT_BUTTON, self.on_button_cancel, self.btn_cancel)
        # select the first in tagset. We must do this after we have registerd the events. 
    
    def event_combobox_change_selection(self, event=None):
        """
        Event function for drop down selection change.
        """
        #print 'selection changed.'
        # clear the listbox.
        self.listBox1.Clear()
        # add the new tags to the listbox.
        for tagset in self.tagsets:
            if event.GetString() == tagset.name:
                self.selected_tagset = tagset 
                tags = tagset.getTags()
                for tag in tags:
                    self.listBox1.Append(tag.valueAsString())
                break

    def event_listbox_change_selection(self, event):
        self.selected_tag = event.GetString()

    def on_button_ok(self, event):
        if self.selected_tag is not None:
            for tag in self.selected_tagset.getTags():
                if tag.valueAsString() == self.selected_tag:
                    objectCubeService.add_tag_to_object(self.selected_tagset.id, tag.id, self.object_id)
                    break
            self.EndModal ( wx.ID_OK )
            self.Destroy()
        else:
            print 'MESSAGEBOX: VALJA TAG FYRST'

    def on_button_cancel(self, event):
        self.EndModal ( wx.ID_CANCEL )
        self.Destroy()



