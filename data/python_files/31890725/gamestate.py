import pygame
from pygame.locals import *

import random
import itertools

import state
import block
import tetros
import states

from text import Text
from colors import Colors
from engine import Engine
from playfield import Playfield

from countdown import Countdown

class GameState(state.State):
    tetro_classes = (tetros.Leftsnake, tetros.Rightsnake, tetros.Stick,
                     tetros.Square, tetros.Tee, tetros.Leftgun,
                     tetros.Rightgun)
    tetro_colors = (Colors.ORANGE, Colors.RED, Colors.BLUE, Colors.YELLOW)

    def __init__(self):
        super(GameState, self).__init__()
        self.falling_tetro = None
        # nrows should be 22
        self.playfield = Playfield(10, 15)
        self.playfield.rect.centerx = Engine.screenrect.centerx
        self.playfield.rect.bottom = Engine.screenrect.bottom - block.SIZE
        self.members.append(self.playfield)
        #
        # self.kill()
        # # start a countdown, and revive ourself when done
        # self.intro = Countdown(3000, 256, self.revive)
        # self.intro.rect.center = Engine.screenrect.center
        # self.members.append(self.intro)

    def update(self):
        # escape back to main menu
        if Engine.is_just_pressed(K_ESCAPE):
            Engine.switch(states.MainMenuState())
        if not self.alive:
            super(GameState, self).update()
            return
        # update falling tetro
        # X movements
        if self.falling_tetro is not None:
            dx = 0
            #
            if Engine.pressed(K_LEFT):
                dx = -block.SIZE
            if Engine.pressed(K_RIGHT):
                dx = block.SIZE
            #
            if dx != 0:
                self.falling_tetro.move(dx, 0)
                # move it back if any of it's block are now outside the
                # playfield
                for tblock in self.falling_tetro.members:
                    if (tblock.rect.x < self.playfield.rect.x
                            or tblock.rect.right > self.playfield.rect.right):
                        self.falling_tetro.move(-dx, 0)
                        break
                else:
                    # not colliding with "walls" check against well blocks
                    well_blocks = self.playfield.get_well_blocks()
                    for tblock, wblock in itertools.product(
                            self.falling_tetro.members, well_blocks):
                        if tblock.rect.colliderect(wblock.rect):
                            # move it back and land
                            self.falling_tetro.move(-dx, 0)
                            break
                    else:
                        self.falling_tetro.col += 1 if dx > 0 else -1
        # Y movements
        if (self.falling_tetro is not None and self.falling_tetro.dropping):
            self.falling_tetro.drop_delay_counter += Engine.elapsed
            if self.falling_tetro.drop_delay_counter > self.falling_tetro.drop_delay:
                # move and check for collisions
                dy = block.SIZE
                self.falling_tetro.move(0, dy)
                #
                well_blocks = self.playfield.get_well_blocks()
                # collision with well bottom
                for tblock in self.falling_tetro.members:
                    if tblock.rect.bottom > self.playfield.rect.bottom:
                        # move it back and land
                        self.falling_tetro.move(0, -dy)
                        if self.falling_tetro.row < 0:
                            self.kill()
                            return
                        self.falling_tetro.land(self.playfield)
                        self.falling_tetro = None
                        break
                else:
                    # collision with blocks in the well
                    for tblock, wblock in itertools.product(
                            self.falling_tetro.members, well_blocks):
                        if tblock.rect.colliderect(wblock.rect):
                            # move it back and land
                            self.falling_tetro.move(0, -dy)
                            if self.falling_tetro.row < 0:
                                self.kill()
                                return
                            self.falling_tetro.land(self.playfield)
                            self.falling_tetro = None
                            break
                    else:
                        # update row
                        self.falling_tetro.row += 1
                        # reset counter
                        self.falling_tetro.drop_delay_counter = 0
        # new tetro if needed
        if self.falling_tetro is None:
            color = random.choice(self.tetro_colors)
            tetro_cls = random.choice(self.tetro_classes)
            #
            # not giving the startx-y may get the tetromino and playfield out
            # of sync because startx-y default to zero
            startx = self.playfield.rect.x + block.SIZE * 4
            starty = self.playfield.rect.y - block.SIZE * 4
            self.falling_tetro = tetro_cls(color, 
                                           startx=startx, 
                                           starty=starty, 
                                           drop_delay=50)
            #
            self.members.append(self.falling_tetro)
            self.falling_tetro.drop()
        super(GameState, self).update()


