import os
import sys
import math
import textwrap
import Coordinates
import NECGenerator
from time import gmtime, strftime


def kochCurve(level, lengthSide):
	
	if(level == 0):
		fc.fd(lengthSide)
	else:
		newLengthSide = lengthSide/3.0
		newLevel = level - 1
		
		kochCurve(newLevel, newLengthSide)
		fc.lt(60)
		kochCurve(newLevel, newLengthSide)
		fc.rt(120)
		kochCurve(newLevel, newLengthSide)
		fc.lt(60)
		kochCurve(newLevel, newLengthSide)
	return


def kochSnowflake(level, lengthSide):
	
	for i in range(3):
		kochCurve(level, lengthSide)
		fc.rt(120)
	
	return


def kochCurveCenter(totalLen):
	
	return (segmentLen/2.0, 0)

def findMedianPos(inputList):
	
	length = len(inputList)
	
	return (length/2)		# Floors by default


def kochSegmentLength(level, sideLen):
	
	"""
	totalLen is based off of the combined length of each segment that is
	expressed underneath the Koch Curve.
	"""
	return sideLen/(3**level)

def kochPerimeter(level, sideLen):
	
	return (4**level * sideLen)/(3**level)

def kochSnowflakeCntrPnt(level, segmentLen):
	
	# Calculate one side-length of triangle
	s = segmentLen
	
	# Calculate third vertex point
	v3 = -(math.sqrt(s**2 - (0.25 * (s**2))))
	
	# Calculate centroid; remember that the first coordinates is always (0, 0)
	x = (s + s/2.0)/3.0
	y = v3/3.0
	
	return (x, y)


size = None

def hilbertCurve(level, angle):
	
	if level == 0:
		return
	
	fc.rt(angle)
	hilbertCurve(level - 1, -angle)
	fc.fd(size)
	fc.lt(angle)
	hilbertCurve(level - 1, angle)
	fc.fd(size)
	hilbertCurve(level - 1, angle)
	fc.lt(angle)
	fc.fd(size)
	hilbertCurve(level - 1, -angle)
	fc.rt(angle)

def hilbertSideLength(level, segmentLen):
    
    #Calculate one side-length of the square
    # Equation: f(x) = 2^n - 1
    
    totalLen = 2**level - 1
    totalLen *= segmentLen
    
    return totalLen

def hilbertCntrPnt(level, segmentLen):
	
	totalLen = hilbertSideLength(level, segmentLen)
	
	x = -(totalLen/2)
	y = totalLen/2
	
	return (x, y)

def hilbertPerimeter(level, sideLen):
	
	# Equation: f(x) = 2^n - 1/(2^n)
	return sideLen*(2.0**level - 1.0/(2.0**level))




# Class Initialization
fc = Coordinates.Coordinates()
nc = NECGenerator.NECGenerator()

# Create file path
d = "C:/fractal-antenna/"

# TODO: Check if linux/mac
if(sys.platform == "win32" or sys.platform == "win64"):
	if not os.path.exists(d):
	        print("Creating folder to store .nec files...")
	        os.makedirs(d)
else:
	sys.exit(-1);
	

# Path of where you want to generate the .nec file
print("Enter a file name for your fractal antenna.")
name = raw_input()
f = open(d + name + ".nec", "w+")

antennas = {1:"Hilbert Curve Dipole", 2:"Koch Curve Dipole", 3:"Koch Snowflake Loop"}

# Retreive date and time
dateTime = strftime("%a, %d %b %Y %H:%M:%S -7", gmtime())

print("\nEnter the Fractal Antenna you would like to render.")
print("1) Hilbert Curve Dipole")
print("2) Koch Curve Dipole")
print("3) Koch Snowflake Loop")

selectedAnten = input()

