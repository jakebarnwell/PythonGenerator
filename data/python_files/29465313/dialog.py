import sys
sys.path.append( '../ObjectCube' )
from ObjectCubePython import *

from direct.gui.OnscreenImage import OnscreenImage
from pandac.PandaModules import TransparencyAttrib
from direct.gui.DirectGui import *

import browser.menu
from browser.actions import actionManager, ActionFilter, ACTION_ADD, ACTION_TAGFILTER
from browser.actions.action import ACTION_TYPE_NUMERICAL_RANGEFILTER

import abstract
from pandac.PandaModules import TextNode
from browser.common import font
from browser.common.messages import CUBE_MENU_RELOAD_FILTERS
from browser.common.messages import CUBE_MENU_RELOAD_DIMENSIONS


# Font
#font = loader.loadFont('Arial.ttf')


class AddTagFilterDialog(abstract.AbstractDialog):
    
    def __init__(self, tagset=None):
        # create np for the dialog.
        np = aspect2d.attachNewNode('AddTagFilterDialog')
        
        # Call the parent constructor.
        abstract.AbstractDialog.__init__(self, np)
        
        # Member variable for last input filter text.
        self.filterText = ''


        # Events acceptions
        base.accept('tagListFilterItemMenuIndexSelect', self.contextHandler)


    def inputTaskHandler(self, task):
        txtFilter = self.txtTagFilter.get() 
        if txtFilter != self.filterText:
            self.filterText = txtFilter
            self.loadTagList(text_filter=txtFilter)
        return task.cont


    def draw(self):
        self.__create_components()
        self.create_ok_cancel_buttons()
        
        # set the position of the ok/cancel buttons
        self.set_ok_button_pos((0.22, 1,-0.43))
        self.set_cancel_button_pos((0.36, 1, -0.43))

        # Start the input task.
        self.inputTask = taskMgr.add(self.inputTaskHandler, 'TagInputHandlerTask')




    def loadTagList(self, text_filter = None):
        # Remove everything from the list.
        del_items = []
        for item in self.tagList['items']: del_items.append(item) 
        
        for item in del_items:
            self.tagList.removeItem(item)     
        
        # Get all the tags
        tagsets = browser.objectcube.objectCubeService.getAllTagsets(True) 
        for tagset in tagsets:
            for tag in tagset.getTags():
                value = tag.valueAsString()
                
                if text_filter is not None:
                    if not value.lower().startswith(text_filter.lower()):continue
                
                tagButton = DirectButton(rolloverSound=None, clickSound=None, text = (value[:40], '+'+value[:40], '+' + value[:40], value[:40]),
                  text_font=font,
                  text_scale=(0.030), borderWidth = (0.01, 0.01), relief=0, command=self.onItemclick, extraArgs=[value, tagset.id, tag.id])
                self.tagList.addItem(tagButton)

        # Fix the scrollbar
        if len(self.tagList['items']) == 0:
            self.tagListBar['range'] = (0,1)
        else:
            self.tagListBar['range'] = (0,len(self.tagList['items']))

        self.tagListBar['value'] = 1
        self.tagListBar['pageSize'] = 13 
        self.tagListBar['scrollSize'] = 1

    
    
    def onTagNameEnter(self, text):
        self.loadTagList(text)
        self.txtTagsetName.setFocus()


    def __create_components(self):
        # Change the size of the background.
        self.bg.setScale(0.50, 1 ,0.50) 
        
        # Create label for the window.
        OnscreenText(text = 'Add tag filter',
        fg=(0,0,0,1),
        parent=self.np,
        frame=(0.3,0.3,0.3,1),
        bg=(0.7,0.7,0.7,1),
        scale=0.035,
        pos=(0, 0.40)
        )


        # Create label and textbox for the tagset name.
        txt = OnscreenText(text = 'Filter taglist', fg=(1,1,1,1), parent=self.np, scale=0.030, 
        pos=(-0.32, 0.32))
        
        self.txtTagFilter = DirectEntry(text = "",
        initialText="", 
        numLines=1, 
        focus=1, 
        width=27,
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        pos=(-0.40, 1, 0.245),
        scale=(0.03),
        )
            
        self.tagListNumVisableItems = 13 
        itemHeight = 0.04
        pos = (-1, 3, 0)
        
        
        # Create taglist.
        self.tagList = DirectScrolledList(
            incButton_scale=(0.000001,0.00001,0.0000001),
            decButton_scale=(0.000001,0.00001,0.0000001),
            pos = pos,
            items = [],
            numItemsVisible = self.tagListNumVisableItems,
            forceHeight = itemHeight,
            itemFrame_frameSize = (-0.35, 0.45, -0.50, 0.05),
            itemFrame_pos = (0.75, 1, 0.15),
            parent=self.np,
            )
        
        self.tagList.setX(-0.80)


        # Create scrollbar for the taglist. 
        self.tagListBar = DirectScrollBar(command=self.onTagListValueChange, parent=self.tagList, range=(0,100), value=50, pageSize=3, orientation= DGG.VERTICAL)

        self.tagListBar['incButton_clickSound'] = None
        self.tagListBar['incButton_rolloverSound'] = None
        self.tagListBar['decButton_clickSound'] = None
        self.tagListBar['decButton_rolloverSound'] = None
        self.tagListBar['thumb_clickSound'] = None
        self.tagListBar['thumb_rolloverSound'] = None
        self.tagListBar['incButton_relief'] = None
        self.tagListBar['decButton_relief'] = None
        self.tagListBar['decButton_text'] = '-'
        self.tagListBar['decButton_text_scale']=(0.07,0.05)
        self.tagListBar['incButton_text'] = '+'
        self.tagListBar['incButton_text_scale']=(0.07,0.05)
        self.tagListBar['incButton_text_pos'] = (-0.005,-0.02)
        self.tagListBar['decButton_text_pos'] = (-0.005,-0.02)
        self.tagListBar['thumb_frameColor'] = (0, 0, 0, 0.2)

        
        
        self.tagListBar.setScale(0.45, 2, 0.55)
        self.tagListBar.setX(1.20)
        self.tagListBar.setY(2)
        self.tagListBar.setZ(-0.075)

        self.loadTagList()
   

    def onTagListValueChange(self):
        index_value = int(self.tagListBar['value'])
        self.tagList.scrollTo(index_value)
    


    
    
    def contextHandler(self, index):
        
        if index == 'add tag filter':
            tagset_id = self.selected_item_tagset_id
            tagset = browser.objectcube.objectCubeService.get_tagset_by_id(tagset_id)
            tag = tagset.getTag(self.selected_item_tag_id)
            
            tagFilter = TagFilter(tag, tagset.id)
            browser.objectcube.objectCubeService.get_state().addFilter( tagFilter )
            browser.objectcube.objectCubeService.update_state()
    
            # add action
            # ADD THIS AGAIN.
            action = ActionFilter(ACTION_TAGFILTER, ACTION_ADD, tagset.id, tag.id)
            actionManager.addAction( action )

            messenger.send(CUBE_MENU_RELOAD_FILTERS)
            messenger.send('update_added_filter') 
            return 
            #####
        
            
           


    def onItemclick(self, item, tagset_id, tag_id):
        self.selected_item = item
        self.selected_item_tagset_id = tagset_id
        self.selected_item_tag_id = tag_id
        browser.menu.context_menu_handler.showTagFilterItemContectMenu()



    
    def click_ok_button(self):
        taskMgr.remove(self.inputTask)
        self.np.remove()
        base.ignore('tagListFilterItemMenuIndexSelect')
        messenger.send('dialog_closing')
        return 


    def click_cancel_button(self):
        taskMgr.remove(self.inputTask)
        self.np.remove()
        base.ignore('tagListFilterItemMenuIndexSelect')
        messenger.send('dialog_closing')
        return 





