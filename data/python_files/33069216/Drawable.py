import operator
from sys import maxint
from math import *

import pygame

from ..LocalFuncs import abst2pixel
from ..Shared.Funcs import rotateAbout
from ..Logging.SingleLog import Log
from ..LocalExceptions import abstract

TAG = "DRAWING"

# Some colours
red    = (239,  39,  19)
green  = ( 70, 111,  32)
blue   = ( 12, 170, 205)
yellow = (234, 234,  45)
white  = (255, 255, 255)
grey   = ( 60,  60,  60)

def drawPitch(screen, w, h):
    # Draw the pitch
    hw = w/2
    hh = h/2
    z = -2
    pygame.draw.polygon(screen, white, ((z,z),(z,h),(w,h),(w,z)), 10)
    pygame.draw.line(screen, white, (hw, 0), (hw, h), 5)
    pygame.draw.circle(screen, white, (hw, hh), 20, 0)

def drawRobot(screen, colour, x, y, a):
    width = 50
    height = 30
    try:
        top = y-(height/2)
        bottom = y+(height/2)
        left = x-(width/2)
        right = x+(width/2)
        x2 = x+(4*(width/2)*cos(float(a)))
        y2 = y+(4*(width/2)*sin(float(a)))
        middle = (x, y)
        points = map( lambda point: rotateAbout(point, middle, a)
                    , [(left, top), (left, bottom), (right, bottom), (right, top)]
                    )
        pygame.draw.polygon(screen, colour, points)
        pygame.draw.line(screen, white, middle, (x2, y2), 2)
        pygame.draw.circle(screen, darken(colour), middle, 10, 0)
    except TypeError:
        # We'll ignore if None happens, it will sometimes
        pass

def drawBall(screen, x, y):
    try:
        pygame.draw.circle(screen, red, (x, y), 5, 0)
    except TypeError:
        # These happen, we ignore them
        pass

def darken((R, G, B)):
    return (R/4, G/4, B/4)

def redraw(screen, bot, ball):
    screen.fill((70, 111, 32))
    ball.draw()
    bot.draw()
    pygame.display.update()

class Drawable:
    def __init__(self):
        abstract()
    def draw(self, screen):
        abstract()

class Cross(Drawable):
    def __init__(self, pos, colour=grey, abst=False, layer='default'):
        self.pos = pos
        self.colour = colour
        self.abst = abst
        self.layer = layer
    def draw(self, screen):
        (x, y) = abst2pixel(self.pos) if self.abst else self.pos
        #Log.d(TAG, "Drawing cross at (%d, %d)" % (x, y))
        pygame.draw.line(screen, self.colour, (x-6, y-6), (x+6, y+6), 2)
        pygame.draw.line(screen, self.colour, (x-6, y+6), (x+6, y-6), 2)

class Circle(Drawable):
    def __init__(self, centre, radius, colour, layer='default', abst=True):
        self.centre = centre
        self.radius = radius
        self.colour = colour
        self.layer  = layer
        self.abst   = abst 
    def draw(self, screen):
        (x, y) = abst2pixel(self.centre) if self.abst else self.centre
        pygame.draw.circle(screen, self.colour, (x,y), abst2pixel(self.radius, dimensions=True), 2)

class Line(Drawable):
    def __init__(self, pos1, pos2, colour=grey, width=4, layer='default', abst=False):
        self.pos1, self.pos2 = pos1, pos2
        self.colour = colour
        self.layer = layer
        self.abst = abst
        self.width = width
    def draw(self, screen):
        (x1, y1) = abst2pixel(self.pos1) if self.abst else self.pos1
        (x2, y2) = abst2pixel(self.pos2) if self.abst else self.pos2
        pygame.draw.line(screen, self.colour, (x1, y1), (x2, y2), self.width)

class Path(Drawable):
    def __init__(self, points, colour=grey, width=4, layer='default', abst=False):
        self.points = points
        self.colour = colour
        self.width = width
        self.layer = layer
        self.abst = abst
    def draw(self, screen):
        prevPoint = None
        for point in self.points:
            if not prevPoint:
                prevPoint = point
            pygame.draw.line(screen, self.colour, prevPoint, point, self.width)
            prevPoint = point

