import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import random
from numpy import *
from sensors import PinholeCamera2D
from sim_env import SimEnv2D
from world import World2D
from objects import Point2D
import matplotlib.pyplot as plt

s = SimEnv2D();
for k in range(0, 10):
    s.add_object(Point2D(array([random.random()-0.5, random.random()-0.5])))

c = PinholeCamera2D(500, 0.25, 0.25, pi/2, 500)

w = World2D([c], s)

w.display()
#plt.axes().set_xlim(-0.5, 0.5);
#plt.axes().set_ylim(-0.5, 0.5);
c.view(s)
plt.show()
