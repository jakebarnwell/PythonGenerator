import pcapy
import impacket.ImpactDecoder
import pyglet
from pyglet.gl import *
from OpenGL.GLUT import * #<==Needed for GLUT calls

import socket
import threading
import time
from math import sqrt, fabs

import morton_ip_map

def _resolve(ip, _cache={}):
    if not _cache.has_key(ip):
        class X(threading.Thread):
            def run(self):
                try:
                    _cache[ip] = socket.gethostbyaddr(ip)[0]
                except:
                    del _cache[ip]
        _cache[ip] = ip ## chaep lock
        X().start()
    return _cache.get(ip, ip)

def _interp(a,b,p):
    return [a[i] + (b[i]-a[i])*p
            for i in range(len(a))]

class Route:
    def __init__(self, src_dst_coords, **options):
	self.src_dst_coords = src_dst_coords
	self.packets = []
        self.options = options
        self.count = 0
	self.created = time.time()

    def get_color(self):
        if len(self.packets):
            return (0.4, 0.2, 0.5, 0.5)
        elif self.count >10000:
            return (0.3, 0.2, 0.2, 0.5)
        elif self.count >1000:
            return (0.2, 0.2, 0.1, 0.5)
        elif self.count >100:
            return (0.1, 0.1, 0.1, 0.5)
        else:
            return (0.01, 0.02, 0.01, 0.5)

    def get_size(self):
        return self.count #min(50, max(1, sum(p.get_size() for p in self.packets)))

    def render(self, engine, selected=False):        
        glLineWidth(self.get_size())
	glBegin(GL_LINES)
        if selected:
            glColor4f(1,1,1,1)
        else:
            glColor4f(*self.get_color())
	src_c, dst_c = self.src_dst_coords
	glVertex2f(src_c[0]*engine.width, src_c[1]*engine.height);
	glVertex2f(dst_c[0]*engine.width, dst_c[1]*engine.height);
	glEnd()
        for packet in self.packets:
            glPointSize(packet.get_size())
            glBegin(GL_POINTS)
            p = packet.get_progress()
            c = _interp(src_c, dst_c,p)
            glColor4f(*packet.get_color())
            glVertex2f(c[0]*engine.width, c[1]*engine.height)
            glEnd()
            
    def _cleanup(self):
        ## ~ garbage collector
        dead = []
        for p in self.packets:
            if p.get_age() > 2:
                dead.append(p)
        for p in dead:
            self.packets.remove(p)

        if not len(self.packets) and self.get_age()>30:
            return True

    def add(self, packet):
	self.packets.append(packet)
        self.count += 1

    def get_age(self):
	return time.time() - self.created

class Packet:
    def __init__(self, **options):
	self.options = options
	self.created = time.time()

    def get_age(self):
	return time.time() - self.created

    def get_progress(self):
        return min(1, self.get_age()/0.5) ## TODO

    def get_color(self):
        v = 1 - min(1, self.get_age()/1.0) ## TODO
        def _port(n):
            return self.options.get('sport',0)==n \
                or self.options.get('dport',0)==n
        if _port(80):
            r,g,b=0.5,1,0.5
        elif _port(22):
            r,g,b=1,0.5,0.5
        elif _port(53):
            r,g,b=0.5,0.5,1
        else:
            r,g,b=0.5,0.5,0.5
        return (v*r,v*g,v*b, 0.5*v)

    def get_size(self):
        return float(min(100, max(4, self.options.get("length", 0)/100, 0)))

    def __str__(self):
        return "(%sb %s->%s)" % (
            self.options.get('length', '?'),
            self.options.get('sport', '?'),
            self.options.get('dport', '?')
            )


