import pygame
from pygame.locals import *
import math
import itertools
from pprint import pprint as pp

import colors
import skeleton
import util

class Body(skeleton.Skeleton):

    width = 20.0

    @property
    def min_tail_length(self):
        return self.width

    _min_segment_length = 10.0

    def kill(self):
        print "Killed"

    def update(self):
        nexthead = self.head_.position.move(self.head_.angle,
                                            self.head_.velocity)
        if util.pointinside(nexthead, self.polygon_pointlist):
            self.kill()
        super(Body, self).update()

    def _draw_debug(self, surf):
        # draw skeleton
        super(Body, self).draw(surf)
        #
        self._draw_body(surf, 1)

    def _draw_body(self, surf, width=0):
        polypoints = self.polygon_pointlist
        screen_plist = [p.screen for p in polypoints]
        color = self.head_.color
        pygame.draw.polygon(surf, color, screen_plist, width)

    def _draw(self, surf):
        super(Body, self).draw(surf)
        #
        self._draw_body(surf)

    draw = _draw_debug

    @property
    def polygon_pointlist(self):
        points_l = []
        points_r = []
        distance = self.width / 2
        points = self.points

        def _rot_line((p1, p2), angle_delta, d):
            angle = util.points_angle(p1, p2) + angle_delta
            return (p1.move(angle, d), p2.move(angle, d))

        def _shift_line_left(line, d):
            angledelta = math.pi / 2
            return _rot_line(line, angledelta, d)

        def _shift_line_right(line, d):
            angledelta = -(math.pi / 2)
            return _rot_line(line, angledelta, d)

        # start at tail
        p1, _ = _shift_line_left(self.tail_segment, distance)
        points_l.append(p1)

        p1, _ = _shift_line_right(self.tail_segment, distance)
        points_r.append(p1)

        def _intersection_of_shift_left(line1, line2, d):
            l1 = _shift_line_left(line1, d)
            l2 = _shift_line_left(line2, d)
            return util.line_intersect_grouped(l1, l2)

        def _intersection_of_shift_right(line1, line2, d):
            l1 = _shift_line_right(line1, d)
            l2 = _shift_line_right(line2, d)
            return util.line_intersect_grouped(l1, l2)

        for (p1, p2, p3) in util.consume_list(3, points):
            l1 = (p1, p2)
            l2 = (p2, p3)
            #
            intersection_point = _intersection_of_shift_left(l1, l2, distance)
            if intersection_point:
                points_l.append(intersection_point)
            #
            intersection_point = _intersection_of_shift_right(l1, l2, distance)
            if intersection_point:
                points_r.append(intersection_point)

        # end at head
        _, p2 = _shift_line_left(self.head_segment, distance)
        points_l.append(p2)

        _, p2 = _shift_line_right(self.head_segment, distance)
        points_r.append(p2)

        return points_l + list(reversed(points_r))


