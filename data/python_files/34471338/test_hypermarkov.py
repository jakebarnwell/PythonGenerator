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
    parents = [None]*n;
    s = nx.DiGraph()
    for i in range(n):
        for j in range(i):
            s.add_edge(j,i);
    gn = gaussian_network.learn_ml(train,s);
    return evaluate_distribution(gn,test,'ML-GN');

def test_gct(n,train,test):
    clique_domains = [range(n)];
    separator_domains = [];
    h = gaussian_clique_tree.prior(n,clique_domains,separator_domains);
    h.incorporate_evidence(train);
    t = h.get_posterior_predictive_distribution();
    return evaluate_distribution(t,test,'BMA-GCT');

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
    train = m.sample(50);
    #print train
    test = m.sample(5000000);
    s = evaluate_distribution(m,test,'Exact');
    (ml,s2) = test_mvn(NVARS,train,test);
    print 'Difference (should be larger than 0) = ',s-s2;
    (t,s3) = test_inverse_wishart(NVARS,train,test);
    print 'Difference BMA - ML (usually larger than 0) = ',s3-s2;
    if (s3 < s2):
        print m.mu
        print m.Sigma
        print ml.mu
        print ml.Sigma
        print t.mu
        print t.Sigma
        print train
    s4 = test_gaussian_network(NVARS,train,test);
    print 'Difference (should be almost 0) = ',s4-s2;
    s5 = test_gct(NVARS,train,test);
    print 'Difference (should be almost 0) = ',s5-s3;
    #test_hyper(NVARS,train,test);
   

