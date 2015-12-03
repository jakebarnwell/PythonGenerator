import unittest
from solar.types import Spectrum
from solar.fresnel import *
from solar import reference,types
from utils import compare
from numpy import pi, linspace
import scipy

class TestOpticalCode(unittest.TestCase):
	def test_basic(self):
		"""
		Compare with program I wrote previously in Mathematica. Also confirms
		that I don't accidentally mess up the program by editing.
		"""
		n_list=[1,2+4j,3+0.3j,1+0.1j]
		d_list=[inf,2,3,inf]
		th_0=0.1
		lam_vac=100
		
		s_data=fresnel_main('s', n_list, d_list, th_0, lam_vac)
		self.assertAlmostEqual(s_data['r'], -0.60331226568845775-0.093522181653632019j)
		self.assertAlmostEqual(s_data['t'], 0.44429533471192989+0.16921936169383078j)
		self.assertAlmostEqual(s_data['R'], 0.37273208839139516)
		self.assertAlmostEqual(s_data['T'], 0.22604491247079261)
		p_data=fresnel_main('p', n_list, d_list, th_0, lam_vac)
		self.assertAlmostEqual(p_data['r'], 0.60102654255772481+0.094489146845323682j)
		self.assertAlmostEqual(p_data['t'], 0.4461816467503148+0.17061408427088917j)
		self.assertAlmostEqual(p_data['R'], 0.37016110373044969)
		self.assertAlmostEqual(p_data['T'], 0.22824374314132009)
		ellips_data = ellips(n_list, d_list, th_0, lam_vac)
		self.assertAlmostEqual(ellips_data['psi'], 0.78366777347038352)
		self.assertAlmostEqual(ellips_data['Delta'], 0.0021460774404193292)
	
	def test_position_resolved(self):
		"""
		Compare with program I wrote previously in Mathematica. Also, various
		consistency checks.
		"""
		
		d_list = [inf, 100, 300, inf] #in nm
		n_list = [1, 2.2+0.2j, 3.3+0.3j, 1]
		th_0=pi/4
		lam_vac=400
		layer=1
		dist=37
		
		pol='p'
		fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
		self.assertAlmostEqual(fresnel_data['kz_list'][1],
				 0.0327410685922732+0.003315885921866465j)
		data=position_resolved(layer,dist,fresnel_data)
		self.assertAlmostEqual(data['poyn'],0.7094950598055798)
		self.assertAlmostEqual(data['absor'],0.005135049118053356)
		self.assertAlmostEqual(1., sum(absorp_in_each_layer(fresnel_data)))
	
	
		pol='s'
		fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
		self.assertAlmostEqual(fresnel_data['kz_list'][1],
				 0.0327410685922732+0.003315885921866465j)
		data=position_resolved(layer,dist,fresnel_data)
		self.assertAlmostEqual(data['poyn'],0.5422594735025152)
		self.assertAlmostEqual(data['absor'],0.004041912286816303)
		self.assertAlmostEqual(1., sum(absorp_in_each_layer(fresnel_data)))
		
		#Poynting vector derivative should equal absorption
		for pol in ['s','p']:
			fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
			data1=position_resolved(layer,dist,fresnel_data)
			data2=position_resolved(layer,dist+0.001,fresnel_data)
			self.assertAlmostEqual((data1['absor']+data2['absor'])/2 , (data1['poyn']-data2['poyn'])/0.001)
		
		#Poynting vector at end should equal T
		layer=2
		dist=300
		for pol in ['s','p']:
			fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
			data=position_resolved(layer,dist,fresnel_data)
			self.assertAlmostEqual(data['poyn'], fresnel_data['T'])
		
		#Poynting vector at start should equal 1-R
		layer=1
		dist=0
		for pol in ['s','p']:
			fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
			data=position_resolved(layer,dist,fresnel_data)
			self.assertAlmostEqual(data['poyn'], 1-fresnel_data['R'])
		
		#Poynting vector should be continuous
		for pol in ['s','p']:
			layer=1
			dist=100
			fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
			data=position_resolved(layer,dist,fresnel_data)
			poyn1 = data['poyn']
			layer=2
			dist=0
			fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
			data=position_resolved(layer,dist,fresnel_data)
			poyn2 = data['poyn']
			self.assertAlmostEqual(poyn1, poyn2)
			
	def test_position_resolved_2(self):
		"""
		Similar to position_resolved_test(), but with initial and final medium
		having a complex refractive index.
		"""
		d_list = [inf, 100, 300, inf] #in nm
		# "00" is before the 0'th layer. This is easy way to generate th0, ensuring
		#that n0*sin(th0) is real.
		n00 = 1
		th00 = pi/4
		n0 = 1+0.1j
		th_0 = snell(n00,n0,th00)
		n_list = [n0, 2.2+0.2j, 3.3+0.3j, 1+0.4j]
		lam_vac=400
		layer=1
		dist=37
	
		for pol in ['s','p']:
			fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
			data=position_resolved(layer,dist,fresnel_data)
			self.assertAlmostEqual(1., sum(absorp_in_each_layer(fresnel_data)))
		
		#Poynting vector derivative should equal absorption
		for pol in ['s','p']:
			fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
			data1=position_resolved(layer,dist,fresnel_data)
			data2=position_resolved(layer,dist+0.001,fresnel_data)
			self.assertAlmostEqual((data1['absor']+data2['absor'])/2 , (data1['poyn']-data2['poyn'])/0.001)
	
		#Poynting vector at end should equal T
		layer=2
		dist=300
		for pol in ['s','p']:
			fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
			data=position_resolved(layer,dist,fresnel_data)
			self.assertAlmostEqual(data['poyn'], fresnel_data['T'])
		
		#Poynting vector at start should equal 1-R
		layer=1
		dist=0
		for pol in ['s','p']:
			fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
			data=position_resolved(layer,dist,fresnel_data)
			self.assertAlmostEqual(data['poyn'], 1-fresnel_data['R'])
	
		#Poynting vector should be continuous
		for pol in ['s','p']:
			layer=1
			dist=100
			fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
			data=position_resolved(layer,dist,fresnel_data)
			poyn1 = data['poyn']
			layer=2
			dist=0
			fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
			data=position_resolved(layer,dist,fresnel_data)
			poyn2 = data['poyn']
			self.assertAlmostEqual(poyn1, poyn2)
		
	def test_absorp_analytic_fn(self):
		"""
		Test find_absorp_analytic_fn() and flip_absorp_analytic_fn()
		"""
		d_list = [inf, 100, 300, inf] #in nm
		n_list = [1, 2.2+0.2j, 3.3+0.3j, 1]
		th_0=pi/4
		lam_vac=400
		layer=1
		d=d_list[layer]
		dist=37
		
		for pol in ['s','p']:
			fresnel_data = fresnel_main(pol,n_list,d_list,th_0,lam_vac)
			expected_absorp = position_resolved(layer, dist, fresnel_data)['absor']
			absorp_func_data = find_absorp_analytic_fn(layer, fresnel_data)
			self.assertAlmostEqual(run_absorp_analytic_fn(dist,absorp_func_data),
				 expected_absorp)
			absorp_func_data2 = flip_absorp_analytic_fn(d,absorp_func_data)
			dist_from_other_side = d - dist
			self.assertAlmostEqual(run_absorp_analytic_fn(dist_from_other_side,absorp_func_data2),
				   expected_absorp)	
	
	def test_incoherent(self):
		"""
		test incoherent_main(). To do: Add more tests.
		"""
		
		#3-incoherent-layer test, real refractive indices (so that R and T are the
		#same in both directions)    
		n0 = 1
		n1 = 2
		n2 = 3
		n_list = [n0,n1,n2]
		d_list = [inf,inf,inf]
		th0 = pi/3
		th1 = snell(n0,n1,th0)
		th2 = snell(n0,n2,th0)
		lam_vac = 400
	
		for pol in ['s','p']:
			inc_data = incoherent_main(pol,n_list,d_list,th0,lam_vac)
			R0 = abs(interface_r(pol,n0,n1,th0,th1)**2)
			R1 = abs(interface_r(pol,n1,n2,th1,th2)**2)
			T0 = 1-R0
			RR = R0 + R1*T0**2/(1-R0*R1)
			self.assertAlmostEqual(inc_data['R'],RR)
			self.assertAlmostEqual(inc_data['R']+inc_data['T'],1)
		
		#One finite layer with incoherent layers on both sides. Should agree with
		#coherent program
		n0 = 1+0.1j
		n1 = 2+0.2j
		n2 = 3+0.4j
		n_list = [n0,n1,n2]
		d_list = [inf,100,inf]
		n00 = 1
		th00 = pi/3
		th0 = snell(n00,n0,th00)
		lam_vac = 400
		for pol in ['s','p']:
			inc_data = incoherent_main(pol,n_list,d_list,th0,lam_vac)
			coh_data = fresnel_main(pol,n_list,d_list,th0,lam_vac)
			self.assertAlmostEqual(inc_data['R'],coh_data['R'])
			self.assertAlmostEqual(inc_data['T'],coh_data['T'])
			self.assertAlmostEqual(1,sum(inc_absorp_in_each_layer(inc_data)))
		
		#The coherent program with a thick but randomly-varying-thickness substrate
		#should agree with the incoherent program.
		nair = 1+0.1j
		nfilm = 2+0.2j
		nsub = 3
		nf = 3+0.4j
		n_list = [nair,nfilm,nsub,nf]
		n00 = 1
		th00 = pi/3
		th0 = snell(n00,n0,th00)
		lam_vac = 400
		for pol in ['s','p']:
			d_list_inc = [inf,100,inf,inf]
			inc_data = incoherent_main(pol,n_list,d_list_inc,th0,lam_vac)
			coh_Rs = []
			coh_Ts = []
			for dsub in linspace(10000,30000,1357):
				d_list = [inf,100,dsub,inf]
				coh_data = fresnel_main(pol,n_list,d_list,th0,lam_vac)
				coh_Rs.append(coh_data['R'])
				coh_Ts.append(coh_data['T'])
			#self.assertAlmostEqual(np.average(coh_Rs),inc_data['R'])
			#self.assertAlmostEqual(np.average(coh_Ts),inc_data['T'])
	
	def test_RT(self):
		"""
		Tests of formulas for R and T
		"""		
		#R+T should equal 1
		
		# "00" is before the 0'th layer. This is easy way to generate th0, ensuring
		#that ni*sin(thi) is real.
		n00 = 1
		th00 = pi/3
		ni=2+.1j
		nf=3+.2j
		thi = snell(n00,ni,th00)
		thf = snell(n00,ni,th00)
		for pol in ['s','p']:
			self.assertAlmostEqual(interface_R(pol,ni,nf,thi,thf)
					 + interface_T(pol,ni,nf,thi,thf),1)
		
		#When ni is real, R should equal abs(r)^2
		ni = 2.
		nf = 3.+0.2j
		thi = pi/5
		thf = snell(ni,nf,thi)
		for pol in ['s','p']:
			r = interface_r(pol,ni,nf,thi,thf)
			R = interface_R(pol,ni,nf,thi,thf)
		self.assertAlmostEqual(abs(r)**2,R)