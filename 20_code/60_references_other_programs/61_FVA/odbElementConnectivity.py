# odbElementConnectivity.py
# Script to extract node and element information.
#
# Command line argument is the path to the output
# database.
#
# For each node of each part instance:
#	 Print the node label and the nodal coordinates.
#
# For each element of each part instance:
#	 Print the element label, the element type, the
#	 number of nodes, and the element connectivity.

from odbAccess import *
import sys

import numpy as np
from numpy.linalg import norm


from itertools import permutations, combinations
#from abaqus_postprocessing import isRelevantFrame

def isRelevantFrame(frameCounter):
	if frameCounter % 3 == 0 and frameCounter > 3:
		return True
	else:
		return False
		
def isRelevantFrame1(frame):
	dispField = frame.fieldOutputs['U']
	if len(dispField.values)>10:
		return True
	else:
		return False
		
def getInstanceBestNodeIdxForPositioning(instance):
	numNodes = numElements = 0
	cnt = 0
	
	n = len(instance.nodes)
	numNodes = numNodes + n
	name = instance.name
	print('Number of nodes of instance %s: %d' % (name, n))
	
	print()
	print('NODAL COORDINATES')

	# For each node of each part instance
	# print the node label and the nodal coordinates.
	# Three-dimensional parts include X-, Y-, and Z-coordinates.
	# Two-dimensional parts include X- and Y-coordinates.
	cnt = 0
	if instance.embeddedSpace == THREE_D:
		print('	X		 Y		 Z')
		
		#for node in instance.nodes:
		#	print(node.coordinates)
		#	cnt = cnt + 1
		#	if cnt == 20:
		#		break
		li = list(instance.nodes)
		print(len(li))
		#print(instance.nodes.getBoundingBox())
		if len(li)<100:
			raise ValueError(name+ 'has rare nodes')

		i = 0
		for nd in li:
			xyz = nd.coordinates
			if i==0:
				print(nd)
			
			if i==0:
				maX = (xyz[0],i)
				maY = (xyz[1],i)
				maZ = (xyz[2],i)
				miX = (xyz[0],i)
				miY = (xyz[1],i)
				miZ = (xyz[2],i)
			
			if xyz[0]>maX[0]:
				maX=(xyz[0],i)
			if xyz[1]>maY[0]:
				maY=(xyz[1],i)
			if xyz[2]>maZ[0]:
				maZ=(xyz[2],i)
			
			if xyz[0]<miX[0]:
				miX=(xyz[0],i)
			if xyz[1]<miY[0]:
				miY=(xyz[1],i)
			if xyz[2]<miZ[0]:
				miZ=(xyz[2],i)
				
			i=i+1
			
		n1 = li[100]
		n2 = li[200]
		n3 = li[300]
		print(n1.coordinates)
		print(n2.coordinates)
		print(n2.coordinates)
		print(maX,maY,maZ)
		print(miX,miY,miZ)
	bdIdxSet = {maX[1],maY[1],maZ[1], miX[1],miY[1],miZ[1]}
	print(bdIdxSet)
	comb = combinations(bdIdxSet,3)
	print("comb", comb)
	comLi = []
	comValLi = []
	i = 0
	for com in list(comb):
		id1 = int(com[0])
		id2 = int(com[1])
		id3 = int(com[2])
		ar1 = li[id1].coordinates
		ar2 = li[id2].coordinates
		ar3 = li[id3].coordinates
		p1 = np.array(ar1)
		p2 = np.array(ar2)
		p3 = np.array(ar3)
		v0 = np.subtract(p2,p1)
		v1 = np.subtract(p3,p1)
		varea = norm(np.cross(v0,v1))
		comValLi.append(varea)
		comLi.append(com)
		print(com, varea)
		i = i+1
	
	print(comValLi)
	
	bestCombIdx = comValLi.index(max(comValLi))
	#print(comLi)
	#print("best Combo", comLi[bestCombIdx])
	return comLi[bestCombIdx]
 

def getBestCombo(odb):
	sys.out = open('ElementOut.txt','w')

	# Open the output database.

	
	assembly = odb.rootAssembly

	# For each instance in the assembly.

	numNodes = numElements = 0
	cnt = 0
	
	print(assembly)

	for name, instance in assembly.instances.items():
		try:
			comb = getInstanceBestNodeIdxForPositioning(instance)
			print("best idx combo", comb)
			pass
		except ValueError:
			#kein Panik
			print('value error catched')
			pass

	sys.stdout.close()
	


