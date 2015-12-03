import random
from browser.modes import AbstractMode
from pandac.PandaModules import LineSegs
from pandac.PandaModules import NodePath
import browser
from browser.cube.labels import DrillUpLabel
from browser.dialogs import CellInfoDialog
from browser.cube import cubeService
from browser.common import X_AXIS, Y_AXIS, Z_AXIS
from browser.configuration import browser_config
from browser.actions import actionManager, ActionAxis, ACTION_DRILL_DOWN, ACTION_DRILL_UP
from pandac.PandaModules import Point3

# import from same module
from handlers import *
from menu import RightMenu

from direct.gui.DirectGui import *
from browser.menu.context import make_context_item, BUTTON_FRAME_COLOR, BUTTON_TEXT_SHADOW, BUTTON_TEXT_FG, FRAME_COLOR
from browser.menu import context_menu_handler



class CubeMode( AbstractMode ):
    
    def __init__(self, name):
        AbstractMode.__init__(self, name)
        
        # Create coord-np
        self.root_np = render.attachNewNode( 'coordinate_root_node' )
        self.np = self.root_np.attachNewNode( 'coordinate_child_node' )
 
        # Create Node path for images.
        self.images_np = self.np.attachNewNode('images_nps')

        # Nps for the cube outlines.
        self.coordinate_line_nps = [None, None, None]
        
        # Member variable for x label nps.
        self.x_labels_np = None

        # Member variable for y label nps.
        self.y_labels_np = None

        # Member varaible for z labels nps.
        self.z_labels_np = None
        
        # Member variable for all the nodes in the cube
        self.x_labels = dict()
        self.y_labels = dict()
        self.z_labels = dict()
        
        # Member variables for parent node labels
        self.parent_node_label_x = None
        self.parent_node_label_y = None
        self.parent_node_label_z = None
        
        # Create cube rotater for the cube mode.
        self.cubeMouseRotater = CubeMouseRotater(self.root_np)
        
        # Create cube scaler handler for the cube mode.
        self.cubeScaler = CubeScaler()
        
        # accept scale up message from cube scaler.
        base.accept(self.cubeScaler.getScaleEventMessage(), self.scale)

        # Create cell scroller
        self.cellScroller = CellScroller()

        # Accept scroll message from the CellScoller
        # TODO: Move this down to the i
        base.accept(self.cellScroller.getScrollMessage(), self.scroll)

        # Accept event from cluster contet menu
        

        # Create instance of FloatingCameraHandler
        self.floatingCameraHandler = FloatingCameraHandler()

        # Create right dimension overview menu.
        self.rightMenu = RightMenu()
        self.rightMenu.hide()
        self.rightMenuVisable = False
        
        base.accept('t', self.printSelectedCells)


    
    
    def createContextMenus(self):
        pass
    
    
    
    
    
    def selectCell(self, cell):
        """
        """
        self.selectedCells[cell.getKey()] = cell
    
    def deselectCell(self, cell):
        """
        """
        del self.selectedCells[cell.getKey()]
    
    
    def deselectAllCells(self):
        """
        """
        self.selectedCells = dict()
        
    def printSelectedCells(self):
        """
        """
        print 'Selected cells:'
        for cell in self.selectedCells.values():
            print cell.getKey()
    
    
    
    
    
    def disable(self):
        """ Document string for disable"""
        self.cubeMouseRotater.disable()
        self.cubeScaler.disable()
        self.cellScroller.disable()
        self.np.hide()
        self.np.setX(-200000)
        browser.dialogs.dialogService.closeInfoDialogs()

        # disable events
        base.ignore('x_dim_action_swap')
        base.ignore('y_dim_action_swap')
        base.ignore('z_dim_action_swap')
        base.ignore('x_dim_action_clear')
        base.ignore('dim_view_tagset')
        base.ignore('dim_view_hierarchy')
        base.ignore('dim_move_to_axis')
        base.ignore('update_added_filter')
        base.ignore('cluster_cell_context_select')
        base.ignore('CLICK_MOUSE3_None')
        self.rightMenu.hide()
        
        # stop the menu mousetask.
        taskMgr.remove(self.menuMouseWatcherTask)
        self.dimensionMenuVisable = False


    
    def initalize(self):
        print 'XX Initalizing the CubeMode'

        self.__create_spaceContextMenu()
        
        self.cubeMouseRotater.enable()
        self.cubeScaler.enable()
        self.cellScroller.enable()
        self.np.show()
        
        # Accept coordinate modivation events
        base.accept('x_dim_action_swap', self.OnXAxisPivot)
        base.accept('y_dim_action_swap', self.OnYAxisPivot)
        base.accept('z_dim_action_swap', self.OnZAxisPivot)
        base.accept('dim_action_clear', self.OnAxisClear)
        base.accept('dim_view_tagset', self.OnViewTagset)
        base.accept('dim_view_hierarchy', self.OnViewHierarchy)
        base.accept('dim_move_to_axis', self.OnAxisMove)
        base.accept('update_added_filter', self.onUpdateFilterAdd)
        base.accept('cluster_cell_context_select', self.OnClusterContextMenuSelect)
        base.accept('CLICK_MOUSE3_None', self.mouseClickEmptySpaceMouseThree)
        
        
        # test accept for drill without filters.
        #base.accept('n', self.foo)
        #base.accept('m', self.foo2)

        # Add buttons for this mode
        browser.menu.pluginButtonContainer.createButton("Random", self.onRandomClick)
        browser.menu.pluginButtonContainer.createButton("Freefloat", self.onFreefloatClick)
        browser.menu.pluginButtonContainer.createButton("Reset view", self.onCameraReset)
        browser.menu.pluginButtonContainer.createButton("Clear", self.clearCube)
        self.toggleMenuButton = browser.menu.pluginButtonContainer.createButton("Hide menu", self.toggelRightMenu)
        
        self.menuMouseWatcherTask = taskMgr.add(self.__menuMouseWatcherTask, 'menuMouseWatcherTask')
        self.dimensionMenuVisable = False
        
        




    
    def mouseClickEmptySpaceMouseThree(self, event):
        context_menu_handler.openContext(self.space_context_menu)
    
    
    
    def __create_spaceContextMenu( self ):
        button_width = 6.8
        menu_items = ['view selected clusters in cardmode', 'view selected clusters in shooter']
        
        self.space_context_menu = DirectScrolledList(text_fg=(1,1,1,1), 
            text_shadow=(0,0,0,1), 
            frameColor=FRAME_COLOR, 
            frameSize=(-7, 7, -2.2, 1.15),
            borderWidth=(0.1,0.1), 
            relief=DGG.RIDGE, 
            text="", 
            forceHeight=1.6,
            scale=0.035,
            items = menu_items,
            numItemsVisible=len(menu_items),
            parent=aspect2d,
            itemMakeFunction=make_context_item,
            itemMakeExtraArgs=[self.spaceContextMenuButtonHandler, button_width]
        )
        self.space_context_menu.hide()
    
    
    def spaceContextMenuButtonHandler(self, title):
        
        if title == 'view selected clusters in cardmode':
            self.space_context_menu.hide()
            self.cube.clearSelectedClusters( )
            
            for cell in self.selectedCells.values():
                self.cube.addSelectedCell( cell )
                print 'ADDED CELL', cell
                
            # send event that we want to go inot card mode!
            messenger.send( 'change-mode', ['CardMode'] )  
        
        elif title == 'view selected clusters in shooter':
            #print 'SHOOT THIS MOTHERUCKER'
            self.space_context_menu.hide()
            self.cube.clearSelectedClusters( )
            
            for cell in self.selectedCells.values():
                self.cube.addSelectedCell( cell )
                
            # send event that we want to go inot card mode!
            messenger.send( 'change-mode', ['ShooterMode'] )  
        
        else:
            raise Exception('Coool stuff.')        
    
    
    
    def __menuMouseWatcherTask(self, task):
        if base.mouseWatcherNode.hasMouse():
            x=base.mouseWatcherNode.getMouseX()
            y=base.mouseWatcherNode.getMouseY()
            if x>=0.96 and not self.dimensionMenuVisable:
                self.rightMenu.show()
                self.dimensionMenuVisable = True
            
            if x <= 0.47 and self.dimensionMenuVisable:
                self.rightMenu.hide()
                self.dimensionMenuVisable = False   

            #print (x,y)
        return task.cont
    
    

    
    def toggelRightMenu(self):
        """
        Event function called when toggle menu button
        is pressed.
        """
        if self.rightMenuVisable:
            self.rightMenuVisable = False
            self.rightMenu.hide()
            self.toggleMenuButton['text'] = 'Show menu'
        else:
            self.rightMenu.show()
            self.rightMenuVisable = True
            self.toggleMenuButton['text'] = 'Hide menu'
            
    
    
    def load(self, cube):        

        # Store the new cube.
        self.cube = cube
        
        # reset the noraml vectors for the coordinate.
        self.__resetNormalVectors()
        
        # Show the images.
        self.__showImages()
        
        
        # Create dictionary for selected cells.
        self.selectedCells = dict()

        # Draw x_axis
        if browser.cube.cubeService.get_x() is not None:            
            if browser_config['show_cube_lines'] is not None and browser_config['show_cube_lines'].lower() == 'true':
                self.__drawXAxis()
            self.__drawXLabels()
            
        else:
            if browser_config['show_cube_lines'] is not None and browser_config['show_cube_lines'].lower() == 'true':
                self.__removeXAxis()
            self.__removeXLabels()
        
        if browser.cube.cubeService.get_y() is not None:
            if browser_config['show_cube_lines'] is not None and browser_config['show_cube_lines'].lower() == 'true':
                self.__drawYAxis()
            self.__drawYLabels()
        else:
            if browser_config['show_cube_lines'] is not None and browser_config['show_cube_lines'].lower() == 'true':
                self.__removeYAxis()
            self.__removeYLabels()
         
        if browser.cube.cubeService.get_z() is not None:
            if browser_config['show_cube_lines'] is not None and browser_config['show_cube_lines'].lower() == 'true':
                self.__drawZAxis()
            self.__drawZLabels()
        else:
            if browser_config['show_cube_lines'] is not None and browser_config['show_cube_lines'].lower() == 'true':
                self.__removeZAxis()
            self.__removeZLabels()
        
        # Place the camera.
        self.__positionCamera()
        self.root_np.setHpr(0,0,0)

        
        # Fix pos of parent labels.
        if self.parent_node_label_x is not None:
            self.parent_node_label_x.update_pos()

        if self.parent_node_label_z is not None:
            self.parent_node_label_z.update_pos()

        if self.parent_node_label_y is not None:
            self.parent_node_label_y.update_pos()

    



    def foo(self):
        """
        Test function for drilling down without filter in a hier.
        """
        browser.cube.cubeService.get_x().setLevel( browser.cube.cubeService.get_x().getLevel()+1 )
        browser.cube.cubeService.draw()
        self.__resetNormalVectors()
        self.__positionCamera()
    
    
    def foo2(self):
        """
        Test function for drilling up without filter in a hier.
        """
        browser.cube.cubeService.get_x().setLevel( browser.cube.cubeService.get_x().getLevel() - 1 )
        browser.cube.cubeService.draw()
        self.__resetNormalVectors()
        self.__positionCamera()



    def onUpdateFilterAdd(self):
        browser.cube.cubeService.draw()

    
    
    def toggleFreefloat(self):
        if self.floatingCameraHandler.isEnabled():
            self.floatingCameraHandler.disable()
        else:
            self.floatingCameraHandler.enable()
        


    def scroll(self, arg):
        
        if arg == 'up':
            if self.cube is None: return
            current_hovered_image = self.cube.getHoveredImage() 
            if current_hovered_image is not None:
                
                # Set the image that got the scroll event as front image.
                front_image = current_hovered_image
                
                
                pos = current_hovered_image.get_pos()
                
                # Create the cell key.
                pos_list = []
                for n in pos: 
                    if n is not None: pos_list.append( str(n) )
                key = ':'.join( pos_list )
                
                # Get the cell that we are scrolling in.
                cell = self.cube.getCell( key )
                
                
                # If there are more then one image in the cluster, then we will be scrolling.
                if len(cell.getVisableImages()) > 1:
                    cell_images = cell.getVisableImages()

                    # the stack value of the image in the back.
                    back_stack_pad = cell_images[ len( cell_images )-1 ].cluster_index

                    i = len(cell_images) - 1
                    while True:
                        cell_images[i].cluster_index = cell_images[i-1].cluster_index
                        i = i - 1
                        if i == 0:
                            break
                    
                    cell_images[0].cluster_index = back_stack_pad
                
                    # update the images with their new cluster index.
                    for image in cell_images:
                        image.clusterIndexUpdate()


        else:
            if self.cube is None: return
            current_hovered_image = self.cube.getHoveredImage() 
            if current_hovered_image is not None:
                # Set the image that got the scroll event as front image.
                front_image = current_hovered_image
                pos = front_image.get_pos()
                
                # Create the cell key.
                pos_list = []
                for n in pos: 
                    if n is not None: pos_list.append( str(n) )
                key = ':'.join( pos_list )
                
                # Get the cell that we are scrolling in.
                cell = self.cube.getCell(key)

                # If there are more then one image in the cluster, then we will be scrolling.
                if len( cell.getVisableImages() ) > 1:
                    cell_images = cell.getVisableImages()

                    # the stack value of the image in the back.
                    back_stack_pad = cell_images[ 0 ].cluster_index

                    i = 0
                    while True:
                        cell_images[i].cluster_index =  cell_images[i+1].cluster_index
                        i = i + 1
                        if i == len(cell_images)-1:
                            break
                    
                    cell_images[len(cell_images)-1].cluster_index = back_stack_pad
                

                    # update the images with their new cluster index.
                    for image in cell_images:
                        image.clusterIndexUpdate()

    

    def scale(self, arg):
        if arg == 'up':
            browser.cube.cubeService.set_max_image_size( browser.cube.cubeService.get_max_image_size() + 0.1 )
            browser.cube.cubeService.set_max_image_space( browser.cube.cubeService.get_max_image_space() + 0.05 )
        else:
            if browser.cube.cubeService.get_max_image_size() >=0:
                browser.cube.cubeService.set_max_image_size( browser.cube.cubeService.get_max_image_size() - 0.1 )
                browser.cube.cubeService.set_max_image_space( browser.cube.cubeService.get_max_image_space() - 0.05 )
        
        
        visibleImages = self.cube.getVisibleImages()
        for image_list in visibleImages.values():
            for image in image_list:
                image.scale_image()
                image.position()
        
        
        # reposition camera.
        if not self.floatingCameraHandler.isEnabled(): 
            self.__positionCamera()
        
        # Redraw the axis.
        if browser_config['show_cube_lines'].lower() == 'true':
            self.__drawXAxis()
            self.__drawYAxis()
            self.__drawZAxis()
        
        # Fix the position of the nodes on x-axis
        for node in self.x_labels.values():
            node.update()
        
        # Fix the position of the nodes on y-axis
        for node in self.y_labels.values():
            node.update()
        
        # Fix the position of the nodes on z-axis
        for node in self.z_labels.values():
            node.update()

        
        # Update parent labels, if needed.
        if self.parent_node_label_x is not None:
            self.parent_node_label_x.update_pos()
    
        # Update parent labels, if needed.
        if self.parent_node_label_y is not None:
            self.parent_node_label_y.update_pos()

        # Update parent labels, if needed.
        if self.parent_node_label_z is not None:
            self.parent_node_label_z.update_pos()


    def onCameraReset(self):
        self.__positionCamera()
        self.root_np.setHpr(0,0,0)
        
    
    
    def onFreefloatClick(self):
        if self.floatingCameraHandler.isEnabled():
            self.floatingCameraHandler.disable()
        else:
            self.floatingCameraHandler.enable()

    
    def clearCube(self):
        # Remove all lables.
        self.clearParentLabel(X_AXIS)
        self.clearParentLabel(Z_AXIS)
        self.clearParentLabel(Y_AXIS)
        
        self.__removeXLabels()
        self.__removeYLabels()
        self.__removeZLabels()
        self.__removeXAxis()
        self.__removeYAxis()
        self.__removeZAxis()
        
        
        self.images_np.remove()
        self.images_np = self.np.attachNewNode('images_nps')
        
        
        self.rightMenu.setXViewText("empty")
        self.rightMenu.setYViewText("empty")
        self.rightMenu.setZViewText("empty")
        browser.cube.cubeService.view_on_x( None )
        browser.cube.cubeService.view_on_y( None )
        browser.cube.cubeService.view_on_z( None )
        browser.cube.cubeService.draw()
        
        # If we were hovering any images, we must remove the info dialog.
        self.current_hovered_image = None
        self.cube.setHoveredImage(None)
        browser.dialogs.dialogService.closeInfoDialogs()

        
        
    
    def clearParentLabel(self, axis):
        if axis == X_AXIS:
            if self.parent_node_label_x is not None:
                self.parent_node_label_x.remove()
                self.parent_node_label_x = None

        elif axis == Y_AXIS:
            if self.parent_node_label_y is not None:
                self.parent_node_label_y.remove()
                self.parent_node_label_y = None
            
        elif axis == Z_AXIS:
            if self.parent_node_label_z is not None:
                self.parent_node_label_z.remove()
                self.parent_node_label_z = None

        else:
            raise Exception('Unknown axis.')
    
    

    def onRandomClick(self):
        """
        Event function, called when the random view button is clicked.
        """
        #print 'Doing some stuff'

        self.clearCube()
        
        # select some random dimensions to play with..
        tagsets = browser.objectcube.objectCubeService.getAllTagsets(True)
        
        for n in range(3):
            if browser.cube.cubeService.get_x() is None:
                r = random.randint(1, len(tagsets)-1)
                randomTagset = tagsets[r]
                dims = randomTagset.getPersistentDimensions()

                if len(dims) > 0:
                    #print 'Viewing dim', dims[0]
                    browser.cube.cubeService.view_on_x(dims[0])
                else:
                    #print 'viewing tagset', randomTagset.name
                    browser.cube.cubeService.view_on_x(randomTagset)
            

            if browser.cube.cubeService.get_z() is None:
                r = random.randint(1, len(tagsets)-1)
                randomTagset = tagsets[r]
                dims = randomTagset.getPersistentDimensions()

                if len(dims) > 0:
                    print 'Viewing dim', dims[0]
                    browser.cube.cubeService.view_on_z(dims[0])
                else:
                    print 'viewing tagset', randomTagset.name
                    browser.cube.cubeService.view_on_z(randomTagset)


            if browser.cube.cubeService.get_y() is None:
                r = random.randint(1, len(tagsets)-1)
                randomTagset = tagsets[r]
                dims = randomTagset.getPersistentDimensions()

                if len(dims) > 0:
                    print 'Viewing dim', dims[0]
                    browser.cube.cubeService.view_on_y(dims[0])
                else:
                    print 'viewing tagset', randomTagset.name
                    browser.cube.cubeService.view_on_y(randomTagset)


        browser.cube.cubeService.draw()















    
    
    def OnAxisMove(self, axisFrom, AxisTo):
        print 'moving axis around...'
        
        if axisFrom == Z_AXIS:
            print 'ZAXIS MOVING AROUND!!!'
            z = browser.cube.cubeService.coordinate.get_z()
            
            if AxisTo == X_AXIS:
                # clear parent of y and x
                self.clearParentLabel(Z_AXIS)
                self.clearParentLabel(X_AXIS)
                
                if z.is_hierarchy():
                    curr_node = z.get_current_node()
                
                    browser.cube.cubeService.view_on_x( z.tagset )
                    if not curr_node is None:
                        browser.cube.cubeService.coordinate.x.drill_down( curr_node )
                        parentNode = browser.cube.cubeService.coordinate.z.get_parent_node_for_current()
                        
                        # create parent label.
                        self.parent_node_label_x = DrillUpLabel( self.np, parentNode, X_AXIS )
                        self.parent_node_label_x.create_label()
                        base.accept( self.parent_node_label_x.create_clickable_box(), self.on_label_parent_x_click )

                    self.rightMenu.setXViewText(z.tagset.getRoot().name + " hierarchy")


                else:
                    browser.cube.cubeService.view_on_x( z.tagset )
                    browser.cube.cubeService.view_on_z( None )
                    self.rightMenu.setXViewText(z.tagset.name + " tagset")

            
                self.rightMenu.setZViewText("empty")
                browser.cube.cubeService.view_on_z( None )
                browser.cube.cubeService.draw()
        
        
            if AxisTo == Y_AXIS:
                # clear parent of y and x
                self.clearParentLabel(Z_AXIS)
                self.clearParentLabel(Y_AXIS)
                
                if z.is_hierarchy():
                    curr_node = z.get_current_node()
                
                    browser.cube.cubeService.view_on_y( z.tagset )
                    if not curr_node is None:
                        browser.cube.cubeService.coordinate.y.drill_down( curr_node )
                        parentNode = browser.cube.cubeService.coordinate.z.get_parent_node_for_current()
                        
                        # create parent label.
                        self.parent_node_label_y = DrillUpLabel( self.np, parentNode, Y_AXIS )
                        self.parent_node_label_y.create_label()
                        base.accept( self.parent_node_label_y.create_clickable_box(), self.on_label_parent_y_click )

                    self.rightMenu.setYViewText(z.tagset.getRoot().name + " hierarchy")


                else:
                    browser.cube.cubeService.view_on_y( z.tagset )
                    browser.cube.cubeService.view_on_z( None )
                    self.rightMenu.setYViewText(z.tagset.name + " tagset")

            
                self.rightMenu.setZViewText("empty")
                browser.cube.cubeService.view_on_z( None )
                browser.cube.cubeService.draw()
        
        
        
        if axisFrom == Y_AXIS:
            y = browser.cube.cubeService.coordinate.get_y()

            if AxisTo == X_AXIS:
                # clear parent of y and x
                self.clearParentLabel(Y_AXIS)
                self.clearParentLabel(X_AXIS)
                
                if y.is_hierarchy():
                    curr_node = y.get_current_node()
                
                    browser.cube.cubeService.view_on_x( y.tagset )
                    if not curr_node is None:
                        browser.cube.cubeService.coordinate.x.drill_down( curr_node )
                        parentNode = browser.cube.cubeService.coordinate.y.get_parent_node_for_current()
                        
                        # create parent label.
                        self.parent_node_label_x = DrillUpLabel( self.np, parentNode, X_AXIS )
                        self.parent_node_label_x.create_label()
                        base.accept( self.parent_node_label_x.create_clickable_box(), self.on_label_parent_x_click )

                    self.rightMenu.setXViewText(y.tagset.getRoot().name + " hierarchy")


                else:
                    browser.cube.cubeService.view_on_x( y.tagset )
                    browser.cube.cubeService.view_on_y( None )
                    self.rightMenu.setYViewText(y.tagset.name + " tagset")

            
                self.rightMenu.setYViewText("empty")
                browser.cube.cubeService.view_on_y( None )
                browser.cube.cubeService.draw()

        
            if AxisTo == Z_AXIS:
                # clear parent of y and x
                self.clearParentLabel(Y_AXIS)
                self.clearParentLabel(Z_AXIS)
                
                if y.is_hierarchy():
                    curr_node = y.get_current_node()
                
                    browser.cube.cubeService.view_on_z( y.tagset )
                    if not curr_node is None:
                        browser.cube.cubeService.coordinate.z.drill_down( curr_node )
                        parentNode = browser.cube.cubeService.coordinate.y.get_parent_node_for_current()
                        
                        # create parent label.
                        self.parent_node_label_z = DrillUpLabel( self.np, parentNode, Z_AXIS )
                        self.parent_node_label_z.create_label()
                        base.accept( self.parent_node_label_z.create_clickable_box(), self.on_label_parent_z_click )

                    self.rightMenu.setZViewText(y.tagset.getRoot().name + " hierarchy")


                else:
                    browser.cube.cubeService.view_on_z( y.tagset )
                    browser.cube.cubeService.view_on_y( None )
                    self.rightMenu.setYViewText(y.tagset.name + " tagset")

            
                self.rightMenu.setYViewText("empty")
                browser.cube.cubeService.view_on_y( None )
                browser.cube.cubeService.draw()
        
        
        
        
        if axisFrom == X_AXIS:
            x = browser.cube.cubeService.coordinate.get_x()
            
            if AxisTo == Z_AXIS:
                # clear parent of x and z
                self.clearParentLabel(X_AXIS)
                self.clearParentLabel(Z_AXIS)
                
                if x.is_hierarchy():
                    curr_node = x.get_current_node()
                
                    browser.cube.cubeService.view_on_z( x.tagset )
                    if not curr_node is None:
                        browser.cube.cubeService.coordinate.z.drill_down( curr_node )
                        parentNode = browser.cube.cubeService.coordinate.x.get_parent_node_for_current()
                        
                        # create parent label.
                        self.parent_node_label_z = DrillUpLabel( self.np, parentNode, Z_AXIS )
                        self.parent_node_label_z.create_label()
                        base.accept( self.parent_node_label_z.create_clickable_box(), self.on_label_parent_z_click )

                    self.rightMenu.setZViewText(x.tagset.getRoot().name + " hierarchy")


                else:
                    browser.cube.cubeService.view_on_z( x.tagset )
                    browser.cube.cubeService.view_on_x( None )
                    self.rightMenu.setZViewText(x.tagset.name + " tagset")

            
                self.rightMenu.setXViewText("empty")
                browser.cube.cubeService.view_on_x( None )
                browser.cube.cubeService.draw()



            if AxisTo == Y_AXIS:
                self.clearParentLabel(X_AXIS)
                self.clearParentLabel(Y_AXIS)
                
                if x.is_hierarchy():
                    curr_node = x.get_current_node()
                
                    browser.cube.cubeService.view_on_y( x.tagset )
                    if not curr_node is None:
                        browser.cube.cubeService.coordinate.y.drill_down( curr_node )
                        parentNode = browser.cube.cubeService.coordinate.x.get_parent_node_for_current()
                        
                        # create parent label.
                        self.parent_node_label_y = DrillUpLabel( self.np, parentNode, Y_AXIS )
                        self.parent_node_label_y.create_label()
                        base.accept( self.parent_node_label_y.create_clickable_box(), self.on_label_parent_y_click )

                    self.rightMenu.setYViewText(x.tagset.getRoot().name + " hierarchy")


                else:
                    #print 'WE ARE HERE!'
                    browser.cube.cubeService.view_on_y( x.tagset )
                    browser.cube.cubeService.view_on_x( None )
                    self.rightMenu.setYViewText(x.tagset.name + " tagset")

            
                self.rightMenu.setXViewText("empty")
                browser.cube.cubeService.view_on_x( None )
                browser.cube.cubeService.draw()


    
    def OnViewHierarchy(self, axis, dim):
        print 'view hir', dim, 'on axis', dim
        if axis == X_AXIS:
            browser.cube.cubeService.view_on_x( dim )
            #print 'level', browser.cube.cubeService.get_x().getLevel()
            self.rightMenu.setXViewText(dim.getRoot().name + " hierarchy")


        elif axis == Y_AXIS:
            browser.cube.cubeService.view_on_y( dim )
            self.rightMenu.setYViewText(dim.getRoot().name + " hierarchy")

        elif axis == Z_AXIS:
            browser.cube.cubeService.view_on_z( dim )
            self.rightMenu.setZViewText(dim.getRoot().name + " hierarchy")


        else:
            raise Exception('Unknonw axis')
        browser.cube.cubeService.draw()

    
    
    
    
    def OnViewTagset(self, axis, tagset):
        
        if axis == X_AXIS:
            browser.cube.cubeService.view_on_x(tagset)
            self.rightMenu.setXViewText(tagset.name + " tagset")

        elif axis == Y_AXIS:
            browser.cube.cubeService.view_on_y(tagset)
            self.rightMenu.setYViewText(tagset.name + " tagset")

        elif axis == Z_AXIS:
            browser.cube.cubeService.view_on_z(tagset)
            self.rightMenu.setZViewText(tagset.name + " tagset")

        else:
            raise Exception( 'Unknown axis!' )
        
        browser.cube.cubeService.draw()

    
    
    
    def OnAxisClear(self, axis):
        if axis == X_AXIS:
            # If there a parent label, then we remove it.
            if self.parent_node_label_x is not None:
                self.parent_node_label_x.remove()
                self.parent_node_label_x = None
            
            # View nothing on the x-axis
            browser.cube.cubeService.view_on_x( None )

            # Set the view text for the x-axis.
            self.rightMenu.setXViewText( 'empty' )



        if axis == Y_AXIS:
            # If there a parent label, then we remove it.
            if self.parent_node_label_y is not None:
                self.parent_node_label_y.remove()
                self.parent_node_label_y = None
            
            # View nothing on the x-axis
            browser.cube.cubeService.view_on_y( None )

            # Set the view text for the y-axis.
            self.rightMenu.setYViewText( 'empty' )

       

        if axis == Z_AXIS:
            # If there a parent label, then we remove it.
            if self.parent_node_label_z is not None:
                self.parent_node_label_z.remove()
                self.parent_node_label_z = None
            
            # View nothing on the x-axis
            browser.cube.cubeService.view_on_z( None )

            # Set the view text for the y-axis.
            self.rightMenu.setZViewText( 'empty' )
        

        browser.cube.cubeService.draw( )







    def OnZAxisPivot(self, axis): 
        z = browser.cube.cubeService.coordinate.get_z()
        
        # If there is nothing on z, we stop.
        if z is None:
            return
        
        if axis == X_AXIS:
            print 'We are pivoting with x'
            x = browser.cube.cubeService.coordinate.get_x()
            
            z_par_label = self.parent_node_label_z 
            x_par_label = self.parent_node_label_x
            
            # clear the labels.
            if self.parent_node_label_x is not None:
                self.parent_node_label_x.remove()
                self.parent_node_label_x = None
            
            
            if self.parent_node_label_z is not None:
                self.parent_node_label_z.remove()
                self.parent_node_label_z = None
            
               
            if z.is_hierarchy():
                curr_node = z.get_current_node()
            
                browser.cube.cubeService.view_on_x( z.tagset )
                
                if not curr_node is None:
                    browser.cube.cubeService.coordinate.x.drill_down( curr_node )
        
                
                if z_par_label is not None:
                    curr_node = z_par_label.getNode()
                    # Get the parent of the node that was cliecked.
                    
                    # Create the parent label. 
                    self.parent_node_label_x = DrillUpLabel( self.np, curr_node, X_AXIS )
                    self.parent_node_label_x.create_label()
                    base.accept( self.parent_node_label_x.create_clickable_box(), self.on_label_parent_x_click )


                self.rightMenu.setXViewText(z.tagset.getRoot().name + " hierarchy")
            
            
            else:
                browser.cube.cubeService.view_on_x( z.tagset )
                self.rightMenu.setXViewText(z.tagset.name + " tagset")

        
            
            if x is not None:
                if x.is_hierarchy():
                    curr_node = x.get_current_node()

                    browser.cube.cubeService.view_on_z( x.tagset )

                    if not curr_node is None:
                        browser.cube.cubeService.coordinate.z.drill_down( curr_node )


                    if x_par_label is not None:
                        curr_node = x_par_label.getNode()
                        
                        # Create the parent label. 
                        self.parent_node_label_z = DrillUpLabel( self.np, curr_node, Z_AXIS )
                        self.parent_node_label_z.create_label()
                        base.accept( self.parent_node_label_z.create_clickable_box(), self.on_label_parent_z_click )


                    self.rightMenu.setZViewText(x.tagset.getRoot().name + " hierarchy")

                else:
                    #print 'not dealing with hirs.'
                    browser.cube.cubeService.view_on_z( x.tagset )
                    self.rightMenu.setZViewText(x.tagset.name + " tagset")
            else:
                browser.cube.cubeService.view_on_z( None )
                self.rightMenu.setZViewText("Empty")




        if axis == Y_AXIS:
            print 'We are pivoting with x'
            y = browser.cube.cubeService.coordinate.get_y()
            
            z_par_label = self.parent_node_label_z 
            y_par_label = self.parent_node_label_y
            
            # clear the labels.
            if self.parent_node_label_y is not None:
                self.parent_node_label_y.remove()
                self.parent_node_label_y = None
            
            
            if self.parent_node_label_z is not None:
                self.parent_node_label_z.remove()
                self.parent_node_label_z = None
            
               
            if z.is_hierarchy():
                curr_node = z.get_current_node()
            
                browser.cube.cubeService.view_on_y( z.tagset )
                
                if not curr_node is None:
                    browser.cube.cubeService.coordinate.y.drill_down( curr_node )
        
                
                if z_par_label is not None:
                    curr_node = z_par_label.getNode()
                    # Get the parent of the node that was cliecked.
                    
                    # Create the parent label. 
                    self.parent_node_label_y = DrillUpLabel( self.np, curr_node, Y_AXIS )
                    self.parent_node_label_y.create_label()
                    base.accept( self.parent_node_label_y.create_clickable_box(), self.on_label_parent_y_click )


                self.rightMenu.setYViewText(z.tagset.getRoot().name + " hierarchy")
            
            
            else:
                browser.cube.cubeService.view_on_y( z.tagset )
                self.rightMenu.setYViewText(z.tagset.name + " tagset")

        
            
            if y is not None:
                if y.is_hierarchy():
                    curr_node = y.get_current_node()

                    browser.cube.cubeService.view_on_z( y.tagset )

                    if not curr_node is None:
                        browser.cube.cubeService.coordinate.z.drill_down( curr_node )


                    if y_par_label is not None:
                        curr_node = y_par_label.getNode()
                        
                        # Create the parent label. 
                        self.parent_node_label_z = DrillUpLabel( self.np, curr_node, Z_AXIS )
                        self.parent_node_label_z.create_label()
                        base.accept( self.parent_node_label_z.create_clickable_box(), self.on_label_parent_z_click )


                    self.rightMenu.setZViewText(y.tagset.getRoot().name + " hierarchy")

                else:
                    #print 'not dealing with hirs.'
                    browser.cube.cubeService.view_on_z( y.tagset )
                    self.rightMenu.setZViewText(y.tagset.name + " tagset")
            else:
                browser.cube.cubeService.view_on_z( None )
                self.rightMenu.setZViewText("Empty")


        # Draw the coordinate. 
        browser.cube.cubeService.draw()







    def OnYAxisPivot(self, axis):
        print 'doing pivot on x with', axis
        
        
        y = browser.cube.cubeService.coordinate.get_y()
        
        
        # If there is nothing on y, we stop.
        if y is None:
            return
        
        
        if axis == X_AXIS:
            print 'We are pivoting with x'
            x = browser.cube.cubeService.coordinate.get_x()
            
            y_par_label = self.parent_node_label_y 
            x_par_label = self.parent_node_label_x
            
            # clear the labels.
            if self.parent_node_label_x is not None:
                self.parent_node_label_x.remove()
                self.parent_node_label_x = None
            
            if self.parent_node_label_y is not None:
                self.parent_node_label_y.remove()
                self.parent_node_label_y = None
            
               
            if y.is_hierarchy():
                curr_node = y.get_current_node()
            
                browser.cube.cubeService.view_on_x( y.tagset )
                
                if not curr_node is None:
                    browser.cube.cubeService.coordinate.x.drill_down( curr_node )
        
                
                if y_par_label is not None:
                    curr_node = y_par_label.getNode()
                    # Get the parent of the node that was cliecked.
                    
                    # Create the parent label. 
                    self.parent_node_label_x = DrillUpLabel( self.np, curr_node, X_AXIS )
                    self.parent_node_label_x.create_label()
                    base.accept( self.parent_node_label_x.create_clickable_box(), self.on_label_parent_x_click )


                self.rightMenu.setXViewText(y.tagset.getRoot().name + " hierarchy")
            
            
            else:
                browser.cube.cubeService.view_on_x( y.tagset )
                self.rightMenu.setXViewText(y.tagset.name + " tagset")

        
            
            if x is not None:
                if x.is_hierarchy():
                    curr_node = x.get_current_node()

                    browser.cube.cubeService.view_on_y( x.tagset )

                    if not curr_node is None:
                        browser.cube.cubeService.coordinate.y.drill_down( curr_node )


                    if x_par_label is not None:
                        curr_node = x_par_label.getNode()
                        
                        # Create the parent label. 
                        self.parent_node_label_y = DrillUpLabel( self.np, curr_node, Y_AXIS )
                        self.parent_node_label_y.create_label()
                        base.accept( self.parent_node_label_y.create_clickable_box(), self.on_label_parent_y_click )


                    self.rightMenu.setYViewText(x.tagset.getRoot().name + " hierarchy")

                else:
                    #print 'not dealing with hirs.'
                    browser.cube.cubeService.view_on_y( x.tagset )
                    self.rightMenu.setYViewText(x.tagset.name + " tagset")
            else:
                browser.cube.cubeService.view_on_y( None )
                self.rightMenu.setYViewText("Empty")

            # Draw the coordinate. 
            browser.cube.cubeService.draw()



        if axis == Z_AXIS:
            print 'We are pivoting with z'
            z = browser.cube.cubeService.coordinate.get_z()
            
            y_par_label = self.parent_node_label_y 
            z_par_label = self.parent_node_label_z
            
            # clear the labels.
            if self.parent_node_label_z is not None:
                self.parent_node_label_z.remove()
                self.parent_node_label_z = None
            
            if self.parent_node_label_y is not None:
                self.parent_node_label_y.remove()
                self.parent_node_label_y = None
            
               
            if y.is_hierarchy():
                curr_node = y.get_current_node()
            
                browser.cube.cubeService.view_on_z( y.tagset )
                
                if not curr_node is None:
                    browser.cube.cubeService.coordinate.z.drill_down( curr_node )
        
                
                if y_par_label is not None:
                    curr_node = y_par_label.getNode()
                    # Get the parent of the node that was cliecked.
                    
                    # Create the parent label. 
                    self.parent_node_label_z = DrillUpLabel( self.np, curr_node, Z_AXIS )
                    self.parent_node_label_z.create_label()
                    base.accept( self.parent_node_label_z.create_clickable_box(), self.on_label_parent_z_click )


                self.rightMenu.setZViewText(y.tagset.getRoot().name + " hierarchy")
            
            
            else:
                browser.cube.cubeService.view_on_z( y.tagset )
                self.rightMenu.setZViewText(y.tagset.name + " tagset")

        
            
            if z is not None:
                if z.is_hierarchy():
                    curr_node = z.get_current_node()

                    browser.cube.cubeService.view_on_y( z.tagset )

                    if not curr_node is None:
                        browser.cube.cubeService.coordinate.y.drill_down( curr_node )


                    if z_par_label is not None:
                        curr_node = z_par_label.getNode()
                        
                        # Create the parent label. 
                        self.parent_node_label_y = DrillUpLabel( self.np, curr_node, Y_AXIS )
                        self.parent_node_label_y.create_label()
                        base.accept( self.parent_node_label_y.create_clickable_box(), self.on_label_parent_y_click )


                    self.rightMenu.setYViewText(z.tagset.getRoot().name + " hierarchy")

                else:
                    #print 'not dealing with hirs.'
                    browser.cube.cubeService.view_on_y( z.tagset )
                    self.rightMenu.setYViewText(z.tagset.name + " tagset")
            else:
                browser.cube.cubeService.view_on_y( None )
                self.rightMenu.setYViewText("Empty")

            # Draw the coordinate. 
            browser.cube.cubeService.draw()
   




    
    
    
    def OnXAxisPivot(self, axis):
        print 'doing pivot on x with', axis
        
        
        x = browser.cube.cubeService.coordinate.get_x()
        
        
        # If there is nothing on x, we stop.
        if x is None:
            return
        
        
        
        if axis == Z_AXIS:
            print 'We are pivoting with z'
            z = browser.cube.cubeService.coordinate.get_z()
            
            x_par_label = self.parent_node_label_x 
            z_par_label = self.parent_node_label_z

            # clear the labels.
            if self.parent_node_label_x is not None:
                self.parent_node_label_x.remove()
                self.parent_node_label_x = None
            
            if self.parent_node_label_z is not None:
                self.parent_node_label_z.remove()
                self.parent_node_label_z = None


            
               
            if x.is_hierarchy():
                curr_node = x.get_current_node()
            
                browser.cube.cubeService.view_on_z( x.tagset )
                
                if not curr_node is None:
                    browser.cube.cubeService.coordinate.z.drill_down( curr_node )
        
                
                if x_par_label is not None:
                    curr_node = x_par_label.getNode()
                    
                    # Create the parent label. 
                    self.parent_node_label_z = DrillUpLabel( self.np, curr_node, 2 )
                    self.parent_node_label_z.create_label()
                    base.accept( self.parent_node_label_z.create_clickable_box(), self.on_label_parent_z_click )


                self.rightMenu.setZViewText(x.tagset.getRoot().name + " hierarchy")
            
            
            else:
                browser.cube.cubeService.view_on_z( x.tagset )
                self.rightMenu.setZViewText(x.tagset.name + " tagset")

        
            
            
            
            if z is not None:
                if z.is_hierarchy():
                    curr_node = z.get_current_node()

                    browser.cube.cubeService.view_on_x( z.tagset )

                    if not curr_node is None:
                        browser.cube.cubeService.coordinate.x.drill_down( curr_node )


                    if z_par_label is not None:
                        curr_node = z_par_label.getNode()
                        
                        # Create the parent label. 
                        self.parent_node_label_x = DrillUpLabel( self.np, curr_node, 0 )
                        self.parent_node_label_x.create_label()
                        base.accept( self.parent_node_label_x.create_clickable_box(), self.on_label_parent_x_click )


                    self.rightMenu.setXViewText(z.tagset.getRoot().name + " hierarchy")

                else:
                    #print 'not dealing with hirs.'
                    browser.cube.cubeService.view_on_x( z.tagset )
                    self.rightMenu.setXViewText(z.tagset.name + " tagset")
            else:
                browser.cube.cubeService.view_on_x( None )
                self.rightMenu.setXViewText("Empty")


            # Draw the coordinate. 
            browser.cube.cubeService.draw()

    
    


        if axis == Y_AXIS:
            print 'We are pivoting with y'
            y = browser.cube.cubeService.coordinate.get_y()
            
            x_par_label = self.parent_node_label_x 
            y_par_label = self.parent_node_label_y 
            
               
            # clear the labels.
            if self.parent_node_label_x is not None:
                self.parent_node_label_x.remove()
                self.parent_node_label_x = None
            
            if self.parent_node_label_y is not None:
                self.parent_node_label_y.remove()
                self.parent_node_label_y = None



            if x.is_hierarchy():
                curr_node = x.get_current_node()
            
                browser.cube.cubeService.view_on_y( x.tagset )
                
                if not curr_node is None:
                    browser.cube.cubeService.coordinate.y.drill_down( curr_node )
        
                
                if x_par_label is not None:
                    curr_node = x_par_label.getNode()
                    # Get the parent of the node that was cliecked.
                    
                    # Create the parent label. 
                    self.parent_node_label_y = DrillUpLabel( self.np, curr_node, 1 )
                    self.parent_node_label_y.create_label()
                    base.accept( self.parent_node_label_y.create_clickable_box(), self.on_label_parent_y_click )


                #self.text_z.setText( x.tagset.getRoot().name + ' on up' )
                self.rightMenu.setYViewText(x.tagset.getRoot().name + " hierarchy")
            
            
            else:
                browser.cube.cubeService.view_on_y( x.tagset )
                #self.text_z.setText( x.tagset.name + ' on up' )
                self.rightMenu.setYViewText(x.tagset.name + " tagset")

        
            
            
            
            if y is not None:
                if y.is_hierarchy():
                    curr_node = y.get_current_node()

                    browser.cube.cubeService.view_on_x( y.tagset )

                    if not curr_node is None:
                        browser.cube.cubeService.coordinate.x.drill_down( curr_node )


                    if y_par_label is not None:
                        curr_node = y_par_label.getNode()
                        
                        # Create the parent label. 
                        self.parent_node_label_x = DrillUpLabel( self.np, curr_node, 0 )
                        self.parent_node_label_x.create_label()
                        base.accept( self.parent_node_label_x.create_clickable_box(), self.on_label_parent_x_click )


                    self.rightMenu.setXViewText(y.tagset.getRoot().name + " hierarchy")

                else:
                    #print 'not dealing with hirs.'
                    browser.cube.cubeService.view_on_x( y.tagset )
                    self.rightMenu.setXViewText(y.tagset.name + " tagset")
            else:
                browser.cube.cubeService.view_on_x( None )
                self.rightMenu.setXViewText("Empty")


            # Draw the coordinate. 
            browser.cube.cubeService.draw()



    
    def __drawXAxis(self):
        x_len = self.cube.x_cell_count

        # we must clear the lines that were before.
        if self.coordinate_line_nps[0] is not None:
            self.coordinate_line_nps[0].remove()
        
        if x_len > 0:
            
            ls_x = LineSegs()
            ls_x.setThickness( 1 )
            n_points = x_len
            n_lineLength = (n_points * browser.cube.cubeService.get_max_image_size()) + ((n_points-1) * browser.cube.cubeService.get_max_image_space())
            
            # draw the line for this axis.
            ls_x.setColor(0, 0, 0, 0)
            ls_x.moveTo(0.0, 0.0, 0.0)
            ls_x.drawTo(n_lineLength, 0.0, 0.0)

            # Create nodepath for the x line
            node = ls_x.create()
            self.coordinate_line_nps[0] = NodePath(node) 
            self.coordinate_line_nps[0].reparentTo(self.np)
    

    def __removeXAxis(self):
         # we must clear the lines that were before.
        if self.coordinate_line_nps[0] is not None:
            self.coordinate_line_nps[0].remove()
            self.coordinate_line_nps[0] = None
     
    
    def __removeYAxis(self):
        if self.coordinate_line_nps[1] is not None:
            self.coordinate_line_nps[1].remove()
            self.coordinate_line_nps[1] = None
    
    def __removeZAxis(self):
        if self.coordinate_line_nps[2] is not None:
            self.coordinate_line_nps[2].remove()
            self.coordinate_line_nps[2] = None
    
    
    
    def __drawYAxis(self):
        y_len = self.cube.y_cell_count
        
        # we must clear the lines that were before.
        if self.coordinate_line_nps[1] is not None:
            self.coordinate_line_nps[1].remove()
        
        if y_len > 0:
            ls_y = LineSegs()
            ls_y.setThickness( 1 )
            n_points = y_len
            n_lineLength = (n_points * browser.cube.cubeService.get_max_image_size()) + ((n_points-1) * browser.cube.cubeService.get_max_image_space())
            
            ls_y.setColor(0, 0, 0, 0)
            ls_y.moveTo(0.0,0.0,0)
            ls_y.drawTo(0.0, n_lineLength, 0.0)
                
            # Create nodepath for the z line
            node = ls_y.create()
            self.coordinate_line_nps[1] = NodePath(node) 
            self.coordinate_line_nps[1].reparentTo(self.np)
   
    def __drawZAxis(self):
        z_len = self.cube.z_cell_count
        
        # we must clear the lines that were before.
        if self.coordinate_line_nps[2] is not None:
            self.coordinate_line_nps[2].remove()
        
        if z_len > 0:
            ls_z = LineSegs()
            ls_z.setThickness( 1 )
            n_points = z_len
            n_lineLength = (n_points * browser.cube.cubeService.get_max_image_size()) + ((n_points-1) * browser.cube.cubeService.get_max_image_space())
            
            ls_z.setColor(0, 0, 0.0, 0.0)
            ls_z.moveTo(0.0, 0.0, 0.0)
            ls_z.drawTo(0.0, 0.0, n_lineLength)
                
            # Create nodepath for the z line
            node = ls_z.create()
            self.coordinate_line_nps[2] = NodePath(node) 
            self.coordinate_line_nps[2].reparentTo(self.np)
     

    








    def __drawXLabels( self ):
        #print 'Drawing x labels for x-axis.'
        
        # Empty the label list. 
        self.x_labels = dict()
        
        # If there are labels before on x-axis, we remove them
        if self.x_labels_np is not None:  
            self.x_labels_np.remove()

        self.x_labels_np = self.np.attachNewNode('x_label_nodes') 
        x_labels = self.cube.getLabelsForAxis(X_AXIS)
        
        # Setting parent for the labels.
        for label in x_labels:
            label.set_parent( self.x_labels_np )
            
            
            # count sub-images in a node and set the count to the label.
            if label.get_hierarchy():
                node = browser.cube.cubeService.get_x().get_node_by_label( label.__str__() )
                num_branches = len(node.getBranches())
                aggr_image_count = len( browser.cube.cubeService.get_x().get_node_by_label( label.__str__() ).getObjectIds())
                if aggr_image_count > 0 and num_branches > 0:
                    label.set_aggrigation_num( aggr_image_count )

            label.create()
            label.update()
            
            self.x_labels[ label.__str__() ] = label
            # Check if we need to create a label for drilling.
            if label.get_hierarchy():    
                node = browser.cube.cubeService.get_x().get_node_by_label( label.__str__() )
                num_branches = len(node.getBranches())

                if num_branches > 0:
                    label.create_click_card()
                    base.accept(  label.get_picker_message( ) , self.event_on_click_label_x )
                    #self.x_labels[ label.__str__() ] = label #fail
            




    def __drawYLabels( self ):

        y = browser.cube.cubeService.get_y() 

        # Empty the label list. 
        self.y_labels = dict()

        if self.y_labels_np is not None:  
            self.y_labels_np.remove()

        self.y_labels_np = self.np.attachNewNode('y_label_nodes') 
        y_labels = self.cube.getLabelsForAxis(1)

        for label in y_labels:
            label.set_parent( self.y_labels_np )

            if label.get_hierarchy():
                # get image aggriagion for the label.
                node = y.get_node_by_label( label.__str__() )
                num_branches = len(node.getBranches())
                aggr_image_count = len(y.get_node_by_label( label.__str__() ).getObjectIds())
                if aggr_image_count > 0 and num_branches > 0:
                    label.set_aggrigation_num( aggr_image_count )

            label.create()
            label.update()
            self.y_labels[ label.__str__() ] = label

            if label.get_hierarchy():
                # Check if we need to create a label for drilling.
                node = y.get_node_by_label( label.__str__() )
                num_branches = len(node.getBranches())

                if num_branches > 0:
                    label.create_click_card()
                    base.accept(  label.get_picker_message( ) , self.event_on_click_label_y )
                    


    def __drawZLabels( self ):

        z = browser.cube.cubeService.get_z()

        # Empty the label list. 
        self.z_labels = dict()

        if self.z_labels_np is not None:  
            self.z_labels_np.remove()

        self.z_labels_np = self.np.attachNewNode('z_label_nodes') 
        z_labels = self.cube.getLabelsForAxis(2)

        for label in z_labels:
            label.set_parent( self.z_labels_np )

            if label.get_hierarchy():
                # get image aggriagion for the label.
                node = z.get_node_by_label( label.__str__() )
                num_branches = len(node.getBranches())
                aggr_image_count = len(z.get_node_by_label( label.__str__() ).getObjectIds())
                if aggr_image_count > 0 and num_branches > 0:
                    label.set_aggrigation_num( aggr_image_count )

            label.create()
            label.update()
            self.z_labels[ label.__str__() ] = label

            if label.get_hierarchy():
                # Check if we need to create a label for drilling.
                node = z.get_node_by_label( label.__str__() )
                num_branches = len(node.getBranches())

                if num_branches > 0:
                    label.create_click_card()
                    base.accept(  label.get_picker_message( ) , self.event_on_click_label_z )
                    








    def __removeXLabels( self ):   
        if self.x_labels_np is not None:  
            self.x_labels = dict()
            self.x_labels_np.remove()
            self.x_labels_np = None
            
    
    def __removeYLabels( self ):   
        if self.y_labels_np is not None:  
            self.y_labels_np.remove()
            self.y_labels_np = None
    
    
    def __removeZLabels( self ):   
        if self.z_labels_np is not None:  
            self.z_labels_np.remove()
            self.z_labels_np = None    
 
    
    def __positionCamera(self):
        base.camera.setHpr(0,0,0)
        base.camera.setY(-90)
        base.camera.setZ(0)
        base.camera.setX(0)
 
        if browser.cube.cubeService.get_x() is not None:
            num_x_nodes =  browser.cube.cubeService.get_x().get_node_count()
            # Calculating the center of the line.
            x_pos = (  browser.cube.cubeService.get_max_image_size() * num_x_nodes ) 
            x_pos += browser.cube.cubeService.get_max_image_space() * (num_x_nodes-1)
            x_pos = (x_pos / 2.0)
            base.camera.setX( x_pos )

        if browser.cube.cubeService.get_y() is not None:
            num_y_nodes =  browser.cube.cubeService.get_y().get_node_count()
    
        if browser.cube.cubeService.get_z() is not None:
            num_z_nodes =  browser.cube.cubeService.get_z().get_node_count()
            # Calculating the center of the line.
            z_pos = (  browser.cube.cubeService.get_max_image_size() * num_z_nodes ) 
            z_pos += browser.cube.cubeService.get_max_image_space() * (num_z_nodes - 1)
            z_pos = (z_pos / 2.0)
            # Do we want the camera to go down when we have a large z axis?
            base.camera.setZ( z_pos )

        # Fix normal vectors for rotation for x.
        if browser.cube.cubeService.get_x() is not None:
            x_pos = ( browser.cube.cubeService.get_max_image_size() * num_x_nodes ) # what happens when we rotade? 
            x_pos += browser.cube.cubeService.get_max_image_space() * (num_x_nodes - 1 )
            x_pos = (x_pos / 2.0)
            self.np.setX(-x_pos)
            self.root_np.setX(x_pos)
        
        # Fix the normal vector for z.
        if browser.cube.cubeService.get_z() is not None:
            z_pos = ( browser.cube.cubeService.get_max_image_size() * num_z_nodes ) 
            z_pos += browser.cube.cubeService.get_max_image_space() * (num_z_nodes - 1)
            z_pos = (z_pos / 2.0)
            self.np.setZ(-z_pos)
            self.root_np.setZ(z_pos)

        # Fix the normal vector for y.
        if browser.cube.cubeService.get_y() is not None:
            y_pos = ( browser.cube.cubeService.get_max_image_size() * num_y_nodes ) 
            y_pos += browser.cube.cubeService.get_max_image_space() * (num_y_nodes - 1)
            y_pos = (y_pos / 2.0)
            self.np.setY(-y_pos)
            self.root_np.setY(y_pos)
    
    
    
    
    
    
    
    
    def __showImages(self):
        # WE SHOULD MOVE THIS TO THE MODE SERVICE!! AND DO THIS FOR ALL MODES:
        browser.image.image_event_service.clear_messages()
        
        
        # If there is no cube, then we don't have to show any images.
        if self.cube is None: return
        
        cells = self.cube.getCells()
        print 'got cells', len(cells), 'number of cells.'

        showing_images = []

        
        for cell in cells.values():
            # Calculate a good size of images for the cell.  
            num_images = (len(cell.getImages())/10)+5 % 10
            
            if num_images > 20:
                num_images = 20
            
            # index for image cluster value.
            cluster_index = 0
            
            visible_cell_images = cell.getVisableImages()
            
            while num_images > 0 and len(visible_cell_images) > 0:
                image = visible_cell_images.pop()
                image.cluster_index = cluster_index
                image.position(animate=True)
                # add events to the image. 
                image.get_np().reparentTo(self.images_np)
                browser.image.image_event_service.add_message( image.getClickMessageLeft(), self.on_image_click_left )
                browser.image.image_event_service.add_message( image.getClickMessageRight(), self.on_image_click_right )
           
                # Get the mouse over messages from the image.
                browser.image.image_event_service.add_message( image.get_mouseover_message(), self.on_image_mouse_over )
                browser.image.image_event_service.add_message( image.get_mouseleave_message(), self.on_image_mouse_leave )
                num_images -= 1
                cluster_index += 1
            
            
            # if there is any rest of images left, then we have to remove them
            for image in visible_cell_images:
                image.remove()
            

            for image in cell.getImages():
                if num_images <= 0:
                    break
                
                if not image.isVisible():
                    image.get_np().reparentTo(self.images_np)
                    image.cluster_index = cluster_index
                    image.position(animate=True)
                    image.shake()
                    image.load_data()
                    showing_images.append(image)
                    
                    # Add events for images.
                    browser.image.image_event_service.add_message( image.getClickMessageLeft(), self.on_image_click_left )
                    browser.image.image_event_service.add_message( image.getClickMessageRight(), self.on_image_click_right )
               
                    # Get the mouse over messages from the image.
                    browser.image.image_event_service.add_message( image.get_mouseover_message(), self.on_image_mouse_over )
                    browser.image.image_event_service.add_message( image.get_mouseleave_message(), self.on_image_mouse_leave )
 
                    num_images -= 1
                    cluster_index += 1
                else:
                    # GET SHIT
                    browser.image.image_event_service.add_message( image.getClickMessageLeft(), self.on_image_click_left )
                    browser.image.image_event_service.add_message( image.getClickMessageRight(), self.on_image_click_right )
               
                    # Get the mouse over messages from the image.
                    browser.image.image_event_service.add_message( image.get_mouseover_message(), self.on_image_mouse_over )
                    browser.image.image_event_service.add_message( image.get_mouseleave_message(), self.on_image_mouse_leave )
                
                    
        for image in showing_images:
            image.show()
        
        self.images = self.cube.getVisibleImages()



    
    
    
    def __resetNormalVectors(self):
        """
        Resetting the nps for the coordiante.
        """
        self.root_np.setX(0)
        self.np.setX(0)
        self.root_np.setZ(0)
        self.np.setZ(0)
        self.root_np.setY(0)
        self.np.setY(0)
    
    
    
    
    def on_image_mouse_over(self, np):
        """
        Event function. This function is called when the mouse goes over an image.
        """
        if not self.cubeMouseRotater.isRotating() and not self.floatingCameraHandler.isEnabled():
            id = int( np.__str__().split(';')[1] )
            location = np.__str__().split(';')[2]
            
            for image in self.images[ location ]:
                if image.get_id() == id:
                    self.current_hovered_image = image
                    self.cube.setHoveredImage(image)
                    cell = self.cube.getCell(image.getCellKey())
                    clusterTags = {0:cell.getXtag(), 1:cell.getYtag(), 2:cell.getZtag()}
                    browser.dialogs.dialogService.openCellInfoDialog(image.getCellKey(), len(cell.getImages()), clusterTags)
                    break
    
    
    
    def on_image_mouse_leave(self, np=None):
        """
        Event function. This function is called when the mouse leaves an image.
        """
        #print 'Mouse over leave image'
        self.current_hovered_image = None
        self.cube.setHoveredImage(None)
        browser.dialogs.dialogService.closeInfoDialogs()

    
    
    
    
    
    def on_image_click_left(self, np):
        id = int( np.__str__().split(';')[1] )
        location = np.__str__().split(';')[2]
        image = None
        for img in self.images[ location ]:
            if img.get_id() == id:
                image = img
                break
                
            
        if img is None: raise Exception('No Image found!')
        
        # Let the cube know what image was clicked.
        self.cube.setLastClickedImage(image)
        
        #cluster = self.cells[ image.get_cluster_key() ]
        cell = self.cube.getCell(image.getCellKey())

        # Get the cluster that the user clicked on and add it to the collectoin
        
        # When user clicks the image we only want to select that single cluster
        self.cube.clearSelectedClusters( )
        self.cube.addSelectedCell( cell )
        
        #print 'got cluster', cluster 
        
        # send event that we want to go inot card mode!
        messenger.send( 'change-mode', ['CardMode'] )    
    
    
    def on_image_click_right(self, np):
        print browser.menu.context_menu_handler.open_image_context()


    
    


    
    
    
    def event_on_click_label_x(self, np, mouse = None):
        """"Event function when drill-down label is clicked on x axis."""
        tag_title = np.__str__().split('/')[-1]
        clicked_label = self.x_labels[ tag_title ]
        clicked_node = browser.cube.cubeService.get_x().get_node_by_label( clicked_label.title )
        #print 'DRILLING DOWN ON NODE with id', clicked_node.getNode().tagId
        
        # create action for the drilldown
        action = ActionAxis(ACTION_DRILL_DOWN, axis1=X_AXIS, tagId=clicked_node.getNode().tagId)
        actionManager.addAction(action)
        
        browser.cube.cubeService.get_x().drill_down( clicked_node )
        browser.cube.cubeService.coordinate.constructCube()
        self.load( browser.cube.cubeService.coordinate.cube )

        # Create drill up label
        if self.parent_node_label_x is not None:
            self.parent_node_label_x.remove()
            self.parent_node_label_x = None

        # Get the parent of the node that was cliecked.
        parent_node = browser.cube.cubeService.get_x().get_parent_for_node( clicked_node )
        
        # Create the parent label. 
        self.parent_node_label_x = DrillUpLabel( self.np, parent_node, 0 )
 
        # Create the label.
        self.parent_node_label_x.create_label()
        
        # Accept the click event.
        base.accept( self.parent_node_label_x.create_clickable_box(), self.on_label_parent_x_click)
        
        # Update the position with respect to image size and space. 
        self.parent_node_label_x.update_pos()







    
    
    
    
    
    
    
    def on_label_parent_x_click(self, e, mouse_button=None):
        x = browser.cube.cubeService.get_x()
        node = x.get_parent_node_for_current()
        x.drill_up( node )
        browser.cube.cubeService.coordinate.constructCube()
        self.load( browser.cube.cubeService.coordinate.cube )
        
        # create action for the drillup
        action = ActionAxis(ACTION_DRILL_UP, axis1=X_AXIS, tagId=node.getNode().tagId)
        actionManager.addAction(action)
        
        # Create drill up label
        parent = None
        try:
            parent = x.get_parent_for_node( node )
        except:
            pass
        
        
        if self.parent_node_label_x is not None:
            self.parent_node_label_x.remove()
            self.parent_node_label_x = None
 
        if parent is not None:
            # Create drill up label.
            self.parent_node_label_x = DrillUpLabel( self.np , parent, 0 )
            self.parent_node_label_x.create_label()
            base.accept( self.parent_node_label_x.create_clickable_box(), self.on_label_parent_x_click)
            self.parent_node_label_x.update_pos() 



    
    
    def event_on_click_label_y(self, np, mouse_button=None):
        """"
        Event function for clicking on label on the X-coordinate for drill-down
        for that node.
        """
        y = browser.cube.cubeService.get_y()
        tag_title = np.__str__().split('/')[-1]
        clicked_label = self.y_labels[ tag_title ]
        clicked_node = y.get_node_by_label( clicked_label.title )
        
        print 'DRILLING DOWN ON NODE with id', clicked_node.getNode().tagId
        
        # create action for the drilldown
        action = ActionAxis(ACTION_DRILL_DOWN, axis1=Y_AXIS, tagId=clicked_node.getNode().tagId)
        actionManager.addAction(action)
        
        y.drill_down( clicked_node )
        
        browser.cube.cubeService.coordinate.constructCube()
        self.load( browser.cube.cubeService.coordinate.cube )

        # Create drill up label
        if self.parent_node_label_y is not None:
            self.parent_node_label_y.remove()
            self.parent_node_label_y = None

        #self.y_parent_node_label = self.np.attachNewNode('y_parent_node')
        
        # Create drill up label
        parent_node = y.get_parent_for_node( clicked_node )
        self.parent_node_label_y = DrillUpLabel( self.np, parent_node, 1 )
        self.parent_node_label_y.create_label()
        base.accept( self.parent_node_label_y.create_clickable_box(), self.on_label_parent_y_click)
        self.parent_node_label_y.update_pos()



    def on_label_parent_y_click(self, e, mouse_button=None):
        """
        Event when we click on z parent label. 
        """
        y = browser.cube.cubeService.get_y()
        node = y.get_parent_node_for_current()
        y.drill_up( node )
        
        browser.cube.cubeService.coordinate.constructCube()
        self.load( browser.cube.cubeService.coordinate.cube )
        
        # create action for the drillup
        action = ActionAxis(ACTION_DRILL_UP, axis1=Y_AXIS, tagId=node.getNode().tagId)
        actionManager.addAction(action)
        

        # Create drill up label
        parent = None
        try:
            parent = y.get_parent_for_node( node )
        except:
            pass
        
        
        if self.parent_node_label_y is not None: 
            self.parent_node_label_y.remove()
            self.parent_node_label_y = None
        
        if parent is not None:
            # Create drill up label.
            self.parent_node_label_y = DrillUpLabel( self.np, parent, 1 )
            self.parent_node_label_y.create_label()
            base.accept( self.parent_node_label_y.create_clickable_box(), self.on_label_parent_y_click)
            self.parent_node_label_y.update_pos()


    
    def event_on_click_label_z(self, np, mouse_button=None):
        """"
        Event function for clicking on label on the X-coordinate for drill-down
        for that node.
        """
        tag_title = np.__str__().split('/')[-1]
        clicked_label = self.z_labels[ tag_title ]
        clicked_node = browser.cube.cubeService.get_z().get_node_by_label( clicked_label.title )
        
        print 'DRILLING DOWN ON NODE with id', clicked_node.getNode().tagId
        # create action for the drilldown
        action = ActionAxis(ACTION_DRILL_DOWN, axis1=Z_AXIS, tagId=clicked_node.getNode().tagId)
        actionManager.addAction(action)
        
        browser.cube.cubeService.get_z().drill_down( clicked_node )
        #self.construct_cube()
        #self.draw()
        browser.cube.cubeService.coordinate.constructCube()
        self.load( browser.cube.cubeService.coordinate.cube )
    
        
        # Create drill up label
        if self.parent_node_label_z is not None:
            self.parent_node_label_z.remove()
            self.parent_node_label_z = None
        
        # Create drill up label
        parent_node = browser.cube.cubeService.get_z().get_parent_for_node( clicked_node )
        self.parent_node_label_z = DrillUpLabel( self.np, parent_node, 2 )
        self.parent_node_label_z.create_label()
        base.accept( self.parent_node_label_z.create_clickable_box(), self.on_label_parent_z_click)
        self.parent_node_label_z.update_pos()
        



    def on_label_parent_z_click(self, e, mouse_button=None):
        """
        Event when we click on z parent label. 
        """
        z = browser.cube.cubeService.get_z()
        node = z.get_parent_node_for_current()
        z.drill_up( node )
        
        browser.cube.cubeService.coordinate.constructCube()
        self.load( browser.cube.cubeService.coordinate.cube )
        
        # create action for the drillup
        action = ActionAxis(ACTION_DRILL_UP, axis1=Z_AXIS, tagId=node.getNode().tagId)
        actionManager.addAction(action)
        

        # Create drill up label
        parent = None
        try:
            parent = z.get_parent_for_node( node )
        except:
            pass
        
        if self.parent_node_label_z is not None: 
            self.parent_node_label_z.remove()
            self.parent_node_label_z = None
        
        if parent is not None:
            # Create drill up label.
            self.parent_node_label_z = DrillUpLabel( self.np, parent, 2 )
            self.parent_node_label_z.create_label()
            base.accept( self.parent_node_label_z.create_clickable_box(), self.on_label_parent_z_click)
            self.parent_node_label_z.update_pos()


    
    def OnClusterContextMenuSelect(self, index):
        if index == "add tag to cell":
            image = self.cube.getHoveredImage()
            cell = self.cube.getCell(image.getCellKey())
            browser.dialogs.dialogService.openAddTagToCellDialog(cell)
        
        elif index == "select cell":
            image = self.cube.getHoveredImage()
            cell = self.cube.getCell(image.getCellKey())
            print 'selecting cell', cell.getKey()
            self.selectCell(cell)
        
        else:
            raise Exception('Unknown index from cluster context menu.')

