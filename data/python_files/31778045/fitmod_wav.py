import pywt
from fitmod import TsT2
from pylab import *
from scipy.fftpack import dct,idct
from scipy.linalg import block_diag,toeplitz
from ipdb import set_trace as st
from scipy.signal import convolve
from sklearn.linear_model import Lasso

def threshAtNNZ(c,nnz):
	inds = argsort(c**2)
	out = c.copy()
	out[inds[:-nnz]] = 0
	return out


nnz = lambda c : (c!=0).sum()
rel_err = lambda a,b : 100*norm(a-b)/norm(a)
nnz = lambda c : (hstack(c)!=0).sum()
threshcols = lambda c,nnz : (threshAtNNZ(c,nnz)!=0).nonzero()[0]

close('all')


# Setup Data
tes = array([15.0,39.0,63.0])

e1 = genfromtxt('e1_r1.txt');
e2 = genfromtxt('e2_r1.txt');
e3 = genfromtxt('e3_r1.txt');

nt = e1.shape[0]
ne = tes.shape[0]


y = vstack((e1,e2,e3))

mu = y.mean(axis=-1)

e1 -=e1.mean()
e2 -= e2.mean()
e3 -= e3.mean()

# Find the compressible basis
a =25
edat =[e1,e2,e3]
cdct = map(lambda x : dct(x,norm='ortho'),edat)
cols = unique(hstack(map(lambda x : threshcols(x,a),cdct)))


# Form the Multiecho Weight matrix
w1 = tes*mu
w2 = mu

W = vstack([w1,w2,ones(3)]).T
w3 =qr(W)[0][:,-1]

W = vstack([w1,w2,w3]).T

# Form the Multiecho DCT matrix
DCT = dct(eye(nt),norm='ortho')[cols,:]

MEDCT = []

nr = cols.shape[0]


G= []
B =[]
for rr in range(nr):
	tmp = DCT[rr,:]
	
	tmpr2 = hstack([tmp*w1[ee] for ee in range(ne)])
	tmps0 = hstack([tmp*w2[ee] for ee in range(ne)])

	G.append(tmpr2)
	B.append(tmps0)


G = vstack(G)
B = vstack(B)

X = vstack([G,B]).T


# Form the tcat and decompose
tcat = hstack([e1,e2,e3])
coef = lstsq(X,tcat)[0]

# Recompose
nr = cols.shape[0]
fitted  = dot(X,coef)

scoefs = [coef[:nr],coef[nr:2*nr]]

dr2c = coef[:nr]



dr2filt = dot(X[:nt,:nr],coef[:nr])
ds0filt = dot(X[:nt,nr:2*nr],coef[nr:2*nr])

figure(figsize=(20,6))
subplot(421)
plot(dr2filt)

subplot(422)
plot(ds0filt)


# No filtering

ts = TsT2(y,tes)

subplot(423)
plot(-ts.dr2s)

subplot(424)
plot(ts.ds0)


# Tikhinov Regularization
lam = 30000
GAM = hstack([dct(eye(nt),norm='ortho')]*2)*lam
GAM = hstack([eye(nt)]*2)*lam

# Make Wg


colwg = zeros(ne*nt)
colwb = zeros(ne*nt)

for ee in range(ne):
	colwg[ee*nt] = w1[ee] 
	colwb[ee*nt] = w2[ee]

Wg = toeplitz(colwg)[:,:nt]
Wb = toeplitz(colwb)[:,:nt]

W = hstack([Wg,Wb])
 
A = dot(W.T,W)+dot(GAM.T,GAM)
tmp = dot(W.T,tcat)
beta = solve(A,tmp)

dr2_tik,ds0_tik = split(beta,2)

subplot(425)
plot(dr2_tik)

subplot(426)
plot(ds0_tik)



### LASSO Idea

baselines  =  genfromtxt('lasso_base.1D')

demean = lambda x : x-x.mean()
normalize   = lambda x : x/x.std()

HRF = array([0,24.4876,98.3811,33.2969,4.09246,0.288748])
edat = vstack([e1,e2,e3])
tcat = edat.ravel()

o = TsT2(edat,tes)

nt = e1.shape[0]
ne = 3

w1 = o.X[:,0] ; w1 = w1/w1.std() 
w2 = o.X[:,1] ; w2 = w2/w2.std()


# Form the overcomplete dictionaries for the lambdas
# spin density is baselines + impulses
# r2 is HRfs + impulses

conv = lambda X :  apply_along_axis(lambda x : convolve(x,HRF)[1:nt+1],1,X)



PHI_G = hstack([conv(dct(eye(nt),norm='ortho')),baselines ])
PHI_B = hstack([conv(dct(eye(nt),norm='ortho')), baselines ])

# Form the Design matrix
Xg = []
Xb = []
for ee in range(ne):
	Xg.append(PHI_G*w2[ee])
	Xb.append(PHI_B*w1[ee])


Xg = vstack(Xg)
ng = Xg.shape[1]

Xb = vstack(Xb)
nb = Xb.shape[1]

X = hstack([Xg,Xb])

clf = Lasso(alpha=2)
clf.fit(X,tcat)

dr2c = clf.coef_[:ng]
ds0c = clf.coef_[ng:]

dr2  = dot(PHI_G,dr2c)	
ds0  = dot(PHI_B,ds0c)	

fitt = dot(X,clf.coef_)

subplot(427)
plot(dr2)

subplot(428)
plot(ds0)


lam = 10000
GAM = zeros([nb+ng,ng+nb])
GAM[ng:,ng:] = eye(ng)
GAM *=lam

A = dot(X.T,X)+dot(GAM.T,GAM)
tmp = dot(X.T,tcat)
beta = solve(A,tmp)

dr2 = dot(PHI_G,beta[:ng])
ds0 = dot(PHI_B,beta[ng:])

figure()
subplot(211)
plot(dr2)

subplot(212)
plot(-ds0)

# DCT Compression stuff commented out -NB 6/1/2012
# c2dct = dct(e2,norm='ortho')
# c2filt = threshAtNNZ(c2dct,a)

# e2filt = idct(c2filt,norm='ortho')

# figure()
# plot(e2filt)
# plot(e2)

# title ('dct ; NNZ = %d'%nnz(c2filt))
# print " Error = %2.2f "% rel_err(e2,e2filt)





# Wavelet stuff commnented out Friday 6/1/2012 - NB

# # wvlet = pywt.Wavelet('sym16')
# wvlet = pywt.Wavelet('db1')
# mode = 'sym'

# c1 = pywt.wavedec(e1,wvlet,mode=mode)
# c2 = pywt.wavedec(e2,wvlet,mode=mode)
# c3 = pywt.wavedec(e3,wvlet,mode=mode)

# thresh = lambda c,val : [ pywt.thresholding.soft(cc,val) for cc in c]


# def wthreshAtNNZ(c,nnz):
# 	val =sort(hstack(c))[-nnz]
# 	return thresh(c,val)

# c1thresh = wthreshAtNNZ(c1,a)
# c2thresh = wthreshAtNNZ(c2,a)
# c3thresh = wthreshAtNNZ(c3,a)

# e1filt = pywt.waverec(c1thresh,wvlet,mode=mode)
# e2filt = pywt.waverec(c2thresh,wvlet,mode=mode)
# e3filt = pywt.waverec(c3thresh,wvlet,mode=mode)

# print " Error = %2.2f "% rel_err(e2,e2filt)
# figure()
# plot(e2filt)
# plot(e2)
# title ('wave ; NNZ = %d'%nnz(c2thresh))

show()