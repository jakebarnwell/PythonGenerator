import numpy as np
import scipy.optimize as op
import scipy.special as fn
#import pylab as p
import math
from collections import OrderedDict, namedtuple
import lines
import pprint
import scipy.interpolate as ip
import scipy.signal as sig
import lines, os
import parser

DEBUG=True

fwhm_coef=2.*math.sqrt(2.*math.log(2.))
sqrt_2pi=math.sqrt(2.*math.pi)
sqrt_2 = math.sqrt(2.)
pi_d_2 = math.pi/2.

#e_0 = 0.0086
e_0 = 0.0
e_mo= 17.48

def gauss(x, x0, A, fwhm):
    sigma = fwhm/fwhm_coef
    _c=A  #/(sigma*sqrt_2pi)
    _=((x-x0)**2)/(2*sigma**2)
    # print _, _c
    _=np.exp(-_)*_c
    return _

def gauss_square(A, fwhm):
    sigma = fwhm/fwhm_coef
    _e = A*sigma*sqrt_2pi
    return _e

def arccot(x):
    return pi_d_2-np.arctan(x)

Pike=namedtuple('Line','x0, A, fwhm, bkg, slope, chisq')

zero_pike=Pike._make((0, 1., 1., 0., 0., None))
zero_line=lines.Line._make((0, '', '', 0.0086, 'Zero', 100))


_LL={"L":0.12, "K":0.5}
def wgt(e1, e2):
    if e1==e2:
        return e1

    K=_LL[e1.name[0]]

    return (e1.keV+K*e2.keV)/(1+K)
    #return (e1+e2)/2.


class Object():
    pass

class FittingWarning(ValueError):
    pass

