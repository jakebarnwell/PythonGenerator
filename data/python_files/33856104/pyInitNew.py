import numpy as np
import struct as st
import os,sys,progressbar,pylab
import matplotlib as mpl
from matplotlib import pyplot as plt
from scipy import spatial as sp
from scipy import special

### Disc related classes and functions...

class Disc(object):
  """Particle data is stored as a big table, called _particles where unknown or missing data is np.nan.
  A type column gives the type of each particle, with 0=normal, 1=star."""
  _coreProperties=dict(type=0)
  def __init__(self):
    self._particles=np.tile(np.nan,(0,len(Disc._coreProperties)))
    self._particleProps=Disc._coreProperties
    #None is no restriction, otherwise it should be a list of tuples of the
    #format (type,subset).  Subset should either be a list of indicies for
    #the restricted set, or None for just a type restriction.
    #self._subset=[(0,[1,2,5])] would get the first, second and fifth
    #particles of type 0, [(0,None)] would get all the type 0 particles
    self._subset=None

  def __getattr__(self,attr):
    """If the disc instance explicitly has an attribute, return that.
    Likewise if it starts with an _.
    Otherwise, try and get the column from the data table."""
    if attr.startswith("_"):
      if hasattr(self,attr):
        return object.__getattr__(self,attr)
    elif attr in self._particleProps:
      #Get the whole thing
      tmp=self._particles[:,self._particleProps[attr]]
      #Get the type we want, and the subset we want
      if self._subset is not None:
        if len(self._subset)==1:
          sub=self._subset[0]
          if sub[1] is None:
            return tmp[self._particles[:,self._particleProps['type']]==sub[0]]
          return tmp[self._particles[:,self._particleProps['type']]==sub[0]][sub[1]]
        ret=[]
        type=self._particles[:,self._particleProps['type']]
        for sub in self._subset:
          if sub[1] is None:
            ret.append(tmp[type==sub[0]])
          else:
            ret.append(tmp[type==sub[0]][sub[1]])
        return ret
      return tmp
    raise AttributeError,attr

  def __setattr__(self,attr,val):
    """Constants are prefixed with an underscore."""
    if attr.startswith("_"):
      object.__setattr__(self,attr,val)
      return
    indx=self.subset2indices()
    if len(val)==self.N:
      indx=np.arange(self.N)
    elif len(indx)!=len(val):
      raise ValueError("Wrong length of setting values")
    #Do we need to add a new data column first?
    if not attr in self._particleProps:
      self._particles=np.append(self._particles,np.tile(np.nan,(self.N,1)),1)
      self._particleProps[attr]=self._particles.shape[1]-1
    #Update the values in the appropriate places...
    self._particles[indx,self._particleProps[attr]]=val

  def hasCol(self,name):
    return name %in% self._particleProps

  def addParticles(self,typeVector):
    """Add a new set of particles..."""
    tmp=self.type
    self._particles=np.append(self._particles,np.tile(np.nan,(len(typeVector),len(self._particleProps))),0)
    self.type=np.append(tmp,typeVector)

  def fetch(self,var):
    """For a single string, it's completely equivalent to getattr(self,var), but for a list of variables
    will return a lovely dataframe with the columns asked for."""
    if isinstance(var,string):
      var=[var]
    else:
      cols=[]
      for v in var:
        if v in self._particleProps:
	  cols.append(self._particleProps[v])
      if not cols:
        raise ValueError
      tmp=self._particles[:,cols]
      return tmp[subset2indicies(),]

  def subsetTmp(s,subset=[(0,None)]):
    """When you need to have a temporary subset but not trash your "good" one.
    Turn the main subset back on, with a call to subsetrestore()"""
    #Already got the temp one enabled, so don't overwrite our previous "good"
    if getattr(s,"__subset",None) is None:
      s.__subset=s._subset
      s._subset=subset

  def subsetRestore(s):
    """Restore the "good" subset."""
    if getattr(s,"__subset",None) is not None:
      s._subset=s.__subset
      s.__subset=None

  def subset2indices(self):
    """Convert the subset list of tuples to a set of indices in the particle
    table."""
    if self._subset is None:
      return np.arange(self.N)
    type=self._particles[:,self._particleProps['type']]
    ret=np.array(0)
    for sub in self._subset:
      tmp=np.where((type==sub[0]))[0]
      if sub[1] is not None:
        ret=np.append(ret,tmp[sub[1]])
      else:
        ret=np.append(ret,tmp)
    return ret[1:]

  def indices2subset(s,indx):
    """Converts indicies on the _particles table to a subset object."""
    types=np.unique(s.type[indx])
    subset=[]
    for t in types:
      s.subsetTmp([(t,None)])
      #Needed as numpy arrays don't have an index method
      typeInd=list(s.subset2indices())
      subset.append((type,[typeInd.index(a) for a in indx if a in typeInd]))
    s.subsetRestore()
    return subset

  def subset(s,fields=None,N=5000,force=True):
    s._subset=None
    if fields is not None:
      if not isintasnce(fields,list):
        fields=[fields]
      subset=np.where(s.type==0)
      for field in fields:
        subset=subset[np.where((np.isfinite(s.fetch(field)[subset])))[0]]
      s._subset=s.indicies2subset(subset)
    elif N<=0 or n>=s.n:
      print "Invalid N, subset unchanged."
    else:
      rand=np.random.permutation(np.sum(s.type==0))
      s._subset=[(0,rand[:min(len(rand),N)])]

  @property
  def N(self):
    return self._particles.shape[0]

  @property
  def N(s):
    return len(s.subset2indices())

  def init_tree(s,force=False):
    s.subsetTmp()
    if force or not hasattr(s,"_tree2"):
      s._tree2=sp.KDTree(s.fetch(['x','y']))
    if force or not hasattr(s,"_tree3"):
      s._tree3=sp.KDTree(s.fetch(['x','y','z']))
    s.subsetRestore()

  def calcCommon(s):
    s.subsetTmp(None)
    #Calculate some commonly used quantities
    s.R=np.sqrt(s.x**2+s.y**2)
    s.r=np.sqrt(s.x**2+s.y**2+s.z**2)
    s.theta=np.artcant2(s.y,s.x)
    s._M=np.max(s.m)
    s.subsetTmp()
    s._m=np.median(s.m)
    s.subsetRestore()
  
  def fromFolder(s,folder):
    os.chdir(folder)
    pos=np.genfromtxt("Position.txt")
    grav=np.genfromtxt("Acceleration.txt")
    pot=np.genfromtxt("GravPotential.txt")
    mass=np.genfromtxt("Masses.txt")
    smooth=np.genfromtxt("Smoothing.txt")
    rho=np.genfromtxt("Density.txt")
    energy=np.genfromtxt("Energy.txt")
    #Adjust the coordinates so the star is at the centre...
    strarg=s.mass.argmax()
    strpos=s.pos[strarg,]
    pos=pos-strpos
    typeVec=np.zeros(pos.shape[0])
    typeVec[strarg]=1
    s.addParticles(typeVec)
    s.subsetTmp()
    #Now the ones that don't have a star...
    s.SPHrho=rho
    s.u=energy
    s.h=smooth
    #Add all the properties that have the star...
    s.subsetTmp(None)
    s.x=pos[:,0]
    s.y=pos[:,1]
    s.z=pos[:,2]
    s.gx=grav[:,0]
    s.gy=grav[:,1]
    s.gz=grav[:,2]
    s.pot=pot
    s.m=mass
    s.calcCommon()

  def fromFile(s,file,format="x y z m rho iphase"):
    """Lodato format is x,y,z,m,rho,iphase"""
    format=format.split()
    if 'x' not in format or 'y' not in format or 'z' not in format:
        raise ValueError("Need at least the positions...")
    fdat=np.genfromtxt(file)
    #s.data=np.array(np.repeat(np.nan,s.fdat.shape[0]-1),dtype=s.dt)
    x=fdat[:,format.index('x')]
    y=fdat[:,format.index('y')]
    z=fdat[:,format.index('z')]
    m=fdat[:,format.index('m')]
    #Move the star
    strarg=m.argmax()
    star=np.array([x[strarg],y[strarg],z[strarg]])
    #Add the particles...
    typeVec=np.zeros(len(x))
    typeVec[strarg]=1
    s.addParticles(typeVec)
    #All should contain the star...
    s.subsetTmp(None)
    s.x=x-x[strarg]
    s.y=y-y[strarg]
    s.z=z-z[strarg]
    s.m=m
    s.calcCommon()

  def fromBinaryFile(s,file,format='gx gy gz',type='f',matchSubset=None):
    """type should be a valid python struct variable type, e.g. f= 4-byte
    float.  Assumes the (idiotic) fortran binary format and that every
    variable has been written in blocks of equal size.  Will add to the particles at position matchIndx"""
    bsize=st.calcsize(type)
    format=format.split()
    f=open(file,'rb')
    fdat=f.read()
    regionend=-4
    i=0
    while regionend+8<len(fdat) and i<len(format):
      size=st.unpack('i',fdat[(regionend+4):(regionend+8)])[0]/bsize
      regionstart=regionend+8
      regionend=regionstart+size*bsize
      #s.addCol(format[i])
      tmp=np.array(st.unpack(type*size,fdat[regionstart:regionend]))
      #add this to the selected rows...
      s.subsetTmp(matchSubset)
      setattr(s,format[i],tmp)
      i=i+1
    s.subsetRestore()

  def calcBands(s,data,boundaries=[.6,1.,2.]):
    """Assigns a factor to the table depending on which side of the
    bondaries the data specified falls on.  Can be used to colour data
    later when plotting..."""
    if not isinstance(boundaries,list):
      boundaries=[boundaries]
    s._bandBoundaries=boundaries
    if len(boundaries)<1:
      raise
    tmp=np.zeros(len(data))
    tmp[np.where(data<boundaries[0])[0]]=0
    count=0
    for i,cut in enumerate(boundaries[1:]):
      count=count+1
      tmp[np.where((data>=boundaries[i]) & (data<cut))] = count
    tmp[np.where((data>=boundaries[-1]))] = count+1
    s.bands=tmp

  @property
  def nBands(self):
    """The number of bands."""
    self.subsetTmp(None)
    if self.hasCol('bands'):
      count=int(np.nanmax(self.bands)+1)
      self.subsetRestore()
      return count
    return 0

  def plot(s, x, y, newBands=False, useBands=True, hline=0, **kw):
    """General purpose plotting function to be used by other things. We can
    calculate bands or display pre-calculated banding.  If boundaries is
    passed to this function, we pass it on to calcBands.
    """
    ret=[]
    #Get from strings...
    if isinstance(x,str):
      if 'xlab' not in kw:
        kw['xlab']=x
      x=getattr(s,x)
    if isinstance(y,str):
      if 'ylab' not in kw:
        kw['ylab']=y
      y=getattr(s,y)
    if newBands:
      if 'boundaries' in kw:
        s.calcBands(y,boundaries=kw.pop('boundaries'))
      else:
        s.calcBands(y)
    #Don't want to be passing a useless kw arg...
    elif 'boundaries' in kw:
      tmp=kw.pop('boundaries')
    if useBands and s.nbands:
      tmp=plot(x,y, pch=0,hline=hline,**kw)
      ret.append(tmp[0])
      for i in xrange(s.nBands):
        o=np.where(s.data['bands']==i)
        tmp=plot(x[o],y[o], pch=i+1,add=True)
        ret.append(tmp)
    else:
      tmp=plot(x,y, hline=hline, **kw)
      ret.append(tmp)
    return ret


    def relerrorScatter(s,x,y1,y2=None,boundaries=[10.,50.,100.,200.],
            legend=True, loc="upper right", **kw):
        """ Calculates the relative error and then passes it to plot"""
        if isinstance(x,str):
            x=s.data[x]
        if isinstance(y1,str):
            y1=s.data[y1]
        if isinstance(y2,str):
            y2=s.data[y2]
        x=s.fetch(x)
        y1=s.fetch(y1)
        if y2 is not None:
            y2=s.fetch(y2)
            y=100.*(np.abs(y2-y1)/np.abs(y1))
        else:
            y=y1
        ret=s.plot(x,y,boundaries=boundaries,**kw)
        if legend and 'bands' in s.data.dtype.names and len(s.bandBoundaries)+1 == len(ret[-1]):
            #Build the labels...
            labs=["< %s %%" % str(s.bandBoundaries[0])]
            for i in xrange(1,len(s.bandBoundaries)):
                labs.append("%s %% - %s %%" %
                    (str(s.bandBoundaries[i-1]),str(s.bandBoundaries[i])))
            labs.append("> %s %%" % str(s.bandBoundaries[-1]))
            plt.legend(ret[-1],labs,loc=loc)
        return ret

    def surfacePlot(s,x,y,z,**kw):
        """Given a set of coordinates {(x,y,z)}, grids up x and y and converts
        the z values into a colour scaling."""
        if isinstance(x,str):
            x=s.data[x]
        if isinstance(y,str):
            y=s.data[y]
        if isinstance(z,str):
            z=s.data[z]
        x=s.fetch(x)
        y=s.fetch(y)
        z=s.fetch(z)
        heatMap(x,y,z,**kw)
        
    def findIndex(self,x,y,z,toll=1e-8):
        """Given x, y and z, return the indecies in data that match to within
        toll.  If multiple indicies match, -1 is returned"""
        if len(x)!=len(y) or len(y)!=len(z) or len(x)!=len(z):
            raise
        index=np.repeat(-1,len(x))
        widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
        pbar = progressbar.ProgressBar(widgets=widgets, maxval=len(x)).start()
        for i in xrange(len(x)):
            tmp=np.where( (np.abs(self.data['x']-x[i])<toll) &
                    (np.abs(self.data['y']-y[i])<toll) &
                    (np.abs(self.data['z']-z[i])<toll))[0]
            if len(tmp)!=1:
                continue
            index[i]=tmp[0]
            pbar.update(i)
        return index

    def calcsumgz(self,recalculate=False):
        """Calculates direct sum gravity and inserts it into the table"""
        s=self
        x=s.data['x']
        y=s.data['y']
        z=s.data['z']
        ptx=self.fetch(x)
        pty=self.fetch(y)
        ptz=self.fetch(z)
        #If we've calculated the values previously, no need to redo them...
        index=self.fetch(np.arange(self.n))
        s.addCol('sumgz')
        if not recalculate:
            o=np.where(np.isnan(self.data['sumgz'][index]))
            ptx=ptx[o]
            pty=pty[o]
            ptz=ptz[o]
            index=index[o]
        widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
        pbar = progressbar.ProgressBar(widgets=widgets, maxval=len(index)).start()
        for count,i in enumerate(index):
            rtmp=np.sqrt((ptx[count]-s.data['x'])**2+(pty[count]-s.data['y'])**2+(ptz[count]-s.data['z'])**2)
            rtmp[rtmp==0]=np.Infinity
            s.data['sumgz'][i]=np.sum((s.G*s.data['m']*(s.data['z']-ptz[count]))/rtmp**3)
            pbar.update(count)

    def calcmidplaneCD(s,tgtN=50,maxR=5.):
        s.init_tree()
        s.addCol("cdMid")
        widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
        pbar = progressbar.ProgressBar(widgets=widgets, maxval=s.N).start()
        for count,i in enumerate(s.subset):
            pbar.update(count)
            pts=np.array(s.tree2.query_ball_point(list(s.data[['x','y']][i]),maxR))
            #Subset to desired range...
            o=np.where(np.abs(s.data['z'][pts])<=np.abs(s.data['z'][i]))[0]
            pts=pts[o]
            #Calculate the distances...
            dist=np.sqrt((s.data['x'][pts]-s.data['x'][i])**2 +
                    (s.data['y'][pts]-s.data['y'][i])**2)
            pts=pts[dist.argsort()]
            dist=dist[dist.argsort()]
            #Subset if possible
            stop=tgtN if len(pts)>tgtN else len(pts)
            if stop<1:
                s.data['cdMid'][i]=0.
                continue
            h=dist[stop-1]
            s.data['cdMid'][i]=np.sum(s.data['m'][pts[:stop]])/(2.*math.pi*h**2)

    def calcsurCD(s,tgtN=50,maxR=5.):
        s.init_tree()
        s.addCol("cdSur")
        widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
        pbar = progressbar.ProgressBar(widgets=widgets, maxval=s.N).start()
        for count,i in enumerate(s.subset):
            pbar.update(count)
            pts=np.array(s.tree2.query_ball_point(list(s.data[['x','y']][i]),maxR))
            #Subset to desired range...
            o=np.where(np.abs(s.data['z'][pts])>=np.abs(s.data['z'][i]))[0]
            pts=pts[o]
            #Calculate the distances...
            dist=np.sqrt((s.data['x'][pts]-s.data['x'][i])**2 +
                    (s.data['y'][pts]-s.data['y'][i])**2)
            pts=pts[dist.argsort()]
            dist=dist[dist.argsort()]
            #Subset if possible
            stop=tgtN if len(pts)>tgtN else len(pts)
            if stop<1:
                s.data['cdSur'][i]=0.
                continue
            h=dist[stop-1]
            s.data['cdSur'][i]=np.sum(s.data['m'][pts[:stop]])/(2.*math.pi*h**2)

    def calcPotential(s):
        """Calculate the potential energy for a subset of particles..."""
        s.addCol("Pot")
        widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
        pbar = progressbar.ProgressBar(widgets=widgets, maxval=s.N).start()
        x=s.fetch(s.data['x'])
        y=s.fetch(s.data['y'])
        z=s.fetch(s.data['z'])
        xall=s.data['x']
        yall=s.data['y']
        zall=s.data['z']
        pot=np.zeros(s.N)
        mass=np.median(s.data['m'])
        for i in xrange(s.N):
            pbar.update(i)
            tmp=np.sqrt((xall-x[i])**2+(yall-y[i])**2+(zall-z[i])**2)
            tmp[tmp==0]=np.inf
            pot[i]=-mass*s.G*np.sum(1./tmp)
        s.data["Pot"][s.subset]=pot


    def seedMap(s,subset=False,nn=50,subsetFrac=.1,maxR=5.):
        """Calculate the column density at a subset of particles.  If subset is
        set to true then we calculate it at the points specified in subset,
        otherwise a random set is chosen.  nn is the number of neighbours to
        use to calculate the surface density at each point and subsetFrac is
        the fraction of total particles to calculate it for."""
        s.init_tree()
        if subset and s.subset is not None:
            npts=s.N
            rr=s.subset
        else:
            npts=int(s.n*subsetFrac)
            rr=np.random.permutation(s.n)[:npts]
        s.addCol("cdTot")
        #Make some temporary lists to make calculation (a lot) faster
        ghost=np.zeros((npts,3))
        ghost[:,0]=s.data['x'][rr]
        ghost[:,1]=s.data['y'][rr]
        mm=s.data['m']
        widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
        pbar = progressbar.ProgressBar(widgets=widgets, maxval=npts).start()
        for i in xrange(npts):
            pbar.update(i)
            pts=s.tree2.query(ghost[i,:2],nn)
            ghost[i,2]=np.sum(mm[pts[1]]/(2.*math.pi*np.max(pts[0])**2))
        s.data['cdTot'][rr]=ghost[:,2]

    def interpolateMap(s,grid=False):
        """Interpolates the surface density to surface using either the grid or
        the 10% column calculation."""
        s.addCol("cdTotInt")
        #Create it if it hasn't been...
        if not grid and not "cdTot" in s.data.dtype.names:
            s.seedMap()
        if grid and not hasattr(s,"gridArray"):
            s.gridMap()
        #Now we have to interpolate the missing points...
        rr=s.subset
        if rr is None:
            rr=np.arange(s.n)
        #Again, far faster to use a different data structure...
        tmp=np.zeros((rr.shape[0],3))
        tmp[:,0]=s.data['x'][rr]
        tmp[:,1]=s.data['y'][rr]
        widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
        pbar = progressbar.ProgressBar(widgets=widgets, maxval=s.N).start()
        if grid:
            gtree=sp.KDTree(s.gridArray[:,:2])
            tt=s.gridArray[:,2]
        else:
            src=np.isfinite(s.data['cdTot'])
            gtree=sp.KDTree(np.column_stack((s.data['x'][src],s.data['y'][src])))
            tt=s.data['cdTot'][src]
        for i in xrange(rr.shape[0]):
            pbar.update(i)
            pts=gtree.query(tmp[i,:2],1)
            tmp[i,2]=tt[pts[1]]
        s.data['cdTotInt'][rr]=tmp[:,2]

    def gridMap(s,Rres=20,tres=10,log=True,minCount=10):
        if log:
            #Rspace=propspace(np.min(s.data['R']),np.max(s.data["R"]),Rres)
            Rspace=np.array(np.percentile(s.data["R"],
                list(np.linspace(0,100,Rres))))
        else:
            Rspace=np.linspace(np.min(s.data["R"]), np.max(s.data["R"]), Rres)
        tspace=np.linspace(np.min(s.data["theta"]),np.max(s.data['theta']),
                tres)
        grid,Redges,tedges=np.histogram2d(s.data["R"],s.data["theta"],[Rspace,tspace])
        area=np.outer((Redges[:-1]+np.diff(Redges))**2-Redges[:-1]**2,np.diff(tedges))
        mass=np.median(s.data['m'])
        counts=grid
        grid=(grid*mass)/area
        #Flatten the grid, because it'll be useful..
        Rcenter=Redges[:-1]+np.diff(Redges)/2.
        tcenter=tedges[:-1]+np.diff(tedges)/2.
        s.gridArray=np.zeros(((Rres-1)*(tres-1),4))
        Rflat=np.ndarray.flatten(np.outer(Rcenter,np.ones(tres-1)))
        tflat=np.ndarray.flatten(np.outer(np.ones(Rres-1),tcenter))
        s.gridArray[:,0]=Rflat*np.cos(tflat)
        s.gridArray[:,1]=Rflat*np.sin(tflat)
        s.gridArray[:,2]=np.ndarray.flatten(grid)
        s.gridArray[:,3]=np.ndarray.flatten(counts)
        #Throw away those that don't meet the threshold...
        s.gridArray=s.gridArray[np.ndarray.flatten(counts)>=minCount,]

    def calc2dh(s,x,y,npts=7):
        """Calculate 2d smoothing for points (x,y)"""
        s.init_tree()
        pts=s.tree2.query([x,y],npts)
        #return 4*np.max(s.smooth[pts[1]])
        return np.max(pts[0])
    
    def SPHCDold(s,x,y,maxiter=100,toll=1e-12):
        s.init_tree()
        eta=1.2
        m=np.median(s.mass)
        rho=m*((len(s.mass)-1)/(math.pi*(s.Rout**2-s.Rin**2)))
        def hfunc(rho):
            return eta*(m/rho)**.5
        def rhofunc(h):
            #Get the points
            num=len(s.tree2.query_ball_point([x,y],2.*h))
            pts=s.tree2.query([x,y],num)
            #Get q at each point
            q=pts[0]/h
            return np.sum(W(q,h,ndim=2))*m
        i=0
        err=100.
        while err>toll and i<maxiter:
            i=i+1
            h=hfunc(rho)
            tmp=rhofunc(h)
            err=rho-tmp
            rho=tmp
        #Now normalize
        num=len(s.tree2.query_ball_point([x,y],2.*h))
        pts=s.tree2.query([x,y],num)
        q=pts[0]/h
        sum=np.sum(W(q,h,ndim=2)/s.rho[pts[1]])*m
        return rho/sum
            

    def SPHCDold2(s,x,y):
        s.init_tree()
        from scipy.optimize import newton
        import scipy.optimize as op
        eta=1.2
        m=np.median(s.mass)
        def func(rho):
            rho=np.abs(rho)
            #Estimate h
            h=eta*np.sqrt(m/rho)
            #get the relevant points
            num=len(s.tree2.query_ball_point([x,y],2.*h))
            pts=s.tree2.query([x,y],num)
            #Get q at each of these points
            q=pts[0]/h
            #Calculate W at each of these points, estimate rho, return residual
            return rho - np.sum(W(q,h,ndim=2))*m
        def fprime(rho):
            rho=np.abs(rho)
            #Estimate h
            h=eta*np.sqrt(m/rho)
            #get the relevant points
            num=len(s.tree2.query_ball_point([x,y],h))
            pts=s.tree2.query([x,y],num)
            #Get q
            q=pts[0]/h
            #dWdh
            tmp=np.sum(dWdh(q,h)*.5*(h/rho))
            return 1-m*tmp
        #Estimate an intial guess at density
        rho=(m*(len(s.mass)-1))/(math.pi*(s.Rout**2-s.Rin**2))
        #return newton(func,rho,fprime)
        return op.fsolve(func,rho)[0]


    def SPHCD(s,x,y,nn=7):
        """SPH column density calculation for a point."""
        #Find those particles in the range
        dx=(x-s.data['x'])
        dy=(y-s.data['y'])
        dr=np.sqrt(dx**2+dy**2)
        #h=np.max(s.smooth)
        h=s.calc2dh(x,y,nn)
        m=np.median(s.mass)
        o=np.where(dr<h)[0]
        qxy=dr[o]/h
        #Now look up the integrals from the table and sum over all particles...
        out=np.zeros(len(qxy))
        out[qxy<=1.]=s.interpolateF(qxy[qxy<=1.])
        tot=np.sum(out)*((16*m)/(math.pi*h**2))
        return tot

    def buildDT(s):
        s.addCol("DTrho")
        from scipy.spatial import Delaunay
        tmp=np.zeros((s.n,2))
        tmp[:,0]=s.data['y']
        tmp[:,1]=s.data['x']
        d=Delaunay(tmp)
        tmp=np.zeros(s.n)
        m=np.median(s.mass)
        #For searching
        flat=d.vertices.flatten()
        widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
        pbar = progressbar.ProgressBar(widgets=widgets, maxval=s.n).start()
        #For each point, need to calculate the contiguous Voronoi cell...
        for i in xrange(s.n):
            pbar.update(i)
            pts=np.where(flat==i)[0]/3
            #Calculate the area of each, add it to total
            area=0.
            for pt in pts:
                nodes=d.points[d.vertices[pt]]
                a=nodes[0]
                b=nodes[1]
                c=nodes[2]
                area=area+np.abs((a[0]-c[0])*(b[1]-a[1])-(a[0]-b[0])*(c[1]-a[1]))/2.
            tmp[i]=(3.*m)/area
        s.data['DTrho']=tmp





        
            
    def buildTable(s,n=10000):
        from scipy import integrate
        lower=0.
        upper=1.
        def F(qxy):
            def curlyW(qz):
                q=(qxy**2.+qz**2.)**.5
                if q>=0 and q<.5:
                    return (1.-6.*q**2.+6.*q**3.)
                elif q>=.5 and q<=1.:
                    return (2.*(1.-q)**3.)
                else:
                    return 0.
        
            lim = (1-qxy**2)**.5
            return integrate.quad(curlyW,0,lim)[0]
        s.Ftable=np.zeros((n,2))
        s.Ftable[:,0]=np.linspace(lower,upper,n)
        widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
        pbar = progressbar.ProgressBar(widgets=widgets, maxval=n).start()
        for i in xrange(n):
            pbar.update(i)
            s.Ftable[i,1]=F(s.Ftable[i,0])
    
    def interpolateF(s,qxy):
        spacing=np.median(np.diff(s.Ftable[:,0]))
        return s.Ftable[np.intp(np.round(qxy/spacing))-1,1]






