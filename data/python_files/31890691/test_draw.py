import pygame
from pygame.locals import *
from pprint import pprint as pp
import math
import random
import os
import sys

SCREEN = pygame.Rect(0,0,640,480)

# pull colors in to module, uppercased
from pygame.colordict import THECOLORS
globals().update(dict((k.upper(),v) for k,v in THECOLORS.iteritems()))
del THECOLORS

class Point(object):
    "Cartesian 2d point"
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    @property
    def screen(self):
        return (int(self.x), int(SCREEN.bottom + -self.y))


def line_intersect(x1,y1,x2,y2,x3,y3,x4,y4):
    # denominator
    d = ((y4-y3)*(x2-x1)-(x4-x3)*(y2-y1))
    if d == 0:
        # parallel
        return
    ua = ((x4-x3)*(y1-y3)-(y4-y3)*(x1-x3)) / d

    x = x1 + ua * (x2 - x1)
    y = y1 + ua * (y2 - y1)

    return Point(x, y)

def pointlist(points, w=10):
    points_l = []
    points_r = []

    def _rot_points(p1, p2, w):
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        dx = x1 - x2
        dy = y1 - y2
        # angle between points rotated 90deg.
        a = math.atan2(dy, dx) + (math.pi / 2)
        # left point
        px = x1 + math.cos(a) * w
        py = y1 + math.sin(a) * w
        lp = Point(px, py)
        # right point
        px = x1 + math.cos(a) * -w
        py = y1 + math.sin(a) * -w
        rp = Point(px, py)
        return lp, rp

    # first points form a flat tail
    lp, rp = _rot_points(points[0], points[1], w)
    points_l.append(lp)
    points_r.insert(0, rp)

    npoints = len(points)

    def _intersect_point(p1, p2, p3, w):
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        x3, y3 = p3.x, p3.y

        # line 1 angle rotated 90 degrees
        a = math.atan2(y1 - y2, x1 - x2) + (math.pi / 2)

        x1 += math.cos(a) * w
        y1 += math.sin(a) * w
        x2 += math.cos(a) * w
        y2 += math.sin(a) * w

        # line 2 angle rotated 90 degrees
        a = math.atan2(y2 - y3, x2 - x3) + (math.pi / 2)

        x2 += math.cos(a) * w
        y2 += math.sin(a) * w
        x3 += math.cos(a) * w
        y3 += math.sin(a) * w

        return line_intersect(x1,y1,x2,y2,x2,y2,x3,y3)

    for i in range(npoints - 2):
        p1, p2, p3 = points[i:i+3]
        points_l.append(_intersect_point(p1, p2, p3, w))
        points_r.insert(0, _intersect_point(p1, p2, p3, -w))

    # last points form a flat head
    lp, rp = _rot_points(points[-1], points[-2], -w)
    points_l.append(lp)
    points_r.insert(0, rp)

    return points_l + points_r

def main():
    os.environ["SDL_VIDEO_CENTERED"] = "1"
    npass, nfail = pygame.init()
    screen = pygame.display.set_mode(SCREEN.size)
    clock = pygame.time.Clock()
    framerate = 60
    #
    points = []
    running = True
    while running:
        #
        elapsed = clock.tick(framerate)
        #
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.event.post(pygame.event.Event(QUIT))
                elif event.key == K_r:
                    points = randompoints()
                else:
                    # repost KEYDOWN events
                    pygame.event.post(event)
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:
                    x, y = event.pos
                    y = SCREEN.bottom + -y
                    p = Point(x, y)
                    points.append(p)
        # clear screen
        screen.fill(WHITE)
        # draw
        # draw test
        if len(points) > 1:
            pygame.draw.lines(screen, BLACK, True, 
                              [p.screen for p in pointlist(points)])
            # skeleton
            pygame.draw.lines(screen, RED, False, 
                              [p.screen for p in points])
        # 
        pygame.display.flip()

if __name__ == "__main__":
    main()

