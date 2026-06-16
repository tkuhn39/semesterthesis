# coding: utf8
from __future__ import print_function
#from abaqus import *
from abaqusConstants import *
from odbAccess import *
from textRepr import *
import xml.etree.ElementTree as ET
import xml.dom.minidom
import math
import numpy as np
from datetime import date
from collections import OrderedDict
from odbElementConnectivity import getInstanceBestNodeIdxForPositioning, isRelevantFrame, exportOdbZ88Net, exportOdbZ88Disp

stageNumber = -1
gear1Number = -1
gear2Number = -1
rotationSpeedOfGear1 = 0
isGear1DrivingGear = True
resultFileName = 'TransientFEM_REXS.xml'
geometryTolerance = 0.001

def getRotationMatrix(angleInRadians, rotationAxis):
	unitVec = rotationAxis / np.linalg.norm(rotationAxis)
	nX = unitVec[0]
	nY = unitVec[1]
	nZ = unitVec[2]
	c = math.cos(angleInRadians);
	s = math.sin(angleInRadians);
	
	if abs(angleInRadians-math.pi/2.0) < 1e-17:
		c = 0
		s = 1

	row0 = np.array([ 	nX*nX*(1.0-c) + c, 
			nX*nY*(1.0-c) - nZ*s,
			nX*nZ*(1.0-c) + nY*s])

	row1 = np.array([ 	nY*nX*(1.0-c) + nZ*s,
			nY*nY*(1.0-c) + c,
			nY*nZ*(1.0-c) - nX*s])
	
	row2 = np.array([	nZ*nX*(1.0-c) - nY*s,
			nZ*nY*(1.0-c) + nX*s,
			nZ*nZ*(1.0-c) + c])

	#print('rotation matrix ')
	#print(np.array([row0, row1, row2]))
	
	return np.array([row0, row1, row2])

def getDistanceOfPointToLine(supportVectorOfLine, directionVectorOfLine, point):
	differenceBetweenPositions = [supportVectorOfLine[0]-point[0], supportVectorOfLine[1]-point[1], supportVectorOfLine[2]-point[2]]
	crossProduct = np.cross(differenceBetweenPositions, directionVectorOfLine)
	return np.linalg.norm(crossProduct) / np.linalg.norm(directionVectorOfLine)

def getAngleBetweenVectorsRelativeToThirdVector(vec, base, up):
	vec_n = vec / np.linalg.norm(vec)
	base_n = base / np.linalg.norm(base)
	
	len = np.dot(vec_n, base_n)
	angle = np.arccos(len)
	
	up_n = up / np.linalg.norm(up)
	positive = np.cross(up_n, base_n)
	if (np.dot(vec_n, positive))<0:
		angle *= -1.0
	
	return angle

def getRadiusOfGear(gearNumber, radiusName): # gear number either 1 or 2
	radius = 0.0
	with open('Geometrieberechnung_E1','r') as br:
		line = br.readline()
		while line:
			if(not line.strip().startswith(radiusName)):
				line = br.readline()
				continue
			
			line = ' '.join(line.split())
			spl = line.split(' ')
			radius = 0.5 * (float)(spl[2+gearNumber])
			break
	
	print('gear ' + str(gearNumber) + ' has ' + radiusName + ' :' + str(2.0*radius))
	return radius
	
def getNumberOfTeethOfGear(gearNumber): # gear number either 1 or 2
	teethNumber = 0
	with open('Geometrieberechnung_E1','r') as br:
		line = br.readline()
		while line:
			if(not line.strip().startswith('Zaehnezahl')):
				line = br.readline()
				continue
			
			line = ' '.join(line.split())
			spl = line.split(' ')
			teethNumber = (int)(spl[2+gearNumber])
			break
	
	print('gear ' + str(gearNumber) + ' has number of teeth: ' + str(teethNumber))
	return teethNumber
	
def getToothWidthOfGear(gearNumber): # gear number either 1 or 2
	toothWidth = 0
	with open('Geometrieberechnung_E1','r') as br:
		line = br.readline()
		while line:
			if(not line.strip().startswith('Verzahnungsbreite b')):
				line = br.readline()
				continue
			
			line = ' '.join(line.split())
			spl = line.split(' ')
			toothWidth = (float)(spl[2+gearNumber])
			break
	
	print('gear ' + str(gearNumber) + ' has tooth width: ' + str(toothWidth))
	return toothWidth

def getMittelspannungsempfindlichkeitOfGear(gearNumber): # gear number either 1 or 2
	radius = 0.0
	with open('Steuerparameter.txt','r') as br:
		line = br.readline()
		while line:
			if(not line.strip().startswith('Mittelspannungsempfindlichkeit')):
				line = br.readline()
				continue
			
			line = ' '.join(line.split())
			spl = line.split('=')[1].strip().split(' ')
			value = (float)(spl[gearNumber-1])
			break
	
	print('gear ' + str(gearNumber) + ' has Mittelspannungsempfindlichkeit of ' + str(value))
	return value
	
def getSchubfestigkeitsfaktorInterpolator(gearNumber): # gear number either 1 or 2
	f_tau = 1.0
	with open('Steuerparameter.txt','r') as br:
		line = br.readline()
		while line:
			if(not line.strip().startswith('Schubfestigkeitsfaktor')):
				line = br.readline()
				continue
			
			line = ' '.join(line.split())
			spl = line.split('=')[1].strip().split(' ')
			f_tau = (float)(spl[gearNumber-1])
			break
			
	interpolationFaktor = (math.sqrt(3) - (1.0/f_tau)) / (math.sqrt(3) - 1.0)
	
	print('gear ' + str(gearNumber) + ' has Schubfestigkeitsfaktor of ' + str(f_tau) + ' and interpolation faktor of: ' + str(interpolationFaktor))
	return interpolationFaktor
	
def getNumberOfPitchesToRollOver():
	numberOfPitchesToRollOver = 1
	with open('Steuerparameter.txt','r') as br:
		line = br.readline()
		while line:
			if(not line.strip().startswith('Anzahl_Teilungen')):
				line = br.readline()
				continue
			
			line = ' '.join(line.split())
			numberOfPitchesToRollOver = (int)(line.split('=')[1].strip())
			break
	
	print('numberOfPitchesToRollOver :' + str(numberOfPitchesToRollOver))
	return numberOfPitchesToRollOver
	
def fillIsGear1DrivingGear():
	global isGear1DrivingGear
	isGear1DrivingGear = True
	with open('eingabedaten.fsk','r') as br:
		line = br.readline()
		while line:
			if(not line.strip().startswith('Radpaarung')):
				line = br.readline()
				continue
			
			line = ' '.join(line.split())
			spl = line.split('=')[1].strip().split(' ')
			gearIndex = (int)(spl[1])
			if gearIndex == 2 :
				isGear1DrivingGear = False
			break
	
	print('gear1IsDriver :' + str(isGear1DrivingGear))
	
def getOffsetOfDrivenGearToDrivingGear():
	offset = 0.0
	with open('eingabedaten.fsk','r') as br:
		line = br.readline()
		while line:
			if(not line.strip().startswith('Radpaarung')):
				line = br.readline()
				continue
			
			line = ' '.join(line.split())
			spl = line.split('=')[1].strip().split(' ')
			offset = (float)(spl[3])
			break
	
	# adapt axial offset from eingabedaten.fsk to Abaqus input file
	toothWidthGear1 = getToothWidthOfGear(1)
	toothWidthGear2 = getToothWidthOfGear(2)
	offset += toothWidthGear2 - toothWidthGear1
	offset *= -1.0
	
	print('offsetOfDrivenGearToDrivingGear :' + str(offset))
	return offset

def writeResultFileHeader():
	global resultFileName
	resultFile = open(resultFileName,'w')
	resultFile.write('<?xml version="1.0" encoding="utf-8"?>\n')
	aktuellesDatum = date.today()
	kernelversion = 'Abaqus 2020'
	resultFile.write('<model version="1.0" kernel="TransientFEM" kernelversion="' + kernelversion + '" compIdSource="KERNEL" attrIdSource="KERNEL" date="' + str(aktuellesDatum) + '">\n')
	resultFile.write('<components>\n')
	resultFile.close()

def writeResultFileFooter():
	global resultFileName
	resultFile = open(resultFileName,'a')
	resultFile.write('</components>\n')
	resultFile.write('</model>\n')
	resultFile.close()

def parseComponentNumbersAndRotationSpeed():
	global stageNumber
	global gear1Number
	global gear2Number
	global rotationSpeedOfGear1

	with open('eingabedaten.fsk','r') as br:
		line = br.readline()
		while line:
			if(line.strip().startswith('Ebenenbezeichnung')):
				line = ' '.join(line.split())
				spl = line.split(' ')
				stageNumber = (int)(spl[2])
			if(line.strip().startswith('Radindex')):
				line = ' '.join(line.split())
				spl = line.split(' ')
				gearNumber = (int)(spl[2])
				line = br.readline()  ## read next line which contains gear number
				line = ' '.join(line.split())
				spl = line.split(' ')
				
				if gearNumber == 1: # gearNumber 1 in eingabedaten.fsk
					if isGear1DrivingGear:
						gear1Number = (int)(spl[2])  # is Abaqus gear 1 if driver
					else:
						gear2Number = (int)(spl[2])  # is Abaqus gear 2 if driven
						
				if gearNumber == 2:  # gearNumber 2 in eingabedaten.fsk
					if isGear1DrivingGear:
						gear2Number = (int)(spl[2])  # is Abaqus gear 2 if driven
					else:
						gear1Number = (int)(spl[2])  # is Abaqus gear 1 if driver
					
			if(line.strip().startswith('Drehzahl')):
				line = ' '.join(line.split())
				spl = line.split(' ')
				gearNumber = (int)(spl[2])
				if gearNumber == 1:
					rotationSpeedOfGear1 = (float)(spl[3])
				else:
					print('ERROR: Rotation speed of gear 1 expected in eingabedaten.fsk')

			line = br.readline()
	
	print('stage id: ' + str(stageNumber) + ' gear1: ' + str(gear1Number) + ' gear2: ' + str(gear2Number) + ' rotation speed gear 1: ' + str(rotationSpeedOfGear1))
	
