import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import matplotlib.pyplot as plt
from sim_env import SuperRaveEnv, Beacon
from robot.ravebot import BarretWAM 
from optimize import scp_solver_beliefs
from utils import mat2tuple
from random import random
from sensors import BeaconSensor3D
from kalman_filter import ekf_update
from covar import cov2vec, vec2cov
from rave_draw import draw_ellipsoid
from transforms import unscented_transform
from openravepy import *
import numpy as np
import time
import struct
import _Getch 


"""
def waitrobot(robot):
    while not robot.GetController().IsDone():
        time.sleep(0.01)
"""

env = Environment() # create the environment
env.SetViewer('qtcoin') # start the viewer
env.Load(os.getcwd() + '/data/wam_scene.env.xml') # load a scene
beacons = [Beacon(np.mat(np.array([-1.3, 0.4, 2.0])).T)]
beacons.append(Beacon(np.mat(np.array([-0.0, 0.2, 1.0])).T))
#beacons = [Beacon(np.mat(np.array([0.0, 2.0, 2.0])).T)]

s = SuperRaveEnv(rave_env=env, beacons=beacons)
s.draw()


robot = env.GetRobots()[0] # get the first robot
arm = BarretWAM(robot,env)
arm.attach_sensor(BeaconSensor3D(decay_coeff=25), lambda x: arm.traj_pos(x))
s.add_robot(arm)

num_states = arm.NX
num_ctrls = arm.NU
num_measure = len(beacons) #arg/make part of robot observe
Q = np.mat(np.diag([1e-7]*num_states)) #arg
#Q[2,2] = 1e-8 # Gets out of hand if noise in theta or phi
R = np.mat(np.diag([1e-5]*num_measure)) #arg
#R[3,3] = 5e-7

T = 20

x0 = np.array([-0.5] * arm.NX)
du = np.array([0.0, 0.1, -0.02, -0.05, 0.04, 0.02, 0.1])
du = np.mat(du).T


mus = np.mat(np.zeros((num_states,T)))
mus[:,0] = np.mat(x0).T
Sigmas = np.zeros((Q.shape[0], Q.shape[1],T))
Sigmas[:,:,0] = np.mat(np.diag([0.002]*num_states)) #arg
#Sigmas[2,2,0] = 0.0000001

X = np.mat(np.zeros((arm.NX, T)))
X[:,0] = np.mat(x0).T
U = np.mat(np.zeros((arm.NU, T-1)))

for t in range(T-1):
	U[:,t] = du
#U[:,T/2:] = -2 * U[:,T/2:]
#U = np.mat(np.random.random_sample((arm.NU, T-1))/5) 
#U[:,10:] = -2 * U[:,10:]

for t in xrange(1,T):
    X[:,t] = arm.dynamics(X[:,t-1], U[:, t-1])
    mus[:,t], Sigmas[:,:,t] = ekf_update(arm.dynamics,
                                         lambda x: arm.observe(s, x=x),
                                         Q, R, mus[:,t-1], Sigmas[:,:,t-1],
                                         U[:,t-1], None) #NOTE No obs

arm.draw_trajectory(X, mus, Sigmas)

drawRobot = X
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
            
