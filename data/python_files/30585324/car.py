import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
from numpy import *
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rc
from objects import SimObject
from utils import scalar
from covar import draw_ellipsoid, vec2cov, cov2vec,\
    project_psd
from kalman_filter import ekf_update
from numpy.random import multivariate_normal as mvn
import time
from math import atan2, atan
from robots import *


class SimpleCar(Robot):
    # See "Differential Dynamic Programming in Belief Space" for
    # Implementation description.
    
    NX = 4
    NU = 2

    def __init__(self, x, l=0.01, color='r', dt=0.1):
        self.l = l
        self.color = color
        Robot.__init__(self, x, dt=dt)
        self.index = SimpleCar.increment_index()

    def __str__(self):
        return 'car[{0}]'.format(self.index)

    def pos(self):
        return self.x[0:2]

    def traj_pos(self,x):
      return mat(x[0:2]).T

    def orientation(self,x):
      return x[2]

    def dynamics(self, X, u):
        x = scalar(X[0])
        y = scalar(X[1])
        theta = scalar(X[2])
        v = scalar(X[3])
        
        a = scalar(u[0])
        phi = scalar(u[1])

        x_dot = v*cos(theta)
        y_dot = v*sin(theta)
        theta_dot = v*tan(phi)/self.l

        return X + mat((x_dot, y_dot, theta_dot, a)).T*self.dt

    def observe(self, scene, x=None):
        if x==None:
            x = self.x
        zs = Robot.observe(self, scene, x)
        # Also give car orientation and steering information
        if zs.size > 0:
            zs = vstack((zs, mat('x[3]')))
        else:
            zs = mat('x[3]')
        return zs

    def draw(self, x=None, color='r'):
        if x == None: x = self.x
        x = array(x)

        LENGTH_TO_WIDTH_RATIO = 1.7
        w = self.l/LENGTH_TO_WIDTH_RATIO

        ax = plt.gca()

        # Draw simple car

        pos = x[0:2]; theta = x[2]; phi = x[3]
        body = mpatches.Rectangle(pos-array([self.l/2, w/2]),
                                  width=self.l, height=w, \
                                  facecolor=self.color)
        t = matplotlib.transforms.Affine2D().rotate_around(pos[0], pos[1],\
                theta)
        body.set_transform(t + ax.transData)
        ax.add_patch(body)

        '''
        phi = x[3]
        steering_dir = mpatches.Arrow(pos[0],\
                pos[1], self.l*cos(phi),\
                self.l*sin(phi), width=self.l/5)
        ax.add_patch(steering_dir)
        '''

        #ax.text(pos[0], pos[1], str(self))

        # Draw attached sensors
        ax = plt.gca()

        for (sensor, pos_fn) in self.sensors:
            sensor.move_to(*pos_fn(x))
            sensor.draw()

        return body