import pygame
from pygame import locals
import sys
import Image
import time

#this is important for capturing/displaying images
import numpy as np
import cv2
import cv2.cv as cv
from video import create_capture
from common import clock, draw_str

#GUI
from pgu import gui as pgui, text

#Velleman board
from pyk8055 import *

#Arduino - only one of this and Velleman will be used. Probably...
import pyduino

#There should be a USB camera, but if not use the webcam.
try:
	camera = create_capture(1)
    	ret, im = camera.read()
	try:
		camera2=create_capture(2)
		ret,im=camera2.read()
	except:
		camera2=None
except:
	camera = create_capture(0)

def playSound(fileName):
	if not pygame.mixer.music.get_busy():
		pygame.mixer.music.load(fileName)
		pygame.mixer.music.play(1)

def open_file_browser(guiInput):
    d = pgui.FileDialog()
    d.connect(pgui.CHANGE, handle_file_browser_closed, d,guiInput)
    d.open()


def handle_file_browser_closed(dlg, guiInput):
    if dlg.value: guiInput.value = dlg.value


def sendSignalVelleman(signalCode):
    k.WriteAllDigital(signalCode)
    k.WriteAllDigital(0)

def sendSignalArduino(signalCode):
    print signalCode

def readOutputPinsArduino():
    output=None
    if arduino is not None:
   	output=""
    	for i in range(3,10):
		output+=str(arduino.digital[i].read())
    return output

def sendSignal(signalCode):
    #Flashes signal to Veleman
    sendSignalVelleman(signalCode)


def headTrackState(arg):
    btn, text = arg
    global headTracking
    headTracking = btn.value

def get_image(camera, headTracking):
    global cascade
    ret, im = camera.read()
    t = clock()
    if (headTracking):
	smallIm = cv2.resize(im, (160,120))
        grey = cv2.cvtColor(smallIm, cv2.COLOR_BGR2GRAY)
        grey = cv2.equalizeHist(grey)
	rects = detect(grey, cascade)
        draw_rects(im, 4*rects, (0,255,0))
	#TODO: Also fire servos we need.
    draw_str(im, (20,40), str(readOutputPinsArduino()))
    dt = clock() - t
    draw_str(im, (20,20), 'Latency: %.4f ms' % (dt*1000))
    im_rgb=cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    cv_img=cv.fromarray(im_rgb)
    return cv_img

def detect(img, cascade):
    rects = cascade.detectMultiScale(img, scaleFactor=1.3, minNeighbors=4, minSize=(30, 30), flags = cv.CV_HAAR_SCALE_IMAGE)
    if len(rects) == 0:
        return []
    rects[:,2:] += rects[:,:2]
    return rects

def draw_rects(img, rects, color):
    for x1, y1, x2, y2 in rects:
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

def set_pin_mode(arduino, pin, mode):
    if mode == 1:
        #Digital input
        arduino.digital_ports[pin >> 3].set_active(1)
        arduino.digital[pin].set_mode(pyduino.DIGITAL_INPUT)
    if mode == 2:
        #Digital output
        arduino.digital_ports[pin >> 3].set_active(1)
        arduino.digital[pin].set_mode(pyduino.DIGITAL_OUTPUT)
        arduino.digital[pin].write(1)    #Turn output high
    if mode == 3:
        #Digital PWM
        arduino.digital_ports[pin >> 3].set_active(1)
        arduino.digital[pin].set_mode(pyduino.DIGITAL_PWM)
    if mode == 4:
        #Analog in
        arduino.analog[pin].set_active(1)



pygame.init()
window = pygame.display.set_mode((0,0),pygame.FULLSCREEN)
pygame.display.set_caption("DalekCam")
screen = pygame.display.get_surface()

pygame.joystick.init()

#Set up the GUI
fontBig = pygame.font.SysFont("default", 48)
fg=(255,255,255)
gui = pgui.App()
lo=pgui.Container(width=1024,height=600)
title = pgui.Label("Dalek Controller", color=fg, font=fontBig)
lo.add(title,700,10)

cbt = pgui.Table()
cb1 = pgui.Switch()
cb1.connect(pgui.CHANGE, headTrackState, (cb1, "Head Tracking"))
cb1l = pgui.Label("Enable Head Tracking",color=fg)
cbt.add(cb1)
cbt.add(cb1l)
cbt.tr()
lo.add(cbt,750,60)

#Choose MP3s
t = pgui.Table()
t.tr()
td_style = {'padding_right': 10, 'color':fg}
t.td( pgui.Label('Top Left Sound File:',color=fg) , style=td_style)
input_file_1 = pgui.Input()
t.td( input_file_1, style=td_style )
b = pgui.Button("Browse...")
t.td( b, style=td_style )
input_file_1.value="./ext1.mp3"
b.connect(pgui.CLICK, open_file_browser, input_file_1)

t.tr()
t.td( pgui.Label('Top Right Sound File:',color=fg) , style=td_style)
input_file_2 = pgui.Input()
t.td( input_file_2, style=td_style )
b2 = pgui.Button("Browse...")
t.td( b2, style=td_style )
b2.connect(pgui.CLICK, open_file_browser, input_file_2)
input_file_2.value="./dalek-doctor.mp3"
lo.add(t,550,500)

#Load information about face detection.

cascade_fn = "./haarcascade_frontalface_default.xml"
cascade = cv2.CascadeClassifier(cascade_fn)
headTracking=False

gui.init(lo)

