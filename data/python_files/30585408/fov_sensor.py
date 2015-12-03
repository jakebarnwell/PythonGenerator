import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from sim_env import SimEnv2D
from sensors import FOVSensor
from objects import Point2D
import random
from numpy import pi

# Set up environment #args

bounds = [-1, 1, -1, 1]

s = SimEnv2D(bounds=bounds)
fov_sensor = FOVSensor(np.array([0, 0, pi/4]), fov_angle=pi/2)

s.draw()
fov_sensor.draw()
s.objects.append(None)

delta = (bounds[1] - bounds[0])/100.0
xs = np.arange(bounds[0], bounds[1], delta)
ys = np.arange(bounds[2], bounds[3], delta)
Z = np.zeros((len(ys), len(xs)))
for j in xrange(len(xs)):
    for k in xrange(len(ys)):
        x = xs[j]; y = ys[k];
        s.objects[0] = Point2D(np.array([x,y]))
        Z[len(ys)-1-k,j] = np.linalg.norm(fov_sensor.observe(s),2)
ax = plt.gca()
print np.max(Z)
print np.min(Z)
Z = Z/np.max(Z)
plt.imshow(Z, cmap=cm.gray, extent=bounds)
plt.colorbar()
plt.gca().set_xlim(0, 1)
plt.gca().set_ylim(0, 1)
plt.show()



