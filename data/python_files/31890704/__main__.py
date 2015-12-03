import pygame
from pygame.locals import *
import math
import sys
import random
from pprint import pprint as pp

import util
import point
from engine import Engine
from game import Game
from state import State

import worm.skeleton
import worm.playableskeleton
import worm.playablebody
import apple

from text import Text
import colors

SCREEN = pygame.Rect(0,0,640,480)

class IntroState(State):

    def __init__(self):
        super(IntroState, self).__init__()

        self.msg = Text("Press space to start")
        self.msg.y = Engine.height / 2 - self.msg.height / 2
        self.msg.x = Engine.width / 2 - self.msg.width / 2
        self.add(self.msg)

        self.exitmsg = Text("Escape to exit")
        self.exitmsg.x = Engine.width / 2 - self.exitmsg.width / 2
        self.exitmsg.y = self.msg.y + self.msg.height
        self.add(self.exitmsg)

    def update(self):
        super(IntroState, self).update()
        if Engine.just_pressed(K_ESCAPE):
            Engine.post(QUIT)
        elif Engine.just_pressed(K_RETURN):
            self.game.switch_state(PlayState())


class PlayState(State):

    def __init__(self):
        super(PlayState, self).__init__()
        #
        #cls = worm.playableskeleton.PlayableSkeleton
        cls = worm.playablebody.PlayableBody
        self.pbody = cls(position=point.Point(100,100),
                         angle=math.radians(0), 
                         velocity=8.0,
                         length=25.0)
        self.add(self.pbody)
        #
        self.apple = apple.Apple(point.Point(320,240))
        self.add(self.apple)
        self.napple = 0
        #
        self.pause = False

    def collisions(self):
        if self.apple not in self.objects:
            x, y =random.randint(50,500), random.randint(50, 400)
            self.apple = apple.Apple(point.Point(x, y))
            self.add(self.apple)

        x, y = self.pbody.head_.position
        r = pygame.Rect(0, 0, 20, 20)
        r.center = x, y
        if self.apple.rect.colliderect(r):
            self.remove(self.apple)
            self.pbody.length += 25.0

    def update(self):
        if not self.pause:
            super(PlayState, self).update()
            self.collisions()
        #
        if Engine.just_pressed(K_ESCAPE):
            Engine.post(QUIT)
        elif Engine.just_pressed(K_p):
            self.pause = not self.pause


def main():
    Engine.init(SCREEN.width, SCREEN.height, framerate=15)
    game = Game(IntroState())
    game.main()

main()