class Parameters(object):

    def __init__(self, channels):
        self.channels=np.array(channels)
        self.x=np.arange(len(self.channels))
        self.peakes=[] # List of the recognized lines
        self.peake_cache={}  # Map initial x0 to its fitted line
        self.scale=Object()
        self.scale.zero_e=None
        self.scale.max_keV=None
        self.scale.done=False
        self.scale.peakes=[]
        self.scale.fwhm=Object()
        self.scale.fwhm.done=False

        self.bkg=None

        self.cwt=Object()
        self.cwt.peakes=OrderedDict() # Map peake x (integer) to its fwhm calculated from CWT
        self.cwt.done=False
        self.line_db_conn=None

        self.set_active_channels(self.channels)
        #self.fig=p

    def set_figure(self, fig):
        self.fig=fig

    def set_line_db_conn(self, conn):
        self.line_db_conn=conn

    def set_active_channels(self, channels):
        self.active_channels=channels
        self.peake_cache={}

    def set_scale_lines(self, zero_e, lines, max_keV):
        self.scale.zero_e=zero_e
        self.scale.lines=lines
        self.scale.max_keV=max_keV

    def sub_line(self, channels, line, s=3.):
        w=int(line.fwhm*s+0.5)
        xmin, xmax = self.cut(line.x0, w, xl)
        y=channels
        y[xmin:xmax]=y[xmin:xmax]-gauss(x[xmin:xmax], line.x0, line.A, line.fwhm)

    def keV_to_channel(self, keV):
        if self.scale.done:
            return (keV-self.scale.b)/self.scale.k
        else:
            return RuntimeError, "scale did not calculated"

    def channel_to_keV(self, channel):
        if self.scale.done:
            return channel*self.scale.k+self.scale.b
        else:
            return RuntimeError, "scale did not calculated"

    def calc_scale(self, plot=False, force=False, pb=None):
        if self.scale.zero_e==None:
            raise ValueError, "energy for Zero pike is not set."
        if len(self.scale.lines)!=1:
            raise ValueError, "supply at exactly one element to make scaling."
        if self.scale.done and not force:
            return self.scale

        max_keV=self.scale.max_keV
        ls=self.line_db_conn.select(element=self.scale.lines,
            where="keV < %3.5f" % max_keV,
            analytical=True, order_by="e.Z")
        ls=list(ls)
        e_2=wgt(ls[0],ls[1])
        lines=[self.scale.zero_e, e_2]

        y=np.array(self.channels)
        xl=len(y)
        x=self.x
        y=np.array(y, dtype=np.dtype('f8'))

        _y=np.atleast_2d(y)

        #Filter out high frequences, i.e., filter out the noice.
        order=1
        _order=int(order*2)
        b, a = sig.butter(order, 0.1, btype='low')
        if pb: pb()
        yfiltered = sig.lfilter(b, a, y)
        y_e=yfiltered[-1]
        #yfiltered[:-_order]=yfiltered[_order:]  # Shift the result (works not fine).
        #yfiltered[-_order:]=np.zeros(_order)+y_e
        if plot:
            p.plot(x,yfiltered, color=(0,1,0), linewidth=3, alpha=0.5)

        #Calc the trend of the background.
        order=5
        _order=int(order*2)
        b, a = sig.butter(order, [0.0003, 0.9], btype='bandstop')
        _y=np.array(y)
        _y[:160]=0.
        yfilteredlb = sig.lfilter(b, a, y)
        y_e=yfilteredlb[-1]
        #yfilteredlb[:-_order]=yfilteredlb[_order:]
        #yfilteredlb[-_order:]=np.zeros(_order)+y_e
        if pb: pb()

        #Find left Zero pike
        chst=-1
        for i, ch in enumerate(yfiltered):
            if ch<chst:
                break
            else:
                chst=ch
        zero=i-1
        chst=-1
        i=x[-1]
        while i>=0:
            _y=yfiltered[i]
            if yfilteredlb[i]>_y:
                i-=1
                continue
            if _y<chst:
                break
            else:
                chst=_y
            i-=1
        tube=i+1
        #FIXME
        tube=3579

        if plot:
            p.plot(x,yfiltered, color=(0,1,0), linewidth=3, alpha=0.5)
            p.plot(x,yfilteredlb, color=(0,1,0), linewidth=3, alpha=0.5)

        points=[zero, tube]
        ws=[]
        S_fwhm=1.0
        print "POINTS", points
        fwhm_guess=None
        for x0 in points:
            Xopt=self.peake_cache.get(x0, None)
            if Xopt != None:
                ws.append(Xopt)
                continue

            task={
                0:([1,1,1,0,0], 1e-8, True, 1000, 1.0),
                1:([1,1,0,1,1], 1e-8, True, 2000, 2.0),
                2:([1,1,1,1,1], 1e-8, True, 6000, 2.5),
            }
            fail_iter=False
            A=y[x0]
            bkg=0.
            for step in range(len(task)):
                if fail_iter:
                    break
                mask, xtol, _plot, iters, s_fwhm=task[step]
                try:
                    if fwhm_guess != None:
                        width=fwhm_guess*s_fwhm
                    else:
                        fwhm_guess=10
                        width=20
                    Xopt=self.r_line(x0, A=A,
                        fwhm=fwhm_guess,
                        width=width, plot=_plot and plot,
                        raise_on_warn=True, iters=iters,
                        mask=mask, xtol=xtol
                        )
                    if pb: pb()
                except FittingWarning, w:
                    print "Fit Warning step", step
                    fail_iter=True
                    continue
                x0=Xopt.x0
                A=Xopt.A
                fwhm_guess=Xopt.fwhm
                bkg=Xopt.bkg
            if not fail_iter:
                self.peake_cache[x0]=Xopt
                ws.append(Xopt)

        print ws
        ws.sort(key=lambda x: x.x0)
        self.scale.peakes=ws
        zero_fwhm, tube_fwhm = [w.fwhm for w in ws]
        zero_x0, tube_x0 = [w.x0 for w in ws]

        _y=np.array(lines)
        _x0=np.array([_.x0 for _ in ws])
        def scale((k,b), x, y):
            return y-((x*k)+b)
        k_scale, b_scale = op.leastsq(scale, [1., 0.], args=(_x0,_y))[0]
        if pb: pb()

        print "K, B:", k_scale, b_scale
        self.scale.k=k_scale
        self.scale.b=b_scale
        self.scale.done=True
        return self.scale

    def refine_scale(self, elements, plot=False, background=True, pb=None):
        ws=[]
        # Select analytical lines (the brightest ones) from the database.
        max_keV=self.channel_to_keV(len(self.channels))
        els=elements # sorted(list(elements))
        ls=self.line_db_conn.select(element=els,
            where="keV < %3.5f" % max_keV,
            analytical=True, order_by="e.Z")
        ls=list(ls)
        if pb: pb()

        ls1=[]
        ls2=[]
        i=0
        lls=len(ls)
        print lls
        while i<lls:
            l=ls[i]
            z=l.Z
            lp=l
            ls1.append(l)
            i+=1
            if i<lls:
                l=ls[i]
            else:
                ls2.append(lp)
                break
            if l.Z!=z:
                ls2.append(lp)
            else:
                ls2.append(l)
                i+=1

        for l1, l2 in zip(ls1, ls2):
            print l1
            print l2
            print "-----"
            x0=self.keV_to_channel(wgt(l1,l2))
            if plot:
                print "Fitting line at x0=", x0
            p=self.iter_r_line(x0, plot=plot, fwhm=self.scale.peakes[0].fwhm, background=background)
            if p:
                ws.append((p, l1, l2))
        if pb: pb()
        if len(ws)<1:
            raise RuntimeError, 'not enough data to graduation, sorry'
        pprint.pprint(ws)
        pass
        _y=np.array([wgt(w[1],w[2]) for w in ws])
        _x0=np.array([w[0].x0 for w in ws])
        _diag=np.array([w[0].A for w in ws])
        def scale((k,b), x, y):
            return y-((x*k)+b)

        if pb: pb()
        k_scale, b_scale = op.leastsq(scale, [1., 0.], args=(_x0,_y),
            #diag=_diag)[0]
            )[0]

        print "K, B:", k_scale, b_scale

        self.scale.k=k_scale
        self.scale.b=b_scale
        self.scale.done=True
        self.scale.peakes.extend([w[0] for w in ws])
        self.calculate_fwhm(self.scale.peakes)

        return self.scale

    def calculate_fwhm(self, peakes, pb=None):
        pprint.pprint(peakes)
        _y=np.array([0.]+[w.fwhm for w in peakes])
        _x0=np.array([self.scale.peakes[0].x0]+[w.x0 for w in peakes])

        def scale((k,b), x, y):
            return y-((np.sqrt(x)*k)+b)

        k_scale, b_scale = op.leastsq(scale, [1., 0.], args=(_x0,_y))[0]

        print "FWHM scale:", k_scale, b_scale
        if pb: pb()

        self.scale.fwhm.k=k_scale
        self.scale.fwhm.b=b_scale
        self.scale.fwhm.done=True

        return self.scale.fwhm

    def keV_to_fwhm(self, keV):
        x0=self.keV_to_channel(keV)
        return np.sqrt(x0)*self.scale.fwhm.k+self.scale.fwhm.b

    def invalidate_background(self):
        self.bkg=None

    def approx_background(self, elements, plot=False,
            sw=((3.9, 0.2), (3.18, 0.)), s=9e7,
                deeping=1., noice=000, relax=0.9,
                pb=None,
                proceed=True,
                iters=10):
        if not proceed:
            return
        #if self.bkg!=None:
        #    print "Cached"
        #    return self.bkg
        if not elements:
            return
        max_keV=self.channel_to_keV(len(self.channels))
        els=elements # sorted(list(elements))
        ls=self.line_db_conn.select(element=els,
            where="keV < %3.5f" % max_keV,
            order_by="e.Z")
        if pb: pb()
        ls=list(ls)
        xl=len(self.channels)
        ws=np.ones(xl)
        deeper=np.zeros(xl)
        for _deep_count in range(iters):
            for _s, w in sw:
                for l in ls:
                    x0=self.keV_to_channel(l.keV)
                    fwhm=self.keV_to_fwhm(l.keV)
                    hwidth=fwhm*_s/2.
                    xmin,xmax=self.cut(x0, hwidth, xl)
                    ws[xmin:xmax]=w

            for _x in self.x:
                if deeper[_x]:
                    ws[_x]=deeper[_x]

            deeper*=relax
            ws[:233]=1.

            if plot:
                self.fig.plot(self.x, ws*max(self.channels)/3., color=(1,0,0), alpha=0.3)


            nx=[]
            ny=[]
            nw=[]

            for _x in self.x:
                if ws[_x]:
                    nx.append(_x)
                    ny.append(self.channels[_x])
                    nw.append(ws[_x])


            spline=ip.splrep(nx,ny,nw, k=3, s=s)
            ys=ip.splev(self.x,spline)
            y=np.array(self.channels)
            for _x in self.x:
                if ys[_x]<0:
                    ys[_x]=0.
                if ys[_x]+noice>y[_x]:
                    deeper[_x]=deeping

            if plot:
                self.fig.plot(self.x, ys, color=(1,0,1), linewidth=3., alpha=0.3)
            if pb: pb()

        self.bkg=ys
        return ys


    def iter_r_line(self, x0, A=None, fwhm=None, bkg=0.,
        task=None, plot=False, background=True):
        xorig=int(x0)
        Xopt=self.peake_cache.get(xorig, None)
        if Xopt != None:
            return Xopt
        if background:
            background=1
        else:
            background=0
        b=background
        if task == None:
            task=(
                ([1,1,1,0,0], 1e-8, False, 1000, 1.5),
                ([1,1,0,b,b], 1e-8, False, 2000, 2.0),
                ([1,1,1,b,b], 1e-8, True, 6000, 2.5),
            )
        if A == None:
            A=self.active_channels[int(x0)]
        slope=0.
        #X=[x0, A, fwhm, bkg, slope]
        fail_iter=False
        for step in range(len(task)):
            if fail_iter:
                break
            mask, xtol, _plot, iters, s_fwhm=task[step]
            try:
                if fwhm == None:
                    fwhm=10
                width=fwhm
                Xopt=self.r_line(x0, A=A,
                    fwhm=fwhm,
                    width=width, plot=_plot and plot,
                    raise_on_warn=True, iters=iters,
                    mask=mask, xtol=xtol
                    )
            except FittingWarning, w:
                print "Fit Warning step", step
                fail_iter=True
                continue
            x0=Xopt.x0
            A=Xopt.A
            fwhm=Xopt.fwhm
            bkg=Xopt.bkg
        if not fail_iter:
            self.peake_cache[int(x0)]=Xopt
            self.peake_cache[int(xorig)]=Xopt
            return Xopt
        return


    def calc_fwhm_scale(self, plot=False, pb=None):
        scale=self.calc_scale

    def nearest_peake(self, x0, peaks):
        dpeaks=np.abs(peaks-x0)
        i = np.argmin(dpeaks)
        return peaks[i]

    def scan_peakes_cwt(self, plot=False, force=False):

        if self.cwt.done and not force:
            return self.cwt

        scale=self.calc_scale(plot=plot)
        ws=scale.peakes
        zero_fwhm, tube_fwhm = [w.fwhm for w in ws]
        zero_x0, tube_x0 = [w.x0 for w in ws]

        a,b=zero_fwhm*0.5, tube_fwhm*1.1
        _wsmin=a
        _wsmax=b
        scan_num=int((b-a)*2)+1
        fwhm_widths=np.linspace(a, b,scan_num)

        def get_fwhm_cwt(cwt_data, peak, fwhm):
            wl, xl=cwt_data.shape
            pmin,pmax=self.cut(peak,1, xl)
            wc=np.argmax(cwt_data[:,peak], axis=0)
            return peak, fwhm[wc]

        cwt_fwhms=OrderedDict()
        y=np.array(self.active_channels)
        peaks,cwt_field=sig.find_peaks_cwt1(y, fwhm_widths, min_snr=0.5,
            max_distances=fwhm_widths)

        for peak in peaks:
            x0, fwhm=get_fwhm_cwt(cwt_field, peak, fwhm_widths)
            cwt_fwhms[peak]=fwhm

        self.cwt.field=cwt_field
        self.cwt.peakes=cwt_fwhms
        self.cwt.done=True
        return self.cwt

    def calculate(self, plot=False, pb=None):
        self.calc_scale(plot=plot, pb=pb)
        self.calc_fwhm_scale(plot=plot, pb=pb)
        return

    def model_spectra(self, elements, plot=False, bkg=None):
        if bkg==None:
            bkg=lambda x: 0
        y=np.array(self.channels)
        ly=len(y)
        x=np.arange(ly)
        x=self.channel_to_keV(x)

        print "x:", x

        max_keV=max(x)

        ls=self.line_db_conn.select(element=elements,
            where="keV < %3.5f" % max_keV,
            order_by="e.Z")
        lines=list(ls)

        const, exp, ampc=self.gen_equation(elements=elements, lines=lines, x=x)
        s_fun="""
def approx_func(Params, x):
    %s = Params
    _1 = %s
    return _1
""" % (','.join(const), '\n    '.join(exp))
        amp=y[ampc]
        print s_fun
        ast=compile(s_fun, '<string-gen>', 'exec')
        print repr(ast.co_code)
        asd

    def gen_equation(self, elements, lines, x):
        const=[]
        sum=[]
        ampc=[]
        for line in lines:
            rel=line.rel
            keV=line.keV
            c_name="C_"+line.element+"_"+line.name[0]
            fwhm=self.keV_to_fwhm(line.keV)
            sum.append("%s*%f*gauss(x,%f,%f)+ \\" % (c_name, rel, keV,fwhm))
            #sum.append("%s*%f*gauss(x,%f,%f)+ \ # %s" % (c_name, rel, keV,fwhm, line))
            if not c_name in const:
                const.append(c_name)
            ampc.append(self.keV_to_channel(keV)) # initial state approx

        sum.append('0.')

        #sum='\n'.join(sum)

        return const, sum, ampc


    def trash(self):

        print "FWHM interval:", zero_fwhm, tube_fwhm
        a,b=zero_fwhm*0.5, tube_fwhm*1.1
        _wsmin=a
        _wsmax=b
        scan_num=int((b-a)*2)+1
        fwhm_widths=np.linspace(a, b,scan_num)
        # print "widths",fwhm_widths

        #We need to interpolate 9 points near found maxima to find the real maxima.

        def get_fwhm_cwt(cwt_data, peak, fwhm):
            #print ">>>", fwhm
            wl, xl=cwt_data.shape
            pmin,pmax=self.cut(peak,1, xl)
            #print cwt_data[:,pmin:pmax]
            wc=np.argmax(cwt_data[:,peak], axis=0)
            #print wc, fwhm[wc]
            return peak, fwhm[wc]

        def nearest_peake(x0, peaks):
            dpeaks=np.abs(peaks-x0)
            i = np.argmin(dpeaks)
            return peaks[i]

        cwt_fwhms={}
        ws=[]
        bad_ws=[]
        for iter_num in range(6):
            print "Start ITERATION:", iter_num
            peaks,cwt_field=sig.find_peaks_cwt1(y, fwhm_widths, min_snr=0.5,
                max_distances=fwhm_widths)

            # np.savetxt("ctw.txt", cwt_field)

            for peak in peaks:
                x0, fwhm=get_fwhm_cwt(cwt_field, peak, fwhm_widths)
                print "x0, fwhm=", x0, fwhm
                cwt_fwhms[peak]=fwhm

            #return

            # bisplrep(x, y, z[, w, xb, xe, yb, ye, kx, ...])	Find a bivariate B-spline representation of a surface.
            # bisplev(x, y, tck[, dx, dy])	Evaluate a bivariate B-spline and its derivatives.

            for pike in peaks:
                p.axvline(x[pike], color=(0,1,1), linewidth=1.)

            #heights=[(y[i], i) for i in peaks]
            #heights.sort()
            #heights.reverse()

            #print "NEAREST to Zero is ", nearest_peake(zero_x0,peaks), ' to ', zero_x0
            #print "NEAREST to Tube is ", nearest_peake(tube_x0,peaks), ' to ', tube_x0


        #for i in peaks:
        #    _x=x[i]
        #    p.axvline(_x, color=(0,0,0))
        #print Xopt, "square:", gauss_square(Xopt.A, Xopt.fwhm)

            fwhm_guess=zero_fwhm
            peaks.sort(key=lambda peak:y[peak])
            peak_rec=False
            for pp in peaks:
                if pp in bad_ws:
                    continue
                try:
                    cwt_b=int(fwhm_guess-_wsmin)
                    cwt_guess=cwt_field[cwt_b][pp]
                    print "Cut: [",pp,']'
                    for _il, _l in enumerate(cwt_field):
                        print _il+_wsmin,':',_l[pp-2:pp+2],
                    print
                    y_guess=y[pp]
                    print "GUESS: y[pp]", y_guess, "CWT:", cwt_guess, "FWHM:", cwt_fwhms[pp]
                    print "Ratio:", y_guess/(cwt_guess/cwt_fwhms[pp])
                    Xopt=self.r_line(x[pp], A=y[pp],
                        fwhm=cwt_fwhms[pp], width=cwt_fwhms[pp]*S_fwhm,
                        plot=False, raise_on_warn=True,
                        mask=[0,1,0,1,0],
                        # account_bkg=[0,0],
                        iters=6000)
                except FittingWarning, w:
                    print "FITWARN!!!!"
                    bad_ws.append(pp)
                    continue
                try:
                    Xopt=self.r_line(Xopt.x0, Xopt.A,
                        fwhm=Xopt.fwhm, width=Xopt.fwhm*S_fwhm,
                        bkg=Xopt.bkg,
                        plot=True, raise_on_warn=True,
                        mask=[1,1,1,1,1],
                        # account_bkg=[0,0],
                        iters=6000)
                except FittingWarning, w:
                    print "FITWARN!!!!"
                    bad_ws.append(pp)
                    continue
                if Xopt.bkg<-5: # FIXME: WHY it is less than -5???
                    bad_ws.append(pp)
                    continue
                if Xopt.x0+Xopt.fwhm/2.>=xl: # Line is not on the spectrum
                    bad_ws.append(pp)
                    continue
                if Xopt.x0-Xopt.fwhm/2.<=0: # Line is not on the spectrum
                    bad_ws.append(pp)
                    continue
                if Xopt.A<0:
                    bad_ws.append(pp)
                    continue
                ws.append(Xopt)
                cwt_fwhms[pp]=Xopt.fwhm
                peak_rec=True
                sub_line(y, Xopt)
            if not peak_rec:
                break

            p.plot(x,y, color=(0,0,0))

        print "Stop ITERATIONs at:", iter_num
        B_fwhm1=4. # 7.
        B_fwhm2=4.

        omega=np.ones(xl)

        cwt_fwhms[1895]=20.
        cwt_fwhms[1994]=20.
        cwt_fwhms[1932]=20.
        cwt_fwhms[2245]=20.

        for x0, fwhm in cwt_fwhms.iteritems():
            if x0 in bad_ws:
                continue
            xmin,xmax=self.cut(x0, fwhm*B_fwhm1/2., xl)
            omega[xmin:xmax]=0.005
        for x0, fwhm in cwt_fwhms.iteritems():
            if x0 in bad_ws:
                continue
            xmin,xmax=self.cut(x0, fwhm*B_fwhm2/2., xl)
            omega[xmin:xmax]=0.0

        omega[:233]=1.

        nx=[]
        ny=[]
        no=[]

        for _x in x:
            if omega[_x]:
                nx.append(_x)
                ny.append(self.active_channels[_x])
                no.append(omega[_x])


        spline=ip.splrep(nx,ny,no, k=3, s=1e7)
        ys=ip.splev(x,spline)
        for _x in x:
            if ys[_x]<0:
                ys[_x]=0.

        p.plot(x, ys, color=(1,0,1), linewidth=3., alpha=0.3)
        p.plot(x, omega*100000, color=(1,0,0))

        #p.plot(x,y, color=(0,1,0))
        p.plot(x,self.active_channels, color=(1,0,0))


        print "WS:"
        pprint.pprint(ws)

        p.show()
        return

        ws.sort(key=lambda x:x.fwhm)
        fwhm_guess_min=ws[0].fwhm
        fwhm_guess_max=fwhm_guess_min*4.
        print "LIMITS:", fwhm_guess_min, fwhm_guess_max
        ws=[l for l in ws if l.fwhm <= fwhm_guess_max] # filter out big fitted lines.

        ws.sort(key=lambda x: x.fwhm)
        fwhm_min=ws[0].fwhm
        fwhm_max=ws[-1].fwhm


        _y=np.array([_.fwhm for _ in ws])
        _x0=np.array([_.x0 for _ in ws])
        _x0-=_x0[0]
        _y[0]=0.
        print "X FWHMs:", _x0
        print "Y FWHMs:", _y
        def ffwhm(k, x):
            return _y-((np.sqrt(x)*k))

        k_fwhm = op.leastsq(ffwhm, [1.], args=_x0)[0]

        print (k_fwhm) # , b_fwhm, c_fwhm)

        def x0_to_fwhm(x0):
            return np.sqrt(x0-_x0[0])*k_fwhm

        print "F FWHMs:", x0_to_fwhm(_x0)

        for l in ws:
            p.axvline(l.x0, color=(0,1,0))

        p.plot(x, np.zeros(xl))

        y_bkg=np.array(self.active_channels)
        _ = np.array(y_bkg)

        print "Bkg processing"

        max_count=20
        for count in range(max_count):
            cmc=(float(max_count-count)/(max_count))
            x_mi=168
            w=int(0.25+x0_to_fwhm(x_mi)*cmc)
            x_ma=x_mi+w*2
            x_c=int((x_mi+x_ma)/2.)
            while 1:
                w=int(0.25+x0_to_fwhm(x_c)*cmc)
                x_mi=x_c-w
                x_ma=x_c+w
                if x_ma >= xl:
                    break
                y_mi=y_bkg[x_mi]
                y_ma=y_bkg[x_ma]
                y_c =y_bkg[x_c]
                y_a=(y_mi+y_ma)/2
                if y_c > y_a:
                    _[x_c]=y_a
                x_c+=1
            y_bkg[:]=_[:]
        p.plot(x, y_bkg, color=(0,0,float(count)/max_count))

        # spline again

        print "Spline:"
        y=np.array(y_bkg)
        w=np.zeros(xl)+1.
        for _i in x:
            if y[_i]>0:
                w[_i]=1./y[_i]
            else:
                w[_i]=0.
        xmin=163
        w[:xmin]=0.
        w0=np.array(w)
        miter=50
        for iter in range(miter):
            spline=ip.splrep(x,y,w)
            ys=ip.splev(x,spline)
            #ya=sum(ys*ys*w)
            dy=y-ys
            le=np.less_equal(dy, 0.)
            for _i in x:
                dy=y[_i]-ys[_i]
                if dy<0:
                    w[_i]=1./-dy
                elif abs(dy)>1000:
                    w[_i]=0.
                else:
                    w[_i]=w0[_i]
            c=float(miter-iter)/miter
            p.plot(x, ys, color=(c,c,c), linewidth=1)
            #print "Iter ", iter, c

        """
        p.plot(x, self.channels-y_bkg, color=(0.5,0.5,0))
        # Repeat the recognition procedure again? or split the Compton pike?

        peaks=sig.find_peaks_cwt(self.channels-y_bkg,
            np.linspace(fwhm_min, fwhm_max, 20), min_snr=0.6)

        pprint.pprint(peaks)
        print len(peaks)+1

        for pi in peaks:
            xp=x[pi]
            yp=y[pi]

            p.axvline(xp, color=(1, 0, 1))
        """

        p.plot(x, self.active_channels, color=(1,0,0))

        #p.subplot(212)
        #p.imshow(cwt_field)

        p.show()



        return

        #Some recognition parameters.
        mm=3.5
        c1_fwhm=2.5
        c2_fwhm=3.5

        # Find a maximum in the spectrum, recognize it as line, split it from soectrum, repeat some times to collect lines.
        Xl=Xopt
        max_lines=200
        for __ in range(5):
            f_lines=[Xopt]
            while True:
                mx = np.argmax(y)
                try:
                    Xl=self.r_line(mx, A=None, fwhm=Xl.fwhm, width=Xopt.fwhm*c1_fwhm,
                        plot=False, account_bkg=[0,0], iters=2000, raise_on_warn=True,
                        channels=y)
                except FittingWarning, w:
                    if w==1:
                        break

                if y[int(Xl.x0+0.5)] - Xl.A < -Xl.A/5.:
                        break
                sub_line(y, Xl, s=S_fwhm)
                #x0, A, fwhm, b, k =list(Xl)
                #xmin1,xmax1=self.cut(Xl.x0, Xl.fwhm*S_fwhm/2., xl)
                #nxw=np.arange(xmin1, xmax1, 0.125)
                #fy=gauss(nxw, Xl.x0, Xl.A, Xl.fwhm)+(nxw-x0)*k+b
                #p.fill_between(nxw,fy,(nxw-x0)*k+b, color=(0.1,0.1,0.9), alpha=0.5)
                xtmp=Xl.x0
                #fy=gauss(nxw, Xl.x0, Xl.A, Xl.fwhm)
                #p.plot(nxw,fy, color=(0.7,0.3,1), alpha=0.5)
                f_lines.append(Xl)
                max_lines-=1
                if max_lines==0:
                    break
            def _fwhm_s(a,b):
                return -int(b.fwhm-a.fwhm)

            f_lines.sort(_fwhm_s)
            if f_lines[-1].fwhm>f_lines[0].fwhm*1.8:
                del f_lines[-1]

            y=np.array(self.active_channels)
            fy=np.zeros(xl, dtype=float)
            w=np.zeros(xl, dtype=float)+1.
            for l in f_lines:
                sub_line(y, l, s=S_fwhm)
                fy=fy+gauss(x, l.x0, l.A, l.fwhm)
                _w=int(l.fwhm*S_fwhm/2.+0.5)
                xmin, xmax = self.cut(l.x0, _w, xl)
                w[xmin:xmax]=0.
            # cut first zero pike and its plato
            xp1=x[Xopt.x0*2:]

            p.plot(x,fy, color=(1,0.1,0.1))

            y=np.array(self.active_channels)
            spline=ip.splrep(xp1,y[Xopt.x0*2:],w[Xopt.x0*2:], k=3, s=5e8)
            ys=ip.splev(x,spline)
            p.plot(x, ys)
            ym=self.channels-ys
            for _i, _ in enumerate(ym):
                if _ <0: ym[_i]=0.
            p.plot(x, ym, color=(1,0,1), linewidth=__+1)
            y=ym

        p.plot(x,self.channels, color=(0,0.6,0.), linewidth=3.)
        pprint.pprint(f_lines)
        print len(f_lines)
        if DEBUG:
            p.show()

        return

        e_fe= 6.4
        e_zr= 15.774
        p.plot(x,y)
        p.plot(x,x*0.)
        x00, _, fwhm_0, b0, k0= r_line(80, width=len(x)/50, plot=True)
        print "FWHM0:", fwhm_0
        #fwhm_0=100
        w=15*fwhm_0/2.
        #x0_fe, _, fwhm_fe, b_fe, k_fe = recog(1370, fwhm=fwhm_0, width=w) # Fe
        x0_fe, _, fwhm_fe, b_fe, k_fe = r_line(1350, fwhm=fwhm_0, width=w, plot=True) # Fe
        s_k=(e_fe-e_0)/(x0_fe-x00)
        s_b=e_fe - (s_k*x0_fe)
        print "Scale:", s_k, s_b
        def to_chan(e):
            return (e-s_b)/s_k
        x0_mo=to_chan(e_mo)
        x0_zr=to_chan(e_zr)
        r_line(1000, fwhm=fwhm_0, width=w, plot=True)
        #recog(3255, fwhm=fwhm_0, width=w/2.)
        #recog(x0_mo, fwhm=fwhm_0, width=w, plot=True)

        def ffwhm(k, x):
            return _y-np.sqrt(x)*k

        k = op.leastsq(ffwhm, [1], args=np.array([e_0, e_fe]))

        fwhm_zr=k[0]*math.sqrt(e_zr)
        fwhm_mo=k[0]*math.sqrt(e_mo)

        #X=r_line(2920, fwhm=fwhm_0, width=w)
        #fwhm_X=math.sqrt((X[0]-b_fwhm)/k_fwhm)
        #r_line_fix(X[0], fwhm=fwhm_zr, width=w, plot=True)

        #r_line(1821, fwhm=fwhm_0, width=w, plot=True)
        print "fwhm:", fwhm_zr, k

        gain=1/s_k
        return

        r_line_zr(x0_zr, fwhm=fwhm_zr, width=fwhm_zr*1.1, plot=True)
        Xtry = _, A_mo, _,a0,a1 = r_line_zr(x0_mo, fwhm=fwhm_mo, width=fwhm_zr*1.1, plot=True)
        print "Releigh pike:", Xtry
        #p.show()
        #Coumpton Pike
        angle=90-2 #(degrees)
        rangle=angle*math.pi/180
        m0=510.996
        #E0=e_mo
        #Ec=E0 #seq(15.0,17.415, by=0.1)
        #DE=(E0*Ec/m0)*(1-math.cos(rangle))
        #print "DE:", DE

        E=e_mo
        E_prime=E/(1+(1-math.cos(rangle))*E/m0)

        #x0_coumpton=to_chan(e_mo-DE)
        x0_coumpton=to_chan(E_prime)
        #p.plot(x, 6000000*Gc(x,x0_coumpton, fwhm=fwhm_mo, fg=2.))
        #p.plot(x, 3000000*T(x,x0_coumpton, fwhm=fwhm_mo, g=2))
        #p.plot(x, 3000000*T(x,x0_coumpton, fwhm=fwhm_mo, g=2, mult=-1))

        xmin,xmax=3100,3750

        """
        y1=y+0.
        Xtry[-1]=Xtry[-2]=0.
        y1[3514:3640]=y1[3514:3640]-ofp(Xtry, x[3514:3640])
        y2,y=y,y1
        p.plot(x, y)
        """

        #Xopt=[A, fg, fa, fb, ga, gb]=cou_fmin(x, x0_coumpton,
        #    fwhm_mo, xmin=xmin, xmax=xmax)
        #p.plot(x[xmin:xmax], cou_approx(A, x[xmin:xmax], x0_coumpton, fwhm_mo,
        #    fg, fa, fb, ga, gb)+ofp(Xtry, x[xmin:xmax])) # Need a common amplitude
        #p.plot(x, cou_approx(2.3e6, x, x0_coumpton, fwhm_mo,
        #    2.0, 1, 1, 10, 9, 0.,x0_mo)) # Need a common amplitude
        Xopt_cou=[A_mo, x0_cou, A_cou, fwhm_co, bkg_cou, shift, c2, a3, b, c, x0_mo]=cou_sim_fmin(
            [A_mo, x0_coumpton, A_mo, fwhm_mo*2.5, 0., 1., 1., 1., 1., 1., x0_mo],
                x0_mo, fwhm_mo, xmin=xmin, xmax=xmax)
        xmin-=300
        xmax+=300
        print "Coumpton group:", Xopt_cou
        _cs=cou_sim(A_mo, x0_cou, A_cou, fwhm_co, bkg_cou, shift, c2, a3, b, c, x0_mo, fwhm_mo, x[xmin:xmax])
        p.plot(x[xmin:xmax], _cs) # Need a common amplitude

        y1=y+0.
        Xtry[-1]=Xtry[-2]=0.
        y1[xmin:xmax]=y1[xmin:xmax]-_cs+bkg_cou
        y2,y=y,y1
        p.plot(x, y)
        r_line_zr(x0_zr, fwhm=fwhm_zr, width=fwhm_zr*1.1, plot=True)

        p.show()



    def cut(self, x0,hw, xl):
        ix0=int(math.floor(x0+0.5))
        ihw=int(math.floor(hw))
        xmin=ix0-ihw
        if xmin<0:
            xmin=0
        xmax=ix0+ihw+1 # +1 as it will be used in [...:...] operation.
        if xmax>=xl:
            xmax=xl
        #print xmin,xmax
        return xmin,xmax

    def split_args(self, X, mask):
        if len(X)!=len(mask):
            raise ValueError, 'vector X and mask must be of the same length'
        nx=[]
        nf=[]
        for x, m in zip(X, mask):
            if m:
                nx.append(x)
            else:
                nf.append(x)
        return nx, nf

    def join_args(self, X, fix, mask):
        args=[]
        xi=0
        fi=0
        for m in mask:
            if m:
                args.append(X[xi])
                xi+=1
            else:
                args.append(fix[fi])
                fi+=1
        return args


    def r_line(self, x0, A=None, fwhm=10, bkg=0, xtol=1e-2, width=None,
            plot=False, account_bkg=None,
            mask=[1,1,1,0,0], iters=10000, channels=None,
            raise_on_warn=False):

        def _gauss(x0, A, fwhm, b, k, xw):
            return gauss(xw, x0, A, fwhm)+b+k*(xw-x0)

        def of(*args):
            #x0,A, fwhm,b,k =X
            _= apply(_gauss, args)
            return _

        def fopt(X, *args):
            mask, fix, rest=args
            xw,yw=list(rest)
            fargs=self.join_args(X, fix, mask)+[xw]
            #print fargs
            _=apply(of, fargs)
            return sum((yw-_)**2)

        if width == None:
            width=fwhm
        hw=width/2.
        if channels != None:
            y=channels
        else:
            y=self.channels
        x=self.x
        xl=len(y)

        xmin,xmax=self.cut(x0, hw, xl)
        if A == None:
            A=max(y[xmin:xmax])
            #print A
        X0=[x0, A, fwhm, bkg,0]
        m=list(mask)
        if account_bkg != None:
            m[-2:]=account_bkg
        X,F=self.split_args(X0, m)
        #print X,F, mask, X0
        xw=x[xmin:xmax]
        yw=y[xmin:xmax]
        Xopt, fval, iterations, fcalls, warnflag =op.fmin(fopt, X, args=(m,F,[xw,yw]),
            xtol=xtol, maxiter=iters,
            maxfun=iters,
            disp=False, full_output=1)
        if warnflag and raise_on_warn:
            raise FittingWarning, warnflag
        Xopt=Pike._make(self.join_args(Xopt, F, m)+[fval])
        while plot:
            if Xopt.A>A*2 or Xopt.x0<0 or Xopt.fwhm<0 or Xopt.fwhm>xl/20:
                return Xopt
            xmin1,xmax1=self.cut(Xopt[0], hw, xl)
            x0, A, fwhm, b, k, chisq =list(Xopt)
            try:
                nxw=np.arange(xmin1, xmax1, 0.25)
            except ValueError:
                break
            fy=apply(of, list(Xopt)[:-1]+[nxw])
            p.fill_between(nxw,fy,(nxw-x0)*k+b, color=(0.7,0.3,0), alpha=0.5)
            #p.fill_between(nxw,fy,b, color=(0.7,0.3,0), alpha=0.5)
            break
        return Xopt

    def ofp(self, X, xw):
        x0,A, fwhm, a0, a1 =X
        dxw=(xw-x0)
        _=gauss(xw, x0, A, fwhm)+a0+a1*dxw
        return _

    def r_line_zr(self, x0, A=None, fwhm=None, xtol=1e-8, width=None, plot=False):

        def fopt(X, x0, fwhm, xw, yw):
            A, a0, a1 = X
            X=[x0, A, fwhm, a0, a1]
            _=ofp(X, xw)
            return sum((yw-_)**2)

        if fwhm==None:
            raise ValueError, "fwhm should be defined"
        if width == None:
            width=fwhm
        hw=width/2.
        xmin,xmax=cut(x0, hw)
        if A == None:
            A=max(y[xmin:xmax])
            #print A
        X0=[A, 0,0]
        xw=x[xmin:xmax]
        yw=y[xmin:xmax]
        Xopt=op.fmin(fopt, X0, args=(x0, fwhm, xw,yw), xtol=xtol, maxiter=10000, maxfun=10000)
        A, a0, a1 =Xopt
        nxw=np.arange(xw[0], xw[-1], 0.25)
        Xopt=[x0, A, fwhm, a0, a1]
        fy=ofp(Xopt, nxw)
        ffy=ofp([x0,A,fwhm,a0,0.], x)
        if plot:
            dnxw=nxw-x0
            p.fill_between(nxw,fy,a0+a1*dnxw, color=(0.7,0.3,0), alpha=0.5)
            p.plot(x,ffy, color=(0.7,0.0,0.3), alpha=0.5)
        return Xopt

    def Gc(self, E, E0, fwhm, fg):
        sigma = fwhm/fwhm_coef
        _1=sigma*fg
        _ = (sqrt_2pi*_1)
        _ = 1/_
        dE=E-E0
        _x= -((dE/_1)**2)/2.
        return _*np.exp(_x)

    def T(self, E, E0, fwhm, g, mult=1.):
        sigma = fwhm/fwhm_coef
        dE=E-E0
        _ef=math.exp(-1/(2*g**2))
        _0=g*sigma
        _1=2*_0*_ef
        _exp1=np.exp(mult*dE/_0)/_1
        _x=mult*dE/(sqrt_2*sigma)+1./(sqrt_2*g)
        return _exp1*fn.erfc(_x)

    def cou_approx(self, A, E, E0, fwhm, fg, fa, fb, ga, gb):
        #print (E, E0, fwhm, fg, fa, fb, ga, gb)
        _  = 0.0
        _ += Gc(E, E0, fwhm, fg)
        #_ += fa*T(E, E0, fwhm, ga)
        #_ += fb*T(E, E0, fwhm, gb, mult=-1)
        return A*_ #+ ofp([x0_mo, A_mo, fwhm, a0, a1], E)

    def cou_opt(self, X,  Ew, E0, fwhm, yw):
        #print X
        A, fg, fa, fb, ga, gb = X
        return sum((cou_approx(A, Ew, E0, fwhm, fg, fa, fb, ga, gb)-yw)**2)

    def cou_fmin(self, E, E0, fwhm, X0=None, xtol=1e-3, xmin=0, xmax=None):
        if X0 == None:
            X0 = [1., 1, 1., 1., 1, 1]
        if xmax == None:
            xmax=len(E)
        Ew=E[xmin:xmax]
        yw=y[xmin:xmax]
        return op.fmin(cou_opt, X0, args=(Ew, E0, fwhm, yw), xtol=xtol, maxiter=10000, maxfun=10000)

    def cou_sim(self, A_mo, x_cou, A_cou, fwhm_cou, bkg,  shift, c2, a3, b, c, x_mo, fwhm_mo, xw):
        _  = 0.0
        _ += gauss(xw, x_mo, A_mo, fwhm_mo)
        _ += gauss(xw, x_cou-shift, A_cou, fwhm_cou)
        _ += gauss(xw, x_cou+shift, c2*A_cou, fwhm_cou)
        #_ += a3*(arccot(b/(x_mo-xw))+arccot(b/(x_mo+shift-xw)))
        _ += a3*arccot(-shift*b-(xw-x_cou))-c*arccot(shift*b-(xw-x_cou))
        _ += bkg
        return _

    def cou_sim_opt(self, X, fwhm_mo, xw, yw):
        A_mo, x_cou, A_cou, fwhm_cou, bkg, shift, c2, a3, b, c, x_mo = X
        _ = cou_sim(A_mo, x_cou, A_cou, fwhm_cou, bkg, shift, c2, a3, b, c, x_mo, fwhm_mo, xw)
        _ = sum((_-yw)**2)
        return _

    def cou_sim_fmin(self, X, x_mo, fwhm_mo, xmin=0, xmax=None, xtol=1e-8):
        if xmax == None:
            xmax=len(E)
        xw=x[xmin:xmax]
        yw=y[xmin:xmax]
        return op.fmin(cou_sim_opt, X, args=(fwhm_mo, xw, yw),
            xtol=xtol, maxiter=10000, maxfun=10000)

    REL_INT={
            "KA1":100,
            "KA2":50,
            "KB1":20,
            "KB3":10,

            "LA1":100,
            "LA2":12,
            "LB1":50,
            "LB2":20,
            "LB3":8,
            "LG1":10,

        }

    REL_NC=5

    def line_plot(self, lines, options):
        if not options.get('show-lines', True):
            return
        fig=self.fig
        ym=0.8
        #L1={'A':ym, "B":ym * 0.6, "G":ym*0.3}
        #L2={'K':(0,0,1), "L":(0,0,0.5)}
        L2={'K':'black', "L":'red', "M":'green'}

        self.calc_scale()
        channels=[]
        chmax = max(self.active_channels)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8, linewidth=0)
        lc=len(self.active_channels)
        k=options.get('k',True)
        l=options.get('l',True)
        m=options.get('m',False)
        anl=options.get('analytical',False)
        for line in lines:
            if not k and line.name.startswith('K'):
                continue
            if not l and line.name.startswith('L'):
                continue
            if not m and line.name.startswith('M'):
                continue
            if anl:
                if line.name[1] != "A":
                    continue
                if line.Z<=50 and line.name.startswith('L'):
                    continue
                if line.Z>50 and line.name.startswith('K'):
                    continue

            #print line
            ch = self.keV_to_channel(line.keV)
            channels.append(ch)
            lname=line.name
            col=L2[lname[0]]
            #ri=self.REL_INT.get(lname, self.REL_NC)
            ri=line.rel
            #ymax=L1[lname[1]]
            fig.axvline(ch, ymax=ym*ri/100., color=col)
            if ch>lc:
                continue
            y=self.active_channels[ch] * 1.
            #if y < 0.3 * chmax:
            #    y=chmax
            fig.text(ch, y, "%s %s"  % (line.element, line.name),
                horizontalalignment='right',
                verticalalignment='bottom',
                family='monospace', size=8,
                alpha=0.6, bbox=props)
        return channels