####################################################
class AddNewTagsetDialog(abstract.AbstractDialog):
    
    def __init__(self, tagset=None):
        # create np for the dialog.
        np = aspect2d.attachNewNode('AddNewTagsetDialog')
        
        # Call the parent constructor.
        abstract.AbstractDialog.__init__(self, np)

        # Accept events.
        base.accept('tagListItemMenuIndexSelect', self.contextHandler)
        
        # Store the tagset as a member variable.
        self.tagset = tagset


    def draw(self):
        self.__create_components()
        self.create_ok_cancel_buttons()
        
        # set the position of the ok/cancel buttons
        if self.tagset is None:
            self.set_ok_button_pos((0.12, 1,-0.43))
            self.set_cancel_button_pos((0.26, 1, -0.43))
        else:
            self.set_ok_button_pos((0.12, 1,-0.26))
            self.set_cancel_button_pos((0.26, 1, -0.26))



    def __create_components(self):
        # Change the size of the background.
        if self.tagset is None:
            self.bg.setScale(0.50, 0 ,0.50)
        else:
            self.bg.setScale(0.50, 0 ,0.30) 
        
        
        
        # Create label for the window.
        if self.tagset is None:
            self.text = OnscreenText(text = 'Create new tagset',
            fg=(0,0,0,1),
            parent=self.np,
            frame=(0.3,0.3,0.3,1),
            bg=(0.7,0.7,0.7,1),
            scale=0.035,
            pos=(0, 0.40)
            )
       
        else:
            self.text = OnscreenText(text = 'Edit tagset ' + self.tagset.name,
            fg=(0,0,0,1),
            parent=self.np,
            frame=(0.3,0.3,0.3,1),
            bg=(0.7,0.7,0.7,1),
            scale=0.035,
            pos=(0, 0.23)
            )
       



        # Create label and textbox for the tagset name.
        if self.tagset is None:
            txt = OnscreenText(text = 'Tagset name', fg=(1,1,1,1), parent=self.np, scale=0.030, 
            pos=(-0.30, 0.32))
            
            self.txtTagsetName = DirectEntry(text = "",
            initialText="", 
            numLines=1, 
            focus=1, 
            width=10,
            clickSound = None,
            rolloverSound = None,
            parent=self.np,
            pos=(-0.38, 1, 0.245),
            scale=(0.03)
            )
            
            # Create label for upper bound.
            txt = OnscreenText(text = 'Tagset type', fg=(1,1,1,1), parent=self.np, scale=0.030, 
            pos=(-0.30, 0.15))
           
            
            # Create tagset type dropdown. 
            values = ['Alphanumerical tagset', 'Numerical tagset']
            self.tagsetType = values[0]
            self.tags_menu = DirectOptionMenu(text="options", 
                scale=0.045,
                text_scale=0.6,
                items=values,
                initialitem=0,
                highlightColor=(0.65,0.65,0.65,1),
                parent=self.np,
                rolloverSound=None,
                pos=(-0.38, 2, 0.1),
                command=self.onDropDownTagsetTypeChange,
            )
        
        # Create textbox for lower bound.
        if self.tagset is None:
            pos = (-0.38, 1, -0.01)
        else:
            pos = (-0.38, 1, 0.15)
        
        self.tagValue = DirectEntry(text = "",
        scale=0.03, 
        initialText="", 
        numLines=1, 
        focus=0, 
        width=10,
        pos=pos,
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )

        
        if self.tagset is None:
            pos = (0.14,0,-0.005)
        else:
            pos = (0.14,0, 0.15)
        
        # create button to clear the taglist.
        self.btn_clear = DirectButton(text_fg=(1,1,1,1), 
            frameColor=(0.5, 0.5, 0.5, 0.8), 
            #borderWidth=(0.0,0.0), 
            relief=DGG.RAISED, 
            text=('clear list', 'clear list', 'clear list', 'clear list'),
            pressEffect=1, 
            scale=0.030, 
            frameSize=(-2, 2, -0.5, 1.0),  
            parent=self.np,
            rolloverSound=self.mouseover_sound,
            clickSound=self.mouseclick_sound,
            command=self.onBtnClearTaglist,
            pos=pos,
            )
        

        if self.tagset is None:
            pos = (0, 0,-0.005)
        else:
            pos = (0,0, 0.15)

        self.btn_add = DirectButton(text_fg=(1,1,1,1), 
            frameColor=(0.5, 0.5, 0.5, 0.8), 
            #borderWidth=(0.0,0.0), 
            relief=DGG.RAISED, 
            text=('add tag', 'add tag', 'add tag', 'add tag'),
            pressEffect=1, 
            scale=0.030, 
            frameSize=(-2, 2, -0.5, 1.0),  
            parent=self.np,
            rolloverSound=self.mouseover_sound,
            clickSound=self.mouseclick_sound,
            command=self.onBtnAddTag,
            pos=pos,
            )
        
        
        self.tagListNumVisableItems = 5 
        itemHeight = 0.06
        items = []

        if self.tagset is None:
            pos = (-1, 3, 0)
        else:
            pos = (-1, 3, 0.17)
        
        if self.tagset is not None:
            for tag in self.tagset.getTags():
                value = tag.valueAsString()
                l1 = DirectButton(text = (value, value, value, value),
                  text_scale=0.035, borderWidth = (0.01, 0.01), relief=1, command=self.onItemclick, extraArgs=[value])
                items.append(l1) 

        self.tagList = DirectScrolledList(
            incButton_scale=0.000001,
            decButton_scale=0.000001,
            pos = pos,
            items = items,
            numItemsVisible = self.tagListNumVisableItems,
            forceHeight = itemHeight,
            itemFrame_frameSize = (-0.35, 0.35, -0.28, 0.05),
            itemFrame_pos = (0.77, 0, -0.1),
            parent=self.np,
            )
        
        self.tagList.setX(-0.80)



        # Create scrollbar for the taglist. 
        self.tagListBar = DirectScrollBar(command=self.onTagListValueChange, parent=self.tagList, range=(0,100), value=50, pageSize=3, orientation= DGG.VERTICAL)
        if len(self.tagList['items']) == 0:
            self.tagListBar['range'] = (0,1)
            self.tagListBar.hide()
        else:
            self.tagListBar['range'] = (0,len(self.tagList['items']))
        
        self.tagListBar['value'] = 1
        self.tagListBar['pageSize'] = 5
        self.tagListBar['scrollSize'] = 1
        self.tagListBar.setScale(0.33, 2, 0.33)
        self.tagListBar.setX(1.12)
        self.tagListBar.setY(3)
        self.tagListBar.setZ(-0.215)
        

    
    def onDropDownTagsetTypeChange(self, value):
        self.tagsetType = value
    

    def onTagListValueChange(self):
        index_value = int(self.tagListBar['value'])
        self.tagList.scrollTo(index_value)
    

    def onBtnClearTaglist(self):
        del_items = []
        for item in self.tagList['items']: del_items.append(item) 
        
        for item in del_items:
            self.tagList.removeItem(item)     
        
        self.tagListBar['value'] = 0        
        self.tagListBar.hide()

        if self.tagset is not None:
            for tag in self.tagset.getTags():
                self.tagset.deleteTag(tag)



    def onBtnAddTag(self):
        value = self.tagValue.get()
        if len(value) == 0: return
        
        l1 = DirectButton(text = (value, value, value, value),
                  text_scale=0.035, borderWidth = (0.01, 0.01), relief=1, command=self.onItemclick, extraArgs=[value])
        
        self.tagList.addItem(l1)        
        self.tagValue.enterText('')
        
        # if we are editing then we must add new tag to the tagset.
        if self.tagset is not None:
            print self.tagset.typeAsString()
            
            if self.tagset.typeAsString() == 'Alphanumerical tag-set':
                tag = AlphanumericalTag(value) 
                self.tagset.addTag(tag)
            
            elif self.tagset.typeAsString() == 'Numerical tag-set':
                tag = NumericalTag(int(value)) 
                self.tagset.addTag(tag)
            else:
                raise Exception('Not supported')
        
        
        # update the taglist
        # if there are many items in the list, we show the scrollbar.
        if len(self.tagList['items']) > self.tagListNumVisableItems:
            self.tagListBar.show()
            
        if not self.tagListBar.isHidden():
            self.tagListBar['range'] = (0,len(self.tagList['items']))


    
   
    def contextHandler(self, index):
        if index == 'remove tag':
            del_item = None
            for item in self.tagList['items']:
                if item['text'][0] == self.selected_item:
                    del_item = item
                    break

            if del_item is None:
                raise Exception('Delete item was not found!')
            
            else:
                self.tagList.removeItem(del_item)
    
            # if we are editing we must remove the tag from the tagset!
            if self.tagset is not None:
                del_tag = None
                for tag in self.tagset.getTags():
                    if tag.valueAsString() == del_item['text'][0]:
                        del_tag = tag
                        break
                self.tagset.deleteTag(tag)      
            
            
               
    
    def onItemclick(self, item):
        self.selected_item = item
        browser.menu.context_menu_handler.showTagsetItemContectMenu()


    def click_ok_button(self):
        if self.tagset is not None:
            self.np.remove()
            messenger.send('dialog_closing')
            return 

        try:
            print self.tagsetType
            tagsetName = self.txtTagsetName.get()
            
            if self.tagsetType == 'Alphanumerical tagset':
                tagset = AlphanumericalTagSet(tagsetName) 
                tagset.create()
                for item in self.tagList['items']:
                    value = item['text'][0]
                    tag = AlphanumericalTag(value)
                    tagset.addTag(tag)
            
            elif self.tagsetType == 'Numerical tagset':
                tagset = NumericalTagSet(tagsetName) 
                tagset.create()
                for item in self.tagList['items']:
                    value = int(item['text'][0])
                    tag = NumericalTag(value)
                    tagset.addTag(tag)
            else:
                raise Exception('Unknown tagset type ' + tagsetType)
            
            self.np.remove()
            messenger.send(CUBE_MENU_RELOAD_DIMENSIONS)
            browser.objectcube.objectCubeService.update_state()
            messenger.send('dialog_closing')
            base.ignore('tagListItemMenuIndexSelect')


        
        except Exception as inst:
            # Create error message.
            dlg = ErrorDialog('Error while creating filter', 'Unable to create filter: ' + str(inst))
            dlg.draw()
            
            # Close the window.
            self.np.remove()
            messenger.send('dialog_closing')
            base.ignore('tagListItemMenuIndexSelect')





