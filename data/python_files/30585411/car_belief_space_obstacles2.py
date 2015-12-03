import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import numpy as np
import matplotlib.pyplot as plt
from sim_env import SimEnv2D, Beacon, RectangularObstacle
from robot.car import SimpleCar
from sensors import BeaconSensor
from utils import mat2tuple
import random
from math import log
from numpy.random import multivariate_normal as mvn
from kalman_filter import ekf_update
from covar import cov2vec, vec2cov
from optimize import scp_solver_beliefs

# Set up environment #args

beacons=[Beacon(np.array([0.4,-0.4])), Beacon(np.array([-0.4,-0.8])), Beacon(np.array([0,-0.4]))]
beacons = beacons[1:]
obstacles = [RectangularObstacle(np.array([[-0.5,0.3], [-0.5, 0.5], [-0.10, 0.5], [-0.10,0.3]], float).T),
             RectangularObstacle(np.array([[0.5,0.5], [0.5, 0.7], [0.10, 0.7], [0.10,0.5]], float).T)]
obstacles = obstacles[0:1]
s = SimEnv2D(bounds=[-0.5, 0.5, -0.1, 1.2], beacons=beacons, obstacles=obstacles)

x0 = np.array([-0.4, 0.2, 0, 0])
car = SimpleCar(x0)
car.attach_sensor(BeaconSensor(decay_coeff=25), lambda x: x[0:2])
s.add_robot(car)

# Number of timesteps
T = 30 #arg

# Dynamics and measurement noise
num_states = car.NX
num_ctrls = car.NU
num_measure = len(beacons)+1 #arg/make part of robot observe
Q = np.mat(np.diag([0.0000001]*num_states)) #arg
R = np.mat(np.diag([0.001]*num_measure)) #arg
R[2,2] = 0.000005
# Sample noise
dynamics_noise = mvn([0]*num_states, Q, T-1).T*0 #FIXME
measurement_noise = mvn([0]*num_measure, R, T-1).T*0 #FIXME

# Setup for EKF
mus = np.mat(np.zeros((num_states,T)))
mus[:,0] = np.mat(x0).T
Sigmas = np.zeros((Q.shape[0], Q.shape[1],T))
Sigmas[:,:,0] = np.mat(np.diag([0.01]*num_states)) #arg
Sigmas[2,2,0] = 0.000000
Sigmas[3,3,0] = 0.000000

# Generate nominal belief trajectory

X_bar = np.mat(np.zeros((car.NX, T)))
X_bar[:,0] = np.mat(x0).T
U_bar = np.ones((car.NU, T-1))*0.4
for t in xrange(1,7):
    U_bar[1,t-1] = 0
for t in xrange(7,10):
    U_bar[1,t-1] = 0.22
for t in xrange(10,15):
    U_bar[1,t-1] = -0.1
for t in xrange(15,30):
    U_bar[1,t-1] = 0
    

for t in xrange(1,T):
    X_bar[:,t] = np.mat(car.dynamics(X_bar[:,t-1], U_bar[:, t-1])) +\
                     np.mat(dynamics_noise[:,t-1]).T 
    mus[:,t], Sigmas[:,:,t] = ekf_update(car.dynamics,
                                         lambda x: car.observe(s, x=x),
                                         Q, R, mus[:,t-1], Sigmas[:,:,t-1],
                                         U_bar[:,t-1], None) #NOTE No obs
                                         
# Plot nominal trajectory with covariance ellipses

ax = plt.gca()
s.draw(ax=ax)

Bel_bar = np.mat(np.zeros((car.NB, T)))
for t in xrange(T):
    Bel_bar[:,t] = np.vstack((X_bar[:,t], cov2vec(Sigmas[:,:,t])))

car.draw_belief_trajectory(Bel_bar)
#plt.show()
#stop

# Apply SCP

As, Bs, Cs = car.linearize_belief_dynamics_trajectory(Bel_bar, U_bar, s, Q, R)

rho_bel = 0.05
rho_u = 0.05
N_iter = 1
goal_bel = np.copy(Bel_bar[:,-1])
goal_bel[car.NX:] = 0

opt_bels, opt_ctrls, opt_vals = scp_solver_beliefs(s, Bel_bar.copy(), U_bar,\
                Q, R, rho_bel, rho_u, goal_bel, N_iter, method='shooting')
Bel_opt = np.mat(np.copy(Bel_bar))
for t in xrange(T-1):
    Bel_opt[:,t+1] = car.belief_dynamics(Bel_opt[:,t], opt_ctrls[:,t], s, Q, R)

car.draw_belief_trajectory(Bel_opt, color='yellow')

plt.show()

