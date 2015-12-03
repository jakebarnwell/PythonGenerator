import pygame

from event_manager import Listener
from entity import Entity
import sprites
import models
import events
import time


class Pygame(Listener):
    """
    Pygame is a Listener class that handles all
    graphics updates with the PyGame library.

    """
    WHITE = (255, 255, 255)
    FONT_NO_ANTIALIASING = 0
    FONT_ANTIALIASING = 1
    WINDOW_SURFACE_FLAGS = 0

    def __init__(self, event_manager, viewport_size, resolution,
                 bitdepth = 32, use_fullscreen = False):
        Listener.__init__(self, event_manager)
        self.em.register(self)

        self.viewport_size = viewport_size
        self.resolution = resolution
        self.use_fullscreen = use_fullscreen
        self.bitdepth = bitdepth

        self._init_display()

    def __del__(self):
        if pygame.display.get_init():
            pygame.display.quit()

    def notify(self, event):
        if isinstance(event, events.Tick):
            self._update_viewport()
        elif isinstance(event, events.PlayerUnitSpawn):
            self._show_player_unit(event.unit)
        elif isinstance(event, events.PlayerUnitHit):
            self._flash_player_unit(event.unit)
        elif isinstance(event, events.PlayerUnitMove):
            self._move_player_unit(event.unit)
        elif isinstance(event, events.PlayerUnitPrimaryFire):
            self._add_bullets(event.bullets)
        elif isinstance(event, events.EnemyUnitSpawn):
            self._add_enemy_unit(event.unit)
        elif isinstance(event, events.EnemyUnitHit):
            self._flash_enemy_unit(event.unit)
        elif isinstance(event, events.EnemyUnitPrimaryFire):
            self._add_enemy_bullets(event.bullets)
        elif isinstance(event, events.EnemyBulletFire):
            self._add_enemy_bullets(event.bullets)
        elif isinstance(event, events.BalanceBarInit):
            self._show_balance_bar(event.hud_item)

    def _init_display(self):
        if not pygame.display.get_init():
            pygame.display.init()
            pygame.font.init()

        # Create "virtual" screen surface (fixed resolution)
        self.window = pygame.Surface(self.viewport_size, self.WINDOW_SURFACE_FLAGS, self.bitdepth)

        fullscreen = 0
        if self.use_fullscreen:
            fullscreen = pygame.FULLSCREEN

        self.real_window = pygame.display.set_mode(self.resolution,
                                                   fullscreen, self.bitdepth)

        # Sprite groups
        self.player_unit_sprites = pygame.sprite.Group()
        self.enemy_unit_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.hud_items_sprites = pygame.sprite.Group()

        # Sprites
        self.player_unit_sprite = sprites.PlayerUnit()
        self.balance_bar_sprite = sprites.BalanceBar()

        # Background
        self.background = pygame.surface.Surface(self.window.get_size())
        self.background.fill((23, 47, 28))

        self.osd_font = pygame.font.SysFont("Courier", 16)
        pygame.display.set_caption("SHMUP PROJECT")
        pygame.mouse.set_visible(False)

        self.old_time = time.time()
        self.start_time = time.time() # for profiling
        self.fps = 0
        self.fps_counter = 0

    def _scale_viewport(self):
        pygame.transform.scale(self.window, self.resolution, self.real_window)

    def _show_player_unit(self, unit):
        self.player_unit_sprites.add(self.player_unit_sprite)
        self._move_player_unit(unit)

    def _move_player_unit(self, unit):
        self.player_unit_sprite.rect.center = unit.pos

    def _add_bullets(self, bullets):
        for bullet in bullets:
            sprite = sprites.Bullet(entity = bullet)
            self.bullet_sprites.add(sprite)

    def _add_enemy_bullets(self, bullets):
        if bullets:
            for bullet in bullets:
                sprite = sprites.EnemyBullet(entity = bullet)
                self.bullet_sprites.add(sprite)

    def _add_enemy_unit(self, unit):
        sprite = sprites.EnemyUnit(entity = unit)
        self.enemy_unit_sprites.add(sprite)

    def _flash_enemy_unit(self, unit):
        for sprite in (s for s in self.enemy_unit_sprites if s.entity == unit):
            sprite.state = sprites.EnemyUnit.FLASHING

    def _flash_player_unit(self, unit):
        self.player_unit_sprite.state = sprites.PlayerUnit.FLASHING

    def _show_balance_bar(self, hud_item):
        self.hud_items_sprites.add(self.balance_bar_sprite)
        self.balance_bar_sprite.rect.center = hud_item.pos

    def _show_debug(self):
        self.fps_counter += 1
        if self.fps > 0:
            text_fps = self.osd_font.render("fps: %d (%.3f ms)" % (self.fps, 1000.0 / self.fps), self.FONT_ANTIALIASING, self.WHITE)
            self.real_window.blit(text_fps, (5, 5))

        text_enemies = self.osd_font.render("enemies: %d" % len(self.enemy_unit_sprites), self.FONT_ANTIALIASING, self.WHITE)
        text_bullets = self.osd_font.render("bullets: %d" % len(self.bullet_sprites), self.FONT_ANTIALIASING, self.WHITE)
        total_entities = len(self.enemy_unit_sprites) + len(self.bullet_sprites)
        text_total_entities = self.osd_font.render("total entities: %d" % total_entities, self.FONT_ANTIALIASING, self.WHITE)
        self.real_window.blit(text_enemies, (5, 20))
        self.real_window.blit(text_bullets, (5, 35))
        self.real_window.blit(text_total_entities, (5, 50))

        if time.time() - self.old_time >= 1:
            self.fps = self.fps_counter
            self.fps_counter = 0
            self.old_time = time.time()
            #print "FPS:", self.fps


    def _update_viewport(self):
        self.player_unit_sprites.update()

        deleted_enemies = [e for e in self.enemy_unit_sprites if e.entity.state == Entity.DELETED]
        self.enemy_unit_sprites.remove(deleted_enemies)
        self.enemy_unit_sprites.update()

        deleted_bullets = [e for e in self.bullet_sprites if e.entity.state == Entity.DELETED]
        self.bullet_sprites.remove(deleted_bullets)
        self.bullet_sprites.update()

        self.window.blit(self.background, self.window.get_rect())

        self.player_unit_sprites.draw(self.window)
        self.enemy_unit_sprites.draw(self.window)
        self.bullet_sprites.draw(self.window)
        self.hud_items_sprites.draw(self.window)

        self._scale_viewport()
        self._show_debug()  # draws to real_window
        pygame.display.update()

        # for profiling
        #if time.time() - self.start_time > 100:
            #self.em.post(events.Quit())

