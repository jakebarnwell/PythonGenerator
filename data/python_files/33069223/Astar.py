
import time
from math import degrees, pi

from ..LocalFuncs import angleBetween, getCorners, relativeAngle, abst2pixel, pixel2abst, abst2astar, astar2abst, getKickingPos, getSquareInFrontOfBall
from ..Shared.Funcs import simpleAngle, getWheelSpeeds, vecDist
from ..Params import Params
from ..Model.PathFinding import *
from ..Drawing.Drawable import Line, Cross

from ..Decision.Strategy import Strategy
from ..Decision.Percept import *
from ..Decision.Decision import Decision
from NavigatePID import moveTo

from ..Logging.SingleLog import Log
import numpy

def plotPath(strategy, destination):
# TODO: rename
    r = strategy.getRobot()
    w = strategy.getWorld()

    bot = w.getUs()
    botThem = w.getThem()
    ball = w.getBall()

    dimensions = w.getDimensions()

    w.clearLayer('goal')    
    w.addToDrawing(Cross(destination, abst=True, colour=(255, 0, 0), layer='goal'))

    bot_raw_pos = bot.getPosition()
    them_raw_pos = botThem.getPosition()
    ball_raw_pos = ball.getPosition()

    goal_converted_pos = abst2astar(destination)
    bot_converted_pos = abst2astar(bot_raw_pos)
    ball_converted_pos = abst2astar(ball_raw_pos)
    them_converted_pos = abst2astar(them_raw_pos)

    graph = Graph(int(dimensions[0]), int(dimensions[1]), 50, 25)

    destinationNode = graph.getNode(*goal_converted_pos)
    ballNode = graph.getNode(*ball_converted_pos)

    graph.setUs(*bot_converted_pos)
    graph.setThem(*them_converted_pos)
    
    graph.blacklistRect(map(abst2astar, getCorners(botThem, Params.robotSizeToleranceAvoiding)))
    graph.addToBadNodes(map(abst2astar, getSquareInFrontOfBall(w)))
    graph._us.blacklist(False)

    
    path = graph.findPath(graph._us, destinationNode) 
    
    if not(path):
        Log.d("ASTAR", "Path Not Found")
        return False
    path = graph.getPath(path)
    w.clearLayer('path')
    prevpoint = None

    abstractPath = []
    for point in path:
        (x, y) = astar2abst(point.toCoords(40, 40))
        abstractPath.append((x,y))
        (x1, y1) = astar2abst(prevpoint.toCoords(40, 40)) if prevpoint else (x, y)
        w.addToDrawing(Line((x1, y1), (x, y), width=2, colour=(80, 121, 42), abst=True, layer='path'))
        w.addToDrawing(Cross((x, y), abst=True, layer='path'))
        prevpoint = point

    return abstractPath

def navigateTo(strategy, destination = None, maxspeed = None):
    # Uses Astar to calculate an optimal path - default destination is kickingPoint behind the ball
    w = strategy.getWorld()
    if not destination:
        destination = getKickingPos(w, Params.kickingDistBall)
    bot = w.getUs()
    w.clearLayer('goalpost')
    w.addToDrawing(Cross(w.getTheirGoalpost(), colour=(255, 0, 0), abst=True, layer='goalpost'))
    
    path = plotPath(strategy, destination)
    if path and len(path) > 1:
        targetX, targetY = path.pop(1)
        move_to_point(strategy, bot, (targetX, targetY), maxspeed)
    else:
        Log.d("ASTAR", "Close to destination, navigate with PID")

    Log.d("ASTAR", "Exiting A* algorithm")

    
def move_to_point(strategy, bot, dest, maxspeed, timeout=0.6):
    start_time = time.time()
    while (not(bot.at(dest)) and time.time()-start_time < timeout):
        moveTo(strategy, dest, maxspeed = maxspeed)
        time.sleep(0.04)
    Log.d("MOVETOPOINT", "MADE IT")
    

