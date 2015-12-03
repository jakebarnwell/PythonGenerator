import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import random
from numpy import *
from sensors import PinholeCamera3D
from sim_env import SimEnv3D
from world import World3D
from objects import Point3D
import matplotlib.pyplot as plt

s = SimEnv3D()
for k in range(0, 35):
    s.add_object(Point3D(mat([random.random()-0.5, random.random()-0.5, random.random()*0.5]).T))

c = PinholeCamera3D(500, array([[0], [0], [-1]]), [0, 0, 0, 1], 600, 400)

w = World3D([c], s)

w.display()
c.view(s)
plt.show()