try:
	j=pygame.joystick.Joystick(0)
	j.init()
	print 'Enabled joystick: ' + j.get_name()
except pygame.error:
	print 'no joystick found'

try:
	k=k8055(0)
except IOError:
	print 'could not find K8055 board'
	k=None


#Define arduino Pins

HEAD_POWER = 7
HEAD_DIRECTION = 8
EYE_DIRECTION = 12
EYE_POWER = 11
TEST_PIN = 13

try:
	arduino = pyduino.Arduino("/dev/ttyUSB0")
	set_pin_mode(arduino, 2, 2)
	set_pin_mode(arduino, 3, 2)
	set_pin_mode(arduino, 4, 2)
	set_pin_mode(arduino, 5, 2)
	set_pin_mode(arduino, 6, 2)
	set_pin_mode(arduino, HEAD_POWER, 2) 
	set_pin_mode(arduino, HEAD_DIRECTION, 2)
	set_pin_mode(arduino, 9, 2)
	set_pin_mode(arduino, 10, 2)
	set_pin_mode(arduino, EYE_POWER, 2) #
	set_pin_mode(arduino, EYE_DIRECTION, 2) 
	set_pin_mode(arduino, TEST_PIN, 2) #Set pin 13 to digital output. Useful for testing, as this pin has a LED on it.
	#TODO: Now set low.


except IOError:
	print 'could not find Arduino'
	arduino=None

done=False

while not done:
	for e in pygame.event.get():
		if e.type is pygame.locals.QUIT:
			done=True
		elif e.type is pygame.locals.KEYDOWN :
			print e.key
			if e.key == pygame.locals.K_ESCAPE:
				done=True
			if e.key == pygame.locals.K_SPACE:
				spacepushed=True
			if int(e.key) >= 49 and int(e.key)<=58:
				if arduino is not None:
					value= arduino.digital[e.key-48].read()
					value = -1 * (value-1)
                        		arduino.digital[e.key-48].write(value)
		
		elif e.type == pygame.locals.JOYAXISMOTION:
			x,y = j.get_axis(0), j.get_axis(1)
			x2,y2 = j.get_axis(2), j.get_axis(3)
			x3,y3 = j.get_axis(4), j.get_axis(5)
			print 'x and y : ' + str(x) + ' , ' + str(y)
			print 'x2 and y2 : ' + str(x2) + ' , ' + str(y2)
			print 'x3 and y3 : ' + str(x3) + ' , ' + str(y3)
		elif e.type == pygame.locals.JOYBALLMOTION:
			print 'ballmotion'
		elif e.type == pygame.locals.JOYHATMOTION:
			#We end up here whether we are pushing or releasing
			#The hat controls eye up/down and head left/right.
			
			if e.value[0] == -1:
				#Set head flag to turn left
				arduino.digital[HEAD_DIRECTION].write(0)
				#Apply power
				arduino.digital[HEAD_POWER].write(1)
			elif e.value[0] == 1:
				#Head right		
				arduino.digital[HEAD_DIRECTION].write(1)
				#Apply power
				arduino.digital[HEAD_POWER].write(1)
			else:
				#Turn off power
				arduino.digital[HEAD_POWER].write(0)
				
			if e.value[1] == -1:
				#Set eye flag to go down
				arduino.digital[EYE_DIRECTION].write(0)
				#Apply power
				arduino.digital[EYE_POWER].write(1)
			elif e.value[1] == 1:
				#Eye up	
				arduino.digital[EYE_DIRECTION].write(1)
				#Apply power
				arduino.digital[EYE_POWER].write(1)
			else:
				#Turn off power
				arduino.digital[EYE_POWER].write(0)
				

		elif e.type == pygame.locals.JOYBUTTONDOWN:
			if e.button ==0 :
				print "Cross"
                        	arduino.digital[11].write(1)
			elif e.button == 1:
				print "Circle"
                        	arduino.digital[11].write(0)
				#Enable Head Tracking
				#cb1.click()
			elif e.button == 2:
				print "Square"
				if arduino is not None:
                        		arduino.digital[10].write(1)
			elif e.button == 3:
				print "Triangle"
				if arduino is not None:
                        		arduino.digital[10].write(0)
			#sendSignal(2)	

			elif e.button == 4:
				print "White (top left)"
				playSound(input_file_1.value)
			elif e.button == 5:
				print "Black (top right)"
				playSound(input_file_2.value)
			elif e.button == 6:
				print "Back"
			elif e.button == 7:
				print "Start"
			elif e.button == 8:
				print "8"
			elif e.button == 9:
				print "L3"
			elif e.button == 10:
				print "R3"
			
		elif e.type == pygame.locals.JOYBUTTONUP:
			print 'buttonup'
		else:
			gui.event(e) #pass it to the GUI

	im = get_image(camera, headTracking)
	pg_img = pygame.image.frombuffer(im.tostring(), cv.GetSize(im), "RGB")
	screen.fill((0,0,0))
	screen.blit(pg_img, (0,0))
	if camera2 !=None:
		im2=get_image(camera2, False)
		pg2_img = pygame.image.frombuffer(im2.tostring(), cv.GetSize(im2), "RGB")
		screen.blit(pg2_img, (640,240))
			
	gui.paint()
	pygame.display.flip()
	#Note sure why this next line was here by default... perhaps when not
	#using video inputs? Leaving it here just in case I remember why...
	#pygame.time.delay(int(1000 * 1.0/fps))

