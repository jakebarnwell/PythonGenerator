import os.path
import pygame
import pygame.locals as pg

from pygamemixin import PygameMixin
from image_cache import ImageCache
from level import Level
from player import Player
from mini import Mini
import config


class Game(PygameMixin):
    def __init__(self):
        # Create the window
        self.w, self.h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        PygameMixin.__init__(self, size=(self.w, self.h), fill=((255,255,255)))

        self.IMAGE_CACHE = ImageCache()
        self._setup()
        
    def _setup(self):
        self._load_resources()
        
        level = Level(self.IMAGE_CACHE)
        level.load("test", "test.txt")
        self.background = level.draw()
        self.screen.blit(self.background, (0, 0))
        
        self.sprites = pygame.sprite.RenderUpdates()
        self.player = Player(image=self.IMAGE_CACHE['sprites'], pos=level.player_spawn(), frame=(0, 1))
        self.sprites.add(self.player)
        
        pygame.display.flip()
        
    def _load_resources(self):
        # load all the tilesets and cache them
        self.IMAGE_CACHE.add('sprites', os.path.join(config.TILESET_PATH, 'sprites.png'))

    def update(self, dt):
        self.update_control()
        self.player.update()
        self.sprites.update()

    def draw(self):
        self.sprites.clear(self.screen, self.background)
        dirty = self.sprites.draw(self.screen)
        pygame.display.update(dirty)
        
    def update_control(self):
        if self.key_pressed(pg.K_UP):
            self.walk(0)
        elif self.key_pressed(pg.K_DOWN):
            self.walk(2)
        elif self.key_pressed(pg.K_LEFT):
            self.walk(3)
        elif self.key_pressed(pg.K_RIGHT):
            self.walk(1)
            
    def walk(self, dir):
        x, y = self.player.pos
        self.player.dir = dir
        self.player.walk_animation()
        self.key_pressed(2)
        #if not self.level.is_blocking(x+DX[d], y+DY[d]):
        #    self.player.animation = self.player.walk_animation()
        
if __name__ == '__main__':
    game = Game()
    game.main_loop(fps=100)
