import code
import glob
import heapq
import operator
import os
import pickle
import random
import score
import sys

from score import Score

eps = 1e-5
inf = float('inf')
rand = random.SystemRandom()

def vecdot(l1, l2):
    ''' Return the dot product of l1 and l2
    '''
    return sum(map(operator.mul, l1, l2))

def vecadd(l1, l2):
    ''' Return the vector sum of l1 and l2
    '''
    return map(operator.add, l1, l2)

def vecsub(l1, l2):
    ''' Return the vector difference of l1 and l2
    '''
    return map(operator.sub, l1, l2)

def vecscale(l, a):
    ''' Scale vector l by scalar a and return the result
    '''
    return [a * x for x in l]

def vecnormalize(l, total=1):
    ''' Normalize vector l so that the elements sum to total
    '''
    factor = total / sum(l)
    l[:] = map(lambda x: factor * x, l)

def vecrand(size):
    ''' Generate a size-length random float [0,1) vector
    '''
    return [rand.random() for x in xrange(size)]

def dedup(l):
    ''' Remove duplicates in a list of floats
        Return the resulting list
    '''
    prev = -inf
    l2 = []
    for x in l:
        if abs(x - prev) > eps:
            l2.append(x)
        prev = x
    return l2


# translation of a sentence
class translation:
    def __init__(self):
        self.engine = None 
        # self.text = None  # TODO: re-read input file to acquire this field
        self.features = None
        self.score = 0  # score (meteor, bleu etc.)

        # metric used in training
        # usage scenario 1 - best translation of a sentence gets metric 1
        #                  - others get metric 0
        # usage scenario 2 - metric = score
        self.metric = 0 

    def grade(self, wt):
        return vecdot(wt, self.features)

# a Sentence
class Sentence:
    def __init__(self):
        # weight used in combining metric of sentences
        # usage scenario 1 - uniform weight for all sentences
        # usage scenario 2 - weight sentences by length
        self.w = 1      
        self.tlns = [] # list of translations for this sentence

    def metric(self, wt):
        ''' Return the weighted metric of this sentence
        '''
        bestgrade = -inf
        ret = 0
        for tra in self.tlns:
            grd = tra.grade(wt)
            if grd > bestgrade:
                bestgrade = grd
                ret = tra.metric
        return ret * self.w

    def metric2(self, src, gradient, gamma):
        wt = vecadd(src, vecscale(gradient, gamma))
        return self.metric(wt)

    def consensus(self, wt):
        ''' Return the engine picked by the consensus algorithm
        '''
        bestgrade = -inf
        ret = None
        for tra in self.tlns:
            grd = tra.grade(wt)
            if grd > bestgrade:
                bestgrade = grd
                ret = tra.engine
        return ret

    def oracle(self):
        ''' Return the engine picked by the oracle
        '''
        bestmetric = -inf
        ret = None
        for tra in self.tlns:
            if tra.metric > bestmetric:
                bestmetric = tra.metric
                ret = tra.engine
        return ret

    def engines(self):
        ''' Return the list of engines
        '''
        return [t.engine for t in self.tlns]
    

def total_metric(src, gradient, gamma, sentences):
    ''' Return the sum of metric of all sentences
    '''
    metric = 0
    for s in sentences:
        metric += s.metric2(src, gradient, gamma)
    return metric
    

