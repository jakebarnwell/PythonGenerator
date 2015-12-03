import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import numpy as np
import matplotlib.pyplot as plt
from sim_env import SimEnv2D
from robots import Links 
from optimize import scp_solver_states
from utils import mat2tuple

########################################
#TODO WRAP THIS ALL UP INTO A FUNCTION #
########################################

# Set up environment

s = SimEnv2D(bounds=[-1, 1, -1, 1])

x0 = np.array([0.1, 0.2])
links = Links(x0)

s.add_robot(links)
T = 50

X_bar = np.mat(np.zeros((links.NX, T)))
U_bar = np.mat(np.random.random_sample((links.NU, T-1)))/2
print U_bar
for t in xrange(1,T):
    X_bar[:,t] = links.dynamics(X_bar[:,t-1], U_bar[:, t-1])

# Plot nominal trajectory

ax = plt.gca()
s.draw(ax=ax)
links.draw_trajectory(mat2tuple(X_bar.T))
#plt.show()
#stop
'''
X = np.mat(np.zeros((car.NX, T)))
As, Bs, Cs = car.linearize_dynamics_trajectory(X_bar, U_bar)
for t in xrange(T-1):
    X[:,t+1] = As[:,:,t]*(X[:,t]-X_bar[:,t]) + Bs[:,:,t]*(U_bar[:,t]-U_bar[:,t]) +\
        Cs[:,t]
s.draw()
car.draw_trajectory(mat2tuple(X.T))
plt.show()
'''

exit()

# Apply SCP

rho_x = 0.1
rho_u = 0.1
N_iter = 5
opt_states, opt_ctrls, opt_vals = scp_solver_states(links, X_bar, U_bar, rho_x, rho_u,\
                                             N_iter, method='shooting')


# Plot states obtained by applying returned optimal controls

X = np.mat(np.zeros((links.NX, T)))
opt_ctrls = np.mat(opt_ctrls)
X[:,0] = X_bar[:,0]
print opt_ctrls.shape
print opt_ctrls
for t in xrange(0,T-1):
    X[:,t+1] = links.dynamics(X[:,t], opt_ctrls[:,t])

links.draw_trajectory(mat2tuple(X.T), color='blue')
plt.show()

