import sys
import pygame
import data
from pygame.locals import *
from pygame.sprite import Sprite
from pygame.time import Clock
from pygame import Surface
from pygame import Rect


class FrameSet(object):
    
    __frames = dict()
    
    @staticmethod
    def load_framesets(filename):
        file = data.load(filename, 'r')
        for line in file:
            line = line.split('#')[0].strip()
            if line.startswith('@'):
                values = line.split(';')
                key = values[0].strip()[1:]
                image = values[1].strip().replace('"', '')
                cols = int(values[2])
                rows = int(values[3])
                margin = int(values[4])
                spacing = int(values[5])
                map = FrameSet(image, cols, rows, margin, spacing)
                FrameSet.__frames[key] = map
    
    @staticmethod
    def get_frameset(map_key):
        if map_key in FrameSet.__frames:
            return FrameSet.__frames[map_key]
        else:
            return None
        
    def __init__(self, filename, cols, rows=1, margin=0, spacing=0):
        pos = filename.rfind('.')
        name = filename[:pos]
        ext = filename[pos:]
        self.__surface = data.load_image(name, ext)
        self.__frames = self.__get_frames(cols, rows, margin, spacing)
    
    def __get_frames(self, cols, rows, margin, spacing):
        frames = []
        width = self.__surface.get_width()
        height = self.__surface.get_height()
        frame_width = (width - 2*margin - (cols-1)*spacing) / cols
        frame_height = (height - 2*margin - (rows-1)*spacing) / rows
        top = margin
        for y in range(rows):
            left = margin
            for x in range(cols):
                rect = Rect(left, top, frame_width, frame_height)
                subsurface = self.__surface.subsurface(rect)
                frame = Frame(subsurface)
                frames.append(frame)
                left = left + frame_width + spacing 
            top = top + frame_height + spacing
        return frames
    
    def get_frame(self, index):
        return self.__frames[index]
    
    def get_frames(self, range=None, transition_draw=None):
        if range == None:
            range = range(len(self.__frames))
        frames = []
        for i in range:
            frame = self.__frames[i]
            if transition_draw:
                frame = Frame(frame.surface, transition_draw)
            frames.append(frame)
        return frames

class Anchor:
    NONE = 0
    TOP_LEFT = 1
    CENTER = 2

class Frame(object):
    
    def __init__(self, surface=None, draw=None, anchor=Anchor.CENTER):
        self.surface = surface
        self.rect = Rect(0, 0, surface.get_width(), surface.get_height())
        self.angle = 0
        self.anchor = anchor
        self.draw = draw if draw else self.__surface_draw

    def set_anchor(self, anchor):
        self.anchor = anchor
    
    def __surface_draw(self, surface, x, y):
        if self.anchor == Anchor.CENTER:
            self.rect.center = (x, y)
        elif self.anchor == Anchor.TOP_LEFT:
            self.rect.x = x
            self.rect.y = y
        surface.blit(self.surface, self.rect)


