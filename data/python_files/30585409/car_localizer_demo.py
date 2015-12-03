import os, sys
#    U_bar[1,t-1] = -0.005
up_path = os.path.abspath('..')
sys.path.append(up_path)
import numpy as np
import matplotlib.pyplot as plt
from sim_env import SimEnv2D, Beacon, CircularObstacle, RectangularObstacle
from robots import LocalizerBot
from robot.car import SimpleCar
from sensors import BeaconSensor, FOVSensor
from math import pi
from utils import mat2tuple
import random
from math import log
from numpy.random import multivariate_normal as mvn
from kalman_filter import ekf_update
from covar import cov2vec, vec2cov
from optimize import scp_solver_beliefs
from scipy.io import loadmat
import matplotlib.animation as animation
colors = ['b', 'g', 'r', 'c', 'm', 'y']
# Set up environment #args

beacons=[Beacon(np.array([0.2,0.2])),
         Beacon(np.array([1.2, 0.5])),
         Beacon(np.array([0.2, 0.8]))]
#obstacles = [RectangularObstacle(np.array([[0.75, 0.2], [0.75, 0.4], [0.85, 0.4], [0.85,0.2]], float).T),\
#             RectangularObstacle(np.array([[0.5,0.85], [1.15,0.85], [1.15,0.6], [0.5,0.6]], float).T)]

obstacles=[]

s = SimEnv2D(bounds=[-0.1, 1.5, -0.1, 1], beacons=beacons, obstacles=obstacles)

ball = np.array([1.4, 0.30])
x0 = np.array([0, 0.5, 0, 0])
car = SimpleCar(x0)
car.attach_sensor(BeaconSensor(decay_coeff=25), lambda x: x[0:2])

localizer = LocalizerBot(car,ball)
x0 = np.mat(localizer.x)
localizer.attach_sensor(FOVSensor(localizer.x, fov_angle=2*pi, decay_coeff=25), lambda x: localizer.fov_state(x))

s.add_robot(localizer)

# Number of timesteps
T = 30 #arg

# Dynamics and measurement noise
num_states = localizer.NX
num_ctrls = localizer.NU
num_measure = len(beacons)+1+1 #arg/make part of robot observe
Q = np.mat(np.diag([1e-5]*num_states)) #arg
Q[2,2] = 1e-8 # Gets out of hand if noise in theta or phi
Q[3,3] = 1e-8 # Can also add theta/phi to measurement like Sameep #TODO?
Q[4,4] = 1e-10 # Can also add theta/phi to measurement like Sameep #TODO?
Q[5,5] = 1e-10 # Can also add theta/phi to measurement like Sameep #TODO?
R = np.mat(np.diag([0.005]*num_measure)) #arg
R[4,4] = 5e-3
#R[3,3] = 1e-9
# Sample noise
dynamics_noise = mvn([0]*num_states, Q, T-1).T*0 #FIXME
measurement_noise = mvn([0]*num_measure, R, T-1).T*0 #FIXME

# Setup for EKF
mus = np.mat(np.zeros((num_states,T)))
mus[:,0] = np.mat(x0).T
Sigmas = np.zeros((Q.shape[0], Q.shape[1],T))
Sigmas[:,:,0] = np.mat(np.diag([0.0002]*num_states)) #arg
Sigmas[2,2,0] = 0.0000001
# Generate nominal belief trajectory

X_bar = np.mat(np.zeros((localizer.NX, T))) #arg
X_bar[:,0] = np.mat(x0).T
U_bar = np.ones((localizer.NU, T-1))*0.35
for t in xrange(1,T):
    U_bar[1,t-1] = -0.005
    
#print U_bar

for t in xrange(1,T):
    X_bar[:,t] = np.mat(localizer.dynamics(X_bar[:,t-1], U_bar[:, t-1])) +\
                     np.mat(dynamics_noise[:,t-1]).T 
    mus[:,t], Sigmas[:,:,t] = ekf_update(localizer.dynamics,
                                         lambda x: localizer.observe(s, x=x),
                                         Q, R, mus[:,t-1], Sigmas[:,:,t-1],
                                         U_bar[:,t-1], None) #NOTE No obs
                                         
# Plot nominal trajectory with covariance ellipses

ax = plt.gca()
s.draw(ax=ax)
localizer.draw_trajectory(mat2tuple(X_bar.T), mus=X_bar, Sigmas=Sigmas[0:2,0:2,:], color='yellow')
localizer.draw_trajectory([], mus=X_bar[4:6,0:1], Sigmas=Sigmas[4:6,4:6,0:1], color='yellow')
localizer.draw_trajectory([], mus=X_bar[4:6,T-2:T-1], Sigmas=Sigmas[4:6,4:6,T-2:T-1], color='yellow')

#for t in range(0,T): 
#  localizer.mark_fov(X_bar[:,t], s, [-1, 1, -1, 1], color=colors[t % len(colors)])
#plt.show()
#stop

Bel_bar = np.mat(np.zeros((localizer.NB, T)))
for t in xrange(T):
    Bel_bar[:,t] = np.vstack((X_bar[:,t], cov2vec(Sigmas[:,:,t])))

'''
fig = plt.gcf()
s.draw_goal_state(Bel_bar[:,-1])
car.draw_trail(mat2tuple(Bel_bar[0:4,:].T))
ims = car.get_animation_artists(Bel_bar)
im_ani = animation.ArtistAnimation(fig, ims, interval=100,
    blit=True)
plt.show()
stop
'''

# Apply SCP

rho_bel = 0.1
rho_u = 0.05
N_iter = 1
goal_bel = np.copy(Bel_bar[:,-1])
goal_bel[0:2] = np.mat(ball).T
goal_bel[localizer.NX:] = 0

opt_bels, opt_ctrls, opt_vals = scp_solver_beliefs(s, Bel_bar.copy(), U_bar,\
               Q, R, rho_bel, rho_u, goal_bel, N_iter, localizer.NX, method='shooting')


opt_mus = np.mat(np.zeros((localizer.NX, T)))
opt_mus[:,0] = X_bar[:,0]
opt_X = opt_mus.copy()
opt_Sigmas = np.zeros((Q.shape[0], Q.shape[1],T))
opt_Sigmas[:,:,0] = Sigmas[:,:,0]
opt_ctrls = np.mat(opt_ctrls)

for t in xrange(1,T):
    opt_X[:,t] = localizer.dynamics(opt_X[:,t-1], opt_ctrls[:,t-1]); 
    opt_mus[:,t], opt_Sigmas[:,:,t] = ekf_update(localizer.dynamics,
        lambda x: localizer.observe(s, x=x),  
        Q, R, opt_mus[:,t-1], opt_Sigmas[:,:,t-1], opt_ctrls[:,t-1], None) 

print goal_bel.T
print opt_X[:,T-1].T
#ax = plt.subplot(122)
#s.draw(ax=ax)
localizer.draw_trajectory(mat2tuple(opt_X.T), mus=opt_mus, Sigmas=opt_Sigmas[0:2,0:2,:], color='green')
localizer.draw_trajectory([], mus=opt_mus[4:6,0:1], Sigmas=opt_Sigmas[4:6,4:6,0:1], color='green')
localizer.draw_trajectory([], mus=opt_mus[4:6,T-2:T-1], Sigmas=opt_Sigmas[4:6,4:6,T-2:T-1], color='green')

plt.show()

