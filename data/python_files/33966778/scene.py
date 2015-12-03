import pcapy
import impacket.ImpactDecoder
import pyglet
from pyglet.gl import *
from pyglet import clock
from OpenGL.GLUT import * #<==Needed for GLUT calls

import socket
import threading
import time, random
from math import sqrt, fabs

import morton_ip_map, ipv4_address_space
from network import Network, Node, Route, Packet
import processes

def project_ip(ip):
    """Project into (-0.5..0.5) in 3D"""
    digits = ip.split('.')
    digits = digits[:2]+digits[3:4]+digits[2:3]
    n = sum(n*(256**(3-i)) for i,n in enumerate(
        map(int, digits)))
    x,y,z = morton_ip_map.deinterleave3(n)
    N = 1024.0
    c = map(lambda v: (v-N/2)/N, (x,y,z))
    return c

def _n(x,maxx): ## normalize
    return (2.0 * x - float(maxx)) / float(maxx)

def _l(x,minn=-1.0, maxx=1.0): ## thresholds
    return max(minn, min(maxx, x))

def _ease(minn, maxx, p): ## p is 0.0-1.0
    return (minn + (maxx-minn)*p)

def _interp(a,b,p, ease=_ease): ## a->b linear interpolation
     return [a[i] + (b[i]-a[i])*p \
             for i in range(len(a))]


class GLElement(object):
    pass

class GLNode(GLElement):
    def __init__(self, node):
        self.node = node

    def get_size(self):
        return _ease(2, 20, 1-_l(self.node.get_contact_age(), 0, 5)/5)

    def get_active_size(self):
        return _ease(2, 40, 1-_l(self.node.get_activation_age(), 0, 5)/5)

    def draw(self):
        glPointSize(self.get_size())
        glBegin(GL_POINTS)
        glColor4f(0.5, 0.5, 0.5, 0.4)
        glVertex3f(*self.get_coords())
        glEnd()
        
        glPointSize(self.get_active_size())
        glBegin(GL_POINTS)
        glColor4f(0.0, 0.5, 1.0, 0.5)
        glVertex3f(*self.get_coords())
        glEnd()

    def get_coords(self):
        return project_ip(self.node.ip)

class GLRoute(GLElement):
    def __init__(self, route):
        self.route = route
        
    def get_size(self):
        return _ease(0.1, 5, 1 - _l(self.route.get_activation_age(), 0, 5)/5)

    def draw(self):
        glLineWidth(self.get_size())
        glBegin(GL_LINES)
        glColor4f(0.8, 0.8, 0.1, 0.3)
        src_coords = project_ip(self.route.src.ip)
        dst_coords = project_ip(self.route.dst.ip)
        glVertex3f(*src_coords)
        glVertex3f(*dst_coords)
        glEnd()

        for packet in self.route.packets:
            if not self.route.is_active(packet): continue
            glPushMatrix()
            glTranslatef(*_interp(
                src_coords, dst_coords,
                self.route.get_progress(packet)))
            GLPacket(packet).draw()
            glPopMatrix()
                

class GLPacket(GLElement):
    def __init__(self, packet):
        self.packet = packet

    def get_size(self):
        return max(2.0, _ease(2, 50, self.packet.get_length()/5000.0))

    def get_color(self):
        if self.packet.is_http():
            return (0.0, 1.0, 0.8, 0.8)
        else:
            return (1.0, 1.0, 1.0, 0.8)

    def draw(self):
        glPointSize(self.get_size())
        glBegin(GL_POINTS)
        glColor4f(*self.get_color())
        glVertex3f(0,0,00)
        glEnd()

