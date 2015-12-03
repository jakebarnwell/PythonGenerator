import os.path
import PC1DGrid
import excite
import csv
from solar.sim.opaquedevice import OpaqueDevice
import numpy as np
from solar.types import QuantumEfficiency
import solar.sim.pc1d

class PC1DDevice (OpaqueDevice):
	def __init__(self, deviceFile, otherFiles):
		OpaqueDevice.__init__(self, deviceFile, otherFiles)
		
	def solve(self, excite):
		node = solar.sim.pc1d.getNode()
		
		node.setSimpleDevice(self.toWire())
		node.setExcitation(excite)
		node.solve()
		
		results = node.getResults()
		
		return results
	
	def ivcurve(self):
		results = self.solve(excite.SweepIV(excite.OneSun()))
		
		iv = np.zeros([len(results.baseVoltage),2])
		
		for i in xrange(0, len(results.baseVoltage)):
			iv[i,0] = results.baseVoltage[i]
			iv[i,1] = results.baseCurrent[i]
		
		return iv
		
	def quantumefficiency(self, front=True):
		node = solar.sim.pc1d.getNode()
		
		node.setSimpleDevice(self.toWire())
		node.setExcitation(excite.SweepEQE(front))
		node.solve()
		
		results = node.getQuantumEfficiencies()
		
		return results
	
	def transmitted_light(self, front=True):
		node = solar.sim.pc1d.getNode()
		
		node.setSimpleDevice(self.toWire())
		node.setExcitation(excite.SweepEQE(front))
		node.solve()
		
		results = node.getOpticalResults()
		
		trans = np.ndarray([len(results.wavelengths), 2])
		trans[:,0] = results.wavelengths
		trans[:,1] = results.transmission
		
		return trans
		
	def eqe(self, front=True):
		results = self.quantumefficiency(front)
		
		qe = np.zeros([len(results.wavelengths), 2])
		
		for i in xrange(0, len(results.wavelengths)):
			qe[i,0] = results.wavelengths[i]
			qe[i,1] = results.eqe[i]
		
		return qe.view(QuantumEfficiency)
		
	def jsc(self, lightF=None, lightB=None):
		if not lightF:
			lightF = excite.OneSun()
			
		results = self.solve(excite.SteadyCurrent(0.0, lightF, lightB))
		
		return results.baseCurrent[0]
	