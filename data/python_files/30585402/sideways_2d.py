import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
from numpy import *
from sensors import PinholeCamera2D
from sim_env import SimEnv2D
from world import World2D
from objects import Point2D
from pylab import *
from utils import *
from covar import draw_ellipsoid
from kalman_filter import ekf_update

# World setup

s = SimEnv2D()
w = f = 500
px = 0; py = 0
s.add_object(Point2D(array([px, py])))
cams = list()
cams.append(PinholeCamera2D(f, [px-0.5, py-.5, pi/4], w, color=COLORS[1]))
cams.append(PinholeCamera2D(f, [px-0.5, py, pi/4], w, color=COLORS[2]))
cams.append(PinholeCamera2D(f, [px-0.5, py, 0], w, color=COLORS[3]))
cams.append(PinholeCamera2D(f, [px-0.75, py, 0], w, color=COLORS[4]))
world = World2D(cams, s)

# Kalman updates

# mus, x in world coordinates
mus = list(); Sigmas = list()
mus.append(mat([[px], [py]]))
Sigmas.append(diag([.05, .05])) # In m
Q = diag([.0, .0])              # In m
R = 100                         # In pixels
u = zeros2((2,1))               # Static dynamics/no controls

f = lambda x, u: x # Dynamics
hs = list()        # Measurement function for each camera
zs = list()        # Simulated measurements from each camera

for cam in cams:
    hs.append(cam.project_point)
    #TODO Better measurement simulation
    zs.append(hs[-1](mus[0]) + (rand()-0.5)*10)

# Indexing doesn't follow convention, z_k measurement of mu_k
mu1, Sigma1 = ekf_update(f, hs[0], Q, R, mus[0], Sigmas[0], u, zs[0])
mus.append(mu1); Sigmas.append(Sigma1)
for k in range(1, len(cams)):
   print zs[k]
   mu1, Sigma1 = ekf_update(f, hs[k], Q, R, mus[1], Sigmas[1], u, zs[k])
   mus.append(mu1); Sigmas.append(Sigma1)

# Display

world.display()
axes().set_xlim(-1, 1);
axes().set_ylim(-1, 1);

conf = 0.95

for k in xrange(len(mus)):
    draw_ellipsoid(mus[k], Sigmas[k], conf, color=COLORS[k%len(COLORS)])
    print COLORS[k%len(COLORS)]
show()

