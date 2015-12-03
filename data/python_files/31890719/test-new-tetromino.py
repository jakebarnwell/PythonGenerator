import os
import sys
sys.path.insert(0, os.getcwd())

# ---- below is as it may appear in "real life"
import random
import itertools
from pprint import pprint as pp
import pygame
from pygame.locals import *

import tetris

from tetris.objects.engine import Engine

class TestState(tetris.objects.state.State):

    color = tetris.colors.Colors.RED
    piece = None
    tetromino_classes = itertools.cycle(tetris.objects.tetromino_classes)

    def update(self):
        if Engine.is_just_pressed(K_q):
            Engine.quit()

        if Engine.is_just_pressed(K_n):
            # (n)ext random piece
            if self.piece is not None:
                # remove the old one
                self.members.remove(self.piece)
            self.piece = None

        if self.piece is None:
            self.piece = next(self.tetromino_classes)(self.color)
            self.members.append(self.piece)

        if Engine.is_just_pressed(K_UP):
            # rotate piece
            if self.piece is not None:
                self.piece.rotate("left")

        super(TestState, self).update()


def main():
    NES_RESOLUTION = NES_WIDTH, NES_HEIGHT = (256, 240)
    SCALE = 2
    #
    Engine.init((NES_WIDTH * SCALE, NES_HEIGHT * 2))
    Engine.start(TestState())

if __name__ == "__main__":
    main()

