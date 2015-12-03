import unittest
from upconverter_harness import UpconverterHarness
from solar.upconversion import gaussian, square, empirical
from solar.types import Spectrum, QuantumEfficiency, OpticalMaterial
from solar import reference,utilities
from solar.sim import SimpleDevice
from utils import compare
import numpy as np
import os.path
import scipy
from scipy import fftpack, signal
from solar.sim import *

class TestSimulatedDevice(unittest.TestCase):
	def setUp(self):
		self.front = QuantumEfficiency.IdealQE(1.1)
		self.back = QuantumEfficiency.ZeroQE()
		self.device = SimpleDevice(self.front)
		self.optical = SimpleOpticalParameters(0.5, 1.0)
		self.illumination = IlluminationParameters()
		self.params = SimulationParameters(self.optical, self.illumination)
		
	def test_eqes(self):
		compare.CompareArrays(self, self.front, self.device.front_eqe())
		compare.CompareArrays(self, self.back, self.device.back_eqe())
		
	def test_voltage(self):
		self.device.set_voltage(1.0)
		
		self.assertRaises(Exception, self.device.front_eqe, self.device)
	
	def test_optical_params(self):
		self.assertAlmostEqual(self.params.optical.front_reflectance(600), 0.5)
		self.assertAlmostEqual(self.params.optical.back_reflectance(600), 1.0)
	
	def test_illumination(self):
		self.assertTrue(self.illumination.dark)
		
		self.illumination.add_light(Spectrum.AM15G(), True)
		self.assertFalse(self.illumination.dark)
		self.assertIsNot(self.illumination.absolute_light(True), None)
		self.assertIs(self.illumination.absolute_light(False), None)
		
		#We should return an error if there's more than one light
		self.illumination.add_light(Spectrum.AM15G(), True)
		self.assertRaises(Exception, self.illumination.absolute_light, self.illumination, True)
		