class AnalyticDisc(Disc):
    def MMwrite(self,file="/home/my304/data/Output/MMtmp_data.txt"):
        f=open(file,'w')
        s=self
        #The parameters must come first and there must be a multiple of 3
        params=[s.Hfact, max(abs(s.data['z'])), s.T0, s.plIndex, s.TIndex, s.Rout,
                s.Rin, s.Mstar, s.Mdisc, s.G, s.D]
        while len(params)%3:
            params.append(0.)
        tmp=[str(p) for p in params]
        f.write('\t'.join(tmp))
        f.write('\n')
        R=s.fetch(s.data['R'])
        t=s.fetch(s.data['theta'])
        z=s.fetch(s.data['z'])
        for i in xrange(s.N):
            f.write(str(R[i]) + '\t' + str(t[i]) + '\t' + str(z[i]) + '\n')
        f.close()
        s.MMsubset=s.subset

    def MMread(s,file="/home/my304/data/Output/MMtmp_processed.txt",subset=None):
        """We need to know which indexes to insert this information into the
        data object, one way is to use a supplied subset (s.MMsubest is saved
        by MMwrite).  If subset is None, we attempt to guess the index based on
        the positions given in the MM file."""
        s.MMdata=np.genfromtxt(file)
        s.addCol('Agznostar')
        s.addCol('MMapprox')
        if subset is not None:
            s.data['Agznostar'][subset]=s.MMdata[:,4]
        else:
            x=s.MMdata[:,0]*np.cos(s.MMdata[:,1])
            y=s.MMdata[:,0]*np.sin(s.MMdata[:,1])
            o=s.findIndex(x,y,s.MMdata[:,2])
            if np.any(o==-1):
                print "No indicies provided and failed to find match for %s points" % np.sum(o==-1)
                raise
            s.data['Agznostar'][o] = s.MMdata[:,4]
            s.data['MMapprox'][o] = s.MMdata[:,3]

    def describeDisc(self,Hfact=.002597943,T0=16.7,plIndex=-0.5,TIndex=0.,Rin=5.,Rout=100.,Mstar=1.,Mdisc=.1,G=887.2057):
        if not self.loaded:
            return
        self.Hfact=Hfact
        self.T0=T0
        self.plIndex=plIndex
        self.TIndex=TIndex
        self.Rin=Rin
        self.Rout=Rout
        self.Mstar=Mstar
        self.Mdisc=Mdisc
        self.G=G
        #We can infer some stuff if we have data...
        self.Mdisc=np.sum(self.data['m'])
        self.Rin=self.data['R'].min()
        self.Rout=self.data['R'].max()
        if plIndex==-2:
            self.D=np.log2(self.Rout/self.Rin)
        else:
            self.D=(1./(self.plIndex+2.))*(self.Rout**(self.plIndex+2)-self.Rin**(self.plIndex+2))
        self.addCol('AscaleH')
        self.data['AscaleH']=self.Hfact*np.sqrt(self.T0/(self.Mstar*(self.Rin**self.TIndex)))*self.data['R']**((self.TIndex+3.)/2.)
        self.addCol('Arho')
        self.data['Arho']=(self.Mdisc/(2.*math.pi*self.D))*(self.data['R']**self.plIndex)*(np.exp((-1.*self.data['z']**2)/(2.*self.data['AscaleH']**2))/np.sqrt(2.*math.pi*self.data['AscaleH']**2))
        self.addCol('AcdSur')
        self.data['AcdSur']=((self.Mdisc*self.data['R']**self.plIndex)/(4.*math.pi*self.D))*(1-special.erf(np.abs(self.data['z'])/np.sqrt(2.*self.data['AscaleH']**2)))
        self.addCol('AcdMid')
        self.data['AcdMid']=(self.data['R']**self.plIndex)*(self.Mdisc/(4.*math.pi*self.D))*(special.erf(np.abs(self.data['z'])/np.sqrt(2.*self.data['AscaleH']**2)))
        self.addCol('AcdTot')
        self.data['AcdTot']=(self.Mdisc/(4.*math.pi*self.D))*self.data['R']**self.plIndex
        self.addCol('Agzstar')
        self.data['Agzstar']=-1.*(self.G*self.Mstar*self.data['z'])/(self.data['r']**3)
        self.addCol('Agzapprox')
        self.data['Agzapprox']=-4.*math.pi*self.G*self.data['AcdMid']*np.sign(self.data['z'])
        self.addCol('gznostar')
        self.data['gznostar']=self.data['gz']-self.data['Agzstar']

