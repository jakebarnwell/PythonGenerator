import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import numpy as np
import matplotlib.pyplot as plt
from sim_env import SimEnv2D, Beacon
from robot.car import SimpleCar
from sensors import BeaconSensor
from utils import mat2tuple
import random
from math import log
from numpy.random import multivariate_normal as mvn
from kalman_filter import ekf_update

# Set up environment #args

beacons=[Beacon(np.array([-1,-1])),
         Beacon(np.array([1,1]))]
beacons = beacons[1:2]
s = SimEnv2D(bounds=[-2, 2, -2, 2], beacons=beacons)

x0 = np.array([-1, 1, -np.pi/4, 0])
car = SimpleCar(x0)
car.attach_sensor(BeaconSensor(), lambda x: x[0:2])

s.add_robot(car)

# Number of timesteps
T = 20 #arg

# Dynamics and measurement noise
num_states = car.NX
num_ctrls = car.NU
num_measure = len(beacons) #arg/make part of robot observe
Q = np.mat(np.diag([0.0005]*num_states)) #arg
Q[2,2] = 0 # Gets out of hand if noise in theta or phi
Q[3,3] = 0
R = np.mat(np.diag([0.00005]*num_measure))*0.001 #arg
# Sample noise
dynamics_noise = mvn([0]*num_states, Q, T-1).T
measurement_noise = mvn([0]*num_measure, R, T-1).T

# Setup for EKF
mus = np.mat(np.zeros((num_states,T)))
mus[:,0] = np.mat(x0).T
Sigmas = np.zeros((Q.shape[0], Q.shape[1],T))
Sigmas[:,:,0] = np.mat(np.diag([0.001]*num_states)) #arg

# Generate trajectory and obtain observations along trajectory

X_bar = np.mat(np.zeros((car.NX, T))) #arg
X_bar[:,0] = np.mat(x0).T
U_bar = np.ones((car.NU, T-1))*1.7 #arg
for t in xrange(1,T):
    U_bar[1,t-1] = 0

for t in xrange(1,T):
    X_bar[:,t] = np.mat(car.dynamics(X_bar[:,t-1], U_bar[:, t-1])) +\
                     np.mat(dynamics_noise[:,t-1]).T 
    z = car.observe(s,x=X_bar[:,t]) + np.mat(measurement_noise[:,t-1]).T
    mus[:,t], Sigmas[:,:,t] = ekf_update(car.dynamics,
                                         lambda x: car.observe(s, x=x),
                                         Q, R, mus[:,t-1], Sigmas[:,:,t-1],
                                         U_bar[:,t-1], z)
                                         
# Plot nominal trajectory with covariance ellipses

ax = plt.gca()
plt.title('Nominal')
s.draw(ax=ax)
#print Sigmas
car.draw_trajectory(mat2tuple(X_bar.T), mus=mus, Sigmas=Sigmas[0:2,0:2,:])

plt.show()

