import os, sys
up_path = os.path.abspath('..')
sys.path.append(up_path)
from numpy import *
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rc
from objects import SimObject
from utils import scalar
from covar import draw_ellipsoid, vec2cov, cov2vec,\
    project_psd
from kalman_filter import ekf_update
from numpy.random import multivariate_normal as mvn
import time
from math import atan2, atan
import robots
from openravepy import * 
from transforms import unscented_transform
from rave_draw import * 
#import openravepy as rave 

class RaveLocalizerBot(robots.Robot):

    NX = -1
    NU = -1

    def __init__(self, bot, obj):
        self.bot = bot
        self.NX = bot.NX + 3 #FIXME (hack for now)
        self.NU = bot.NU
        self.dt = bot.dt
        
        x = array(zeros((self.NX)))
        for t in range(bot.NX):
            x[t] = bot.x[t]
        x[bot.NX] = obj[0]
        x[bot.NX+1] = obj[1]
        x[bot.NX+2] = obj[2]
        self.EPS = bot.EPS

  
        robots.Robot.__init__(self, x, dt=self.dt)

    def dynamics(self, X, u):
        bot_up = self.bot.dynamics(X[0:self.bot.NX], u)
        return vstack((bot_up, X[self.bot.NX:]))

    def collision_penalty_trajectory(self, x, env):
        return 0 #Todo: FIXME

    def camera_obj_state(self,x):
        #Returns the transform of the camera and object
        camera_transform = self.bot.camera_transform(x[0:self.bot.NX])

        obj_pos = x[self.bot.NX:]

        z = mat(zeros((10,1)))
        z[0:7] = camera_transform
        z[7:10] = obj_pos

        return z
    """
    def fov_state(self, x):
        xy = mat(self.bot.traj_pos(x)).T
        theta = self.bot.orientation(x)
        #print vstack((xy, theta, x[self.bot.NX:]))
        if isinstance(x, tuple) or len(x.shape) == 1:
            x = mat(x).T
        if isinstance(xy, tuple) or xy.shape[0] < xy.shape[1]:
            xy = mat(xy).T
        return vstack((xy, theta, x[self.bot.NX:]))
    """

    def observe(self, scene, x=None):
        zs = self.bot.observe(scene, x[0:self.bot.NX])
        return vstack((zs, robots.Robot.observe(self, scene, x)))

    def draw_trajectory(self, xs, mus=None, Sigmas=None, color=array((1.0, 0.0, 0.0, 0.2))):
        bnx = self.bot.NX
        self.bot.draw_trajectory(xs[0:bnx], mus[0:bnx], Sigmas[0:bnx, 0:bnx], color)
  
    def draw(self, X=None, color=array((1.0, 0.0, 0.0))):
        self.bot.draw(x[0:bnx], color)
 
            


