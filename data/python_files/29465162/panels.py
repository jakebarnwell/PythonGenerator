import wx
#from browser.common import *
from lists import ObjectList
from filter import FilterList
#from browser.common import * 
#from browser.coordinate import *
from tagset import TagsetList

# This will fail..
#from browser.objectcube import objectCubeService

import sys
sys.path.append( '../ObjectCube' )
from ObjectCubePython import *


class ObjectPanel(wx.Panel):
    """
    Panel for the objects view in the control box.
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.object_list = ObjectList(self) 
        
        # create sizer for the object panel.
        self.sizer=wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.object_list,1,wx.EXPAND)
        self.SetSizer(self.sizer)
    
    def refresh_object_list(self):
        self.object_list.reload_data()



class CoordinatePanel(wx.Panel):
    def __init__(self, parent):
        """
        Constructor for the PageTagset panel.
        """
        # Initalize the panel.
        wx.Panel.__init__(self, parent)

        # Member variables
        self.__init_components() 
        self.__bind_events()


    def __init_components(self):
        # get all tagsets.
        self.tagsets = objectCubeService.getAllTagsets()
        tagset_choices = [tagset.name for tagset in self.tagsets]
        
        # Create dropdown with all the tagsets
        self.drop_down_x = wx.ComboBox(self, -1, choices=tagset_choices, style=wx.CB_READONLY, pos=(20,10), size=(210,27))
        
        self.drop_down_x_type = wx.ComboBox(self, -1, choices=['Tagset', 'Hierarchy'], style=wx.CB_READONLY, pos=(240,10), size=(100,25))
        self.drop_down_x_type.Select(0)
        
        self.drop_down_y = wx.ComboBox(self, -1, choices=tagset_choices, style=wx.CB_READONLY, pos=(20,50), size=(210,27))
        self.drop_down_y_type = wx.ComboBox(self, -1, choices=['Tagset', 'Hierarchy'], style=wx.CB_READONLY, pos=(240,50), size=(100,25))
        self.drop_down_y_type.Select(0)
        
        self.drop_down_z = wx.ComboBox(self, -1, choices=tagset_choices, style=wx.CB_READONLY, pos=(20,90), size=(210,27))
        self.drop_down_z_type = wx.ComboBox(self, -1, choices=['Tagset', 'Hierarchy'], style=wx.CB_READONLY, pos=(240,90), size=(100,25))
        self.drop_down_z_type.Select(0)
 
        # Create check box
        self.cb_show_tags = wx.CheckBox(self, -1, 'Show tags', (20, 130))
        self.cb_show_tags.SetValue(True)
        
        self.cb_show_lines = wx.CheckBox(self, -1, 'Show lines', (120, 130))
        self.cb_show_lines.SetValue(True)

        self.cb_only_tags_with_objects = wx.CheckBox(self, -1, 'Only show tags with objects', (20, 160))
        self.cb_only_tags_with_objects.SetValue(True)
        
        # Create buttons
        self.btn_draw = wx.Button(self, id=-1, label='View', pos=(20, 190))
        self.btn_clear = wx.Button(self, id=-1, label='Clear', pos=(110, 190))


    def __bind_events(self):
        self.btn_clear.Bind(wx.EVT_BUTTON, self.event_btn_clear)
        self.btn_draw.Bind(wx.EVT_BUTTON, self.event_btn_draw)
        self.Bind(wx.EVT_TEXT, self.On_drop_down_x_type_change, self.drop_down_x_type)
        self.Bind(wx.EVT_TEXT, self.On_drop_down_y_type_change, self.drop_down_y_type)
        self.Bind(wx.EVT_TEXT, self.On_drop_down_z_type_change, self.drop_down_z_type)
        

    def On_drop_down_x_type_change(self, event):
        value = event.GetString()
        self.drop_down_x.Clear()
        self.drop_down_x.SetValue('')
        
        if value == 'Hierarchy':
            for dim in serviceLayer.get_all_dimensions():
                tagset = serviceLayer.get_tagset_by_id(dim.tagSetId)
                root_node = dim.getRoot()
                self.drop_down_x.Insert(str(dim.id) + ',' + tagset.name + ',' + root_node.name, 0)
        else:
            self.drop_down_x.Clear()
            self.drop_down_x.SetValue('')
                    
            for tagset in serviceLayer.getAllTagsets():
                self.drop_down_x.Insert(tagset.name, 0)
    
    
    def On_drop_down_y_type_change(self, event):
        value = event.GetString()
        self.drop_down_y.Clear()
        self.drop_down_y.SetValue('')
        
        if value == 'Hierarchy':
            for dim in serviceLayer.get_all_dimensions():
                tagset = serviceLayer.get_tagset_by_id(dim.tagSetId)
                root_node = dim.getRoot()
                self.drop_down_y.Insert(str(dim.id) + ',' + tagset.name + ',' + root_node.name, 0)
        
        else:
            self.drop_down_y.Clear()
            self.drop_down_y.SetValue('')
                    
            for tagset in serviceLayer.getAllTagsets():
                self.drop_down_y.Insert(tagset.name, 0)

    
    def On_drop_down_z_type_change(self, event):
        value = event.GetString()
        self.drop_down_z.Clear()
        self.drop_down_z.SetValue('')
        
        if value == 'Hierarchy':
            for dim in serviceLayer.get_all_dimensions():
                tagset = serviceLayer.get_tagset_by_id(dim.tagSetId)
                root_node = dim.getRoot()
                self.drop_down_z.Insert(str(dim.id) + ',' + tagset.name + ',' + root_node.name, 0)
        
        else:
            self.drop_down_z.Clear()
            self.drop_down_z.SetValue('')
                    
            for tagset in serviceLayer.getAllTagsets():
                self.drop_down_z.Insert(tagset.name, 0)
    
    
    
    def event_btn_draw(self, event):
        
        """
        This function is called when the user presses the draw button.
        """
        coordinateService.clear()
        cord = Coordinate()
        
        # Stack that we used to collect the axis. 
        x = None
        z = None
        y = None
        
        try:
            if len(self.drop_down_x.GetValue()) > 0:
                x_type = self.drop_down_x_type.GetValue()
                axis = None
                if x_type == 'Hierarchy':
                    dim_id = self.drop_down_x.GetValue().split(',')[0]
                    dim_tagset_name = self.drop_down_x.GetValue().split(',')[1]
                    dim = serviceLayer.getTagsetByName(dim_tagset_name).getDimension( int( dim_id ))
                    axis = Axis( dim, self.cb_only_tags_with_objects.GetValue(), True, 'x' )
                else:
                    axis = Axis( serviceLayer.getTagsetByName( self.drop_down_x.GetValue()), self.cb_only_tags_with_objects.GetValue(), False, 'x' )
                #axis_list.append( axis  )
                x = axis
        except:
            raise
            pass
         
        try:
            if len(self.drop_down_y.GetValue()) > 0:
                y_type = self.drop_down_y_type.GetValue()
                axis = None
                if y_type == 'Hierarchy':
                    dim_id = self.drop_down_y.GetValue().split(',')[0]
                    dim_tagset_name = self.drop_down_y.GetValue().split(',')[1]
                    dim = serviceLayer.getTagsetByName(dim_tagset_name).getDimension( int( dim_id ))
                    axis = Axis( dim, self.cb_only_tags_with_objects.GetValue(), True, 'y' )
                else:
                    axis = Axis( serviceLayer.getTagsetByName( self.drop_down_y.GetValue()), self.cb_only_tags_with_objects.GetValue(), False,'y' )
                #axis_list.append( axis  )
                y=axis
        except:
            raise
            pass 
        
        try:
            if len(self.drop_down_z.GetValue()) > 0:
                z_type = self.drop_down_z_type.GetValue()
                axis = None
                if z_type == 'Hierarchy':
                    dim_id = self.drop_down_z.GetValue().split(',')[0]
                    dim_tagset_name = self.drop_down_z.GetValue().split(',')[1]
                    dim = serviceLayer.getTagsetByName(dim_tagset_name).getDimension( int( dim_id ))
                    axis = Axis( dim, self.cb_only_tags_with_objects.GetValue(), True, 'z' )
                else:
                    axis = Axis( serviceLayer.getTagsetByName( self.drop_down_z.GetValue()), self.cb_only_tags_with_objects.GetValue(), False,'z' )
                #axis_list.append( axis  )
                z = axis
        except:
            raise
            pass
            
        
        cord.x = x
        cord.y = y
        cord.z = z
        
        if not cord.x is None:
            #cord.x = ax
            x.set_axis_color( (0,0,0.5) )
        
        if not cord.y is None:
            #cord.x = ax
            y.set_axis_color( (0,0,0.5) )
        if not cord.z is None:
            #cord.x = ax
            z.set_axis_color( (0,0,0.5))
        coordinateService.set_coordinate(cord, self.cb_show_lines.GetValue(), self.cb_show_tags.GetValue())
        coordinateService.draw()
        
        
        
        """
        while len(axis_list) > 0:
            ax = axis_list.pop(0)
            
            if cord.x is None:
                cord.x = ax
                ax.set_axis_color( (0,0,0.5) )
            
            elif cord.z is None:
                cord.z = ax
                ax.set_axis_color( (0.5,0.0,0.0) )
            
            else:
                cord.y = ax
                ax.set_axis_color( (0.0,0.5,0.0) )
        
        # Set the coordinate and draw it. 
        coordinateService.set_coordinate(cord, self.cb_show_lines.GetValue(), self.cb_show_tags.GetValue())
        coordinateService.draw()
        """
        
    
    def event_btn_clear(self, event):
        self.drop_down_x.SetValue('')
        self.drop_down_y.SetValue('')
        self.drop_down_z.SetValue('')
        coordinateService.clear()
        State.removeAllFilters()
        


class FilterPanel(wx.Panel):
    """
    Panel for the filters.
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        
        # Member variables.
        self.filters = []
        self.filter_list = FilterList(self) 
        
        # create sizer for the object panel.
        self.sizer=wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.filter_list, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

    
    def add_filter(self, filter):
        # add the filter to service layer.
        serviceLayer.add_filter( filter )

        # notify filter_list that he needs to reload.
        self.filter_list.reload_data()
