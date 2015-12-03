
import os, sys, optparse
from matplotlib import pyplot
from mpl_toolkits.axes_grid.axislines import SubplotZero
import matplotlib.ticker as ticker

import random
from scipy import pi, exp
import scipy.integrate
from scipy.interpolate import interp1d
import scipy
import numpy
#numpy.seterr(all='raise')

parser = optparse.OptionParser()
parser.add_option('-L', type=float, default=1.0, help='lunghezza impulso mod in T')
parser.add_option('-T', type=float, default=0.5, help='tempo di simbolo')
parser.add_option('-H', type=float, default=0.5, help='indice di modulazione')
parser.add_option('-M', type=float, default=2.0, help='numero di simboli')
parser.add_option('-g', type=str, default='rec', help='impulso di modulazione: rec, rc')
parser.add_option('-m', '--modo', type=str, default='default', help='metodo di calcolo: default, cpm, cpfsk')
parser.add_option('-d', '--data-dir', type=str, default='data', help='cartella di salvataggio dei dati')
parser.add_option('-n', '--n-simps', type=int, default=1000, help='numero di punti da usare per approssimazione integrale R (default=1000)')
parser.add_option('-r', '--r-simps', type=int, default=500, help='numero di punti da usare per approssimazione integrale per ottenere l\'autocorrelazione (default=500)')
parser.add_option('-i', '--input-file', type=str, default='S', help='File di input da cui generare il grafico')
parser.add_option('-o', '--output-file', type=str, default='output', help='Nome del grafico da generare')
parser.add_option('-p', '--plot', type=str, default='notset', help='grafico da generare (cpm, cpfsk, i, psi)')
options, args = parser.parse_args()
L=options.L
T=options.T
h=options.H
M=options.M
R_INT_N = options.r_simps
S_INT_N = options.n_simps

#if 'plot' in sys.argv[0]:
#    print 'Genero grafico con L=%d h=%.2f M=%d T=%.2f' %(L, h, M, T)


def plot_test(x, y):
    fig = pyplot.figure()
    p = fig.add_subplot(1, 1, 1)
    opt_line = p.plot(x, y, 'b')
    #fig.savefig('test.svg')
    pyplot.show()
    sys.exit(0)

integral = scipy.integrate.quad
def cplx_integral(func, a, b, **kwargs):
    kwargs['limit']=500
    # per l'autocorr va benone
    kwargs['weight'] = 'sin'
    kwargs['wvar'] = 2*pi*h*M
    #kwargs['full_output'] = 1
    def real_func(x):
        return scipy.real(func(x))
    def imag_func(x):
        return scipy.imag(func(x))
    real_integral = integral(real_func, a, b, **kwargs)
    imag_integral = integral(imag_func, a, b, **kwargs)
    return real_integral[0] + 1j*imag_integral[0]

def _simps_integral(f, a, b, n, *args, **kwargs):
    x = numpy.linspace(a, b, n)
    #y = map(f, x)
    uf = numpy.frompyfunc(f, 1, 1)
    y = uf(x)
    return scipy.integrate.simps(y, x, *args, **kwargs)
simps_integral = numpy.frompyfunc(_simps_integral, 4, 1)

def simps_interp_integral(a, b, f=None, x=None, y=None, n=100):
    if f is not None:
        x = numpy.linspace(a, b, n)
        y = map(f, x)
    fint = scipy.interpolate.interp1d(x, y)
    x = numpy.linspace(a, b, n*100)
    y = map(f, x)
    return scipy.integrate.simps(x, y)

def make_func_from_s(xv, yv):
    minx, maxx = min(xv), max(xv)
    f_int = interp1d(xv, yv)
    def func(_x):
        if _x < minx:
            print 'W: %.2f' %(_x-minx,)
            return f_int(minx)
        elif _x > maxx:
            print 'W: %.2f' %(_x-maxx,)
            return f_int(maxx)
        else:
            return f_int(_x)
        #if minx <= _x <= maxx:
        #     for i, tmpx in enumerate(xv):
        #         if _x <= tmpx:
        #             #return yv[i]
        #             # _X e' contenuta in i-1, i
        #             # retta passante per 2 punti
        #             x1, x2 = xv[i-1], tmpx
        #             y1, y2 = yv[i-1], yv[i]
        #             return (_x - x1)*(y2-y1)/(x2-x1) + y1
        #else:
        #    raise ValueError('mi mancano i valori per %f' %_x)
    #return func
    return numpy.frompyfunc(func, 1, 1)

def make_func_s(f, xa, xb, n=1000):
    xv = numpy.linspace(xa, xb, n)
    fu = numpy.frompyfunc(f, 1, 1)
    yv = fu(xv)
    return xv, yv

def remove_nan(xs, ys):
    nans_i = []
    assert len(xs) == len(ys)
    for i, _x, _y in zip(range(len(xs)+1), xs, ys):
        if numpy.isnan(_y):
            print 'nan',i, _x, _y
            nans_i.append(i)
    return numpy.delete(xs, nans_i), numpy.delete(ys, nans_i)

def getsymbols():
    allsym = range(-(int(M)-1), int(M))
    return [s for s in allsym if (s%2)==1]