#############

class DialogAddNumericalRange(abstract.AbstractDialog):
    
    def __init__(self, dim):
        # create np for the dialog.
        np = aspect2d.attachNewNode('AddNumericalRangeDialog')
        
        # Safe the tagset that we are working with.
        self.dim = dim
        
        # Call the parent constructor.
        abstract.AbstractDialog.__init__(self, np)
        

    def draw(self):
        self.__create_components()
        self.create_ok_cancel_buttons()
        
        # set the position of the ok/cancel buttons
        self.set_ok_button_pos((0.06, 1,-0.14))
        self.set_cancel_button_pos((0.20, 1, -0.14))
    
    def __create_components(self):
        # Change the size of the background.
        self.bg.setScale(0.40, 0 ,0.25)
        
        # Create label for the window.
        self.text = OnscreenText(text = 'Create range filter on ' + self.dim.name,
        fg=(0,0,0,1),
        parent=self.np,
        frame=(0.3,0.3,0.3,1),
        bg=(0.7,0.7,0.7,1),
        scale=0.035,
        pos=(0, 0.17)
        )
        
        # Create label for lower bound.
        self.text_lower = OnscreenText(text = 'Lower bound', fg=(1,1,1,1), parent=self.np, scale=0.030, pos=(-0.17, 0.06))
        
        # Create textbox for lower bound.
        self.txt_lowerBound = DirectEntry(text = "",
        scale=0.03, 
        initialText="", 
        numLines=1, 
        focus=1, 
        width=10,
        pos=(-0.04, 1, 0.056),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )

        # Create label for upper bound.
        self.text_upper = OnscreenText(text = 'Upper bound', fg=(1,1,1,1), parent=self.np, scale=0.030, pos=(-0.17, -0.02))
        
        # Create textbox for upper bound.
        self.txt_upperBound = DirectEntry(text = "",
        initialText="", 
        numLines=1, 
        focus=0, 
        width=10,
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        pos=(-0.04, 1, -0.02),
        scale=(0.03)
        )


    def click_ok_button(self):
        try:
            # Get the upper and lower values from user.
            lower = int(self.txt_lowerBound.get())
            upper = int(self.txt_upperBound.get())
            
            # Create numerical range filter.
            numerical_range_filter = NumericalRangeFilter(lower, upper, self.dim.id )
            
            # Add the filter to the global.
            browser.objectcube.objectCubeService.get_state().addFilter( numerical_range_filter )
            browser.objectcube.objectCubeService.update_state()
            #State.addFilter( numerical_range_filter )
            
            # Reload the filter list.
            messenger.send(CUBE_MENU_RELOAD_FILTERS)
            self.np.remove()
            messenger.send('dialog_closing')
            #services.dialogService.notify_close()

            # Create action.
            action = ActionFilter(ACTION_TYPE_NUMERICAL_RANGEFILTER, ACTION_ADD, tagsetId=self.dim.id, lowerValue=lower, higherValue=upper )
            actionManager.addAction( action )


            
            # TODO: If there is something on the coordinate... we must reload it?
            #browser.common.coordinateService.redraw()
            #TODO: Reload everything that we have on the drawing area.
            browser.cube.cubeService.reload()
            
        
        except Exception as inst:
            # Create error message.
            dlg = ErrorDialog('Error while creating filter', 'Unable to create filter: ' + str(inst))
            dlg.draw()
            
            # Close the window.
            self.np.remove()
            messenger.send('dialog_closing')





