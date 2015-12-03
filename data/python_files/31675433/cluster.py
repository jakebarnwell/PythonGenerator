import nibabel as nib
import scipy as sc
from scipy.spatial.distance import *
import numpy as nn
from scipy.cluster.hierarchy import dendrogram
from munkres import Munkres
from Pycluster import *
import time,re
import sys



def cordist(x,y):
    return np.inner(x,y)/np.std(x)/np.std(y)


def fmask(mask,data):

    #Initializations
    nx,ny,nz,nt  = data.shape
    nnz  = mask.sum()


    print "Flattening Array"
    flat = data.reshape((nx*ny*nz,nt))
    maskf = mask.flatten()


    print "Applying Mask"
    mdata = flat.compress(maskf,axis=0)

    return mdata
    

def cluster_data(data,k):
    classvec , error, nfound = kcluster(data,transpose=0,nclusters=k,dist='c',npass=100)
    return classvec +1

def uncompress(data,mask):
    nf = data.shape
    #nt = 1
    maskf = mask.flatten()
    N = maskf.shape[0]
    
    out = nn.zeros((N))
    #for i in range(nt):
    out[maskf.nonzero()[0]] = data
    
    return out
    
def hCluster(imfile,m,outfile=None):
    print image1, m
    if isinstance(image1,str):
        m = nib.load(m)
        image1 = nib.load(image1)

    head = image1.get_header()
    aff = image1.get_affine()
    fname = image1.file_map['image'].filename 
    fname = fname.split('/')[-1]
    prefix  = re.search('(\w*)_',fname).group(1) 
    # load the image data
    md = m.get_data().flatten()
    i1d = image1.get_data()

    nx,ny,nz,nt = i1d.shape

    #mask the images
    i1dm = fmask(md,i1d) 
    
    #compute linkage
    Z = hclust.linkage(i1dm,method='ward',metric='euclidean')
    

def cluster(image1,m,k=7):
    print image1, m
    if isinstance(image1,str):
        m = nib.load(m)
        image1 = nib.load(image1)

    head = image1.get_header()
    aff = image1.get_affine()
    fname = image1.file_map['image'].filename 
    fname = fname.split('/')[-1]
    prefix  = re.search('(\w*)_',fname).group(1) 
    # load the image data
    md = m.get_data().flatten()
    i1d = image1.get_data()

    nx,ny,nz,nt = i1d.shape

    #mask the images
    i1dm = fmask(md,i1d) 
    
    #cluster
    class1 = cluster_data(i1dm,k)
    
    #write brik
    tmp = uncompress(class1,md)
    tmp = tmp.reshape((nx,ny,nz))
    imout = nib.Nifti1Image(tmp, aff, header=head)
    imout.to_filename("%s_clust_%0.2d.nii.gz"%(prefix,k))
    return tmp

def compute_xor(bd,od,nk):

    xor = nn.zeros((nk,nk))
    for i in range (nk):
        for j in range(nk):
            num = float(nn.logical_xor((bd==i) , (od==j)).sum())
            xor[i,j]= num
    return xor
def compute_err(bd,od,nk):

    xor = nn.zeros((nk,nk))
    for i in range (nk):
        for j in range(nk):
            tmp1 = float(nn.logical_and((bd==i) , (od==j)).sum())
            tmp2 = float((od==j).sum())
            xor[i,j]= tmp2-tmp1
    return xor
    
def colormatch(bname,oname,mname=None,outfile=None):
    """
    Matches Clusters
    """
    #load images
    if isinstance(bname,str):
        base = nib.load(bname)
        orig = nib.load(oname)
        
        bd = base.get_data()
        od = orig.get_data()
        head = base.get_header()
        aff = base.get_affine()

    elif isinstance(bname,nib.nifti1.Nifti1Image):
        head = base.get_header()
        aff = base.get_affine()
        
        bd = base.get_data()
        od = orig.get_data()
    else:
        bd = bname
        od = oname

    size = bd.shape
    denom = float((bd!=0).sum())
    out = nn.zeros((size))
    nk = int(bd.max())+1
    osizes = nn.zeros(nk)


    #rows is base, cols are orig
    bsizes = nn.zeros(nk)
    #cost  = compute_xor(bd,od,nk)
    cost  = compute_err(bd,od,nk)
    costs = cost.copy()
    m = Munkres()
    indexes = m.compute(cost)
    total = 0
    for row,col in indexes:
        inds  = (od == col).nonzero()
        out[inds] = row
        total +=costs[row,col]
    #write image
    if outfile is not None:
        outimage = nib.Nifti1Image(out,aff,header=head)
        outimage.to_filename(outfile)

    return (indexes,total/denom)

    
def loadFromFilename(f1):
 #load images
    if isinstance(f1,str):
        i1 = nib.load(f1)

    #head = i1.get_header()
    #aff = i1.get_affine()
    
    i1d =i1.get_data()

    return i1d