def getNumberOfRollingPositionsPerPitch():
	numberOfRollingPositionsPerPitches = 9
	with open('eingabedaten.fsk','r') as br:
		line = br.readline()
		while line:
			if(not line.strip().startswith('Anzahl_Waelzstellungen')):
				line = br.readline()
				continue
			
			line = ' '.join(line.split())
			numberOfRollingPositionsPerPitches = (int)(line.split('=')[1].strip())
			break
	
	print('numberOfRollingPositionsPerPitches :' + str(numberOfRollingPositionsPerPitches))
	return numberOfRollingPositionsPerPitches
	
def writeMatrixToResultFile(gearNumber, axial_positions_row, values_col, matrix, 
attributeNameRow, attributeNameCol, attributeNameMatrix, unitRow, unitCol, unitMatrix):
	global stageNumber
	global gear1Number
	global gear2Number
	global resultFileName
	
	if gearNumber == 1:
		gearNumberWB = gear1Number
	else:
		gearNumberWB = gear2Number
	
	numberEntriesRow = len(axial_positions_row)
	numberEntriesCol = len(values_col)
	numberEntriesRowTotal = len(matrix)
	
	#print('numberEntriesRow: ' + str(numberEntriesRow))
	#print('numberEntriesCol: ' + str(numberEntriesCol))
	#print('numberEntriesRowTotal: ' + str(numberEntriesRowTotal))
	# in y-Richtung untereinander angeordnet
	
	stageGearDataId = str(stageNumber) + '_' + str(gearNumberWB)
	resultFile = open(resultFileName,'a')
	resultFile.write('<component id="' + stageGearDataId  + '" type="mesh_gear_data">\n')
	
	## x-range matrix
	resultFile.write('    <attribute id="' + attributeNameCol + '" unit="' + unitCol + '" type="float_array">\n')
	resultFile.write('    <array>\n')
	for j in range(numberEntriesCol):
		resultFile.write('        <c>%f</c>\n' % values_col[j])
	resultFile.write('    </array>\n')
	resultFile.write('    </attribute>\n')
	
	## y-range matrix
	resultFile.write('    <attribute id="' + attributeNameRow + '" unit="' + unitRow + '" type="float_array">\n')
	resultFile.write('    <array>\n')
	for i in range(numberEntriesRow):
		resultFile.write('        <c>%f</c>\n' % axial_positions_row[i])
	resultFile.write('    </array>\n')
	resultFile.write('    </attribute>\n')
		
	## matrix itself
	resultFile.write('    <attribute id="' + attributeNameMatrix + '" unit="' + unitMatrix + '" type="float_matrix">\n')
	resultFile.write('    <matrix>\n')
	for i in range(numberEntriesRowTotal):
		resultFile.write('        <r>\n')
		for j in range(numberEntriesCol):
			resultFile.write('            <c>%f</c>\n' % matrix[i][j])
		resultFile.write('        </r>\n')
	resultFile.write('    </matrix>\n')
	resultFile.write('    </attribute>\n')
	
	resultFile.write('</component>\n')
	resultFile.close()

def writeMatrixAndColArrayToResultFile(gearNumber, values_col, matrix, attributeNameCol, attributeNameMatrix, unitCol, unitMatrix):
	global stageNumber
	global gear1Number
	global gear2Number
	global resultFileName
	
	if gearNumber == 1:
		gearNumberWB = gear1Number
	else:
		gearNumberWB = gear2Number
	
	numberEntriesCol = len(values_col)
	
	#print('numberEntriesCol: ' + str(numberEntriesCol))
	# in y-Richtung untereinander angeordnet
	
	stageGearDataId = str(stageNumber) + '_' + str(gearNumberWB)
	resultFile = open(resultFileName,'a')
	resultFile.write('<component id="' + stageGearDataId  + '" type="mesh_gear_data">\n')
	
	## x-range matrix
	resultFile.write('    <attribute id="' + attributeNameCol + '" unit="' + unitCol + '" type="float_array">\n')
	resultFile.write('    <array>\n')
	for j in range(numberEntriesCol):
		resultFile.write('        <c>%f</c>\n' % values_col[j])
	resultFile.write('    </array>\n')
	resultFile.write('    </attribute>\n')
	
	resultFile.write('</component>\n')
	resultFile.close()
	
	writeMatrixOnlyToResultFile(gearNumber, matrix, attributeNameMatrix, unitMatrix)

def writeMatrixOnlyToResultFile(gearNumber, matrix, attributeNameMatrix, unitMatrix):
	global stageNumber
	global gear1Number
	global gear2Number
	global resultFileName
	
	if gearNumber == 1:
		gearNumberWB = gear1Number
	else:
		gearNumberWB = gear2Number
	
	numberEntriesCol = len(matrix[0])
	numberEntriesRowTotal = len(matrix)

	#print('numberEntriesCol: ' + str(numberEntriesCol))
	#print('numberEntriesRowTotal: ' + str(numberEntriesRowTotal))
	# in y-Richtung untereinander angeordnet
	
	stageGearDataId = str(stageNumber) + '_' + str(gearNumberWB)
	resultFile = open(resultFileName,'a')
	resultFile.write('<component id="' + stageGearDataId  + '" type="mesh_gear_data">\n')
	
	## matrix itself
	resultFile.write('    <attribute id="' + attributeNameMatrix + '" unit="' + unitMatrix + '" type="float_matrix">\n')
	resultFile.write('    <matrix>\n')
	for i in range(numberEntriesRowTotal):
		resultFile.write('        <r>\n')
		for j in range(numberEntriesCol):
			resultFile.write('            <c>%f</c>\n' % matrix[i][j])
		resultFile.write('        </r>\n')
	resultFile.write('    </matrix>\n')
	resultFile.write('    </attribute>\n')
	
	resultFile.write('</component>\n')
	resultFile.close()
	
def writeSingleValueToResultFile(gearNumber, value, attributeNameValue, unitValue):
	global stageNumber
	global gear1Number
	global gear2Number
	global resultFileName
	
	if gearNumber == 1:
		gearNumberWB = gear1Number
	else:
		gearNumberWB = gear2Number

	stageGearDataId = str(stageNumber) + '_' + str(gearNumberWB)
	resultFile = open(resultFileName,'a')
	resultFile.write('<component id="' + stageGearDataId  + '" type="mesh_gear_data">\n')
	resultFile.write('    <attribute id="' + attributeNameValue + '" unit="' + unitValue + '" type="float">' + str(value) + '</attribute>\n')
	resultFile.write('</component>\n')
	resultFile.close()

def writeTotalContactRatioAndMaxFlankPressurePerFlankToResultFile(gearNumber, flankNumbers, attributeFlankNumbers, totalContactRatioLoadDependentPerFlank, attributeTotalContactRatio, maximalFlankPressurePerFlank, attributeFlankPressure):
	global stageNumber
	global gear1Number
	global gear2Number
	global resultFileName
	
	if gearNumber == 1:
		gearNumberWB = gear1Number
	else:
		gearNumberWB = gear2Number
	
	numberEntriesCol = len(flankNumbers)
	
	stageGearDataId = str(stageNumber) + '_' + str(gearNumberWB)
	resultFile = open(resultFileName,'a')
	resultFile.write('<component id="' + stageGearDataId  + '" type="mesh_gear_data">\n')
	
	## flank numbers
	resultFile.write('    <attribute id="' + attributeFlankNumbers + '" type="integer_array">\n')
	resultFile.write('    <array>\n')
	for j in range(numberEntriesCol):
		resultFile.write('        <c>%d</c>\n' % flankNumbers[j])
	resultFile.write('    </array>\n')
	resultFile.write('    </attribute>\n')
	
	## total contact ratio load dependent per flank
	resultFile.write('    <attribute id="' + attributeTotalContactRatio + '" unit=\'--\' type="float_array">\n')
	resultFile.write('    <array>\n')
	for j in range(numberEntriesCol):
		resultFile.write('        <c>%f</c>\n' % totalContactRatioLoadDependentPerFlank[j])
	resultFile.write('    </array>\n')
	resultFile.write('    </attribute>\n')
	
	## maximum pressure per flank
	resultFile.write('    <attribute id="' + attributeFlankPressure + '" unit=\'dr__mega_pascal\' type="float_array">\n')
	resultFile.write('    <array>\n')
	for j in range(numberEntriesCol):
		resultFile.write('        <c>%f</c>\n' % maximalFlankPressurePerFlank[j])
	resultFile.write('    </array>\n')
	resultFile.write('    </attribute>\n')
	
	resultFile.write('</component>\n')
	resultFile.close()


