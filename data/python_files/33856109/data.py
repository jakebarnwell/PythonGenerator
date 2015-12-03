import numpy as np
import struct as st
import scipy.optimize as op
import os,sys,progressbar,pylab
import matplotlib as mpl
from matplotlib import pyplot as plt
from scipy import spatial as sp
from scipy import stats
from scipy import special
from copy import deepcopy
from .plot import plot,ratioScatter,relerrorScatter

### Disc related classes and functions...

class Disc(object):
  """Particle data is stored as a big table, called _particles where unknown or missing data is np.nan.
  A type column gives the type of each particle, with 0=normal, 1=star.
  
  Each function has to implicitly make a choice on which type of data it will act upon.  Most of
  the time it should act on only a subset of particles (calculating quantities, plotting), but
  sometimes it makes more sense to hit everything."""
  coreProperties=dict(type=0)
  def __init__(self):
    self.particles=np.tile(np.nan,(0,len(Disc.coreProperties)))
    self.particleProps=deepcopy(Disc.coreProperties)
    #None is no restriction, otherwise it should be a list of tuples of the
    #format (type,subset).  Subset should either be a list of indicies for
    #the restricted set, or None for just a type restriction.
    #self._subset=[(0,[1,2,5])] would get the first, second and fifth
    #particles of type 0, [(0,None)] would get all the type 0 particles
    self.subset=None

  def __getattr__(self,attr):
    """If the disc instance explicitly has an attribute, return that.
    It's a data table propertty if it ends with an _."""
    if not attr.endswith("_"):
      return object.__getattr__(self,attr)
    attr=attr.strip("_")
    if attr in self.particleProps:
      #Get the whole thing
      tmp=self.particles[:,self.particleProps[attr]]
      #Get just the particles we want...
      return tmp[self.subset2indices()]
    raise AttributeError,attr

  def __setattr__(self,attr,val):
    """Particle properties end with _."""
    if not attr.endswith("_"):
      object.__setattr__(self,attr,val)
      return
    attr=attr.strip("_")
    indx=self.subset2indices()
    if len(val)!=len(indx):
      if len(val)==self.N:
        indx=np.arange(self.N)
      else:
        raise ValueError("Wrong length of setting values")
    #Do we need to add a new data column first?
    if not attr in self.particleProps:
      self.particles=np.append(self.particles,np.tile(np.nan,(self.N,1)),1)
      self.particleProps[attr]=self.particles.shape[1]-1
    #Update the values in the appropriate places...
    self.particles[indx,self.particleProps[attr]]=val

  def getCol(self,attr):
    """Convenience function to get an entire column (subset ignored)."""
    if attr in self.particleProps: 
      return self.particles[:,self.particleProps[attr]]
    raise AttributeError,attr

  def subset2indices(self):
    """Convert the subset list of tuples to a set of indices in the particle
    table.  A set of indicies is also a valid object."""
    if self.subset is None:
      return np.arange(self.N)
    #Is it just a raw list of indices?
    if len(self.subset)==0 or not isinstance(self.subset[0],tuple):
      return np.unique(self.subset)
    #Must be special format, so unpack.
    type=self.particles[:,self.particleProps['type']]
    ret=np.array(0)
    for sub in self.subset:
      tmp=np.where((type==sub[0]))[0]
      if sub[1] is not None:
        ret=np.append(ret,tmp[sub[1]])
      else:
        ret=np.append(ret,tmp)
    #Make sure it's in the right order and save to avoid repeating...
    self.subset=np.unique(ret[1:])
    return np.unique(ret[1:])

  def sInd2gInd(self,sInd):
    """If you have indices for the current subset, but want global indices,
    this will give them to you."""
    return self.subset2indices()[sInd]

  def gInd2sInd(self,gInd):
    """The reverse of the above.  Given a set of global indices, will return the
    indices within the current subset.  If a global index is given that isn't in the
    subset, then it will be lost."""
    sub=self.subset2indices()
    olap=np.repeat(False,self.N)
    olap[gInd]=True
    return np.where(olap[sub])[0]

  def indices2subset(self,indx):
    """Converts indicies on the _particles table to a subset object.  Note
    that this is slow as all hell at present.  Really no reason to use this."""
    self.subsetTmp(None)
    types=np.intp(np.unique(self.type[indx]))
    subset=[]
    for t in types:
      self.subsetTmp([(t,None)])
      #Needed as numpy arrays don't have an index method
      typeInd=list(self.subset2indices())
      subset.append((t,[typeInd.index(a) for a in indx if a in typeInd]))
    self.subsetRestore()
    return subset

  def hasCol(self,name):
    return name in self.particleProps

  def addParticles(self,typeVector):
    """Add a new set of particles..."""
    tmp=self.getCol('type')
    self.particles=np.append(self.particles,np.tile(np.nan,(len(typeVector),len(self.particleProps))),0)
    self.type_=np.append(tmp,typeVector)

  def delParticles(self,dropVector):
    """Drops these particles...."""
    mask=np.repeat(True,self.N)
    mask[dropVector]=False
    #Update the particle matrix, the subset and the backup subset...
    ssMask=np.repeat(False,self.N)
    ssMask[self.subset2indices()]=True
    self.subset=np.where(ssMask[mask])[0]
    if hasattr(self,"bsubset"):
      ssMask=np.repeat(False,self.N)
      ssMask[self.bsubset]=True
      self.bsubset=np.where(ssMask[mask])[0]
    self.particles=self.particles[mask,]

  def addProperty(self,name):
    if not name.endswith("_"):
      name=name+"_"
    setattr(self,name,np.repeat(np.nan,self.N))

  def fetch(self,var):
    """For a single string, it's completely equivalent to getattr(self,var), except a 2-d array with 1 column is returned,
    but for a list of variables will return a lovely dataframe with the columns asked for."""
    if isinstance(var,str):
      var=[var]
    cols=[]
    for v in var:
      if v in self.particleProps:
        cols.append(self.particleProps[v])
    if not cols:
      raise ValueError
    tmp=self.particles[:,cols]
    return tmp[self.subset2indices(),]

  def subsetTmp(self,subset=[(0,None)]):
    """When you need to have a temporary subset but not trash your "good" one.
    Turn the main subset back on, with a call to subsetrestore()"""
    if not hasattr(self,"bsubset"):
      self.bsubset=self.subset
    self.subset=subset

  def subsetRestore(self):
    """Restore the "good" subset."""
    if hasattr(self,"bsubset"):
      self.subset=self.bsubset
      delattr(self,"bsubset")

  def subsetSet(self,fields=None,N=5000,**kwargs):
    """To set the subset, pass subset="""
    #Get everything until we're done...
    self.subset=None
    if hasattr(self,"bsubset"):
        del self.bsubset
    if 'subset' in kwargs:
      self.subset=kwargs['subset']
    elif fields is not None:
      if not isinstance(fields,list):
        fields=[fields]
      subset=np.where(self.type_==0)[0]
      for field in fields:
        subset=subset[np.where((np.isfinite(getattr(self,field+"_")[subset])))[0]]
      self.subset=subset
    elif N<=0 or N>=self.N:
      print "Invalid N, subset unchanged."
    else:
      rand=np.random.permutation(np.sum(self.type_==0))
      self.subset=[(0,rand[:min(len(rand),N)])]

  @property
  def N(self):
    return self.particles.shape[0]

  @property
  def n(self):
    return len(self.subset2indices())

  def init_tree(self,force=False):
    """The tree will include ALL particles.  Not just the subset currently set."""
    self.subsetTmp(None)
    if force or not hasattr(self,"tree2"):
      self.tree2=sp.KDTree(self.fetch(['x','y']))
    if force or not hasattr(self,"tree3"):
      self.tree3=sp.KDTree(self.fetch(['x','y','z']))
    self.subsetRestore()

  def calcCommon(self):
    self.subsetTmp(None)
    #Calculate some commonly used quantities
    self.R_=np.sqrt(self.x_**2+self.y_**2)
    self.r_=np.sqrt(self.x_**2+self.y_**2+self.z_**2)
    self.theta_=np.arctan2(self.y_,self.x_)
    self.M=np.max(self.m_)
    self.subsetTmp([(0,None)])
    self.m=np.median(self.m_)
    self.Rin=np.min(self.R_)
    self.Rout=np.max(self.R_)
    self.subsetRestore()
  
  def fromFolder(self,folder):
    os.chdir(folder)
    pos=np.genfromtxt("Position.txt")
    grav=np.genfromtxt("Acceleration.txt")
    pot=np.genfromtxt("GravPotential.txt")
    mass=np.genfromtxt("Masses.txt")
    smooth=np.genfromtxt("Smoothing.txt")
    rho=np.genfromtxt("Density.txt")
    energy=np.genfromtxt("Energy.txt")
    #Adjust the coordinates so the star is at the centre...
    strarg=mass.argmax()
    strpos=pos[strarg,]
    pos=pos-strpos
    typeVec=np.zeros(pos.shape[0])
    typeVec[strarg]=1
    self.addParticles(typeVec)
    self.subsetTmp()
    #Now the ones that don't have a star...
    self.SPHrho_=rho
    self.u_=energy
    self.h_=smooth
    #Add all the properties that have the star...
    self.subsetTmp(None)
    self.x_=pos[:,0]
    self.y_=pos[:,1]
    self.z_=pos[:,2]
    self.gx_=grav[:,0]
    self.gy_=grav[:,1]
    self.gz_=grav[:,2]
    self.pot_=pot
    self.m_=mass
    self.calcCommon()

  def fromFile(self,file,format="x y z m rho iphase",**kw):
    """Will read in one column per entry in format"""
    format=format.split()
    core=['x','y','z']
    if not np.all([x in format for x in core]):
        raise ValueError("Need at least the positions...")
    fdat=np.genfromtxt(file,**kw)
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
    self.addParticles(typeVec)
    #All should contain the star...
    self.subsetTmp(None)
    self.x_=x-x[strarg]
    self.y_=y-y[strarg]
    self.z_=z-z[strarg]
    self.m_=m
    #Add any other columns...
    for col in format:
      if col not in core:
        setattr(self,col+"_",fdat[:,format.index(col)])
    self.calcCommon()

  def fromBinaryFile(self,file,format='gx gy gz',type='f',matchSubset=None):
    """type should be a valid python struct variable type, e.g. f= 4-byte
    float.  Assumes the (idiotic) fortran binary format and that every
    variable has been written in blocks of equal size.  
    Will add to the particles at position matchIndx"""
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
      tmp=np.array(st.unpack(type*size,fdat[regionstart:regionend]))
      #add this to the selected rows...
      self.subsetTmp(matchSubset)
      setattr(self,format[i]+'_',tmp)
      i=i+1
    self.subsetRestore()

  def fromGadgetBinary(self,file,newFormat=True,verbose=True):
    """Load all information from a gadget formatted binary.  If additional blocks are found beyond 
    the standard ones, we'll print out a warning."""
    f=open(file,'rb')
    fdat=f.read()
    f.close()
    #Sanity check that this is a gadget binary
    if st.unpack('i',fdat[:4])[0]!=256 or st.unpack('i',fdat[260:264])[0]!=256:
      raise TypeError("This is not a valid GADGET binary")
    #First, decode the header
    npart=np.array(st.unpack('I'*6,fdat[4:28]))
    mass=np.array(st.unpack('d'*6,fdat[28:76]))
    time=st.unpack('d',fdat[76:84])[0]
    self.time=time
    redshift=st.unpack('d',fdat[84:92])[0]
    self.redshift=redshift
    flag_sfr=st.unpack('i',fdat[92:96])[0]
    self.flag_sfr=flag_sfr
    flag_feedback=st.unpack('i',fdat[96:100])[0]
    self.flag_feedback=flag_feedback
    nall=np.array(st.unpack('I'*6,fdat[100:124]))
    flag_cooling=st.unpack('i',fdat[124:128])[0]
    self.flag_cooling=flag_cooling
    numfiles=st.unpack('i',fdat[128:132])[0]
    boxsize=st.unpack('d',fdat[132:140])[0]
    self.boxsize=boxsize
    omega0=st.unpack('d',fdat[140:148])[0]
    self.omega0=omega0
    omega_lambda=st.unpack('d',fdat[148:156])[0]
    self.omega_lambda=omega_lambda
    hubble_param=st.unpack('d',fdat[156:164])[0]
    self.hubble_param=hubble_param
    flag_age=st.unpack('i',fdat[164:168])[0]
    self.flag_age=flag_age
    flag_metals=st.unpack('i',fdat[168:172])[0]
    self.flag_metals=flag_metals
    nallhw=np.array(st.unpack('I'*6,fdat[172:196]))
    flag_entr_ics=st.unpack('i',fdat[196:200])[0]
    self.flag_entr_ics=flag_entr_ics
    if newFormat:
      extra_output=st.unpack('I',fdat[200:204])[0]
    if verbose:
      print "Read output block:"
      print "Npart = %g, %g, %g, %g, %g, %g" % tuple(npart) 
      print "Mass = %g, %g, %g, %g, %g, %g" % tuple(mass)
      print "Time = %g" % time
      print "Boxsize = %g" % boxsize
      print "Extra = %d" % extra_output
    #Now we know what to expect from the following blocks
    N=np.sum(npart)
    ptr=268
    typeVec=np.repeat(range(6),npart)
    self.addParticles(typeVec)
    #Select just the new particles
    newpart=np.arange(self.N-N,self.N)
    #Select just the new gas particles
    newpartgas=np.arange(self.N-N,self.N-N+npart[0])
    self.subsetTmp(subset=newpart)
    pos=np.reshape(st.unpack('f'*N*3,fdat[ptr:(ptr+N*12)]),(N,3))
    self.x_=pos[:,0]
    self.y_=pos[:,1]
    self.z_=pos[:,2]
    ptr=ptr+N*12+8
    vel=np.reshape(st.unpack('f'*N*3,fdat[ptr:(ptr+N*12)]),(N,3))
    self.vx_=vel[:,0]
    self.vy_=vel[:,1]
    self.vz_=vel[:,2]
    ptr=ptr+N*12+8
    ids=np.array(st.unpack('I'*N,fdat[ptr:(ptr+N*4)]))
    self.ID_=ids
    ptr=ptr+N*4+8
    #The next block might be a mass block...
    Nm=np.sum(npart*(mass==0))
    mtmp=np.repeat(mass,npart)
    if Nm:
      masses=np.array(st.unpack('f'*Nm,fdat[ptr:(ptr+Nm*4)]))
      mtmp[mtmp==0]=masses
      ptr=ptr+Nm*4+8
    self.m_=mtmp
    #It could be internal energy...
    if npart[0]:
      self.subsetTmp(subset=newpartgas)
      energy_int=np.array(st.unpack('f'*npart[0],fdat[ptr:(ptr+npart[0]*4)]))
      self.u_=energy_int
      ptr=ptr+npart[0]*4+8
      #If it's energy, it's density too...
      density=np.array(st.unpack('f'*npart[0],fdat[ptr:(ptr+npart[0]*4)]))
      self.SPHrho_=density
      ptr=ptr+npart[0]*4+8
      #And smoothing...
      hsml=np.array(st.unpack('f'*npart[0],fdat[ptr:(ptr+npart[0]*4)]))
      self.h_=hsml
      ptr=ptr+npart[0]*4+8
    #Any remaining blocks will only be present if they're enabled in the makefile
    if newFormat:
      #Output potential
      if extra_output & 1:
        self.subsetTmp(subset=newpart)
        grav_pot=np.array(st.unpack('f'*N,fdat[ptr:(ptr+N*4)]))
        self.pot_=grav_pot
        ptr=ptr+N*4+8
      if extra_output & 2:
        self.subsetTmp(subset=newpart)
        accel = np.reshape(st.unpack('f'*3*N,fdat[ptr:(ptr+N*12)]),(N,3))
        self.ax_=accel[:,0]
        self.ay_=accel[:,1]
        self.az_=accel[:,2]
        ptr=ptr+N*12+8
      if extra_output & 4:
        self.subsetTmp(subset=newpartgas)
        dAdt = np.array(st.unpack('f'*npart[0],fdat[ptr:(ptr+npart[0]*4)]))
        self.dAdt_=dAdt
        ptr=ptr+npart[0]*4+8
      if extra_output & 8:
        self.subsetTmp(subset=newpart)
        timesteps = np.array(st.unpack('f'*N,fdat[ptr:(ptr+N*4)]))
        self.dt_=timesteps
        ptr=ptr+N*4+8
      if extra_output & 16:
        self.subsetTmp(subset=newpartgas)
        alpha = np.array(st.unpack('f'*npart[0],fdat[ptr:(ptr+npart[0]*4)]))
        self.alpha_=alpha
        ptr=ptr+npart[0]*4+8
    if ptr<len(fdat):
      print "Unknown block(s) present at end of snapshot which were not read in."
    self.calcCommon()


  def toGadgetBinary(self,file,newFormat=True,fromSelf=True,time=0.0,redshift=0.0,flag_sfr=0, 
      flag_feedback=0, flag_cooling=0, boxsize=0.0,omega0=0.0,omega_lambda=0.0, 
      hubble_param=0.0, flag_age=0, flag_metals=0, flag_entr_ics=0):
    """Writes out the current subset of the disc to a GADGET binary file.
    If fromSelf is true then all the header information will be read from the 
    properties of the passed object if they exist.  i.e., any supplied values
    will be ignored."""
    f=open(file,'wb')
    if fromSelf:
      time=getattr(self,"time",time)
      redshift=getattr(self,"redshift",redshift)
      flag_sfr=getattr(self,"flag_sfr",flag_sfr)
      flag_feedback=getattr(self,"flag_feedback",flag_feedback)
      flag_cooling=getattr(self,"flag_cooling",flag_cooling)
      boxsize=getattr(self,"boxsize",boxsize)
      omega0=getattr(self,"omega0",omega0)
      omega_lambda=getattr(self,"omega_lambda",omega_lambda)
      hubble_param=getattr(self,"hubble_param",hubble_param)
      flag_age=getattr(self,"flag_age",flag_age)
      flag_metals=getattr(self,"flag_metals",flag_metals)
      flag_entr_ics=getattr(self,"flag_entr_ics",flag_entr_ics)
    #Needed for header
    tmp=self.type_
    npart=np.bincount(tmp.astype('int'),minlength=6)
    mass=np.repeat(0,6)
    nall=npart
    numfiles=1
    nallhw=np.repeat(0,6)
    extra_output=0
    if newFormat:
      extra_output=0+1*self.hasCol('pot')+2*self.hasCol('ax')+4*self.hasCol('dAdt')+8*self.hasCol('dt')+16*self.hasCol('alpha')
    #Write the header
    f.write(st.pack('i',256))
    f.write(''.join([st.pack('I',x) for x in npart]))
    f.write(''.join([st.pack('d',x) for x in mass]))
    f.write(st.pack('d',time))
    f.write(st.pack('d',redshift))
    f.write(st.pack('i',flag_sfr))
    f.write(st.pack('i',flag_feedback))
    f.write(''.join([st.pack('I',x) for x in nall]))
    f.write(st.pack('i',flag_cooling))
    f.write(st.pack('i',numfiles))
    f.write(st.pack('d',boxsize))
    f.write(st.pack('d',omega0))
    f.write(st.pack('d',omega_lambda))
    f.write(st.pack('d',hubble_param))
    f.write(st.pack('i',flag_age))
    f.write(st.pack('i',flag_metals))
    f.write(''.join([st.pack('I',x) for x in nallhw]))
    f.write(st.pack('i',flag_entr_ics))
    f.write(st.pack('i',extra_output))
    #extra 56 bytes of nothing
    f.write(''.join([st.pack('i',0) for x in xrange(14)]))
    f.write(st.pack('i',256))
    #Now we write the blocks...
    #first the position block
    pos=self.fetch(['x','y','z']).flatten()
    f.write(st.pack('i',len(pos)*4))
    f.write(''.join([st.pack('f',x) for x in pos]))
    f.write(st.pack('i',len(pos)*4))
    vel=self.fetch(['vx','vy','vz']).flatten()
    f.write(st.pack('i',len(vel)*4))
    f.write(''.join([st.pack('f',x) for x in vel]))
    f.write(st.pack('i',len(vel)*4))
    #If id isn't given, create one
    if self.hasCol('ID'):
      ids=self.ID_
    else:
      ids=np.arange(self.n)
    f.write(st.pack('i',len(ids)*4))
    f.write(''.join([st.pack('I',x) for x in ids]))
    f.write(st.pack('i',len(ids)*4))
    f.write(st.pack('i',self.n*4))
    f.write(''.join([st.pack('f',x) for x in self.m_]))
    f.write(st.pack('i',self.n*4))
    #The gas particle blocks, if they're needed
    if npart[0]:
      o=self.type_==0
      f.write(st.pack('i',npart[0]*4))
      f.write(''.join([st.pack('f',x) for x in self.u_[o]]))
      f.write(st.pack('i',npart[0]*4))
      f.write(st.pack('i',npart[0]*4))
      f.write(''.join([st.pack('f',x) for x in self.SPHrho_[o]]))
      f.write(st.pack('i',npart[0]*4))
      f.write(st.pack('i',npart[0]*4))
      f.write(''.join([st.pack('f',x) for x in self.h_[o]]))
      f.write(st.pack('i',npart[0]*4))
    #Now the extra blocks if they exist
    if extra_output & 1:
      f.write(st.pack('i',self.n*4))
      f.write(''.join([st.pack('f',x) for x in self.pot_]))
      f.write(st.pack('i',self.n*4))
    if extra_output & 2:
      f.write(st.pack('i',self.n*12))
      tmp=self.fetch(['ax','ay','az']).flatten()
      f.write(''.join([st.pack('f',x) for x in tmp]))
      f.write(st.pack('i',self.n*12))
    if extra_output & 4:
      f.write(st.pack('i',self.n*4))
      f.write(''.join([st.pack('f',x) for x in self.dAdt_]))
      f.write(st.pack('i',self.n*4))
    if extra_output & 8:
      f.write(st.pack('i',self.n*4))
      f.write(''.join([st.pack('f',x) for x in self.dt_]))
      f.write(st.pack('i',self.n*4))
    if extra_output & 16:
      f.write(st.pack('i',self.n*4))
      f.write(''.join([st.pack('f',x) for x in self.alpha_]))
      f.write(st.pack('i',self.n*4))
    #All done...
    f.close()















    





  def calcBands(self,data,boundaries=[.6,1.,2.],cts=False,maxVal=None,minVal=None,returnVal=True):
    """Assigns a factor to the table depending on which side of the
    bondaries the data specified falls on.  Can be used to colour data
    later when plotting..."""
    if cts:
      #Set invalid values to median
      t=np.median(data[np.isfinite(data)])
      data[np.logical_not(np.isfinite(data))]=t
      if maxVal is not None:
        data[data>maxVal]=maxVal
      if minVal is not None:
        data[data<minVal]=minVal
      self.bands_=data
    else:
      if not isinstance(boundaries,list):
        boundaries=[boundaries]
      self.bandBoundaries=boundaries
      if len(boundaries)<1:
        raise
      tmp=np.zeros(len(data))
      tmp[np.where(data<boundaries[0])[0]]=0
      count=0
      for i,cut in enumerate(boundaries[1:]):
        count=count+1
        tmp[np.where((data>=boundaries[i]) & (data<cut))] = count
      tmp[np.where((data>=boundaries[-1]))] = count+1
      self.bands_=tmp
    if returnVal:
      return self.bands_

  @property
  def nBands(self):
    """The number of bands."""
    if self.hasCol('bands'):
      count=int(np.nanmax(self.getCol('bands'))+1)
      if count==0:
        count=1
      return count
    return 0

  def plot(self, x, y, useBands=True, colbar=True, **kw):
    """General purpose plotting function to be used by other things."""
    #Get from strings...
    if isinstance(x,str):
      if 'xlab' not in kw:
        kw['xlab']=x
      x=getattr(self,x+"_")
    if isinstance(y,str):
      if 'ylab' not in kw:
        kw['ylab']=y
      y=getattr(self,y+"_")
    #Do the plotting...
    if useBands and self.nBands:
      ret=plot(x,y,c=self.bands_,colbar=colbar,**kw)
    else:
      ret=plot(x,y, **kw)
    return ret
  
  def ratioScatter(self,x,y1,y2=None,useBands=True,newBands=False,**kw):
    """If newbands, then bands will be calculated from the absolute log ratio,
    if usebands, then the bands will be used to display a colour scale.  The
    maxVal parameter will be honoured when making new bands."""
    #Get from strings...
    if isinstance(x,str):
      if 'xlab' not in kw:
        kw['xlab']=x
      x=getattr(self,x+"_")
    if isinstance(y1,str):
      y1=getattr(self,y1+"_")
    if y2 is not None and isinstance(y2,str):
      y2=getattr(self,y2+"_")
    #Calculate the log ratio if needed
    if y2 is not None:
      y=np.log2(np.abs(y1)/np.abs(y2))
    else:
      y=y2
    #Calculate bands...
    if newBands:
      maxVal=None
      if 'maxVal' in kw:
        maxVal=kw.pop('maxVal')
      minVal=None
      if 'minVal' in kw:
        minVal=kw.pop('minVal')
      self.calcBands(np.abs(y),cts=True,maxVal=maxVal,minVal=minVal)
    if useBands and self.nBands:
      ret=ratioScatter(x,y,c=self.bands_,colbar=True,**kw)
    else:
      ret=ratioScatter(x,y,**kw)
    return ret

  def relerrorScatter(self,x,y1,y2=None,useBands=True,newBands=False,**kw):
    """If newbands, then bands will be calculated from the absolute log ratio,
    if usebands, then the bands will be used to display a colour scale.  The
    maxVal parameter will be honoured when making new bands."""
    #Get from strings...
    if isinstance(x,str):
      if 'xlab' not in kw:
        kw['xlab']=x
      x=getattr(self,x+"_")
    if isinstance(y1,str):
      y1=getattr(self,y1+"_")
    if y2 is not None and isinstance(y2,str):
      y2=getattr(self,y2+"_")
    #Calculate the error if needed
    if y2 is not None:
      y=100.*(np.abs(y2-y1)/np.abs(y1))
    else:
      y=y2
    #Calculate bands...
    if newBands:
      maxVal=None
      if 'maxVal' in kw:
        maxVal=kw.pop('maxVal')
      minVal=None
      if 'minVal' in kw:
        minVal=kw.pop('minVal')
      self.calcBands(y,cts=True,maxVal=maxVal,minVal=minVal)
    if useBands and self.nBands:
      ret=relerrorScatter(x,y,c=self.bands_,colbar=True,**kw)
    else:
      ret=relerrorScatter(x,y,**kw)
    return ret


  def findIndex(self,x,y,z,toll=1e-8):
    """Given x, y and z, return the indecies in data that match to within
    toll.  If multiple indicies match, -1 is returned.  Indices are GLOBAL,
    not subset specific."""
    self.subsetTmp(None)
    if len(x)!=len(y) or len(y)!=len(z) or len(x)!=len(z):
      raise ValueError
    index=np.repeat(-1,len(x))
    widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=len(x)).start()
    for i in xrange(len(x)):
      tmp=np.where( (np.abs(self.x_-x[i])<toll) &
              (np.abs(self.y_-y[i])<toll) &
              (np.abs(self.z_-z[i])<toll))[0]
      if len(tmp)!=1:
        continue
      index[i]=tmp[0]
      pbar.update(i)
    self.subsetRestore()
    return index

  def calcsumgz(self,recalculate=False):
    """Calculates direct sum gravity and inserts it into the table."""
    #If we've calculated the values previously, no need to redo them...
    index=np.arange(self.n)
    ptx=self.x_
    pty=self.y_
    ptz=self.z_
    if not recalculate and hasattr(self,'sumgz'):
      o=np.where(np.isnan(self.sumgz_))
      ptx=ptx[o]
      pty=pty[o]
      ptz=ptz[o]
      index=index[o]
      tmp=self.sumgz_
    else:
      tmp=np.repeat(np.nan,self.n)
    widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=len(index)).start()
    self.subsetTmp(None)
    for count,i in enumerate(index):
      rtmp=np.sqrt((ptx[count]-self.x_)**2+(pty[count]-self.y_)**2+(ptz[count]-self.z_)**2)
      rtmp[rtmp==0]=np.Infinity
      tmp[i]=np.sum((self.G*self.m*(self.z_-ptz[count]))/rtmp**3)
      pbar.update(count)
    self.subsetRestore()
    self.sumgz_=tmp

  def calcmidplaneCD(self,tgtN=50,maxR=5.):
    """Calculate the column density using only type 0 particles."""
    self.init_tree()
    widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=self.n).start()
    spts=self.fetch(['x','y'])
    z=self.z_
    subset=self.subset2indices()
    tmp=np.zeros(self.n)
    self.subsetTmp([(0,None)])
    for i in xrange(len(tmp)):
      pbar.update(i)
      pts=np.array(self.tree2.query_ball_point(spts[i,],maxR))
      #Convert to just the subset (the type 0 particles)
      pts=self.gInd2sInd(pts)
      #Subset to desired range...
      o=np.where(np.abs(self.z_[pts])<=np.abs(z[i]))[0]
      pts=pts[o]
      #Calculate the distances...
      dist=np.sqrt((self.x_[pts]-spts[i,0])**2+(self.y_[pts]-spts[i,1])**2)
      pts=pts[dist.argsort()]
      dist=dist[dist.argsort()]
      #Subset if possible
      stop=tgtN if len(pts)>tgtN else len(pts)
      if stop<1:
        tmp[i]=0.
        continue
      h=dist[stop-1]
      tmp[i]=np.sum(self.m_[pts[:stop]])/(2.*np.pi*h**2)
    self.subsetRestore()
    self.cdMid_=tmp

  def calcsurCD(self,tgtN=50,maxR=5.):
    """Calculate the column density using only type 0 particles."""
    self.init_tree()
    widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=self.n).start()
    spts=self.fetch(['x','y'])
    z=self.z_
    subset=self.subset2indices()
    tmp=np.zeros(self.n)
    self.subsetTmp([(0,None)])
    for i in xrange(len(tmp)):
      pbar.update(i)
      pts=np.array(self.tree2.query_ball_point(spts[i,],maxR))
      #Convert to just the subset (the type 0 particles)
      pts=self.gInd2sInd(pts)
      #Subset to desired range...
      o=np.where(np.abs(self.z_[pts])>=np.abs(z[i]))[0]
      pts=pts[o]
      #Calculate the distances...
      dist=np.sqrt((self.x_[pts]-spts[i,0])**2+(self.y_[pts]-spts[i,1])**2)
      pts=pts[dist.argsort()]
      dist=dist[dist.argsort()]
      #Subset if possible
      stop=tgtN if len(pts)>tgtN else len(pts)
      if stop<1:
        tmp[i]=0.
        continue
      h=dist[stop-1]
      tmp[i]=np.sum(self.m_[pts[:stop]])/(2.*np.pi*h**2)
    self.subsetRestore()
    self.cdSur_=tmp

  def calcPotential(self):
    """Calculate the potential energy for a subset of particles..."""
    widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=self.n).start()
    x=self.x_
    y=self.y_
    z=self.z_
    pot=np.zeros(self.n)
    #We only want to calculate the potential due to type 0 praticles
    self.subsetTmp([(0,None)])
    xall=self.x_
    yall=self.y_
    zall=self.z_
    mall=self.m_
    for i in xrange(len(pot)):
      pbar.update(i)
      tmp=np.sqrt((xall-x[i])**2+(yall-y[i])**2+(zall-z[i])**2)
      tmp[tmp==0]=np.inf
      pot[i]=-self.G*np.sum(mall/tmp)
    self.subsetRestore()
    self.Pot_=pot

  def seedMap(self,subset=False,nn=50,subsetFrac=.1,maxR=5.):
    """Calculate the column density at a subset of particles.  If subset is
    set to true then we calculate it at the points specified in subset,
    otherwise a random set is chosen.  nn is the number of neighbours to
    use to calculate the surface density at each point and subsetFrac is
    the fraction of total particles to calculate it for."""
    self.init_tree()
    if subset:
      npts=self.n
      rr=self.subset2indices()
    else:
      npts=int(self.N*subsetFrac)
      rr=np.random.permutation(self.N)[:npts]
    #Get the positions where we'll calculate it
    self.subsetTmp(rr)
    spts=self.fetch(['x','y'])
    tmp=np.zeros(npts)
    #We only want to count type 0 particles
    m=self.getCol("m")
    m[self.getCol('type')!=0]=0.
    #Make some temporary lists to make calculation (a lot) faster
    widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=npts).start()
    for i in xrange(npts):
      pbar.update(i)
      pts=self.tree2.query(spts[i,],nn)
      tmp[i]=np.sum(m[pts[1]])/(2.*np.pi*np.max(pts[0])**2)
    self.cdTot_=tmp
    self.subsetRestore()

  def interpolateMap(self,grid=False):
    """Interpolates the surface density to surface using either the grid or
    the 10% column calculation."""
    #Create it if it hasn't been...
    if not grid and not self.hasCol("cdTot"):
      self.seedMap()
    if grid and not hasattr(self,"gridArray"):
      self.gridMap()
    #Now we have to interpolate the missing points...
    rr=self.subset2indices()
    #Again, far faster to use a different data structure...
    spts=self.fetch(['x','y'])
    ret=np.zeros(self.n)
    widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=self.n).start()
    if grid:
      gtree=sp.KDTree(self.gridArray[:,:2])
      tt=self.gridArray[:,2]
    else:
      src=np.isfinite(self.getCol('cdTot'))
      self.subsetTmp(np.where(src)[0])
      gtree=sp.KDTree(self.fetch(['x','y']))
      tt=self.cdTot_
      self.subsetRestore()
    for i in xrange(self.n):
      pbar.update(i)
      pts=gtree.query(spts[i,],1)
      ret[i]=tt[pts[1]]
    self.cdTotInt_=ret

  def gridMap(self,Rres=20,tres=10,log=True,minCount=10):
    """Grid up all the type 0 particles."""
    self.subsetTmp([(0,None)])
    if log:
      Rspace=np.array(np.percentile(self.R_,list(np.linspace(0,100,Rres))))
    else:
      Rspace=np.linspace(np.min(self.R_), np.max(self.R_), Rres)
    tspace=np.linspace(np.min(self.theta_),np.max(self.theta_),tres)
    grid,Redges,tedges=np.histogram2d(self.R_,self.theta_,[Rspace,tspace])
    area=np.outer((Redges[:-1]+np.diff(Redges))**2-Redges[:-1]**2,np.diff(tedges))
    counts=grid
    grid=(grid*self.m)/area
    #Flatten the grid, because it'll be useful..
    Rcenter=Redges[:-1]+np.diff(Redges)/2.
    tcenter=tedges[:-1]+np.diff(tedges)/2.
    self.gridArray=np.zeros(((Rres-1)*(tres-1),4))
    Rflat=np.ndarray.flatten(np.outer(Rcenter,np.ones(tres-1)))
    tflat=np.ndarray.flatten(np.outer(np.ones(Rres-1),tcenter))
    self.gridArray[:,0]=Rflat*np.cos(tflat)
    self.gridArray[:,1]=Rflat*np.sin(tflat)
    self.gridArray[:,2]=np.ndarray.flatten(grid)
    self.gridArray[:,3]=np.ndarray.flatten(counts)
    #Throw away those that don't meet the threshold...
    self.gridArray=self.gridArray[np.ndarray.flatten(counts)>=minCount,]
    self.subsetRestore()

  def DTFE(self):
    """Because it's so awesomely optimized now, calculate the area at all particles."""
    from scipy.spatial import Delaunay
    self.subsetTmp([(0,None)])
    tmp=self.fetch(['x','y'])
    d=Delaunay(tmp)
    tmp=np.zeros(self.n)
    flat=d.vertices.flatten()
    widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=self.n).start()
    #Replace each point in d.vertices with its (x,y) coordinate in a flat way
    d.vertPts=np.reshape(d.points[flat].flatten(),(d.vertices.shape[0],6))
    #Calculate the area of all the triangles at once...
    d.area=np.abs((d.vertPts[:,0]-d.vertPts[:,4])*(d.vertPts[:,3]-d.vertPts[:,1])-(d.vertPts[:,0]-d.vertPts[:,2])*(d.vertPts[:,5]-d.vertPts[:,1]))/2.
    #Basic idea is that each triangle is represented 3 times, with the coordinates permuted.
    #The resulting big array can be sorted by its first column and we can efficiently pull out 
    fast=np.column_stack([d.vertices,d.area])
    fast2=deepcopy(fast)
    #Permute cols
    fast2[:,0]=fast[:,1]
    fast2[:,1]=fast[:,2]
    fast2[:,2]=fast[:,0]
    fast3=deepcopy(fast)
    fast3[:,0]=fast2[:,1]
    fast3[:,1]=fast2[:,2]
    fast3[:,2]=fast2[:,0]
    #Stack them all up
    bigfast=np.row_stack([fast,fast2,fast3])
    #Sort
    bigfast=bigfast[np.argsort(bigfast[:,0]),]
    counts=np.bincount(np.intp(bigfast[:,0]))
    boundaries=np.append(0,np.cumsum(counts))
    for i in xrange(self.n):
      pbar.update(i)
      #Fetch the area of each cell...
      tmp[i]=(3.*self.m)/np.sum(bigfast[boundaries[i]:boundaries[i+1],3])
    self.DTCD_=tmp
    self.subsetRestore()

  def VD(self):
    """Pretty craptacular"""
    Nx=10000
    Ny=10000
    self.subsetTmp([(0,None)])
    x=self.x_
    y=self.y_
    z=np.arange(self.n)
    xi=np.linspace(np.min(x),np.max(x),Nx)
    yi=np.linspace(np.min(y),np.max(y),Ny)
    sqArea=((np.max(x)-np.min(x))/(Nx-1.))*((np.max(y)-np.min(y))/(Ny-1.))
    zi=griddata((x,y),z,(xi[None,:],yi[:,None]),method='nearest')
    t=zi.flatten()
    t.sort()
    tmp=list(t)
    d={}
    for v in tmp: d[v] = d[v]+1 if v in d else 1
    cnt=np.array([d.get(i,0) for i in xrange(self.n)])
    self.VDCD_=self.m/(sqArea*cnt)

  def MBE(self,Rgrid=100,thetagrid=100,logSpace=True):
    """Calculates the column density using the MBE method outlined in BJ Ferdosi et al, 2011."""
    from mypy.math import Epanechnikov
    self.subsetSet(subset=[(0,None)])
    self.init_tree()
    #First create grid...
    Rstart=np.min(self.R_)
    Rstop=np.max(self.R_)
    tstart=0.
    tstop=2.*np.pi
    if logSpace:
      rr=np.logspace(np.log10(Rstart),np.log10(Rstop),Rgrid)
    else:
      rr=np.linspace(Rstart,Rstop,Rgrid)
    tt=np.linspace(tstart,tstop,thetagrid)
    spts=np.zeros((Rgrid*thetagrid,3))
    rtmp=np.repeat(rr,thetagrid)
    ttmp=np.tile(tt,Rgrid)
    spts[:,0]=rtmp*np.cos(ttmp)
    spts[:,1]=rtmp*np.sin(ttmp)
    stree=sp.KDTree(spts[:,:2])
    #What is the optimal window size?
    a=np.percentile(self.x_,(20,80))
    b=np.percentile(self.y_,(20,80))
    bw=np.min((a[1]-a[0],b[1]-b[0]))/np.log(self.n)
    #Now calculate the pilot estimate
    ngbs=stree.query_ball_tree(self.tree2,bw)
    #Now calculate each of them
    #For each particle, get 50 nearest neighbours...
    widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=len(spts)).start()
    for i in xrange(len(spts)):
      q=sp.distance.cdist([spts[i,:2]],self.tree2.data[ngbs[i]])/bw
      spts[i,2]=np.sum(Epanechnikov(q[0,],bw,2))
      pbar.update(i)
      
    g=stats.mstats.gmean(spts[:,2])
    #Interpolate to get estimates at the points
    pts=self.fetch(['x','y'])
    zi=griddata(spts[:,:2],spts[:,2],pts,method='linear')/self.n
    hi=bw*np.sqrt(g/zi)
    hi[np.logical_not(np.isfinite(hi))]=np.median(hi)
    tmp=np.zeros(self.n)
    #Now do one more nearest neighbour search...
    widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=self.n).start()
    for i in xrange(self.n):
      q=sp.distance.cdist([pts[i,]],self.tree2.data[self.tree2.query_ball_point(pts[i,],hi[i])])[0,]
      tmp[i]=np.sum(Epanechnikov(q/hi[i],hi[i],2))/self.n
      pbar.update(i)
    self.CDMBE_=tmp
   
  def SPHCD(self,eta=1.2,maxh=np.inf):
    """Calculates it at the subset, because it's not as efficient as DT.  nn is used to determine
    what value of h to use.  This routine is roughly 100 times slower than the DTFE and as far as 
    I can tell represents the best case for an SPH based estimator.  For each particle, h is set 
    so that there are nn neigbhours within
    the SUPPORT (i.e. 2h) of the particle.  This avoids having to do costly (and more importantly
    buggy) numerical solves to self consistently satisfy h=eta(m/Sigma)^.5."""
    from mypy.math import W
    nn=np.round(np.pi*4.*eta*eta)
    self.init_tree()
    spts=self.fetch(['x','y'])
    tmp=np.zeros(self.n)
    #Mask mass to only include contribution from type 0 particles
    mmask=self.getCol("m")
    mmask[self.getCol("type")!=0]=0.
    #For each particle, get 50 nearest neighbours...
    widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=self.n).start()
    for i in xrange(self.n):
      pbar.update(i)
      pts=self.tree2.query(spts[i,],nn,distance_upper_bound=maxh)
      h=np.max(pts[0])/2.
      q=pts[0]/h
      tmp[i]=np.sum(W(q,h,ndim=2)*mmask[pts[1]])
    self.SPHCD_=tmp

  def IterativeSPHCD(self,eta=1.2):
    """This is MUCH slower than the above SPH column density estimator.  It is slower because it 
    uses the self consistent iterative method and solves for the non-linear solution to the coupled
    equations rho= sum(mW(q,h)) and h=eta(m/rho)**.5."""
    from mypy.math import dWdrho
    self.init_tree()
    self.DTFE()
    spts=self.fetch(['x','y'])
    tmp=np.zeros(self.n)
    #Define the functions to solve
    def fr(r,pt):
      #print "Calculating f with %s",r
      return r-self.rho(pt,self.h(r,ndim=2))

    def fh(h,pt):
      return h-eta*(self.m/self.rho(pt,h))**.5

    def fprime(r,pt):
      #print "Calculating fprime with %s",r
      h=self.h(r,ndim=2)
      q=self.q(pt,h)[0]
      return 1.-np.sum(self.m*dWdrho(q,h,r,ndim=2)*(q/(2.*r)))

    widgets = [progressbar.Percentage(), progressbar.Bar(),' ',progressbar.FormatLabel('Time elapsed: %(elapsed)s'),' ',progressbar.ETA()]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=self.n).start()
    for i in xrange(self.n):
      #tmp[i]=op.newton(fr,self.DTCD_[i],fprime=fprime,args=(spts[i,],))
      tmp[i]=op.brentq(fr,1e-10,1.,args=(spts[i,],))
      pbar.update(i)
    self.iSPHCD_=tmp


  def q(self,pt,h):
    """
    Given a point and a smoothing length, return the points within 2h and their q values.
    Returns a list where the first element is the q values and the second is the indices of
    the neighbouring points.
    """
    self.init_tree()
    if isinstance(pt,int) or isinstance(pt,float):
      pt=np.array([pt])
    ndim=pt.size
    if ndim<=1 or ndim>3:
      raise ValueError("pt must be a vector with length==ndim")
    if ndim==2:
      pts=self.tree2.query_ball_point(pt,2*h)
      self.subsetTmp(pts)
      q=self.fetch(['x','y'])-pt
      q=np.sqrt(q[:,0]**2+q[:,1]**2)/h
    elif ndim==3:
      pts=self.tree3.query_ball_point(pt,2*h)
      self.subsetTmp(pts)
      q=self.fetch(['x','y','z'])-pt
      q=np.sqrt(q[:,0]**2+q[:,1]**2+q[:,2]**2)/h
    self.subsetRestore()
    return [q,pts]

  def rho(self,pt,h):
    """Given a value of h, calculate the SPH estimate of rho at the point pt."""
    from mypy.math import W
    if isinstance(pt,int) or isinstance(pt,float):
      pt=np.array([pt])
    ndim=pt.size
    q,pts=self.q(pt,h)
    return np.sum(self.getCol('m')[pts]*W(q,h,ndim))

  def h(self,rho,eta=1.2,ndim=3):
    """Given an estimate of rho, estimate h."""
    return eta*(self.m/rho)**(1./ndim)

