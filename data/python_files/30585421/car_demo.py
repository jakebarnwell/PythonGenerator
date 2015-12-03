import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
import numpy as np
import matplotlib.pyplot as plt
from sim_env import SimEnv2D
from robot.car import SimpleCar 
from optimize import scp_solver_states
from utils import mat2tuple
from random import random

########################################
#TODO WRAP THIS ALL UP INTO A FUNCTION #
########################################

# Set up environment

s = SimEnv2D(bounds=[-1, 1, -1, 1])

x0 = np.array([0, 0, 0, np.pi/2])
car = SimpleCar(x0)

s.add_robot(car)

T = 30
X_bar = np.mat(np.zeros((car.NX, T)))
U_bar = np.mat(np.zeros((car.NU, T-1)))
#U_bar = np.mat(np.random.random_sample((car.NU, T-1)))/5
for t in xrange(1,T):
    U_bar[0,t-1] = 0.3
    U_bar[1,t-1] = 0.1
    if t > T / 2:
        U_bar[0,t-1] = 0
        U_bar[1,t-1] = -U_bar[1,t-1]

    X_bar[:,t] = car.dynamics(X_bar[:,t-1], U_bar[:, t-1])

# Plot nominal trajectory

ax = plt.subplot(221)
plt.title('Nominal')
s.draw(ax=ax)
car.draw_trajectory(mat2tuple(X_bar.T))

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

# Apply SCP

rho_x = 0.1
rho_u = 0.1
N_iter = 20
opt_states, opt_ctrls, opt_vals = scp_solver_states(car, X_bar, U_bar, rho_x, rho_u,\
                                             N_iter, method='shooting')

# Plot returned optimal states

ax = plt.subplot(222)
s.draw(ax=ax)
plt.title('Opt States')
car.draw_trajectory(mat2tuple(opt_states.T))

# Plot states obtained by applying returned optimal controls

X = np.mat(np.zeros((car.NX, T)))
X[:,0] = X_bar[:,0]
for t in xrange(0,T-1):
    X[:,t+1] = car.dynamics(X[:,t], opt_ctrls[:,t])

ax = plt.subplot(223)
s.draw(ax=ax)
plt.title('Applying Opt Ctrls')
car.draw_trajectory(mat2tuple(X.T))

# Plot cost over time

ax = plt.subplot(224)
plt.title('Cost over iterations')
plt.xlabel('iteration')
plt.ylabel('cost')
iters = [i for i in xrange(1,len(opt_vals)+1)]
ax.xaxis.set_ticks(iters)
plt.plot(iters, [v.item(0) for v in opt_vals])

plt.show()