class World(object):
    def __init__(self, network):
        self.network = network

    def draw(self):
        glClear(GL_COLOR_BUFFER_BIT)
        for node in self.network.get_active_nodes():
            GLNode(node).draw()
        for route in self.network.get_active_routes():
            GLRoute(route).draw()
        self.draw_axis()

    def draw_axis(self):
        glBegin(GL_QUADS)
        glColor4f(1.0, 0.5, 0.5, 0.1)
        glVertex3f(-0.5, -0.5, 0)
        glVertex3f(-0.5, 0.5, 0)
        glVertex3f(0.5, 0.5, 0)
        glVertex3f(0.5, -0.5, 0)

        glColor4f(0.5, 1.0, 0.5, 0.1)
        glVertex3f(0.0, -0.5, -0.5)
        glVertex3f(0.0, -0.5, 0.5)
        glVertex3f(0.0, 0.5, 0.5)
        glVertex3f(0.0, 0.5, -0.5)

        glColor4f(0.5, 0.5, 1.0, 0.1)
        glVertex3f(-0.5, 0.0, -0.5)
        glVertex3f(-0.5, 0.0, 0.5)
        glVertex3f(0.5, 0.0, 0.5)
        glVertex3f(0.5, 0.0, -0.5)

        glEnd()

        glLineWidth(1.0)
        glBegin(GL_LINES)
        glColor4f(1.0, 1.0, 1.0, 0.1)
        
        glVertex3f(-0.5, 0.0, 0)
        glVertex3f(0.5, 0.0, 0)
        glVertex3f(0.0,-0.5, 0.0)
        glVertex3f(0.0,0.5, 0.0)
        glVertex3f(0.0,0.0,-0.5)
        glVertex3f(0.0,0.0,0.5)
        
        glEnd()
        


from trackball_camera import TrackballCamera