class Anim(object):
    
    __anims = dict()
    
    @staticmethod
    def load_anims(filename):
        file = data.load(filename, 'r')
        anim = None
        for line in file:
            line = line.split('#')[0].strip()
            if line.startswith('@'):
                values = line.split(';')
                key = values[0].strip()[1:]
                repeat = values[1].strip().lower() in ('repeat', 'loop', 'true', '1')
                anim = Anim(repeat=repeat)
                Anim.__anims[key] = anim
            elif line and key:
                values = line.split(';')
                FrameSet_key = values[0].strip()
                frame_index = int(values[1])
                duration = int(values[2])
                filter_list = values[3:]
                frame_map = FrameSet.get_frameset(FrameSet_key)
                frame = frame_map.get_frame(frame_index)
                for filter in filter_list:
                    if filter.strip():
                        frame = Anim.transform(frame, filter)
                anim.add_frame(frame, duration)
    
    @staticmethod
    def get_anim(anim_key):
        if anim_key in Anim.__anims:
            return Anim.__anims[anim_key]
        else:
            return None
    
    @staticmethod
    def transform(frame, filter):
        tmp = filter.split('(', 1)
        filter_name = tmp[0].strip()
        param_list = tmp[1].split(')', 1)[0]
        params = param_list.split(',')
        for i in range(len(params)):
            params[i] = params[i].strip()
        new_surface = None
        if filter_name == 'FLIP':
            xbool, ybool = bool(int(params[0])), bool(int(params[1]))
            new_surface = pygame.transform.flip(frame.surface, xbool, ybool)
        elif filter_name == 'SCALE':
            new_size = (int(params[0]), int(params[1]))
            new_surface = pygame.transform.scale(frame.surface, new_size)
        elif filter_name == 'SCALE2X':
            new_surface = pygame.transform.scale2x(frame.surface)
        elif filter_name == 'SCALESM':
            new_size = (int(params[0]), int(params[1]))
            new_surface = pygame.transform.smoothscale(frame.surface, new_size)
        elif filter_name == 'ROTATE':
            angle = float(params[0])
            new_surface = pygame.transform.rotate(frame.surface, angle)
        elif filter_name == 'ROTOZOOM':
            angle, scale = float(params[0]), float(params[1])
            new_surface = pygame.transform.rotozoom(frame.surface, angle, scale)
        else:
            return None
        new_frame = Frame(new_surface)
        return new_frame
    
    def __init__(self, frames=None, duration=10, repeat=False):
        self.__frames = []
        self.__durations = []
        self.__current = 0
        self.__repeat = repeat
        self.__dt = 0
        self.__playing = False
        self.__visible = False
        if frames:
            for i in range(len(frames)):
                self.add_frame(frames[i], duration)
    
    def add_frame(self, frame, duration):
        self.__frames.append(frame)
        self.__durations.append(duration)
    
    def set_repeat(self, repeat):
        self.__repeat = repeat
    
    def draw(self, surface, x, y):
        frame = self.get_frame()
        if frame:
            frame.draw(surface, x, y)
        
    def update(self, dt):
        if not self.__playing: return
        dt += self.__dt
        while dt >= self.__durations[self.__current] and self.__durations[self.__current] > 0:
            dt -= self.__durations[self.__current]
            if self.__current == len(self.__frames) - 1:
                if self.__repeat:
                    self.__current = 0
                else:
                    self.__playing = False
                    break
            else:
                self.__current += 1
            self.__dt = dt
        self.__dt = dt
    
    def is_playing(self):
        return self.__playing
    
    def is_over(self):
        is_last_frame = (self.__current == len(self.__frames) - 1)
        frame_time_passed = self.__dt >= self.__durations[self.__current]
        return (not self.__playing and is_last_frame and frame_time_passed)
    
    def play(self):
        self.__playing = True
        return self
    
    def pause(self):
        self.__playing = False
        return self
    
    def stop(self):
        self.__playing = False
        self.__current = 0
        self.__dt = 0
        return self
    
    def show(self):
        self.__visible = True
        return self
        
    def hide(self):
        self.__visible = False
        return self
    
    def is_visible(self):
        return self.__visible
    
    def seek(self, frame_index):
        self.__playing = False
        self.__current = frame_index
        self.__dt = 0
        return self
    
    def reverse(self):
        anim = Anim()
        anim.set_repeat(True)
        for i in range(len(self.__frames) - 1, -1, -1):
            anim.add_frame(self.__frames[i], self.__durations[i])
        return anim
    
    def get_frame(self, index=None):
        if index == None:
            if not self.__visible:
                return None
            else:
                index = self.__current
        if index in range(len(self.__frames)):
            return self.__frames[index]
        else:
            return None
    
    def get_next_frame(self):
        index = self.__current + 1
        return self.get_frame(index)


class Controller(object):
    
    keydown = []
    keyup = []
    
    @staticmethod
    def update_keyboard():
        Controller.keydown = pygame.event.get(KEYDOWN)
        Controller.keyup = pygame.event.get(KEYUP)
    
    def __init__(self):
        self.dt = 0
        
    def update(self, entity, dt):
        return None
    
    def key_pressed(self, key):
        keys_pressed = pygame.key.get_pressed()
        return keys_pressed[key]

    def any_key_pressed(self):
        return len(Controller.keydown) > 0