def strToSaveFileName(s):
	keepcharacters = ('_') #(' ','.','_')
	return "".join(c for c in s if c.isalnum() or c in keepcharacters).rstrip()

# Open the odb data base
odbPath = 'abq_abw.odb'
odbNeedsUpgrade = isUpgradeRequiredForOdb(upgradeRequiredOdbPath=odbPath)
if odbNeedsUpgrade:
	upradedOdbPath = 'abq_abw_upgraded.odb'
	upgradeOdb(existingOdbPath=odbPath, upgradedOdbPath=upradedOdbPath)
	odbPath = upradedOdbPath

odb = openOdb(path=odbPath)

############ initialize xml result file
fillIsGear1DrivingGear() # fill first because it is necessary for the next line
parseComponentNumbersAndRotationSpeed()
writeResultFileHeader()

########
############ write results for tooth values of gears
########
# analysis is performed within one step containing many frames
step = odb.steps['STEP-1']
sortedListOfAxialPositionsOfGears = []
axialPositionsMappingOfGears = []
numberOfPitchesToRollOver = getNumberOfPitchesToRollOver()
for gearNum in range(1,3): # gear 1 & 2
	referencePointNodeSetName = 'REFERENCE_POINT_        ' + str(gearNum)
	referencePointNodeSet = odb.rootAssembly.nodeSets[referencePointNodeSetName]
	referencePointCoordinates = referencePointNodeSet.nodes[0][0].coordinates  # has only one node
	
	supportVectorOfLine = referencePointCoordinates
	directionVectorOfLine = [0.0, 0.0, 1.0]
	fussFormKreisRadius = getRadiusOfGear(gearNum, 'Fussformkreisdurchmesser')
	interpolationFaktorStressStrain = getSchubfestigkeitsfaktorInterpolator(gearNum)

	gearName = 'RAD_VZ_' + str(gearNum)
	toothGapElementSetTuples = []
	# only surface nodes are required for evaluation
	toothGapNodeSetsOfGear = [] 
	# collect all element sets of tooth roots
	flankenCounter = 0
	for currentElementSet in odb.rootAssembly.instances[gearName].elementSets.values():
		elementSetName = currentElementSet.name
		print(elementSetName)
		nameStart = 'G' + str(gearNum) + 'T'         # z.B. G1T001F1_ELEMENTSET
		
		if(elementSetName.startswith(nameStart)):  # element set beinhaltet Flanke & Fuß
			flankenCounter += 1
			
	numToothGapsPerGear = int((flankenCounter - 2) / 2)
	
	for n in range(1, numToothGapsPerGear+1):
		set1Kenner = 'G' + str(gearNum) + 'T' + str(n).zfill(3) + 'F1_ELEMENTSET'
		set2Kenner = 'G' + str(gearNum) + 'T' + str(n+1).zfill(3) + 'F2_ELEMENTSET'
		toothGapElementSetTuples.append((set1Kenner, set2Kenner))
		
	for values in toothGapElementSetTuples:
		surfaceNodeSetNodeIds = set()
		for leftFlankRightFlankIter in range(0,2):
			split = values[leftFlankRightFlankIter].split("_")
			surfaceNodeSetName = split[0] + '_NODESET'
			surfaceNodeSetNodes = odb.rootAssembly.instances[gearName].nodeSets[surfaceNodeSetName].nodes
			for i in range(len(surfaceNodeSetNodes)):
				surfaceNodeSetNodeIds.add(surfaceNodeSetNodes[i].label)
		toothGapNodeSetsOfGear.append(surfaceNodeSetNodeIds)
		
	# find relevant nodes in tooth root
	nodalAxialAnd3DPosition = []
	axialSortedNodes = []

	zeroFrame = step.frames[0]
	logarithmicStrain = zeroFrame.fieldOutputs['LE']
	listOfAxialPositions = []
	for toothGapIter in range(len(toothGapElementSetTuples)):
		toothRootElementSetTuple = toothGapElementSetTuples[toothGapIter]
			
		surfaceNodeSetNodeIds = toothGapNodeSetsOfGear[toothGapIter]
		
		minimalRadius = 999999999.0
		maximalRadius = 0
		nodalAxialAnd3DPositionOfToothGap = dict()
		for leftFlankRightFlankIter in range(0,2):
			
			elementSet = odb.rootAssembly.instances[gearName].elementSets[toothRootElementSetTuple[leftFlankRightFlankIter]]
			elementSetStrain = logarithmicStrain.getSubset(region=elementSet,position=ELEMENT_NODAL) ###!!! important here: interpolated at nodes
			
			## fill list of radial and axial positions of each node
			fieldValues = elementSetStrain.values
			for elementStrainNodalValue in fieldValues:
				
				nodeId = elementStrainNodalValue.nodeLabel
				
				if nodeId in surfaceNodeSetNodeIds:
					nodeCoordinates = odb.rootAssembly.instances[gearName].nodes[nodeId-1].coordinates
					distanceFromShaftAxis = getDistanceOfPointToLine(supportVectorOfLine, directionVectorOfLine, nodeCoordinates)

					if (distanceFromShaftAxis <= (1.0+geometryTolerance)*fussFormKreisRadius):
						axialDistanceKenner = 999999999.0
						for ax in listOfAxialPositions:
							if abs(ax - nodeCoordinates[2])<geometryTolerance:
								axialDistanceKenner = ax
						if axialDistanceKenner == 999999999.0:
							listOfAxialPositions.append(nodeCoordinates[2])
							axialDistanceKenner = nodeCoordinates[2]
						
						minimalRadius = min(distanceFromShaftAxis, minimalRadius)
						maximalRadius = max(distanceFromShaftAxis, maximalRadius)
						nodalAxialAnd3DPositionOfToothGap[nodeId] = (axialDistanceKenner, distanceFromShaftAxis, nodeCoordinates)
		
		axialSortedNodesOfToothGap = dict()
		axialSortedNodes.append(axialSortedNodesOfToothGap)
		for id, value in nodalAxialAnd3DPositionOfToothGap.items():
			(axialDistanceKenner, distanceFromShaftAxis, coordinates) = value
			vec = np.subtract(coordinates, supportVectorOfLine)
			base = [0.0, 1.0, 0.0]
			angle = getAngleBetweenVectorsRelativeToThirdVector(vec, base, directionVectorOfLine)
			
			if not axialDistanceKenner in axialSortedNodesOfToothGap:
				axialSortedNodesOfToothGap[axialDistanceKenner] = dict()
			axialSortedNodesOfToothGap[axialDistanceKenner][angle] = (id, distanceFromShaftAxis)
		
		limitRadiusForEvaluatingWithAngle = minimalRadius + 0.1*(maximalRadius-minimalRadius)
		#### sort with increasing angle per axial distance kenner
		#### due to Hinterschnitt -> split necessary for sorting; 1st: radial, 2nd: angle, 3rd: radial
		list.sort(listOfAxialPositions)
		for axialKenner in listOfAxialPositions:
			purelyAngleSortedDictForThisAxialKenner = OrderedDict(sorted(axialSortedNodesOfToothGap[axialKenner].items()))
			
			resortingAlongRadiusNecessaryFirstHalf = dict()
			resortingAlongRadiusNecessarySecondHalf = dict()
			firstHalf = True
			for angle, tupleIdAndDistanceFromShaft in purelyAngleSortedDictForThisAxialKenner.items():
				(id, distanceFromShaftAxis) = tupleIdAndDistanceFromShaft
				
				if firstHalf:
					if(distanceFromShaftAxis > limitRadiusForEvaluatingWithAngle):
						resortingAlongRadiusNecessaryFirstHalf[distanceFromShaftAxis] = id
					else:
						firstHalf = False
				else:
					if(distanceFromShaftAxis > limitRadiusForEvaluatingWithAngle):
						resortingAlongRadiusNecessarySecondHalf[distanceFromShaftAxis] = id
			
			radialResortedFirstHalf = OrderedDict(sorted(resortingAlongRadiusNecessaryFirstHalf.items(), reverse=True))
			radialResortedSecondHalf = OrderedDict(sorted(resortingAlongRadiusNecessarySecondHalf.items()))
			
			finallySortedNodeIds = []
			finallySortedNodeIds.extend(radialResortedFirstHalf.values())
			for iter in range(len(radialResortedFirstHalf), len(purelyAngleSortedDictForThisAxialKenner)-len(radialResortedSecondHalf)):
				finallySortedNodeIds.append(list(purelyAngleSortedDictForThisAxialKenner.values())[iter][0])
			finallySortedNodeIds.extend(radialResortedSecondHalf.values())
			
			axialSortedNodes[toothGapIter][axialKenner] = finallySortedNodeIds
				
		nodalAxialAnd3DPosition.append(nodalAxialAnd3DPositionOfToothGap)
		
	## store sorted list of axial positions for each gear
	axialMapping = dict()
	iterator = 0
	for ax in listOfAxialPositions:
		axialMapping[ax] = iterator
		iterator += 1
		
	sortedListOfAxialPositionsOfGears.append(listOfAxialPositions)
	print('sorted axial positions of gear ' + str(gearNum) + ':')
	print(sortedListOfAxialPositionsOfGears[gearNum-1])
	axialPositionsMappingOfGears.append(axialMapping)

	
	## get relevant range for stress output: 
	## an arbitrary axial node set can be chosen (chose 0th here) -> result is equal for each of them
	listOfAbgewickelteDistances = []
	listOfAbgewickelteDistances.append(0.0)
	nodeIdsSortedByIncreasingAngle = axialSortedNodes[0][listOfAxialPositions[0]]
	
	for iter in range(len(nodeIdsSortedByIncreasingAngle)-1):
		nodeId1 = nodeIdsSortedByIncreasingAngle[iter]
		nodeId2 = nodeIdsSortedByIncreasingAngle[iter+1]
		coordinates1 = nodalAxialAnd3DPosition[0][nodeId1][2]
		coordinates2 = nodalAxialAnd3DPosition[0][nodeId2][2]
		distance = np.linalg.norm(np.subtract(coordinates2, coordinates1))
		listOfAbgewickelteDistances.append(listOfAbgewickelteDistances[iter] + distance)
		
	centerValue = listOfAbgewickelteDistances[int(len(listOfAbgewickelteDistances)/2)]
	for i in range(len(listOfAbgewickelteDistances)):
		listOfAbgewickelteDistances[i] -= centerValue

	print('rolled off positions of tooth root of gear ' + str(gearNum) + ':')
	print(listOfAbgewickelteDistances)

	########
	######## start evaluation for all time steps
	########
	transient_fem_root_strain_rolling_path_col = []

	## for output: add offset to axial position to start from zero
	transient_fem_root_strain_coordinates_row = np.copy(listOfAxialPositions)
	offsetToStartFromZero = listOfAxialPositions[0]
	if gearNum==2:
		offsetToStartFromZero -= getOffsetOfDrivenGearToDrivingGear()
	for i in range(len(transient_fem_root_strain_coordinates_row)):
		transient_fem_root_strain_coordinates_row[i] -= offsetToStartFromZero
		
	print('number of result frames: ' + str(len(step.frames)))
	if len(step.frames) < 4:
		print('ERROR: Simulation diverged early -> Less than 4 result frames in odb file')
	
	# initialize strain matrix
	numberRelevantFrames = int((len(step.frames)-4)/3)
	rootStrainMatrix = np.empty([len(toothGapElementSetTuples)*len(listOfAxialPositions), numberRelevantFrames]) #only consider here relevant frames
	rootStrainMatrix.fill(np.nan)
	
	nodalMinimumStressBar = dict()
	nodalMaximumStressBar = dict()
	
	frameCounter = -1
	relevantFrameCounter = -1
	for currentFrame in step.frames:
		frameCounter += 1

		if not isRelevantFrame(frameCounter):
			continue
			
		relevantFrameCounter += 1
		
		# ranges from 0 ... number of pitches (subdivided with number of rolling positions)
		transient_fem_root_strain_rolling_path_col.append(float(relevantFrameCounter)*numberOfPitchesToRollOver/(numberRelevantFrames-1))

		#if relevantFrameCounter>2:
		#	break
		
		####
		#### evaluate root strain
		####
		nominalStrain = currentFrame.fieldOutputs['LE']
		for toothGapIter in range(len(toothGapElementSetTuples)):
			toothRootElementSetTuple = toothGapElementSetTuples[toothGapIter]
			
			nodalStrainBarFromElements = dict()
			for leftFlankRightFlankIter in range(0,2):
				elementSet = odb.rootAssembly.instances[gearName].elementSets[toothRootElementSetTuple[leftFlankRightFlankIter]]
				elementSetStrain = nominalStrain.getSubset(region=elementSet,position=ELEMENT_NODAL)
				fieldValues = elementSetStrain.values
				for elementStrainNodalValue in fieldValues:
					nodeId = elementStrainNodalValue.nodeLabel
					if nodeId in nodalAxialAnd3DPosition[toothGapIter]:
						misesStrainAtNode = elementStrainNodalValue.mises
						maxPrincipalStrainAtNode = elementStrainNodalValue.maxPrincipal
						if not nodeId in nodalStrainBarFromElements:
							nodalStrainBarFromElements[nodeId] = []
						nodalStrainBarFromElements[nodeId].append(interpolationFaktorStressStrain*maxPrincipalStrainAtNode + (1.0-interpolationFaktorStressStrain)*misesStrainAtNode)
						
			## Compute averaged nodal strain
			nodalAveragedStrainBar = dict()
			for key, values in nodalStrainBarFromElements.items():
				valueSum = 0.0
				for v in values:
					valueSum += v
				nodalAveragedStrainBar[key] = valueSum/len(values)
			
			## reduce data to single line // PRÜFEN DRUCK ODER ZUG -> Max Principal sollte Zug sein (Werte < 0 sind Druckdehnungen)
			maxValueOnLineInWidthDirection = np.zeros(len(listOfAxialPositions))
			for axialDistKenner, nodeIds in axialSortedNodes[toothGapIter].items():
				for nodeId in nodeIds:
					currentValue = nodalAveragedStrainBar[nodeId]
					oldValue = maxValueOnLineInWidthDirection[axialMapping[axialDistKenner]]
					maxValueOnLineInWidthDirection[axialMapping[axialDistKenner]] = max(currentValue, oldValue)
			
			## set proper gap counter for data filling
			fillDataIter = toothGapIter
			# the gaps match from 1 ... numGaps for driver and driven gear
			if (not isGear1DrivingGear and rotationSpeedOfGear1 < 0 and gearNum == 2) or (not isGear1DrivingGear and rotationSpeedOfGear1 > 0 and gearNum == 1) or (isGear1DrivingGear and rotationSpeedOfGear1 > 0 and gearNum == 2) or (isGear1DrivingGear and rotationSpeedOfGear1 < 0 and gearNum == 1):
				fillDataIter = len(toothGapElementSetTuples) - toothGapIter - 1
			
			for iter in range(len(listOfAxialPositions)):
				value = maxValueOnLineInWidthDirection[iter]
				rootStrainMatrix[fillDataIter*len(listOfAxialPositions) + iter][relevantFrameCounter] = value
				
		####
		#### collect stress minimum and maximum for later root stress evaluation
		####
		stress = currentFrame.fieldOutputs['S']
		for toothGapIter in range(len(toothGapElementSetTuples)):
			toothRootElementSetTuple = toothGapElementSetTuples[toothGapIter]
			
			nodalStressBarFromElements = dict()
			for leftFlankRightFlankIter in range(0,2):
				elementSet = odb.rootAssembly.instances[gearName].elementSets[toothRootElementSetTuple[leftFlankRightFlankIter]]
				elementSetStress = stress.getSubset(region=elementSet,position=ELEMENT_NODAL)
				fieldValues = elementSetStress.values
				for elementStressNodalValue in fieldValues:
					nodeId = elementStressNodalValue.nodeLabel
					if nodeId in nodalAxialAnd3DPosition[toothGapIter]:
						misesStressAtNode = elementStressNodalValue.mises
						maxPrincipalStressAtNode = elementStressNodalValue.maxPrincipal
						if not nodeId in nodalStressBarFromElements:
							nodalStressBarFromElements[nodeId] = []
						nodalStressBarFromElements[nodeId].append(interpolationFaktorStressStrain*maxPrincipalStressAtNode + (1.0-interpolationFaktorStressStrain)*misesStressAtNode)

						
			## Compute averaged nodal stress
			nodalAveragedStressBarToothGap = dict()
			for key, values in nodalStressBarFromElements.items():
				valueSum = 0.0
				for v in values:
					valueSum += v
				nodalAveragedStressBarToothGap[key] = valueSum/len(values)
			
			if relevantFrameCounter == 0:
				for nodeId, stressBar in nodalAveragedStressBarToothGap.items():
					nodalMinimumStressBar[nodeId] = stressBar
					nodalMaximumStressBar[nodeId] = stressBar

			for nodeId, stressBar in nodalAveragedStressBarToothGap.items():
				nodalMinimumStressBar[nodeId] = min(stressBar, nodalMinimumStressBar[nodeId])
				nodalMaximumStressBar[nodeId] = max(stressBar, nodalMaximumStressBar[nodeId])

	### after loop over all time steps of all tooth gaps
	
	## write root strain to xml result file
	writeMatrixToResultFile(gearNum, transient_fem_root_strain_coordinates_row, transient_fem_root_strain_rolling_path_col, 
			rootStrainMatrix, 'transient_fem_axial_direction_coordinates_x', 'transient_fem_gear_roll_off_process_coordinates_y', 
			'transient_fem_root_strain', 'si__milli_metre', '--', '--')
	writeSingleValueToResultFile(gearNum, rootStrainMatrix.max(), 'transient_fem_root_maximal_strain', '--')
	
	print('root strain matrix finalized')
	#print(rootStrainMatrix)

	
	# initialize root stress matrix
	rootEquivalentStressMatrix = np.empty([len(toothGapElementSetTuples)*len(listOfAxialPositions), len(listOfAbgewickelteDistances)])
	rootEquivalentStressMatrix.fill(np.nan)
	rootMeanStress = rootEquivalentStressMatrix.copy()
	rootOscillatingStress = rootEquivalentStressMatrix.copy()
	rootStressRatio = rootEquivalentStressMatrix.copy()
	mittelspannungsempfindlichkeit = getMittelspannungsempfindlichkeitOfGear(gearNum)
	for toothGapIter in range(len(toothGapElementSetTuples)):

		## set proper gap counter for data filling
		fillDataIter = toothGapIter
		# the gaps match from 1 ... numGaps for driver and driven gear
		if (not isGear1DrivingGear and rotationSpeedOfGear1 < 0 and gearNum == 2) or (not isGear1DrivingGear and rotationSpeedOfGear1 > 0 and gearNum == 1) or (isGear1DrivingGear and rotationSpeedOfGear1 > 0 and gearNum == 2) or (isGear1DrivingGear and rotationSpeedOfGear1 < 0 and gearNum == 1):
			fillDataIter = len(toothGapElementSetTuples) - toothGapIter - 1

		for axialDistKenner, nodeIds in axialSortedNodes[toothGapIter].items():
			colCounter = 0
			for nodeId in nodeIds:
				mittelSpannung    = 0.5 * (nodalMaximumStressBar[nodeId] + nodalMinimumStressBar[nodeId])
				ausschlagSpannung = 0.5 * (nodalMaximumStressBar[nodeId] - nodalMinimumStressBar[nodeId])
				aequivalenteSchwellSpannung = 2.0 * (ausschlagSpannung + mittelspannungsempfindlichkeit*mittelSpannung) / (1.0 + mittelspannungsempfindlichkeit)
				rootEquivalentStressMatrix[fillDataIter*len(listOfAxialPositions) + axialMapping[axialDistKenner]][colCounter] = aequivalenteSchwellSpannung
				rootMeanStress[fillDataIter*len(listOfAxialPositions) + axialMapping[axialDistKenner]][colCounter] = mittelSpannung
				rootOscillatingStress[fillDataIter*len(listOfAxialPositions) + axialMapping[axialDistKenner]][colCounter] = ausschlagSpannung
				rootStressRatio[fillDataIter*len(listOfAxialPositions) + axialMapping[axialDistKenner]][colCounter] = nodalMinimumStressBar[nodeId] / nodalMaximumStressBar[nodeId]
				colCounter += 1
		
	## write root stress to xml result file
	writeMatrixAndColArrayToResultFile(gearNum, listOfAbgewickelteDistances, rootEquivalentStressMatrix, 
			'transient_fem_root_equivalent_stress_coordinates_y', 'transient_fem_root_equivalent_stress', 'si__milli_metre', 'dr__mega_pascal')
	writeSingleValueToResultFile(gearNum, rootEquivalentStressMatrix.max(), 'transient_fem_root_maximal_equivalent_stress', 'dr__mega_pascal')
	
	writeMatrixOnlyToResultFile(gearNum, rootMeanStress, 'transient_fem_root_mean_stress', 'dr__mega_pascal')
	
	writeMatrixOnlyToResultFile(gearNum, rootOscillatingStress, 'transient_fem_root_oscillating_stress', 'dr__mega_pascal')
	
	writeMatrixOnlyToResultFile(gearNum, rootStressRatio, 'transient_fem_root_stress_ratio', '--')
	
	print('root equivalent stress matrix finalized')
	#print(rootEquivalentStressMatrix)


