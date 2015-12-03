import numpy as np
from scipy import interpolate
from scipy.integrate import quadrature
from scipy.special import gammainc
import glob
import re
import sqlite3
from pylab import *  #Remove later. Only for debugging

class model:

    def __init__(self, age, met, res=1000,n=10000,wd=False):

        isofile = self.FindIso(age,met)
        self.iso = np.loadtxt(isofile)
        if wd==False:
            self.iso = self.iso[(self.iso[:,13] == 0.0),]
        self.res = res
        self.n = n
    
    def findiso (self, age, met, group='padova', filterset='sdss'):
        """ 
        Find the corresponding isochrone for a given age and metallicity
        """        

        _ISOCDIR=os.path.join(os.path.dirname(os.path.realpath(__file__)),'data')

        table_name = group+'_'+filterset

        connection=sqlite3.connect(_ISOCDIR+'isoc.sqlite')
        cursor=connection.cursor()

        cursor.execute('SELECT TOP 1 Z_met, lage FROM '+table_name+' ORDER BY ABS(Z_met - '+str(met)+')')
        n_Z = cursor.fetchall()

        cursor.execute('SELECT TOP 1 Z_met, lage FROM '+table_name+' ORDER BY ABS(lage - '+str(age)+')')
        n_age = cursor.fetchall()

        if float(n_Z) != met or float(n_age) != age:
            print "Model with Z = "+str(met)+" and log(age/yr) = "+str(age)+" not found."
            print "Using Z = "+str(n_Z)+" and log(age/yr) = "+str(n_age)+" not found."
            age = str(n_age)
            met = str(n_z)

        cursor.execute('SELECT m_ini, m_act, u, g, r, i, z, J, H, Ks FROM '+table_name+' WHERE lage = '+age+' AND z_met = '+met)
        self.isocrone = cursor.fetchall()

        return age, met, self.isocrone

    def __interpolate__(self, iso, cols=[8,9,10,11,12]):
        """
        This method can be generalized to interpolate any quantity given in the 
        isochrone table. 
        """
        res = self.res
        m = {}
        z = iso[:,1]
        for idx in cols:
            m[idx] = interpolate.interp1d(z, iso[:,idx], bounds_error=False)

        return m

    def __mkmf__(self, mfpars=[0.15,-2.0,2.5], mlim=None):
        """
        Returns the mass function (MF), integral of the mass function (IMF) and the probability
        distribution function (PDF). 
        """

        iso = self.iso
        res = self.res
        if mlim == None:
            mmass, Mmass = np.min(iso[:,1]), np.max(iso[:,1])
        else:
            mmass, Mmass = mlim[0], mlim[1]
        mc,a,b = mfpars[:]
        mf = lambda x: ((x**a)*(1 - np.exp(-(x/mc)*b)))
        imf = lambda x: (x**a*(b*x*((b*x)/mc)**a + (1 + a)*mc*gammainc(1 + a, (b*x)/mc)))/((1 + a)*b*((b*x)/mc)**a)
        pdf = lambda x,y: imf(x) - imf(y)
        return pdf,mmass,Mmass

    def find_nearest(self, array, value):
        idx = (np.abs(array-value)).argmin()
        return idx

    def populate(self, n=1000):
        """
        Populate a given PDF. There MUST be a better way of doing this. Look into
        statistics books.
        """
        pdf, m, M = self.__mkmf__()
        p = self.__interpolate__(self.iso)
        bs = (M-m)/self.res
        scolor = smag = smass = N = np.zeros((n)) 
        na = 0
        out = np.empty((n,6))
        while na < n:
            rmass = m + (M-m)*np.random.rand()                # randomly generated masses
            mbin = int((rmass - m)/bs)                        # mass bin (starting from zero) 
            if N[mbin] < pdf(m + (mbin+1)*bs, m + (mbin)*bs)*n:
                x = [p[j] for j in sorted(p)]
                x = [func(rmass) for func in x]
                out[na,0] = rmass
                out[na,1:] = x
                N[mbin] = N[mbin]+1
                na = na + 1
        self.out = out
        return self.out

    def addbin(self, fbin=1.0):
        print self.out[0]


if __name__ == "__main__":
        import gencmd

        mymodel = model(7.0, 0.019)
        x = mymodel.populate(n=10000)
        mymodel.addbin() # does nothing for now
        np.savetxt('teste',x,fmt='%.6f')

# Design should go as follows
# x.addbin(fbin=??)
# x.adderr(coefs)
# plot(x[:,0],x[:,1],'k.',ms=1)

# 2. How to add unresolved binnaries without a bunch of loops
