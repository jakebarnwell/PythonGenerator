import os
import os.path
import math
from decimal import Decimal

import numpy
import scipy
import scipy.stats
import uncertainties
from uncertainties import ufloat
from uncertainties.unumpy import nominal_values, std_devs

def heaviside(x):
    if x > 0:
        return x
    else:
        return 0

# default is round to even!!!
#   1.25  -> 1.2
#   1.251 -> 1.3
#   1.15  -> 1.2
#   1.151 -> 1.2
def round_figures(value, figures):
    d = Decimal(value)
    if d == 0:
        return '0'
    d = round(d, figures - int(math.floor(math.log10(abs(d)))) - 1)
    return "{:f}".format(d)

def round_places(value, places):
    d = Decimal(value)
    if d == 0:
        return '0'
    d = round(d, places)
    return "{:f}".format(d)

def round_to(value, error, figures=1):
    de = Decimal(error)
    f = figures - int(math.floor(math.log10(abs(de)))) - 1
    return round_places(value, f)

def lfloat(repres, tag=None):
    """
    lab-float:
           2 iterables
               => array of ufloats
           number
               => ufloat without error
           string
               => regular ufloat
    """
    if isinstance(repres, (tuple, list, numpy.ndarray)):
        result = []
        vals, errs = repres
        for v, e in zip(vals, errs):
            result.append(ufloat("{}+/-{}".format(v, e)))
        return numpy.array(result)

    if isinstance(repres, (int, float)):
        repres = "{}+/-0".format(repres)

    return ufloat(repres)

# More convenient extraction of value and error from ufloats
vals = nominal_values
stds = std_devs

def linregress(x, y):

    sqrt = math.sqrt

    x = vals(x)
    y = vals(y)

    N = len(y)
    Delta = N * sum(x**2) - (sum(x))**2

    A = (N * sum(x * y) - sum(x) * sum(y)) / Delta
    B = (sum(x**2) * sum(y) - sum(x) * sum(x * y)) / Delta

    sigma_y = sqrt(sum((y - A * x - B)**2) / (N - 2))

    A_error = sigma_y * math.sqrt(N / Delta)
    B_error = sigma_y * math.sqrt(sum(x**2) / Delta)

    return ufloat((A, A_error)), ufloat((B, B_error))

def curve_fit(f, x, y, **kwargs):
    popt, pcov = scipy.optimize.curve_fit(f, vals(x), vals(y), **kwargs)
    r = []
    for i in range(len(popt)):
        r.append(ufloat((popt[i], math.sqrt(pcov[i][i]))))
    return r

def get_new_file_path(name):
    if os.path.dirname(name) != "":
        os.makedirs("./build/" + os.path.dirname(name), exist_ok=True)
    return "./build/" + name

def get_file_path(name):
    if os.path.exists("./build/" + name):
        return "./build/" + name
    elif os.path.exists("./" + name):
        return "./" + name
    elif os.path.exists("../" + name):
        return "../" + name
    elif os.path.exists("../powertools/" + name):
        return "../powertools/" + name
    else:
        return "./build/" + name

def mean(values, axis=0):
    return uncertainties.unumpy.uarray((numpy.mean(vals(values), axis=axis), scipy.stats.sem(vals(values), axis=axis)))

# doesn't seem to work, see http://en.wikipedia.org/wiki/Weighted_mean#Dealing_with_variance
def umean(values, axis=0):
    if numpy.shape(values)[axis] == 1:
        return values
    w = numpy.sum(1 / stds(values)**2, axis=axis)
    m = numpy.sum(vals(values) / stds(values)**2, axis=axis) / w
    w2 = numpy.sum((vals(values) - m)**2 / stds(values)**2, axis=axis)
    print(numpy.sqrt(w), numpy.sqrt(w / (numpy.shape(values)[axis] - 1) * w2))
    return uncertainties.unumpy.uarray((m, numpy.sqrt(w / (numpy.shape(values)[axis] - 1) * w2)))

def constant(name):
    c = scipy.constants.physical_constants[name]
    return ufloat((c[0], c[2]))