########
############ write results for FLANK values of gears
########
print('\nstart evaluating flank pressure')
step = odb.steps['STEP-1']
zeroFrame = step.frames[0]
contactPressure = zeroFrame.fieldOutputs['CPRESS']
allNodalAxialAnd3DPositionFlankOfGears = []
flankContactPressureOfGears = []
flankNodeIdOfContactPressureOfGears = []
referencePointCoordinatesOfGears = []

####
#### evaluate flank pressure
####
flankNodeSetsOfGears = []
for gearNum in range(1,3): # gear 1 & 2
	referencePointNodeSetName = 'REFERENCE_POINT_        ' + str(gearNum)
	referencePointNodeSet = odb.rootAssembly.nodeSets[referencePointNodeSetName]
	referencePointCoordinates = referencePointNodeSet.nodes[0][0].coordinates  # has only one node
	referencePointCoordinatesOfGears.append(referencePointCoordinates)
	
	supportVectorOfLine = referencePointCoordinates
	directionVectorOfLine = [0.0, 0.0, 1.0]
	fussFormKreisRadius = getRadiusOfGear(gearNum, 'Fussformkreisdurchmesser')

	gearName = 'RAD_VZ_' + str(gearNum)
	flankNodeSetsOfGear = []
	# find relevant nodes on tooth flank
	allNodalAxialAnd3DPositionFlank = []
	axialSortedNodes = []

	listOfAxialPositions = sortedListOfAxialPositionsOfGears[gearNum-1]
	axialMapping = axialPositionsMappingOfGears[gearNum-1]
	
	# collect all flank node sets
	flankenCounter = -1
	for currentNodeSet in odb.rootAssembly.instances[gearName].nodeSets.values():
		nodeSetName = currentNodeSet.name
		
		## care for sense of rotation and choose flank which is in contact
		if (isGear1DrivingGear and rotationSpeedOfGear1 < 0) or (not isGear1DrivingGear and rotationSpeedOfGear1 > 0):
			if not nodeSetName.endswith('F1_NODESET'):
				continue
		else :
			if not nodeSetName.endswith('F2_NODESET'):
				continue
		
		flankenCounter += 1
		flankNodeSetsOfGear.append(nodeSetName)
			
		nodeSetContactStress = contactPressure.getSubset(region=currentNodeSet,position=NODAL)
		
		axialSortedNodesOfFlank = dict()
		nodalAxialAnd3DPositionOfFlank = dict()

		## fill list of radial and axial positions of each node
		fieldValues = nodeSetContactStress.values
			
		for contactPressureNodalValue in fieldValues:
			
			nodeId = contactPressureNodalValue.nodeLabel
			nodeCoordinates = odb.rootAssembly.instances[gearName].nodes[nodeId-1].coordinates
			distanceFromShaftAxis = getDistanceOfPointToLine(supportVectorOfLine, directionVectorOfLine, nodeCoordinates)
			
			if (distanceFromShaftAxis >= (1.0-geometryTolerance)*fussFormKreisRadius):
				axialDistanceKenner = 999999999.0
				for ax in listOfAxialPositions:
					if abs(ax - nodeCoordinates[2])<geometryTolerance:
						axialDistanceKenner = ax
				if axialDistanceKenner == 999999999.0:
					print('ERROR: DAS DARF NICHT SEIN -> MUSS BEREITS ENTHALTEN SEIN')
					listOfAxialPositions.append(nodeCoordinates[2])
					axialDistanceKenner = nodeCoordinates[2]
				
				nodalAxialAnd3DPositionOfFlank[nodeId] = (axialDistanceKenner, nodeCoordinates)
				
				if not axialDistanceKenner in axialSortedNodesOfFlank:
					axialSortedNodesOfFlank[axialDistanceKenner] = dict()
				axialSortedNodesOfFlank[axialDistanceKenner][distanceFromShaftAxis] = nodeId

		#### sort with increasing radial position per axial distance kenner
		axialSortedNodes.append(dict())
		for axialKenner in listOfAxialPositions:
			axialSortedNodes[flankenCounter][axialKenner] = OrderedDict(sorted(axialSortedNodesOfFlank[axialKenner].items()))
			
		allNodalAxialAnd3DPositionFlank.append(nodalAxialAnd3DPositionOfFlank)
		
	allNodalAxialAnd3DPositionFlankOfGears.append(allNodalAxialAnd3DPositionFlank)
	flankNodeSetsOfGears.append(flankNodeSetsOfGear)
	
	## get relevant range for maximum flank pressure output: 
	## an arbitrary axial node set can be chosen (chose 0th here) -> result is equal for each of them
	listOfDiameterValuesFlank = list((axialSortedNodes[0][listOfAxialPositions[0]]).keys())
	for iter in range(len(listOfDiameterValuesFlank)):
		listOfDiameterValuesFlank[iter] *= 2.0
	
	print('flank diameter values of gear ' + str(gearNum) + ':')
	print(listOfDiameterValuesFlank)
	
	########
	######## start evaluation for all time steps
	########

	# initialize pressure matrix
	numberRelevantFrames = int((len(step.frames)-4)/3)
	flankContactPressure = np.empty([len(flankNodeSetsOfGear)*len(listOfAxialPositions), numberRelevantFrames]) #only consider here relevant frames
	flankContactPressure.fill(np.nan)
	flankContactPressureCorrectFlankOrder = flankContactPressure.copy()
	flankNodeIdOfContactPressure = flankContactPressure.copy()
	
	nodalMaximumFlankPressure = dict()
	
	frameCounter = -1
	relevantFrameCounter = -1
	for currentFrame in step.frames:
		frameCounter += 1

		if not isRelevantFrame(frameCounter):
			continue
			
		relevantFrameCounter += 1
			
		contactPressure = currentFrame.fieldOutputs['CPRESS']
		for flankIter in range(len(flankNodeSetsOfGear)):
			currentFlankNodeSet = flankNodeSetsOfGear[flankIter]
			
			maxValueOnLineInWidthDirection = np.zeros(len(listOfAxialPositions))
			idWithMaxValueOnLineInWidthDirection = np.zeros(len(listOfAxialPositions))
			idWithMaxValueOnLineInWidthDirection.fill(np.nan)
			nodeSet = odb.rootAssembly.instances[gearName].nodeSets[currentFlankNodeSet]
			nodalContactPressure = contactPressure.getSubset(region=nodeSet,position=NODAL)
			fieldValues = nodalContactPressure.values
			for nodalContactPressureValue in fieldValues:
				nodeId = nodalContactPressureValue.nodeLabel
				if nodeId in allNodalAxialAnd3DPositionFlank[flankIter]:
					(axialDistKenner, nodeCoordinates) = allNodalAxialAnd3DPositionFlank[flankIter][nodeId]
					contactPressureAtNode = nodalContactPressureValue.data
					oldValue = maxValueOnLineInWidthDirection[axialMapping[axialDistKenner]]
					if contactPressureAtNode > oldValue:
						maxValueOnLineInWidthDirection[axialMapping[axialDistKenner]] = contactPressureAtNode
						idWithMaxValueOnLineInWidthDirection[axialMapping[axialDistKenner]] = nodeId
						
					if relevantFrameCounter == 0:
						nodalMaximumFlankPressure[nodeId] = contactPressureAtNode
					nodalMaximumFlankPressure[nodeId] = max(nodalMaximumFlankPressure[nodeId], contactPressureAtNode)
			
			## set proper flank counter for data filling
			fillDataIterFlanks = flankIter
			# the flanks match from 1 ... numFlanks for driver and driven gear
			if (not isGear1DrivingGear and rotationSpeedOfGear1 < 0 and gearNum == 2) or (not isGear1DrivingGear and rotationSpeedOfGear1 > 0 and gearNum == 1) or (isGear1DrivingGear and rotationSpeedOfGear1 > 0 and gearNum == 2) or (isGear1DrivingGear and rotationSpeedOfGear1 < 0 and gearNum == 1):
				fillDataIterFlanks = len(flankNodeSetsOfGear) - flankIter - 1

			#  data layout in flankContactPressure for driver and driven gear
			#  flank 1  flank 2
			#  ------   ------          
			#  ------   ------     no. of frames in y-direction
			#  ------   ------          
			#   gear width direction in x-direction
			for iter in range(len(listOfAxialPositions)):
				value = maxValueOnLineInWidthDirection[iter]
				flankContactPressureCorrectFlankOrder[fillDataIterFlanks*len(listOfAxialPositions) + iter][relevantFrameCounter] = value
				flankContactPressure[flankIter*len(listOfAxialPositions) + iter][relevantFrameCounter] = value
				id = idWithMaxValueOnLineInWidthDirection[iter]
				flankNodeIdOfContactPressure[flankIter*len(listOfAxialPositions) + iter][relevantFrameCounter] = id
	
	flankContactPressureOfGears.append(flankContactPressure)
	flankNodeIdOfContactPressureOfGears.append(flankNodeIdOfContactPressure)
	### after loop over all time steps of all flanks
	
	## write flank contact pressure to xml result file
	writeMatrixOnlyToResultFile(gearNum, flankContactPressureCorrectFlankOrder, 'transient_fem_flank_pressure', 'dr__mega_pascal')
	
	# compute load dependent total contact ratio
	# if all values in first and last frame are zero and any value > 0 in between, the flank is completely rolled over
	# correct flank order is assumed here such that numbering is fine
	totalContactRatioLoadDependentPerFlank = []
	maximalFlankPressurePerFlank = []
	for flankIter in range(len(flankNodeSetsOfGear)):
		firstAndLastFrameZero = True
		minTouchedInnerFrame = numberRelevantFrames + 1
		maxTouchedInnerFrame = 0
		maxPressureValueFlank = 0.0
		for widthIter in range(len(listOfAxialPositions)):
			for frameIter in range(numberRelevantFrames):
				value = flankContactPressureCorrectFlankOrder[flankIter*len(listOfAxialPositions) + widthIter][frameIter]
				if ((frameIter==0) or (frameIter==numberRelevantFrames-1)) and (abs(value) > 1.0e-9):
					firstAndLastFrameZero = False
				elif (abs(value) > 1.0e-9):
					maxPressureValueFlank = max(maxPressureValueFlank, value)
					minTouchedInnerFrame = min(minTouchedInnerFrame, frameIter)
					maxTouchedInnerFrame = max(maxTouchedInnerFrame, frameIter)
			
		totalContactRatioLoadDependent = np.nan
		if firstAndLastFrameZero and (abs(maxPressureValueFlank) > 1.0e-9):
			totalContactRatioLoadDependent = float(numberOfPitchesToRollOver) * (maxTouchedInnerFrame - minTouchedInnerFrame) / (numberRelevantFrames-1)
			print('gearNum ' + str(gearNum) + ' flank ' + str(flankIter) + ' total contact ratio under load ' + str(totalContactRatioLoadDependent) + ' and maxPressureValueFlank ' + str(maxPressureValueFlank))
		else:
			maxPressureValueFlank = np.nan
			
		totalContactRatioLoadDependentPerFlank.append(totalContactRatioLoadDependent)
		maximalFlankPressurePerFlank.append(maxPressureValueFlank)

	flankNumbers = list(range(1, len(flankNodeSetsOfGear)+1))
	writeTotalContactRatioAndMaxFlankPressurePerFlankToResultFile(gearNum, flankNumbers, 'transient_fem_flank_numbers', totalContactRatioLoadDependentPerFlank, 'transient_fem_total_contact_ratio_load_dependent_per_flank', maximalFlankPressurePerFlank, 'transient_fem_flank_maximal_pressure_per_flank')
	
	print('flank contact pressure matrix finalized')
	#print(flankContactPressure)
	
	# initialize maximum flank pressure matrix
	maximumFlankPressureMatrixCorrectFlankOrder = np.empty([len(flankNodeSetsOfGear)*len(listOfAxialPositions), len(listOfDiameterValuesFlank)])
	maximumFlankPressureMatrixCorrectFlankOrder.fill(np.nan)
	for flankIter in range(len(flankNodeSetsOfGear)):
		
		## set proper flank counter for data filling
		fillDataIterFlanks = flankIter
		# the flanks match from 1 ... numFlanks for driver and driven
		if (not isGear1DrivingGear and rotationSpeedOfGear1 < 0 and gearNum == 2) or (not isGear1DrivingGear and rotationSpeedOfGear1 > 0 and gearNum == 1) or (isGear1DrivingGear and rotationSpeedOfGear1 > 0 and gearNum == 2) or (isGear1DrivingGear and rotationSpeedOfGear1 < 0 and gearNum == 1):
			fillDataIterFlanks = len(flankNodeSetsOfGear) - flankIter - 1
		
		for axialDistKenner, dictDistFromShaftAndNodeIds in axialSortedNodes[flankIter].items():
			nodeIds = dictDistFromShaftAndNodeIds.values()
			colCounter = 0
			for nodeId in nodeIds:
				maximumFlankPressureMatrixCorrectFlankOrder[fillDataIterFlanks*len(listOfAxialPositions) + axialMapping[axialDistKenner]][colCounter] = nodalMaximumFlankPressure[nodeId]
				colCounter += 1
	
	## write maximum flank pressure to xml result file
	writeMatrixAndColArrayToResultFile(gearNum, listOfDiameterValuesFlank, maximumFlankPressureMatrixCorrectFlankOrder, 
			'transient_fem_flank_diameters_coordinates_y', 'transient_fem_flank_local_maximal_pressure', 'si__milli_metre', 'dr__mega_pascal')
	writeSingleValueToResultFile(gearNum, maximumFlankPressureMatrixCorrectFlankOrder.max(), 'transient_fem_flank_maximal_pressure', 'dr__mega_pascal')
	
	print('flank maximum contact pressure matrix finalized')
	#print(maximumFlankPressureMatrixCorrectFlankOrder)
	
