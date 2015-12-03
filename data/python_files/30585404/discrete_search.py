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
w = f = 500.0
px = 0.0; py = 0.0
s.add_object(Point2D(np.array([px, py])))
cams = list()
# Initial camera
cams.append(PinholeCamera2D(f, px-.5, py-.5, -pi/4, w, color=COLORS[1]))
# Camera whose pose we'll optimize
cams.append(PinholeCamera2D(f, px-.5, py-.5, 0.0, w, color=COLORS[2]))
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

for cam in cams:
    # Second camera will be moving aronud but h[1] should change with it
    hs.append(cam.project_point)

def sim_noise():
    #return (rand()-0.5)*10
    return 0

# Indexing doesn't follow convention, z_k measurement of mu_k
mu1, Sigma1 = ekf_update(f, hs[0], Q, R, mus[0], Sigmas[0], u, hs[0](mus[0]) +
    sim_noise())
mus.append(mu1); Sigmas.append(Sigma1)

# Discretization/search
dxy = 0.1
dtheta = .314
min_trace = inf
z1 = hs[1](mus[0]) + sim_noise()
for x in arange(-1, dxy, 1):
    for y in arange(-1, dxy, 1):
        if x == 0 and y == 0: # Object at focal pt. exception
            continue
        for theta in arange(-pi, pi, dtheta):
            if theta == 0: # Results in inf/error
                continue
            print x, y, theta
            cams[1].move_to(x, y, theta)
            mu1, Sigma1 = ekf_update(f, hs[1], Q, R, mus[1], Sigmas[1], u, z1)
            if trace(Sigma1) < min_trace:
                min_x = x; min_y = y; min_theta = theta
                min_trace = trace(Sigma1)
cams[1].move_to(min_x, min_y, min_theta)
mu1, Sigma1 = ekf_update(f, hs[1], Q, R, mus[1], Sigmas[1], u, z1)
mus.append(mu1); Sigmas.append(Sigma1)

# Display

world.display()
title('Discrete search')
axes().set_xlim(-1, 1);
axes().set_ylim(-1, 1);

conf = 0.95

for k in xrange(len(mus)):
    draw_ellipsoid(mus[k], Sigmas[k], conf, color=COLORS[k%len(COLORS)])
show()