class TextDialog(abstract.AbstractDialog):
    def __init__(self, title=None, message=None):
        np = aspect2d.attachNewNode('Text dialog')
        abstract.AbstractDialog.__init__(self, np)
        
        self.message = message
        self.title = title
        
    def draw(self):
        self.create_ok_button()
        self.bg.setScale(0.45, 1 ,0.20)
        
        # Create instruction label for the window.
        instruction_text = OnscreenText(text = self.message,
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        pos=(0, 0),
        wordwrap=25
        )
        
        # We don't need buttons for this dialog.
        self.btn_ok.hide()


    def Close(self):
        self.np.remove()
        messenger.send('dialog_closing')




###############################################################################        
class CellInfoDialog(abstract.AbstractDialog):
    def __init__(self, cellKey=None, num_images=None, current_hovered_image = None, current_hovered_images_tags = None):
        np = render2d.attachNewNode('Text dialog')
        abstract.AbstractDialog.__init__(self, np)
        
        self.text_np = render2d.attachNewNode('text info np.')
        
        self.tags = current_hovered_images_tags
        self.cellKey = cellKey
        self.num_images = num_images
        
    def draw(self):
        self.create_ok_button()

        
        # Create instruction label for the window.
        tagString = 'Axis location:\n'
        num = 0
        for n in range(3):
            if self.tags[n] is not None:
                if n is 0:
                    tagString += ' -front: ' + self.tags[n][:22] + '\n'
                    num += 1
                
                if n is 1:
                    tagString += ' -in: ' + self.tags[n][:22] + '\n'
                    num += 1
                
                if n is 2:
                    tagString += ' -up: ' + self.tags[n][:22] + '\n'
                    num += 1
        
        tagString += "Number of images: " + str(self.num_images)
        self.bg.setScale(aspect2d, 0.20, 1 ,0.05 + (num*0.021))
        
        
        self.cellInfoText = OnscreenText(align=TextNode.ALeft, text = tagString,
            fg=(1,1,1,1),
            #parent=self.np,
            parent=self.text_np,
            #scale=(0.014, 0.020),
            #scale=(0.024,0.028),
            scale=(0.023),
            pos=(-0.12, 0.025 + ((num-1)*0.015)),
            wordwrap=30,
            font=font
            )
        
        # We don't need buttons for this dialog.
        self.btn_ok.hide()

        # Start mouse watchers task so the dialog will follow the mouse
        self.mouse_task = taskMgr.add( self.mouseWatcherTask, 'MyTaskName', appendTask=True )


    def mouseWatcherTask(self, task):
        if base.mouseWatcherNode.hasMouse():
            x=base.mouseWatcherNode.getMouseX()
            y=base.mouseWatcherNode.getMouseY()
            self.np.setPos(render2d, x+0.14, 1, y-0.1)
            self.text_np.setPos(render2d, x+0.14, 1, y-0.105)
            self.text_np.setScale(aspect2d, 1.35, 1, 1.35)
        return task.cont
    
    
    def close(self):
        self.np.remove()
        self.text_np.remove()
        taskMgr.remove(self.mouse_task)
