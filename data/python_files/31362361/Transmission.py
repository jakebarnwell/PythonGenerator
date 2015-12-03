import numpy as np
import os.path
import cPickle
import tempfile
from CacheFile import CacheFile
from Extinction import Extinction
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt


'''
Filenames:
    mktrans_zm_10_10.dat
    mktrans_zm_16_10.dat
    mktrans_zm_30_10.dat
    mktrans_zm_50_10.dat
'''



class Transmission(CacheFile):
    def __init__(self, clear=False, verbose=False):
        super(Transmission, self).__init__("", clear, verbose)
        self.basedir = "Transmission"
        self.extinction = Extinction(verbose)

    
    def getData(self, watercolumn, airmass=1.0, disable=False):
        self.filename = "mktrans_zm_%2d_10.dat" % watercolumn
        return self._createFullRange(airmass, disable)

    def _createFullRange(self, airmass, disable):
        tdata = super(Transmission, self).getData()

        # must add the extinction portion of the transmission spectrum to
        # the variable water column depth
        ex, ey = self.extinction.getData()


        # must interpolate the given data
        interp = interp1d(ex, ey, kind='linear')

        # get the sampling grid of the transmission information
        sgrid = np.diff(tdata[0])


        nPoints = (ex.max() - ex.min()) / sgrid[0]

        #print "%d points required" % nPoints
        #print "Spanning %f -> %f" % (ex.min(), tx.max())

        outdata = np.zeros([2, nPoints])

        ## set up the x array
        outdata[0, :] += np.linspace(ex.min(), tdata[0].min(), nPoints)
        ## need 2 indices, lower and upper
        li = outdata[0] < 0.7
        hi = (outdata[0] >= 0.7) & (outdata[0] <= 0.9)

        if not disable: 
            outdata[1, li] = 10**(-0.6 * airmass * interp(outdata[0, li]))
        else:
            outdata[1, li] = 1.0
        outdata[1, hi] = 1.0

        outdata = np.hstack([outdata, tdata])

        #self.plot(outdata[0], outdata[1])

        return outdata

    def plot(self, x, y):
        plt.plot(x, y, 'r-')
        plt.xlim(0.3, 1.0)
        plt.show()

if __name__ == '__main__':
    t = Transmission()
    x, y = t.getData(10)

