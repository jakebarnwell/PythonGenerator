import sys
import time
import pygame
from pygame.locals import *
from VisionDebugger import *
from optparse import OptionParser
from SimpleCV import *




# These are the posible command-line arguments
parser = OptionParser()
parser.add_option("-P", "--pitch", dest="pitch", action="store", type="int", help="Choose pitch to run on, one of {0, 1}", default=0)
parser.add_option("-m", "--use-mplayer", dest="use_mplayer", action="store_true", help="Use mplayer for vision input rather than SimpleCV", default=False)
parser.add_option("-v", "--videoDev", dest="videoDev", action="store", type="int", help="Use video device x", default=0)
(options, args) = parser.parse_args()



# Check that a valid argument is passed
if not options.pitch in [0,1]:
    parser.error("Pitch must be one of: {0,1}")
if not options.videoDev in [-2,-1,0,1,2]:
    parser.error("Pitch must be one of: {-2..2}")



# Set global variables used throuout
# Calculations output
image2display = []
image = []
hsv_image = []
croped_image = []
binary_image_yellow_robot = []
binary_image_yellow_circle = []
binary_image_blue_robot = []
binary_image_blue_circle = []
binary_image_ball = []
coords_yellow_robot = None
coords_yellow_circle = None
coords_blue_robot = None
coords_blue_circle = None
coords_ball = None
coords_yellow_robot_cropped = None
coords_blue_robot_cropped = None
coords_ball_cropped = None
orientation_yellow_robot = None
orientation_blue_robot = None
fps = 0

# Other variables
display = None
focus = None
step = False
move = False
show = "full"



# Initialize the pygame and the debugger
pygame.init()
path = 'vision'
vision_debugger = VisionDebugger(path, pitch=options.pitch, use_mplayer=options.use_mplayer, videoDevice=options.videoDev)



# Calculate all needed information
def makeCalculations():
    
    global image, hsv_image, croped_image, binary_image_yellow_robot, binary_image_yellow_circle, \
    binary_image_blue_robot, binary_image_blue_circle, binary_image_ball, \
    coords_yellow_robot, coords_yellow_circle, coords_blue_robot, coords_blue_circle,\
    coords_ball, coords_yellow_robot_cropped, coords_blue_robot_cropped, coords_ball_cropped, \
    orientation_yellow_robot, orientation_blue_robot, fps
    
    image, hsv_image, croped_image, binary_image_yellow_robot, binary_image_yellow_circle, \
    binary_image_blue_robot, binary_image_blue_circle, binary_image_ball, \
    coords_yellow_robot, coords_yellow_circle, coords_blue_robot, coords_blue_circle,\
    coords_ball, coords_yellow_robot_cropped, coords_blue_robot_cropped, coords_ball_cropped, \
    orientation_yellow_robot, orientation_blue_robot, fps \
    = vision_debugger.doCalculations()



