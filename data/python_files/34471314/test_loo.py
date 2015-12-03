import numpy as np;
import numpy.random as nr;
import numpy.linalg as linalg;
import networkx as nx;

import maths;
import mvn;
import normal_inverse_wishart;
import gaussian_network;
import gaussian_clique_tree;

def evaluate_distribution(d,test,name):
    lpdf = d.logpdf(test);
    s = np.sum(lpdf);
    print name,' log score = ',s;
    return s;

def test_mvn(n,train,test):
    mvn_ = mvn.learn_ml(train);
    return (mvn_,evaluate_distribution(mvn_,test,'ML-MVN'));

def test_inverse_wishart(n,train,test):
    niw = normal_inverse_wishart.prior_2(n,n-1)
    niw.incorporate_evidence(train);
    t = niw.get_posterior_predictive_distribution();
    return (t,evaluate_distribution(t,test,'BMA-NIW'));
    

def test_gaussian_network(n,train,test):
    s = nx.DiGraph()
    for i in range(n):
        for j in range(i):
            s.add_edge(j,i);
    gn = gaussian_network.learn_ml(train,s);
    return (gn,evaluate_distribution(gn,test,'ML-GN'));

def test_gct(n,train,test):
    clique_domains = [range(n)];
    separator_domains = [];
    h = gaussian_clique_tree.prior(n,clique_domains,separator_domains);
    h.incorporate_evidence(train);
    t = h.get_posterior_predictive_distribution();
    return (h,evaluate_distribution(t,test,'BMA-GCT'))

def make_multidimensional_normal(n_vars):   

    #mu = [2,5];
    #sigma = [[3,0.7];[0.7,2]];

    mu = nr.randn(n_vars);
    #print "mu =",mu,' ',mu.shape;

    s = nr.randn(n_vars,n_vars);
    sigma = maths.make_symmetric(np.dot(s.transpose(),s));
    ei = linalg.eig(sigma);
    #print ei
    while (not np.all(ei > 0)):
        s = nr.randn(n_vars)
        sigma = maths.make_symmetric(np.dot(s.transpose(),s));
        ei = linalg.eig(sigma)
    #print "real mu=",mu;
    #print "real sigma=",sigma;
    sigma = 10.*linalg.inv(sigma);
    return mvn.mvn(mu,sigma);

if __name__ == '__main__':
    NVARS = 3
    m = make_multidimensional_normal(NVARS);
    NTRAIN = 50
    train = m.sample(NTRAIN);
    NLOO = 2
    #print train
    test = m.sample(500000);
    gn,s_gn = test_gaussian_network(NVARS,train,test);
    loo_train = train[0:NTRAIN-NLOO,:]
    loo_out = train[NTRAIN - NLOO:NTRAIN,:]
    gn_loo_1,s_gn_loo_1 = test_gaussian_network(NVARS,loo_train,test);
    gn_loo_2 = gn.get_loo_model(loo_out)
    s_gn_loo_2 = evaluate_distribution(gn_loo_2,test,'LOO_2')
    
    (gct,s_gct) = test_gct(NVARS,train,test)
    gct_loo_1,s_gct_loo_1 = test_gct(NVARS,loo_train,test)
    gct_loo_2 = gct.get_loo_model(loo_out)
    s_gn_loo_2 = evaluate_distribution(gct_loo_2,test,'LOO_2')
    #print 'Difference (should be almost 0) = ',s4-s2;
    #
    #print 'Difference (should be almost 0) = ',s5-s3;
    #test_hyper(NVARS,train,test);
   