############################################################################### 







class ErrorDialog(abstract.AbstractDialog):
    def __init__(self, title=None, message=None):
        np = aspect2d.attachNewNode('Error dialog')
        abstract.AbstractDialog.__init__(self, np)
        
        self.message = message
        self.title = title
        
    def draw(self):
        self.create_ok_button()
        self.bg.setScale(0.45, 1 ,0.20)
        
        # Create error title in the window.
        OnscreenText(text = self.title,
        fg=(1,1,1,1),
        frame=(1, 0, 0, 1),
        bg=(1,0,0,0.8),       
        parent=self.np,
        scale=0.040,
        pos=(0, 0.12)
        )

        # Create instruction label for the window.
        instruction_text = OnscreenText(text = self.message,
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        pos=(0, 0.03),
        wordwrap=25
        )
        
        # Set the position of the ok button.
        self.set_ok_button_pos((0, 1,-0.14))










class DialogAddTagToCell(abstract.AbstractDialog):
    """
    Dialog for adding tags to a complete cell.
    """
    def __init__(self, cell=None):
        # create np for the dialog.
        np = aspect2d.attachNewNode('AddTagToCellDialog')
        
        # Safe the tagset that we are working with.
        self.cell = cell
        self.selectedTagset = None
        self.selectedTag = None
        
        # Call the parent constructor.
        abstract.AbstractDialog.__init__(self, np)
        
            

    def draw(self):
        self.__create_components()
        self.create_ok_cancel_buttons()
        
        # set the position of the ok/cancel buttons
        self.set_ok_button_pos((0.18, 1, -0.22))
        self.set_cancel_button_pos((0.32, 1, -0.22))
    
    
    def __onTagsetDropDownSelectChange(self, t):
        selectedTagset = browser.objectcube.objectCubeService.getTagsetByName(t)
        self.tags = []
        
        for tag in selectedTagset.getTags():
            self.tags.append( tag.valueAsString() )


        self.dropDownTags['items'] = self.tags
        self.selectedTagset = selectedTagset


    def __onTagDropDownSelectChange(self, t):
        # find the tag in the current selected tagset
        for tag in self.selectedTagset.getTags():
            if tag.valueAsString() == t:
                self.selectedTag = tag
                return
        raise Exception('Tag was not found in current tagset.')
                


    
    
    def __create_components(self):
        # Change the size of the background.
        self.bg.setScale(0.45, 1 ,0.30)
        
        # Create label for the window.
        title = OnscreenText(text = 'Add tag to cell',
        fg=(0,0,0,1),
        parent=self.np,
        frame=(0.3,0.3,0.3,1),
        bg=(0.7,0.7,0.7,0.8),
        scale=0.035,
        pos=(0, 0.20)
        )
        
        # Create the tagset drop down.
        values = []
        self.tagsets = []
        for tagset in browser.objectcube.objectCubeService.getAllTagsets():
            if tagset.accessTypeAsString() == "User access":
                values.append( tagset.name )
                self.tagsets.append(tagset)
        
        self.dropDownTagsets = DirectOptionMenu(text="tagsets", 
            scale=0.035,
            text_scale=0.8,
            items=values,
            initialitem=0,
            highlightColor=(0.65,0.65,0.65,1),
            parent=self.np,
            rolloverSound=None,
            clickSound=self.mouseclick_sound,
            item_text_font=font,
            pos=(-0.4, 2, 0.05),
            command=self.__onTagsetDropDownSelectChange,
            frameSize=(0, 20, -0.5, 1)

        )
        self.selectedTagset = self.tagsets[0]
        
        tags = []
        
        # Get all tags for first tagset to present
        for tag in self.tagsets[0].getTags():
            tags.append(tag.valueAsString())

        self.dropDownTags = DirectOptionMenu(text="tags", 
            scale=0.035,
            text_scale=0.8,
            items=tags,
            initialitem=0,
            highlightColor=(0.65,0.65,0.65,1),
            parent=self.np,
            rolloverSound=None,
            clickSound=self.mouseclick_sound,
            pos=(-0.4, 2, -0.09),
            item_text_font = font,
            command=self.__onTagDropDownSelectChange,
            frameSize=(0, 20, -0.5, 1),
        )


        # Create instruction label for the window.
        instruction_text = OnscreenText(text = 'Select tagset from the dropdown list.',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        pos=(-0.15, 0.10)
        )


        # Create instruction label for the window.
        instruction_text = OnscreenText(text = 'Select tag from the dropdown list.',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        pos=(-0.17, -0.03)
        )



    def click_ok_button(self):        
        
        # Add the tag to all the images that are in the cluster.
        for image in self.cell.getImages():
            image.addTag( self.selectedTag )

        # Close the window.
        self.np.remove()
        messenger.send('dialog_closing')
        
        # where the newly added tag might change somehting on the screen!
        browser.cube.cubeService.reload()










