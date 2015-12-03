import sys
sys.path.append( '../ObjectCube' )
import ObjectCubePython
from browser.objectcube import filterManager, objectCubeService
from coordinate import Coordinate
import browser.cube.axis
from browser.common.messages import CUBE_MENU_RELOAD_FILTERS
from browser.common import X_AXIS, Z_AXIS, Y_AXIS
from browser.dialogs import TextDialog





class CubeService:
    """
    This class is used operate as a service for a singleton
    instance that is accessible to other parts.
    """
    
    def __init__(self):        
        # Used for axis indexing in ObjectCube. 
        #axis_counter = 0
        
        # Keep instance of a coordinate in memory.
        self.coordinate = Coordinate()
        
        # Default values for max image size, max image space and cluster index space.
        self.max_image_size = 10
        self.max_image_space = 5
        self.cluster_index_space = 0.2


    
    def get_max_image_size(self):
        return self.max_image_size
    
    
    def set_max_image_size(self, size):
        self.max_image_size = size
        
    
    def get_max_image_space(self):
        return self.max_image_space
    
    
    def set_max_image_space(self, size):
        self.max_image_space = size

    
    def get_cluster_stack_space(self):
        return self.cluster_index_space
    
    
    
    
    def view_on_x(self, dim):
        
        if dim is None:
            self.coordinate.set_x( None )
            
        elif type(dim) == ObjectCubePython.NumericalTagSet or type(dim) == ObjectCubePython.AlphanumericalTagSet or type(dim) == ObjectCubePython.DateTagSet or type(dim) == ObjectCubePython.TimeTagSet:
            x_ax = browser.cube.axis.AxisTagset( dim, axis=X_AXIS)
            self.coordinate.set_x( x_ax )
        
        elif type(dim) == ObjectCubePython.PersistentDimension:
            x_ax = browser.cube.axis.AxisHierarchy( dim, axis=X_AXIS )
            self.coordinate.set_x( x_ax )
        
        
        else:
            print 'typewas', type(dim)
            raise Exception('Viewving unknown dimension on X: ' + dim.__str__())


    
    
    
    def view_on_y(self, dim):
        if dim is None:
            self.coordinate.set_y( None )
        
        elif type(dim) == ObjectCubePython.PersistentDimension:
            y_ax = browser.cube.axis.AxisHierarchy( dim, axis = Y_AXIS )
            self.coordinate.set_y( y_ax )

        else:
            y_ax = browser.cube.axis.AxisTagset( dim, axis = Y_AXIS )
            self.coordinate.set_y( y_ax )
        
        

    
    
    def view_on_z(self, dim):    
        if dim is None:
            self.coordinate.set_z( None )
        
        elif type(dim) == ObjectCubePython.PersistentDimension:
            z_ax = browser.cube.axis.AxisHierarchy( dim, axis=Z_AXIS )
            self.coordinate.set_z( z_ax )
        
        else:
            z_ax = browser.cube.axis.AxisTagset( dim, axis=Z_AXIS )
            
            # If there is something on x, we must remove it...
            self.coordinate.set_z( z_ax )
        
        
        
 
    def get_x(self):
        return self.coordinate.x

    def get_y(self):
        return self.coordinate.y

    def get_z(self):
        return self.coordinate.z

    def getCurrentCube(self):
        return self.coordinate.cube
    
    
    def draw(self):
        self.dlg = TextDialog(title="CardMode", message="Constructing cube, please wait")
        self.dlg.draw()
        # Force repaint for showing the dialog before the images.
        base.graphicsEngine.renderFrame()
        base.graphicsEngine.renderFrame()
        
        # Let the coordinate construct new cube.
        # NOTE: Should this be self.drawing_area instead of coordinate
        
        if self.coordinate.x is None and self.coordinate.y is None and self.coordinate.z is None:
            # we need to clear all filters!!!
            filterManager.clear(True)
            
            messenger.send(CUBE_MENU_RELOAD_FILTERS)
            self.dlg.Close()
            return
        else:
            self.coordinate.constructCube()
            
            # Draw the cord.
            self.coordinate.draw()
            
            # Reload the filter list
            messenger.send(CUBE_MENU_RELOAD_FILTERS)
            self.dlg.Close()
    
    def reload(self):
        self.draw()


