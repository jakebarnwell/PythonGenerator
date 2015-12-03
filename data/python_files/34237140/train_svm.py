import math
import sys
import os

from extract_sift import *
from svm import *
from svmutil import *
from bow import *
from conf import *

def load_bow(dir):
    vectors = []
    
    files = os.listdir(dir)
    for f in files:
        filename = "%s/%s" % (dir, f)
	# print filename
        if os.path.isfile(filename) and os.path.splitext(filename)[1].lower() == '.bow':
	    #print filename
            f_h = open(filename, 'r')
            vectors.append(map(int, f_h.readline().split()))

    return vectors


# number of test set features
test = 50

def train_images():
    bow = load_bow(class1)
    bow += load_bow(class2)
    bow += load_bow(class3)
    bow += load_bow(class4)
    bow += load_bow(class5)
    bow += load_bow(class6)
    bow += load_bow(class7)
    bow += load_bow(class8)
    bow += load_bow(class9)
    bow += load_bow(class10)

    labels = [1]*90
    labels += [2]*90
    labels += [3]*90
    labels += [4]*90
    labels += [5]*90
    labels += [6]*90
    labels += [7]*90
    labels += [8]*90
    labels += [9]*90
    labels += [10]*90

    print labels
    print len(labels)
    print len(bow)

    print 'len of databow'
    print bow
    print len(bow[0])

###############################################################################################################
#options:
#-s svm_type : set type of SVM (default 0)
#	0 -- C-SVC
#	1 -- nu-SVC
#	2 -- one-class SVM
#	3 -- epsilon-SVR
#	4 -- nu-SVR
#-t kernel_type : set type of kernel function (default 2)
#	0 -- linear: u'*v
#	1 -- polynomial: (gamma*u'*v + coef0)^degree
#	2 -- radial basis function: exp(-gamma*|u-v|^2)
#	3 -- sigmoid: tanh(gamma*u'*v + coef0)
#-d degree : set degree in kernel function (default 3)
#-g gamma : set gamma in kernel function (default 1/num_features)
#-r coef0 : set coef0 in kernel function (default 0)
#-c cost : set the parameter C of C-SVC, epsilon-SVR, and nu-SVR (default 1)
#-n nu : set the parameter nu of nu-SVC, one-class SVM, and nu-SVR (default 0.5)
#-p epsilon : set the epsilon in loss function of epsilon-SVR (default 0.1)
#-m cachesize : set cache memory size in MB (default 100)
#-e epsilon : set tolerance of termination criterion (default 0.001)
#-h shrinking: whether to use the shrinking heuristics, 0 or 1 (default 1)
#-b probability_estimates: whether to train a SVC or SVR model for probability estimates, 0 or 1 (default 0)
#-wi weight: set the parameter C of class i to weight*C, for C-SVC (default 1)
###############################################################################################################

    prob = svm_problem(labels, bow)
    #param = svm_parameter(kernel_type = LINEAR, c = 10)
    param = svm_parameter()

    if kernel is 'LINEAR': param.kernel_type=LINEAR
    if kernel is 'RBF': param.kernel_type=RBF
    if kernel is 'POLY': param.kernel_type=POLY
    if kernel is 'SIGMOID': param.kernel_type=SIGMOID
    
    #TODO:LINEAR gives 85.38% on training and 57.142% on test
    #TODO:RBF gives 100% on training and 50 on test
    #TODO:POLY gives 100% on training and 52.381 on test
    #TODO:SIGMOID gives 70.76% on training and 50 on test

    ## training  the model
    model = svm_train(prob, param)

    print '$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$'

    p_labels, p_acc, p_vals = svm_predict(labels, bow, model)

    print '$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$'

    print 'model trained... '
    print 'test clusters loaded... '

    bow = load_bow(test1)
    bow += load_bow(test2)
    bow += load_bow(test3)
    bow += load_bow(test4)
    bow += load_bow(test5)
    bow += load_bow(test6)
    bow += load_bow(test7)
    bow += load_bow(test8)
    bow += load_bow(test9)
    bow += load_bow(test10)

    labels = [1]*10
    labels += [2]*10
    labels += [3]*10
    labels += [4]*10
    labels += [5]*10
    labels += [6]*10
    labels += [7]*10
    labels += [8]*10
    labels += [9]*10
    labels += [10]*10


    #generate test features with big dictionary
    print len(labels)

    p_labels, p_acc, p_vals = svm_predict(labels, bow, model)

    print p_labels
    print p_acc

#train_images()