###
### evaluate flank wear
###
supportVectorOfLineGear1 = referencePointCoordinatesOfGears[0]
supportVectorOfLineGear2 = referencePointCoordinatesOfGears[1]
directionVectorOfLineGear1 = np.array([0.0, 0.0, 1.0])
directionVectorOfLineGear2 = directionVectorOfLineGear1.copy()

numberOfTeethGear1 = getNumberOfTeethOfGear(1)
numberOfTeethGear2 = getNumberOfTeethOfGear(2)
numberOfRollingPositionsPerPitch = getNumberOfRollingPositionsPerPitch()
timeIncrement = abs(60.0 / (rotationSpeedOfGear1 * numberOfTeethGear1 * numberOfRollingPositionsPerPitch))  # min --> second


### rotation info for gear 1
#using C_proj = C - dot(C - P, n) * n       with P: support vector of plane  and n: normal of plane
dotCMinusPTimesN = np.dot(np.subtract(supportVectorOfLineGear2, supportVectorOfLineGear1), directionVectorOfLineGear1)
projectedPointOnPlaneGear1 = np.subtract(supportVectorOfLineGear2, dotCMinusPTimesN*directionVectorOfLineGear1)
uAxisVectorGear1 = np.subtract(projectedPointOnPlaneGear1, supportVectorOfLineGear1)
uAxisVectorGear1 = uAxisVectorGear1 / np.linalg.norm(uAxisVectorGear1)
vAxisVectorGear1 = -1.0 * np.cross(uAxisVectorGear1, directionVectorOfLineGear1)
trafoMatrixGlobalToLocalGear1 = np.array([uAxisVectorGear1, vAxisVectorGear1, directionVectorOfLineGear1])
trafoMatrixLocalToGlobalGear1 = trafoMatrixGlobalToLocalGear1.transpose()

