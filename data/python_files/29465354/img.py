import sys
import random

from pandac.PandaModules import *
from direct.interval.LerpInterval import *
from direct.gui.OnscreenText import OnscreenText

from browser.objectcube import objectCubeService
from browser.objectcube import TagSet
from browser.devices import mouse_handler
from browser.common import Hoverable, font, tagTexture
import browser.cube

import sys
import os
from imageContainer import ImageContainer, active_queues
from pandac.PandaModules import *
import PIL


# Constant for image move speed?
move_speed = 1.5

# Global functions
def convert_cluster_pos_to_screen_pos(pos):
    """
    Calculates the image position on screen in a cube from the simple image cord, with respect to image size and image space
    in the cube.
    """
    x = 0
    y = 0
    z = 0

    if pos[0] is not None:
        x = (pos[0] * (browser.cube.cubeService.get_max_image_space() + browser.cube.cubeService.get_max_image_size()))
    
    if pos[1] is not None:
        y = (browser.cube.cubeService.get_max_image_size()/2) + pos[1] * (browser.cube.cubeService.get_max_image_size() + browser.cube.cubeService.get_max_image_space() )

    if pos[2] is not None:
        z = ( pos[2] * (browser.cube.cubeService.get_max_image_space() + browser.cube.cubeService.get_max_image_size()))

    return (x,y,z) 




########################################################################################
class ImageNodePath:
    """
    What is this?
    """
    def __init__(self, np_name):
        self.np_name = np_name
        self.np = NodePath(self.np_name)
    
    def get_np(self):
        return self.np
    
    def reset_orientation(self):
        self.np.setHpr(0,0,0)
########################################################################################




