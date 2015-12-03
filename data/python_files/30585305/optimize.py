import numpy as np
import numdifftools as nd
from mlabwrap import mlab
import time
from value_iter_solver import ValueIterationSolver
from covar import cov2vec, vec2cov

def print_status(msg):
    print 
    print '='*80
    print msg
    print '='*80

def value_iteration_solver(sim_env, Bel_bar, U_bar, M, N, rho_bel, rho_u, goal_bel, N_iter, nx): 
    # Efficient Approximate Value Iteration for Continuous Gaussian POMDPs
    # http://www.cs.unc.edu/~sachin/papers/Berg-AAAI2012.pdf
    
    # Optimize a T time-step trajectory
    # sim_env: Environment containing a robot
    # wrapper robot classes
    # Bel_bar: Nominal trajectory beliefs--(NB, T)
    # U_bar: Nominal trajectory controls--(NU, T-1)
    # Q: Dynamics noise
    # R: Measurement noise
    # rho_bel: Trust region on beliefs #TODO Make vec?
    # rho_u: Trust region on controls
    # N_iter: Number of iterations of SCP

    SIZE_BEL = Bel_bar.shape[0]
    SIZE_CTRL = U_bar.shape[0]
    T = Bel_bar.shape[1]
    assert U_bar.shape[1] == T-1, 'Invalid number of controls'
   
    X_bar = np.zeros((nx, T))
    Sigma_bar = np.zeros((nx, nx, T))
    goal_x = goal_bel[0:nx]
    
    for t in range(T):
      X_bar[:,t] = np.array(Bel_bar[0:nx, t]).T
      Sigma_bar[:,:,t] = np.array(vec2cov(Bel_bar[nx:,t]))
      
    solver = ValueIterationSolver(sim_env, M, N, goal_x)
    opt_x, opt_sigma, opt_u = solver.solve(X_bar, Sigma_bar, U_bar, goal_x) 

    pass


def scp_solver_states(robot, X_bar, U_bar, rho_x, rho_u, N_iter, method='collocation'):

    from mlabwrap import mlab
    # Optimize a T time-step trajectory
    # robot: Robot model with dynamics function and linearize function
    # X_bar: Nominal trajectory states--(NX, T)
    # U_bar: Nominal trajectory controls--(NU, T-1)
    # rho_x: Trust region on states
    # rho_u: Trust region on controls
    # N_iter: Number of iterations of SCP

    #TODO Pass in a cost function, pass in constraints?
    # Add nominal cost

    SIZE_STATE = X_bar.shape[0]
    SIZE_CTRL = U_bar.shape[0]
    T = X_bar.shape[1]
    assert U_bar.shape[1] == T-1, 'Invalid number of controls'

    tol = 1e-7 # Quit if improvement after iteration less than this

    opt_vals = list()

    # Run SCP for N_iter iterations
    for k in xrange(N_iter):
        
        print_status('SCP iteration {0}'.format(k+1))
        As, Bs, Cs = robot.linearize_dynamics_trajectory(X_bar, U_bar)

        ''' Call CVX optimizer '''
        opt_states, opt_ctrls, opt_val = mlab.solver_cvx_states(X_bar, U_bar, As, Bs, Cs, \
                rho_x, rho_u, nout=3)

        ''' Doesn't work w/ penalty Jacobians
        if len(opt_vals) > 1 and opt_vals[-1] <= opt_val + tol:
            print_status('Improvement in iteration {0} below tolerance'.format(k+1))
            break
        '''
        opt_vals.append(opt_val)

        if method == 'shooting':
            # Apply optimal controls to obtain new nominal trajectory (shooting)
            U_bar = np.mat(opt_ctrls)
            for t in xrange(T-1):
                X_bar[:,t+1] = robot.dynamics(X_bar[:,t], U_bar[:,t])
        else:
            # No execution (collocation)
            X_bar = np.mat(opt_states)
            U_bar = np.mat(opt_ctrls)

    return opt_states, opt_ctrls, opt_vals