class DialogAddTagFilter(abstract.AbstractDialog):
    """
    Dialog for adding new tagfilter
    """
    def __init__(self, dim):
        # create np for the dialog.
        np = aspect2d.attachNewNode('AddTagFilterDialog')
        
        # Safe the tagset that we are working with.
        self.dim = dim
        
        # Call the parent constructor.
        abstract.AbstractDialog.__init__(self, np)
        
        self.tags_hash = {}
            

    def draw(self):
        self.__create_components()
        self.create_ok_cancel_buttons()
        
        # set the position of the ok/cancel buttons
        self.set_ok_button_pos((0.18, 1,-0.14))
        self.set_cancel_button_pos((0.32, 1, -0.14))
    
    
    def __create_components(self):
        # Change the size of the background.
        self.bg.setScale(0.45, 1 ,0.22)

        # Create label for the window.
        title = OnscreenText(text = 'Create tag filter on ' + self.dim.name,
        fg=(0,0,0,1),
        parent=self.np,
        frame=(0.3,0.3,0.3,1),
        bg=(0.7,0.7,0.7,0.8),
        scale=0.035,
        pos=(0, 0.15)
        )
        

        # Create instruction label for the window.
        instruction_text = OnscreenText(text = 'Select tag from the dropdown list.',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        pos=(-0.17, 0.05)
        )

        # Create the tagset drop down.
        values = []
        tags = self.dim.getTags()
        for tag in tags:
            values.append( tag.valueAsString() )
            self.tags_hash[ tag.valueAsString() ] = tag
        
        self.tags_menu = DirectOptionMenu(text="options", 
            scale=0.045,
            text_scale=0.6,
            items=values,
            initialitem=0,
            highlightColor=(0.65,0.65,0.65,1),
            parent=self.np,
            rolloverSound=None,
            pos=(-0.4, 2, -0.02),
            command=None
        )

    
    def click_ok_button(self):        
        # Create the tag filter.
        tag = self.tags_hash[ self.tags_menu.get() ]
        tagFilter = TagFilter(tag, self.dim.id )
        
        # Add the filter to the global.
        #State.addFilter( tagFilter )
        browser.objectcube.objectCubeService.get_state().addFilter( tagFilter )
        browser.objectcube.objectCubeService.update_state()
        
        # Reload the filter menu.
        messenger.send(CUBE_MENU_RELOAD_FILTERS)
        
        # Close the window.
        self.np.remove()
        messenger.send('dialog_closing')
        
        # add action
        action = ActionFilter(ACTION_TAGFILTER, ACTION_ADD, self.dim.id, tag.id)
        actionManager.addAction( action )
        
        #TODO: Reload everything that we have on the drawing area.
        #browser.cube.cubeService.reload()
        browser.cube.cubeService.reload()




