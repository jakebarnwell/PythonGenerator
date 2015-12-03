import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import numpy as np
import matplotlib.pyplot as plt
from sim_env import SimEnv2D, Beacon
from robots import Links 
from optimize import scp_solver_beliefs
from utils import mat2tuple
from sensors import BeaconSensor
from kalman_filter import ekf_update
from covar import cov2vec, vec2cov
from math import pi
# Set up environment

beacons=[Beacon(np.array([0.8, 0.7])), Beacon(np.array([0.7, 0.7]))]


s = SimEnv2D(bounds=[-1, 1, -1, 1], beacons=beacons)
#s = SimEnv2D(bounds=[-3, 3, -3, 3], beacons=beacons)

theta0 = np.array([-0.5, -0.2]) #x0 is broken, just set to 0
origin = np.array([0.0, 0.0])
links = Links(theta0, origin=origin, state_rep='angles')
x0 = np.mat(theta0).T
#x0 = links.forward_kinematics(origin, theta0)
#x0 = np.mat(x0).T
# hack xN
thetaN = np.array([-3.8, -1.9]) # can be looked up using IK
xN = np.mat(thetaN).T
#xN = links.forward_kinematics(origin, thetaN)
#xN = np.mat(xN).T

links.attach_sensor(BeaconSensor(decay_coeff=15), lambda x: links.forward_kinematics(origin, x))
#links.attach_sensor(BeaconSensor(decay_coeff=25), lambda x: x[0:2])

s.add_robot(links)
T = 20
num_states = links.NX
num_ctrls = links.NU
num_measure = len(beacons)#+1 #arg/make part of robot observe

Q = np.mat(np.diag([1e-5]*num_states)) #arg
#Q[2,2] = 1e-4 
#Q[3,3] = 1e-4
R = np.mat(np.diag([0.0005]*num_measure)) #arg
#R[1,1] = 1e-3
#R[2,2] = 1e-3

# Setup for EKF
mus = np.mat(np.zeros((num_states,T)))
mus[:,0] = x0;
Sigmas = np.zeros((Q.shape[0], Q.shape[1],T))
Sigmas[:,:,0] = np.mat(np.diag([0.005]*num_states)) #arg
#Sigmas[2,2,0] = 0.0000001
#Sigmas[3,3,0] = 0.0000001

# Generate a nomimal trajectory
X_bar = np.mat(np.zeros((links.NX, T)))
X_bar[:,0] = x0;
U_bar = np.mat(np.zeros((links.NU, T-1)))
#U_bar = 10*np.mat(np.random.random_sample((links.NU, T-1))) - 5
for t in xrange(1,T):
    U_bar[0, t-1] = 1*float(t)/T 
    U_bar[1, t-1] = 1.2
    X_bar[:,t] = links.dynamics(X_bar[:,t-1], U_bar[:, t-1])
    
    mus[:,t], Sigmas[:,:,t] = ekf_update(links.dynamics,
                                         lambda x: links.observe(s, x=x),
                                         Q, R, mus[:,t-1], Sigmas[:,:,t-1],
                                         U_bar[:,t-1], None) 
    
# Plot nominal trajectory
#ax = plt.subplot(121)
ax = plt.gca()
s.draw(ax=ax)
links.draw_trajectory(mat2tuple(X_bar.T), mus=X_bar, Sigmas=Sigmas[0:2,0:2,:], color='red')
#plt.show()
#stop

Bel_bar = np.mat(np.zeros((links.NB, T)))
for t in xrange(T):
  Bel_bar[:,t] = np.vstack((X_bar[:,t], cov2vec(Sigmas[:,:,t])))

goal_bel = np.copy(Bel_bar[:,-1])
#goal_bel[0:links.NX] = xN; 
goal_bel[links.NX:] = 0


# Apply SCP
rho_bel = 0.1
rho_u = 0.1
N_iter = 3

opt_bels, opt_ctrls, opt_vals = scp_solver_beliefs(s, Bel_bar.copy(), U_bar, \
    Q, R, rho_bel, rho_u, goal_bel, N_iter, links.NX, method='shooting')

# Plot states obtained by applying returned optimal controls

opt_mus = np.mat(np.zeros((links.NX, T)))
opt_mus[:,0] = X_bar[:,0]
opt_X = opt_mus.copy()
opt_Sigmas = np.zeros((Q.shape[0], Q.shape[1],T))
opt_Sigmas[:,:,0] = Sigmas[:,:,0]
opt_ctrls = np.mat(opt_ctrls)

for t in xrange(1,T):
    opt_X[:,t] = links.dynamics(opt_X[:,t-1], opt_ctrls[:,t-1]); 
    opt_mus[:,t], opt_Sigmas[:,:,t] = ekf_update(links.dynamics,
        lambda x: links.observe(s, x=x),  
        Q, R, opt_mus[:,t-1], opt_Sigmas[:,:,t-1], opt_ctrls[:,t-1], None) 

print goal_bel.T
print opt_X[:,T-1].T
#ax = plt.subplot(122)
#s.draw(ax=ax)
links.draw_trajectory(mat2tuple(opt_X.T), mus=opt_mus, Sigmas=opt_Sigmas[0:2,0:2,:], color='green')
plt.show()

