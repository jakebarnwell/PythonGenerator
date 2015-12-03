import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import numpy as np
import matplotlib.pyplot as plt
from sim_env import SimEnv2D, Beacon
from robots import Links, LocalizerBot, Dot
from optimize import scp_solver_beliefs
from utils import mat2tuple
from sensors import BeaconSensor, FOVSensor
from kalman_filter import ekf_update
from covar import cov2vec, vec2cov
from math import pi
colors = ['b', 'g', 'r', 'c', 'm', 'y']
# Set up environment

beacons=[Beacon(np.array([-0.0, 0.6]))]
ball = np.array([-0.4, 0.15])
start_pt = np.array([0.10, -0.3])
#s = SimEnv2D(bounds=[-1, 1, -1, 1], beacons=beacons)
s = SimEnv2D(bounds=[-4, 4, 0, 4], beacons=beacons)

#theta0 = np.array([-2.11, 2.65]) #x0 is broken, just set to 0
theta0 = np.array([-2.26, 2.03]) #x0 is broken, just set to 0
origin = np.array([0.0, 0.0])
links = Links(theta0, origin=origin, state_rep='angles')
x0 = np.mat(theta0).T
print links.forward_kinematics(origin, theta0)
#x0 = links.forward_kinematics(origin, theta0)
#x0 = np.mat(x0).T
# hack xN
#thetaN = np.array([-3.8, -1.9]) # can be looked up using IK
thetaN = links.inverse_kinematics(origin, ball)
#xN = np.vstack((thetaN.T, ball.T))
#xN = np.reshape(xN, (4,1))
xN = np.mat(thetaN).T
print xN

#xN = links.forward_kinematics(origin, thetaN)
#xN = np.mat(xN).T

links.attach_sensor(BeaconSensor(decay_coeff=15), lambda x: links.forward_kinematics(origin, x))
#links.attach_sensor(BeaconSensor(decay_coeff=25), lambda x: x[0:2])

localizer = links # HAAAAAACK!!!!!!
#localizer = LocalizerBot(links, ball)
#x0 = np.mat(localizer.x).T;
#localizer.attach_sensor(FOVSensor(localizer.x, fov_angle=2*pi, decay_coeff=25), lambda x: localizer.fov_state(x))


s.add_robot(localizer)
T = 20
num_states = localizer.NX
num_ctrls = localizer.NU
num_measure = len(beacons)#+1 #arg/make part of robot observe

Q = np.mat(np.diag([1e-5]*num_states)) #arg
#Q[2,2] = 1e-10
#Q[3,3] = 1e-10
R = np.mat(np.diag([0.0005]*num_measure)) #arg
#R[1,1] = 5e-2
#R[2,2] = 1e-3

# Setup for EKF
mus = np.mat(np.zeros((num_states,T)))
mus[:,0] = x0;
Sigmas = np.zeros((Q.shape[0], Q.shape[1],T))
Sigmas[:,:,0] = np.mat(np.diag([0.005]*num_states)) #arg
#Sigmas[2,2,0] = 0.0000001
#Sigmas[3,3,0] = 0.0000001

# Generate a nomimal trajectory
# first the trajectory of pts
ax = plt.gca()
s.draw(ax=ax)

pts= np.mat(np.zeros((localizer.NX, T)))
pts[0,0] = start_pt[0];
pts[1,0] = start_pt[1];
#plt.plot(pts[0,0], pts[1,0], 'o', color='g', markersize=9)
for t in xrange(1,T):
  if t < 10:
    pts[:,t] = pts[:,t-1]
    pts[1,t] = pts[1,t-1] + 0.05
  else:
    pts[:,t] = pts[:,t-1]
    pts[0,t] = pts[0,t-1] - 0.05
  #plt.plot(pts[0,t], pts[1,t], 'o', color='g', markersize=9)

X_bar = np.mat(np.zeros((localizer.NX, T)))
U_bar = np.mat(np.zeros((localizer.NU, T-1)))
X_bar[:, 0] = x0;
for t in xrange(1,T):
  X_bar[0:2, t] = np.mat(links.inverse_kinematics(origin,pts[:,t]).ravel()).T
  U_bar[0:2, t-1] = (X_bar[0:2, t] - X_bar[0:2, t-1]) / localizer.dt
  X_bar[:,t] = localizer.dynamics(X_bar[:,t-1], U_bar[:,t-1])
  mus[:,t], Sigmas[:,:,t] = ekf_update(localizer.dynamics,
                                         lambda x: localizer.observe(s, x=x),
                                         Q, R, mus[:,t-1], Sigmas[:,:,t-1],
                                         U_bar[:,t-1], None) 


#newlinks = Links(np.array([-0.1, 0.1]), origin=origin, state_rep='points')
#newlinks.draw_trajectory(mat2tuple(X_bar.T))
#U_bar = 10*np.mat(np.random.random_sample((links.NU, T-1))) - 5
'''
for t in xrange(1,T):
    U_bar[0, t-1] = 1*float(t)/T 
    U_bar[1, t-1] = 1.2
    if t > 10:
      U_bar[1, t-1] = 0
    X_bar[:,t] = localizer.dynamics(X_bar[:,t-1], U_bar[:, t-1])
    
    mus[:,t], Sigmas[:,:,t] = ekf_update(localizer.dynamics,
                                         lambda x: localizer.observe(s, x=x),
                                         Q, R, mus[:,t-1], Sigmas[:,:,t-1],
                                         U_bar[:,t-1], None) 
'''    
# Plot nominal trajectory
#ax = plt.subplot(121)
ax = plt.gca()
s.draw(ax=ax)
#localizer.draw_trajectory(mat2tuple(X_bar.T), mus=X_bar[0:2,:], Sigmas=Sigmas[0:2,0:2,:], color='red')
localizer.draw_trajectory([], mus=X_bar[0:2,:], Sigmas=Sigmas[0:2,0:2,:], color='red')
#localizer.draw_trajectory([], mus=X_bar[2:4,0:1], Sigmas=Sigmas[2:4,2:4,0:1], color='red')
#localizer.draw_trajectory([], mus=X_bar[2:4,T-2:T-1], Sigmas=Sigmas[2:4,2:4,T-2:T-1], color='red')
#ax.plot(X_bar[2,0], X_bar[3,0], 'yo') 

#for t in range(0,T): 
#  localizer.mark_fov(X_bar[0:2,t], s, [-1, 1, -1, 1], color=colors[t % len(colors)])

#plt.show()
#stop

Bel_bar = np.mat(np.zeros((localizer.NB, T)))

for t in xrange(T):
  Bel_bar[:,t] = np.vstack((X_bar[:,t], cov2vec(Sigmas[:,:,t])))

goal_bel = np.copy(Bel_bar[:,-1])
goal_bel[0:localizer.NX] = xN; 
goal_bel[localizer.NX:] = 0


# Apply SCP
rho_bel = 0.1
rho_u = 0.1
N_iter = 1

opt_bels, opt_ctrls, opt_vals = scp_solver_beliefs(s, Bel_bar.copy(), U_bar, \
    Q, R, rho_bel, rho_u, goal_bel, N_iter, localizer.NX, method='shooting')

# Plot states obtained by applying returned optimal controls

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
#localizer.draw_trajectory(mat2tuple(opt_X.T), mus=opt_mus, Sigmas=opt_Sigmas[0:2,0:2,:], color='green')
localizer.draw_trajectory([], mus=opt_mus, Sigmas=opt_Sigmas[0:2,0:2,:], color='green')

plt.show()
