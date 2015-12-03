import dataset;
import numpy as np
import scipy.io;
import matplotlib.cm as cm
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import networkx as nx
import scipy.stats as ss

#z = scipy.io.loadmat('tmp.dat');
#ccfull = z['ccfull']
#sx,sy = ccfull.shape 
##x = np.arange(sx)
##delta = 0.025
##X, Y = np.meshgrid(x, x)
##Z1 = mlab.bivariate_normal(X, Y, 1.0, 1.0, 0.0, 0.0)
##Z2 = mlab.bivariate_normal(X, Y, 1.5, 0.5, 1, 1)
##Z = Z2-Z1  # difference of Gaussians
#
#im = plt.imshow(ccfull, interpolation='bilinear',
#                origin='lower', extent=[1,sx,1,sx])
#
#plt.savefig('corrcoeff.pdf')
#
#p = 1 - (ccfull*ccfull)
#
#im = plt.imshow(p, interpolation='bilinear', 
#                origin='lower', extent=[1,sx,1,sx])
#plt.savefig('corrcoef2.pdf')
#plt.show()

z = scipy.io.loadmat('tmp2');
mi = z['mi']
sx,sy = mi.shape 

#im = plt.imshow(mi, interpolation='bilinear',
#                origin='lower', extent=[1,sx,1,sx])

#plt.savefig('mi.pdf')
#plt.show()
print "MI Loaded"

mi = np.triu(mi)
a = mi.ravel();
print a
level = ss.scoreatpercentile(a,99.)
indexes = np.transpose(np.find(mi<level))
#mi[mi<level]=0

plt.savefig('mi2.pdf')
exit()
print level
print "MI prunned"

G = nx.Graph();
for r in indexes:
#for i in xrange(sx):
    #if i % 100 == 0:
    #    print i
    #for j in xrange(i):
    #    z = mi[i][j]
     #   if z > 0:
    G.add_edge(r[0], r[1], weight=-mi[r]);

print "Graph built"

T = nx.minimum_spanning_tree(G);

print T
print "Tree found"