########################################################################################
class Image( ImageNodePath, Hoverable ):
    def __init__(self, id, location):
        # Invoke parent constructors.
        ImageNodePath.__init__(self, ';' + str(id) + ';' + location)
        Hoverable.__init__(self)
        # Make the image hovarble.
        mouse_handler.makeNPMouseHoverable(self.np)
        
        # Get the object for this image. 
        self.object = objectCubeService.getObjectByName(location)
        
        # Member functions for plugin code. Image movements functions can changed for images.
        self.move_image_function = self.default_move_image_function
        self.remove_image_function = self.test_remove_image_function
        self.add_image_function = self.test_add_image_function
        
        # Member variable for the id, what is the id?
        self.id = id
        
        # Member variable for the image location.
        self.location = location
            
        # Member variables for image position. 
        self.pos = None
        self.old_pos = None
        self.screen_pos = None
        self.old_screen_pos = None

        # Member variable that contains this image data.
        self.image_data = None
        self.parent_np = None
        self.cluster_index = None
          
        # Member variable for the image card (contains image texture.)
        self.card = None
        
        self.random_r = None
        self.visable = False
        # Member variable for data size.
        self.dataSize = IMAGE_SIZE_SMALL

        
    

    def setDataSize(self, size):
        # If the size is not on correct range, then we'll throw
        # an exception.
        if size not in range(3):
            raise Exception('Unknown data-size')
        
        # Setting the data size.
        fileName = self.location.split('/')[-1]
        folder = self.location[0:self.location.rfind('/')]
        self.dataSize = size
        self.image_data = image_service.get_pnmimage( folder, fileName, self.dataSize )
        print 'DATA SIZE CHANGED'   
    
    
    def getTags(self):
        """
        Returns all the tags that the object that this image reprensets contains.
        """
        for tag in self.object.getTags():
            yield tag 
            
            
    def addTag(self, tag):
        """
        Adds tag to the ObjectCube object for this given image.
        """
        if not self.object.hasTag(tag.id):
            objtag = ObjectTag( tag )
            self.object.addTag(objtag)
    

    
    def shake(self):
        if self.cluster_index is not 0:
            self.np.setR( self.random_r )
   

    def remove_shake(self):
        self.np.setR( 0 )
     
    
    def getClickMessageLeft(self):
        return self.messageLeftClick
    
    def getClickMessageRight(self):
        return self.messageRightClick
    
    
    def get_mouseover_message(self):
        if self.np is not None: return 'zoomin_' + str(self.np)
        else: return None
    
    
    def get_mouseleave_message(self):
        if self.np is not None: return 'zoomout_' + str(self.np)
        else: return None    
    
    
    
    def default_move_image_function(self, np, location, old_pos, new_pos, cluster_index):
        new_pos = convert_cluster_pos_to_screen_pos( new_pos )
        
        # add the stackspace. 
        new_pos = ( new_pos[0], new_pos[1] + cluster_index * browser.cube.cubeService.get_cluster_stack_space(), new_pos[2] )
        LerpPosInterval(self.np, move_speed, new_pos ).start()


    def test_remove_image_function(self, np, pos):
        pos_lerp = LerpPosInterval(self.np, move_speed, ((random.sample( [-1,1],1 )[0]) * 100,50,0) ).start()
        i = LerpFunc(self.myFunction, fromData = 0, toData = 5, duration = 3, blendType = 'noBlend', extraArgs = [pos_lerp], name = None)
        i.start()

    #bad function, need to fix.
    def myFunction(self, t, lerp): 
        if t >= 5:
            self.np.remove()
            self.visable = False

    
    
    def test_add_image_function(self,np, pos):
        new_pos = convert_cluster_pos_to_screen_pos( pos )
        
        # add the stack space.
        new_pos = ( new_pos[0], new_pos[1] + self.cluster_index * browser.cube.cubeService.get_cluster_stack_space(), new_pos[2] )
        
        # this should not be random... 
        np.setPos( (-60, 0, 0))
        LerpPosInterval(np, move_speed, new_pos ).start()
    
    
    
    def get_location(self):
        return self.location
    
    
    def get_id(self):
        return self.id
    
    
    
    def getCellKey(self):
        # Create the cell key.
        pos_list = []
        for n in self.pos: 
            if n is not None: pos_list.append( str(n) )
        key = ':'.join( pos_list )
        return key
    
    
    
    def set_pos(self, pos):
        """
        Set the position of the image, this position is the cube position, not the
        screen position.
        """
        if self.pos is not None:
            self.old_pos = self.pos
        self.pos = pos
        


    def update_pos(self, pos):
        if self.move_image_function is None:
            self.position()
        else:
            self.move_image_function(self.np, self.location, self.get_old_pos(), self.get_pos(), self.get_cluster_index())

    
    def clusterIndexUpdate(self, animate=False):
        self.position()
    
    
    def get_pos(self):
        return self.pos
        
    
    def get_old_pos(self):
        return self.old_pos


    def remove(self):
        self.np.hide()
        self.np.setX(-3000)
        self.visable = False


    def get_screen_pos(self):
        return self.screen_pos


    def get_old_screen_pos(self):
        return self.old_screen_pos
    
    
    
        
    def reload(self):
        #print 'reload image!!!!!!!!!!!!!!'
        self.card.remove()
        
        # Create a new texture object.
        self.myTexture=Texture()
        self.myTexture.load( self.image_data )
        
        # Create the card for the image.
        cm = CardMaker('card-' + self.pos.__str__() + '=' + self.location)
        
        self.card = self.np.attachNewNode(cm.generate())
        self.card.setTwoSided(True)
        self.card.setTexture(self.myTexture) 
    
    
    
    
    def load_data(self):
        """
        Loads the image data from the PNMImage service.
        """
        fileName = self.location.split('/')[-1]
        folder = self.location[0:self.location.rfind('/')]
            
        # Load the image data.
        if self.image_data is None:
            self.image_data = image_service.get_pnmimage( folder, fileName, IMAGE_SIZE_SMALL )
            #print 'got image data from image service', self.image_data

        else:
            raise Exception('IMAGE DATA IS NONE')
        
        
        # Create a new texture object.
        self.myTexture=Texture()
        #print 'IMAGE DATA IS:' 
        #print self.image_data
        self.myTexture.load(self.image_data)
        
        # Create the card for the image.
        cm = CardMaker('card-' + self.pos.__str__() + '=' + self.location)
        
        self.card = self.np.attachNewNode(cm.generate())
        self.card.setTwoSided(True)
        
        # Make the image np clickable.
        self.messageRightClick = mouse_handler.makeNPPickableRight(self.np)
        self.messageLeftClick = mouse_handler.makeNPPickableLeft(self.np)

       

        
        # Set the picture as the texture for the card.
        self.card.setTexture(self.myTexture)        
        
        
        # Create the tagset card
        cm = CardMaker('card-' + self.pos.__str__() + '=' + self.location + "-tags")
        
        self.tags_card = self.np.attachNewNode(cm.generate())
        self.tags_card.setTexture(tagTexture)
        self.tags_card.setTransparency(TransparencyAttrib.MAlpha)
 
 
        # Create image tags labels to put under the image when drawed.
        obj = objectCubeService.getObjectByName(self.location)
        
        tags = ''   
        for tag in obj.getTags():
            tagset = objectCubeService.get_tagset_by_id( tag.getTag().tagSetId )
            
            # we only show acces types tags with user (not showing system specific tags.)
            if tagset.accessId == TagSet.ACCESS_TYPE.USER: 
                tags += tag.getTag().valueAsString() + ", " 
        
          
        # Remove the trailing ','.
        tags = tags[0:len(tags)-2]
        
        # Create text object. (We must load this elsewhere for chaging image size.)
        self.textObject = OnscreenText(align=TextNode.ALeft,fg =(1,1,1,1), text = tags, scale=(0.03, 0.03), wordwrap=40, font=font, mayChange=True)
        self.t_np = self.np.attachNewNode('t_node')
        self.textObject.reparentTo( self.t_np )
        self.textObject.setTwoSided(True)
                
        self.t_np.setY(-0.03)
        self.t_np.setX(0.02)
        self.t_np.setZ(-0.03)
          
        self.scale_image()
        self.hide_tags()


        
    
    
    
    def show(self):
        if self.image_data is None:
            self.load_data()
        
        self.np.show()
        self.visable = True
        
    
    
    
    
    def isVisible(self):
        return self.visable
    
    
    
    
    
    
    
    
    def position(self, animate=False):

        if animate:
            if self.old_pos is not None:
                #print 'WOW!!! WE SHOULD RELOCATED IMAGE!!!'
                if self.move_image_function is None:
                    raise Exception('Move image function is not set.')
                else:
                    self.move_image_function(self.np, self.location, self.get_old_pos(), self.get_pos(), self.cluster_index)
            else:
                if not self.add_image_function is None:
                    self.add_image_function(self.np, self.get_pos())
                else:
                    raise Exception('Add function not defined')

        else:
            if self.screen_pos is not None:
                self.old_screen_pos = self.screen_pos
        
        

        
            screen_pos = convert_cluster_pos_to_screen_pos( self.get_pos() )
        
            if screen_pos[0] is not None:
                self.np.setX( screen_pos[0] )
        
            if screen_pos[1] is not None:
                self.np.setY( screen_pos[1] )
        
            if screen_pos[2] is not None:
                self.np.setZ( screen_pos[2] )
        
            # add the stack space
            self.np.setY( self.np.getY() + (self.cluster_index * browser.cube.cubeService.get_cluster_stack_space()) )

            self.screen_pos = self.np.getPos()



    
    
    def scale_image(self, scale_factor=None, scale_tags=False):
        xSize = self.image_data.getReadXSize()
        ySize = self.image_data.getReadYSize()    
        
        if scale_factor is None:
            max_image_size = browser.cube.cubeService.get_max_image_size()
        
        else:
            max_image_size = scale_factor
        
        max_image_space = browser.cube.cubeService.get_max_image_space()
        
        # calculate the scale value for the image.
        ratio = float(xSize) / float(ySize)
        
        if ratio > 1:
            self.width, self.height = (max_image_size, max_image_size / ratio)
        else:
            self.width, self.height = (max_image_size * ratio, max_image_size)
    
        self.card.setScale(Vec3(self.width, 1, self.height))
        
        # set the scale of the tagset card with respect to the width of the image card.
        if scale_tags:
            self.tags_card.setScale(self.width, 1, 0.1)
            self.tags_card.setZ(-0.1)
            self.textObject.setWordwrap(self.width*32)
        
        




    def show_tags(self):
        self.tags_card.show()
        self.t_np.show()        


    def hide_tags(self):
        self.tags_card.hide()
        self.t_np.hide()
