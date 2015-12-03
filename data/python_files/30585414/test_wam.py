import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import matplotlib.pyplot as plt
from sim_env import SimEnv2D
from robot.ravebot import BarretWAM 
from optimize import scp_solver_states
from utils import mat2tuple
from random import random

from openravepy import *
import numpy, time
import struct
import _Getch 


"""
def waitrobot(robot):
    while not robot.GetController().IsDone():
        time.sleep(0.01)
"""

env = Environment() # create the environment
env.SetViewer('qtcoin') # start the viewer
env.Load('data/lab1.env.xml') # load a scene
robot = env.GetRobots()[0] # get the first robot

arm = BarretWAM(robot,env)

x0 = numpy.array([0.0] * arm.NX)
du = numpy.array([0.0] * arm.NU) 
du = numpy.array([0.0, 0.1, -0.02, -0.05, 0.04, 0.02, 0.1])
du = numpy.mat(du)
#U_bar = np.mat(np.random.random_sample((car.NU, T-1)))/5


T = 20
X = numpy.mat(numpy.zeros((arm.NX, T)))
U = numpy.mat(numpy.zeros((arm.NU, T-1)))
U = numpy.mat(numpy.random.random_sample((arm.NU, T-1))/5) 
U[:,10:] = -2 * U[:,10:]

for t in range(T-1):
	U[:,t] = du.T
	X[:,t+1] = arm.dynamics(X[:,t], U[:,t])

arm.draw_trajectory(X)

rho_x = 0.1
rho_u = 0.1
N_iter = 1
print X
X_copy = X.copy()
U_copy = U.copy()
opt_states, opt_ctrls, opt_vals = scp_solver_states(arm, X_copy, U_copy, rho_x, rho_u,\
                                             N_iter, method='shooting')

arm.draw_trajectory(opt_states, color=numpy.array((0.0,1.0,0.0)))

drawRobot = opt_states
getch = _Getch._Getch()
t = 0 
while True:
	c = getch()
	print c
	if c == 'x':
		break;
	elif ord(c) == 3 or ord(c) == 4:
		exit(0)
	elif c == 'n':
		print 'drawRobot = X'
		drawRobot = X
	elif c == 'm':
		drawRobot = opt_states
	elif c == ',' or c == '<':
		t = t - 1
	elif c == '.' or c == '>':
		t = t + 1

	if t >= T-1:
		t = T-1
	elif t <= 0:
		t = 0

	print arm.traj_pos(drawRobot[:,t])
	env.UpdatePublishedBodies()
            
