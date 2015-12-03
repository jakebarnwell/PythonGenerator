import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.nxutils as nx
import matplotlib.patches as mpatches
from sensors import BeaconSensor
import rave_draw
#from robots import Links

class SimEnv(object):

    sim_env_index = 0

    @classmethod
    def increment_index(cls):
        cls.sim_env_index += 1
        return cls.sim_env_index

class Beacon:

    beacon_index = 0

    def __init__(self, pos, decay_fn=None):
        self.pos = pos
        # Takes in X, Y from meshgrid as arguments and returns value
        # between 0 and 1
        # Make sure decay function works element-wise on vectors and
        # matrices as well
        '''
        if decay_fn != None:
             self.decay_fn = decay_fn 
        else:
            self.decay_fn = self.quadratic_decay
        '''

    @classmethod
    def increment_index(cls):
        cls.beacon_index += 1
        return cls.sim_env_index
            
    '''
    def quadratic_decay(self, X, Y, k=10):
        return 1.0/(k*(self.pos[0]-X)**2 + k*(self.pos[1]-Y)**2 + 1)
    '''

class Obstacle:
    # Currently just assuming obstacles are polygons
    # Don't necessarily have to be convex as long as we're sampling
    # Circular obstacles does provide nice way to define smoother
    # penalty in terms of distance from center though

    def __init__(self, vertices, color='red'):
        pass

    def in_collision(self, pts):
        raise Exception('in_collision not implemented')

    def draw(self):
        raise Exception('draw not implemented')

#FIXME This can be any type of polygon
class RectangularObstacle(Obstacle):

    def __init__(self, vertices, color='red'):
        # Vertices as 2-by-k np array, e.g.
        # np.array([ [0,0], [0, 1], [1, 1], [1,0]], float).T
        self.vertices = vertices
        self.color = color

    def in_collision(self, pts):
        # Points as 2-by-k np array
        # Unfortunately points_inside_poly uses k-by-2
        return nx.points_inside_poly(pts.T, self.vertices.T)

    def draw(self):
        ax = plt.gca()
        poly = mpatches.Polygon(self.vertices.T, closed=True,\
                                facecolor=self.color, edgecolor='black')
        ax.add_patch(poly)

class CircularObstacle(Obstacle):

    def __init__(self, x, y, r, color='red'):
        self.pos = np.array([x, y])
        self.r = r
        self.color = color

    def in_collision(self, pts):
        # pts should be a 2-by-k array
        in_col = np.array([False]*pts.shape[-1])
        for k in xrange(pts.shape[-1]):
            pt = pts[:,k]
            if (pt[0]-self.pos[0])**2 + (pt[1]-self.pos[1])**2 < self.r**2:
                in_col[k] = True
        return in_col

    def draw(self):
        ax = plt.gca()
        circ = mpatches.Circle(self.pos, self.r, \
                               facecolor=self.color, edgecolor='black')
        ax.add_patch(circ)

class SimEnv2D(SimEnv):

    def __init__(self, bounds=[-1, 1, -1, 1],\
            beacons=list(), obstacles=list()):
        self.bounds = bounds
        self.robots = list()
        self.objects = list()
        self.beacons = beacons
        self.obstacles = obstacles
        self.index = SimEnv2D.increment_index()

    def __str__(self):
        return 'sim_env_2d[' + str(self.index) + ']'

    def add_robot(self, robot):
        self.robots.append(robot)

    def add_object(self, obj):
        self.objects.append(obj)

    def add_beacon(self, beacon):
        self.beacons.append(beacon)

    def add_obstacle(self, obstacle):
        self.obstacles.append(obstacle)

    def in_collision(self, pts):
        # Points as k-by-2 np array
        collides = np.array([False]*pts.shape[1])
        for obs in self.obstacles:
            collides = collides | obs.in_collision(pts) # Numpy bitwise or
        return collides

    def draw_beacons(self):
        if not self.beacons:
            return
        bs = BeaconSensor()
        delta = (self.bounds[1] - self.bounds[0])/100.0
        xs = np.arange(self.bounds[0], self.bounds[1], delta)
        ys = np.arange(self.bounds[2], self.bounds[3], delta)
        Z = np.zeros((len(ys), len(xs)))
        #links = Links(np.array([0, 0]), state_rep='angles')
        for j in xrange(len(xs)):
            for k in xrange(len(ys)):
                x = xs[j]; y = ys[k];
                #xyef = links.forward_kinematics(np.array([0,0]), np.array([x, y]))
                Z[len(ys)-1-k,j] = np.linalg.norm(bs.observe(self, np.array([x,y])),2)
                #Z[len(ys)-1-k,j] = np.linalg.norm(bs.observe(self, xyef),2)
        ax = plt.gca()
        plt.imshow(Z, cmap=cm.gray, extent=self.bounds)
        #plt.colorbar()

    def draw_goal_state(self, x):
        r = abs(self.bounds[1]-self.bounds[0])/50
        circ = mpatches.Circle((x[0], x[1]), r, \
                               facecolor='#74C365', edgecolor=None)
        plt.gca().add_patch(circ)
        
    def draw(self, ax=None):
        if ax==None:
            plt.figure()
            ax = plt.axes()
        ax.set_aspect('equal')
        #ax.set_xlabel('x')
        #ax.set_ylabel('y')
        #plt.title(str(self))

        for r in self.robots:
            r.draw()
        for obj in self.objects:
            obj.draw()
        for obstacle in self.obstacles:
            obstacle.draw()

        self.draw_beacons()

        plt.gca().set_xlim(self.bounds[0], self.bounds[1])
        plt.gca().set_ylim(self.bounds[2], self.bounds[3])
        #plt.show()


class SuperRaveEnv(SimEnv):
    # class simply adds beacons, overzealous naming

    def __init__(self, rave_env, beacons=list()):
        self.objects = list()
        self.index = SuperRaveEnv.increment_index()
        self.beacons = beacons
        self.rave_env = rave_env
        self.handles = [] 
        self.robots = []

    def __str__(self):
        return 'SimEnv_3d[' + str(self.index) + ']'

    def add_object(self, obj):
        self.objects.append(obj)

    def get_objects(self):
        return self.objects

    def add_beacon(self, beacon):
        self.beacons.append(beacon)

    def add_robot(self, robot):
        self.robots.append(robot)

    def draw_beacons(self):
        for beacon in self.beacons:
            beacon_plot = rave_draw.draw_beacon(beacon.pos, self.rave_env)
            for handle in beacon_plot:
                self.handles.append(handle)

    def draw(self):
        self.draw_beacons()
        return self.handles

        