if(selectedAnten == 1):
	
	print("\nEnter the iteration level for the %s" % antennas[1])
	itLevel = input()
	
	print("\nEnter segment length (m) for the %s" % antennas[1])
	size = input()
	
	#print ("Enter the angle size for the %s" % antennas[1])
	#angle = input()
	angle = 90 		# Degrees
	
	
	"""
	There are two possible dipole methods that can be invoked using the
	Hilbert Curve. The first method involves only one Koch Curve in which
	the line feed is positioned near the center of the curve. The second
	method is a dipole that utilizes two Hilbert Curves; one for each
	wavelength of the specified frequency. The line feed for the latter
	method is positioned at the point where the first Hilbert Curve ends
	and the second one begins.
	"""
	
	
	print("\nEnter the %s method you would like to invoke." % antennas[1])
	print("1) Single Hilbert Curve Method")
	print("2) Double Hilbert Curve Method")
	hilbertMethod = input()
	
	
	if(hilbertMethod == 1):
		
		center = hilbertCntrPnt(itLevel, size)
		fc.setpos(center[0], center[1])
		
		hilbertCurve(itLevel, angle)
		xyPoints = fc.pointsVisited[1:]
		
		medianPos = findMedianPos(xyPoints)
		
		
		print("\nEnter the number of segments for each wire.")
		segNum = input()
		
		print("\nEnter the wire radius (m).")
		wireRad = str(raw_input())
		
		
		# Comments
		nc.CM("Hilbert Curve Fractal Antenna, courtesy of Austin Schaller with 4NEC2 on %s.\r\nSegment Length (m): %s\r\nTotal Length (m): %s\r\n" % (dateTime, str(size), str(hilbertPerimeter(itLevel, size))))
		
		# Add z coordinates to existing tuples
		hilbertPoints = []
		for i in range(len(xyPoints)):
			hilbertPoints += (xyPoints[i] + (0.0,),)
		
		
		for i in range(len(hilbertPoints) - 1):
				
			if(i + 1 == len(hilbertPoints)):
				break
			
			# Geometry
			firstCoor = ' '.join(map(str, hilbertPoints[i]))
			secCoor = ' '.join(map(str, hilbertPoints[i + 1]))
			nc.GW(segNum, firstCoor, secCoor, wireRad)
		
		# Load Parameters
		# nc.GE(0)
		# nc.EK()
		# nc.LD('5', str(medianPos), str(segNum/2), '0', '57471265.5', '0')
		# nc.EX('0', str(medianPos), str(segNum/2), '0', '1', '0')
		# nc.GN('-1')
		# nc.FR('1000', '900', '1')
		# nc.EN()

		print("\nEnter the loading parameters as a list of strings:")
		ldList = input()
		#ldList = ['5', '0', '0', '0', '57471265.5', '0']
		ldEnd = len(ldList)
		
		for i in range(6 - ldEnd):
			ldList.append('')
		
		nc.LD(ldList[0], ldList[1], ldList[2], ldList[3], ldList[4], ldList[5])
		
		
		print("\nEnter excitation parameters as a list of strings:")
		exList = input()
		#exList = ['0', '9', '1', '0', '1', '0']
		exEnd = len(exList)
		
		for i in range(6 - exEnd):
			exList.append('')
		
		#nc.EX(exList[0], exList[1], exList[2], exList[3], exList[4], exList[5])
		
		
		print("\nEnter the ground parameters as a list of strings:")
		gndList = input()
		#gndList = ['-1']
		gndEnd = len(gndList)
		
		for i in range(4 - gndEnd):
			gndList.append('')
		
		nc.GN(gndList[0], gndList[1], gndList[2], gndList[3])
		
		print("\nEnter the frequency parameters as a list of strings:")
		frList = input()
		frEnd = len(frList)
		
		for i in range(3 - frEnd):
			frList.append('')
		
		nc.FR(frList[0], frList[1], frList[2])
		nc.EN()
		
		nc.Write(f)
	
	elif(hilbertMethod == 2):
		
		startPos = -(hilbertSideLength(itLevel, size) + size/2)
		fc.setpos(startPos, 0)
		
		
		print("\nEnter the number of segments for each wire.")
		segNum = input()
		
		print("\nEnter the wire radius (m).")
		wireRad = str(raw_input())
		
		
		# First half of dipole
		hilbertCurve(itLevel, angle)
		
		fc.fd(size)		# Used to connect both halves of the dipole
		
		# Second half of dipole
		hilbertCurve(itLevel, angle)
		
		xyPoints = fc.pointsVisited[1:]
		medianPos = findMedianPos(xyPoints)
		
		
		# Comments
		nc.CM("Hilbert Curve Fractal Antenna, courtesey of Austin Schaller with 4NEC2 on %s.\r\nSegment Length (m): %s\r\nTotal Length (m): %s\r\n" % (dateTime, str(size), str(hilbertPerimeter(itLevel, size))))
		
		# Add z coordinates to existing tuples
		hilbertPoints = []
		for i in range(len(xyPoints)):
			hilbertPoints += (xyPoints[i] + (0.0,),)
		
		
		for i in range(len(hilbertPoints) - 1):
				
			if(i + 1 == len(hilbertPoints)):
				break
			
			# Geometry
			firstCoor = ' '.join(map(str, hilbertPoints[i]))
			secCoor = ' '.join(map(str, hilbertPoints[i + 1]))
			nc.GW(segNum, firstCoor, secCoor, wireRad)
		
		# Load Parameters
		# nc.GE(0)
		# nc.EK()
		# nc.LD('5', '0', '0', '0', '57471265.5', '0')
		# nc.EX('0', str(medianPos), str(segNum/2), '0', '1', '0')
		# nc.GN('-1')
		# nc.FR('1', '146', '0')
		# nc.EN()

		print("\nEnter the loading parameters as a list of strings:")
		ldList = input()
		#ldList = ['5', '0', '0', '0', '57471265.5', '0']
		ldEnd = len(ldList)
		
		for i in range(6 - ldEnd):
			ldList.append('')
		
		nc.LD(ldList[0], ldList[1], ldList[2], ldList[3], ldList[4], ldList[5])
		
		
		print("\nEnter excitation parameters as a list of strings:")
		exList = input()
		#exList = ['0', '9', '1', '0', '1', '0']
		exEnd = len(exList)
		
		for i in range(6 - exEnd):
			exList.append('')
		
		#nc.EX(exList[0], exList[1], exList[2], exList[3], exList[4], exList[5])
		
		
		print("\nEnter the ground parameters as a list of strings:")
		gndList = input()
		#gndList = ['-1']
		gndEnd = len(gndList)
		
		for i in range(4 - gndEnd):
			gndList.append('')
		
		nc.GN(gndList[0], gndList[1], gndList[2], gndList[3])
		
		print("\nEnter the frequency parameters as a list of strings:")
		frList = input()
		frEnd = len(frList)
		
		for i in range(3 - frEnd):
			frList.append('')
		
		nc.FR(frList[0], frList[1], frList[2])
		nc.EN()
		
		nc.Write(f)
		
	else:
		# Error; no item was selected
		pass

