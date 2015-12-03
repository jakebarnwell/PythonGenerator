import pygame
from pygame.locals import *
import itertools
import math
from pprint import pprint as pp

import head
import util

class Skeleton(object):

    min_tail_length = 0.0
    
    def __init__(self, length=None, **kwargs):
        if length is None:
            length = 100.0
        self.length = length # length to constrain worm
        self.head_ = head.Head(**kwargs)
        #
        self._bodypoints = [self.head_.position.move(self.head_.angle, -self.length)]

    def steer_head(self, angle_delta):
        self._bodypoints.append(self.head_.position.copy())
        self.head_.angle += angle_delta

    def update(self):
        # this moves the head
        self.head_.update()
        # correct the length if necessary
        self._update_length()

    def _update_length(self):
        if self.tail_length < self.min_tail_length:
            self._bodypoints.pop(0)

        while (self.segments_length_sum > self.length):
            # distance to adjust tail so that the worm is the correct length
            correction_length = self.length - self.segments_length_sum
            if math.fabs(correction_length) < 0.001:
                # get out of here with that, come back when you got some
                # correctin' to do!
                break
            # the direction to correct in
            correction_angle = util.points_angle(*self.tail_segment)
            # is there enough tail to make that correction?
            if math.fabs(correction_length) > self.tail_length:
                self._bodypoints.pop(0)
            else:
                self.tail_point = self.tail_point.move(correction_angle,
                                                       correction_length)

    def draw(self, surf):
        self._draw_segment_lines(surf)

    def _draw_segment_lines(self, surf):
        screen_points = [p.screen for p in self.points]
        closed = False
        return pygame.draw.lines(surf, self.head_.color, closed, screen_points)

    @property
    def tail_point(self):
        return self._bodypoints[0]
    @tail_point.setter
    def tail_point(self, v):
        self._bodypoints[0] = v

    @property
    def tail_length(self):
        "return the length of the tail segment"
        p1, p2 = self.tail_segment
        return util._dist_line(p1, p2)

    @property
    def head_segment(self):
        return self.points[-2:]

    @property
    def tail_segment(self):
        "return the points making up the tail segment"
        if len(self._bodypoints) == 1:
            return self._bodypoints + [self.head_.position]
        else:
            return self.points[0:2]

    @property
    def segments_length_sum(self):
        return sum(itertools.starmap(util._dist_line, self.segment_points))

    @property
    def segment_points(self):
        "return a list of segment point tuples from tail to head"
        points = self.points
        return [(p1, points[i+1]) for i, p1 in enumerate(points[:-1])]

    @property
    def points(self):
        """return a list of all the points including the head position in this
        worm"""
        return self._bodypoints + [self.head_.position]


