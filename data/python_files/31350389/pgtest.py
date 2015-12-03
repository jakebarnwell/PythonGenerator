# Import a library of functions called 'pygame'
import pygame
from pygame.locals import *

import socket # We need to communicate
import sys
import re     # We're gonna parse strings
from drawable import *
from local_exceptions import *
from VisionClient import *

def drawAll():
    draws['d'].draw()
    draws['y'].draw()
    draws['b'].draw()
    draws['r'].draw()


HOST = sys.argv[2] if len(sys.argv)>2 else ''
PORT = int(sys.argv[1]) if len(sys.argv)>1 else 31410           # The same port as used by the server

vc = VisionClient(HOST, PORT)
clock = pygame.time.Clock()

clock.tick(10)
size = vc.getDimensions()
(w,h) = size

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
print vc.isDone()
try:
    while not done and not vc.isDone():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                done = True
                print "User exited"
        all = vc.getAll()
        for type in all:
            draws[type].setPos(all[type])

        screen.fill(green)
        drawAll()
        pygame.display.update()

except KeyboardInterrupt:
    sys.stdout.write("\rUser exited\n")
    sys.stdout.flush()

vc.stop()