angleInRadiansGear1 = 2.0 * math.pi / (numberOfTeethGear1 * numberOfRollingPositionsPerPitch)
rotationMatrixGear1 = getRotationMatrix(angleInRadiansGear1, directionVectorOfLineGear1)


### rotation info for gear 2 (rotation direction is opposite to gear 1)
dotCMinusPTimesN = np.dot(np.subtract(supportVectorOfLineGear1, supportVectorOfLineGear2), directionVectorOfLineGear2)
projectedPointOnPlaneGear2 = np.subtract(supportVectorOfLineGear1, dotCMinusPTimesN*directionVectorOfLineGear2)
uAxisVectorGear2 = np.subtract(projectedPointOnPlaneGear2, supportVectorOfLineGear2)
uAxisVectorGear2 = uAxisVectorGear2 / np.linalg.norm(uAxisVectorGear2)
vAxisVectorGear2 = -1.0 * np.cross(uAxisVectorGear2, directionVectorOfLineGear2)
trafoMatrixGlobalToLocalGear2 = np.array([uAxisVectorGear2, vAxisVectorGear2, directionVectorOfLineGear2])
trafoMatrixLocalToGlobalGear2 = trafoMatrixGlobalToLocalGear2.transpose()

angleInRadiansGear2 = - 2.0 * math.pi / (numberOfTeethGear2 * numberOfRollingPositionsPerPitch)
rotationMatrixGear2 = getRotationMatrix(angleInRadiansGear2, directionVectorOfLineGear2)


