import unittest
from solar.sim.wxamps import WxAmpsDevice
from solar.types import *
from solar.sim import *
import scipy.integrate
from utils import compare, persist 
import numpy as np	
import os.path


class TestWxAmps(unittest.TestCase):
	def setUp(self):
		self.dev = wxamps.WxAmpsDevice(os.path.join(os.path.dirname(__file__), "data", "CdTe_Gloeckler.dev"))
		
		optical = SimpleOpticalParameters(0.0, 0.0)
		illum = IlluminationParameters()
		illum.take_eqe(380, 900, 5)

		self.params = SimulationParameters(optical, illum)
	
	def check_device(self, file):
		dev = wxamps.WxAmpsDevice(os.path.join(os.path.dirname(__file__), "data", file))
		
		dev.solve(self.params)
		
		front = dev.get_eqe()
		
		dev.reverse()
		dev.solve(self.params)
		
		back = dev.get_eqe()
		
		return (front, back)
		
	def test_front(self):
		self.dev.solve(self.params)
		
		eqe = self.dev.get_eqe()
		compare.CompareArrayWithReference(self, eqe, "cdte-front-eqe.csv")
	
	def test_back(self):
		self.dev.reverse()

		self.dev.solve(self.params)
		
		eqe = self.dev.get_eqe()
		compare.CompareArrayWithReference(self, eqe, "cdte-back-eqe.csv")
		
	def test_graded_cigs(self):
		(front, back) = self.check_device("Cigs_Graded.dev")
		
		compare.CompareArrayWithReference(self, front, "cigs-graded-front.csv")
		
	def test_ungraded_cigs(self):
		(front, back) = self.check_device("Cigs_Ungraded.dev")
		
		compare.CompareArrayWithReference(self, front, "cigs-ungraded-front.csv")
		
	def test_combined(self):	
		"""
		Simulate the eqe of the device with a back reflector as the simulated transmission
		of the device multiplied by the back eqe + the front eqe.  This should test how well
		our optical model maps onto the one used by wxamps.
		"""	
		optical = SimpleOpticalParameters(0.0, 0.0)
		illum = IlluminationParameters()
		illum.take_eqe(380, 900, 5)
		
		params = SimulationParameters(optical, illum)
		
		self.dev.solve(params)
		front = self.dev.get_eqe()
		self.dev.reverse()
	
		self.dev.solve(params)
		back = self.dev.get_eqe()
		self.dev.reverse()
		
		optical = SimpleOpticalParameters(0.0, 1.0)
		params = SimulationParameters(optical, illum)
		
		self.dev.solve(params)
		comb = self.dev.get_eqe()
		
		stack = self.dev.optical_stack()
		stack.prepend_layer(OpticalFilm(OpticalMaterial(float(stack.layers[0].material.n(800)), 0.0), np.inf))
		stack.add_layer(OpticalFilm(OpticalMaterial(float(stack.layers[-1].material.n(800)), 0.0), np.inf))
				
		trans = stack.transmission(front[:,0])		
		
		simulated = front[:,1] + back[:,1]*trans
		
		diff = comb[:,1] - simulated
		diff *= diff
		
		normed_diff = np.sqrt(scipy.integrate.trapz(diff, comb[:,0]))
		total = scipy.integrate.trapz(back[:,1], back[:,0])
		
		self.assertLess(normed_diff/total, 0.001)