P_eq = dict([(s, 1.0/M) for s in getsymbols()])

def rand_dist(N, step):
    _P = P_eq.copy()
    for i in range(N):
        _indsub = random.choice(_P.keys())
        _P[_indsub] -= step
        _indadd = random.choice(_P.keys())
        _P[_indadd] += step
    return _P
P_rand = rand_dist(100, 0.01)

P = P_eq

def g_REC(t):
    if 0<=t and t<=(L*T):
        return 1/(2*T)
    else:
        return 0

def g_RC(t):
    if 0<=t and t<=(L*T):
        return (1/(2*L*T))*(1 - scipy.cos(((2*pi*t)/(L*T))))
    else:
        return 0

g = g_REC
def _q_REC(t):
    if t<0:
        return 0
    elif 0<=t and t<=(L*T):
        #return cplx_integral(g, -scipy.integrate.Inf, t)
        #x = numpy.linspace(0, t, 9)
        #y = map(g, x)
        #print x, y
        #return scipy.integrate.romb(y, x)
        return t/(2*L*T)
        #return (1/(2*L*T))*(t+((L*T)/(2*pi))*scipy.sin((2*pi*t)/(L*T)))
        #return cplx_integral(g, -3000000000000, t)
    else:
        return 0.5
def _q_RC(t):
    if t<0:
        return 0
    elif 0<=t and t<=(L*T):
        #return cplx_integral(g, -scipy.integrate.Inf, t)
        #x = numpy.linspace(0, t, 9)
        #y = map(g, x)
        #print x, y
        #return scipy.integrate.romb(y, x)
        #return t/(2*L*T)
        return (1/(2*L*T))*(t-((L*T)/(2*pi))*scipy.sin((2*pi*t)/(L*T)))
        #return cplx_integral(g, -3000000000000, t)
    else:
        return 0.5
#q = numpy.frompyfunc(_q, 1, 1)
#q = _q
if options.g == 'rec':
    #q = _q_REC
    q = numpy.frompyfunc(_q_REC, 1, 1)
elif options.g == 'rc':
    #q = _q_RC
    q = numpy.frompyfunc(_q_RC, 1, 1)
else:
    raise SystemExit('Impulso di modulazione sconosciuto')

class FileFunc(object):
    def save_file(self, *args, **kwargs):
        return write_file(*args, **kwargs)
    def read_file(self, *args, **kwargs):
        return read_file(*args, **kwargs)
    # fname_template = '%s/%%s_M%d_L%d_h%.2f_%s' %(options.data_dir, M, L, h, options.g)
    # def save_file(self, xs, ys, name):
    #     assert len(xs) == len(ys)
    #     fname = self.fname_template %(name,)
    #     with open(fname, 'w') as fh:
    #         for x, y in zip(xs, ys):
    #             fh.write('%s\t%s\n' %(repr(x), repr(y)))

    # def read_file(self, name):
    #     fname = self.fname_template %name
    #     if os.path.exists(fname):
    #         with open(fname) as fh:
    #             lines = fh.readlines()
    #         ns = len(lines)
    #         x, y = numpy.ndarray(ns), numpy.ndarray(ns, dtype=complex)
    #         for i, l in enumerate(lines):
    #             xr, yr = l.split('\t')
    #             x[i] = eval(xr)
    #             y[i] = eval(yr)
    #         return x, y
    #     else:
    #         print >>sys.stderr, 'Manca il file %s' %(self.fname_template %name,)
    #         sys.exit(1)

fname_template = '%s/%%s_M%d_L%d_h%.2f_%s' %(options.data_dir, M, L, h, options.g)
def write_file(xs, ys, name):
    assert len(xs) == len(ys)
    fname = fname_template %(name,)
#    with open(fname, 'w') as fh:
#        for x, y in zip(xs, ys):
#            fh.write('%s\t%s\n' %(repr(x), repr(y)))
    scipy.save(fname+'_x', xs)
    scipy.save(fname+'_y', ys)

def read_file(name):
    fname = fname_template %name
    if os.path.exists(fname+'_x.npy') and os.path.exists(fname+'_y.npy'):
        xs = scipy.load(fname+'_x.npy')
        ys = scipy.load(fname+'_y.npy')
        return xs, ys
    elif os.path.exists(fname):
        with open(fname) as fh:
            lines = fh.readlines()
        ns = len(lines)
        x, y = numpy.ndarray(ns), numpy.ndarray(ns, dtype=complex)
        for i, l in enumerate(lines):
            xr, yr = l.split('\t')
            x[i] = eval(xr)
            y[i] = eval(yr)
        return x, y
    else:
        print >>sys.stderr, 'Manca il file %s' %(fname_template %name,)
        #sys.exit(1)
        return None, None

# grep ^def common.py | sed -e 's/def //g' -e 's/(.*//g'
__all__ = [
'plot_test',
'cplx_integral',
'simps_integral',
'simps_interp_integral',
'make_func_from_s',
'make_func_s',
'remove_nan',
'getsymbols',
'rand_dist',
'g_REC',
'g_RC',
'q',
'P',
#
'FileFunc',
'read_file',
'write_file',
#
'M',
'L',
'T',
'h',
'options',
'R_INT_N',
'S_INT_N'
]