class DialogAddDateFilter(abstract.AbstractDialog):
    """
    Dialog for adding DateRangeFilter.
    """
    def __init__(self, dim):
        # create np for the dialog.
        np = aspect2d.attachNewNode('AddDateRangeFilterDialog')
        
        # Safe the tagset that we are working with.
        self.dim = dim
        
        # Call the parent constructor.
        abstract.AbstractDialog.__init__(self, np)
        
        self.tags_hash = {}
            

    def draw(self):
        self.__create_components()
        self.create_ok_cancel_buttons()
        
        # set the position of the ok/cancel buttons
        self.set_ok_button_pos((0.28, 1,-0.22))
        self.set_cancel_button_pos((0.43, 1, -0.22))
    
    
    def __create_components(self):
        #self.bg.setScale(0.8, 1 ,0.8)
        # Change the size of the background.
        self.bg.setScale(0.60, 1 ,0.30)
        
        
        # Create label for the window.
        title = OnscreenText(text = 'Create Date range filter for ' + self.dim.name,
        fg=(0,0,0,1),
        parent=self.np,
        frame=(0.3,0.3,0.3,1),
        bg=(0.7,0.7,0.7,0.8),
        scale=0.035,
        align=TextNode.ACenter,
        pos=(0, 0.22)
        )
        
        title = OnscreenText(text = 'Lower day (dd)',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(-0.41, 0.14)
        )
        
        # Create textbox for lower bound.
        self.txt_lower_day = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(-0.51, 1, 0.08),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )

        # Create label for lower month.
        OnscreenText(text = 'Lower month (mm)',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(0.0, 0.14)
        )

        self.txt_lower_month = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(-0.13, 1, 0.08),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )


        # Create label for lower month.
        OnscreenText(text = 'Lower year (yy)',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(0.35, 0.14)
        )



           
        self.txt_lower_year = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(0.25, 1, 0.08),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )
        

        # Text for upper day
        OnscreenText(text = 'Upper day (dd)',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(-0.41, -0.04)
        )
        
             
        # Create textbox for lower bound.
        self.txt_upper_day = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(-0.51, 1, -0.1),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )
        
        # Text for upper month
        OnscreenText(text = 'Upper month (mm)',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(0, -0.04)
        )
        
        
        self.txt_upper_month = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(-0.13, 1, -0.1),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )
        
        
        # Create label for lower month.
        OnscreenText(text = 'Upper year (yy)',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(0.35, -0.04)
        )        

        
        self.txt_upper_year = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(0.25, 1, -0.1),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )

    
    def click_ok_button(self):        
        # Values for the lower values.

        
        # Create the tag filter.
        #tag = self.tags_hash[ self.tags_menu.get() ]
        
        # Add the filter to the global.
        try:
            lower_day = int(self.txt_lower_day.get())
            lower_month = int(self.txt_lower_month.get())
            lower_year = int(self.txt_lower_year.get())

            # Values for the upper values.
            upper_day = int(self.txt_upper_day.get())
            upper_month = int(self.txt_upper_month.get())
            upper_year = int(self.txt_upper_year.get())
            
            filter = DateRangeFilter(lower_year, lower_month, lower_day, upper_year, upper_month, upper_day, self.dim.id)
            #State.addFilter( filter )

            browser.objectcube.objectCubeService.get_state().addFilter( filter )
            browser.objectcube.objectCubeService.update_state()

            # Reload the filter menu.
            messenger.send(CUBE_MENU_RELOAD_FILTERS)

            # Close the window.
            self.np.remove()
            messenger.send('dialog_closing')
            #TODO: Reload everything that we have on the drawing area.
            browser.cube.cubeService.reload()

            
            
        except Exception as inst:
            # Create error message.
            dlg = ErrorDialog('Error while creating filter', 'Unable to create filter: ' + str(inst))
            dlg.draw()
            
            # Close the window.
            self.np.remove()
            messenger.send('dialog_closing')    