### further relevant data
allNodalAxialAnd3DPositionFlankGear1 = allNodalAxialAnd3DPositionFlankOfGears[0]
allNodalAxialAnd3DPositionFlankGear2 = allNodalAxialAnd3DPositionFlankOfGears[1]

listOfAxialPositionsGear1 = sortedListOfAxialPositionsOfGears[0]
listOfAxialPositionsGear2 = sortedListOfAxialPositionsOfGears[1]

flankContactPressureGear1 = flankContactPressureOfGears[0]
flankContactPressureGear2 = flankContactPressureOfGears[1]
flankNodeIdOfContactPressureGear1 = flankNodeIdOfContactPressureOfGears[0]
flankNodeIdOfContactPressureGear2 = flankNodeIdOfContactPressureOfGears[1]

flankPressureTimesSlidingSpeedGear1 = flankContactPressureGear1.copy()
flankPressureTimesSlidingSpeedGear1.fill(np.nan)
flankPressureTimesSlidingSpeedGear2 = flankContactPressureGear2.copy()
flankPressureTimesSlidingSpeedGear2.fill(np.nan)


step = odb.steps['STEP-1']
frameCounter = -1
relevantFrameCounter = -1
gear1Name = 'RAD_VZ_1'
gear2Name = 'RAD_VZ_2'
for currentFrame in step.frames:
	frameCounter += 1

	if not isRelevantFrame(frameCounter):
		continue
		
	relevantFrameCounter += 1
	
	displacement = currentFrame.fieldOutputs['U']

	for flankIter in range(len(flankNodeSetsOfGears[0])):
	
		## while reading data adapt flank iterator
		flankIterGear1 = flankIter
		# the flanks match from 1 ... numFlanks for driver and driven (here only gear 1 part of if-clause necessary)
		if (not isGear1DrivingGear and rotationSpeedOfGear1 > 0) or (isGear1DrivingGear and rotationSpeedOfGear1 < 0):
			flankIterGear1 = len(flankNodeSetsOfGears[0]) - flankIter - 1
	
		currentDisplacementOfThisFlankGear1 = dict()
		currentFlankNodeSetNameGear1 = flankNodeSetsOfGears[0][flankIterGear1]
		currentFlankNodeSetGear1 = odb.rootAssembly.instances[gear1Name].nodeSets[currentFlankNodeSetNameGear1]
		nodeSetDisplacement = displacement.getSubset(region=currentFlankNodeSetGear1)
		fieldValues=nodeSetDisplacement.values
		for nodalDisplacementValues in fieldValues:
			nodeId = nodalDisplacementValues.nodeLabel
			if nodeId in allNodalAxialAnd3DPositionFlankGear1[flankIterGear1]:
				(axialDistKenner, nodeCoordinates) = allNodalAxialAnd3DPositionFlankGear1[flankIterGear1][nodeId]
				currentPositionOfNode = nodeCoordinates + nodalDisplacementValues.data
				currentDisplacementOfThisFlankGear1[nodeId] = (axialDistKenner, currentPositionOfNode)
		
		## while reading data adapt flank iterator
		flankIterGear2 = flankIter
		# the flanks match from 1 ... numFlanks for driver and driven (here only gear 2 part of if-clause necessary)
		if (not isGear1DrivingGear and rotationSpeedOfGear1 < 0) or (isGear1DrivingGear and rotationSpeedOfGear1 > 0):
			flankIterGear2 = len(flankNodeSetsOfGears[1]) - flankIter - 1
		
		currentDisplacementOfThisFlankGear2 = dict()
		currentFlankNodeSetNameGear2 = flankNodeSetsOfGears[1][flankIterGear2]
		currentFlankNodeSetGear2 = odb.rootAssembly.instances[gear2Name].nodeSets[currentFlankNodeSetNameGear2]
		nodeSetDisplacement = displacement.getSubset(region=currentFlankNodeSetGear2)
		fieldValues=nodeSetDisplacement.values
		for nodalDisplacementValues in fieldValues:
			nodeId = nodalDisplacementValues.nodeLabel
			if nodeId in allNodalAxialAnd3DPositionFlankGear2[flankIterGear2]:
				(axialDistKenner, nodeCoordinates) = allNodalAxialAnd3DPositionFlankGear2[flankIterGear2][nodeId]
				currentPositionOfNode = nodeCoordinates + nodalDisplacementValues.data
				currentDisplacementOfThisFlankGear2[nodeId] = (axialDistKenner, currentPositionOfNode)

		### evaluate wear indicator for gear 1
		for iterGear1 in range(len(listOfAxialPositionsGear1)):
			nodeIdGear1 = flankNodeIdOfContactPressureGear1[flankIterGear1*len(listOfAxialPositionsGear1) + iterGear1][relevantFrameCounter]
			if math.isnan(nodeIdGear1):
				flankPressureTimesSlidingSpeedGear1[flankIter*len(listOfAxialPositionsGear1) + iterGear1][relevantFrameCounter] = 0.0  # assembly with flankIter
				continue
				
			(axialDistanceKennerGear1, currentPositionGear1) = currentDisplacementOfThisFlankGear1[nodeIdGear1]
			
			minimalDistanceNodeId2 = 0
			minimalDistance = 999999999.0
			minimalDistanceCoordinatesGear2 = []
			for iterGear2 in range(len(listOfAxialPositionsGear2)): # order is already reversed for flank 2 in flankNodeIdOfContactPressureGear2
				nodeIdGear2 = flankNodeIdOfContactPressureGear2[flankIterGear2*len(listOfAxialPositionsGear2) + iterGear2][relevantFrameCounter]
				if math.isnan(nodeIdGear2):
					continue
				(axialDistanceKennerGear2, currentPositionGear2) = currentDisplacementOfThisFlankGear2[nodeIdGear2]
				pointDistance = np.linalg.norm(currentPositionGear2-currentPositionGear1)
				
				if pointDistance < minimalDistance:
					minimalDistance = pointDistance
					minimalDistanceCoordinatesGear2 = currentPositionGear2
					minimalDistanceNodeId2 = nodeIdGear2
					
			if minimalDistance == 999999999.0:
				print('ERROR: NO CLOSEST NODE FOUND ON OTHER FLANK')
				
			centerPointOfBothPointsWithMaximalPressure = 0.5*(minimalDistanceCoordinatesGear2 + currentPositionGear1)

			globalPositionGear1 = np.subtract(centerPointOfBothPointsWithMaximalPressure, supportVectorOfLineGear1)
			localVector = trafoMatrixGlobalToLocalGear1.dot(globalPositionGear1)
			rotatedlocalVector = rotationMatrixGear1.dot(localVector)
			globalPositionRotated = trafoMatrixLocalToGlobalGear1.dot(rotatedlocalVector)
			rotatedGlobalPositionGear1 = np.add(supportVectorOfLineGear1, globalPositionRotated)
			
			globalPositionGear2 = np.subtract(centerPointOfBothPointsWithMaximalPressure, supportVectorOfLineGear2)
			localVector = trafoMatrixGlobalToLocalGear2.dot(globalPositionGear2)
			rotatedlocalVector = rotationMatrixGear2.dot(localVector)
			globalPositionRotated = trafoMatrixLocalToGlobalGear2.dot(rotatedlocalVector)
			rotatedGlobalPositionGear2 = np.add(supportVectorOfLineGear2, globalPositionRotated)

			slidingSpeedNorm = np.linalg.norm(np.subtract(rotatedGlobalPositionGear2, rotatedGlobalPositionGear1)) / timeIncrement
			flankPressureGear1 = flankContactPressureGear1[flankIterGear1*len(listOfAxialPositionsGear1) + iterGear1][relevantFrameCounter]
			pressureTimesSlidingSpeed = flankPressureGear1 * slidingSpeedNorm
			flankPressureTimesSlidingSpeedGear1[flankIter*len(listOfAxialPositionsGear1) + iterGear1][relevantFrameCounter] = pressureTimesSlidingSpeed   # assembly with flankIter
			
		### evaluate wear indicator for gear 2
		for iterGear2 in range(len(listOfAxialPositionsGear2)): # order is already reversed for flank 2 in flankNodeIdOfContactPressureGear2
			nodeIdGear2 = flankNodeIdOfContactPressureGear2[flankIterGear2*len(listOfAxialPositionsGear2) + iterGear2][relevantFrameCounter]
			if math.isnan(nodeIdGear2):
				flankPressureTimesSlidingSpeedGear2[flankIter*len(listOfAxialPositionsGear2) + iterGear2][relevantFrameCounter] = 0.0   # assembly with flankIter
				continue
				
			(axialDistanceKennerGear2, currentPositionGear2) = currentDisplacementOfThisFlankGear2[nodeIdGear2]
			
			minimalDistanceNodeId1 = 0
			minimalDistance = 999999999.0
			minimalDistanceCoordinatesGear1 = []
			for iterGear1 in range(len(listOfAxialPositionsGear1)):
				nodeIdGear1 = flankNodeIdOfContactPressureGear1[flankIterGear1*len(listOfAxialPositionsGear1) + iterGear1][relevantFrameCounter]
				if math.isnan(nodeIdGear1):
					continue
				(axialDistanceKennerGear1, currentPositionGear1) = currentDisplacementOfThisFlankGear1[nodeIdGear1]
				pointDistance = np.linalg.norm(currentPositionGear1-currentPositionGear2)
				
				if pointDistance < minimalDistance:
					minimalDistance = pointDistance
					minimalDistanceCoordinatesGear1 = currentPositionGear1
					minimalDistanceNodeId1 = nodeIdGear1
					
			if minimalDistance == 999999999.0:
				print('ERROR: NO CLOSEST NODE FOUND ON OTHER FLANK')
				
			centerPointOfBothPointsWithMaximalPressure = 0.5*(minimalDistanceCoordinatesGear1 + currentPositionGear2)

			globalPositionGear1 = np.subtract(centerPointOfBothPointsWithMaximalPressure, supportVectorOfLineGear1)
			localVector = trafoMatrixGlobalToLocalGear1.dot(globalPositionGear1)
			rotatedlocalVector = rotationMatrixGear1.dot(localVector)
			globalPositionRotated = trafoMatrixLocalToGlobalGear1.dot(rotatedlocalVector)
			rotatedGlobalPositionGear1 = np.add(supportVectorOfLineGear1, globalPositionRotated)
			
			globalPositionGear2 = np.subtract(centerPointOfBothPointsWithMaximalPressure, supportVectorOfLineGear2)
			localVector = trafoMatrixGlobalToLocalGear2.dot(globalPositionGear2)
			rotatedlocalVector = rotationMatrixGear2.dot(localVector)
			globalPositionRotated = trafoMatrixLocalToGlobalGear2.dot(rotatedlocalVector)
			rotatedGlobalPositionGear2 = np.add(supportVectorOfLineGear2, globalPositionRotated)

			slidingSpeedNorm = np.linalg.norm(np.subtract(rotatedGlobalPositionGear2, rotatedGlobalPositionGear1)) / timeIncrement
			flankPressureGear2 = flankContactPressureGear2[flankIterGear2*len(listOfAxialPositionsGear2) + iterGear2][relevantFrameCounter]
			pressureTimesSlidingSpeed = flankPressureGear2 * slidingSpeedNorm
			flankPressureTimesSlidingSpeedGear2[flankIter*len(listOfAxialPositionsGear2) + iterGear2][relevantFrameCounter] = pressureTimesSlidingSpeed   # assembly with flankIter
	