def collectNodes(instance):
	n = len(instance.nodes)
	#print('Number of nodes of instance %s: %d' % (name, n))
	#numNodes = numNodes + n

	print()
	print('NODAL COORDINATES')

	# For each node of each part instance
	# print(the node label and the nodal coordinates.
	# Three-dimensional parts include X-, Y-, and Z-coordinates.
	# Two-dimensional parts include X- and Y-coordinates.

	if instance.embeddedSpace == THREE_D:
		print('	X		 Y		 Z')
		for node in instance.nodes:
			print(node.coordinates)
	else:
		print('	X		 Y')
		for node in instance.nodes:
			print(node.coordinates)

def collectElements(instance):
	# For each element of each part instance
	# print(the element label, the element type, the
	# number of nodes, and the element connectivity.
	   
	n = len(instance.elements)
	#print('Number of elements of instance ', name, ': ', n)
	#numElements = numElements + n

	print('ELEMENT CONNECTIVITY')
	print(' Number  Type	Connectivity')
	for element in instance.elements:
		print('%5d %8s' % (element.label, element.type),)
		for nodeNum in element.connectivity:
		   print('%4d' % nodeNum,)
		print()
		
def convertAbqToZ88Element(element, nEl):
	s = ''
	nodeNumLi = []
	typ = ''
	for nodeNum in element.connectivity:
		nodeNumLi.append(str(nodeNum))
	if element.type == "C3D4":
		typ = '17'
		for nodeNum in nodeNumLi:
		   s = s + str(nodeNum) + '\t'
	if element.type == "C3D8" or element.type == "C3D8R":
		typ = '1'
		s += nodeNumLi[7-1] + '\t'
		s += nodeNumLi[8-1] + '\t'
		s += nodeNumLi[5-1] + '\t'
		s += nodeNumLi[6-1] + '\t'
		s += nodeNumLi[3-1] + '\t'
		s += nodeNumLi[4-1] + '\t'
		s += nodeNumLi[1-1] + '\t'
		s += nodeNumLi[2-1] + '\t'
	if element.type == "C3D10" or element.type == "C3D10R":
		typ = '16'
		s += nodeNumLi[1-1] + '\t'
		s += nodeNumLi[2-1] + '\t'
		s += nodeNumLi[3-1] + '\t'
		s += nodeNumLi[4-1] + '\t'
		s += nodeNumLi[5-1] + '\t'
		s += nodeNumLi[6-1] + '\t'
		s += nodeNumLi[7-1] + '\t'
		s += nodeNumLi[9-1] + '\t'
		s += nodeNumLi[10-1] + '\t'
		s += nodeNumLi[8-1] + '\t'
	if element.type == "C3D20" or element.type == "C3D20R":
		typ = '10'
		s += nodeNumLi[7-1] + '\t'
		s += nodeNumLi[8-1] + '\t'
		s += nodeNumLi[5-1] + '\t'
		s += nodeNumLi[6-1] + '\t'
		s += nodeNumLi[3-1] + '\t'
		s += nodeNumLi[4-1] + '\t'
		s += nodeNumLi[1-1] + '\t'
		s += nodeNumLi[2-1] + '\t'
		
		s += nodeNumLi[15-1] + '\t'
		s += nodeNumLi[16-1] + '\t'
		s += nodeNumLi[13-1] + '\t'
		s += nodeNumLi[14-1] + '\t'
		
		s += nodeNumLi[11-1] + '\t'
		s += nodeNumLi[12-1] + '\t'
		s += nodeNumLi[9-1] + '\t'
		s += nodeNumLi[10-1] + '\t'
		
		s += nodeNumLi[19-1] + '\t'
		s += nodeNumLi[6-1] + '\t'
		s += nodeNumLi[17-1] + '\t'
		s += nodeNumLi[18-1] + '\t'
	s.rstrip()
	s = str(nEl+1)+'\t'+typ+'\n'+s+'\n'
	return s
		