while True:
    
    # Return True if a key is pressed
    pressed = pygame.key.get_pressed()



    # Loop through events
    for event in pygame.event.get():
        
        # Escape function (when X is pressed)
        if event.type == QUIT:
            pygame.quit()
            sys.exit()



    # Crop/Rotate
    if pressed[273]: # Up arrow: move image up
        vision_debugger.parameters.decrement_crop_y()
        vision_debugger.pre_processor.load_default_parameters()

    if pressed[274]: # Down: move image up down
        vision_debugger.parameters.increment_crop_y()
        vision_debugger.pre_processor.load_default_parameters()

    if pressed[276]: # Left arrow: move image left
        vision_debugger.parameters.decrement_crop_x()
        vision_debugger.pre_processor.load_default_parameters()

    if pressed[275]: # Right arrow: move image right
        vision_debugger.parameters.increment_crop_x()
        vision_debugger.pre_processor.load_default_parameters()

    if pressed[264]: # Num 8: increase height
        vision_debugger.parameters.increment_crop_h()
        vision_debugger.pre_processor.load_default_parameters()

    if pressed[258]: # Num 2: decrease crop height
        vision_debugger.parameters.decrement_crop_h()
        vision_debugger.pre_processor.load_default_parameters()

    if pressed[260]: # Num 4: increase crop width
        vision_debugger.parameters.decrement_crop_w()
        vision_debugger.pre_processor.load_default_parameters()

    if pressed[262]: # Num 6: decrease crop width
        vision_debugger.parameters.increment_crop_w()
        vision_debugger.pre_processor.load_default_parameters()
            
    if pressed[261]: # Num 5: default croping
        vision_debugger.parameters.load_parameters()
        vision_debugger.pre_processor.load_default_parameters()
        
    if pressed[265]: # Num 9: full image
        vision_debugger.parameters.set_parameters_to_full_image()
        vision_debugger.pre_processor.load_default_parameters()

    if pressed[K_KP_MINUS]: # Minus: decrease rotation
        vision_debugger.parameters.decrement_rotate()
        vision_debugger.pre_processor.load_default_parameters()

    if pressed[K_KP_PLUS]: # Plus: increase rotation
        vision_debugger.parameters.increment_rotate()
        vision_debugger.pre_processor.load_default_parameters()



    # Display options
    if pressed[K_1]: # 1: showing ball
        show = "ball"
        print "Showing Ball"
        time.sleep(0.1)

    if pressed[K_2]: # 2: showing blue robot
        show = "blue_robot"
        print "Showing Blue robot"
        time.sleep(0.1)

    if pressed[K_3]: # 3: showing yellow robot
        show = "yellow_robot"
        print "Showing Yellow robot"
        time.sleep(0.1)

    if pressed[K_4]: # 4: showing circle (blue)
        show = "blue_circle"
        print "Showing circle (blue)"
        time.sleep(0.1)

    if pressed[K_5]: # 5: showing circle (yellow)
        show = "yellow_circle"
        print "Showing circle (yellow)"
        time.sleep(0.1)

    if pressed[K_6]: # 6: showing full image
        show = "full"
        print "Showing full image"
        time.sleep(0.1)

    if pressed[K_7]: # 7: showing croped image
        show = "croped"
        print "Showing croped image"
        time.sleep(0.1)

    if pressed[K_8]: # 8: showing full image, hsv
        show = "hsv"
        print "Showing full image in HSV"
        time.sleep(0.1)



    # Train
    if pressed[K_r]: # R: Train red
        focus = vision_debugger.ball
        print "Focus on red ball"
        time.sleep(0.1)

    if pressed[K_b]: # B: Train blue
        focus = vision_debugger.blue_robot
        print "Focus on blue robot"
        time.sleep(0.1)         

    if pressed[K_y]: # Y: Train yellow
        focus = vision_debugger.yellow_robot
        print "Focus on yellow robot"
        time.sleep(0.1)

    if pressed[K_c]: # C: Train blue circle
        focus = vision_debugger.blue_circle
        print "Focus on black circle (blue)"
        time.sleep(0.1)

    if pressed[K_v]: # V: Train yellow circle
        focus = vision_debugger.yellow_circle
        print "Focus on black circle (yellow)"
        time.sleep(0.1)

    if pressed[K_n]: # N: Train none
        focus = None
        print "Cancel Training"
        time.sleep(0.1)

    if pygame.mouse.get_pressed()[0]: # Left click: Train the object
        x,y = pygame.mouse.get_pos()
        colour = hsv_image.getPixel(x, y)
        if focus and (show == "full" or show == "hsv"):
            focus.set_colour(colour)
            print "Colour set to: ", colour
        else:
            print "Please switch to the full image (6) and focus on an object (R,B or Y)"



    # Print information
    if pressed[K_EQUALS]: # =: Print all current known information
        vision_debugger.parameters.printCropping()
        print "Current yellow robot parameters: "
        vision_debugger.yellow_robot.printColour()
        print "[x,y] = ", coords_yellow_robot
        print "Angle = ", orientation_yellow_robot
        print "Current blue robot parameters: "
        vision_debugger.blue_robot.printColour()
        print "[x,y] = ", coords_blue_robot
        print "Angle = ", orientation_blue_robot
        print "Current ball parameters: "
        vision_debugger.ball.printColour()
        print "[x,y] = ", coords_ball
        print "         \|||/\n         (o o)\n|~~~~ooO~~( )~~~~~~~|\n|      die          |"
        print "|   Flipperwaldt    |\n|         gersput   |\n|~~~~~~~~~~~~~~Ooo~~|"
        print "        |  |  |      \n         -- --       \n         || ||       \n        ooO Ooo      "
        time.sleep(0.1)

    if pygame.mouse.get_pressed()[2]: # Right click: Print cursor coordinates
        x,y = pygame.mouse.get_pos()
        pixelValue = hsv_image.getPixel(x, y)
        print "Coordinates: (" + str(x) + "," + str(y) + ")"
        print "Pixel value [h,s,v]: ", pixelValue

    if pressed[K_f]: # F: Get frame rate
        print fps
        time.sleep(0.2)



    # Other functions
    if pressed[K_t]: # T: Take snapshot
        image2display.save("Snapshots/Snapshot.jpg")
        time.sleep(0.1)

    if pressed[K_p]: # P: Reload parameters
        vision_debugger.reload_parameters()
        time.sleep(0.1)

    if pressed[K_s]: # S: Change mode to use steps
        step = not step
        if step:
            print "Entering step mode. Press enter to move frame"
        else:
            print "Exiting step mode"
        time.sleep(0.5)

    if pressed[K_KP_ENTER]:
        move = True



    # Decide which calculations to make
    if not step:
        makeCalculations()
    else:
        if move:
            makeCalculations()
            move = False



    # Image to show
    if show == "croped":
        image2display = croped_image
    elif show == "ball":
        image2display = binary_image_ball
    elif show == "blue_robot":
        image2display = binary_image_blue_robot
    elif show == "yellow_robot":
        image2display = binary_image_yellow_robot
    elif show == "blue_circle":
        image2display = binary_image_blue_circle
    elif show == "yellow_circle":
        image2display = binary_image_yellow_circle
    elif show == "hsv":
        image2display = hsv_image
    elif show == "full":
        image2display = image



    # Draw on a layer
        try:
            if image2display:
                dl = image2display.dl()
                
                # Draw centroids and orientations
                if coords_yellow_robot:
                    dl.circle(coords_yellow_robot, 3, (255, 0, 0), filled=True)
                
                if coords_blue_robot:
                    dl.circle(coords_blue_robot, 3, (255, 0, 0), filled=True)
                
                if coords_yellow_circle:
                    dl.circle(coords_yellow_circle, 3, (0, 255, 255), filled=True)
                
                if coords_blue_circle:
                    dl.circle(coords_blue_circle, 3, (0, 255, 255), filled=True)
                
                if coords_ball:
                    dl.circle(coords_ball, 3, (255,0,0), filled=True)
                
                if coords_yellow_robot and coords_yellow_circle:
                    dl.line(coords_yellow_robot, coords_yellow_circle, (0,255,255), 3)
                
                if coords_blue_robot and coords_blue_circle:
                    dl.line(coords_blue_robot, coords_blue_circle, (0,255,255), 3)
                
        except TypeError:
            pass



    # Display the image
    if not display:
        display = Display(image2display.size(),pygame.RESIZABLE,'Vision Display')
        print image2display.size()
    
    if image2display:
       image2display.save(display)
       #display.writeFrame(image2display, False)



