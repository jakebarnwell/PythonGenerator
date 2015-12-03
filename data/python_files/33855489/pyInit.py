import numpy as np
import copy as cp
import struct as st
import math,os,sys,progressbar,pylab
import matplotlib as mpl
from matplotlib import pyplot as plt
from numpy.lib import recfunctions
from scipy import spatial as sp
from scipy import special
from scipy.interpolate import griddata,interp1d
from scipy.ndimage import map_coordinates


def gauss_kern(size, sizey=None):
   """ Returns a normalized 2D gauss kernel array for convolutions """
   size = int(size)
   if not sizey:
       sizey = size
   else:
       sizey = int(sizey)
   x, y = mgrid[-size:size+1, -sizey:sizey+1]
   g = exp(-(x**2/float(size)+y**2/float(sizey)))
   return g / g.sum()
 
def blur_image(im, n, ny=None) :
   """ blurs the image by convolving with a gaussian kernel of typical
       size n. The optional keyword argument ny allows for a different
       size in the y direction.
   """
   g = gauss_kern(n, sizey=ny)
   improc = signal.convolve(im,g, mode='valid')
   return improc

def sround(x,figs=0):
    pw=np.floor(np.log10(np.abs(x)))
    return 10**pw*round(x*10**-pw)

def propspace(a,b,n=50):
    """Basically just logspace, but I wanted to be able to "see" what I was
    doing."""
    K=((b/a)**(1./(n-1.)))-1.
    out=np.zeros(n)
    for i in xrange(n):
        out[i]=a*((1+K)**i)
    return out
    
    

def polar2cartesian(r, t, grid, x, y, order=3):
    """Coordinate transform for converting a polar array to Cartesian
    coordinates.  r and t are the coordinates on the current polar grid, grid
    are the values at each location and x,y, are the points where we are to
    interpolate in cartesian space.  A spline controls the interpolation, where
    order specificies the spline order (0-5)."""

    X, Y = np.meshgrid(x, y)

    new_r = np.sqrt(X*X+Y*Y)
    new_t = np.arctan2(X, Y)

    ir = interp1d(r, np.arange(len(r)), bounds_error=False)
    it = interp1d(t, np.arange(len(t)))

    new_ir = ir(new_r.ravel())
    new_it = it(new_t.ravel())

    new_ir[new_r.ravel() > r.max()] = len(r)-1
    new_ir[new_r.ravel() < r.min()] = 0
    return map_coordinates(grid, np.array([new_ir, new_it]),
                            order=order).reshape(new_r.shape)



def plot(x, y, hline=None, vline=None, box=True, xlab='', ylab='',
        title='', fontsize=mpl.rcParams['font.size'], log='', pch='.', add=False, **kw):
    """ General purpose plotting function.  Use log on xy axis if x or y or
    both appears in the string log.  box plots a boxplot to the left of data
    range and hline and vline include vertical and horizontal lines. 
    
    Returns list of [[fig],[box],main]
    """
    pchConvert = ['.','o','^','v','<','>','p','s','+','*','x']
    if not isinstance(pch,str):
      pch=pchConvert[pch%len(pchConvert)]
    ret = []
    if not add:
        figobj=plt.figure()
        ret.append(figobj)
    pltfunc=plt.plot
    if log.find('x')>=0 and log.find('y')>=0:
        pltfunc=plt.loglog
    elif log.find('x')>=0:
        pltfunc=plt.semilogx
    elif log.find('y')>=0:
        pltfunc=plt.semilogy
    if box and not add:
        qs=np.percentile(y,[5,25,50,75,95])
        whis=np.max((qs[4]-qs[2],qs[2]-qs[0]))/(qs[3]-qs[1])
        xsize=sround((x.max()-x.min())/10.)
        boxobj=plt.boxplot(y,positions=[x.min()-xsize],widths=[xsize],whis=whis)
        ret.append(boxobj)
    #make col a synonym for color to have R like syntax
    if 'col' in kw:
        kw['color']=kw.pop['col']
    main=pltfunc(x,y,pch,**kw)
    ret.append(main)
    if box and not add:
        pylab.xticks(np.arange(sround(x.min()),sround(x.max()),xsize))
    if hline is not None:
        hline = [hline] if not isinstance(hline,list) else hline
        for l in hline:
            pltfunc([x.min(),x.max()],[l,l],'r')

    if vline is not None:
        vline = [vline] if not isinstance(vline,list) else vline
        for l in vline:
            pltfunc([l,l],[y.min(),y.max()],'r')
    if not add:
        plt.xlabel(xlab,fontsize=fontsize)
        plt.ylabel(ylab,fontsize=fontsize)
        plt.title(title,fontsize=fontsize)
    return ret

