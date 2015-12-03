# Import a library of functions called 'pygame'
import pygame
from pygame.locals import *

import socket # We need to communicate
import sys
import re     # We're gonna parse strings
import time
from drawable import *
from VisionClient import *

def drawAll():
    draws['d'].draw()
    draws['y'].draw()
    draws['b'].draw()
    draws['r'].draw()


HOST = sys.argv[2] if len(sys.argv)>2 else ''
PORT = int(sys.argv[1]) if len(sys.argv)>1 else 31410           # The same port as used by the server

clock = pygame.time.Clock()

vc = VisionClient(HOST, PORT)
(w,h) = vc.getDimensions()
size = (w,h)

# Initialize the game engine
pygame.init()

# Define the colors we will use in RGB format
black  = (  0,  0,  0)
white  = (255,255,255)
blue   = ( 12,170,205)
green  = ( 70,111, 32)
red    = (239, 39, 19)
yellow = (234,234, 45)

# Set the height and width of the screen
screen=pygame.display.set_mode(size)


draws = dict()
draws['d'] = Pitch(w, h, white, screen)
draws['r'] = Ball(None, None, red, screen)
draws['y'] = Robot(None, None, yellow, screen)
draws['b'] = Robot(None, None, blue, screen)

pygame.display.set_caption("Herp Derp")

done = False
try:
    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                done = True
                print "User exited"
        (bx, by, ba) = vc.getBlueBot()
        (yx, yy, ya) = vc.getYellowBot()
        (ballx, bally) = vc.getBall()
        draws['r'].setPos(ballx, bally)
        draws['y'].setPos(yx, yy)
        draws['b'].setPos(bx, by)
        draws['b'].setAngle(ba)
        #print ba
        #draws['b'].turn(angleBetween(draws['b'], draws['r']))
        draws['y'].setAngle(ya)


        screen.fill(green)
        drawAll()
        pygame.display.update()

except KeyboardInterrupt:
    sys.stdout.write("\rUser exited\n")
    sys.stdout.flush()

vc.stop()
