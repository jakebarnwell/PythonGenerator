import cv
import time
import sys
import string
from blob_detection import *
import calibrate
import SimpleCV as s 
import numpy as np
from printer import print


origIm = cv.LoadImage("test.png")
imgGray = cv.CreateImage(cv.GetSize(origIm), 8, 1)
cv.CvtColor(origIm, imgGray, cv.CV_BGR2GRAY)

#cv.Canny(imgGray, imgGray, 50, 200, 3)


#cv.Threshold(imgGray, imgGray, cv.CV_GAUSSIAN, 11, 11); 
#cv.Smooth(imgGray, imgGray, cv.CV_GAUSSIAN, 11, 11); 

cv.ShowImage("sfgsd", imgGray)

storage = cv.CreateMat(imgGray.width, 1, cv.CV_32FC3)

#This is the line that throws the error
circles = cv.HoughCircles(imgGray, storage, cv.CV_HOUGH_GRADIENT, 2, 1, 200, 100) 



if storage.rows == 0:
	print_line("No circles")

circs = np.asarray(storage)
sz = circs.shape

print_line(sz)


for i in range(sz[0]):
	print_line("found circle")
	print_line(circs[i][0][0],circs[i][0][1])
	print_line(circs[i][0][2])
	cv.Circle(origIm, (circs[i][0][0],circs[i][0][1]), 10, (255,255,255), 1)


cv.ShowImage("img", origIm)
	

cv.WaitKey(0)