def test1():
    import matplotlib.pyplot as p
    if os.name!="nt":
        ldb=lines.Lines(dbname='/home/eugeneai/Development/codes/dispersive/data/lines.sqlite3')
    else:
        ldb=lines.Lines(dbname='C:\\dispersive\\data\\lines.sqlite3')
    if 1: #list of test data channels
        channels=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 ,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,2,3,5,8,19,     37,57,110,201,331,602,1006,1683 ,2646,4283,6783,10382,15344,22612,32871,     45971,63336,85157,112676,144016,183174,226837, 275037,324926,376696,428399,     474959,515910,548642,570915,581400,579176,565419,538934,505254, 461770,     414213,363708,312642,263381,217939,176157,139385,108892,83128,61869,45213,     32574 ,22949,15943,10889,7380,4810,3253,2117,1347,976,638,418,323,204,188,     159,141,97,94,83,90,75 ,74,70,57,62,63,75,55,64,34,29,36,27,21,22,16,12,     27,41,37,45,49,37,49,49,84,80,90,154,293 ,638,1374,2277,3247,3821,4012,     3927,3855,3869,3845,3804,3830,3664,3667,3777,3823,3753,3643, 3558,3614,     3482,3457,3609,3542,3428,3452,3319,3393,3426,3346,3229,3312,3223,3258,     3243, 3193,3122,3092,3230,3150,3078,3121,3066,3194,3085,3033,3103,2919,     2902,3038,3121,2866,2951, 2906,2888,2983,2882,2850,2894,2940,2882,2842,     2771,2862,2847,2851,2859,2816,2766,2714,2831, 2719,2757,2810,2723,2713,     2657,2700,2725,2802,2684,2695,2691,2680,2694,2702,2638,2686,2588, 2609,     2653,2534,2605,2608,2579,2569,2624,2622,2525,2580,2578,2565,2640,2614,     2558,2562, 2516,2575,2538,2565,2514,2427,2574,2534,2582,2435,2421,2579,     2456,2484,2436,2384,2562,2390, 2411,2444,2414,2437,2317,2429,2376,2413,     2347,2330,2389,2431,2381,2371,2345,2399,2362,2460, 2423,2322,2348,2318,     2277,2258,2257,2215,2291,2310,2136,2279,2100,2125,2165,2155,2110,2061,      2127,2053,2035,2051,2075,1964,1962,1962,2028,2025,2086,2030,2058,1953,     1992,1970,2053, 2030,2018,1982,2048,2051,1915,2005,2011,2024,2035,1983,     1984,2011,1927,1928,1962,1982,1933, 1822,1908,1869,1891,1980,1897,1892,     1913,1849,2019,2038,2081,2052,2201,2292,2449,2722,2848, 3087,3435,3739,     4232,4698,5115,5805,6294,6984,7817,8285,9215,9612,10265,10762,11107, 11397,11539,11585,11485,11413,11112,10818,10480,9978,9461,8814,8145,     7864,7261,7063,6597, 6120,5824,5501,5286,5048,4717,4667,4578,4489,4594,     4638,4889,5255,5841,6563,7533,8858,10589 ,12603,15007,17943,21444,25399,     29728,34756,40006,45571,51301,56779,62070,67589,72754,77015, 80603,82682,     83931,84935,84480,83473,80914,77332,73071,68805,63644,58770,53293,47728, 42893,37443,32859,29090,25032,22040,18677,16320,14142,12538,10814,9553,     8635,7719,6851,6180, 5835,5144,4935,4759,4436,4241,4113,3948,4005,3913,     3876,3797,3739,3767,3746,3762,3551,3646, 3547,3552,3496,3476,3302,3230,     3143,3133,2981,2872,2830,2718,2697,2707,2492,2549,2441,2362, 2282,2237,     2150,2214,2086,2133,1993,1999,2019,1955,1828,1880,1848,1889,1825,1883,     1840, 1755,1718,1822,1646,1756,1788,1737,1732,1629,1682,1631,1706,1722,     1728,1748,1739,1663,1766, 1756,1761,1682,1812,1765,1754,1874,1809,1825,     1755,1824,1843,1808,1754,1774,1750,1766,1903, 1796,1740,1708,1717,1701,     1639,1704,1752,1712,1602,1701,1614,1631,1661,1633,1677,1625,1581, 1623,     1617,1625,1636,1582,1600,1628,1625,1589,1580,1648,1583,1564,1592,1519,     1599,1657, 1596,1598,1567,1633,1688,1656,1588,1591,1589,1701,1694,1735,     1682,1723,1701,1751,1809,1910, 1847,1838,1926,1890,1966,1998,2019,2017,     1901,2024,1983,1968,1966,1956,1939,1928,1937,1984, 1900,1832,1899,1956,     1924,1836,1903,1946,1973,1957,1953,2051,1960,1953,2019,1977,1964,2016,      1947,1995,2019,1979,2012,1960,2056,1962,1963,1986,1995,1921,1936,1879,     1827,1871,1899, 1880,1899,1809,1919,1848,1877,1852,1876,1909,1910,1929,     2086,1992,2188,2146,2142,2131,2084, 2225,2147,2127,2219,2271,2259,2285,     2263,2204,2168,2115,2151,2159,2094,2103,1994,2014,1948, 1971,2018,1952,     1917,2014,1963,2021,1857,1999,1982,2018,2012,2059,2069,2099,2137,2173, 2181,2214,2364,2442,2522,2616,2822,3152,3353,3737,4123,4704,5483,6301,     7434,8758,10371, 12037,14287,16829,20204,23741,27753,32321,37330,42397,     48679,54519,61426,68407,75284,81925, 88818,95139,101377,106392,110984,     114684,117829,119732,119976,119714,118406,115420,111845, 107262,101514,     96162,89506,83032,75387,69004,62465,54984,48873,42564,37661,31846,27707, 23633,20132,17132,14310,12154,10238,8846,7672,6659,5952,5450,5033,4894,     4779,4965,5148,5457 ,5838,6236,6847,7528,8474,9119,10153,11196,12524,     13895,15265,16646,18467,20479,22489,24838 ,27217,30123,33336,36433,40748,     44573,49188,53508,59492,64830,71255,77696,83567,90527,97050, 103143,109422,     114846,120182,124433,128548,130701,132814,132637,132333,131539,128022, 124166,119944,115248,108549,101801,95079,87876,80181,72321,65021,58187,     51734,45219,39529, 34086,29596,25072,21297,17662,15030,12621,10451,8765,     7566,6296,5375,4622,3994,3623,3338, 3168,3019,2963,3065,3061,3299,3614,     3563,4076,4381,4782,5202,5783,6457,7147,7807,8476,9415, 10250,10991,11957,     12926,13833,14615,15297,16154,16808,17560,17770,18109,18157,18342,18451,      17854,17837,17078,16610,16147,15275,14054,13365,12629,11398,10717,10014,     8846,8031,7190 ,6487,5882,5208,4515,4210,3690,3267,3008,2713,2427,2226,     2044,1878,1757,1706,1597,1592,1521 ,1412,1429,1346,1407,1385,1386,1342,     1365,1366,1425,1428,1387,1304,1392,1435,1334,1401,1494 ,1437,1499,1515,     1470,1614,1695,1641,1691,1871,1912,2067,2213,2426,2634,2889,3154,3545,      3960,4579,5048,5854,6645,7437,8680,9697,11061,12439,14091,16037,17444,     19398,21623, 23682,25559,27680,29667,32011,34128,35834,37527,38856,41119,     41379,42055,42299,42951,42888, 41962,41292,40570,39615,37550,35993,34197,     32387,30324,28645,26050,24065,22446,20491,18664, 16961,15249,14004,12634,     11437,10615,9996,9112,8449,7884,7353,7042,6515,6412,6093,5831,5566 ,5308,     5070,4736,4743,4598,4263,4308,4015,3929,3800,3844,3741,3733,3758,3756,     3819,3978 ,4098,4173,4423,4591,4890,5124,5170,5433,5749,6002,6119,6402,     6752,6838,7150,7315,7697,7683 ,8210,8194,8411,8418,8766,8755,8824,9316,     9391,9347,9663,9494,9572,9470,9577,9397,9381,8930 ,8790,8799,8545,8386,     8006,7676,7159,6827,6554,6221,5768,5499,5247,4806,4479,4209,3781,3715 ,     3446,3173,3018,2771,2597,2511,2421,2384,2297,2258,2187,2219,2233,2229,     2210,2203,2221 ,2302,2352,2320,2377,2456,2433,2433,2500,2449,2502,2451,     2506,2502,2564,2481,2521,2549,2502 ,2345,2457,2409,2432,2319,2413,2218,     2358,2323,2344,2320,2308,2352,2248,2337,2265,2180,2297 ,2184,2071,2223,     2235,2169,2166,2136,2242,2150,2104,2083,2100,2124,2081,2057,2130,2063,      2082,2040,1999,2038,1963,2018,2006,1880,2029,2033,2178,2015,2119,2073,     2096,2136,2114, 2096,2105,2176,2175,2161,2124,2222,2210,2150,2301,2229,     2331,2208,2278,2300,2268,2214,2138, 2254,2273,2185,2131,2125,2050,2060,     2125,1969,2036,2042,2026,1951,1913,1904,1956,1870,1884, 1906,1785,1907,     1943,1892,1781,1882,1964,2067,1947,2009,2076,2185,2216,2212,2284,2349, 2535,2660,2885,2966,3042,3428,3490,3972,4168,4674,4979,5325,5888,6334,     6893,7398,8138,8778, 9488,10231,11096,11595,12222,12856,13790,14385,14831,     15384,15922,16191,16514,16603,16918, 16960,16844,16634,16216,16028,15739,     15095,14406,14047,13017,12704,11662,11099,10368,9813, 8930,8418,7758,7305,     6841,6249,5924,5398,5062,4769,4467,4293,4189,3985,3846,3609,3629,3649,      3554,3495,3529,3481,3593,3542,3555,3665,3704,3833,3966,3926,4121,4248,     4307,4378,4631, 4886,5101,5375,5707,5996,6390,7071,7483,8226,9117,10424,     11884,13838,15550,18256,21663, 25321,29942,34933,41444,49066,57880,68104,     79097,93206,108467,125905,145302,167334,190234, 215787,243561,273199,     305256,338845,374630,410922,447619,483237,521626,558315,594427,626179,      658777,687807,714286,735083,753942,768135,775673,779820,776828,774598,     761417,747270, 727100,702896,676692,648849,613594,582254,544090,508350,     471945,433457,396586,361645,326468, 292739,260941,232228,205463,179433,     157424,136009,118031,101327,86412,73683,61835,52204, 44458,36845,31104,     25587,21165,17464,14641,12186,10135,8603,7178,6219,5488,4783,4156,3760,      3399,3246,3044,2841,2722,2618,2622,2597,2415,2371,2343,2358,2337,2420,     2323,2244,2332, 2318,2252,2318,2318,2331,2373,2427,2365,2428,2423,2441,     2590,2601,2564,2652,2751,2826,2836, 2938,3091,3157,3261,3491,3692,3802,     4038,4317,4604,4881,5410,5745,6143,6805,7512,8415,9355, 10347,11487,13033,     14368,16448,18217,20398,22655,25103,27986,31235,34530,38595,42181,46464,      50155,54478,59007,63727,68130,72736,77388,81520,85569,88531,92392,94732,     97444,99007, 101002,102329,102220,101955,101542,99811,98312,95524,92644,     89335,85911,81682,77613,73085, 68070,63993,58972,54656,50349,45765,41363,     37333,34125,29786,26653,23578,20667,18214,15789, 13963,11999,10409,8899,     7752,6463,5482,4735,4054,3477,2969,2463,2253,1836,1577,1363,1231, 1061,     997,925,874,761,739,692,665,649,605,636,558,552,591,595,558,562,562,     543,563,536, 526,572,571,593,581,580,547,539,561,541,578,586,550,561,     541,574,542,539,507,539,591,489, 506,517,476,493,462,486,454,454,465,     423,441,436,444,440,412,384,444,416,421,400,419,371, 390,384,433,404,     447,403,429,372,382,422,396,417,438,448,421,421,393,425,392,382,374, 398,409,389,413,409,406,442,424,441,398,417,379,445,435,436,463,418,     446,421,469,457,505, 470,477,477,495,470,463,538,511,574,526,526,491,     588,585,557,591,615,602,656,628,698,708, 714,765,793,844,862,898,932,     1024,1049,1102,1170,1147,1234,1273,1323,1348,1379,1403,1517, 1569,1495,     1598,1600,1607,1582,1629,1679,1635,1680,1652,1589,1547,1512,1491,1518,     1482, 1339,1363,1321,1275,1237,1203,1149,1079,1046,995,986,935,972,844,     811,821,750,755,770,729, 640,578,600,604,541,542,483,498,483,477,445,488,     414,451,426,432,399,401,408,424,405,368, 425,417,374,393,389,376,380,413,     387,400,413,404,400,413,393,420,403,389,432,441,403,412, 430,449,429,462,     508,487,482,566,510,589,635,679,688,788,847,900,954,1074,1108,1254,1349,      1437,1507,1667,1778,1869,2021,2163,2177,2436,2500,2611,2746,2860,2917,3023,3010,3066,3192,  3207,3223,3239,3238,3191,3092,3063,3042,3005,2781,2819,2645,2469,2453,2375,2175,2103,2022,1891 , 1805,1649,1514,1454,1303,1287,1120,1026,1033,963,902,806,756,695,614,681,610,610,536,603,557,  537,483,502,493,505,492,493,487,552,478,500,520,471,501,533,578,508,528,497,501,492,487,478, 476 ,497,460,494,467,488,470,471,453,447,453,427,452,478,469,434,463,429,378,434,470,430,403, 470, 456,441,465,432,483,472,471,504,509,552,582,578,688,601,650,662,752,758,751,832,886,898, 959,992 ,1019,1100,1132,1167,1153,1170,1222,1294,1303,1307,1324,1356,1291,1352,1310,1332,1349, 1256,1258 ,1247,1182,1181,1116,1095,1050,1015,1014,1000,977,868,838,757,772,715,668,672,590,591 ,597,509, 572,472,521,480,476,454,460,423,438,405,441,401,455,423,450,462,441,466,489,530,515, 505,587,557 ,585,572,586,608,608,686,690,749,695,741,739,798,792,773,830,805,792,808,821,841, 823,863,864, 869,870,863,915,924,905,862,902,896,893,889,835,869,889,915,912,913,860,799,827, 802,812,809,807 ,758,770,740,746,733,734,669,671,656,617,637,584,567,595,542,558,533,520,520, 502,477,480,449, 497,471,490,425,491,438,465,464,430,484,484,500,481,506,460,459,512,482,520, 522,494,549,582,584 ,585,654,622,610,634,654,674,671,704,722,736,722,747,806,812,772,783,792, 852,829,814,873,871, 835,838,790,810,771,798,756,763,808,738,735,700,663,676,659,628,625,597, 591,565,559,567,571,552 ,564,503,592,517,548,546,501,492,487,472,489,549,539,510,547,508,561, 497,506,507,507,507,524, 507,530,528,578,567,530,541,563,563,557,551,569,543,571,625,608,586, 627,664,625,684,656,725,775 ,737,779,763,825,851,837,885,926,877,969,964,1026,983,1014,1031, 1077,1142,1094,1093,1145,1125, 1093,1106,1131,1117,1116,1067,1102,1100,1029,953,976,923,924,897 ,902,846,832,718,706,685,698, 660,641,659,576,584,557,521,560,498,491,506,498,440,467,432,436, 440,412,410,408,427,413,409,408 ,434,423,437,409,429,451,445,435,430,484,457,459,445,424,452, 445,473,486,466,472,503,513,449, 467,492,479,490,455,515,489,484,470,464,463,466,472,464,412, 414,447,418,434,416,385,397,374,374 ,368,388,353,383,381,353,354,362,328,363,327,363,326,368, 365,298,317,346,309,329,352,353,346, 330,328,329,331,349,327,336,322,330,333,305,346,326,306, 298,319,343,335,350,348,343,335,325,344 ,373,333,344,339,317,331,365,322,330,368,364,312,361, 357,350,322,347,352,335,367,330,334,367, 311,378,362,356,351,336,360,327,325,328,308,316,316, 319,340,341,334,285,338,306,337,350,336,303 ,316,324,365,312,310,340,323,335,323,312,344,363, 356,330,341,361,336,368,355,324,305,312,337, 358,375,343,341,331,349,341,340,354,374,342,339, 375,382,338,366,359,311,386,342,332,374,372,375 ,341,376,393,343,353,426,408,381,404,405,436, 446,456,441,454,486,459,518,537,531,505,536,561, 582,614,637,657,620,683,659,713,730,744,769, 750,790,704,751,763,755,765,789,782,748,757,712,739 ,687,666,684,665,632,619,609,632,582,605, 580,550,586,515,485,479,490,474,473,445,444,418,442, 379,407,414,387,385,361,377,405,347,351, 393,422,397,359,401,363,383,360,382,390,373,382,400,358 ,394,397,377,388,375,426,408,390,423, 411,429,441,438,438,444,466,460,433,428,450,472,460,457, 441,431,434,461,453,427,473,432,410, 417,487,424,476,450,427,448,405,436,431,448,419,403,439,436 ,485,431,430,463,424,464,395,483, 475,455,542,524,546,532,516,609,595,599,602,668,621,720,768, 731,761,776,754,862,856,850,959, 921,981,950,1007,1098,1059,1086,1152,1206,1135,1193,1169,1215, 1304,1297,1320,1432,1435,1441, 1444,1558,1544,1561,1666,1622,1687,1735,1706,1809,1922,1853,1957, 1980,1855,2026,2071,2063,2087 ,2083,2160,2026,2001,2086,1998,2036,2043,1850,2014,1932,1977,1852, 1856,1830,1760,1718,1646, 1602,1545,1482,1490,1399,1328,1363,1265,1147,1177,1163,1132,1085,1033, 981,988,898,887,802,800, 811,776,799,733,741,759,660,667,678,660,617,631,633,594,584,569,623,578 ,568,539,599,603,600, 573,582,571,579,588,543,587,597,597,585,593,632,615,639,669,709,742,744, 815,831,906,927,1022, 1109,1154,1222,1233,1433,1491,1510,1589,1797,1865,2050,2157,2319,2481,2637 ,2890,2977,3190,3339 ,3569,3610,3934,4048,4325,4415,4604,4699,4876,5154,5265,5369,5545,5493,5575 ,5714,5789,5928, 5949,5938,5901,5971,6014,5815,5825,5694,5445,5487,5355,5247,5055,5067,4806,4672 ,4395,4275,4221 ,3947,3749,3543,3348,3222,3054,2945,2787,2604,2406,2245,2114,2044,1884,1749,1658 ,1565,1463, 1299,1304,1251,1141,1083,1092,1028,964,994,903,857,836,859,793,818,773,760,735,748, 731,708,700 ,691,705,653,634,704,654,632,655,653,657,644,662,641,668,634,647,704,649,745,647,683 ,693,639, 653,658,674,699,680,703,693,703,736,748,789,823,791,800,855,872,898,1015,1041,1068, 1109,1218, 1220,1404,1510,1540,1738,1817,1982,2202,2325,2646,2878,3206,3485,3670,4058,4471,4918, 5435,5839 ,6223,6807,7378,7976,8547,9078,9894,10645,11095,11836,12840,13688,14167,15154,15724, 16561, 17293,18288,18947,19378,19981,20523,21206,21811,22148,22725,23021,23501,23484,24094,24134, 24343 ,23961,24013,23799,23665,23163,22917,22345,22123,21724,21032,20517,19743,18822,18350,17587, 16713,15958,15276,14155,13727,12844,12159,11319,10702,9829,9350,8668,7704,7460,6801,6141,5842, 5202,4768,4323,4061,3614,3327,3121,2885,2520,2337,2158,1886,1870,1730,1591,1432,1405,1301,1237,  1199,1169,1071,1019,1033,958,981,964,884,862,846,923,834,824,894,875,840,851,877,859,920,887, 895,867,887,854,910,865,875,808,871,878,958,925,912,931,884,871,878,967,916,921,911,948,949,956  ,984,982,996,1031,961,1041,1030,1013,1048,1020,1122,1103,1197,1122,1168,1166,1216,1234,1233, 1295,1321,1279,1321,1359,1422,1501,1541,1586,1627,1657,1704,1859,1727,1795,1911,2012,2047,2109,  2182,2233,2372,2375,2429,2618,2632,2646,2819,2847,2967,2976,3065,3023,3187,3191,3252,3368,3350 , 3418,3437,3542,3461,3458,3511,3544,3605,3548,3443,3326,3437,3586,3380,3396,3297,3219,3206, 3163, 3092,3023,2976,2936,2734,2615,2818,2729,2598,2544,2460,2415,2396,2372,2250,2216,2178,2002 ,2165, 2090,2082,2023,2056,1939,1974,2051,1931,1938,1982,1964,1897,1846,1883,1966,2008,1899, 1969,1926, 1908,1996,1953,2028,2009,2025,1915,2046,1998,2061,1990,2101,2036,2030,2029,2042,2027 ,2130,2151, 2119,2166,2223,2121,2257,2279,2244,2273,2283,2327,2293,2312,2369,2358,2360,2392, 2417,2363,2406, 2412,2414,2546,2521,2464,2518,2594,2618,2549,2593,2476,2527,2649,2715,2669,2748 ,2771,2857,2879, 2899,2890,2891,2918,2951,3018,3002,3051,3043,2934,2993,3157,3185,3129,3221, 3209,3315,3229,3319, 3464,3528,3518,3502,3581,3686,3719,3680,3906,3961,3879,4055,4047,4077,4175 ,4332,4317,4543,4551, 4593,4900,5017,5080,5130,5134,5246,5417,5657,5901,5936,6033,6210,6405, 6483,6542,6749,6880,6936, 7268,7295,7427,7547,7646,7791,7877,7874,7904,7968,7904,8078,8153,8134 ,8180,8297,8417,8148,8254, 8220,8162,8079,8301,8386,8126,7987,8058,7976,8113,7981,7881,7965, 7998,7926,7691,7673,7966,7705, 7818,7832,7991,7773,7780,7855,7921,8039,8144,8044,8151,8335,8503 ,8342,8485,8642,8727,8968,9037, 8973,9286,9472,9467,9649,9633,9852,10087,10324,10455,10544, 10671,10723,10915,11142,11511,11370, 11767,11854,12030,12100,12551,12617,12970,13156,13173,13556 ,14035,13927,14554,14687,14774,15226, 15195,15757,16083,16156,16280,16907,17065,17712,17816, 18071,18382,18764,19315,19362,19550,20389, 20653,20877,21672,21694,22271,22445,22773,23473,23780 ,24216,24612,24919,25419,25889,26356,26655, 27013,27463,28239,28932,29076,29406,30525,30579, 31144,31481,31670,32470,32822,33354,33483,34402, 34691,35146,35908,36336,36851,37150,37975,38026 ,38632,39310,39664,40183,40102,41029,41434,42113, 42382,42752,43332,43589,44660,45201,45332, 45652,46371,46950,47189,47419,48039,48300,48845,49391, 49563,50736,50760,50813,51345,51783,52317 ,52077,53156,53270,53428,53676,54473,54911,55191,55081, 55411,56022,56171,56415,56042,57405, 57315,57685,58210,58000,58331,58283,58735,59244,59623,59415, 59791,59853,60559,60735,60174,60449 ,60685,61229,61318,61072,61579,61947,61542,61872,62304,62042, 62301,62212,62331,62645,62827, 63027,62745,62643,63126,63198,63308,63000,63625,63539,63314,63434, 63613,63732,63337,63586,63961 ,63401,63664,63382,63363,63167,62516,63287,63164,63811,63358,62960, 63058,63298,63002,62929, 62864,62814,62547,62532,62245,62734,62170,62748,61913,62155,62169,61630, 61773,61329,61714,61168 ,61225,61584,61449,61443,61247,61445,61816,61913,61766,61879,62553,62069, 62767,62801,63584, 64331,65020,65601,65916,66887,67793,69130,69897,71488,72783,73867,75168,76931, 78633,79978,82379 ,83725,86025,87889,90032,92146,94860,97142,99208,102240,103899,106554,109281, 111729,114053, 116401,119073,121053,123172,125016,127208,129671,131055,132664,134543,135633, 137326,137801, 138699,139156,139417,138971,139652,139539,138118,137578,136973,135182,133500, 131798,130274, 128197,125389,123221,120332,117842,113851,110543,107432,103640,99809,95733,92327, 88210,84098, 80526,76943,72796,68490,65378,61465,57688,54128,50967,47401,44181,41497,38624,35151, 33068,30305 ,28066,25714,23793,21736,19949,18203,16443,15365,13955,12837,11643,10445,9662,8778, 8183,7438, 6737,6171,5828,5194,4740,4440,4057,3794,3737,3372,3131,2918,2779,2639,2519,2386,2240, 2142,2173 ,2094,1989,1886,1801,1704,1635,1641,1624,1532,1478,1410,1384,1379,1345,1317,1213,1288, 1215, 1177,1164,1123,1108,1072,1001,1032,1021,973,933,874,881,886,796,813,772,799,802,744,770, 711, 679,689,685,628,659,635,583,613,577,617,563,525,571,553,526,501,487,470,502,476,462,464,449 , 429,432,419,440,394,458,371,386,368,364,358,339,353,329,360,280,335,323,322,291,314,281,289, 269,324,286,264,265,309,280,266,235,268,269,251,250,238,233,274,257,226,256,229,235,245,227,248  ,223,197,202,214,224,203,184,185,195,218,219,212,202,214,201,182,191,207,195,175,180,193,197, 169,194,179,189,182,216,179,181,190,176,131,195,188,187,174,181,160,180,159,163,173,152,194,173  ,179,181,170,172,173,166,182,159,202,176,167,151,172,147,167,175,182,155,171,148,149,159,171, 163,161,138,150,159,159,141,171,150,156,169,130,148,144,154,148,125,150,148,159,149,155,149,152  ,124,125,155,157,155,124,146,175,145,152,156,136,153,139,156,160,151,143,144,141,157,153,150, 145,164,141,149,155,151,126,142,163,163,159,147,153,158,154,172,160,161,166,175,156,157,155,158  ,153,170,174,166,167,147,190,174,168,152,190,172,162,176,164,189,177,150,150,182,159,171,190, 156,134,161,191,152,163,163,145,144,132,119,140,169,152,146,142,138,128,134,130,131,147,104,139  ,100,114,108,106,116,91,94,120,117,101,94,93,79,78,92,86,100,86,110,87,95,86,101,75,86,79,78, 88,75,91,91,94,97,84,80,82,95,96,112,102,92,91,97,106,98,101,99,116,90,118,104,128,130,126,95, 130,114,117,113,113,107,128,130,127,128,131,124,112,135,130,129,118,118,101,111,140,122,130,123  ,111,115,117,118,102,108,126,99,132,102,96,107,103,91,100,115,96,78,98,121,109,107,95,81,125, 107,71,92,100,99,109,111,94,86,107,89,99,101,98,88,89,89,111,85,80,93,97,85,124,95,96,119,99, 87,96,113,110,89,107,103,116,92,103,104,114,104]
        plastic=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,8,14,31,38,74,164,246,477,811,1299,2247,3567,5642,8565,13142,19457,28502,40365,55624,76541,101225,132192,168113,210436,256771,305809,358263,409224,456630,500519,538105,562950,576847,580403,569609,548119,517206,477429,431533,381562,331294,281218,234641,192011,152976,120943,93226,70067,52237,38423,27557,19602,13581,9300,6346,4287,2975,1961,1287,932,657,504,340,254,249,186,161,153,129,93,109,100,97,101,102,86,95,82,61,76,46,52,39,37,22,24,31,52,155,174,175,189,180,184,180,200,222,229,261,396,752,1586,2867,4180,5356,5857,6110,6003,6121,5923,5942,5870,5738,5755,5885,5617,5622,5711,5652,5515,5591,5469,5342,5419,5403,5324,5359,5233,5234,5249,5265,5260,5231,5153,5195,5126,5129,5181,5077,5047,4889,5071,4992,4927,4948,4932,4811,4792,4879,4955,4851,4906,4716,4730,4764,4671,4723,4718,4656,4650,4881,4806,4687,4627,4742,4605,4678,4590,4625,4667,4592,4516,4618,4689,4567,4668,4440,4470,4463,4522,4624,4451,4565,4516,4526,4556,4459,4421,4471,4411,4364,4443,4296,4552,4383,4406,4427,4590,4446,4513,4339,4330,4250,4418,4319,4421,4290,4278,4293,4128,4346,4232,4319,4322,4188,4204,4292,4228,4162,4315,3994,4201,3918,4070,4059,4030,3935,4069,3901,3840,3940,3728,3763,3766,3680,3758,3766,3669,3599,3701,3605,3638,3604,3492,3420,3415,3381,3411,3282,3279,3206,3168,3136,3162,2989,3008,2961,3037,2817,2911,2996,2886,2826,2806,2730,2736,2609,2597,2567,2553,2487,2562,2508,2511,2372,2443,2413,2215,2416,2259,2326,2255,2223,2167,2136,2123,2170,2057,2105,2001,2062,2072,2054,2003,2009,2037,1938,1918,1888,1924,1884,1853,1925,1821,1827,1847,1879,1841,1886,1796,1763,1867,1777,1754,1721,1787,1717,1773,1690,1771,1775,1711,1766,1757,1730,1764,1716,1735,1697,1674,1623,1747,1650,1567,1635,1573,1539,1604,1638,1584,1562,1562,1518,1502,1562,1505,1524,1548,1451,1518,1494,1459,1506,1475,1469,1409,1408,1425,1407,1417,1478,1404,1384,1344,1397,1436,1297,1414,1447,1341,1358,1426,1387,1429,1458,1423,1424,1487,1397,1453,1463,1466,1460,1445,1486,1406,1417,1506,1443,1444,1438,1383,1391,1419,1405,1377,1309,1373,1371,1379,1422,1384,1410,1353,1417,1494,1501,1472,1447,1505,1405,1397,1487,1521,1575,1489,1477,1571,1490,1572,1574,1551,1624,1570,1650,1583,1575,1621,1590,1586,1506,1514,1471,1535,1554,1492,1511,1567,1496,1499,1493,1467,1525,1514,1456,1402,1446,1406,1533,1439,1397,1380,1407,1363,1420,1393,1326,1317,1325,1346,1330,1382,1337,1308,1350,1357,1371,1398,1367,1359,1388,1433,1492,1486,1544,1575,1634,1830,1816,2018,2239,2251,2316,2588,2706,2832,3153,3219,3340,3609,3544,3753,3575,3896,3791,3902,3771,3735,3623,3511,3401,3209,3135,2936,2789,2552,2383,2254,2093,1961,1967,1817,1718,1620,1589,1482,1446,1410,1401,1424,1339,1416,1382,1379,1413,1298,1345,1381,1260,1291,1303,1284,1304,1341,1192,1241,1285,1198,1169,1127,1237,1227,1173,1168,1208,1166,1163,1083,1178,1151,1128,1170,1219,1167,1202,1121,1119,1122,1128,1122,1158,1154,1140,1113,1229,1070,1087,1083,1089,1032,1082,1075,1064,1126,1112,1035,1074,1110,1058,1095,1069,1036,1040,983,1060,1071,1058,1027,1038,1105,1059,1094,1018,1029,1022,1053,995,1091,1097,1068,1071,1027,1081,947,979,1053,1084,1105,1061,1013,1048,1053,1192,1126,1136,1175,1219,1220,1222,1195,1215,1193,1256,1225,1184,1213,1196,1208,1236,1243,1213,1195,1144,1125,1121,1096,1090,1140,1147,1085,1070,1080,1006,1073,1009,1053,1038,972,951,1032,959,997,1029,957,956,1021,1006,1037,1029,1001,1014,1072,1039,1014,972,1051,995,990,1027,975,1008,1020,1035,1056,1029,1027,1053,1095,1073,1016,1115,1084,1094,1113,1100,1143,1147,1164,1194,1167,1180,1173,1176,1162,1131,1210,1216,1149,1176,1227,1223,1182,1214,1168,1110,1113,1141,1127,1048,1088,1015,1035,1066,1004,955,997,990,1010,972,998,980,1013,964,993,966,950,1017,995,1017,1012,957,1018,1012,1031,1116,1058,1121,1136,1226,1284,1410,1521,1584,1742,1850,2057,2359,2649,3104,3534,4030,4489,5189,5979,6961,7872,8658,9785,10999,12198,13274,14552,15609,16802,17947,18497,19494,20176,20783,21366,21414,21322,21280,20964,20423,19866,19008,18164,17238,16164,14992,13608,12403,11407,10314,9142,8123,7298,6366,5683,4799,4102,3790,3198,2807,2437,2143,1957,1681,1542,1463,1356,1231,1224,1179,1116,1080,1141,1122,1109,1184,1229,1240,1307,1335,1437,1525,1595,1677,1804,1851,2049,2245,2268,2316,2610,2679,2745,2819,2960,3088,3174,3325,3357,3439,3421,3274,3426,3366,3243,3055,3058,3022,2877,2679,2550,2347,2208,2186,1976,1832,1698,1548,1483,1404,1314,1187,1193,1120,1050,1018,939,973,920,868,870,845,824,845,831,856,858,854,817,794,782,764,824,789,786,816,756,758,765,815,855,793,783,812,788,760,786,820,826,762,816,792,770,811,854,822,813,849,751,761,786,750,797,790,802,782,806,774,801,828,768,802,785,808,822,797,889,849,805,760,839,833,819,777,817,860,790,855,811,828,833,842,804,794,830,813,825,831,746,792,789,795,798,789,767,771,732,778,818,779,728,768,732,797,838,798,751,773,774,749,799,758,748,762,753,795,779,754,751,757,744,723,770,730,715,764,752,764,778,785,754,789,750,775,702,694,772,749,794,747,731,732,734,706,721,757,772,765,763,735,734,794,753,784,760,702,770,740,706,742,749,746,768,719,754,752,746,788,711,754,801,762,794,725,711,716,723,736,750,693,731,741,728,741,731,711,739,734,703,734,707,686,730,711,667,779,703,736,710,706,717,713,691,763,727,731,744,716,730,764,733,731,706,734,738,716,739,749,691,692,677,676,721,702,723,733,724,732,694,688,668,678,737,720,753,668,691,693,785,769,689,723,705,749,703,704,757,711,692,724,700,677,768,744,764,714,701,763,713,756,709,722,700,775,723,749,707,761,691,709,738,742,656,745,708,706,683,733,697,677,689,693,724,660,675,704,697,672,714,665,686,736,685,670,695,710,688,698,691,694,688,658,663,692,683,679,685,681,718,680,657,673,673,676,681,702,695,663,703,733,660,682,712,717,678,712,714,687,689,714,710,711,659,692,710,678,694,674,692,646,664,705,662,676,696,663,644,720,711,682,710,740,711,731,702,696,713,717,725,656,730,676,674,709,675,708,663,707,688,631,704,674,711,701,740,656,699,689,661,640,692,651,691,737,688,665,690,667,686,660,676,664,697,658,685,675,653,679,649,698,667,709,721,671,719,636,691,667,680,657,694,671,667,721,693,683,684,710,670,656,727,768,731,775,759,763,754,741,759,818,823,835,1005,986,1035,997,1065,1130,1213,1291,1298,1360,1435,1550,1614,1631,1739,1741,1842,1921,2004,2059,2009,2089,2044,2073,2072,2034,2133,1956,1980,1947,1948,1849,1728,1739,1634,1632,1494,1502,1389,1338,1325,1177,1152,1067,1054,1011,951,946,895,831,792,801,772,761,740,730,689,715,708,673,685,708,682,661,715,705,644,610,653,665,661,650,675,628,638,655,651,633,662,653,633,666,651,654,618,602,648,698,686,638,632,596,609,583,644,670,637,636,659,635,642,637,631,696,697,628,651,641,675,639,638,691,670,699,644,644,629,661,610,643,661,651,679,663,680,683,652,671,691,657,666,637,720,676,716,731,721,736,711,711,791,816,742,769,789,750,785,790,792,787,801,844,841,831,836,822,857,834,866,834,790,770,774,816,732,806,747,753,740,757,705,750,686,720,696,676,759,617,655,684,668,645,651,637,665,623,647,646,640,643,633,617,652,574,623,639,643,606,619,654,615,658,637,606,627,648,670,678,656,635,646,673,639,605,709,639,673,649,655,700,674,659,637,664,729,690,689,704,717,707,706,706,708,720,760,723,748,733,741,713,709,751,640,717,707,724,730,723,702,704,666,734,661,663,664,637,648,661,674,664,679,623,661,669,598,651,625,677,664,628,637,663,627,634,635,630,606,641,651,633,598,627,605,597,623,610,669,619,644,643,587,615,621,647,659,664,632,659,613,629,634,627,599,621,616,651,651,672,615,633,640,656,636,676,703,690,724,728,681,648,768,780,778,850,793,902,864,925,965,967,1111,1083,1129,1204,1290,1373,1382,1421,1487,1555,1609,1630,1674,1821,1879,1868,1969,1943,2013,2076,1985,1953,2079,1937,1968,1954,1911,1895,1813,1740,1730,1671,1587,1620,1472,1433,1397,1349,1309,1265,1150,1137,1022,1072,969,932,859,847,797,853,786,764,735,712,764,738,711,694,672,657,662,636,653,641,630,670,625,665,654,644,625,656,684,629,615,633,628,642,664,641,612,626,641,602,627,590,671,646,631,661,645,611,595,600,631,629,644,612,599,660,605,666,641,626,671,673,651,691,702,642,681,695,724,740,787,743,737,785,863,855,896,935,919,1062,959,1020,966,1103,1060,1126,1109,1146,1196,1163,1209,1191,1249,1276,1233,1238,1248,1233,1256,1225,1163,1182,1126,1144,1177,1091,1081,1072,1039,955,990,923,980,947,856,858,869,827,782,765,778,710,755,719,733,730,713,665,686,701,730,715,703,723,750,738,809,774,742,800,757,799,817,744,802,765,796,750,824,797,814,834,743,826,725,796,705,744,765,735,692,802,771,695,759,669,698,667,735,680,623,652,679,651,678,600,663,681,653,626,649,607,652,644,644,597,598,604,600,622,645,657,608,623,614,632,613,653,604,633,642,610,633,629,572,642,604,613,679,616,594,674,653,636,655,693,662,656,628,690,629,615,652,609,652,603,687,627,638,652,638,605,585,660,654,652,638,634,591,622,636,676,610,571,622,647,609,622,623,643,588,631,596,615,616,648,646,623,666,642,633,641,634,627,713,668,628,671,691,685,684,713,697,717,687,710,675,696,706,644,668,712,680,665,693,686,657,694,668,692,680,688,741,714,691,717,720,684,654,650,673,685,662,655,625,664,701,673,643,664,616,648,651,659,658,642,592,600,639,623,626,626,703,604,606,600,597,651,638,653,617,680,669,613,653,591,611,670,630,620,587,633,625,575,616,604,651,631,597,622,692,675,629,639,645,646,603,660,634,629,609,600,592,626,640,635,587,649,652,610,646,644,658,646,683,630,617,659,643,592,662,616,605,656,606,633,629,642,648,613,551,658,627,649,700,627,629,636,671,637,620,654,658,620,589,650,652,610,668,625,614,641,606,632,632,627,612,654,578,696,613,605,643,660,651,652,658,676,656,642,654,659,635,665,631,608,635,654,641,679,641,673,699,661,724,669,681,685,703,690,665,689,708,745,760,695,697,733,737,767,723,774,729,742,768,765,705,826,783,794,803,792,812,786,820,844,762,816,799,835,810,838,799,800,783,754,758,798,785,736,782,777,803,726,714,719,787,730,714,752,715,723,761,675,674,654,657,704,633,662,739,626,709,709,658,708,689,662,691,641,685,700,674,633,659,681,726,732,665,680,702,706,678,730,687,668,709,680,702,668,670,695,723,702,703,722,678,708,672,702,724,691,683,672,738,694,703,725,665,687,667,669,675,688,686,713,682,672,673,677,702,704,688,703,662,706,664,712,666,785,735,691,698,710,706,695,722,676,691,635,668,709,693,743,728,692,690,721,683,673,685,686,700,703,684,699,753,708,711,725,693,680,720,791,773,688,701,693,691,709,757,754,721,736,750,725,722,707,734,744,753,720,731,762,739,752,736,760,747,729,701,725,705,761,768,724,699,738,777,710,765,748,705,747,742,678,750,705,798,752,747,772,716,783,709,721,722,799,745,688,757,717,712,751,728,724,792,762,780,707,744,754,762,699,789,757,772,728,682,755,734,723,783,755,752,766,765,750,725,796,726,728,756,757,789,756,764,770,788,798,766,773,790,805,748,765,763,713,731,760,734,775,779,751,774,774,801,775,828,770,779,809,822,772,773,828,767,822,797,805,794,827,797,850,802,856,820,800,847,828,771,880,786,814,836,800,856,813,863,800,739,781,760,825,862,799,828,788,824,795,779,790,768,769,780,821,770,784,834,788,826,813,790,855,787,810,851,803,807,845,862,825,852,820,852,855,876,850,838,845,797,869,800,873,863,808,824,819,786,876,837,845,827,842,835,858,816,862,812,847,846,854,820,836,855,871,859,889,852,870,904,892,799,867,860,853,876,844,848,895,854,849,869,838,874,815,893,856,911,841,830,891,876,902,900,845,873,938,897,939,916,920,932,880,916,984,968,952,908,958,1025,936,1025,1017,986,966,991,942,977,1035,1117,1069,1024,1010,1025,1040,1044,1023,1023,1021,1054,1055,1053,1093,1044,995,1133,1057,1044,1044,1046,1048,1030,988,996,1056,1036,961,986,995,1018,986,977,1023,948,968,1016,975,954,1041,948,948,975,968,972,909,927,973,986,1009,953,894,919,1005,994,915,935,963,955,945,912,949,964,997,935,1000,954,1010,1029,997,1008,1068,1051,996,984,1021,1009,1029,1004,1025,1003,984,1041,1081,1009,1098,1027,948,987,976,1082,1039,997,1041,1049,1066,1050,1039,1044,1053,1049,1094,1013,1065,1062,994,1107,996,1056,1030,1061,1057,1092,997,1028,1067,1062,1013,1033,1052,1098,1104,1095,1094,1141,1077,1060,1159,1119,1115,1086,1059,1116,1088,1089,1118,1114,1107,1072,1150,1121,1106,1149,1106,1109,1120,1098,1148,1105,1173,1091,1129,1122,1174,1108,1117,1147,1139,1155,1145,1140,1219,1162,1160,1182,1165,1140,1166,1181,1173,1158,1162,1213,1199,1170,1234,1266,1170,1263,1263,1204,1182,1227,1266,1268,1224,1225,1215,1209,1179,1295,1269,1277,1236,1289,1243,1238,1249,1279,1289,1315,1333,1241,1250,1229,1289,1279,1320,1238,1252,1332,1262,1336,1345,1250,1262,1377,1325,1302,1297,1370,1378,1357,1333,1350,1360,1319,1308,1411,1330,1354,1414,1359,1400,1383,1439,1418,1436,1398,1430,1454,1426,1409,1456,1409,1474,1449,1485,1443,1425,1439,1505,1504,1471,1396,1523,1468,1495,1473,1537,1576,1445,1525,1655,1563,1516,1570,1538,1525,1585,1574,1637,1578,1708,1607,1622,1642,1610,1623,1633,1647,1642,1684,1736,1733,1702,1629,1669,1707,1775,1709,1706,1740,1755,1767,1814,1755,1854,1802,1759,1827,1784,1774,1867,1848,1864,1865,1892,1914,1997,1908,1964,1947,1984,1977,1981,1953,1933,1954,1960,1934,2058,2018,2156,2045,2025,2025,2083,2038,2089,2025,2073,2123,2117,2153,2198,2064,2101,2055,2091,2189,2088,2148,2081,2195,2172,2294,2144,2220,2197,2313,2268,2224,2218,2303,2248,2264,2261,2329,2335,2393,2381,2433,2378,2449,2455,2446,2534,2433,2469,2466,2522,2491,2588,2552,2584,2737,2689,2607,2610,2684,2747,2827,2714,2732,2772,2844,2909,2798,2776,2832,2753,2887,2878,2949,2893,3019,2820,2916,2957,3053,3066,3060,3059,3094,3128,3126,3196,3211,3155,3264,3226,3327,3256,3221,3285,3362,3446,3471,3403,3492,3413,3539,3577,3592,3553,3648,3636,3744,3901,3660,3833,3819,3714,3836,3771,3917,3983,3942,4015,3959,4082,4102,4017,4136,4076,4261,4120,4268,4257,4336,4300,4407,4460,4342,4491,4486,4531,4579,4611,4669,4729,4787,4766,4709,4808,4802,4876,4868,4962,4966,4986,5175,5021,5095,5188,5345,5350,5364,5476,5337,5581,5527,5460,5647,5559,5686,5681,5648,5820,5898,5878,5979,5901,6168,6189,6313,6249,6222,6484,6518,6642,6644,6669,6778,6750,6920,6861,6899,7020,7151,7081,7122,7416,7303,7388,7365,7679,7603,7613,7842,7699,8019,7973,8235,8200,8281,8402,8601,8460,8833,8571,8692,9019,9023,8969,9253,9266,9322,9456,9451,9524,9763,9611,9908,9825,10099,10333,10281,10177,10679,10659,10550,10984,10935,11036,11385,11162,11383,11618,11663,11585,11871,12083,12288,12329,12314,12460,12725,12811,12728,12895,13101,13295,13215,13436,13578,13882,13804,13954,14118,14534,14269,14492,14691,15214,15143,15276,15191,15473,15381,16121,15926,16080,16383,16369,16669,16775,17005,17176,17364,17506,17313,17772,18018,18063,18345,18645,18510,18613,18666,19021,19256,19262,19602,19722,19837,20367,20175,20382,20591,21224,20954,21352,21417,21818,21730,21818,22236,22448,22658,22872,22985,23225,23345,23224,23829,23597,24343,24305,24894,24947,24926,25157,25108,25444,25758,26225,26086,26377,26872,26718,26907,27227,27696,27550,28054,28525,28777,28606,28948,29245,30047,29980,30402,30441,30745,31019,31206,31872,32073,32652,32828,33135,33941,33749,34397,34720,35335,35516,36618,36720,37062,37753,37738,38391,38672,39453,40147,40680,41330,42148,42522,43344,44168,44223,45331,46043,46791,47671,48333,49289,49903,51222,51560,52431,53736,54771,55395,56635,57975,58783,60063,60750,61850,63949,64524,66027,67355,68215,69511,71452,73013,74444,75571,76238,79146,80068,81760,83112,84831,86806,88632,90280,91901,93533,95441,97575,99642,101866,103228,105327,107246,109348,110982,113256,114470,116477,119976,121808,123670,125575,127906,130328,132476,134753,136925,139384,141561,143657,145857,148049,150543,153260,154869,157941,159987,162128,163216,166002,167884,170192,172410,174683,176952,178989,180739,183088,184708,187639,189788,191423,192987,195502,198045,199719,201800,203411,204561,207381,208405,210033,212865,213959,215201,217614,219259,221249,222239,224177,225447,226987,227702,229150,230496,232469,233817,234412,236205,236803,238421,238962,240226,241669,241824,242859,243658,245650,246878,246729,247924,248210,249838,250762,251332,252317,252520,253667,253396,255385,254988,255212,255936,255799,256411,257605,257719,259053,258208,259030,260503,260067,259733,259796,260924,260529,262075,262557,262779,262415,263262,263189,263750,263286,265314,264042,264191,263947,264504,264273,265335,265568,266235,266296,266421,266333,266965,267299,266914,267166,267118,268350,267663,268481,267895,268755,269184,268584,268336,268552,268570,269838,269813,270625,269490,270311,270829,270661,270529,271254,270882,271465,271017,270834,271212,271413,271857,270654,271473,271121,271611,271897,271644,272146,271307,272256,271444,271757,271407,271547,270708,271491,272015,271209,272718,272068,271375,271710,272534,272797,274333,275660,275904,276898,277759,278410,279550,280296,282327,283723,284303,287093,288717,291369,293479,296775,298356,301099,304809,308338,311443,313742,317597,320110,324262,327865,330656,335376,337837,342973,345263,349940,352960,356077,360416,363829,365909,368587,370809,373249,374398,378233,378810,380148,379176,379984,380034,378243,377946,375696,373009,371077,367440,363704,358748,355539,349671,342747,337626,329740,322916,316544,307674,298949,290912,281870,272057,263412,252135,243550,234322,223598,214332,203807,194059,183850,175173,164878,156012,146495,137792,129625,121198,113402,106373,98799,91440,84968,78996,73211,67922,62790,57697,53508,49114,45713,42338,38837,35803,32816,30135,28336,26038,23989,22505,21071,19508,18114,16954,16045,15068,13857,13587,12614,12059,11410,11164,10623,10206,9783,9372,9353,8887,8509,8395,8072,7931,7629,7300,7170,6961,6916,6669,6646,6267,6354,6110,5962,5747,5646,5451,5519,5323,5179,5088,4765,4766,4712,4638,4377,4294,4275,4118,3982,3890,3945,3900,3591,3550,3424,3531,3305,3283,3178,3084,2925,2923,2899,2769,2737,2674,2699,2541,2485,2393,2334,2243,2208,2220,2141,2043,2025,1928,1967,1877,1818,1755,1715,1631,1620,1681,1596,1492,1528,1487,1438,1357,1397,1310,1354,1289,1263,1221,1178,1206,1139,1187,1115,1109,1054,1109,1063,1034,1072,1006,1009,921,983,979,929,931,914,908,832,866,881,855,806,812,828,827,795,792,740,806,761,732,746,734,725,725,705,701,720,713,645,679,656,657,655,629,649,629,604,625,641,641,539,612,599,578,579,551,567,551,563,555,537,522,537,567,524,551,536,520,542,523,489,501,515,547,516,458,473,456,446,478,475,475,485,482,492,471,436,455,431,464,455,423,438,401,441,447,416,432,442,432,407,425,433,404,409,380,406,401,386,396,385,400,417,428,406,386,372,365,333,360,379,363,372,363,364,385,393,384,370,357,369,385,351,354,351,342,350,335,355,352,344,337,365,351,310,332,363,334,345,303,317,346,311,325,301,275,334,312,332,316,319,307,290,332,290,299,316,297,314,277,327,324,321,301,300,304,301,291,300,301,258,290,270,282,292,283,265,280,311,250,310,256,285,298,282,318,256,315,276,274,289,241,277,251,270,272,252,266,269,268,272,265,285,244,246,258,263,258,239,254,255,245,231,235,223,251,246,247,239,252,232,253,248,222,237,246,214,250,264,233,255,269,254,266,242,214,243,208,256,273,286,272,257,246,249,247,275,255,253,280,285,257,259,305,289,269,270,281,249,276,274,289,285,286,276,270,269,275,260,264,274,243,273,232,240,238,241,248,236,205,202,191,193,175,202,183,175,189,155,163,153,131,157,114,141,120,118,120,126,117,105,102,98,99,91,116,95,89,94,85,92,82,104,94,90,84,77,82,85,75,87,83,81,87,73,61,66,89,73,68,83,82,75,67,80,77,91,80,70,76,82,68,73,76,73,68,64,69,61,72,63,65,78,68]
        standard=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,0,4,4,10,16,29,64,107,158,288,494,828,1180,1837,2882,4314,6147,9097,12703,17768,24613,33194,44596,58721,76029,99131,126740,159807,200691,248441,305914,373841,452568,541955,641280,750045,869434,994871,1119786,1247348,1367476,1480473,1578506,1658468,1716573,1744018,1749673,1725983,1684366,1611891,1518644,1409395,1287358,1159633,1029417,897705,771894,653432,544623,447022,360940,287478,225601,173560,131846,98989,73083,53459,38381,27241,19020,13170,9013,6184,4128,2969,1963,1390,982,758,531,440,372,290,303,250,240,195,195,211,215,175,125,110,116,106,81,75,68,60,103,182,200,236,223,237,265,288,465,737,1281,2175,3788,6092,8730,11426,13220,13670,13768,13649,13379,13310,13350,13249,13101,12706,12805,12720,12547,12392,12502,12179,12250,12118,12096,11978,11907,11748,11802,11670,11454,11574,11498,11513,11411,11321,11412,11410,11363,11273,11189,11384,11416,11285,11499,11201,11272,11032,11202,11114,11134,10938,11132,10996,10718,10642,10517,10464,10595,10320,10273,10252,10203,10113,9901,9880,9891,9624,9707,9639,9406,9649,9659,9659,9434,9452,9364,9542,9461,9592,9515,9759,9742,9701,9856,9973,10089,10239,10305,10555,11007,11156,11447,11678,12397,12818,13350,13954,14970,15735,16614,17816,18636,19787,20934,21836,22968,23626,24833,25096,25777,25863,26170,25824,25979,25205,24363,23855,22861,21646,20701,19362,18306,17100,15956,14900,14080,13101,12261,11598,11138,10650,10247,9874,9781,9287,9208,9316,9187,9180,8997,9151,9099,9128,9272,9420,9429,9476,9317,9421,9443,9362,9310,9250,9283,9034,9135,8882,8629,8675,8530,8340,8370,8290,7975,7707,7886,7709,7637,7616,7537,7555,7372,7304,7286,7160,7213,7269,7131,7349,7288,7456,7251,7361,7446,7463,7621,7648,7417,7781,7767,7848,7920,8030,7875,8069,8186,8184,8267,8296,8321,8425,8480,8448,8445,8591,8642,8679,8789,8542,8844,8735,8793,8579,8666,8856,8700,8682,8660,8628,8294,8422,8286,8336,8282,8162,8045,7948,7858,7900,7704,7475,7756,7436,7428,7505,7456,7209,7186,7141,7245,7099,6976,7028,7130,6914,6978,6988,6993,6885,7117,7230,7154,7398,7582,7744,8194,8516,8813,9079,9917,10568,11575,12589,13543,14996,16614,18241,20077,22570,24924,27433,30425,33556,37259,40277,44178,47892,51473,55052,58382,62534,65332,68449,71107,73620,75444,77938,79312,79646,80515,81661,80840,80208,79637,79363,76947,76059,74392,72141,70407,67941,65879,63852,61397,58759,55779,53777,50352,47962,44782,42798,40410,38115,35243,33130,31459,29783,28056,26557,25892,25179,24447,23963,23968,24240,25020,25448,26337,27424,28702,29786,30725,32353,33759,35103,36326,37400,38431,38939,39849,40340,40050,40040,39823,39263,38493,37355,36755,35483,34458,32699,31769,30424,28879,28109,26426,25422,24367,23787,22963,21870,20931,20873,19757,19593,19032,18886,18711,18529,18528,18811,19230,19377,19922,20733,21358,22615,23977,25235,26780,28497,30713,33190,34887,37620,40406,43114,45655,48212,51158,53069,54997,57602,58686,59788,60990,61988,61031,60828,59849,59179,57663,55930,53934,51910,49519,47047,44410,42238,40155,37989,35499,33355,31780,30279,29523,28238,27533,26751,26382,26628,26617,27486,28492,29988,31837,34702,37563,41864,47041,53122,60330,69204,79658,91381,107139,123914,144351,166626,192553,222730,254976,291033,332087,375636,423283,473587,525964,578263,633734,688930,743175,795173,842888,886490,927162,962779,987298,1004509,1015055,1016175,1008413,991796,966764,934374,896107,850721,803217,751100,695191,637111,581120,525740,470415,419694,372984,328252,286899,251924,220243,193167,169514,149956,134179,121820,112715,105688,101328,98351,97117,96564,96865,98310,99507,100845,101677,102454,102388,102591,101956,100452,98162,95518,91507,87606,83323,78730,73172,67576,62544,57181,51945,47069,42121,37473,33509,29405,25684,22540,19677,17155,14838,13002,11505,10172,9045,7870,7227,6531,5972,5471,5255,4940,4764,4488,4308,4198,4065,3904,3803,3794,3708,3664,3686,3564,3550,3561,3619,3483,3610,3476,3572,3713,3658,3625,3773,3937,4107,4184,4291,4355,4621,4592,4895,4951,5052,5379,5582,5600,5707,5801,6292,6092,6236,6095,6308,6385,6270,6232,6171,6114,5840,5707,5680,5465,5389,5076,4861,4783,4629,4378,4245,4111,4025,3856,3641,3604,3460,3449,3277,3321,3230,3250,3117,3157,3078,3011,3160,2991,3028,3007,2936,3029,2952,2839,2905,2912,2988,2984,2810,2953,2921,2922,2804,2880,2920,2890,2800,2874,2787,2870,2836,2980,2843,2888,2855,2859,2863,2816,2855,2813,2956,2828,3003,2908,2876,2981,2910,2906,3029,3021,2960,2995,3014,2996,2960,3038,3094,3057,3177,3180,3122,3249,3169,3314,3181,3328,3258,3269,3301,3333,3378,3317,3275,3343,3246,3329,3237,3239,3210,3161,3083,3122,3079,3078,3069,2993,3062,2949,2832,2932,2982,2971,2885,2912,2875,2743,2746,2829,2939,2767,2851,2877,2852,2851,2723,2817,2822,2734,2733,2827,2765,2817,2827,2844,2862,2750,2831,2942,2854,2873,2816,2819,2763,2859,2870,2848,2818,2827,2826,2937,2846,2760,2857,2872,2886,2793,2894,2850,2850,2853,2904,2846,2885,2847,2891,2745,2972,2990,2890,2873,2875,2953,2890,2886,2974,2807,2985,2844,2921,2983,2899,2929,3060,2903,2887,2921,3057,2984,3039,2989,3069,3010,3135,2961,2963,3041,2980,2918,3004,2945,3038,3034,3073,3074,2913,3097,3114,2976,2987,3073,3056,3103,3044,3023,3142,2927,3165,3132,3090,3159,3147,3231,3122,3236,3218,3129,3199,3105,3218,3125,3105,3122,3081,3165,3155,3027,3225,3169,3071,3145,3111,3092,3230,3231,3113,3106,3137,3187,3167,3098,3058,3101,3213,3166,3118,3151,3167,3127,3244,3202,3163,3224,3255,3167,3227,3257,3247,3365,3285,3275,3344,3361,3421,3342,3459,3497,3384,3541,3489,3509,3600,3682,3675,3781,3763,3777,3752,3892,4046,4101,4122,4309,4380,4553,4553,4788,4966,5102,5535,5591,6004,6508,7062,7668,8407,9440,10454,12092,13689,15563,17969,20920,24228,27997,32351,38048,43653,50214,57849,66725,76908,86901,99465,112927,127487,142702,159748,176783,195443,214172,235092,253430,273409,293254,312534,330815,347610,364479,378811,390794,401689,408998,414951,417769,416643,415174,408392,401962,391064,378985,363739,348147,330463,311465,292914,271956,251601,231402,211001,192743,173100,153637,137916,121884,107418,94949,81751,70709,60871,52417,44725,38264,31791,27454,22969,19213,16764,14215,12244,10523,9254,8138,7215,6561,5953,5587,5352,5125,5270,4912,4933,4898,5084,4932,5103,5102,5234,5390,5436,5637,5799,5962,6358,6510,6887,7312,7786,8456,8858,9433,10244,11195,12269,13502,14707,15873,17558,19051,21120,22852,24788,27362,29656,32269,34860,36971,39586,42216,44887,47359,49608,52101,54236,56055,57510,58976,60040,60826,60897,61515,60421,59394,58974,57618,55945,54374,52399,49047,46831,44919,41989,39667,36500,33361,31045,28516,26357,23630,21213,19264,17244,15233,13678,12182,10827,9515,8522,7440,6626,6086,5499,4865,4319,4031,3809,3530,3407,3221,2910,2904,2732,2676,2611,2526,2454,2459,2470,2501,2421,2423,2408,2304,2330,2314,2266,2333,2295,2326,2310,2334,2227,2317,2286,2327,2294,2250,2254,2173,2265,2220,2313,2288,2181,2282,2298,2155,2244,2298,2223,2250,2247,2256,2144,2329,2240,2180,2241,2214,2160,2298,2264,2148,2333,2152,2345,2284,2327,2174,2292,2275,2208,2282,2216,2315,2232,2228,2236,2146,2199,2288,2242,2219,2265,2219,2211,2229,2205,2286,2195,2256,2228,2157,2154,2250,2152,2212,2221,2200,2225,2273,2128,2194,2283,2321,2301,2241,2209,2235,2194,2238,2174,2378,2255,2318,2265,2356,2282,2354,2251,2175,2188,2240,2259,2295,2189,2251,2217,2291,2331,2376,2348,2296,2234,2353,2420,2368,2486,2500,2447,2439,2599,2618,2634,2724,2763,2769,2816,2893,2908,2947,3042,3057,3158,3192,3244,3224,3436,3401,3438,3503,3454,3496,3555,3512,3517,3619,3459,3583,3517,3451,3376,3329,3426,3358,3278,3274,3209,3139,3181,3145,3086,3038,3162,3122,3115,3032,3215,3116,3098,3215,3214,3238,3361,3276,3501,3459,3519,3648,3890,3779,3839,3944,4122,4023,4171,4338,4272,4380,4488,4407,4508,4413,4430,4388,4600,4485,4511,4225,4445,4337,4207,4104,4098,4034,3967,3787,3795,3632,3611,3555,3370,3243,3297,3187,3071,3115,2952,2846,2819,2845,2797,2780,2654,2697,2696,2709,2748,2654,2703,2785,2729,2720,2724,2685,2822,2777,2795,2740,2950,2884,3005,3020,3109,3043,3124,3042,3162,3241,3221,3239,3201,3258,3379,3377,3365,3252,3426,3399,3391,3481,3410,3344,3409,3366,3440,3389,3489,3365,3292,3417,3264,3308,3314,3178,3215,3267,3265,3241,3211,3354,3175,3177,3222,3158,3262,3266,3306,3247,3274,3284,3334,3381,3474,3444,3550,3676,3815,3880,4089,4277,4426,4514,4904,5096,5359,5625,6123,6434,6995,7371,7926,8894,9421,10416,11134,12201,13290,14009,15484,16693,17877,19530,20745,22277,23449,25286,26505,28297,29916,31359,32544,34006,35507,36969,37149,38569,39211,40269,40166,40198,40466,40800,40446,40053,39535,38945,38229,36511,35887,34529,32742,31775,29949,28957,27043,25805,24040,23053,21560,19956,18455,17336,16066,14792,13794,12772,12025,11234,10411,9557,8846,8354,7909,7434,7157,6748,6347,6079,5880,5687,5451,5410,5391,5280,5099,5008,4812,4918,4928,4771,4826,4752,4830,4798,4758,4766,4743,4711,4611,4697,4793,4877,4868,4891,5095,5137,5201,5562,5613,5852,6130,6243,6517,7068,7111,7561,7941,8443,8935,9572,9978,10609,11291,11666,12646,12984,13797,14444,14984,15733,16425,17164,17437,18527,18768,19264,19655,20080,20479,20731,20752,20872,21091,20953,21224,20880,20451,20254,19945,19806,19002,18434,17991,17690,16929,16329,15657,15046,14615,14002,13427,12962,12348,12131,11694,11116,10729,10372,10086,9785,9488,9261,9204,9028,9022,9051,8992,9099,9179,9343,9256,9714,9859,10269,10435,10787,11637,11902,12744,13688,14330,15724,17065,18530,20156,22468,24871,27767,30707,34400,38576,43196,48934,55044,62311,69849,78741,88673,99686,111696,124904,139878,157002,173505,192816,212761,234746,259191,283906,309502,336855,366729,395503,425395,457751,489041,521036,552921,583472,613863,645574,670842,697267,722983,744804,766295,784070,798330,810250,816327,820568,820555,818327,812781,802128,789889,772894,752027,730030,703823,679422,650323,619079,587589,554896,524272,490238,456421,424980,392007,361271,332800,302608,275002,250017,224957,201804,180523,161735,143693,127991,113178,99298,87825,77171,68306,59981,52730,46714,41566,36748,32816,29582,26935,25022,23284,21781,20747,19835,19444,19164,19142,18658,18940,18929,19245,19244,19461,20006,20047,20433,20645,20510,21055,21070,21042,21325,21301,21153,21035,20530,20402,20156,19611,19678,19020,18435,17936,17353,16770,16289,15715,15172,14811,14260,13636,13058,12699,12179,12153,11472,11239,11067,10613,10469,10271,10385,9858,10150,9964,10129,10040,10471,10527,10630,10905,11155,11378,11774,12073,12320,12375,12920,13272,13677,13941,14177,14700,14696,15126,15668,15462,15594,16014,15746,15995,15931,16028,15973,15915,15636,15722,15315,15272,14956,14566,14443,14335,13839,13425,13201,12901,12492,12187,11947,11782,11269,11175,10961,10467,10232,10210,10012,9725,9544,9512,9239,9180,9144,9014,8851,8999,8992,8854,8910,8784,8934,8945,9115,9134,9130,9185,9388,9485,9649,9793,10083,10238,10501,10664,11165,11175,11724,11748,12399,12923,13504,14109,14664,15137,16140,16911,17854,18772,20045,21299,22261,23829,25747,27682,29268,31826,34152,36747,39406,42519,45144,48940,52980,56933,60950,65587,70544,75367,80565,86347,92356,98247,105440,113219,120183,129012,136531,146092,155960,166375,176487,188462,200695,214227,226970,241801,257644,272403,289226,307234,324890,341803,361291,380989,399384,418448,437089,454947,475979,492831,510654,525922,541841,553716,565011,576242,584871,591931,597049,599096,601377,598857,595949,590816,584843,576229,564719,552782,539365,526390,508669,491729,474636,457902,440218,421911,403845,385830,368081,353969,336874,319383,305432,291874,278132,266437,255272,245059,234985,226869,220202,213396,206796,201474,197375,193932,191023,187670,186998,185296,183517,183095,183068,182598,182890,183680,184790,184531,185598,184978,186439,185537,185694,185435,184962,183415,182648,179912,178119,175807,172315,168527,165122,161274,156706,151390,145490,141410,135913,129418,123482,117884,111629,105259,99408,93449,87467,82164,76702,71402,66513,61341,57168,52845,48993,45202,42217,38647,35888,33750,31563,29500,27622,26191,24468,23524,22109,21310,20443,19989,19213,18814,18486,18308,17766,17768,17451,17605,17112,17331,17123,16976,17110,16726,16763,16791,16630,16695,16924,17001,17129,17481,17963,18177,18960,19312,20045,21091,22244,23656,25349,27235,29801,31669,34691,38059,41718,45892,50473,55738,61636,67546,74354,81871,89606,98680,107361,117284,127974,137789,148732,161354,173471,185650,197636,211821,223903,235297,249029,260009,272278,283813,294433,305578,313800,322464,329738,336705,340612,345082,347056,348765,348223,346596,343546,340013,334282,328043,320148,311692,302217,292197,281577,269515,257648,244673,232090,219157,206511,192014,179929,167617,155302,143547,132739,121084,111001,100626,91436,82298,74123,66693,60568,53631,47864,42843,38096,33828,29882,26436,23328,20485,18369,15982,14393,13030,11543,10509,9563,8685,8140,7370,7170,6813,6611,6106,6192,6075,6067,5973,6082,6065,6086,6173,6295,6401,6659,6725,6954,7117,7254,7408,7585,7810,8029,8111,8203,8266,8329,8477,8690,8727,8872,8983,8955,8996,9056,9166,9106,9001,8912,8966,9010,9013,8865,8668,8765,8557,8648,8526,8438,8589,8581,8803,8690,8839,9219,9423,9877,10047,10556,11078,11676,12315,13042,14026,15384,16391,18047,19597,21294,23034,24798,27226,29315,32156,34387,37424,40482,43582,47070,50058,53736,57605,61185,64819,67787,71626,75855,79225,82650,86623,89468,92572,94778,97562,99879,101597,103590,104196,105721,106454,106347,106384,105279,104272,103246,102543,99163,97149,94728,91951,89319,86029,82150,79174,75564,71593,68388,64571,60944,57667,54085,51415,48127,44582,41886,39444,36675,34478,32074,30356,28924,27093,25893,24663,23833,23364,22969,22447,22397,22556,22796,22889,23216,24090,24677,25616,26636,27660,28862,30309,31409,32946,34849,36390,37934,39986,41962,43602,45928,48053,49804,51688,54035,56299,58390,60566,62550,64340,66252,68103,69782,71611,73173,74695,76375,77531,78786,79229,80037,80653,81098,80651,81102,80568,80074,79671,78812,77883,76544,75190,73686,71862,69930,68086,66039,63586,61305,59062,56632,54344,52005,49112,46782,44428,42182,40073,38055,35518,33223,31131,29595,27940,26175,24503,22822,21519,20470,19400,18144,16863,16234,15390,14540,13848,13341,12811,12399,11899,11508,11184,10765,10560,10379,10288,10111,10037,9776,9685,9836,9671,9529,9556,9543,9697,9500,9576,9332,9713,9486,9499,9285,9317,9278,9223,9084,9092,8985,8829,8623,8674,8343,8226,7915,7751,7447,7269,7102,6678,6605,6393,6067,5820,5784,5394,5182,4982,4882,4822,4461,4174,4083,3953,3675,3645,3527,3411,3270,3228,3142,3002,3038,2880,2865,2747,2822,2593,2626,2578,2546,2483,2531,2493,2408,2422,2385,2430,2294,2184,2323,2187,2244,2188,2125,2121,2134,2028,2007,1958,1951,1922,1965,1853,1927,1822,1809,1805,1790,1730,1764,1676,1672,1739,1716,1728,1720,1695,1702,1728,1683,1639,1636,1637,1703,1691,1653,1633,1668,1672,1639,1649,1702,1681,1640,1665,1664,1650,1697,1673,1579,1651,1659,1586,1573,1633,1555,1559,1608,1555,1545,1517,1532,1532,1480,1469,1476,1539,1506,1448,1395,1421,1499,1427,1389,1383,1361,1361,1388,1352,1373,1426,1361,1357,1404,1328,1290,1284,1378,1294,1323,1355,1290,1326,1318,1396,1238,1266,1280,1290,1273,1305,1262,1322,1386,1286,1309,1273,1300,1299,1268,1364,1297,1358,1277,1275,1331,1313,1325,1283,1335,1409,1389,1424,1376,1419,1398,1421,1483,1389,1418,1448,1477,1516,1544,1515,1520,1605,1567,1678,1629,1684,1691,1654,1695,1755,1745,1754,1793,1764,1818,1873,1884,1861,1924,1982,1980,2047,2014,2063,2029,2059,2090,2178,2050,2096,2181,2114,2172,2266,2200,2246,2231,2286,2216,2287,2142,2354,2412,2296,2450,2398,2474,2391,2420,2339,2485,2530,2400,2512,2519,2434,2429,2500,2476,2506,2457,2501,2395,2354,2460,2320,2356,2330,2447,2330,2287,2314,2255,2224,2179,2227,2146,1979,2079,1969,2009,1962,2022,1913,1822,1907,1870,1736,1891,1742,1675,1743,1780,1701,1712,1705,1676,1675,1606,1658,1739,1547,1571,1572,1599,1555,1532,1608,1529,1577,1572,1599,1586,1567,1554,1588,1524,1648,1573,1610,1571,1555,1627,1617,1578,1662,1604,1620,1596,1655,1630,1671,1613,1643,1632,1625,1621,1616,1661,1669,1637,1736,1638,1735,1698,1760,1731,1733,1770,1790,1753,1821,1798,1780,1823,1822,1835,1934,1890,1976,1854,1930,1964,1869,1946,1884,1948,2024,1999,1906,1989,2077,2064,2031,1973,2002,1981,1990,2076,2072,1950,2038,2047,1987,2033,2078,2040,2114,1996,2033,2056,2070,2093,2074,2092,2018,2064,2040,2029,2099,1962,2150,2140,2114,2008,2024,2026,2047,2073,2084,2022,2060,2091,2087,2096,2051,2101,2133,2016,2077,2118,2111,2191,2098,2158,2069,2083,2139,2118,2074,2117,2091,2183,2213,2172,2266,2150,2154,2245,2231,2295,2257,2239,2172,2277,2292,2275,2314,2292,2371,2344,2351,2331,2404,2414,2336,2451,2412,2423,2434,2473,2384,2343,2405,2440,2456,2402,2541,2442,2430,2487,2493,2514,2520,2580,2589,2545,2587,2664,2562,2540,2665,2549,2603,2678,2693,2802,2688,2792,2742,2787,2721,2695,2646,2774,2887,2870,2949,2910,2994,2959,2880,2962,3078,3006,3055,2961,2970,3141,3187,3049,3259,3135,3191,3066,3169,3165,3326,3140,3274,3204,3292,3308,3296,3251,3276,3387,3369,3259,3374,3420,3233,3424,3382,3280,3323,3381,3344,3310,3391,3305,3333,3389,3330,3477,3401,3317,3387,3454,3491,3428,3472,3463,3519,3590,3407,3559,3579,3500,3465,3645,3682,3651,3681,3707,3748,3671,3789,3804,3686,3710,3828,3892,3838,3965,4064,3993,4080,4035,3858,4024,4047,4002,4140,4157,4154,4069,4132,4141,4216,4097,4414,4289,4248,4282,4429,4323,4375,4451,4360,4423,4390,4559,4408,4544,4657,4534,4498,4566,4647,4598,4685,4581,4566,4698,4626,4620,4843,4687,4788,4832,4749,4853,4763,4729,4804,4832,4858,4938,4826,4840,5012,4930,4811,4927,4923,4942,5004,4932,4930,4956,4921,4888,5005,4921,4947,5034,4882,4934,5196,5066,5136,5091,5058,5059,5051,5171,5078,5036,5188,5197,5342,5253,5265,5405,5522,5353,5516,5609,5731,5712,5863,5937,5900,6035,5960,6226,6198,6375,6510,6611,6680,6824,7200,7283,7474,7747,7819,8349,8530,8889,9245,9662,9984,10660,11322,11953,12425,13446,14309,15039,16122,16984,18440,19474,20608,21927,23748,25053,26911,28594,30701,32418,34478,37109,39130,41042,43916,46411,48980,52010,54747,57580,59656,63080,65742,68708,71248,74118,76948,79423,82598,84798,87172,89966,91962,94734,96803,97941,100070,102038,102831,104502,104667,105303,105586,105751,106031,105758,104827,104290,103853,102197,100880,99160,97088,95472,93247,90398,88001,86183,82838,80537,77436,74130,72215,68721,65923,63160,60145,56830,54398,52106,49225,47311,44362,42064,40068,37948,35755,33657,31989,31028,28692,27393,25762,24964,24066,22547,21957,21142,20387,19682,19127,18766,18302,17750,17516,17307,17169,17115,17239,17242,16907,16975,16938,17037,17082,17308,17765,17987,17889,18056,18350,18391,18545,18913,19352,19565,19768,20116,20728,21153,21127,21323,22177,22262,22878,22983,23566,24135,24145,24757,25426,25772,26191,26576,27165,27549,28144,28313,29114,29515,29993,30820,31293,31768,32228,33042,33609,34266,35194,35656,36095,36882,37135,38043,38330,39330,40230,40815,41307,41932,42377,43398,44150,44717,45436,46076,46920,47772,48399,49290,49991,50752,51382,51776,52582,53800,53995,55198,55452,56214,57160,57570,58868,58970,59948,60389,61096,61735,62660,63243,64019,64754,65136,65808,66639,67532,68320,68663,69084,69525,69799,70887,71244,71903,72720,74023,73862,74542,74530,75358,75888,76397,77048,77468,77682,78002,79055,79348,79686,79684,80499,80713,81133,81158,81612,82048,82658,83244,83079,84127,84434,84378,83986,84583,84887,85665,85674,85817,86533,86315,86766,87112,87495,87845,87309,87981,88472,88729,88523,88949,88837,89074,89150,89222,89140,89918,89992,89944,90931,90715,90782,90760,91568,91989,91884,91989,92532,92974,92649,92647,93766,93930,93835,94093,94584,94429,95380,95659,95998,96009,96746,96971,97617,97053,97522,98572,98695,99271,99247,99058,100015,100238,101320,101378,102270,102688,102998,103908,103924,104132,104888,106308,106067,106555,107630,108630,108797,109093,110474,110998,111812,112500,113903,114520,115663,116809,117679,119357,120993,122093,124096,125157,126880,129154,131826,133337,136086,138828,142306,144743,148478,152274,155740,160255,164748,169695,174869,180406,186575,192745,198693,207200,214120,221327,230093,239461,248044,257517,266900,277689,287815,298611,310227,321854,332905,345524,357127,370350,382738,395759,409252,421685,435090,447290,460325,472484,484462,497071,507581,519965,528869,538469,548388,556359,564604,572483,577761,584047,588583,591238,595037,596872,597485,596266,596223,591622,589437,583014,577361,569846,562031,551546,543545,532550,519875,509851,495718,481317,467241,453254,437291,420798,405980,391353,375383,359285,342422,327628,311407,296379,281175,267176,252007,238896,225656,212267,199947,188658,177237,166441,156064,146827,136731,129540,120195,113972,106248,100032,93684,88948,83136,78001,73220,69708,66298,62392,59372,56663,53827,50901,49103,46668,45253,43082,41692,40058,38811,37855,36293,35222,33931,33373,32574,31541,31105,30487,29825,29150,28538,27954,27655,27527,27143,26655,26617,26117,25652,25725,25471,24978,24915,24409,24214,24085,23833,23822,23538,23530,23180,22986,22827,22498,22274,22540,22286,21995,21737,21563,21360,21157,21082,20879,20739,20372,19910,20071,19577,19199,19206,18859,18526,18470,18262,17877,17381,17649,16873,16884,16632,16129,16154,16058,15264,15462,15023,15000,14671,14549,14143,13917,13756,13565,13572,13337,13126,12998,12700,12484,12438,12089,11955,11691,11516,11619,11161,11087,11137,10821,10619,10422,10241,10293,10047,9858,9995,9853,9554,9466,9362,9146,9280,8951,8795,8684,8694,8422,8253,8112,7863,7879,7835,7641,7661,7324,7206,7243,6950,6820,6878,6757,6647,6504,6248,6129,6189,6083,5964,5775,5672,5544,5516,5343,5322,5175,5145,5019,4970,4750,4730,4575,4406,4496,4394,4290,4122,4044,4051,3986,3838,3831,3633,3516,3498,3475,3461,3349,3273,3243,3080,3171,3035,2937,2930,2829,2849,2784,2718,2602,2658,2533,2485,2511,2376,2442,2415,2272,2286,2170,2272,2243,2090,2056,2117,2189,2005,1941,1960,1983,1901,1918,1866,1902,1819,1722,1789,1749,1779,1833,1801,1753,1723,1756,1733,1676,1704,1648,1743,1606,1624,1656,1642,1652,1608,1684,1673,1555,1636,1553,1564,1597,1532,1566,1567,1502,1514,1506,1539,1374,1410,1472,1425,1478,1423,1363,1349,1365,1321,1283,1256,1263,1252,1270,1148,1217,1214,1173,1226,1081,1197,1139,1144,1150,1114,1163,1073,1101,1082,1033,1114,1016,1029,1088,1055,1083,1055,1016,1074,986,961,1047,1011,1006,1015,1024,1051,1036,1053,1068,1113,1030,1120,1068,1105,1068,1019,1071,1147,1101,1140,1061,1122,1131,1163,1037,1177,1091,1121,1093,1158,1072,1119,1152,1154,1141,1135,1046,1159,1091,1130,1081,1104,1157,1144,1105,1094,1196,1072,1102,1097,1111,1088,1134,1127,1160,1124,1117,1204,1176,1180,1222,1172,1296,1209,1274,1270,1302,1303,1323,1318,1326,1338,1375,1285,1410,1420,1403,1460,1493,1495,1517,1494,1511,1578,1548,1516,1510,1579,1520,1648,1614,1646,1596,1537,1663,1574,1490,1532,1526,1492,1642,1507,1571,1396,1456,1497,1305,1390,1357,1346,1330,1293,1248,1228,1194,1162,1224,1134,1129,1059,1120,1043,1011,1027,971,989,945,964,969,916,917,908,901,911,883,869,857,922,830,870,912,955,904,952,974,993,999,994,998,1067,1037,1093,1115,1108,1181,1192,1118,1227,1304,1285,1362,1350,1360,1355,1368,1407,1483,1539,1474,1560,1482,1589,1614,1598,1656,1642,1614,1648,0]
        standard2=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,2,6,11,22,31,61,105,165,308,470,803,1249,1964,3050,4399,6446,9285,13051,18370,25303,34315,45460,60196,78404,101859,129481,163079,204899,254371,313352,382522,460084,552230,652596,763961,885654,1011265,1140275,1269510,1390037,1503116,1599868,1679947,1730825,1763056,1762391,1739057,1686982,1610746,1515458,1402818,1277117,1145556,1010390,875508,751412,630230,524268,425584,340555,267727,208776,159026,118611,87255,63615,45494,31784,21919,14781,9841,6505,4017,2626,1698,1032,598,336,223,154,88,56,33,33,16,13,20,16,12,20,10,6,9,10,6,7,5,5,8,4,9,4,7,4,5,4,11,24,40,117,200,327,580,810,965,1085,1084,1068,1023,1069,1025,1139,1028,987,946,1002,986,970,1020,940,916,962,861,928,891,913,859,981,890,881,876,984,901,884,910,899,915,880,847,859,879,819,841,827,860,802,837,877,853,807,846,832,818,805,819,802,780,848,747,815,754,800,744,757,832,820,759,748,835,794,750,759,713,773,786,698,735,706,707,732,727,701,666,768,671,707,735,672,677,681,659,668,668,673,643,642,662,697,633,603,619,639,630,602,631,635,638,628,585,594,604,638,572,548,592,558,604,645,581,600,593,580,587,606,574,587,622,596,570,599,592,620,612,629,636,584,579,565,570,610,611,559,584,619,598,616,604,628,646,631,640,638,653,666,643,613,640,690,690,681,691,716,666,640,814,670,720,735,708,716,682,795,726,753,829,833,822,801,855,857,829,826,843,906,830,889,825,891,872,876,915,874,855,883,935,909,920,978,910,937,938,999,1057,1013,1010,967,1117,1085,1061,1114,1161,1147,1137,1175,1144,1124,1245,1167,1212,1287,1274,1239,1280,1327,1314,1290,1287,1401,1374,1331,1413,1370,1409,1437,1406,1386,1429,1446,1383,1466,1434,1383,1425,1431,1372,1383,1380,1393,1442,1449,1477,1424,1472,1458,1513,1426,1552,1449,1589,1592,1694,1800,1819,1853,1956,2169,2258,2456,2559,2762,3011,3189,3421,3746,3978,4248,4589,4869,4918,5229,5297,5603,5679,5726,5753,5723,5741,5718,5558,5498,5501,5327,5238,4981,4859,4558,4358,4221,4207,4029,3870,3825,3580,3623,3507,3428,3354,3342,3273,3224,3161,3170,3139,2965,3069,2854,2955,2920,2783,2730,2701,2592,2574,2462,2451,2415,2361,2279,2220,2214,2140,2171,2101,2047,1981,1842,1834,1801,1797,1632,1540,1592,1494,1449,1426,1314,1390,1334,1214,1215,1167,1138,1160,1121,1062,1025,1004,1046,969,991,930,942,992,903,872,900,886,921,902,940,940,1000,956,956,1023,1036,1214,1184,1326,1323,1380,1468,1613,1683,1810,1961,2002,2129,2208,2327,2608,2593,2746,2881,3065,3105,3342,3288,3401,3442,3565,3765,3851,3789,3871,4031,4060,4205,4087,4165,4293,4269,4357,4385,4326,4252,4373,4379,4385,4273,4427,4309,4103,4212,4148,4087,4062,4069,3997,3903,3729,3633,3590,3508,3422,3248,3177,3038,3050,2871,2847,2731,2655,2496,2543,2497,2386,2233,2128,2090,2025,2050,1905,1864,1770,1685,1703,1629,1677,1456,1535,1407,1290,1368,1322,1270,1215,1112,1137,1068,1043,996,938,880,943,893,832,847,883,784,793,800,761,747,755,727,753,756,759,725,709,736,733,692,696,725,686,707,710,729,722,746,823,792,819,900,926,918,1005,1067,1198,1251,1321,1408,1591,1599,1813,1936,2157,2157,2202,2488,2615,2811,2942,3013,3045,3189,3348,3317,3378,3361,3437,3338,3278,3321,3277,3139,3009,2941,2893,2823,2780,2702,2608,2545,2542,2474,2283,2330,2194,2328,2256,2280,2393,2454,2631,2580,2579,2803,2841,2940,3035,3197,3340,3397,3450,3561,3565,3583,3675,3798,3725,3741,3703,3750,3708,3571,3727,3528,3479,3419,3409,3405,3320,3466,3509,3459,3546,3378,3543,3474,3593,3577,3584,3645,3653,3560,3596,3539,3577,3605,3550,3494,3284,3265,3196,3090,2999,2955,2758,2683,2497,2375,2309,2177,2177,2072,1972,1792,1824,1688,1663,1575,1580,1479,1498,1435,1440,1417,1361,1312,1309,1336,1305,1218,1265,1252,1262,1264,1266,1273,1247,1219,1272,1366,1366,1371,1422,1416,1479,1545,1531,1648,1721,1841,1845,1975,2084,2150,2211,2357,2563,2674,2809,2855,2895,2980,3157,3204,3140,3268,3351,3462,3506,3354,3280,3252,3184,3076,2911,2876,2722,2635,2404,2184,2047,1977,1815,1692,1544,1405,1365,1213,1125,994,960,830,767,735,686,652,612,560,586,538,550,520,547,565,506,516,555,548,518,568,588,602,584,626,616,660,745,775,774,806,868,873,953,935,1014,1153,1123,1138,1281,1384,1417,1472,1644,1715,1838,1968,1998,2070,2100,2200,2317,2334,2472,2556,2585,2469,2526,2653,2636,2605,2542,2446,2459,2293,2273,2185,2155,2032,1892,1891,1759,1581,1590,1532,1522,1475,1325,1261,1220,1203,1153,1230,1142,1175,1197,1188,1215,1286,1275,1325,1331,1437,1386,1472,1498,1528,1497,1510,1526,1560,1456,1504,1422,1445,1481,1377,1299,1427,1372,1449,1414,1362,1449,1408,1487,1556,1577,1589,1722,1750,1864,1953,2068,2186,2284,2364,2547,2591,2739,2971,3085,3011,3149,3161,3309,3414,3430,3569,3583,3548,3532,3413,3444,3324,3320,3205,3060,3072,2920,3065,2857,2828,2762,2741,2665,2619,2589,2629,2539,2582,2630,2658,2609,2612,2596,2657,2691,2686,2650,2575,2731,2564,2464,2455,2492,2434,2500,2302,2203,2248,2167,2062,2075,1944,1934,1930,1911,1984,1890,1987,2060,2007,2056,2105,2264,2330,2559,2499,2602,2756,2884,2989,3127,3268,3340,3442,3652,3758,3857,3907,4136,4201,4197,4427,4502,4548,4844,4805,4976,5118,5280,5365,5574,5541,5701,5851,5828,5868,5930,6091,6076,6242,5974,5858,6012,5871,5836,5827,5748,5640,5484,5379,5152,5103,4974,4871,4755,4532,4309,4239,4010,3867,3695,3598,3384,3282,3200,3057,2998,2782,2743,2649,2544,2589,2488,2485,2505,2429,2490,2513,2508,2587,2661,2699,2786,2883,2904,2962,2984,3149,3209,3194,3346,3454,3448,3528,3498,3539,3582,3551,3555,3620,3521,3590,3601,3721,3605,3585,3624,3770,3788,3801,3964,3971,3975,4362,4330,4500,4830,4902,5080,5388,5441,5714,5902,5956,6167,6260,6616,6723,6699,6780,6786,6795,6822,6715,6619,6606,6402,6464,6110,5889,5815,5657,5431,5348,5090,4659,4571,4501,4226,4118,3884,3763,3550,3546,3394,3395,3465,3366,3304,3246,3263,3372,3354,3308,3368,3386,3444,3527,3549,3615,3717,3724,3719,3680,3774,3745,3861,3810,3710,3851,3830,3809,3734,3813,3641,3613,3615,3654,3576,3595,3676,3633,3575,3607,3704,3771,3829,3798,3896,4084,4311,4274,4617,4649,5010,5227,5337,5645,5853,6139,6429,6648,6827,7145,7409,7781,7806,8058,8319,8421,8520,8623,8627,8750,8694,8757,8667,8664,8795,8426,8267,7913,7805,7661,7234,7194,6767,6748,6349,6044,5965,5668,5490,5290,5072,5035,4884,4611,4569,4494,4346,4177,4257,4165,4067,4110,3967,4091,3973,3950,3886,3631,3798,3797,3678,3705,3584,3654,3538,3465,3326,3469,3400,3418,3411,3286,3227,3325,3463,3302,3553,3536,3556,3639,3906,3858,3990,4083,4146,4388,4411,4378,4840,4742,4781,5046,5170,5444,5426,5466,5548,5714,5816,6117,6119,6428,6465,6654,6753,7072,7248,7354,7568,7753,8116,8195,8569,8760,9060,9302,9477,9846,9990,10174,10450,10595,10842,10974,11045,11098,11170,11276,11142,11056,10938,10907,10746,10562,10647,10092,9953,9678,9507,9331,9088,8764,8234,8021,7872,7434,7231,7031,6711,6303,6150,5775,5737,5374,5263,4892,4756,4586,4471,4439,4178,4078,4100,4045,3984,4050,3926,4196,4159,4215,4329,4474,4398,4630,4752,4695,4948,5260,5227,5396,5460,5427,5563,5737,5803,5820,5937,5830,5962,5932,5742,5769,5838,5693,5589,5616,5522,5596,5453,5432,5493,5481,5474,5606,5680,5724,6005,5995,6335,6517,7026,7395,7794,7978,8389,9012,9481,9861,10486,10930,11224,11500,11914,12358,12828,12960,13237,13455,13474,13734,13748,13721,13772,13310,13226,13318,12965,12601,12341,11773,11496,10983,10606,10243,9751,9343,8952,8522,7962,7688,7406,6899,6461,6582,6336,5834,5729,5726,5596,5428,5350,5404,5504,5467,5388,5543,5485,5581,5623,5708,5859,5856,6048,6083,6084,6421,6163,6315,6256,6271,6418,6353,6464,6482,6324,6232,6155,6038,6027,5811,5781,5726,5475,5572,5258,5235,5220,5246,4982,5047,5047,5096,5140,5110,5138,5356,5383,5672,5766,5970,6256,6606,6918,7430,7526,7985,8535,8982,9253,9752,10318,10796,11262,11867,11963,12660,12986,13743,13940,14033,14609,14665,15379,15295,15388,15488,15684,15687,15665,15328,15149,15001,15013,14473,14134,13976,13652,13222,12815,12552,12068,11743,11381,11070,10828,10647,10128,9794,9688,9436,9375,9038,8950,8785,8669,8613,8377,8144,8314,8115,8185,8062,8076,8099,7821,7590,7708,7540,7247,7018,6967,6857,6780,6498,6231,6139,5985,5894,5752,5568,5384,5248,5098,4962,4864,4715,4747,4629,4452,4446,4441,4283,4141,4221,4117,4038,4097,4057,4036,3897,3858,3821,3789,3710,3638,3736,3788,3789,3808,3967,3875,3952,4078,4185,4340,4517,4659,4839,5106,5520,5806,6053,6248,6557,7198,7662,8103,8415,8935,9312,9755,10137,10749,10972,11404,11919,12374,12812,13164,13287,13669,13687,13861,13956,14150,14029,13874,13883,13733,13416,13293,13211,12839,12600,12348,11762,11536,11068,10797,10427,10135,9694,9205,8806,8648,8268,7979,7711,7246,6891,6760,6305,6097,5820,5701,5509,5391,5224,5040,5052,4887,4826,4754,4805,4611,4655,4561,4701,4535,4748,4823,4893,4903,5006,5063,5237,5196,5472,5753,5719,5662,5947,6070,6095,6337,6417,6590,6597,6661,6647,6842,6897,6834,6927,6879,6781,6854,6851,6671,6728,6639,6742,6608,6340,6502,6344,6405,6336,6349,6608,6672,6787,6762,6991,7160,7531,7591,8046,8553,8951,9369,9781,10155,10822,11341,12106,12583,13065,13625,14365,14993,15478,16107,16666,16926,17448,17982,18097,18607,18581,18673,18775,18688,18821,18815,18720,18332,18036,17770,17135,16738,16252,15780,15127,14480,13726,13459,12739,12204,11513,10827,10220,9776,9262,8622,8184,7636,7257,6715,6466,5948,5584,5392,4928,4632,4469,4435,4066,3827,3688,3561,3471,3328,3300,3258,3220,3087,3053,2979,2961,2901,2866,2926,2874,2850,2731,2699,2731,2764,2714,2620,2630,2692,2613,2598,2646,2524,2550,2582,2559,2514,2567,2529,2484,2528,2569,2588,2560,2675,2632,2659,2672,2826,2853,2857,2981,3090,3178,3433,3462,3757,3813,4123,4482,4680,4843,5413,5602,5849,6244,6761,7015,7527,8124,8566,8965,9487,9964,10519,11307,11454,12229,12401,12811,13196,13878,13887,14196,14274,14568,14538,14664,14759,14716,14716,14418,14216,13969,13851,13420,12791,12643,12244,11733,11478,10842,10441,9870,9325,9171,8498,8276,7716,7295,6856,6492,6156,5823,5436,5128,4932,4571,4479,4302,4095,3819,3598,3460,3402,3224,3256,3137,3061,3084,2896,2859,2754,2775,2820,2740,2699,2782,2683,2758,2874,2785,2822,2781,2983,3029,2989,2951,2980,3095,3044,3210,3103,3156,3280,3243,3287,3357,3432,3479,3413,3466,3402,3434,3509,3475,3460,3553,3645,3595,3640,3597,3628,3578,3690,3780,3778,3790,3842,4019,3970,4132,4197,4305,4477,4650,4889,5032,5187,5371,5798,6057,6205,6701,6848,7319,7529,7951,8368,8597,9153,9356,9853,10059,10344,10622,10926,11373,11615,11825,11979,12112,12403,12428,12543,12662,12385,12515,12383,12227,12252,11836,11961,11452,11302,11040,10879,10465,10071,9916,9652,9334,9058,8844,8514,8297,7804,7747,7336,7163,6819,6523,6346,5994,6148,5802,5727,5462,5269,5289,5103,4902,4771,4777,4710,4585,4785,4559,4720,4616,4773,4759,4866,4948,5187,5243,5334,5473,5697,5972,6299,6351,6630,6905,7019,7541,7796,8098,8343,8683,8753,9136,9515,9704,9747,9879,10012,10074,10264,10164,10318,10570,10455,10494,10505,10312,10245,9912,9782,9591,9555,9203,8932,8795,8732,8425,8245,8072,7729,7782,7549,7459,7335,7180,7374,7196,7310,7563,7741,7896,8155,8294,8483,9113,9468,9988,10479,10901,11389,11825,12616,13181,13765,14491,14944,15408,15847,16313,16825,17324,17899,18053,18119,18387,18949,18751,18831,18971,18839,18652,18289,18149,17798,17474,17066,16490,15923,15561,14838,14243,13751,12855,12477,11735,11278,10741,9768,9519,8658,8387,7923,7500,7090,6753,6448,6066,5922,5857,5646,5573,5451,5358,5237,5403,5304,5457,5623,5678,5907,6150,6407,6462,6604,6810,7087,7319,7427,7751,7850,7993,8157,8383,8414,8672,8753,8743,8697,8623,8825,8657,8557,8533,8462,8253,8189,8025,7784,7524,7492,7235,6928,6827,6492,6374,6125,5903,5566,5396,5147,4989,4921,4587,4341,4202,4218,3944,3907,3730,3628,3520,3481,3509,3455,3558,3503,3560,3766,3707,3867,3981,4073,4277,4327,4675,4978,5174,5567,5663,6002,6457,6766,6906,7402,7733,8339,8520,8889,9356,9670,10110,10520,10571,10935,11242,11331,11735,11845,11900,12063,12276,12138,11823,11904,11889,11823,11509,11427,11139,10822,10586,10264,9977,9642,9279,8764,8295,7867,7389,6957,6687,6119,5975,5402,5093,4585,4368,3980,3671,3296,3147,2869,2641,2350,2179,1977,1702,1644,1447,1333,1201,1139,1044,998,867,844,764,767,692,705,665,587,568,611,597,591,611,606,677,621,686,742,773,753,726,778,930,933,1000,1066,1051,1124,1155,1214,1315,1426,1386,1553,1646,1653,1776,1883,1874,2015,2040,2044,2157,2151,2226,2370,2422,2526,2444,2527,2618,2558,2682,2677,2662,2646,2654,2580,2691,2619,2607,2558,2509,2596,2474,2442,2309,2227,2276,2116,1991,1966,2002,1932,1873,1745,1704,1570,1523,1472,1512,1320,1302,1227,1216,1183,1174,1092,1050,971,1012,986,946,940,905,906,872,838,872,905,856,826,873,793,825,831,823,798,839,813,844,862,861,847,893,936,928,887,1008,963,1022,1120,1140,1163,1217,1335,1340,1456,1492,1624,1686,1793,1932,2098,2260,2335,2514,2629,2818,2921,3073,3279,3336,3652,3697,3904,4095,4197,4386,4628,4638,4716,4911,5071,5001,5363,5332,5489,5425,5509,5401,5411,5410,5506,5574,5391,5237,5249,5204,5140,5000,4945,4848,4641,4518,4371,4304,4181,4034,3966,3725,3686,3596,3341,3362,3288,3146,3124,2987,3057,2926,2925,2801,2797,2842,2768,2895,2916,2893,2961,2913,2972,3144,3208,3222,3276,3391,3484,3756,3975,3984,4180,4277,4320,4536,4751,4861,5022,5225,5495,5606,5697,5846,6215,6275,6502,6450,6575,6750,6930,7090,7127,7168,7330,7320,7227,7384,7354,7393,7417,7399,7171,7274,7063,6951,6845,6751,6469,6385,6355,6076,5825,5633,5657,5173,5050,4974,4792,4449,4377,4279,4081,3993,3902,3636,3699,3550,3465,3303,3262,3287,3307,3192,3197,3304,3367,3399,3331,3589,3563,3728,3849,3947,4270,4455,4543,4749,5033,5213,5621,5866,5998,6289,6693,6889,7212,7661,7706,8128,8557,8728,8921,9224,9630,9647,9946,10043,10319,10414,10699,10692,10809,10981,10886,10964,10784,10632,10606,10194,10164,10094,9937,9554,9586,9168,8831,8613,8331,8034,7784,7257,7161,6717,6367,6091,5714,5516,5378,5097,4792,4446,4310,4242,4011,3926,3761,3808,3729,3646,3759,3700,3864,4045,4075,4089,4390,4571,4781,5144,5483,5638,6066,6536,6898,7489,7675,8150,8838,9327,9605,10420,10806,11517,11943,12528,13111,13495,13959,14534,15160,15409,15837,16184,16738,16998,17453,17613,17574,17737,17673,18149,18035,17911,17854,17780,17552,17567,17002,16610,16318,16278,15948,15412,14969,14553,14223,13637,13272,12837,12262,11926,11675,11016,10829,10388,10189,9835,9525,9406,9036,8823,8876,8459,8377,8244,8221,8141,8092,7992,7765,7708,7964,7645,7674,7590,7559,7396,7668,7375,7273,7129,7097,6786,6818,6566,6423,6171,6115,5861,5630,5356,5091,5008,4665,4461,4227,4006,3900,3566,3503,3250,3001,2806,2560,2389,2222,2047,1918,1837,1616,1532,1457,1266,1226,1154,1131,1021,928,851,877,833,825,740,785,678,735,778,781,755,886,856,918,994,1040,1135,1281,1287,1417,1611,1762,1958,2074,2258,2401,2742,3018,3229,3658,3929,4310,4639,5026,5501,5946,6332,6797,7146,7582,8258,8972,9695,10209,10968,11428,11746,12567,13182,13850,14191,14809,15363,15931,16556,17036,17520,18085,18144,18542,18964,19204,19494,19350,19696,20072,19761,19634,19398,19372,19225,18840,18659,18045,17702,17030,16899,16291,15704,15060,14531,14196,13618,12887,12370,11776,10954,10491,9957,9186,8722,8310,7609,7194,6662,6191,5712,5242,4907,4588,4204,3918,3703,3223,2947,2778,2473,2387,2214,1923,1771,1688,1451,1386,1231,1197,1125,1018,916,862,773,767,711,651,627,614,556,546,503,525,481,476,455,441,434,388,383,390,375,474,441,442,471,442,468,493,473,495,524,529,539,544,591,577,566,668,674,694,713,800,792,873,941,1027,1021,1045,1107,1202,1353,1353,1433,1448,1627,1681,1884,2015,2114,2204,2400,2574,2845,2961,3214,3363,3710,3902,4284,4417,4826,5078,5397,5803,6229,6568,6995,7591,7836,8342,8825,9365,9881,10292,11054,11481,11814,12435,12879,13505,13794,14492,14976,15429,16000,16202,16530,16807,17234,17506,17755,18158,18251,18414,18488,18523,18285,18744,18344,18135,18259,17634,17505,17200,16790,16499,16007,15603,14984,14542,14209,13608,13150,12622,11842,11265,10950,10148,9697,9090,8563,8012,7700,7014,6703,6197,5906,5325,5015,4766,4461,4158,3900,3645,3334,3166,2948,2885,2639,2578,2447,2244,2218,2059,2014,1910,1846,1806,1743,1616,1626,1645,1612,1577,1551,1511,1483,1515,1394,1435,1397,1351,1302,1262,1264,1236,1156,1171,1111,1105,1048,1021,941,912,924,868,900,825,785,748,703,668,672,663,617,622,608,572,585,582,599,528,504,526,532,558,543,530,542,525,552,586,617,608,676,686,692,708,788,767,817,914,898,903,1007,971,1007,1154,1111,1168,1150,1192,1231,1332,1339,1387,1432,1396,1497,1539,1548,1559,1615,1644,1692,1736,1747,1785,1807,1949,1840,1934,2021,1974,2063,2119,2257,2153,2234,2262,2297,2347,2508,2447,2533,2627,2599,2713,2762,2791,2926,2861,2951,2899,3129,3055,3115,3202,3085,3213,3293,3231,3213,3307,3295,3264,3242,3118,3101,3047,3066,3012,2858,2996,2757,2792,2704,2647,2550,2452,2443,2300,2126,2149,2134,2025,1888,1849,1747,1703,1688,1650,1530,1472,1519,1405,1369,1356,1284,1237,1231,1156,1201,1168,1165,1110,1174,1086,1060,1067,1064,1124,1075,1111,1064,1017,1126,1113,1090,1107,1115,1134,1131,1157,1098,1111,1113,1135,1164,1123,1145,1127,1155,1223,1257,1282,1201,1264,1191,1202,1287,1307,1334,1343,1358,1340,1337,1450,1481,1503,1514,1553,1498,1618,1560,1693,1663,1831,1844,1853,1866,1905,1927,2055,2076,2054,2159,2216,2214,2298,2354,2393,2416,2438,2462,2572,2562,2608,2668,2696,2677,2782,2760,2783,2739,2808,2712,2890,2813,2831,2822,2962,2890,2946,2808,2941,2847,2949,2858,2875,2948,2931,2997,2875,2947,2859,2971,2943,2967,3099,3104,3051,3094,3099,3154,3299,3186,3372,3376,3511,3589,3641,3745,3735,3736,3869,3901,4023,4162,4254,4184,4269,4312,4479,4656,4516,4622,4702,4751,4931,4759,4985,4926,4948,4943,4953,5016,5033,4968,4939,5120,5035,4957,4903,4886,4766,4799,4643,4664,4689,4525,4426,4442,4470,4360,4196,4316,4325,4057,4189,3998,4067,4152,3934,4043,3874,3933,3837,3847,3861,3826,3784,3729,3865,3722,3826,3800,3757,3794,3740,3844,3755,3807,3917,3765,3792,3843,3793,3793,3929,3967,4000,3872,3928,4007,3857,3998,3965,3938,3995,3813,4030,3993,4063,3959,3937,4174,3947,3963,4025,4012,4101,4039,4140,4202,4149,4366,4251,4187,4404,4427,4455,4555,4663,4740,4784,4951,5188,5334,5267,5435,5608,5753,5992,6233,6417,6771,6897,7155,7386,7754,8028,8220,8460,8964,9295,9588,10045,10484,10868,11173,11602,11847,12453,12751,13123,13458,13810,14314,14387,14941,15600,15739,15966,16652,16655,17065,17317,17676,17656,17687,17854,17805,18099,18359,18494,18218,18064,18312,18076,18177,17775,17589,17300,17139,16677,16397,16153,15948,15449,14955,14393,14069,13852,13030,12745,12325,11634,11408,10691,10162,9592,9147,8630,8096,7701,7304,6798,6499,6037,5507,5270,4793,4573,4168,3795,3562,3283,2988,2923,2571,2406,2120,2048,1840,1708,1518,1432,1313,1160,1136,1003,937,889,794,750,739,664,604,550,549,504,497,493,456,440,431,382,355,353,347,333,305,309,312,273,241,295,291,276,236,260,250,228,222,233,245,238,207,209,217,202,199,222,187,216,220,186,186,199,163,177,158,169,160,160,138,153,133,148,145,151,157,102,116,131,114,140,134,111,128,120,115,119,115,104,105,118,119,118,111,101,92,87,92,79,101,93,85,90,85,82,76,107,84,87,88,69,83,93,67,69,64,67,77,75,60,76,61,67,67,70,78,63,50,59,63,53,62,74,51,53,62,54,56,48,51,46,50,46,52,48,52,39,54,51,52,37,44,57,52,38,40,40,42,25,28,39,28,42,38,39,45,37,33,29,32,38,36,39,27,37,42,31,32,31,34,39,28,35,36,33,29,37,19,34,32,26,25,22,21,27,21,24,26,22,21,22,31,18,23,20,26,19,22,19,18,23,17,17,22,14,22,22,14,23,14,20,25,15,17,16,16,18,23,23,18,22,14,14,14,19,14,9,26,16,21,17,10,18,13,18,18,23,16,9,12,11,21,18,16,11,13,12,14,17,13,7,11,13,28,10,14,19,14,8,8,14,9,17,20,13,14,19,7,18,12,6,10,12,12,13,12,14,12,7,12,6,15,12,13,9,11,14,16,12,13,14,10,14,12,12,7,13,11,20,13,17,8,5,10,11,15,15,16,8,3,11,14,12,11,15,11,7,10,16,6,8,7,7,3,13,9,8,10,15,11,9,9,11,12,10,5,10,9,9,9,12,9,11,9,12,13,13,13,14,8,8,7,11,14,19,13,9,11,17,9,10,15,13,17,12,14,19,17,15,10,18,12,16,15,23,18,11,22,17,13,18,15,13,18,14,14,22,15,17,9,12,13,15,14,19,16,11,10,13,15,4,7,13,10,8,14,11,7,7,8,6,7,10,8,7,11,7,6,7,7,5,3,10,2,7,4,8,6,6,5,7,7,5,3,1,6,4,3,3,2,2,9,4,6,8,5,7,4,4,6,3,5,10,2,7,5,5,5,1,4,4,4]

    par=Parameters(standard)
    par.set_figure(p.gca())
    par.set_line_db_conn(ldb)
    par.set_scale_lines(e_0, ['Mo'], 20.)
    par.calculate(plot=False)
    #par.scan_peakes_cwt(plot=True)

    elements=set("Ne,Ni,Rb,Cl,Os,Ca,Ir,Si,S,P,As,Ar,Fe,W,V,Hf,Zr,Br".split(','))
    #elements=set(["W", "As"])

    ls = ldb.as_deltafun(order_by="keV", element=elements,
            where="not l.name like 'M%' and keV<20.0")
            #where="not l.name like 'M%' and keV<20.0", analytical=True)
    ls=list(ls)
    #pprint.pprint(ls)

    #par.refine_scale(elements=elements-set(['Mo']))
    par.refine_scale(elements=set(['As', 'V']))
    #par.scale.k=0.005004
    #par.scale.b=-0.4843
    par.line_plot(ls, {'analytical':True})
    ybkg = par.approx_background(elements=elements, plot=True, iters=2)

    p.plot(par.x, par.channels, color=(0,0,1), alpha=0.6,)
    p.plot(par.x, ybkg, color=(0,1,1), alpha=0.5, linestyle='-')
    par.set_active_channels(par.channels-ybkg)

    par.refine_scale(elements=set(['As', 'V', 'W']), background=False, plot=False)
    par.model_spectra(elements=elements)

    p.plot(par.x, par.channels-ybkg, color=(0,0,0))
    p.axis('tight')
    ax=list(p.axis())
    ax[2]=-ax[-1]/100.
    ax[-1]=ax[-1]*1.1
    p.axis(ax)
    p.axhline(y=0, xmin=0, xmax=1, color=(0,0,0), alpha=0.3, linestyle='--')
    p.show()

def test2():
    l=Pike(x0=0, fwhm=1, A=1, bkg=0, slope=0)
    print l


if __name__=='__main__':
    test1()
