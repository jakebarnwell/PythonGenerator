import solar.sim
from solar.sim.opaquedevice import OpaqueDevice
from os import path
import os
from xml.dom import minidom
import tempfile
import numpy as np
import solar.types
from solar import reference
from solar.types import OpticalStack, OpticalFilm, OpticalMaterial
from wxsolver import AmpsManager
from solar.sim.simulation import OpticalParameters, SimpleOpticalParameters, IlluminationParameters, SimulationParameters

#WxAmps Device class

class WxAmpsDevice:
	def __init__(self, devFile):
		self.amps = AmpsManager()
		self.amps.loadDevice(devFile)
		self.fileName = devFile
		self.inverted = False
	
	def _getText(self, nodelist):
		rc = []
		for node in nodelist:
			if node.nodeType == node.TEXT_NODE:
				rc.append(node.data)
		return ''.join(rc)
	
	def _extract_extinction(self, alpha):
		entries = alpha.getElementsByTagName("waveLength")
		numEntries = len(entries)
		
		k_arr = np.ndarray([numEntries, 2])
		
		for i in xrange(0, numEntries):
			entry = entries[i]
			wave = float(entry.getAttribute("nm"))
			alpha = float(self._getText(entry.childNodes)) #alpha is in inverse meters for WxAmpsDevice
			k = alpha*wave*(10**-9)/(4*3.141592653)
			k_arr[i,0] = wave
			k_arr[i,1] = k
		
		return k_arr
	
	def optical_stack(self, **kw):
		dom = minidom.parse(self.fileName)
		
		dev = dom.getElementsByTagName("Device")[0]
		layerCount = int(dev.getAttribute("layers"))
		
		layers = dev.getElementsByTagName("Material")
		
		stack = OpticalStack()
		
		if len(layers) != layerCount:
			raise Exception("Device file seems to be invalid.  Cannot parse its optical stack.")
		
		for i in xrange(0, len(layers)):
			layer = layers[i]
			
			thickness = float(layer.getAttribute("thickness")) #in microns
			eps = float(self._getText(layer.getElementsByTagName("Electric")[0].getElementsByTagName("Dielectric")[0].childNodes))
			
			n = np.sqrt(eps)
			k = self._extract_extinction(layer.getElementsByTagName("Optical")[0].getElementsByTagName("alpha")[0])
			
			#Build layer
			material = OpticalMaterial(n, k, extend=True)
			film = OpticalFilm(material, thickness*1000) #convert from micron to nm
			stack.add_layer(film)
		
		#We invert devices in amps, but read the stack from the unchanged device file
		#so manually inver the layers if we're inverted.
		if self.inverted:
			return stack.reverse()
		
		#now set the appropriate boundary conditions if we need to
		if "extend" not in kw:
			return stack
		else:
			extend = kw["extend"]
		
		if extend == "front" or extend == "both":
			stack.prepend_layer(stack.layers[0].index_matched())
		if extend == "back" or extend == "both":
			stack.add_layer(stack.layers[-1].index_matched())
		
		return stack
		
	def _set_optical(self, optical):
		if optical.model == OpticalParameters.InternalModel:
			if optical.reflectance != OpticalParameters.ConstantReflectance:
				print "WARNING: WxAmps internal optical model does not support wavelength dependent reflectance.  Using the reflectance at 600 nm as the constant value."
			
			top = optical.front_reflectance(600)
			bottom = optical.back_reflectance(600)
			
			self.amps.setReflectance(float(top), float(bottom))
		else:
			raise Exception("WxAmps does not support external optical modeling yet.")
	
	def _set_illumination(self, illum):
		if illum.eqe:
			eqe_range = illum.eqe_end - illum.eqe_start
			waves = np.linspace(illum.eqe_start, illum.eqe_end, int(eqe_range / illum.eqe_spacing) + 2)
			
			self.amps.enableEQE(waves)
		
		if not illum.dark:
			raise Exception("WxAmps does not currently handle taking IV curves") #FIXME: Setup IV curve taking
		
	def reverse(self):
		self.amps.reverse()
		self.inverted = not self.inverted
			   
	#override solve methods to be wxamps specific
	#if spectrum is set, do the work of converting it to the appropriate format and
	#setting params.light
	#FIXME: solve needs to be redone.
	def solve(self, params):
		self._set_optical(params.optical)
		self._set_illumination(params.illumination)	
			
		self.amps.solve()
		
	def get_eqe(self):
		waves = self.amps.getEQEWavelengths()
		qe = self.amps.getEQEResults()
		
		eqe = np.ndarray([len(waves),2])
		eqe[:,0] = waves
		eqe[:,1] = qe
		
		return eqe.view(solar.types.QuantumEfficiency)
		
	def get_iqe(self):
		waves = self.amps.getEQEWavelengths()
		qe = self.amps.getIQEResults()
		
		iqe = np.ndarray([len(waves),2])
		iqe[:,0] = waves
		iqe[:,1] = qe
		
		return iqe.view(solar.types.QuantumEfficiency)
	
	def calculate_qes(self, fromBehind = False):
		optical = SimpleOpticalParameters(0.0, 0.0)
		
		illum = IlluminationParameters()
		illum.take_eqe(reference.canonical_start, reference.canonical_end, reference.canonical_sampling)
		
		params = SimulationParameters(optical, illum)
		
		if fromBehind:
			self.reverse()

		self.solve(params)
		
		if fromBehind:
			self.reverse()