class AnalyticDisc(Disc):
  def MMwrite(self,file="/home/my304/data/Output/MMtmp_data.txt"):
    f=open(file,'w')
    #The parameters must come first and there must be a multiple of 3
    params=[self.Hfact, max(abs(self.getCol('z'))), self.T0, self.plIndex,
            self.TIndex, self.Rout,
            self.Rin, self.Mstar, self.Mdisc, self.G, self.D]
    while len(params)%3:
      params.append(0.)
    tmp=[str(p) for p in params]
    f.write('\t'.join(tmp))
    f.write('\n')
    R=self.R_
    t=self.theta_
    z=self.z_
    for i in xrange(self.N):
      f.write(str(R[i]) + '\t' + str(t[i]) + '\t' + str(z[i]) + '\n')
    f.close()
    self.MMsubset=self.subset

  def MMread(self,file="/home/my304/data/Output/MMtmp_processed.txt",subset=None):
    """We need to know which indexes to insert this information into the
    data object, one way is to use a supplied subset (self._MMsubest is saved
    by MMwrite).  If subset is None, we attempt to guess the index based on
    the positions given in the MM file."""
    self.MMdata=np.genfromtxt(file)
    if subset is not None:
      self.subsetTmp(subset)
      self.Agznostar_=self.MMdata[:,4]
      self.MMapprox_=self.MMdata[:,3]
    else:
      x=self.MMdata[:,0]*np.cos(self.MMdata[:,1])
      y=self.MMdata[:,0]*np.sin(self.MMdata[:,1])
      o=self.findIndex(x,y,self.MMdata[:,2])
      if np.any(o==-1):
        print "No indicies provided and failed to find match for %s points" % np.sum(o==-1)
        raise ValueError
      self.subsetTmp(None)
      self.addProperty("Agznostar")
      self.addProperty("MMapprox")
      tmp=self.Agznostar_
      tmp[o]=self.MMdata[:,4]
      self.Agznostar_=tmp
      tmp[o]=self.MMdata[:,3]
      self.MMapprox_=tmp
    self.subsetRestore()

  def describeDisc(self,Hfact=.002597943,T0=16.7,plIndex=-0.5,TIndex=0.,Rin=5.,Rout=100.,Mstar=1.,Mdisc=.1,G=887.2057):
    if not self.N:
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
    #All these properties only apply to the gas particles..
    self.subsetTmp([(0,None)])
    #We can infer some stuff if we have data...
    self.Mdisc=np.sum(self.m_)
    self.Rin=self.R_.min()
    self.Rout=self.R_.max()
    if plIndex==-2:
      self.D=np.log2(self.Rout/self.Rin)
    else:
      self.D=(1./(self.plIndex+2.))*(self.Rout**(self.plIndex+2)-self.Rin**(self.plIndex+2))
    self.AscaleH_=self.Hfact*np.sqrt(self.T0/(self.Mstar*(self.Rin**self.TIndex)))*self.R_**((self.TIndex+3.)/2.)
    self.Arho_=(self.Mdisc/(2.*np.pi*self.D))*(self.R_**self.plIndex)*(np.exp((-1.*self.z_**2)/(2.*self.AscaleH_**2))/np.sqrt(2.*np.pi*self.AscaleH_**2))
    self.AcdSur_=((self.Mdisc*self.R_**self.plIndex)/(4.*np.pi*self.D))*(1-special.erf(np.abs(self.z_)/np.sqrt(2.*self.AscaleH_**2)))
    self.AcdMid_=(self.R_**self.plIndex)*(self.Mdisc/(4.*np.pi*self.D))*(special.erf(np.abs(self.z_)/np.sqrt(2.*self.AscaleH_**2)))
    self.AcdTot_=(self.Mdisc/(4.*np.pi*self.D))*self.R_**self.plIndex
    self.Agzstar_=-1.*(self.G*self.Mstar*self.z_)/(self.r_**3)
    self.Agzapprox_=-4.*np.pi*self.G*self.AcdMid_*np.sign(self.z_)
    self.gznostar_=self.gz_-self.Agzstar_

#    def ctsH(self,R):
#        return self.Hfact*np.sqrt(self.T0/(self.Mstar*(self.Rin**self.TIndex)))*R*((self.TIndex+3.)/2.)
#    def ctsrho(R,z):
#        return self.Mdisc/(2.*np.pi*self.D)*(R**self.plIndex)*np.exp((-1*z**2)/(2.*self.ctsH(R)**2))/np.sqrt(2*np.pi*self.ctsH(R)**2)

#def dWdh(q,h):
#    """This is just for the special case of ndim=2"""
#    if isinstance(q,int) or isinstance(q,float):
#        q=np.array([q])
#    sigma=10./(7.*np.pi)
#    out=q.copy()
#    c1=(q>=0) & (q<1)
#    c2=(q>=1) & (q<2)
#    c3=(q>=2)
#    out[c1] = (sigma/(h**3))*(-2.+6.*q[c1]**2-(3.75)*q[c1]**3)
#    out[c2] = (sigma/(h**3))*((1.25*q[c2]-1.)*(2-q[c2])**2)
#    out[c3] = 0.
#    return out
# 
#
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
