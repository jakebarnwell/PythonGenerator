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

class Dot(Robot):
    # Trivial model
    # State: [x,y]
    # Control: [u_x, u_y]
    # Dynamics: X1 = X0 + dt*U

    NX = 2
    NU = 2

    def __init__(self, x, color='red', dt=0.1):
        self.color = color
        Robot.__init__(self, x, dt=dt)
        self.index = Dot.increment_index()

    def dynamics(self, X, U):
        return X + U*self.dt

    def draw(self, x=None, color='r'):
        if x == None: x = self.x
        x = array(x)

        ax = plt.gca()

        # Draw dot

        plt.plot(x[0], x[1], color=self.color, lw=0.1)

        # Draw attached sensors

        for (sensor, pos_fn) in self.sensors:
            sensor.move_to(*pos_fn(x))
            sensor.draw()