class Camera(object):

    def __init__(self, win, zoom=1.0, phi=0, theta=0, nv=0.2):
        self.win = win
        self.tbcam = TrackballCamera(20.0)
        self.offset_x = 0
        self.offset_y = 0
        self.offset_z = 0
        
        self.matrix = (c_double*16)()
        self.pmatrix = (c_double*16)()
        self.viewport = (c_int*4)()

    def __repr__(self):
        return "on"
        d = self.tbcam.__dict__.copy()
        return ", ".join('%s:%s' % (k,v) for k,v in d.items())

    def worldProjection(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective( 
            40.0,                            # Field Of View
            float(self.win.width)/float(self.win.height),  # aspect ratio
            0.001,                             # z near
            100.0)                           # z far
        glTranslatef(self.offset_x, self.offset_y, self.offset_z)
        self.tbcam.update_modelview()
        glScalef(10.0, 10.0, 10.0)

        ## save for project/unproject
        glGetDoublev(GL_MODELVIEW_MATRIX, self.matrix)
        glGetDoublev(GL_PROJECTION_MATRIX, self.pmatrix)
        glGetIntegerv(GL_VIEWPORT, self.viewport)        

    def hudProjection(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, self.win.width, 0, self.win.height)

    def project(self, c):
        x,y,z = c_double(),c_double(),c_double()
        gluProject(c[0], c[1], c[2],
                   self.matrix, self.pmatrix, self.viewport,
                   x, y, z)
        return (x.value, y.value)

    def get_zoom_factor(self):
        return self.tbcam.cam_eye[2]


class Hud(object):

    ## class _Names():
    ##     def __init__(self, count=10, delay=3):
    ##         self.count = count
    ##         self.delay = delay
    ##         self._new()

    ##     def _new(self):
    ##         self._names = random.sample(ipv4_address_space.ipv4_address_space, self.count)
    ##         self._last = time.time()

    ##     def __iter__(self):
    ##         if time.time() - self._last >self.delay:
    ##             self._new()
    ##         return iter(self._names)

    def __init__(self, app):
        self.helv = pyglet.font.load('Helvetica', 10)
        self.helv20 = pyglet.font.load('Helvetica', 20)
        self.fps = clock.ClockDisplay()
        self.app = app

    def draw(self):
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        self.fps.draw()

        text = pyglet.font.Text(
            self.helv,
            'Nodes: %d Routes: %d packets: %d active' % (
                len(self.app.network.nodes),
                len(self.app.network.routes),
                len(self.app.network.get_active_packets()),
                ),
            x=0,
            y=20,
            color=(1, 1, 1, 0.5),
        )
        text.draw()
        self.draw_names()
        self.draw_nodes()
        self.draw_routes()


    def draw_routes(self):
        processes.open_connections_manager.snapshot()
        for route in self.app.network.get_active_routes():
            names = set()
            for p in route.packets:
                process = processes.open_connections_manager.get_emitter_process(p)
                if process:
                    names.add(process['name'])
            if names:
                ## TODO: pass through GLRoute (and put interp() there)
                c1 = GLNode(route.src).get_coords()
                c2 = GLNode(route.dst).get_coords()
                c = _interp(c1, c2, 0.8)

                ### TODO copypaste
                x,y = self.app.camera.project(c)
                label = u'%s' % ",".join(names)
                _cached_text_key = (label,x,y)
                if getattr(route, '_cached_text_key', None) == _cached_text_key:
                    text = route._cached_text
                else:
                    text = pyglet.font.Text(
                        self.helv,
                        label,
                        x=x, y=y,
                        halign=pyglet.font.Text.CENTER,
                        valign=pyglet.font.Text.CENTER,
                        color=(0.8, 0.8, 0.4, 0.7))
                    route._cached_text = text
                    route._cached_text_key = _cached_text_key
                text.draw()


    def draw_nodes(self):
        for node in self.app.network.get_active_nodes():
            c = GLNode(node).get_coords()
            x,y = self.app.camera.project(c)
            label = u'%s' % node
            _cached_text_key = (label,x,y)
            if getattr(node, '_cached_text_key', None) == _cached_text_key:
                text = node._cached_text
            else:
                text = pyglet.font.Text(
                    self.helv,
                    label,
                    x=x, y=y,
                    color=(1, 1, 1, 0.5))
                node._cached_text = text
                node._cached_text_key = _cached_text_key
            text.draw()

    def get_names(self):
        node_nums = set(n.ip.split('.')[0] for n in self.app.network.get_active_nodes())
        for l in ipv4_address_space.ipv4_address_space:
            if l[0] in node_nums:
                yield l


    def draw_names(self, _cache={}):
        for num, name, date, status in self.get_names():
            x, y = self.app.camera.project(project_ip("%s.0.0.0" % num))
            _key = (x,y)
            if _cache.has_key(num) and _cache[num][0]==_key:
                text = _cache[num][1]
            else:
                text = pyglet.font.Text(
                    self.helv,
                    "%s - %s" % (num, name),
                    x=x, y=y,
                    color=(0.2, 0.8, 0.5, 0.5))
                _cache[num] = (_key, text)
            text.draw()
            _last = name

class App(object):
    def __init__(self):
        self.win = pyglet.window.Window(resizable=True, vsync=True)
        self.camera = Camera(self.win, zoom=10)
        self.setup_GL()
        self._setup_win_handlers()

        self.network = Network()
        self.world = World(self.network)
        self.hud = Hud(self)

        clock.set_fps_limit(60)

    def setup_GL(self):
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_POINT_SMOOTH)
        ##glShadeModel(GL_SMOOTH)

    def _setup_win_handlers(self):

        @self.win.event
        def on_mouse_scroll(x, y, scroll_x, scroll_y):
            self.camera.tbcam.mouse_zoom_diff(
                scroll_x/100.0, -scroll_y/1000.0)

        @self.win.event
        def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
            if buttons & pyglet.window.mouse.LEFT:
                self.camera.offset_x += dx/1000.0 * self.camera.get_zoom_factor()
                self.camera.offset_y += dy/1000.0 * self.camera.get_zoom_factor()
            if buttons & pyglet.window.mouse.RIGHT:
                self.camera.tbcam.mouse_roll(_n(x, self.win.width), _n(y, self.win.height))
            if buttons & pyglet.window.mouse.MIDDLE:
                self.camera.tbcam.mouse_zoom_diff(
                    dx/100.0, dy/1000.0)


        @self.win.event
        def on_mouse_press(x, y, buttons, modifiers):
            if buttons & pyglet.window.mouse.RIGHT:
                self.camera.tbcam.mouse_roll(_n(x, self.win.width), _n(y, self.win.height), False)

    def mainLoop(self):
        while self._is_running():
            try:
                self.win.dispatch_events()            

                self.camera.worldProjection()                
                self.world.draw()
                
                self.camera.hudProjection()
                self.hud.draw()

                clock.tick()
                self.win.flip()
                self.network._collect_garbage()

            except KeyboardInterrupt:
                break
            except Exception, e:
                import traceback
                traceback.print_exc()
                break
            
        self.win.has_exit = True

    def _is_running(self):
        return not getattr(self.win, "has_exit", False)

if __name__ == "__main__":
    app = App()

    import random
    def _gen_ip(n):
        for i in range(n):
            yield ".".join(str(random.randrange(256)) for _i in range(4))

    for ip in _gen_ip(1000):
        app.world.network._get_node(ip)

    app.mainLoop()

    ##pyglet.app.exit()
