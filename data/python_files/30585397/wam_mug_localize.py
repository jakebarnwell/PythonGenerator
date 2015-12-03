import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import matplotlib.pyplot as plt
from sim_env import SuperRaveEnv, Beacon
from robot.ravebot import BarretWAM, RaveLocalizerBot
from optimize import scp_solver_beliefs
from utils import mat2tuple
from random import random
from sensors import BeaconSensor3D, OpenRAVECamera
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
mug_pos = np.mat(np.array([0.0, 1.0, 0.8])).T
mug = env.GetKinBody('mug2')
mugTransform = mug.GetTransform()
mugTransform[0,3] = mug_pos[0]
mugTransform[1,3] = mug_pos[1]
mugTransform[2,3] = mug_pos[2]
mug.SetTransform(mugTransform)


s = SuperRaveEnv(rave_env=env, beacons=beacons)
s.draw()

robot = env.GetRobots()[0] # get the first robot
arm = BarretWAM(robot,env)
arm.attach_sensor(BeaconSensor3D(decay_coeff=25), lambda x: arm.traj_pos(x))

localizer = RaveLocalizerBot(arm, mug_pos)
localizer.attach_sensor(OpenRAVECamera(KK=np.mat(np.array([(640.0, 0.0, 320.0), (0.0, 480.0, 240.0), (0.0, 0.0, 1.0)]))), 
	lambda x: localizer.camera_obj_state(x))
s.add_robot(localizer)

for attachedsensor in robot.GetAttachedSensors():
    if attachedsensor.GetSensor().Supports(Sensor.Type.Camera):
        attachedsensor.GetSensor().Configure(Sensor.ConfigureCommand.PowerOn)
        attachedsensor.GetSensor().Configure(Sensor.ConfigureCommand.RenderDataOn)


num_states = localizer.NX
num_ctrls = localizer.NU
num_measure = len(beacons) + 2
Q = np.mat(np.diag([1e-7]*num_states)) #arg
Q[arm.NX, arm.NX] = 1e-11
Q[arm.NX+1, arm.NX+1] = 1e-11
Q[arm.NX+2, arm.NX+2] = 1e-11
#Q[2,2] = 1e-8 # Gets out of hand if noise in theta or phi
R = np.mat(np.diag([1e-5]*num_measure)) #arg
#R[3,3] = 5e-7

T = 20

arm_x0 = np.array([0.5] * arm.NX)
du = np.array([0.0, 0.1, -0.02, -0.05, 0.04, 0.02, 0.1])
du = np.mat(du).T

x0 = np.mat(np.zeros((localizer.NX,1)))
x0[0:7] = np.mat(arm_x0).T
x0[7:10] = mug_pos


"""
print localizer.observe(s, test)

print arm.camera_transform(x0)

while True:
	try:
		sensordata = robot.GetAttachedSensor('camera').GetData()
		print sensordata.transform
		break
	except:
		time.sleep(0.1)
"""


mus = np.mat(np.zeros((num_states,T)))
mus[:,0] = x0
Sigmas = np.zeros((Q.shape[0], Q.shape[1],T))
Sigmas[:,:,0] = np.mat(np.diag([0.002]*num_states)) #arg
#Sigmas[2,2,0] = 0.0000001

X = np.mat(np.zeros((localizer.NX, T)))
X[:,0] = x0
U = np.mat(np.zeros((localizer.NU, T-1)))

for t in range(T-1):
	U[:,t] = du
#U[:,T/2:] = -2 * U[:,T/2:]
#U = np.mat(np.random.random_sample((arm.NU, T-1))/5) 
#U[:,10:] = -2 * U[:,10:]

for t in xrange(1,T):
    X[:,t] = localizer.dynamics(X[:,t-1], U[:, t-1])
    mus[:,t], Sigmas[:,:,t] = ekf_update(localizer.dynamics,
                                         lambda x: localizer.observe(s, x=x),
                                         Q, R, mus[:,t-1], Sigmas[:,:,t-1],
                                         U[:,t-1], None) #NOTE No obs

localizer.draw_trajectory(X, mus, Sigmas)

Bel_bar = np.mat(np.zeros((localizer.NB, T)))
for t in xrange(T):
    Bel_bar[:,t] = np.vstack((X[:,t], cov2vec(Sigmas[:,:,t])))


rho_bel = 0.1
rho_u = 0.1
N_iter = 5
goal_bel = np.copy(Bel_bar[:,-1])
goal_bel[localizer.NX:] = 0

opt_bels, opt_ctrls, opt_vals = scp_solver_beliefs(s, Bel_bar.copy(), U,\
               Q, R, rho_bel, rho_u, goal_bel, N_iter, localizer.NX, method='shooting')


opt_mus = np.mat(np.zeros((localizer.NX, T)))
opt_mus[:,0] = X[:,0]
opt_X = opt_mus.copy()
opt_Sigmas = np.zeros((Q.shape[0], Q.shape[1],T))
opt_Sigmas[:,:,0] = Sigmas[:,:,0]
opt_ctrls = np.mat(opt_ctrls)

for t in xrange(1,T):
    opt_X[:,t] = localizer.dynamics(opt_X[:,t-1], opt_ctrls[:,t-1]); 
    opt_mus[:,t], opt_Sigmas[:,:,t] = ekf_update(localizer.dynamics,
        lambda x: localizer.observe(s, x=x),  
        Q, R, opt_mus[:,t-1], opt_Sigmas[:,:,t-1], opt_ctrls[:,t-1], None) 

localizer.draw_trajectory(opt_X, opt_mus, opt_Sigmas, color=np.array((0.0,1.0,0.0,0.2)))


drawRobot = opt_X

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
		drawRobot = opt_X
	elif c == ',' or c == '<':
		t = t - 1
	elif c == '.' or c == '>':
		t = t + 1

	if t >= T-1:
		t = T-1
	elif t <= 0:
		t = 0

	print arm.traj_pos(drawRobot[0:arm.NX,t])
	env.UpdatePublishedBodies()
            