def scp_solver_states_quadratize(robot, X_bar, U_bar, rho_x, rho_u, cost, final_cost, N_iter, method='collocation'):
    # Optimize a T time-step trajectory
    # robot: Robot model with dynamics function and linearize function
    # X_bar: Nominal trajectory states--(NX, T)
    # U_bar: Nominal trajectory controls--(NU, T-1)
    # rho_x: Trust region on states
    # rho_u: Trust region on controls
    # cost: function defining cost(x_t, u_t)
    # final_cost: function defining final_cost(x_t)
    # N_iter: Number of iterations of SCP

    #TODO Pass in a cost function, pass in constraints?
    # Add nominal cost

    SIZE_STATE = X_bar.shape[0]
    SIZE_CTRL = U_bar.shape[0]
    T = X_bar.shape[1]
    assert U_bar.shape[1] == T-1, 'Invalid number of controls'

    tol = 1e-7 # Quit if improvement after iteration less than this

    opt_vals = list()

    # Run SCP for N_iter iterations
    for k in xrange(N_iter):
        
        print_status('SCP iteration {0}'.format(k+1))
        As, Bs, Cs = robot.linearize_dynamics_trajectory(X_bar, U_bar)

        Hs = np.zeros((robot.NX+robot.NU, robot.NX+robot.NU, T-1))
        Js = np.zeros((robot.NX+robot.NU, T-1))
        Gs = np.zeros((1,T-1))

        print 'Numerical quadratization of cost function around nominal'

        for t in range(T-1):
            h = nd.Hessian(  lambda x: cost[t](x[0:robot.NX], x[robot.NX:]))
            j = nd.Jacobian( lambda x: cost[t](x[0:robot.NX], x[robot.NX:]))
            H = h(np.array(np.vstack((X_bar[:,t], U_bar[:,t]))).ravel())
            J = j(np.array(np.vstack((X_bar[:,t], U_bar[:,t]))).ravel())
            Hs[:,:,t] = np.diag(np.diag(H)) 
            Js[:,t] = J
            Gs[:,t] = cost[t](X_bar[:,t], U_bar[:,t])
            w, v = np.linalg.eig(Hs[:,:,t])


        hf = nd.Hessian(final_cost)
        jf = nd.Jacobian(final_cost)
        Hf = hf(np.array(X_bar[:,T-1]).ravel())
        Jf = jf(np.array(X_bar[:,T-1]).ravel())
        Gf = final_cost(X_bar[:,T-1])

        print 'Quadratization complete'





        ''' Call CVX optimizer '''
        opt_states, opt_ctrls, opt_val = mlab.solver_cvx_states_quadratize(X_bar, U_bar,\
         As, Bs, Cs, Hs, Js, Gs, Hf, Jf, Gf, rho_x, rho_u, nout=3)

        ''' Doesn't work w/ penalty Jacobians
        if len(opt_vals) > 1 and opt_vals[-1] <= opt_val + tol:
            print_status('Improvement in iteration {0} below tolerance'.format(k+1))
            break
        '''
        opt_vals.append(opt_val)

        if method == 'shooting':
            # Apply optimal controls to obtain new nominal trajectory (shooting)
            U_bar = np.mat(opt_ctrls)
            for t in xrange(T-1):
                X_bar[:,t+1] = robot.dynamics(X_bar[:,t], U_bar[:,t])
        else:
            # No execution (collocation)
            X_bar = np.mat(opt_states)
            U_bar = np.mat(opt_ctrls)

    return opt_states, opt_ctrls, opt_vals

def scp_solver_beliefs(sim_env, Bel_bar, U_bar, Q, R, rho_bel, rho_u,
        goal_bel, N_iter, nx, method='collocation'):
    
    from mlabwrap import mlab
    # Optimize a T time-step trajectory
    # sim_env: Environment containing a robot
    #FIXME currently assuming just one robot, though may just write
    # wrapper robot classes
    # Bel_bar: Nominal trajectory beliefs--(NB, T)
    # U_bar: Nominal trajectory controls--(NU, T-1)
    # Q: Dynamics noise
    # R: Measurement noise
    # rho_bel: Trust region on beliefs #TODO Make vec?
    # rho_u: Trust region on controls
    # N_iter: Number of iterations of SCP

    robot = sim_env.robots[0]

    SIZE_BEL = Bel_bar.shape[0]
    SIZE_CTRL = U_bar.shape[0]
    T = Bel_bar.shape[1]
    assert U_bar.shape[1] == T-1, 'Invalid number of controls'

    tol = 1e-7 # Quit if improvement after iteration less than this

    opt_vals = list()

    # Run SCP for N_iter iterations
    for k in xrange(N_iter):
        
        print_status('SCP iteration {0}'.format(k+1))

        J_A = robot.collision_penalty_jacobian_trajectory(Bel_bar, U_bar, sim_env)

        print 'Done computing collision penalty Jacobian.'

        As, Bs, Cs = robot.linearize_belief_dynamics_trajectory(Bel_bar,\
                U_bar, sim_env, Q, R)

        print 'Done computing dynamics Jacobians.'

        ''' Call CVX optimizer '''
        opt_bels, opt_ctrls, opt_val = mlab.scp_solver_cvx(Bel_bar, U_bar, As,\
                Bs, Cs, J_A, rho_bel, rho_u, goal_bel, nx, nout=3)
        '''
        if len(opt_vals) > 1 and opt_vals[-1] <= opt_val + tol:
            print_status('Improvement in iteration {0} below tolerance'.format(k+1))
            break
        '''
        opt_vals.append(opt_val)

        U_bar = np.mat(opt_ctrls)
        if method == 'shooting':
            # Apply optimal controls to obtain new nominal trajectory (shooting)
            for t in xrange(T-1):
                Bel_bar[:,t+1] = robot.belief_dynamics(Bel_bar[:,t], U_bar[:,t],\
                        sim_env, Q, R)
        elif method == 'mixture':
            # No execution (collocation)
            Bel_bar = np.mat(opt_bels)
        #TODO? Some mixture method, e.g. collocation for states and shooting
        # covariances

    return opt_bels, opt_ctrls, opt_vals