class DialogAddTimeFilter(abstract.AbstractDialog):
    """
    Dialog for adding DateRangeFilter.
    """
    def __init__(self, dim):
        # create np for the dialog.
        np = aspect2d.attachNewNode('AddDateRangeFilterDialog')
        
        # Safe the tagset that we are working with.
        self.dim = dim
        
        # Call the parent constructor.
        abstract.AbstractDialog.__init__(self, np)
        
        self.tags_hash = {}
            

    def draw(self):
        self.__create_components()
        self.create_ok_cancel_buttons()
        
        # set the position of the ok/cancel buttons
        self.set_ok_button_pos((0.28, 1,-0.22))
        self.set_cancel_button_pos((0.43, 1, -0.22))
    
    
    def __create_components(self):
        #self.bg.setScale(0.8, 1 ,0.8)
        # Change the size of the background.
        self.bg.setScale(0.75, 1 ,0.30)
        
        
        # Create label for the window.
        title = OnscreenText(text = 'Create time range filter for ' + self.dim.name,
        fg=(0,0,0,1),
        parent=self.np,
        frame=(0.3,0.3,0.3,1),
        bg=(0.7,0.7,0.7,0.8),
        scale=0.035,
        align=TextNode.ACenter,
        pos=(0, 0.22)
        )
        
        title = OnscreenText(text = 'Lower hour (hh)',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(-0.60, 0.14)
        )
        
        # Create textbox for lower bound.
        self.txt_lower_hour = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(-0.70, 1, 0.08),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )

        # Create label for lower month.
        OnscreenText(text = 'Lower min (mm)',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(-0.25, 0.14)
        )

        self.txt_lower_min = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(-0.38, 1, 0.08),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )


        # Create label for lower month.
        OnscreenText(text = 'Lower sec (ss)',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(0.08, 0.14)
        )



           
        self.txt_lower_sec = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(-0.02, 1, 0.08),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )
        

        # Text for lower msec
        OnscreenText(text = 'Lower msec',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(0.4, 0.14)
        )  
        
        self.txt_lower_msec = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(0.32, 1, 0.08),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )      
        
        # Text for upper day
        OnscreenText(text = 'Upper hour (hh)',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(-0.60, -0.04)
        )
        
        # Create textbox for lower bound.
        self.txt_upper_hour = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(-0.70, 1, -0.1),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )
        
        # Text for upper month
        OnscreenText(text = 'Upper min (mm)',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(-0.25, -0.04)
        )
        
        self.txt_upper_min = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(-0.38, 1, -0.1),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )
        
        # Create label for lower month.
        OnscreenText(text = 'Upper sec (ss)',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(0.08, -0.04)
        )        
        
        self.txt_upper_sec = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(-0.02, 1, -0.1),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )
        
        # Create label for uppser msec.
        OnscreenText(text = 'Upper msec',
        fg=(1,1,1,1),
        parent=self.np,
        scale=0.030,
        align=TextNode.ACenter,
        pos=(0.40, -0.04)
        )
        
        self.txt_upper_msec = DirectEntry(text = "",
        scale=0.03,
        initialText="", 
        numLines=1, 
        focus=1, 
        width=8,
        pos=(0.32, 1, -0.1),
        clickSound = None,
        rolloverSound = None,
        parent=self.np,
        )


    def click_ok_button(self):        
        try:
            filter = TimeRangeFilter(self.dim.id)

            if len(self.txt_lower_hour.get()) > 0:
                filter.hoursFrom = int(self.txt_lower_hour.get())
            
            if len(self.txt_upper_hour.get()) > 0:
                filter.hoursTo = int(self.txt_lower_hour.get())

            if len(self.txt_lower_min.get()) > 0:
                filter.hoursFrom = int(self.txt_lower_min.get())

            if len(self.txt_upper_min.get()) > 0:
                filter.hoursTo = int(self.txt_lower_min.get())


            browser.objectcube.objectCubeService.get_state().addFilter( filter )
            browser.objectcube.objectCubeService.update_state()
            
            # Reload the filter menu.
            messenger.send(CUBE_MENU_RELOAD_FILTERS)

            # Close the window.
            self.np.remove()
            messenger.send('dialog_closing')
            
            #TODO: Reload everything that we have on the drawing area.
            browser.cube.cubeService.reload()
        
        except Exception as inst:
            # Create error message.
            dlg = ErrorDialog('Error while creating filter', 'Unable to create filter: ' + str(inst))
            dlg.draw()
            
            # Close the window.
            self.np.remove()
            messenger.send('dialog_closing')
            