class BarretWAM(robots.Robot):
    # wrapper for openrave robots
    NX = 7 
    NU = 7 
    EPS = 1e-3
    
    def __init__(self, ravebot, env, state_rep='angles', dt=-1):

        self.ravebot = ravebot
        self.env = env # used for drawing purposes
        self.state_rep = state_rep 
        self.handles = [ ] # used for drawing purposes
        self.jointnames = ['Shoulder_Yaw', 'Shoulder_Pitch', 'Shoulder_Roll', 'Elbow', 'Wrist_Yaw', 'Wrist_Pitch', 'Wrist_Roll']
        self.jointidxs = [ravebot.GetJoint(name).GetDOFIndex() for name in self.jointnames]
        self.ravebot_manip = self.ravebot.SetActiveManipulator('arm')
        self.lower_limits, self.upper_limits = self.ravebot.GetDOFLimits()
        tmp_lower_limits = []
        tmp_upper_limits = []
        for idx in self.jointidxs:
            tmp_lower_limits.append(self.lower_limits[idx])
            tmp_upper_limits.append(self.upper_limits[idx])
        self.lower_limits = mat(array(tmp_lower_limits)).T
        self.upper_limits = mat(array(tmp_upper_limits)).T



        self.ravebot.SetActiveDOFs(self.jointidxs)
        x = [0] * len(self.jointidxs)
        robots.Robot.__init__(self, x, dt=dt)
        self.index = BarretWAM.increment_index()


    def traj_pos(self, x=None):
        if x == None:
            x = self.x

        if self.state_rep == 'angles':
            return mat(self.forward_kinematics(x)[0:3,3])
        else: #state representation = points 
            pass
    
    def orientation(self, x=None):
        if x == None:
            x = self.x
      
        if self.state_rep == 'angles':
            return self.forward_kinematics(x)[0:3,0:3]
        else:
            pass 

    def __str__(self):
        return 'ravebot[' + str(self.index) + ']'

    def dynamics(self, x, u):
        if self.state_rep == 'angles':
            thetas = x + u
            thetas = minimum(thetas, self.upper_limits)
            thetas = maximum(thetas, self.lower_limits)
            """
            for i in range(thetas.shape[0]):
                if thetas[i] > self.upper_limits[i]:
                    thetas[i] = self.upper_limits[i]
                elif thetas[i] < self.lower_limits[i]:
                    thetas[i] = self.lower_limits[i]
            """
            return thetas
        else:
            pass 

    def camera_transform(self, x):
        camera_rel_transform = self.ravebot.GetAttachedSensor('camera').GetRelativeTransform()
        with self.env:
            self.ravebot.SetDOFValues(x, self.jointidxs)
            link_transform = mat(self.ravebot.GetLink('wam4').GetTransform())
        camera_trans = link_transform * camera_rel_transform
        camera_quat = quatFromRotationMatrix(array(camera_trans[0:3,0:3]))
        camera_vec = mat(zeros((7,1)))
        camera_vec[0:3] = camera_trans[0:3,3]
        camera_vec[3:7] = mat(camera_quat).T
        return camera_vec



    def observe(self, scene, x=None):
        if x==None:
            x = self.x
        zs = robots.Robot.observe(self, scene, x)
        # also give joint angle observations
        #if zs.size > 0:
        #    pass
            #zs = vstack((zs, mat('x[2]')))
            #zs = vstack((zs, mat('x[3]')))
        #else:
        #    zs = mat('x[3]')
        return zs

    def forward_kinematics(self, thetas):
        with self.env:
            self.ravebot.SetDOFValues(thetas,self.jointidxs)
            return mat(self.ravebot_manip.GetEndEffectorTransform())
        
  
    def inverse_kinematics(self, xyz):
        pass 

    def draw_Cspace(self, X=None, color='blue'):
        pass 

    def collision_penalty_trajectory(self, x, env):
        return 0 #Todo: FIXME

    def draw_trajectory(self, xs, mus=None, Sigmas=None, color=array((1.0, 0.0, 0.0, 0.2))):
        T = xs.shape[1]
        XYZ = mat(zeros((3,T)))
        for t in range(T):
            XYZ[:,t] = self.traj_pos(xs[:,t])

        if mus != None and Sigmas != None:
            for t in range(T):
                    mu_y, Sigma_y = unscented_transform(mus[:,t], Sigmas[:,:,t],\
                     lambda x: self.traj_pos(x))
                    # padding for positive definiteness
                    Sigma_y = Sigma_y + 0.0001 * identity(3)  
                    self.handles.append(draw_ellipsoid(mu_y, Sigma_y, std_dev=2,\
                        env=self.env, colors=color))



        #self.handles.append(self.env.drawlinestrip(points=array(((xyz[0], xyz[1], xyz[2]),(0.0, 0.0,0.0))),
        #                    linewidth=3.0))

        self.handles.append(self.env.drawlinestrip(points=XYZ.T, linewidth=3.0, colors=color[0:3]))

    def draw(self, X=None, color=array((1.0, 0.0, 0.0))):

        if X == None:
            X = self.x
        
        xyz = self.traj_pos(X)
        with self.env:
            """
            # works with only a few robots
            newrobot = RaveCreateRobot(self.env,self.ravebot.GetXMLId())
            newrobot.Clone(self.ravebot,0)
            for link in newrobot.GetLinks():
                for geom in link.GetGeometries():
                    geom.SetTransparency(0.6)
            self.env.Add(newrobot,True)
            newrobot.SetActiveDOFs(self.jointidxs)
            newrobot.SetDOFValues(X, self.jointidxs)

            self.handles.append(newrobot)
            """ 
       
            self.handles.append(self.env.plot3(points=xyz, pointsize=1.0, colors=color))