def heatMap(x,y,z,xres=5000,yres=5000,bar=True,log=True,xlab='', ylab='',
    title=''):
    """Given a set of coordinates {(x,y,z)}, grids up x and y and converts
    the z values into a colour scaling."""
    xi=np.linspace(x.min(),x.max(),xres)
    yi=np.linspace(y.min(),y.max(),yres)
    zi=griddata((x,y),np.log10(z),(xi[None,:],yi[:,None]),method='cubic')
    ex=[xi.min(),xi.max(),yi.max(),yi.min()]
    ret=plt.imshow(zi,extent=ex)
    plt.xlabel(xlab)
    plt.ylabel(ylab)
    plt.title(title)
    if bar:
        plt.colorbar()
    return ret

class Disc(object):
    """This object is used to store information about an SPH disc, to calculate
    infromation from this data and to plot the data in a useful way.  At it's
    core is an object called "data", which is populated from the SPH data.
    This is a structured (named) array, SPH particles as all entries.  
    Unknown or missing data is represented with np.nan.  The star is stored
    seperately"""
    #The default data type to store things as f4 is 32bit float, f8 is 64bit
    #float.  Change as needed
    DTYPE='f8'
    #The parameters will be written out in this order...
    def __init__(self,G=887.2057):
        self.loaded=False
        self.subset=None
        self.G=G
        #These are the core data atributes, we'll usually have many more...
        self.dt=np.dtype([('x',self.DTYPE), ('y',self.DTYPE), ('z',self.DTYPE),('m',self.DTYPE)])

    def init_tree(s,force=False):
        if force or not hasattr(s,"tree2"):
            s.tree2=sp.KDTree(np.column_stack((s.data['x'],s.data['y'])))
        if force or not hasattr(s,"tree3"):
            s.tree3=sp.KDTree(np.column_stack((s.data['x'],s.data['y'],s.data['z'])))

    def addCol(self,name):
        """Ensure the column mentioned exists."""
        if name not in self.data.dtype.names:
            self.data=recfunctions.append_fields(self.data, name,
                    np.repeat(np.nan,self.data.shape[0]), dtypes=self.DTYPE,
                    usemask=False)

    def swapStar(self,data,st):
        tmp=cp.deepcopy(data[-1,])
        data[-1,]=data[st,]
        data[st,]=tmp
        return data

    def fromFolder(s,folder):
        os.chdir(folder)
        s.pos=np.genfromtxt("Position.txt")
        s.grav=np.genfromtxt("Acceleration.txt")
        s.pot=np.genfromtxt("GravPotential.txt")
        s.mass=np.genfromtxt("Masses.txt")
        s.smooth=np.genfromtxt("Smoothing.txt")
        s.rho=np.genfromtxt("Density.txt")
        s.energy=np.genfromtxt("Energy.txt")
        s.strarg=s.mass.argmax()
        strarg=s.strarg
        s.star=s.pos[strarg,]
        s.Mstar=s.mass.max()
        #Adjust for the position of the star
        s.pos=s.pos-s.star
        #The star is always the last record... Even if we don't have one (?!)
        #To do this, any list with a star value will swap the last entry with
        #the star, which should be consistent
        row=tuple(np.repeat(np.nan,len(s.dt)))
        s.data=np.array([row for i in xrange(s.pos.shape[0]-1)],dtype=s.dt)
        #s.data=np.array(np.repeat(np.nan,s.pos.shape[0]-1),dtype=s.dt)
        s.pos=s.swapStar(s.pos,strarg)
        s.star=s.pos[s.n]
        s.data['x']=s.pos[:s.n,0]
        s.data['y']=s.pos[:s.n,1]
        s.data['z']=s.pos[:s.n,2]
        s.mass=s.swapStar(s.mass,strarg)
        s.data['m']=s.mass[:s.n]
        s.star=np.concatenate((s.star,[s.mass[s.n]]))
        s.grav=s.swapStar(s.grav,strarg)
        s.star=np.concatenate((s.star,[s.grav[s.n,2]]))
        s.addCol('gz')
        s.data['gz']=s.grav[:s.n,2]
        s.addCol('R')
        s.data['R']=np.sqrt(s.data['x']**2+s.data['y']**2)
        s.addCol('r')
        s.data['r']=np.sqrt(s.data['x']**2+s.data['y']**2+s.data['z']**2)
        s.addCol('theta')
        s.data['theta']=np.arctan2(s.data['y'],s.data['x'])
        s.loaded=True

    def fromFile(s,file,format="x y z m rho iphase"):
        """Lodato format is x,y,z,m,rho,iphase"""
        format=format.split()
        if 'x' not in format or 'y' not in format or 'z' not in format:
            raise
        s.fdat=np.genfromtxt(file)
        row=tuple(np.repeat(np.nan,len(s.dt)))
        s.data=np.array([row for i in xrange(s.fdat.shape[0]-1)],dtype=s.dt)
        #s.data=np.array(np.repeat(np.nan,s.fdat.shape[0]-1),dtype=s.dt)
        x=s.fdat[:,format.index('x')]
        y=s.fdat[:,format.index('y')]
        z=s.fdat[:,format.index('z')]
        m=s.fdat[:,format.index('m')]
        #Move the star
        s.strarg=m.argmax()
        s.Mstar=m.max()
        s.star=np.array([x[s.strarg],y[s.strarg],z[s.strarg]])
        x=x-x[s.strarg]
        y=y-y[s.strarg]
        z=z-z[s.strarg]
        s.addCol("x")
        s.addCol("y")
        s.addCol("z")
        tmp=s.swapStar(x,s.strarg)
        s.data['x']=tmp[:s.n]
        tmp=s.swapStar(y,s.strarg)
        s.data['y']=tmp[:s.n]
        tmp=s.swapStar(z,s.strarg)
        s.data['z']=tmp[:s.n]
        #Load everything into the array, except the star
        for i,var in enumerate(format):
            #Already been loaded...
            if var in ['x','y','z']:
                continue
            s.addCol(var)
            tmp=s.fdat[:,i]
            tmp=s.swapStar(tmp,s.strarg)
            s.data[var]=tmp[:s.n]
        s.addCol('R')
        s.data['R']=np.sqrt(s.data['x']**2+s.data['y']**2)
        s.addCol('r')
        s.data['r']=np.sqrt(s.data['x']**2+s.data['y']**2+s.data['z']**2)
        s.addCol('theta')
        s.data['theta']=np.arctan2(s.data['y'],s.data['x'])
        s.loaded=True

    def fromBinaryFile(s,file,format='gx gy gz',type='f'):
        """type should be a valid python struct variable type, e.g. f= 4-byte
        float.  Assumes the (idiotic) fortran binary format and that every
        variable has been written in blocks of equal size."""
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
            s.addCol(format[i])
            tmp=np.array(st.unpack(type*size,fdat[regionstart:regionend]))
            #Remove star if necessary
            if len(tmp)==s.n+1:
                tmp=s.swapStar(tmp,s.strarg)
            s.data[format[i]]=tmp[:s.n]
            i=i+1

    @property
    def N(self):
        if self.subset is not None:
            return len(self.subset)
        return self.n

    @property
    def n(s):
        if not hasattr(s,'data'):
            return 0
        return s.data.shape[0]

    def fetch(self,variable):
        #If it's a variable of the length of the full data table, return the
        #subset, otherwise we shouldn't
        if self.subset is not None and len(variable)==self.n:
            return variable[self.subset]
        return variable

    def subsetoff(s):
        #Save it for turning back on later...
        if hasattr(s,"subset") and s.subset is not None:
            s.__subset=s.subset
        s.subset=None

    def subseton(self,fields=None,N=5000,force=False):
        """All functions will act on just a subset of the data, rather than the
        entirety of it.  You can either supply N in which case the particles
        will be randomly chosen (N of them) or supply any number of fields, in
        which case the praticles will be set to those rows where there is data
        available.  If this is all entries or None, or you enter a stupid value
        for N, the current subset will not be changed"""
        #If it's already on, do nothing
        if self.subset is not None:
            return None
        #Restore the old one if it's still there
        if not force and hasattr(self,"__subset"):
            self.subset=self.__subset
            return None
        if fields is not None:
            if not isinstance(fields,list):
                subset=np.where((np.isfinite(self.data[fields])))[0]
            else:
                subset=np.arange(self.n)
                for field in fields:
                    subset=subset[np.where((np.isfinite(self.data[field][subset])))]
            if len(subset)==0 or len(subset)==self.n:
                print "Invalid fields, subset is unchanged"
            else:
                self.subset=subset
        elif N<=0 or N>=self.n:
            print "Invalid N, subset is unchanged"
        else:
            rand=np.random.permutation(self.n)
            self.subset=rand[:min(len(rand),N)]

    def calcBands(self,data,boundaries=[.6,1.,2.]):
        """Assigns a factor to the table depending on which side of the
        bondaries the data specified falls on.  Can be used to colour data
        later when plotting..."""
        if not isinstance(boundaries,list):
            boundaries=[boundaries]
        self.addCol('bands')
        self.bandBoundaries=boundaries
        data=np.abs(self.fetch(data))
        if len(boundaries)<1:
            raise
        self.data['bands'][np.where(data<boundaries[0])]=0
        count=0
        for i,cut in enumerate(boundaries[1:]):
            count=count+1
            self.data['bands'][np.where((data>=boundaries[i]) & (data<cut))] = count
        self.data['bands'][np.where((data>=boundaries[-1]))] = count+1

    @property
    def nBands(self):
        if 'bands' in self.data.dtype.names and not np.all(np.isnan(self.data['bands'])):
            return int(np.nanmax(self.data['bands'])+1)
        return 0

    def plot(s, x, y, newBands=False, useBands=True, hline=0, **kw):
        """General purpose plotting function to be used by other things. We can
        calculate bands or display pre-calculated banding.  If boundaries is
        passed to this function, we pass it on to calcBands.
        
        Returns the figure object and the series of line segments [fig,[lines]]
        """
        ret=[]
        #Get from strings...
        if isinstance(x,str):
            if 'xlab' not in kw:
                kw['xlab']=x
            x=s.data[x]
        if isinstance(y,str):
            if 'ylab' not in kw:
                kw['ylab']=y
            y=s.data[y]
        #Otherwise, we have them already
        x=s.fetch(x)
        y=s.fetch(y)
        if newBands:
            if 'boundaries' in kw:
                s.calcBands(y,boundaries=kw.pop('boundaries'))
            else:
                s.calcBands(y)
        #Don't want to be passing a useless kw arg...
        elif 'boundaries' in kw:
            tmp=kw.pop('boundaries')
        if useBands and 'bands' in s.data.dtype.names:
            tmp=plot(x,y, pch=0,hline=hline,**kw)
            ret.append(tmp[0])
            lines=[]
            for i in xrange(s.nBands):
                o=np.where(s.data['bands']==i)
                tmp=plot(x[o],y[o], pch=i+1,add=True)
                lines.append(tmp[-1])
            ret.append(lines)

        else:
            tmp=plot(x,y, hline=hline, **kw)
            ret.append(tmp[0])
            ret.append([tmp[-1]])
        return ret

    def ratioScatter(s, x, y1, y2=None, boundaries = [.6,1.], legend=True, loc="upper right", **kw):
        """ Designed for plotting log ratios.  If y1 and y2 both given, the y
        axis becomes log2(|y1|/|y2|), otherwise y1 is assumed to be a valid log
        ratio of two values."""
        #Get from strings...
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
            y=np.log2(np.abs(y1)/np.abs(y2))
        else:
            y=y1
        ret=s.plot(x,y,boundaries=boundaries, **kw)
        if legend and 'bands' in s.data.dtype.names and len(s.bandBoundaries)+1 == len(ret[-1]):
            #Build the labels...
            labs=["< %s" % str(s.bandBoundaries[0])]
            for i in xrange(1,len(s.bandBoundaries)):
                labs.append("%s - %s" %
                    (str(s.bandBoundaries[i-1]),str(s.bandBoundaries[i])))
            labs.append("> %s" % str(s.bandBoundaries[-1]))
            plt.legend(ret[-1],labs,loc=loc)
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






#A SPH smoother...
def W(q,h,ndim=3):
    #Here q=|r_a-r_b|/h
    import math
    if isinstance(q,int) or isinstance(q,float):
        q=np.array([q])
    sigma3=1./math.pi
    sigma2=10./(7.*math.pi)
    sigma1=2./3.
    if ndim==1:
        sigma=sigma1
    elif ndim==2:
        sigma=sigma2
    elif ndim==3:
        sigma=sigma3
    else:
        raise NameError('ndim must be between 1-3')
    out=q.copy()
    c1=(q>=0) & (q<1)
    c2=(q>=1) & (q<2)
    c3=(q>=2)
    out[c1] = (sigma/(h**ndim))*(1.-(1.5)*q[c1]**2+(.75)*q[c1]**3)
    out[c2] = (sigma/(h**ndim))*(.25*(2-q[c2])**3)
    out[c3] = 0
    return out

