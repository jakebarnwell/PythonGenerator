import sys
import threading
import time
import cv
import SimpleCV as s

import SocketServer

from utils.blackwhite import blackwhite
from utils.detect_centers import detect_centers
from utils.calibrate import Calibrate
from utils.backgroundaveraging import BackgroundAveraging

def start_vision():
    """
    Creates a video feed and shows the colored blobs detected
    """
    frame = 0
    
    cv.NamedWindow("video",cv.CV_WINDOW_AUTOSIZE)
    #NOTE: BREAKS HERE
    cam = s.Camera(0,{"width" : 720, "height": 576})
   # im = cam.getImage()
  #  print type(im)
    
    print "There"
    #Calibrate cam
    #TO DO:Create new calibration data
    chessboard_dim = (9,6)
    cal = Calibrate(chessboard_dim)
    cal.calibrate_camera_from_mem("utils/calibration_data/") 
    
    img = cam.getImage().getBitmap()

    #number of frames to construct bg
    numFrames = 30
    
    #Backg image, undistort it 
    bg = cv.LoadImage("00000006.jpg")

    undist_im = cal.undist_fisheye(bg)
    cropped = cal.crop_frame(undist_im)
    bgFixed = cal.undist_perspective(cropped, corners_from_mem=False)
    frame_dim = cv.GetSize(bgFixed)
    ba = BackgroundAveraging(bgFixed)
    
    while(True):
        #This is frame count(?)
        frame += 1
        img = cam.getImage().getBitmap()
        
        #Build BG model
        if(frame < numFrames):
            undist_im = cal.undist_fisheye(img)
            cropped = cal.crop_frame(undist_im)
            baseimg = cal.undist_perspective(cropped, corners_from_mem=False)
            ba.accumulate_background(baseimg)
        elif(frame == numFrames):
            ba.create_models_from_stats()
        else:
            #ba.background_diff(img, mask1)
            #more arguments added, cal is a camera calibration object
            #           ba is background model
            #If ba = None, pre-saved image is used as bg 
            #
            (im, centers) = detect_centers(img,cal,ba,bgFixed)

            # OUTPUT THE LINE INTO THE FORMAT THE STRATEGY TEAM WANT
            #--- only after bg is built-----
            yellow, blue, ball = centers
            framebuffer = "%d;%f,%f,%f;%f,%f,%f;%f,%f" % (frame,
                          yellow[0], yellow[1], yellow[2],
                          blue[0], blue[1], blue[2],
                          ball[0], ball[1])

            cv.ShowImage("video", im)
           # cv.WaitKey(0)
            if(cv.WaitKey(10) != -1 ):
                break

    # Exit the server thread when the main thread terminates
    cv.DestroyWindow("video");


def main():
	start_vision()

if __name__ == "__main__":
    main()