class Entity(object):
    
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
    
    def draw(self, surface, x=0, y=0):
        print "Override me!!!"
    
    def update(self, dt):
        print "Override me!!!"
    
    def get_pos(self):
        return self.x, self.y
    
    def set_pos(self, x, y):
        self.x, self.y = (x, y)

    def translate(self, offsx, offsy):
        self.x += offsx
        self.y += offsy


class Actor(Entity):
    
    def __init__(self, controller=None, x=0, y=0):
        super(Actor, self).__init__(x, y)
        self.__anims = []
        self.__positions = []
        self.__state_flow = {}
        self.__state = None
        self.__update_anims_dt = False
        self.__controller = controller
        self.__commands = []
        
    def add_anim(self, anim, offs_x=0, offs_y=0):
        offs = (offs_x, offs_y)
        self.__anims.append(anim)
        self.__positions.append(offs)
    
    def draw(self, surface, x=0, y=0):
        for i in range(len(self.__anims)):
            anim = self.__anims[i]
            if anim.is_visible():
                anim_x, anim_y = self.__positions[i]
                anim.draw(surface, self.x + anim_x, self.y + anim_y)
    
    def update(self, dt):
        self.__update_controller(dt)
        self.__update_state_flow()
        self.update_state(self.__state, dt)
        self.__update_anims(dt)
        
    def __update_controller(self, dt):
        self.__commands = []
        if self.__controller:
            self.__commands = self.__controller.update(self, dt)
        
    def __update_state_flow(self):
        if self.__commands:
            for cmd in self.__commands:
                if self.__state in self.__state_flow:
                    flow = self.__state_flow[self.__state]
                    if cmd in flow:
                        state, params = flow[cmd]
                        if state != self.__state:
                            self.set_state(state, params)
        
    def __update_anims(self, dt):
        if self.__update_anims_dt:
            for anim in self.__anims:
                anim.update(dt)
        self.__update_anims_dt = True
    
    def update_state(self, state, dt):
        print "override me!!! Actor.update_state", state, dt
    
    def enter_state(self, state, prev_state, params=None):
        print "override me!!! Actor.enter_state", state, prev_state, params
    
    def exit_state(self, state, next_state, params=None):
        print "override me!!! Actor.exit_state", state, next_state, params
    
    def get_state(self):
        return self.__state
    
    def set_state(self, state, params=None):
        if self.__state != None:
            self.exit_state(self.__state, state, params)
        if state != None:
            self.enter_state(state, self.__state, params)
            self.__update_anims_dt = False
        self.__state = state
    
    def define_state_flow(self, src_states, command, dest_state, params=None):
        if not isinstance(src_states, (list, tuple)):
            src_states = [src_states]
        for state in src_states:
            if state not in self.__state_flow:
                self.__state_flow[state] = {}
            self.__state_flow[state][command] = dest_state, params
    
    def get_anim(self, index):
        return self.__anims[index]


class Layer(Entity):

    @classmethod
    def create_from_file(cls, filename, x=0, y=0, w=None, h=None, anchor=Anchor.TOP_LEFT):
        s = data.load_image(filename)
        sw = s.get_width()
        sh = s.get_height()
        sw = w or sw
        sh = h or sh

        if sw != s.get_width() or sh != s.get_height():
            s = pygame.transform.smoothscale(s, (sw, sh))
        f = Frame(s)
        return cls(f, x, y, anchor)
    
    def __init__(self, frame, x=0, y=0, anchor=Anchor.TOP_LEFT):
        super(Layer, self).__init__(x, y)
        self.frame = frame
        self.frame.set_anchor(anchor)
    
    def draw(self, surface, x=0, y=0):
        self.frame.draw(surface, x + self.x, y + self.y)
    
    def update(self, dt):
        pass


class EntityGroup(Entity):
    
    def __init__(self, x=0, y=0):
        super(EntityGroup, self).__init__(x, y)
        self.__entities = []
    
    def draw(self, surface, x=0, y=0):
        for entity in self.__entities:
            entity.draw(surface, x + self.x, y + self.y)
    
    def update(self, dt):
        for entity in self.__entities:
            entity.update(dt)
    
    def add(self, entity):
        self.__entities.append(entity)