def linear_optimum(src, gradient, nengine, nfeature, sentences):
    ''' Find a point along a line that maximizes the weighted total metric
        of all sentences. The line is defined as src + gamma * gradient

        @return
        Return (best_gamma, best_metric)
        @param
        nengine - number of translation engines
        @param
        nfeature - number of features
        @param
        sentences - list of sentences
    '''
    gmlists = []    # list of lists of (gamma, delta_metric) pairs
    mingamma = inf  # min gamma
    for s in sentences:

        # find boundaries
        # (src + gamma*gradient).features_eng1 = (src + gamma*gradient).features_eng2
        # => gamma = -src.df/ gradient.df
        # where df = features_eng1 - features_eng2
        gammas = []
        for i in xrange(0, nengine-1):
            for j in xrange(i+1, nengine):
                f1 = s.tlns[i].features
                f2 = s.tlns[j].features
                df = vecsub(f1, f2)
                divisor = vecdot(gradient, df)
                if abs(divisor) < eps:
                    continue
                gamma = -vecdot(src, df) / divisor
                gammas.append(gamma)
                
        if not gammas:
            continue
        
        gammas.sort()
        gammas = dedup(gammas)
        if gammas[0] < mingamma:
            mingamma = gammas[0]
        
        N = len(gammas)
        gmlist = []     # list of (gamma, delta_metric) pairs
        gammas.append(gammas[-1]+100)
        prev = s.metric2(src, gradient, gammas[0]-50)
        for i in xrange(0, N):
            metric = s.metric2(src, gradient, 0.5 * (gammas[i] + gammas[i+1]))
            gmlist.append((gammas[i], metric - prev))
            prev = metric
        gmlists.append(gmlist)
        
    it = heapq.merge(*gmlists) # merge all indiviual lists
    prevgamma = mingamma - 100
    metric = total_metric(src, gradient, prevgamma+50, sentences)
    bestmetric = -inf
    bestgamma = 0
    while True:
        try:
            node = it.next()
        except StopIteration:
            if metric > bestmetric:
                bestmetric = metric
                bestgamma = prevgamma + 50
            break
        (gamma, dm) = node
        
        if abs(gamma - prevgamma) > eps and metric > bestmetric:
            bestmetric = metric
            bestgamma = (prevgamma + gamma) * 0.5
        metric += dm
        prevgamma = gamma

    return bestgamma
    

def train_one_src(nengine, nfeature, sentences):
    threshold = 0.01
    maxstalecount = 5
    
    src = vecrand(nfeature)
    vecnormalize(src, 10000)     # normalize src point to 1000
    bestmetric = -1
    stalecount = 0
    
    while stalecount < maxstalecount:
        gradient = vecrand(nfeature)
        vecnormalize(gradient, 1)   # normalize gradient to 1
        gamma = linear_optimum(src, gradient, nengine, nfeature, sentences)
        metric = total_metric(src, gradient, gamma, sentences)

        if metric > bestmetric:
            stalecount = 0
            src = vecadd(src, vecscale(gradient, gamma))
            vecnormalize(src, 10000)
            bestmetric = metric
        else:
            stalecount += 1

    return (src, metric)


def train_weight(nengine, nfeature, sentences):
    ''' Return a list of weights, one for each feature
        @param
        nengine - number of translation engines
        @param
        nfeature - number of features
        @param
        sentences - list of sentences
    '''
    threshold = 0.01
    maxstalecount = 10
    stalecount = 0
    bestmetric = -1
    bestwt = None
    
    while stalecount < maxstalecount:
        (wt, metric) = train_one_src(nengine, nfeature, sentences)

        if metric > bestmetric:
            stalecount = 0
            bestwt = wt
            bestmetric = metric
        else:
            stalecount += 1

    return (bestwt, bestmetric)

def apply_consensus(wt, sentences):
    return [s.consensus(wt) for s in sentences]

def apply_oracle(sentences):
    return [s.oracle() for s in sentences]

if __name__ == "__main__":
    for data_file in glob.glob(os.path.join(score.OUTPUT_DIR, "*.pkl")):
        try:
            with open(data_file) as fd:
                scores = pickle.load(fd)
            print "Opened " + data_file
        except IOError, e:
            print "Could not open pkl file", e
            continue

        sentences = []
        n_sentences = len(scores.B[0][0])
        for k in xrange(n_sentences):
            s = Sentence()
            s.w = 1
            
            bestscore = -inf
            bestengine = None
            for engine in scores.ref_scores:
                if scores.ref_scores[engine][k] > bestscore:
                    bestengine = engine
                    bestscore = scores.ref_scores[engine][k]
            
            for i, B_i in enumerate(scores.B):
                tln = translation()
                tln.engine = scores.engine_i_to_name[i]
                tln.features = [B_ij[k] for B_ij in B_i]
                tln.score = scores.ref_scores[tln.engine][k]
                if tln.engine == bestengine:
                    tln.metric = 1
                else:
                    tln.metric = 0
                s.tlns.append(tln)
            sentences.append(s)
        (wt, metric) = train_weight(len(scores.ref_scores), len(scores.B[0]), sentences)
        print 'best weights: ', wt
        print '%d sentences, best metric = %d' % (len(sentences), metric)
        print 'individual engines: ',
        for engine in scores.ref_scores:
            print '%d ' % sum(scores.ref_scores[engine]),
        print '\n'
        