class RenderEngine(pyglet.window.Window):
    def __init__(self):
        super(RenderEngine, self).__init__(resizable=True)
	glMatrixMode (GL_PROJECTION);
	glLoadIdentity ();
	##glOrtho (0, 1, 1, 0, 0, 1);
	glOrtho(0.0, 1.0, 0.2, 1.0, -1.0, 1.0); 
	glMatrixMode (GL_MODELVIEW);

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        pyglet.clock.schedule_interval(self.redraw, 1/30.0)
        self.routes = {}
        self.selected_routes = []

    def project_ip(self, ip):
        n = sum(n*(256**(3-i)) for i,n in enumerate(
            map(int, ip.split('.'))))
        x,y = morton_ip_map.deinterleave2(n)
        N = 65536.0
        c = x/N,y/N,0
        ###print ip, n, (x,y), c
        return c
        ## x,y,z,w = map(int, ip.split('.'))        
        ## N = 256**2
        ## return ((x*256.0 + z)/N, (y*256.0+w)/N, (z*256.0+w)/N)
        ## ## return (x/256.0, y/256.0, (z*256.0+w)/(256**2))

    def add_to_scene(self, attrs):
        src_coords = self.project_ip(attrs['src'])
        dst_coords = self.project_ip(attrs['dst'])
        ##print src_coords, dst_coords
        route = self.get_or_create_route((src_coords, dst_coords), attrs)
        route.add(Packet(**attrs))

    def get_or_create_route(self, src_dst_coords, attrs):
        if not self.routes.has_key(src_dst_coords):
            self.routes[src_dst_coords] = Route(src_dst_coords, **attrs)
        return self.routes[src_dst_coords]

    def redraw(self, dt):
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        for k, r in self.routes.items():
	    r.render(self, selected=k in self.selected_routes)
            if r._cleanup():
                del self.routes[k]

        glColor4f(1,1,1,0.3)
        for n in range(0, 256, 10):
            x,y,_z = self.project_ip("%d.0.0.1" % (n,))
            label = pyglet.text.Label(
                '%d' % n,
                font_name='Times New Roman',
                font_size=10,
                #color=(1, 1, 1,1),
                x=self.width*x, y=self.height*y,
                anchor_x='left', anchor_y='top')
            label.draw()
        n_routes = len(self.routes)/2
        n_packets = sum(len(r.packets) for r in self.routes.values())
        pyglet.text.Label(
            '%d pairs, %d packets' % (n_routes, n_packets),
            font_name='Times New Roman',
            font_size=20,
            #color=(1, 1, 1,1),
            x=self.width/2, y=20,
            anchor_x='center', anchor_y='center').draw()

        for i, k in enumerate(self.selected_routes):
            try:
                r = self.routes[k]
            except KeyError:
                continue
 
            pyglet.text.Label("""%(src)s->%(dst)s\n""" % r.options \
                              + " | %d/%d | " % (len(r.packets), r.count) \
                              + " " + _resolve(r.options['src']) \
                              + " ".join("%s" % p for p in r.packets),
                              font_name='Times New Roman',
                              font_size=10,
                              x=0, y=self.height-20-i*20).draw()

    def on_resize(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(gl.GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, 0, height, -1, 1)
        glMatrixMode(gl.GL_MODELVIEW)

    def nearest_routes(self, x, y):
        rs = []
        def _dist_l(src_dst_coords, x, y):
            s_c, d_c = src_dst_coords
            ## http://stackoverflow.com/questions/849211/shortest-distance-between-a-point-and-a-line-segment
            def pdis(a, b, c):
                t = b[0]-a[0], b[1]-a[1]           # Vector ab
                dd = sqrt(t[0]**2+t[1]**2)         # Length of ab
                t = t[0]/dd, t[1]/dd               # unit vector of ab
                n = -t[1], t[0]                    # normal unit vector to ab
                ac = c[0]-a[0], c[1]-a[1]          # vector ac
                return fabs(ac[0]*n[0]+ac[1]*n[1]) # Projection of ac to n (the minimum distance)

            ##print pdis((1,1), (2,2), (2,0))        # Example (answer is 1.414)
            x, y = x*1.0/self.width,y*1.0/self.height
            return pdis(s_c, d_c, (x,y))

        def _dist(a, x, y):
            x, y = x*1.0/self.width,y*1.0/self.height
            return sqrt((x-a[0])**2 + (y-a[1])**2)
        
        for src_dst_c, r in self.routes.items():
            distance = max(_dist_l(src_dst_c, x, y)*10,
                           min(_dist(src_dst_c[0], x,y),
                                _dist(src_dst_c[1], x,y))/2)
            rs.append((distance, src_dst_c))
        rs.sort()
        return [r for (distance, r) in rs
                if distance < 0.2][:5]
        

    def on_mouse_motion(self, x, y, dx, dy):
        self.selected_routes = self.nearest_routes(x,y)

class Main(threading.Thread):
    class UnknownPacket(Exception): pass

    def __init__(self, reader):
        super(Main, self).__init__()
        self.reader = reader
        self.decoder = impacket.ImpactDecoder.EthDecoder()
        self.engine = RenderEngine()

    def handle(self, data):
        try:
            attrs = self.decode(data)
            self.engine.add_to_scene(attrs)
            return attrs
        except Main.UnknownPacket:
            pass

    def decode(self, data):
        packet = self.decoder.decode(data)
        if packet.get_ether_type() == 2048:
            ip = packet.child()
            src, dst = ip.get_ip_src(), ip.get_ip_dst()
            length = ip.get_ip_len()
            data = {'src':src,
                    'dst':dst,
                    'length':length}
            try:
                data.update({
                    'sport':ip.child().get_th_sport(),
                    'dport':ip.child().get_th_dport(),
                              })
            except:
                pass
            return data
        else:
            if not packet.get_ether_type()==2054: # ARP
                print "UNKNOWN TYPE",  
                print packet
            raise Main.UnknownPacket

    def run(self):
        while not self.engine.has_exit:
            self.step()
        print "thread end"

    def step(self, dt=None):
        try:
            header, data = self.reader.next()
        except pcapy.PcapError, e:
            time.sleep(0.1) ## no more data ?
            return
        self.handle(data)

class SimulatedReader:
    def __init__(self, reader):
        self._reader = reader

    def next(self):
        h,d = self._reader.next()
	t,tt = h.getts()
        t = (t*1000000 + tt)/100000.0
        if hasattr(self, "_last_t"):
	    dt = t - self._last_t
	    time.sleep(dt/5)
        self._last_t = t
        return h, d
        


import argparse

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--from-file', '-r', metavar='path', 
                    help='read from pcap file')
parser.add_argument('--interface', '-i', metavar='iface',
                    default="en0", help='sniff')
args = parser.parse_args()

if args.from_file:
    r = pcapy.open_offline(args.from_file)
    r = SimulatedReader(r)
    main = Main(r)
else:
    r = pcapy.open_live(args.interface, 1600, 0, 100)
    main = Main(r)

main.start()

try:
    pyglet.app.run()
except KeyboardInterrupt:
    main.engine.has_exit = True
    print "interrupt"
except Exception, e:
    import traceback
    traceback.print_exc()
main.engine.has_exit = True
print "end"
## time.sleep(1)
## pyglet.app.exit()
