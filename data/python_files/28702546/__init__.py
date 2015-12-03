import Orange
from orngWrap import PreprocessedLearner
from Orange.OrangeWidgets.OWWidget import OWWidget
from Orange.OrangeWidgets import OWGUI
from PyQt4.QtGui import QApplication, QIntValidator, QLabel, QWidget, QFormLayout, QAbstractButton, QDoubleValidator
from PyQt4.QtCore import QObject
from PyQt4 import QtCore
from PyQt4 import uic
import os
import sys
import inspect
import types

# optimization imports
from Goldenberry.optimization.base.GbBaseCostFunction import *
from Goldenberry.optimization.base.GbBaseOptimizer import *
from Goldenberry.optimization.cost_functions.functions import *
from Goldenberry.optimization.cost_functions import functions
from Goldenberry.optimization.edas.Cga import Cga
from Goldenberry.optimization.edas.Bmda import Bmda

# classification imports
from Goldenberry.classification.Perceptron import PerceptronLearner, PerceptronClassifier