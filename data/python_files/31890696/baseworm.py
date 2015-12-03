import pygame
from pygame.locals import *
import math
from pprint import pprint as pp
from itertools import imap, izip
from operator import attrgetter

from engine import Engine
from point import Point
import util
import colors

class BaseWorm(object):

    def __init__(self, startpoint, width, length, color, head_color=colors.WHEAT4):
        self.width = width # makes the square "head" (not seen)
        self._length = length # length of worm body
        self.color = color
        self.head_color = head_color
        self.velocity = 0.0
        self.angle = 0.0 # facing right
        self._debug_draw_skeleton = False
        #
        dx = math.cos(self.angle + math.pi) * 2.5 * width
        p = Point(startpoint.x + dx, startpoint.y)
        self.points = [startpoint, p]
        # Silly testing crap
        self._dead = 0
        # following is for animating a little circle around the pointlist
        self._anim_ = 0
        self._anim_advance_timer = 0
        self._anim_points = []

    def update(self):
        # speed testing
        if self.velocity < 3.0:
            self.velocity += 0.025
        #
        nh = self.next_headpoint
        # Self Collision Test
        h = self.headpoint.copy()
        if util.pointinside(nh, self.pointlist):
            self._dead += 1
        #
        self.headpoint = nh

    @property
    def headpoint(self):
        return self.points[-1]

    @headpoint.setter
    def headpoint(self, v):
        self.points[-1] = v

    @property
    def next_headpoint(self):
        p = self.headpoint.copy()
        p.x += math.cos(self.angle) * self.velocity
        p.y += math.sin(self.angle) * self.velocity
        return p

    def steer_to(self, angle):
        """rotate the head to point to a given angle. only valid rotations
        allowed. i.e.: abs(<angle> - <current angle>) in (90, 270)"""
        # Valid angles to turn to
        # self.angle down left-most column
        #
        # diff || K_UP | K_RIGHT | K_DOWN | K_LEFT 
        #      ||   90 |      0  |    270 |    180 
        # -----++------+---------+--------+--------
        #   90 ||    0 |     -90 |    180 |     90 
        #    0 ||  -90 |       0 |   -270 |   -180 
        #  270 || -180 |    -270 |      0 |    -90 
        #  180 ||  -90 |    -180 |     90 |      0 
        #
        # So only 90 and 270 match up to valid moves
        relative_angle = angle - self.angle
        if math.fabs(relative_angle) not in imap(math.radians, (90, 270)):
            return
        # How the head is rotated
        # 1.              2.                    3.                       
        #                                                +--*--+         
        #                                                |  |  |         
        #                                                |  |  |         
        #                                                |  |  |         
        #    +----------+    +----------+--*--+    +-----+  |  |         
        #    |          |    |             |  |    |        |  |         
        #    *----------*    *-------------*  |    *--------*  |         
        #    |          |    |                |    |           |         
        #    +----------+    +----------------+    +-----------+         
        #                                                                
        # The idea is to make a pivot point half width back from the head
        # point and append a new head rotated by rot onto the points.    
        #                                                                
        # This takes into consideration how the "body" (pointlist) of the
        # worm is created, so that it appears to stay solid.             
        #                                                                
        # rotate around a point "back" a distance of self.width
        # point to rotate around
        rotp = self.points[-1]
        rotp.x += math.cos(self.angle + math.pi) * (self.width/2)
        rotp.y += math.sin(self.angle + math.pi) * (self.width/2)
        # the new head point
        newp = rotp.copy()
        newp.x += math.cos(self.angle + relative_angle) * self.width
        newp.y += math.sin(self.angle + relative_angle) * self.width
        self.points.append(newp)
        # commit the new angle
        self.angle = (self.angle + relative_angle) % math.radians(360)

    def _update_length(self):
        while self.length > self._length:
            # keep popping tails until we have a delta to move by that isn't
            # larger than the tail length
            (x1, y1), (x2, y2) = self.points[0:2]
            dx = x1 - x2
            dy = y1 - y2
            # delta length
            dlen = self._length - self.length
            #
            if math.fabs(dlen) > (self.tail_len - self.width):
                # remove tail point
                self.points.pop(0)
                # angle of line just after (towards head) tail
                #(x1, y1), (x2, y2) = self.points[0:2]
                a = util.points_angle(*self.points[0:2])
                #a = math.atan2(x1 - x2, y1 - y2)
                # adjust new tail
                p = self.points[0]
                p.x += math.cos(a) * self.width
                p.y += math.sin(a) * self.width
            else:
                a = math.atan2(dy, dx)
                # new dx, dy
                # what to move x1, y1 by
                dx = math.cos(a) * dlen
                dy = math.sin(a) * dlen
                self.points[0] = Point(x1 + dx, y1 + dy)
                break

    @property
    def tail_len(self):
        "length of tail line (could be the whole worm too"
        return util._dist_line(self.points[0], self.points[1])

    @property
    def pointlist_l(self):
        "left-side list of points"
        return self._pointlist(self.width)

    @property
    def pointlist_r(self):
        "right-side list of points"
        return list(reversed(self._pointlist(-self.width)))

    @property
    def pointlist(self):
        return self.pointlist_l + self.pointlist_r

    def _pointlist(self, w):
        "helper for building the left and right side lists"
        points = []
        p1, p2 = self.points[0:2]
        point = self._rot_points(p1, p2, w)
        points.append(point)

        for i in range(len(self.points) - 2):
            p1, p2, p3 = self.points[i:i+3]
            p = self._intersect_point(p1, p2, p3, w)
            if p:
                points.append(p)

        # last points form a flat head
        point = self._rot_points(self.points[-1], self.points[-2], -w)
        points.append(point)

        return points

    def _rot_points(self, p1, p2, w):
        """find the angle between points p1 and p2, rotate by 90 deg., and
        return a point w distance from p1 at that rotated angle"""
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        dx = x1 - x2
        dy = y1 - y2
        # angle between points rotated 90deg.
        a = math.atan2(dy, dx) + (math.pi / 2)
        # left point
        px = x1 + math.cos(a) * w
        py = y1 + math.sin(a) * w
        return Point(px, py)

    def _intersect_point(self, p1, p2, p3, w):
        """takes three points and ...
        1. finds two lines p1->p2 and p2->p3
        2. shifts lines by width w
        3. returns the points where the shifted lines intersect"""
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

        return util.line_intersect(x1,y1,x2,y2,x2,y2,x3,y3)

    @property
    def length(self):
        "total worm length"
        l = 0.0
        for i, p1 in enumerate(self.points[:-1]):
            p2 = self.points[i+1]
            l += util._dist_line(p1, p2)
        return l

    def _draw_head(self, surf):
        hline = (self.points[-1], self.points[-2])
        hangle = math.atan2(hline[0].y - hline[1].y, hline[0].x - hline[1].x)

        hpoint = hline[0].copy()

        hpoint.x += math.cos(hangle + math.pi) * self.width
        hpoint.y += math.sin(hangle + math.pi) * self.width

        hrect = pygame.Rect(0, 0, self.width, self.width)
        x, y = hpoint.screen
        hrect.centerx = x
        hrect.centery = y

        pygame.draw.rect(surf, self.head_color, hrect)

    def _draw_skeleton(self, surf):
        # draw "skeleton" of worm
        pygame.draw.lines(surf, self.color, False, 
                          [p.screen for p in self.points])
        # draw points in pointlist
        for point in self.points:
            pygame.draw.circle(surf, colors.BLUE, point.screen, 3)

    def _draw_hitboxen(self, surf):
        for rect in self.hitboxen:
            r = rect.copy()
            r.y = Engine.height + -r.y
            pygame.draw.rect(surf, colors.RED, r, 1)

    def _draw_pointlist_order_test(self, surf):
        pointlist = self.pointlist
        if self._anim_advance_timer < 25:
            self._anim_advance_timer += Engine.elapsed
        else:
            self._anim_advance_timer = 0
            self._anim_ += 1
        self._anim_ %= len(pointlist)
        pos = pointlist[self._anim_].screen
        self._anim_points = self._anim_points[1:] + [pos]
        fade_colors = ("BLUE1", "BLUE2", "BLUE3", "BLUE4")
        for i, (c, p) in enumerate(zip(fade_colors, self._anim_points)):
            pygame.draw.circle(surf, getattr(colors, c) , p, i + 5, 1)

    def _draw_dead_num(self, surf):
        rendtext = Engine.font.render(str(self._dead), True, colors.BLACK)
        surf.blit(rendtext, (0,0))

    def _draw_head_pos(self, surf):
        rendtext = Engine.font.render(str(self.headpoint), True, colors.BLACK)
        surf.blit(rendtext, (0,Engine.height - rendtext.get_rect().height))

    def _draw_headpoint(self, surf):
        pygame.draw.circle(surf, colors.RED, self.headpoint.screen, 5)

    def _draw_next_headpoint(self, surf):
        pygame.draw.circle(surf, colors.YELLOW, self.next_headpoint.screen, 5)

    def draw(self, surf):
        # draw polygon (body)
        pygame.draw.polygon(surf, self.color, 
                            [p.screen for p in self.pointlist], 1)
        self._draw_dead_num(surf)
        self._draw_head_pos(surf)
        self._draw_pointlist_order_test(surf)
        self._draw_headpoint(surf)
        self._draw_next_headpoint(surf)
        """
        # draw "head" point
        pygame.draw.circle(surf, self.color, self.points[-1].screen, 5)
        # draw "head"
        self._draw_head(surf)
        #
        if self._debug_draw_skeleton:
            self._draw_skeleton(surf)
        """


