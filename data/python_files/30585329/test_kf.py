import random
import unittest
import sys; sys.path.append('..')
from numpy import *
from kalman_filter import *
from numpy.testing import assert_allclose
from numpy.linalg import norm
from utils import *
from math import atan2

def cart_to_polar(pt):
    x = pt[0]; y = pt[1]
    r = sqrt(x**2 + y**2)
    theta = atan2(y, x)
    return array([[r], [theta]])

# Matrices/vectors for Kalman filter tests
# Contrived example checked against MATLAB implementation
A0 = matrix([[1, 2], [3, 4]])
B0 = matrix([[3, 4], [5, 6]])
C1 = matrix([9, 10])
d1 = matrix([1.3])
Q0 = matrix([[3, 1], [1, 4]])
R1 = matrix([2.4])
mu00 = matrix([[6], [4]])
Sigma00 = matrix([[0.9, 0.8], [0.8, 0.9]])
u0 = matrix([[8], [7]])
z1 = C1*mu00 + d1 + matrix([3.1])
# For EKF test case
def dynamics_update(x, u): 
    return A0*x + B0*u

class TestKF(unittest.TestCase):

    def setUp(self):
        pass

    def test_linearize(self):
        # Basic quadratic function
        f_mu, F = linearize_taylor(lambda x: x**2, 1)
        self.assertEqual(f_mu, 1)
        assert_allclose(scalar(F), 2)

        # Mapping from Cartesian to polar coordinates
        x = rand()
        y = rand()
        r = sqrt(x**2 + y**2)
        f_mu, F = linearize_taylor(cart_to_polar, array([[x], [y]]))
        # Analytic solution
        self.assertTrue(allclose(F, array([[x/r, y/r], [-y/r**2, x/r**2]])))

    def test_kf(self):
        mu11, Sigma11 = kf_update(A0, B0, C1, d1, Q0, R1, mu00, Sigma00,
            u0, z1)
        self.assertTrue(allclose(mu11, array([[12.53226367], [-1.52407114]])))
        self.assertTrue(allclose(Sigma11, array([[1.493443, -1.33635416],
            [-1.33635416, 1.21974216]])))

    def test_ekf(self):
        # Test with linear function, should get same results as regular Kalman
        # filter
        f0 = dynamics_update
        h1 = lambda(x): C1*x + d1
        mu11, Sigma11 = ekf_update(f0, h1, Q0, R1, mu00, Sigma00, u0, z1)
        self.assertTrue(allclose(mu11, array([[12.53226367], [-1.52407114]])))
        self.assertTrue(allclose(Sigma11, array([[1.493443, -1.33635416],
            [-1.33635416, 1.21974216]])))

    def test_ukf(self):
        pass

    def test_kf_smooth(self):
        pass

if __name__ == '__main__':
    unittest.main()

