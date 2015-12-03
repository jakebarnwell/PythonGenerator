import Blender
from Blender import Camera, Object, Scene, NMesh
from Blender import Mathutils
from Blender.Mathutils import *

file = "loadme.txt"
fps = 25


#Load data from file.

orientationTimeStamp = []
orientationXValues = []
orientationYValues = []
orientationZValues = []
accelerationTimeStamp = []
accelerationXValues = []
accelerationYValues = []
accelerationZValues = []

lines = open(file,"r").readlines()
i = lines.index("Acceleration\n")
for line in lines[1:i-1] :
    lineSplit = line.split()
    orientationTimeStamp.append( float(lineSplit[0]) / 1000000000.0 )
    orientationXValues.append( float(lineSplit[1]) )
    orientationYValues.append( float(lineSplit[2]) )
    orientationZValues.append( float(lineSplit[3]) )
for line in lines[i+1:] :
    lineSplit = line.split()
    accelerationTimeStamp.append( float(lineSplit[0]) / 1000000000.0 )
    accelerationXValues.append( float(lineSplit[1]) )
    accelerationYValues.append( float(lineSplit[2]) )
    accelerationZValues.append( float(lineSplit[3]) )

#Create the camera

cur = Scene.getCurrent()

cam = Camera.New('persp')
cam.lens = 35.0
cam.setDrawSize(1.0)
obj = Object.New('Camera')
obj.name = "imported_camera"
obj.link(cam)
cur.link(obj)
cur.setCurrentCamera(obj)

ipo = Blender.Ipo.New('Object','camera_ipo')
obj.setIpo(ipo)

locx = ipo.addCurve('LocX')
locx.setInterpolation('Linear')
locy = ipo.addCurve('LocY')
locy.setInterpolation('Linear')
locz = ipo.addCurve('LocZ')
locz.setInterpolation('Linear')

rotx = ipo.addCurve('RotX')
rotx.setInterpolation('Bezier')
roty = ipo.addCurve('RotY')
roty.setInterpolation('Bezier')
rotz = ipo.addCurve('RotZ')
rotz.setInterpolation('Bezier')

#Set its orientation

for index, time in enumerate(orientationTimeStamp) :
    time = float(time - orientationTimeStamp[0]) * fps
    rotx.addBezier((time, orientationXValues[index] / 10.0 ))
    roty.addBezier((time, orientationYValues[index] / 10.0 ))
    rotz.addBezier((time, orientationZValues[index] / 10.0 ))


#Because acceleration has gravity, it needs to be processed first


#Then compute the speed and position.
speedXValues = [0.0]
speedYValues = [0.0]
speedZValues = [0.0]
positionXValues = [0.0]
positionYValues = [0.0]
positionZValues = [0.0]
#Integrate the acceleration to get speed
#Use Euler (maybe Runge-Kutta or something else would be better)
for i in range(0, len(accelerationXValues)-1) :
    dt = accelerationTimeStamp[i+1] - accelerationTimeStamp[i]
    speedXValues.append( speedXValues[i] + accelerationXValues[i] * dt )
    speedYValues.append( speedYValues[i] + accelerationYValues[i] * dt )
    speedZValues.append( speedZValues[i] + accelerationZValues[i] * dt )
#integrate the speed to get position
for i in range(0, len(accelerationXValues)-1) :
    dt = accelerationTimeStamp[i+1] - accelerationTimeStamp[i]
    positionXValues.append( positionXValues[i] + speedXValues[i] * dt )
    positionYValues.append( positionYValues[i] + speedYValues[i] * dt )
    positionZValues.append( positionZValues[i] + speedZValues[i] * dt )


for index, time in enumerate(accelerationTimeStamp) :
    time = float(time - accelerationTimeStamp[0]) * fps
    locx.addBezier((time, positionXValues[index] ))
    locy.addBezier((time, positionYValues[index] ))
    locz.addBezier((time, positionZValues[index] ))

empty= Object.New('Empty','imported_camera_scene')
empty.setLocation(0.0,0.0,0.0)
cur.link(empty)
empty.makeParent([obj])
