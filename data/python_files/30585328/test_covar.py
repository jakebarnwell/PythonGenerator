import sys; sys.path.append('..')
from numpy import *
from numpy.random import multivariate_normal as mvn
from numpy.testing import assert_allclose
from pylab import *
from covar import *
from utils import *
from math import atan2
import unittest

class TestCost2Go(unittest.TestCase):

    def setUp(self):
        pass

    def test_conf_ellipsoid_axes(self):
        semiaxes = conf_ellipsoid_axes(mat('2 1; 1 2'), 0.9)
        ax1 = to_vec(semiaxes[:,0]); ax2 = to_vec(semiaxes[:,1])
        # Check orthogonal
        assert_allclose(dot(ax1, ax2), 0.0, atol=1e-7)
        # Check angle
        self.assertTrue(atan2(semiaxes[1,0], semiaxes[0,0]) > 0)
        semiaxes = conf_ellipsoid_axes(mat('1 -0.5; -0.5 1'), 0.9)
        self.assertTrue(atan2(semiaxes[1,0], semiaxes[0,0]) < 0)
        semiaxes = conf_ellipsoid_axes(mat('25 0; 0 9'), 0.68)
        ax1 = semiaxes[:,0]; ax2 = semiaxes[:,1]
        # Check ratio
        assert_allclose(mag(ax1), 5/3.0*mag(ax2), atol=1e-7)
        
    def test_draw_ellipsoid(self):
        # Visual confirmation for 2D case
        '''
        figure()
        ax = subplot(111, aspect='equal')
        mu = array([1, 1])
        Sigma = mat('1 -0.5; -0.5 1')
        for k in xrange(100):
            sample = mvn(mu, Sigma)
            ax.plot(sample[0], sample[1], 'bo')
        draw_ellipsoid(mu, Sigma, 0.9)
        autoscale()
        show()
        '''
        pass

if __name__ == '__main__':
    unittest.main()

