import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import numpy as np
import matplotlib.pyplot as plt
from sim_env import SimEnv2D, Beacon, CircularObstacle, RectangularObstacle
from robots import SimpleCar
from sensors import BeaconSensor
from utils import mat2tuple
import random
from math import log
from numpy.random import multivariate_normal as mvn
from kalman_filter import ekf_update
from covar import cov2vec, vec2cov
from optimize import value_iteration_solver
from scipy.io import loadmat

# Set up environment #args

beacons=[Beacon(np.array([0.2,0.2])),
         Beacon(np.array([1.2, 0.5])),
         Beacon(np.array([0.2, 0.8]))]
#obstacles = [RectangularObstacle(np.array([[0.75, 0.2], [0.75, 0.4], [0.85, 0.4], [0.85,0.2]], float).T),\
#             RectangularObstacle(np.array([[0.5,0.85], [1.15,0.85], [1.15,0.6], [0.5,0.6]], float).T)]
obstacles = []

s = SimEnv2D(bounds=[-0.1, 1.5, -0.1, 1], beacons=beacons, obstacles=obstacles)

x0 = np.array([0, 0.5, 0, 0])
car = SimpleCar(x0)
car.attach_sensor(BeaconSensor(decay_coeff=25), lambda x: x[0:2])

s.add_robot(car)

# Number of timesteps
T = 30 #arg

# Dynamics and measurement noise
num_states = car.NX
num_ctrls = car.NU
num_measure = len(beacons)+1 #arg/make part of robot observe
Q = np.mat(np.diag([1e-5]*num_states)) #arg
Q[2,2] = 1e-8 # Gets out of hand if noise in theta or phi
Q[3,3] = 1e-8 # Can also add theta/phi to measurement like Sameep #TODO?
R = np.mat(np.diag([0.005]*num_measure)) #arg
R[3,3] = 1e-9
# Sample noise
dynamics_noise = mvn([0]*num_states, Q, T-1).T*0 #FIXME
measurement_noise = mvn([0]*num_measure, R, T-1).T*0 #FIXME

# Setup for EKF
mus = np.mat(np.zeros((num_states,T)))
mus[:,0] = np.mat(x0).T
Sigmas = np.zeros((Q.shape[0], Q.shape[1],T))
Sigmas[:,:,0] = np.mat(np.diag([0.0002]*num_states)) #arg
Sigmas[2,2,0] = 0.0000001
Sigmas[3,3,0] = 0.0000001

# Generate nominal belief trajectory

X_bar = np.mat(np.zeros((car.NX, T))) #arg
X_bar[:,0] = np.mat(x0).T
U_bar = np.ones((car.NU, T-1))*0.35
for t in xrange(1,T):
    U_bar[1,t-1] = -0.005
    
#print U_bar

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
car.draw_trajectory(mat2tuple(X_bar.T), mus=X_bar, Sigmas=Sigmas[0:2,0:2,:])
#plt.show()
#stop

Bel_bar = np.mat(np.zeros((car.NB, T)))
for t in xrange(T):
    Bel_bar[:,t] = np.vstack((X_bar[:,t], cov2vec(Sigmas[:,:,t])))
As, Bs, Cs = car.linearize_belief_dynamics_trajectory(Bel_bar, U_bar, s, Q, R)
for t in xrange(T-1):
    # Overwrites Bel_bar
    #NOTE Keep making mistake in line below
    # Small mismatch occurs due to dynamics noise
    Bel_bar[:,t+1] = Cs[:,t]#As[:,:,t]*Bel_bar[:,t] + Bs[:,:,t]*np.mat(U_bar[:,t]).T + Cs[:,t]

# Apply value iteration
rho_bel = 0.1
rho_u = 0.05
N_iter = 1
goal_bel = np.copy(Bel_bar[:,-1])
goal_bel[car.NX:] = 0

opt_bels, opt_ctrls, opt_vals = value_iteration_solver(s, Bel_bar.copy(), U_bar, Q, R, rho_bel, rho_u, goal_bel, N_iter, car.NX)

stop 
Bel_opt = np.mat(np.copy(Bel_bar))
for t in xrange(T-1):
    Bel_opt[:,t+1] = car.belief_dynamics(Bel_opt[:,t], opt_ctrls[:,t], s, Q, R)

car.draw_belief_trajectory(Bel_opt, color='yellow')

plt.show()

