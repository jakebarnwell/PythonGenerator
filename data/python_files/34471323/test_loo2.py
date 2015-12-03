import numpy as np;
import numpy.random as nr;
import numpy.linalg as linalg;
import networkx as nx;
from sklearn.cross_validation import LeaveOneOut
import math

import maths;
import mvn;
import normal_inverse_wishart;

import gaussian_network;
import gaussian_clique_tree;
import dataset
import bma_gct_inducer
import ml_cgn_inducer

def compare_models_bma(model,xtrain,ytrain,xtest,ytest,inducer):
    #print "Getting loo model"
    loo_model = model.get_loo_model(ytest,xtest)
    #print loo_model
    #print "Getting direct model"
    direct_model = inducer.learn(d.str,xtrain,ytrain)
    #print direct_model
    loo_pred = loo_model.predict(xtest)
    #print loo_pred
    if np.isnan(loo_pred).any():
        print 'loo is wrong'
        exit()
    
    direct_pred = direct_model.predict(xtest)
    #print direct_pred
    if np.isnan(direct_pred).any():
        print 'direct is wrong'
    return np.abs(loo_pred-direct_pred)

if __name__ == '__main__':
    d = dataset.load('../data/vehicle.mat')
    x = d.x
    y = d.y
    s = nx.complete_graph(d.str.n_vars)
    cv = LeaveOneOut(d.str.n_instances)
    print cv
    options = {}
 #   cgn = ml_cgn_inducer.wcGJAN_bn_learner(d.str, x, y,options)
 #   ml_model = ml_cgn_inducer.learn_parameters(d.str,x,y,cgn,options)
    bma_ind = bma_gct_inducer.bma_gct_inducer(options)
    
    #cliques,separators = bma_gct_inducer.wcGJAN_ct_learner(d.str, x, y,options)
    print "Learning main model"
    bma_model = bma_ind.learn(d.str,x,y)
    print "Main model induced"
    print bma_model
   # logmeasure_ml = np.zeros((d.str.n_instances,d.str.n_classes))
    logmeasure_bma = np.zeros((d.str.n_instances,d.str.n_classes))
    
    for train, test in cv:
        print test
        xtrain = x[train,:]
        ytrain = y[train,:]
        xtest = x[test,:]
        ytest = y[test,:]
         #logmeasure_ml[test,:] = compare_models_ml(cgn,ml_model,xtrain,ytrain,xtest,ytest)
        logmeasure_bma[test,:] = compare_models_bma(bma_model,xtrain,ytrain,xtest,ytest,bma_ind)
        #exit()
    meanerror = np.mean(logmeasure_bma)
    print 'Mean BMA absolute error:', meanerror
        
        