elif(selectedAnten == 2):
	
	print("\nEnter the iteration level for the %s" % antennas[2])
	itLevel = input()
	
	print("\nEnter the side length (m) for the %s" % antennas[2])
	sideLen = input()

	"""
	There are two possible dipole methods that can be invoked using the
	Koch Curve. The first method involves only one Koch Curve in which the
	line feed is positioned at the very tip of the center triangle. The
	second method is a dipole that utilizes two Koch Curves; one for each
	wavelength of the specified frequency. The line feed for the latter
	method is positioned at the point where the first Koch Curve ends and
	the second one begins.
	"""
	
	print("\nEnter the %s method you would like to invoke." % antennas[2])
	print("1) Single Koch Curve Method")
	print("2) Double Koch Curve Method")
	
	kochMethod = input()
	
	if(kochMethod == 1):
		
		fc.setpos(-(sideLen/2), 0)
		
		kochCurve(itLevel, sideLen)
		xyPoints = fc.pointsVisited[1:]
		
		medianPos = findMedianPos(xyPoints)
		
		
		"""
		Generate Koch Curve in 4NEC2 so that the starting position and
		ending position are mapped to the tip of the center triangle.
		"""
		
		
		# Complete entire .nec transaction
		
		print("\nEnter the number of segments for each wire.")
		segNum = input()
		
		print("\nEnter the wire radius (m).")
		wireRad = str(raw_input())
		
		
		# Add z coordinates to existing tuples
		kochPoints = []
		for i in range(len(xyPoints)):
			kochPoints += (xyPoints[i] + (0.0,),)
		
		
		# Comments
		nc.CM("Koch Curve Fractal Antenna, courtesy of Austin Schaller with 4NEC2 on %s.\r\nSegment Length (m): %s\r\nSide Length (m): %s\r\nTotal Length (m): %s\r\n" % (dateTime, str(sideLen), str(kochSegmentLength(itLevel, sideLen)), str(kochPerimeter(itLevel, sideLen))))
		
		for i in range(len(kochPoints) - 1):			
			if(i + 1 == len(kochPoints)):
				break
			
			# Geometry
			firstCoor = ' '.join(map(str, kochPoints[i]))
			secCoor = ' '.join(map(str, kochPoints[i + 1]))
			nc.GW(str(segNum), firstCoor, secCoor, wireRad)
		
		
		nc.GE(0)
		nc.EK()
		
		print("\nEnter the loading parameters as a list of strings:")
		ldList = input()
		#ldList = ['5', '0', '0', '0', '57471265.5', '0']
		ldEnd = len(ldList)
		
		for i in range(6 - ldEnd):
			ldList.append('')
		
		nc.LD(ldList[0], ldList[1], ldList[2], ldList[3], ldList[4], ldList[5])
		
		
		print("\nEnter excitation parameters as a list of strings:")
		exList = input()
		#exList = ['0', '9', '1', '0', '1', '0']
		exEnd = len(exList)
		
		for i in range(6 - exEnd):
			exList.append('')
		
		#nc.EX(exList[0], exList[1], exList[2], exList[3], exList[4], exList[5])
		
		
		print("\nEnter the ground parameters as a list of strings:")
		gndList = input()
		#gndList = ['-1']
		gndEnd = len(gndList)
		
		for i in range(4 - gndEnd):
			gndList.append('')
		
		nc.GN(gndList[0], gndList[1], gndList[2], gndList[3])
		
		print("\nEnter the frequency parameters as a list of strings:")
		frList = input()
		frEnd = len(frList)
		
		for i in range(3 - frEnd):
			frList.append('')
		
		nc.FR(frList[0], frList[1], frList[2])
		nc.EN()
		
		
		#nc.GE(0)
		#nc.EK()
		#nc.LD('5', '0', '0', '0', '57471265.5', '0')
		#nc.EX('0', str(medianPos + 1), '1', '0', '1', '0')
		#nc.GN('-1')
		#nc.FR('1', '900', '0')
		#nc.EN()
		
		nc.Write(f)
	
	elif(kochMethod == 2):
		
		fc.setpos(-(sideLen), 0)
		
		# First half of dipole
		kochCurve(itLevel, sideLen)
		
		segLen = kochSegmentLength(itLevel, sideLen)
		fc.fd(segLen)
		
		# Second half of dipole
		kochCurve(itLevel, sideLen)
		
		xyPoints = fc.pointsVisited[1:]
		
		medianPos = findMedianPos(xyPoints)
		
		# Complete entire .nec transaction
		
		print("\nEnter the number of segments for each wire.")
		segNum = input()
		
		print("\nEnter the wire radius.")
		wireRad = str(raw_input())
		
		
		# Add z coordinates to existing tuples
		kochPoints = []
		for i in range(len(xyPoints)):
			kochPoints += (xyPoints[i] + (0.0,),)
		
		
		# Comments
		nc.CM("Koch Curve Fractal Antenna, courtesy of Austin Schaller with 4NEC2 on %s.\r\nSegment Length (m): %s\r\nSide Length (m): %s\r\nTotal Length (m): %s\r\n" % (dateTime, str(sideLen), str(kochSegmentLength(itLevel, sideLen)), str(kochPerimeter(itLevel, sideLen))))
		
		for i in range(len(kochPoints) - 1):			
			if(i + 1 == len(kochPoints)):
				break
			
			# Geometry
			firstCoor = ' '.join(map(str, kochPoints[i]))
			secCoor = ' '.join(map(str, kochPoints[i + 1]))
			nc.GW(str(segNum), firstCoor, secCoor, wireRad)
		
		
		nc.GE(0)
		nc.EK()
		
		print("\nEnter the loading parameters as a list of strings:")
		ldList = input()
		#ldList = ['5', '0', '0', '0', '57471265.5', '0']
		ldEnd = len(ldList)
		
		for i in range(6 - ldEnd):
			ldList.append('')
		
		nc.LD(ldList[0], ldList[1], ldList[2], ldList[3], ldList[4], ldList[5])
		
		
		print("\nEnter excitation parameters as a list of strings:")		# All except tag nr
		exList = input()
		#exList = ['0', '9', '1', '0', '1', '0']
		exEnd = len(exList)
		
		for i in range(6 - exEnd):
			exList.append('')
		
		nc.EX(exList[0], exList[1], exList[2], exList[3], exList[4], exList[5])
		
		print("\nEnter the ground parameters as a list of strings:")
		gndList = input()
		gndList = ['-1']
		gndEnd = len(gndList)
		
		for i in range(4 - gndEnd):
			gndList.append('')
		
		nc.GN(gndList[0], gndList[1], gndList[2], gndList[3])
		
		print("\nEnter the frequency parameters as a list of strings:")
		frList = input()
		frEnd = len(frList)
		
		for i in range(3 - frEnd):
			frList.append('')
		
		nc.FR(frList[0], frList[1], frList[2])
		nc.EN()
		
		# Generic parameters found from other nec antennas
		#nc.GE(0)
		#nc.EK()
		#nc.LD('5', '0', '0', '0', '57471265.5', '0')
		#nc.EX('0', str(medianPos), str(segNum/2), '0', '1', '0')
		#nc.GN('-1')
		#nc.FR('1', '146', '0')
		#nc.EN()
		
		nc.Write(f)
	
	else:
		# Error; no item selected.
		pass
	
	