#    def ctsH(self,R):
#        return self.Hfact*np.sqrt(self.T0/(self.Mstar*(self.Rin**self.TIndex)))*R*((self.TIndex+3.)/2.)

#    def ctsrho(R,z):
#        return self.Mdisc/(2.*math.pi*self.D)*(R**self.plIndex)*np.exp((-1*z**2)/(2.*self.ctsH(R)**2))/np.sqrt(2*math.pi*self.ctsH(R)**2)





def dWdh(q,h):
    """This is just for the special case of ndim=2"""
    if isinstance(q,int) or isinstance(q,float):
        q=np.array([q])
    sigma=10./(7.*math.pi)
    out=q.copy()
    c1=(q>=0) & (q<1)
    c2=(q>=1) & (q<2)
    c3=(q>=2)
    out[c1] = (sigma/(h**3))*(-2.+6.*q[c1]**2-(3.75)*q[c1]**3)
    out[c2] = (sigma/(h**3))*((1.25*q[c2]-1.)*(2-q[c2])**2)
    out[c3] = 0.
    return out
 

#import numpy as np
#from scipy.spatial import Delaunay
#
#points = np.random.rand(30, 2) # 30 points in 2-d
#tri = Delaunay(points)
#
## Make a list of line segments: 
## edge_points = [ ((x1_1, y1_1), (x2_1, y2_1)),
##                 ((x1_2, y1_2), (x2_2, y2_2)),
##                 ... ]
#edge_points = []
#edges = set()
#
#def add_edge(i, j):
#    """Add a line between the i-th and j-th points, if not in the list already"""
#    if (i, j) in edges or (j, i) in edges:
#        # already added
#        return
#    edges.add( (i, j) )
#    edge_points.append(points[ [i, j] ])
#
## loop over triangles: 
## ia, ib, ic = indices of corner points of the triangle
#for ia, ib, ic in tri.vertices:
#    add_edge(ia, ib)
#    add_edge(ib, ic)
#    add_edge(ic, ia)
#
## plot it: the LineCollection is just a (maybe) faster way to plot lots of
## lines at once
#import matplotlib.pyplot as plt
#from matplotlib.collections import LineCollection
#
#lines = LineCollection(edge_points)
#plt.figure()
#plt.title('Delaunay triangulation')
#plt.gca().add_collection(lines)
#plt.plot(points[:,0], points[:,1], 'o', hold=1)
#plt.xlim(-1, 2)
#plt.ylim(-1, 2)
#
## -- the same stuff for the convex hull
#
#edges = set()
#edge_points = []
#
#for ia, ib in tri.convex_hull:
#    add_edge(ia, ib)
#
#lines = LineCollection(edge_points)
#plt.figure()
#plt.title('Convex hull')
#plt.gca().add_collection(lines)
#plt.plot(points[:,0], points[:,1], 'o', hold=1)
#plt.xlim(-1, 2)
#plt.ylim(-1, 2)
#plt.show()
 
