import sys
sys.path.append( '../ObjectCube' )
import ObjectCubePython
from browser.objectcube import filterManager, objectCubeService
#from browser.image import image_service
import browser.image

#used by Coordinate
from browser.cube.cube import Cube, Cell
import browser.cube.axis
import browser

class Coordinate:
    def __init__(self):        
        # Member variables for the axis.
        self.x = None
        self.y = None
        self.z = None
        
        # Hold the cube  
        self.cube = None


    
    def set_x(self, x):
        """ Set dimension to x in the coordinate. """
        self.x = x
        
    
    def get_x(self):
        return self.x
        
    
    def get_z(self):
        return self.z        
        
        
    def set_y(self, y):
        self.y = y

    
    def get_y(self):
        return self.y


    def set_z(self, z):
        self.z = z
    

    
    def constructCube(self):
        
        # Get all the visiable images that images in the last cube -- if there was any
        last_visiable_images = dict()
        
        if self.cube is not None:
            last_visiable_images = self.cube.getVisibleImages()
            print 'Before constructing cube: Number of visiable images by name from last cube is', len(last_visiable_images.keys())
                   
        # Clear the old axis, if there are any.
        objectCubeService.get_state().getMultiDimensionalView(False).clearAxes()
 
        # Clear all filters!
        filterManager.clear()
        
        filters = []
        if self.x is not None:
            filters.append( self.x.get_load_filter() )
        
        if self.y is not None:
            filters.append( self.y.get_load_filter() )
        
        if self.z is not None:
            filters.append( self.z.get_load_filter() )
         
        
        # Add the filters.
        filterManager.add_filters( filters )

        
        # Get mdv from Object cube.
        mdv = objectCubeService.get_state().getMultiDimensionalView(False)
        axis_index = 0


        if self.x is not None:
            if not self.x.is_hierarchy():
                mdv.setAxis(axis_index, self.x.tagset)
                self.x.set_axis_index( axis_index )
                axis_index += 1
            else:
                mdv.setAxis( axis_index, self.x.get_state_hierarchy_node(), self.x.getLevel())
                self.x.set_axis_index( axis_index )
                axis_index +=1
        
        
        if self.y is not None:
            if not self.y.is_hierarchy():
                mdv.setAxis(axis_index, self.y.tagset )
                self.y.set_axis_index( axis_index )
                axis_index += 1
            else:
                mdv.setAxis( axis_index, self.y.get_state_hierarchy_node(), self.y.getLevel())
                self.y.set_axis_index( axis_index ) 
                axis_index += 1
        
        
        if self.z is not None:
            if not self.z.is_hierarchy():
                mdv.setAxis(axis_index, self.z.tagset )
                self.z.set_axis_index( axis_index )
                axis_index += 1
            else:
                mdv.setAxis( axis_index, self.z.get_state_hierarchy_node(), self.z.getLevel())
                self.z.set_axis_index( axis_index )
                axis_index += 1
 
        
        mdv = objectCubeService.get_state().getMultiDimensionalView(False)
        
        # Notify the image loader for the new images
        browser.image.image_service.notifyImageLoad( objectCubeService.get_state().getObjects() )
        
        
        self.cube = Cube( mdv, self.x, self.y, self.z, last_visiable_images )
        print '--New cube constructred with', self.cube.getNumberOfImages(), 'number of images.'
        
    
    
    
    def draw(self):
        messenger.send('change-mode', ['CubeMode'])