def hammingDist(i1d,i2d):
    
    num = (i1d==i2d).sum()
    denom = (i1d==0).sum()

    return float(num)/float(denom)


def loadImages(ims):
    out = {'mask':None,'base':None,'orig':None}
    for imi in ims:
        eval("%s = nib.load(%s)"%(imi,ims[imi]))
        out[imi] = im
    return out
        
 
def hclust(data,classvec=None):
    #only ward method, using 1-correlation
    """
    Use scipy's def of linkage matrix:
        Z = [label1, label2, cost, size of new cluster]
        labels are from 0 to (N-1) (number of initial clusters)
        new clusters are given label 1+(number of clusters-1)
    """
    n,t = data.shape
    classvec = classvec-classvec.min()
    N = classvec.max()+1
    N = int(N)
    Z = nn.zeros((N-1,4))
    
    stds = data.std(axis=1)
    ms = data.mean(axis=1) 
    
    znorm = nn.zeros((n,t))

    for i in range(n):
        znorm[i,:] = (data[i,:]-ms[i])/stds[i]

    #init dist matrix
    Y = squareform(pdist(znorm))
    for i in range(N):
        Y[i,i] = 1000000000

    clustlabs = range(N)        
    currentlabel = N-1

    #currentlabel =
    for k in range(N-1):
        print "%f%% Percent Done"%(float(k)/(N-1))
        mincost=10000000000
        currentlabel +=1
        #currentlabel -= 1
        #find cost minimizing agglomeration     
        for i in range(len(clustlabs)):
            for j in range(i):
                labi = clustlabs[i]
                labj = clustlabs[j]
                centi = znorm[classvec==labi,:].mean(axis=0)
                centj = znorm[classvec==labj,:].mean(axis=0)
                
                ni = (classvec==labi).sum()
                nj = (classvec==labj).sum()
                
                newcent = (ni*centi+nj*centj)/(ni+nj)
                #SS1 = newcent**2*(ni+nj)
                #SS2 = centi**2*ni +centj**2*nj
                #wardcost = SS1.sum() -SS2.sum()
                #euclidean dist between centroids
                #C = clusterdistance(znorm, index1=iind, index2=jind, method='a', dist='e')
                C = euclidean(centi,centj)
                wardcost =  C*nn.sqrt(2*ni*nj/(ni+nj))

                Y[i,j] = wardcost
                Y[j,i] = wardcost
                #if wardcost < mincost:
                    #lab1 = clustlabs[i]
                    #lab2 = clustlabs[j]
                    #mincost= wardcost
        i,j = nn.unravel_index(Y.argmin(),dims=(N,N))  
        lab1 = clustlabs[i]
        lab2 = clustlabs[j]

        Z[k,0] = lab1
        Z[k,1] = lab2
        Z[k,2]  = Y[i,j]
        Z[k,3]  = ni+nj
        classvec[nn.logical_or(classvec==lab1,classvec==lab2)] = currentlabel
        clustlabs.remove(lab1)
        clustlabs.remove(lab2)
        clustlabs.append(currentlabel)
    
    return Z,znorm


def silhouette(X, cIND):
    """
    Computes the silhouette score for each instance of a clustered dataset,
    which is defined as:
        s(i) = (b(i)-a(i)) / max{a(i),b(i)}
    with:
        -1 <= s(i) <= 1

    Args:
        X    : A M-by-N array of M observations in N dimensions
        cIDX : array of len M containing cluster indices (starting from zero)

    Returns:
        s    : silhouette value of each observation
    """
    def silval(x, Y,cIND):
        nk  = int(cIND.max())
        thisk = x[0]
        x = x[1:]
        D = 1-np.inner(Y,x)
        st()
        bs =np.array([ D.compress(cIND==k).mean()  for k in range(1,nk+1)])
        st()
   
     
    N = X.shape[0]              # number of instances
    k = len(np.unique(cl))-1    # number of clusters

   
    def znorm(x):
        return (x-x.mean())/np.linalg.norm(x)

    Xnorm = np.apply_along_axis(znorm,1,X)
    
    
    np.apply_along_axis(silval,1,np.hstack((cIND,Xnorm)),Xnorm,cIND)
    # compute a,b,s for each instance
    a = np.zeros(N)
    b = np.zeros(N)
    for i in range(N):
        print "%f %% Done"%(float(i)/N)
        # instances in same cluster other than instance itself
        a[i] = np.mean( [D[i][ind] for ind in kIndices[cIDX[i]] if ind!=i] )
        # instances in other clusters, one cluster at a time
        b[i] = np.min( [np.mean(D[i][ind]) 
                        for k,ind in enumerate(kIndices) if cIDX[i]!=k] )
    s = (b-a)/np.maximum(a,b)

    return s

    
if __name__ == '__main__':
    im1,im2,pref = sys.argv[1:4] 
    colormatch(im1,im2,outfile=pref)