## write wear indicator to xml result file
writeMatrixOnlyToResultFile(1, flankPressureTimesSlidingSpeedGear1, 'transient_fem_flank_wear_indicator', 'dr__newton*milli_metre^-1*second^-1')
writeSingleValueToResultFile(1, flankPressureTimesSlidingSpeedGear1.max(), 'transient_fem_flank_maximal_wear_indicator', 'dr__newton*milli_metre^-1*second^-1')
writeMatrixOnlyToResultFile(2, flankPressureTimesSlidingSpeedGear2, 'transient_fem_flank_wear_indicator', 'dr__newton*milli_metre^-1*second^-1')
writeSingleValueToResultFile(2, flankPressureTimesSlidingSpeedGear2.max(), 'transient_fem_flank_maximal_wear_indicator', 'dr__newton*milli_metre^-1*second^-1')

print('wear indicator matrices finalized')

############ finalize xml result file
writeResultFileFooter()

print('REXS result file completed\n')


############ START WRITING FULL 3D displacement field for 3D representation
defInfo = ET.Element('defInfo')
g1id = ET.SubElement(defInfo, 'Gear1id')
g1id.text = str(gear1Number)
g2id = ET.SubElement(defInfo, 'Gear2id')
g2id.text = str(gear2Number)

allInstances = []
allInstances = odb.rootAssembly.instances.keys()
allInstances.remove('ASSEMBLY')

cnt = 0

for partName in allInstances:
	inst = odb.rootAssembly.instances[partName]
	bestIdxComb = getInstanceBestNodeIdxForPositioning(inst)
	part = ET.SubElement(defInfo, 'Grid')
	fn = ET.SubElement(part,'fileName')
	fn.text = 'z88i1_' + strToSaveFileName(partName) + '.txt'
	nodenr = ET.SubElement(part, 'nodeCount')
	nodenr.text = str(len(inst.nodes))
	nm = ET.SubElement(part, 'FemName')
	nm.text = partName
	gid = ET.SubElement(part,'id')
	if partName == 'RAD_VZ_1':
		rpxml = ET.SubElement(part, 'ReferencePoint')
		rpx = ET.SubElement(rpxml,'x')
		rpy = ET.SubElement(rpxml,'y')
		rpz = ET.SubElement(rpxml,'z')
		rp = referencePointCoordinatesOfGears[0]
		rpx.text = str(rp[0])
		rpy.text = str(rp[1])
		rpz.text = str(rp[2])
	elif partName == 'RAD_VZ_2':
		rpxml = ET.SubElement(part, 'ReferencePoint')
		rpx = ET.SubElement(rpxml,'x')
		rpy = ET.SubElement(rpxml,'y')
		rpz = ET.SubElement(rpxml,'z')
		rp = referencePointCoordinatesOfGears[1]
		rpx.text = str(rp[0])
		rpy.text = str(rp[1])
		rpz.text = str(rp[2])
	else:
		pass
	gid.text = str(cnt+1)
	cnt = cnt + 1
	for idx in bestIdxComb:
		xyz = list(inst.nodes)[idx].coordinates
		
		posNode = ET.SubElement(part, 'PositioningNode')
		IdxMesh = ET.SubElement(posNode, 'IndexInMesh')
		asmX = ET.SubElement(posNode, 'AsmPositionX')
		asmY = ET.SubElement(posNode, 'AsmPositionY')
		asmZ = ET.SubElement(posNode, 'AsmPositionZ')
		
		IdxMesh.text = str(idx)
		asmX.text = str(xyz[0])
		asmY.text = str(xyz[1])
		asmZ.text = str(xyz[2])
		
partCounter = 0
for partName in allInstances:	
	partCounter = partCounter + 1
	
	print('write 3D results for part ' + partName)
	
	nodeSetGearName = 'ALL_NODES_PART_' + partName
	step = odb.steps['STEP-1']
	frameCounter = -1
	relevantFrameCounter = 0
	for currentFrame in step.frames:
		frameCounter += 1

		if not isRelevantFrame(frameCounter):
			continue
			
		relevantFrameCounter += 1
			
		displacement = currentFrame.fieldOutputs['U']
		nodeSetGear1 = odb.rootAssembly.instances[partName].nodeSets[nodeSetGearName]
		nodeSetDisplacement = displacement.getSubset(region=nodeSetGear1)
		fieldValues=nodeSetDisplacement.values
		
		displacementStepFileName = partName + '_disp-step-' + str(relevantFrameCounter) + '.txt'
		
		#print(currentFrame.frameId)
		time = currentFrame.frameValue*numberOfPitchesToRollOver
		desp = currentFrame.description
		
		# collect info for xml structure file
		step = ET.SubElement(defInfo, 'Step')
		item00 = ET.SubElement(step, 'desp')
		item0 = ET.SubElement(step, 'time')
		item1 = ET.SubElement(step, 'fileName')
		item2 = ET.SubElement(step, 'gridNum')
		item3 = ET.SubElement(step, 'num')
		
		item00.text = str(desp)
		item0.text = str(time)
		item1.text = displacementStepFileName
		item2.text = str(partCounter)
		item3.text = str(relevantFrameCounter)


# write XML structure file with the results
mydata = ET.tostring(defInfo)
dom = xml.dom.minidom.parseString(mydata)
mydata = dom.toprettyxml()

myfile = open("DefInfoNeu.xml", "w")
myfile.write(mydata)
myfile.close()

exportOdbZ88Net(odb)
exportOdbZ88Disp(odb)
