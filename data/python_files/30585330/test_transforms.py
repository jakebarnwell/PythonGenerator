import random
import unittest
import sys; sys.path.append('..')
from numpy import *
from transforms import *
from numpy.testing import assert_allclose
from numpy.linalg import norm

def rand():
    return random.random()

class TestTransforms(unittest.TestCase):

    def setUp(self):
        self.rand = rand()
        pass

    def test_theta2R(self):
        R = theta2R(self.rand)
        assert_allclose(R[0,0], cos(self.rand))
        assert_allclose(R[0,1], -sin(self.rand))

    def test_R2theta(self):
        R = theta2R(self.rand)
        assert_allclose(self.rand, R2theta(R))

    def test_q2R(self):
        R = q2R(array([0, 0, 0, 1]))
        self.assertTrue(allclose(R, eye(3)))

    def test_R2q(self):
        q = R2q(eye(3))
        self.assertTrue(allclose(q, array([0, 0, 0, 1])))

        q = array([0.435953, 0.310622, -0.718287, 0.444435])
        R = q2R(q)
        q2 = R2q(R)
        self.assertTrue(allclose(q, q2))

    #TODO def test_rpy2R

    #TODO def test_R2rpy

if __name__ == '__main__':
    unittest.main()

