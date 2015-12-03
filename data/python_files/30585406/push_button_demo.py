import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import matplotlib.pyplot as plt
from sim_env import SimEnv2D
from robots import Links
from objects import Point2D
from sensors import ExtendedCamera2D
from numpy import pi, array, mat, cos, sin, zeros, ones
from optimize import scp_solver

s = SimEnv2D()

s.add_object(Point2D(array([0.8, 0.8]), Sigma=mat('0.01 0; 0 0.01')))
w = f = 500

# 2-link arm
xy = [0, 0]
#thetas = [pi/2, 5*pi/6]
thetas = [0, 0]
l1 = 0.5; l2 = 0.5
two_link = Links(xy, thetas, l1, l2)

# Sensor
cam = ExtendedCamera2D(f, 0, 0, -pi/4, w, ks=array([-0.25, 0.11]),\
        color='k')

# Attach sensor to elbow of arm facing direction of second link
def pos_fn(x):
    return x[0] + cos(x[2]+pi/2)*l1,\
           x[1] + sin(x[2]+pi/2)*l1,\
           x[2] + x[3]
two_link.attach_sensor(cam, pos_fn)
    
s.add_robot(two_link)

# Draw scene
s.draw()
plt.gca().set_xlim(-1, 1);
plt.gca().set_ylim(-1, 1);

# Generate a nominal trajectory
T = 100
X_bar = mat(zeros((two_link.NX, T)))
U_bar = mat(ones((two_link.NU, T-1))/10)
for t in xrange(T):
   X_bar[:,t] = two_link.dynamics(X_bar[:,t-1], U_bar[:, t-1])

#print X_bar[:,T-1]

# Trust region
rho_x = 1000.0
rho_u = 10.0

opt_states, opt_controls = scp_solver(two_link, X_bar, U_bar, rho_x, rho_u, 1)