elif(selectedAnten == 3):
	
	print("\nEnter the iteration level for the %s" % antennas[3])
	itLevel = input()
	
	print("\nEnter segment length (m) for the %s" % antennas[3])
	segLen = input()
	
	center = kochSnowflakeCntrPnt(itLevel, segLen)
	fc.setpos(-center[0], -center[1])
	
	kochSnowflake(itLevel, segLen)
	
	xyPoints = fc.pointsVisited[1:]
	
	medianPos = findMedianPos(xyPoints)
	
	
	# Complete entire .nec transaction
	
	print("\nEnter the number of segments for each wire.")
	segNum = input()
	
	print("\nEnter the wire radius.")
	wireRad = str(raw_input())
	
	
	# Comments
	nc.CM("Koch Snowflake Fractal Antenna, courtesy of Austin Schaller with 4NEC2 on %s.\r\nSegment Length (m): %s\r\nSide Length (m): " + str(segLen) + "\r\nTotal Length (m): %s\r\n" % (dateTime, str(kochSegmentLength(itLevel, segLen)), str(3*(kochPerimeter(itLevel, segLen)))))
	
	# Add z coordinates to existing tuples
	kochSnowflakePoints = []
	for i in range(len(xyPoints)):
		kochSnowflakePoints += (xyPoints[i] + (0.0,),)
	
	
	for i in range(len(kochSnowflakePoints) - 1):
			
		if(i + 1 == len(kochSnowflakePoints)):
			break
		
		# Geometry
		firstCoor = ' '.join(map(str, kochSnowflakePoints[i]))
		secCoor = ' '.join(map(str, kochSnowflakePoints[i + 1]))
		nc.GW(str(segNum), firstCoor, secCoor, wireRad)
	
	nc.GE(0)
	nc.EK()
	
	print("\nEnter the loading parameters as a list of strings:")
	ldList = input()
	#ldList = ['5', '0', '0', '0', '57471265.5', '0']
	ldEnd = len(ldList)
	
	for i in range(6 - ldEnd):
		ldList.append('')
	
	nc.LD(ldList[0], ldList[1], ldList[2], ldList[3], ldList[4], ldList[5])
	
	
	print("\nEnter excitation parameters as a list of strings:")
	exList = input()
	#exList = ['0', '9', '1', '0', '1', '0']
	exEnd = len(exList)
	
	for i in range(6 - exEnd):
		exList.append('')
	
	nc.EX(exList[0], exList[1], exList[2], exList[3], exList[4], exList[5])
	
	print("\nEnter the ground parameters as a list of strings:")
	gndList = input()
	#gndList = ['-1']
	gndEnd = len(gndList)
	
	for i in range(4 - gndEnd):
		gndList.append('')
	
	nc.GN(gndList[0], gndList[1], gndList[2], gndList[3])
	
	print("\nEnter the frequency parameters as a list of strings:")
	frList = input()
	frEnd = len(frList)
	
	for i in range(3 - frEnd):
		frList.append('')
	
	nc.FR(frList[0], frList[1], frList[2])
	nc.EN()
	
	# Generic parameters found from other nec antennas
	#nc.GE(0)
	#nc.EK()
	#nc.LD('5', '0', '0', '0', '57471265.5', '0')
	#nc.EX('0', str(medianPos + 1), '1', '0', '1', '0')
	#nc.GN('-1')
	#nc.FR('1', '146', '0')
	#nc.EN()
	
	nc.Write(f)

else:
	pass


f.close()

print("\nFractal antenna .nec file created at:")
print("%s%s.nec" % (d, name))