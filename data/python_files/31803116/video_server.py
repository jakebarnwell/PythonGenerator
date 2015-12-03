import sys
import threading
import time
import datetime
import cv
import SimpleCV as s
from alternative import *

import SocketServer

from utils.blackwhite import blackwhite
from utils.detect_centers import detect_centers
from utils.calibrate import Calibrate
from utils.backgroundaveraging import BackgroundAveraging
import utils

HOST, PORT = "localhost", 8474

# This is the line currently being output to all clients
frame = 0
framebuffer = ""

Q_KEYS = [113,    # q
         1048689, # q + numlock
         131153,  # q + capslock
         1179729] # q + capslock + numlock

class ThreadedVisionRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        print "Client connected!"
        lastframeout = 0
        while True:
            if lastframeout != frame:
                lastframeout = frame
                # Print out one set of coordinates per line
                # TODO: Fix broken pipes when clients disconnect messily
                self.wfile.write(framebuffer)
                self.wfile.write("\n")
                self.wfile.flush()
             
        print "Client disconnected"

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

def start_vision():
    """
    Creates a video feed and shows the colored blobs detected
    """
    global framebuffer, frame
    
    cv.NamedWindow("video",cv.CV_WINDOW_AUTOSIZE)
    if utils.PITCH == "side":
        cam = MplayerCamera()
    else:
        cam = MplayerCamera()
        #cam = s.Camera(0,{"width" : 720, "height": 576})
    
    #Calibrate cam
    chessboard_dim = (9,6)
    cal = Calibrate(chessboard_dim)
    #TODO: Separate calibration data folders for the two pitches
    string = "utils/" + utils.PITCH + "/"
    cal.calibrate_camera_from_mem(string) 
    img = cam.getImage().getBitmap()

    #number of frames to construct bg
    numFrames = 60
    
    #Process previously saved background image 
    #TODO: Separate background images for the two pitches
    
    bg = cv.LoadImage("00000006.jpg")
    bgFixed  = cal.calibrate_image(utils.PITCH, bg)
    frame_dim = cv.GetSize(bgFixed)
    ba = BackgroundAveraging(bgFixed)
    # for calculating fps later on
    start = time.mktime(datetime.datetime.now().timetuple())
    while(True):
        # counting frames
        frame += 1
        img = cam.getImage().getBitmap()
        
        #Build BG model
        if ( frame <= 2):
            continue

        if(frame < numFrames):
            baseimg  = cal.calibrate_image(utils.PITCH,img)
            if utils.BG_CALC: 
                ba.accumulate_background(baseimg)
            else:
                #TODO: impelement working from a directory (based on the pitch...)
                ba.accumulate_background(bgFixed)
        elif(frame == numFrames):
            ba.create_models_from_stats()
        else:
            #more arguments added, cal is a camera calibration object
            #           ba is background model
            #If ba = None, pre-saved image is used as bg 
            #
            #### THIS IS THE CORE OF THE PROGRAM ####
            (im, centers) = detect_centers(img,cal,ba,bgFixed)
            
            # OUTPUT THE DETECTION FOR THE STRATEGY TEAM
            yellow, blue, ball = centers
            framebuffer = "%d;%f,%f,%f;%f,%f,%f;%f,%f" % (frame,
                          yellow[0], yellow[1], yellow[2],
                          blue[0], blue[1], blue[2],
                          ball[0], ball[1])
            end = time.mktime(datetime.datetime.now().timetuple()) # used in fps calculation
            #output fps
            cv.PutText(im,"FPS: "+str(int(float(frame)/(end-start))), (500,20),cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 0.5, 0.5) , (255,255,255))
            cv.ShowImage("video", im)
            if(cv.WaitKey(5) in Q_KEYS): # Die on the q key
                print "Exiting on keypress"
                #done = True
                if utils.PITCH == "side":
                    cam.kill_mplayer()
                break

    # Exit the server thread when the main thread terminates
    cv.DestroyWindow("video");

def main():
    """
    Initiates multithreaded vision server
    """
    if (len(sys.argv) > 1): 
        for arg in sys.argv:
            if arg == "debug":
                utils.DEBUG = True
            if arg == "yellow":
                utils.YELLOW_PRESENT = True
                utils.BLUE_PRESENT = False
            elif arg == "blue":
                utils.BLUE_PRESENT = True
                utils.YELLOW_PRESENT = False
            if arg == "side":
                utils.PITCH = "side"
            elif arg == "main":
                utils.PITCH = "main"
            if arg == "buildbg":
                utils.BG_CALC = True
            elif arg == "storedbg":
                utils.BG_CALC = False
    
    print "PRESS q TO EXIT"
    print "Starting video server for " + utils.PITCH
    print "Other arguments: "
    print "DEBUG " + str(utils.DEBUG)
    print "YELLOW_PRESENT " + str(utils.YELLOW_PRESENT) 
    print "BLUE_PRESENT " + str(utils.BLUE_PRESENT)
    print "BG_CALC " + str(utils.BG_CALC)

    print "You can ignore the following three error messages..."

    # Create a multithreaded server, as one does
    server = ThreadedTCPServer((HOST, PORT), ThreadedVisionRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()


    # Create a new thread for the capture loop
    vision_thread = threading.Thread(target=start_vision)
    vision_thread.daemon = True
    vision_thread.start()
    vision_thread.join()
  
    # When terminated shutdown the server
    server.shutdown()
    print "Cleaned up server"

if __name__ == "__main__":
    main()

