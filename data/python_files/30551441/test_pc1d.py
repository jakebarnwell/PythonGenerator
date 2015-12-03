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
from solar.sim import pc1d
from solar.sim import SimpleDevice

import matplotlib.pylab as plt
import numpy as np	
import Ice


class TestPC1D(unittest.TestCase):
	def setUp(self):
		try:
			pc1d.initialize("172.16.168.128", 10000, silent=True, timeout=4000)
		except Ice.ConnectTimeoutException:
			self.skipTest("PC1D Grid node not available for testing")
	
	def test_simpledevice(self):
		sil = SimpleDevice.FromPC1DDirectory(os.path.join(os.path.dirname(__file__), "data", "si_reference"))
		
	def test_current(self):
		sil = SimpleDevice.FromPC1DDirectory(os.path.join(os.path.dirname(__file__), "data", "si_reference"))
		
		current = sil.current()
		
		self.assertAlmostEqual(current, 0.0335616807321)