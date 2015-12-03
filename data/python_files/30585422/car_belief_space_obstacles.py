import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import numpy as np
import matplotlib.pyplot as plt
from sim_env import SimEnv2D, Beacon, CircularObstacle
from robot.car import SimpleCar
from sensors import BeaconSensor
from utils import mat2tuple
import random
from math import log
from numpy.random import multivariate_normal as mvn
from kalman_filter import ekf_update
from covar import cov2vec, vec2cov
from optimize import scp_solver_beliefs
from scipy.io import loadmat

'''
Copied from car_ekf.py, really need to start sticking stuff in
function
'''

d = loadmat('../../../roboscp/car/ex1.mat')
'''
print d
stop
print d['dat_states'].shape
print d['dat_ctrls'].shape
'''

# Set up environment #args

beacons=[Beacon(np.array([0.3,0.7])),
         Beacon(np.array([0.8,-0.1]))]
obstacles = [CircularObstacle(0.5, 0.63, 0.08)]
s = SimEnv2D(bounds=[-0.1, 1.3, -0.1, 1], beacons=beacons, obstacles=obstacles)

x0 = d['dat_states'][:,0]
car = SimpleCar(x0)
car.attach_sensor(BeaconSensor(decay_coeff=25), lambda x: x[0:2])

s.add_robot(car)

# Number of timesteps
T = 30 #arg

# Dynamics and measurement noise
num_states = car.NX
num_ctrls = car.NU
num_measure = len(beacons)+2 #arg/make part of robot observe
Q = np.mat(np.diag([0.000001]*num_states)) #arg
Q[2,2] = 0 # Gets out of hand if noise in theta or phi
Q[3,3] = 0 # Can also add theta/phi to measurement like Sameep #TODO?
R = np.mat(np.diag([0.0005]*num_measure)) #arg
R[2,2] = 0.000005
R[3,3] = 0.000005
# Sample noise
dynamics_noise = mvn([0]*num_states, Q, T-1).T*0 #FIXME
measurement_noise = mvn([0]*num_measure, R, T-1).T*0 #FIXME

# Setup for EKF
mus = np.mat(np.zeros((num_states,T)))
mus[:,0] = np.mat(x0).T
Sigmas = np.zeros((Q.shape[0], Q.shape[1],T))
Sigmas[:,:,0] = np.mat(np.diag([0.0001]*num_states)) #arg
Sigmas[2,2,0] = 0.0000001
Sigmas[3,3,0] = 0.0000001

# Generate nominal belief trajectory

'''
X_bar = np.mat(np.zeros((car.NX, T))) #arg
X_bar[:,0] = np.mat(x0).T
U_bar = np.load('data/nominal_trajectory.npy')
#U_bar = np.random.random((car.NU, T-1))
#for t in xrange(1,T):
    #U_bar[1,t-1] = (U_bar[1,t-1] - 0.5)
#np.save('data/nominal_trajectory', U_bar)
'''
X_bar = np.mat(d['dat_states'])
U_bar = np.mat(d['dat_ctrls'])

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
#print Sigmas
#car.draw_trajectory(mat2tuple(X_bar.T), mus=X_bar, Sigmas=Sigmas[0:2,0:2,:])

Bel_bar = np.mat(np.zeros((car.NB, T)))
for t in xrange(T):
    Bel_bar[:,t] = np.vstack((X_bar[:,t], cov2vec(Sigmas[:,:,t])))
As, Bs, Cs = car.linearize_belief_dynamics_trajectory(Bel_bar, U_bar, s, Q, R)
for t in xrange(T-1):
    # Overwrites Bel_bar
    #NOTE Keep making mistake in line below
    # Small mismatch occurs due to dynamics noise
    Bel_bar[:,t+1] = Cs[:,t]#As[:,:,t]*Bel_bar[:,t] + Bs[:,:,t]*np.mat(U_bar[:,t]).T + Cs[:,t]

car.draw_belief_trajectory(Bel_bar)
#plt.show()
#stop

# Apply SCP

rho_bel = 0.05
rho_u = 0.05
N_iter = 5
goal_bel = np.copy(Bel_bar[:,-1])
goal_bel[car.NX:] = 0

opt_bels, opt_ctrls, opt_vals = scp_solver_beliefs(s, Bel_bar.copy(), U_bar,\
                Q, R, rho_bel, rho_u, goal_bel, N_iter, method='shooting')
Bel_opt = np.mat(np.copy(Bel_bar))
for t in xrange(T-1):
    Bel_opt[:,t+1] = car.belief_dynamics(Bel_opt[:,t], opt_ctrls[:,t], s, Q, R)

car.draw_belief_trajectory(Bel_opt, color='yellow')

plt.show()