def makeZ88Net(instance, fileOutName):
	fo = open(fileOutName,'w')
	#header
	nNode = len(instance.nodes)
	nElement = len(instance.elements)
	fo.write('3\t%d\t%d\t%d\t0\n' % (nNode, nElement, nNode*3))
	#for v in fieldValues:
	#	fo.write('%10.4E\n%10.4E\n%10.4E\n' % (v.data[0], v.data[1], v.data[2]))
	n = 0
	#write nodes
	for node in instance.nodes:
		fo.write('%d\t3\t%10.4E\t%10.4E\t%10.4E\n' % (n+1, node.coordinates[0], node.coordinates[1], node.coordinates[2]))
		n = n + 1
	#write elements
	nEl = 0
	#print((instance.elements[0].type))
	for element in instance.elements:
		#fo.write(str(nEl+1)+'\t1\n')
		#s = ''
		#for nodeNum in element.connectivity:
		#   s = s + str(nodeNum) + '\t'
		#s = s.rstrip()
		#fo.write(s+'\n')
		s = convertAbqToZ88Element(element, nEl)
		fo.write(s)
		nEl = nEl + 1
	fo.close()
	print(fileOutName + " was written.")


def exportOdbZ88Net(odb):
	
	assembly = odb.rootAssembly
	
	for name, instance in assembly.instances.items():
		try:
			makeZ88Net(instance, 'z88i1_'+name+".txt")
			pass
		except ValueError:
			#kein Panik
			print('value error catched')
			pass

def walkThrough(odb):
	
	assembly = odb.rootAssembly
	# For each instance in the assembly.

	numNodes = numElements = 0
	cnt = 0
	
	print(assembly)

	for name, instance in assembly.instances.items():
		try:
	 #	   collectNodes(instance)
			pass
		except ValueError:
			#kein Panik
			print('value error catched')
			pass

	for name, instance in assembly.instances.items():
		try:
			collectElements(instance)
			pass
		except ValueError:
			#kein Panik
			print('value error catched')
			pass

def writeDisp(instance, step, partName):
	frameCounter = -1
	relevantFrameCounter = 0
	nodeSetGearName = 'ALL_NODES_PART_' + partName
	for currentFrame in step.frames:
		frameCounter += 1

		if not isRelevantFrame(frameCounter):
			continue
			
		relevantFrameCounter += 1
		
		print('frame # ' + str(frameCounter) + ' processed')
		
		#if relevantFrameCounter > 2:   #stop earlier for debug reasons
		#	break
		
		#displacement = currentFrame.fieldOutputs['U']
		#nodeSetGear1 = odb.rootAssembly.instances[partName].nodeSets[nodeSetGearName]
		#nodeSetDisplacement = displacement.getSubset(region=nodeSetGear1)
		#fieldValues=nodeSetDisplacement.values
		
		displacementStepFileName = partName + '_disp-step-' + str(relevantFrameCounter) + '.txt'
		
		#print(' before open frame'+str(frameCounter)))
		dispFile = open(displacementStepFileName,'w')
		#print(' after open frame'+str(frameCounter)))
		
		#print('before load [U] frame'+str(frameCounter))
		nodeSetGear1 = instance.nodeSets[nodeSetGearName]
		dispField = currentFrame.fieldOutputs['U'].getSubset(region=nodeSetGear1)
		#dispField = currentFrame.fieldOutputs['U'].nodeSets[nodeSetGearName]
		
		#numNodesTotal = len( instance.nodes )
		numNodesTotal = len( nodeSetGear1.nodes )
		
		print('nodeSetLen:', len(nodeSetGear1.nodes))
		print('dispField.valuesLen:', len(dispField.values))
		
		
		#print('before range loop'+str(numNodesTotal))
		res = []
		
		for i in range( numNodesTotal ):
			res.append((0,0,0))
			#v = dispField.values[i]
			#print(v.nodeLabel)
		
		print('res len', len(res))
		
		for v in dispField.values:
			res[v.nodeLabel-1] = (v.data[0], v.data[1], v.data[2])
			#print(v)
		
		for r in res:
			dispFile.write('%10.4E\n%10.4E\n%10.4E\n' % (r[0], r[1], r[2]))
		
		dispFile.close()
		
def exportOdbZ88Disp(odb):
	
	assembly = odb.rootAssembly
	
	for name, instance in assembly.instances.items():
		try:
			if name == 'ASSEMBLY':
				continue
			writeDisp(instance, odb.steps['STEP-1'], name)
			pass
		except:
			print("Unexpected error:", sys.exc_info()[0])
			raise
			
def main():
	#print(sys.argv))
	odbPath = sys.argv[1]
	print('Model data for ODB: ', odbPath)

	odb = openOdb(path=odbPath)
	#getBestCombo(odb)
	
	#walkThrough(odb)
	exportOdbZ88Net(odb)
	#exportOdbZ88Disp(odb)

if __name__ == "__main__":
	main()