########################################################################################








#############################################################
# CONSTANTS                                                 #
#############################################################
IMAGE_SIZE_SMALL = 0
IMAGE_SIZE_MEDIUM = 1
IMAGE_SIZE_LARGE = 2





#############################################################
class PNMIImageService:
    """
    Service for fetching images to disk, aswell caching them
    in memory so they can speed things up.
    """
    def __init__(self):
        # Dictionary that will contain locations and PNMImage
        # objects. Used to cache images in memeory and for
        # providing fast retreival.
        self.hash = {}
        
        self.mid_size_data = {}
        self.small_size_data = {}

        self.max_size_small = 1
        self.max_size_mid = 400
        self.max_size_large = 10
        
        # Create instance of the ImageContainer
        self.imageContainer = ImageContainer()
        
        # Start the ImageContainer thread.
        self.imageContainer.setDaemon(True)
        self.imageContainer.start()
        
        # dead never used.
        #self.imageContainer.pause = False
        #self.imageContainer.join()

        
    
    def notifyImageLoad(self, objects):
        """
        print 'XX NOTIFYING IMAGES'
        for object in objects:
            active_queues[0].put(object.name)
        """
        pass

    
    def contains(self, location):
        return location in self.mid_size_data
        
    
    
    
    
    def get_pnmimage(self, folder, fileName, size):
        """
        Get PNM image.
        """
        #print 'requesting image', fileName, 'with size', size
        
        
        if size == 0:
            location = os.path.join( folder, 'T_' + fileName )
            if location in self.small_size_data:
                return self.small_size_data[location]
            else:
                small_size = PNMImage()
                small_size.read(Filename(location))
                self.small_size_data[location] = small_size
                return small_size


        else:
            location = os.path.join( folder, fileName )
        
            if location in self.mid_size_data:
                return self.mid_size_data[location]
            else:
                mid_size = PNMImage()
                mid_size.read(Filename(location))
                self.mid_size_data[location] = mid_size
                return mid_size
        
        
        # todo: go through this code and fix.
        #if size == IMAGE_SIZE_SMALL:
        #    location = os.path.join(folder,fileName)
        #    thumnailLocation = os.path.join(folder,'T_' + fileName)
        #    
        #    if self.contains(thumnailLocation):
        #        return self.mid_size_data[thumnailLocation]
        #        
        #    else:
        #        #im = PIL.Image.open(thumnailLocation)
        #        #xSize = im.size[0]
        #        #ySize = im.size[1]
        #        #image_ratio = (xSize / (ySize + 0.0))

        #        # Create medium size image and store it in hash.
        #        #if image_ratio > 1:
        #        #    width, height = (self.max_size_mid, self.max_size_mid / image_ratio)
        #        #else:
        #        #    width, height = (self.max_size_mid * image_ratio, self.max_size_mid)
        #        
        #        mid_size = PNMImage()
        #        #mid_size.setReadSize(width, height)
        #        
        #        mid_size.read(Filename(thumnailLocation))
        #        
        #        
        #        self.mid_size_data[location] = mid_size
        #        
        #        # Create small size
        #        #if image_ratio > 1:
        #        #    width, height = (self.max_size_small, self.max_size_small / image_ratio)
        #        #else:
        #        #    width, height = (self.max_size_small * image_ratio, self.max_size_small)
        #        
        #        #small_size = PNMImage()
        #        #small_size.setReadSize(width, height)
        #        #small_size.read(Filename(location))
        #        #self.samll_size_data[location] = small_size            
        #        
        #        return mid_size
        #else:
        #    location = os.path.join(folder,fileName)
        #    imageName = os.path.join(folder,fileName)
        #    if self.imageContainer.contains(imageName):
        #        return self.imageContainer.getImage(imageName)
        #    else:               
        #        im = PIL.Image.open(imageName)
        #        xSize = im.size[0]
        #        ySize = im.size[1]
        #        image_ratio = (xSize / (ySize + 0.0))
        #        self.max_size_mid = 500
        #        if image_ratio > 1:
        #            width, height = (self.max_size_mid, self.max_size_mid / image_ratio)
        #        else:
        #            width, height = (self.max_size_mid * image_ratio, self.max_size_mid)

        #        image = PNMImage()
        #        image.setReadSize(int(width), int(height))
        #        image.read(Filename(imageName))
        #        return image
            
                
            
            


# create singleton instance.
image_service = PNMIImageService()
#############################################################













