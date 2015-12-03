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

class Links(Robot):
    # Model from http://www.eng.utah.edu/~cs5310/chapter5.pdf
    # Two possible state representations: joint angles or
    #   xy in end effector space
    # xy in end effector is nicer for reasoning, but worse because
    #   there are two possible robot arm configurations per feasible
    #   xy position (elbow up and elbow down). 
    NX = 2
    NU = 2
    
    def __init__(self, thetas, state_rep='angles', origin=array([0,0]),
                 l1=0.3, l2=0.3, dt=0.1):
        # Note that following the camera model, theta = 0 is up
        self.l1 = l1 # Length of first link
        self.l2 = l2 # Length of second link 
        self.state_rep = state_rep
        self.origin = origin # Origin of first link
        if self.state_rep == 'angles':
          x = thetas; 
        else: 
          x = self.forward_kinematics(origin, thetas)
        #x = array([xy_ef, thetas]).ravel()
        #x = thetas; 
        Robot.__init__(self, x, dt=dt)
        self.index = Links.increment_index()

    def traj_pos(self, x=None):
        if x == None:
            x = self.x

        if self.state_rep == 'angles':
            return self.forward_kinematics(self.origin, x)
        else: #state representation = points 
            return mat(x[0:2]).T
    
    def orientation(self, x=None):
        if x == None:
            x = self.x
      
        if self.state_rep == 'angles':
            return x[0] + x[1]
        else:
            thetas = self.inverse_kinematics(self.origin, x)
            return thetas[0] + thetas[1]


    def __str__(self):
        return 'links[' + str(self.index) + ']'

    def dynamics(self, x, u):
        if self.state_rep == 'angles':
            thetas = x + self.dt*u
            return thetas
        else:
            thetas = mat(self.inverse_kinematics(self.origin, x)).T
            new_thetas = thetas + self.dt*u
            new_xy = self.forward_kinematics(self.origin, new_thetas)
            return mat(new_xy).T
        #thetas = x + self.dt*u;
        #xy_ef = self.forward_kinematics(self.origin, thetas)
        #x1 = mat(array([xy_ef.ravel(), thetas]).ravel()).T

    def observe(self, scene, x=None):
        if x==None:
            x = self.x
        zs = Robot.observe(self, scene, x)
        # also give joint angle observations
        if zs.size > 0:
            pass
            #zs = vstack((zs, mat('x[2]')))
            #zs = vstack((zs, mat('x[3]')))
        else:
            zs = mat('x[3]')
        return zs

    def forward_kinematics(self, origin, thetas):
        # Class function which returns end-effector position given
        # joint angles

        # Note that following the camera model, theta = 0 is up
        x_ef = origin[0] + self.l1*cos(thetas[0]) + \
            self.l2*cos(thetas[0]+thetas[1])
        y_ef = origin[1] + self.l1*sin(thetas[0]) + \
            self.l2*sin(thetas[0]+thetas[1])
        return array([x_ef, y_ef]).ravel()
  
    def inverse_kinematics(self, origin, xy):
        x = xy[0] - origin[0]
        y = xy[1] - origin[1] 
        a1 = self.l1
        a2 = self.l2

        if (x**2 + y**2) > (a1 + a2)**2:
            #print "infeasible kinematics, probably from linearization"
            max_dist = a1 + a2 - 0.001
            curr_dist = sqrt(x**2 + y**2)
            ratio = max_dist / curr_dist
            x = ratio * x
            y = ratio * y
        
        numerator = (a1 + a2)**2 - (x**2 + y**2)
        denom = (x**2 + y**2) - (a1 - a2)**2
        frac = float(numerator) / denom
        frac_sqrt = sqrt(frac)
        theta_2 = 2 * atan(frac_sqrt)

        phi = atan2(y,x)
        gamma = atan2(a2*sin(theta_2), a1 + a2*cos(theta_2))
        theta_1 = phi - gamma 

        return array([theta_1, theta_2]).ravel()

    def draw_Cspace(self, X=None, color='blue'):
        if X == None:
            X = self.x

        if self.state_rep == 'angles':
            thetas = X[0:2]
        else:
            thetas = self.inverse_kinematics(self.origin, X[0:2])
        
        ax = plt.gca()
        ax.plot(thetas[0], thetas[1], 'o', color=color, markersize=2)


    def draw(self, X=None, color='blue'):

        if X == None:
            X = self.x
        ax = plt.gca()

        # Draw 2-link arm
        
        pos = self.origin; 
        if self.state_rep == 'angles':
            thetas = X[0:2]
            xy_ef = self.traj_pos(x=X)
        else:
            thetas = self.inverse_kinematics(self.origin, X[0:2])
            xy_ef = X[0:2]

        xs = [pos[0], pos[0]+self.l1*cos(thetas[0]), xy_ef[0]]
        ys = [pos[1], pos[1]+self.l1*sin(thetas[0]), xy_ef[1]]

        ax.plot(xs, ys, lw=2, color=color, solid_joinstyle='round')
        ax.plot(xs, ys, lw=3, color=color)
        ax.plot(xs[1:2], ys[1:2], 'o', color='black')
        ax.plot(xs[0:1], ys[0:1], 'o', color=color, markersize=2)

        #ax.text(pos[0], pos[1], str(self))

        # Draw attached sensors

        for (sensor, pos_fn) in self.sensors:
            sensor.move_to(*pos_fn(X))
            sensor.draw()

