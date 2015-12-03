
import time
from math import degrees, pi

from ..LocalFuncs import angleBetween, getCorners, relativeAngle, abst2pixel, pixel2abst, abst2astar, astar2abst, getKickingPos, getSquareInFrontOfBall, getBallRobotDist, abst2cm
from ..Shared.Funcs import simpleAngle, getWheelSpeeds, vecDist
from ..Params import Params
from ..Model.PathFinding import *
from ..Drawing.Drawable import Line, Cross, Circle
from .NavigatePID import moveTo

from ..Decision.Strategy import Strategy
from ..Decision.Percept import *
from ..Decision.Decision import Decision
from ..Simulator.Util.Lookahead import IntersectionNotFound

#from ..Logging.SingleLog import Log
class L:
    def d(self, tag, message):
        pass
Log = L()
import numpy

TAG = "SIMPLEACTIONS"

def kick(strategy):
    strategy.getRobot().kick()
        
def doStartRush(strategy):
    r = strategy.getRobot()
    w = strategy.getWorld()
    
    dist = abst2cm(getBallRobotDist(w))
    
    print dist
    
    r.startRush( dist )
    
    

def stopSleep(strategy, sleeptime):
    strategy.getRobot().stop()
    Log.d(TAG, "Stop Sleep is true!!")
    time.sleep(sleeptime)

def faceBall(strategy):
    r = strategy.getRobot()
    w = strategy.getWorld()
    bot = w.getUs()
    ball = w.getBall()
    angle = angleBetween(bot, ball)
    if abs(angle) > 0.3:
        r.turn(angle)
        time.sleep(0.3)    
        r.stop()
        
        
def moveToInterception(strategy, maxspeed=None):    
    try:      
        (x,y) = strategy.getExtra('Goal Position')
    except KeyError:
        Log.d(TAG, "moveToInterception - KeyError")
        return
    goal = computeIntersection(strategy.getWorld(), gx = x)
    changeGoal(strategy, goal)
    if not maxspeed:
        moveTo(strategy, gpos=strategy.getExtra('Goal Position'))
        return
    moveTo(strategy, gpos=strategy.getExtra('Goal Position'), maxspeed = maxspeed)
    
def moveToGoalPos(strategy):    
    try:
        moveTo(strategy, gpos=strategy.getExtra('Goal Position'))
    except KeyError:
        Log.d(TAG, "moveToGoalPos - KeyError")
    
def changeGoal(strategy, goal):
    Log.d(TAG, "Setting goal position to %s" % (goal,))
    w = strategy.getWorld()
    if goal:
        w.clearLayer('moving to position')
        w.addToDrawing(Cross(goal, colour=(0, 0, 255), abst=True, layer='moving to position'))
        w.addToDrawing(Circle(goal, Params.inBallMotionLineTol, colour=(0,0,255), layer='moving to position'))
    strategy.setExtra('Goal Position', goal)

    moveTo(strategy, gpos = goal)



def defend(strategy):
    world = strategy.getWorld()
    r = strategy.getRobot()
    bot = world.getUs()
    (w, h) = world.getDimensions()
    Log.d("DEFEND", "ball_pos %f %f" % world.getBall().getPosition())
    Log.d("DEFEND", "w %d h %d" % (w,h))
    goal = (w - 50, -500)
    if world.getTheirSide() == "high":
        goal = (-w + 50, -500)
    Log.d("DEFEND", goal)
    angle = relativeAngle(bot, goal)
    Log.d("DEFEND", "angle %f" % degrees(angle))
    if abs(angle) > 0.3:
        r.turn(angle)
        time.sleep(0.2)
    else:
        r.move(50, 50)


def printVisionData(strategy):
    w = strategy.getWorld()

    print "Yellow Bot  Position: " + str(w.getYellowRobot().getPosition()) \
     + ",  \tOrientation: " + str(degrees(w.getYellowRobot().getAngle())) \
     + "\n            Velocity: " + str(w.getYellowRobot().getVelocity()) \
     + "\nBlue Bot    Position: " + str(w.getBlueRobot().getPosition()) \
     + ",  \tOrientation: " + str(degrees(w.getBlueRobot().getAngle())) \
     + "\n            Velocity: " + str(w.getBlueRobot().getVelocity()) \
     + "\nBall        Position: " + str(w.getBall().getPosition()) \
     + "\n            Velocity: " + str(w.getBall().getVelocity()) + "\n"

def printPrediction(strategy):
    print strategy.getPredictor().get_intersection_ball_us()


def dribble(strategy):
    r = strategy.getRobot()
    r.move(10,10)
    time.sleep(0.3)
    r.move(30,30)
    time.sleep(0.3)
    r.move(50,50)
    time.sleep(0.4)
    r.move(80,80)
    time.sleep(0.7)
    r.stop()
    strategy.finish()
    
def straightSpeedTest(strategy):
    r = strategy.getRobot()
    r.move(40,40)
    time.sleep(0.2)
    r.getVelocity
    time.sleep(0.2)
    r.getVelocity
    time.sleep(0.2)
    r.getVelocity
    time.sleep(0.2)
    r.getVelocity
    time.sleep(0.2)
    r.getVelocity
    time.sleep(0.2)
    r.getVelocity
    time.sleep(0.2)
    r.getVelocity
    time.sleep(0.2)
    r.getVelocity
    time.sleep(0.2)
    r.getVelocity
    time.sleep(0.2)
    r.getVelocity
    r.stop()
    strategy.finish()


def debugPrediction(strategy):
    w = strategy.getWorld()
    #w.clearLayer('moving to position')
    p = strategy.getPredictor().get_ball_position()

    w.addToDrawing(Circle(p, 100, colour=(0, 0, 255), abst=True, layer='moving to position'))
    print "Predicted Position: " + str(p)

def catch_ball(strategy):
    try:
        p = strategy.getPredictor().get_intersection_ball_us()
    except IntersectionNotFound:
        p = strategy.getPredictor().get_ball_position()

    moveTo(strategy, p)

    w = strategy.getWorld()
    #w.clearLayer('moving to position')

    w.addToDrawing(Circle(p, 100, colour=(0, 0, 255), abst=True, layer='moving to position'))
    print "Predicted Position: " + str(p)
