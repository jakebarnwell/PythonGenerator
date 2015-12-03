import sys
import os

sys.path.append( '../ObjectCube' )
from ObjectCubePython import *
import ObjectCubePython
from ObjectCubePython import ObjectTag
import random
from browser.configuration import browser_config
from PIL import Image

# Variable for setting this module to Debug mode.
DEBUG = True


# Module constants
CANNED = '1'
SQLITE = '2'
MONETDB = '3'


####################################################################
#class ObjectCubeException(exception):
#    """
#    Custom Exception for this package. 
#    """
#    def __init__(self, value):
#        self.parameter = value
#    
#    def __str__(self):
#        return repr(self.parameter)
####################################################################



####################################################################
class ObjectCube:
    """
    This class serves as a API layer on top of the
    ObjectCube framework.
    """
    def __init__(self, dataAccessType, dbName = None, language=None):
        """
        Constructor for the ServiceLayer class.
        """
        # Get the data access type from configuraion.
        _dataAccessType = str(browser_config.getValue('dataAccessType'))
        
        # Set the data access type from configuration.
        Parameters.getParameters().add( "dataAccessType", _dataAccessType )

        
        # Create hub for the object cube framework.
        #Parameters.getParameters().add( "outputDebugInfo", "1" )
        #browser_config.getValue('debug')
        #print 'KEYS', browser_config.getConfigKeys()
        # Set the data access type from configuration.
        
        
        
        Parameters.getParameters().add( "MonetDB_database", "ObjectCube" )

        if dbName is not None:
            self.hub.destroy()
            Parameters.getParameters().update( "SQLite", dbName)

        else:
            if 'sqlite_database_file' in browser_config.getConfigKeys():
                dbFile = browser_config.getValue('sqlite_database_file')
                Parameters.getParameters().remove('SQLite')
                Parameters.getParameters().add( "SQLite", dbFile)
        
        if language is not None:
            Hub.setLanguageId(language)
        
        # Create hub from ObjectCube.
        self.hub = Hub.getHub()
        
        # Store the tagset types in memory as a list of tuples
        # where each tuple contains an id and string.
        self.tagset_types = []

        for x in TagSet.TYPE.values:
            self.tagset_types.append((x,TagSet.typeAsStringStatic(x)))

        # Collections of filters that have been created.
        #self.filters = []
        
        # TODO: Make this configurable.
        #Parameters.getParameters().add( "DimensionFilterV2", "0")
        #Parameters.getParameters().add( "outputDebugInfo", "0" )
        #Parameters.getParameters().add( "outputStateHierarchyObjects", "0" )
        #Parameters.getParameters().add( "SQLite", "/home/hs01/temp/objectcube/trunk/PhotoCube/Database/x" )   
        self.state = State.getState()
        

    def reset(self, dbname):
        self.__init__(dbName = dbname)
        

    def addObject(self, folder, filename):
        imgFullPath = os.path.join(folder, filename)
        # Create Object for this new image.
        cubeObject = Object( imgFullPath )
        try:
            cubeObject.create()
            if DEBUG:
                print '-- added image ', imgFullPath
            
            # Create a thumbnail for the image that we are adding.
            tn = Image.open(imgFullPath)
            tn.thumbnail((200, 200), Image.ANTIALIAS)
            tn_location = os.path.join(folder, 'T_' + filename)
            tn.save(tn_location, "JPEG")
            if DEBUG:
                print '-- thumbnail created ', tn_location

        except Exception as inst:
            print 'error when create image', inst
            pass
    
    
    def getObjectByName(self, name):
        """ DocString for getObjectByName"""
        return Object.fetch(name)
    
    
    def getObjectById(self, object_id):
        """ DocString for getObjectById"""
        o = Object.fetch(object_id)
        return o
    
    
    def get_state(self):
        return self.state
    
    def update_state(self):
        self.state = self.state.getState()
    
    
    def get_filters(self):
        print 'getting filters'
        l = []
        for filter in State.getFilters():
            l.append(filter)
        return l

    
    def get_filter_by_id(self, id):
        """
        Function for fetching filter by id
        """
        for filter in self.get_filters():
            if filter.id == id:
                return filter
        return None

    
    def remove_filter(self, filter):
        print 'removeing filter', filter
        State.removeFilter(filter)

    
    
    def getAllTagsets(self, onlyUserDefined=False):
        returnList = []
        if onlyUserDefined:
            
            for tagset in self.hub.getTagSets():
                if tagset.accessId  == TagSet.ACCESS_TYPE.USER:
                    returnList.append(tagset)
            
            
            
            returnList.sort(lambda x, y: cmp(x.name.lower(),y.name.lower()))
            

            
            
            return returnList 
        
        else: 
            tagsets =  self.hub.getTagSets()
            # Create list from ObjectCube vec list.
            for tagset in tagsets:
                returnList.append( tagset )
                returnList.sort(lambda x, y: cmp(x.name.lower(),y.name.lower()))
            return returnList


    
    def get_tagset_by_id(self, id):
        for tagset in self.hub.getTagSets():
            if tagset.id == id: return tagset
        return None
    
    
    
    def getTagsetByName(self, tagset_name):
        """
        Get tag by name (case ins). If there is not tagset
        with a given search name, then the function returns
        none value.
        """
        for tagset in self.getAllTagsets():
            if tagset.name.lower() == tagset_name.lower():
                return tagset
        return None

    
    
    def get_all_tagset_types(self):
        return self.tagset_types

    
    
    def get_tagset_type_id_by_name(self, name):
        for n in self.tagset_types: 
            if n[1] == name: return n[0]
        return -1

    

    def get_all_objects(self):
        return_list = []
        State.removeAllFilters() 
        
        state = State.getState()
        objects = state.getObjects()
        
        for n in range(len(objects)):
            return_list.append(objects[n])

        return return_list

    

    def get_object_tags(self, object):
        """
        Function that returns list of quadtripplet on the form:
        (tagset_id, tagset_name, tag, tagset_id) that have been tagged
        to object with object_id.
        """
        #o = Object.fetch(object_id)
        returnList = []
        
        for object_tag in object.getTags():
            tag = object_tag.getTag()
            tagset_id = tag.tagSetId
            tagset = self.get_tagset_by_id(tagset_id) 
            returnList.append([tagset.name, tag])
        return returnList

    
    
    def remove_tag_from_object(self, object_id, tag_id, tagset_id):
        """
        Removes tag from object.
        """
        tagset = self.hub.getTagSet(tagset_id)
        tag = tagset.getTag(tag_id)
        o = Object.fetch(object_id)
        o.removeTag(tag)


    
    def add_tag_to_object(self, tagset_id, tag_id, object_id):
        tagset = self.hub.getTagSet(tagset_id)
        tag = tagset.getTag(tag_id)
        o = Object.fetch(object_id)
        o_tag = ObjectTag(tag)
        o.addTag(o_tag)
   

    
    def get_object_location(self, object_id):
        o = Object.fetch(object_id)
        return o.name

    
    
    def get_all_dimensions(self):
        """
        Retuns all dimensions that have been stored to the db.
        """
        return_list = []
        for dim in self.hub.getPersistentDimensions():
            return_list.append(dim)
        return return_list
        
    
    def get_tag(self, tagset_id, tag_id):
        tagset = self.hub.getTagSet(tagset_id)
        return tagset.getTag(tag_id)
                    
####################################################################


# Create singleton instance of the ObjectCube.
objectCubeService = ObjectCube(MONETDB)
