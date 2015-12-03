import math
import random
import copy

from hnn3 import HNN3
from inputset import InputSet
from ees.individual import SectionReal
from ees.individual import SectionInteger
from ees.individual import Individual

from scipy.stats.distributions import norm
from scipy.stats.distributions import randint
from scipy.stats.distributions import uniform

__author__="Marcos Gabarda"
__date__ ="$29-dic-2010 12:43:12$"

class SectionQ(SectionReal):
    """
    Section Q, real value for the q-mean computed in hidden neurons.
    """
    def mutate(self):
        #Mutate sigma
        self.sigma[0] = self.sigma[0] * math.exp(self.tau_prim * norm.rvs() + \
        self.tau * norm.rvs());
        #Mutate q
        new_q = self.genes[0] + norm.rvs(scale=self.sigma[0])
        if not self.lsup and not self.linf:
            self.genes[0] = new_q
        elif not self.lsup:
            if new_q < self.linf:
                self.genes[0] = self.linf
            else:
                self.genes[0] = new_q
        elif not self.linf:
            if new_q > self.lsup:
                self.genes[0] = self.lsup
            else:
                self.genes[0] = new_q
        else:
            if new_q <= self.lsup and new_q >= self.linf:
                self.genes[0] = new_q
            elif new_q > self.lsup:
                self.genes[0] = self.lsup
            elif new_q < self.linf:
                self.genes[0] = self.linf

class SectionLambda(SectionReal):
    """
    Section Lambda, parameter for ridge regression.
    """
    def mutate(self):
        #Mutate sigma
        self.sigma[0] = self.sigma[0] * math.exp(self.tau_prim * norm.rvs() + \
        self.tau * norm.rvs());
        #Mutate l
        new_l = self.genes[0] + norm.rvs(scale=self.sigma[0])
        if not self.lsup and not self.linf:
            self.genes[0] = new_l
        elif not self.lsup:
            if new_l < self.linf:
                self.genes[0] = self.linf
            else:
                self.genes[0] = new_l
        elif not self.linf:
            if new_l > self.lsup:
                self.genes[0] = self.lsup
            else:
                self.genes[0] = new_l
        else:
            if new_l <= self.lsup and new_q >= self.linf:
                self.genes[0] = new_l
            elif new_l > self.lsup:
                self.genes[0] = self.lsup
            elif new_l < self.linf:
                self.genes[0] = self.linf

class SectionH(SectionInteger):

    def random_initialization(self):
        self.genes = []
        for i in range(self.size):
            self.genes.append(randint.rvs(1, 100))
        self.sigma = [uniform.rvs()]

    def mutate(self):
        #Mutate sigma
        self.sigma[0] = self.sigma[0] * math.exp(self.tau_prim * norm.rvs() + \
        self.tau * norm.rvs());
        #Mutate h
        alpha = norm.rvs(scale=self.sigma[0])
        inc = 0
        if alpha < -self.sigma[0]:
            inc = -1
        elif alpha > self.sigma[0]:
            inc = 1
        new_h = self.genes[0] + inc
        if new_h >= self.linf and new_h <= self.lsup:
            self.genes[0] = new_h


class SectionCenter(SectionInteger):

    def __random_gen(self):
        all_indexes = range(self.lsup)
        pos = list(set(all_indexes)-set(self.genes))
        return random.sample(pos, 1)[0]

    def random_initialization(self):
        self.genes = random.sample(range(self.lsup), self.size)
        self.sigma = []
        for i in range(self.size):
            self.sigma.append(uniform.rvs())

    def resize(self, size):
        curr_size = len(self.genes)
        if size < curr_size:
            self.genes = self.genes[:size]
        elif size > curr_size:
            for i in range(size-curr_size):
                self.genes.append(self.__random_gen())

    def mutate(self):
        # Mutate as a binary.
        sq = self.individual.genoma[0]
        q = sq.genes[0]
        data_set = self.individual.data_set
        pm = 1.0 / float(len(self.genes))
        mut = 0.0
        for i in range(len(self.genes)):
            x = uniform.rvs()
            if x < pm:
                mut += 1.0
                self.genes[i] = data_set.get_nearest(self.get_gen(i), q, \
                exclusion=self.genes)
        self.mutation_factor = mut/float(len(self.genes))


class SectionGamma(SectionReal):
    def mutate(self):
        #Mutate sigma
        random_number = norm.rvs()
        for i in range(len(self.sigma)):
            self.sigma[i] = self.sigma[i] * math.exp(self.tau_prim * \
            random_number + self.tau * norm.rvs());
        #Mutate gammas
        for i in range(len(self.genes)):
            new_gamma = self.genes[i] + norm.rvs(scale=self.sigma[i])
            if not self.lsup and not self.linf:
                self.genes[i] = new_gamma
            elif not self.lsup:
                if new_gamma < self.linf:
                    self.genes[i] = self.linf
                else:
                    self.genes[i] = new_gamma
            elif not self.linf:
                if new_gamma > self.lsup:
                    self.genes[i] = self.lsup
                else:
                    self.genes[i] = new_gamma
            else:
                if new_gamma <= self.lsup and new_q >= self.linf:
                    self.genes[i] = new_gamma
                elif new_l > self.lsup:
                    self.genes[i] = self.lsup
                elif new_l < self.linf:
                    self.genes[i] = self.linf

class IndividualHNN3(Individual):
    """
    @type data_set: InputSet
    """
    def __init__(self, data_set, id=None):
        sq = SectionQ("q", self, 1)
        sq.random_initialization()
        sl = SectionLambda("lambda", self, 1, 0.0)
        sl.random_initialization()
        sh = SectionH("h", self, 1, 1, data_set.size())
        sh.random_initialization()
        sc = SectionCenter("centers", self, sh.get_gen(0), 1, data_set.size())
        sc.random_initialization()
        sg = SectionGamma("gammas", self, sh.get_gen(0), 0.0, 3.0)
        sg.random_initialization()
        self.genoma = [sq, sl, sh, sc, sg]
        self.id = id
        self.score = None
        self.data_set = data_set
        self.parent = None

    def mutate(self):
        ind = IndividualHNN3(self.data_set)
        ind.genoma[0].genes = copy.deepcopy(self.genoma[0].genes)
        ind.genoma[0].sigma = copy.deepcopy(self.genoma[0].sigma)
        ind.genoma[1].genes = copy.deepcopy(self.genoma[1].genes)
        ind.genoma[1].sigma = copy.deepcopy(self.genoma[1].sigma)
        ind.genoma[2].genes = copy.deepcopy(self.genoma[2].genes)
        ind.genoma[2].sigma = copy.deepcopy(self.genoma[2].sigma)
        ind.genoma[3].genes = copy.deepcopy(self.genoma[3].genes)
        ind.genoma[3].sigma = copy.deepcopy(self.genoma[3].sigma)
        ind.genoma[4].genes = copy.deepcopy(self.genoma[4].genes)
        ind.genoma[4].sigma = copy.deepcopy(self.genoma[4].sigma)
        ind.genoma[0].mutate()
        ind.genoma[1].mutate()
        ind.genoma[2].mutate()
        new_h = ind.genoma[2].get_gen(0)
        ind.genoma[3].resize(new_h)
        ind.genoma[3].mutate()
        ind.genoma[4].resize(new_h)
        ind.genoma[4].mutate()
        if self.id:
            ind.id = self.id
        ind.score = None
        ind.parent = self
        return ind

    def __fitness_function_classification(self):
        q = self.genoma[0].genes[0]
        l = self.genoma[1].genes[0]
        centers = self.genoma[3].genes
        gammas = self.genoma[4].genes
        hnn3 = HNN3(self.data_set, centers, gammas, q, l)
        return hnn3.get_training_accuracy()

    def __fitness_function_regression(self):
        q = self.genoma[0].genes[0]
        l = self.genoma[1].genes[0]
        centers = self.genoma[3].genes
        gammas = self.genoma[4].genes
        hnn3 = HNN3(self.data_set, centers, gammas, q, l)
        return hnn3.get_training_nrms()

    def get_hnn3(self):
        q = self.genoma[0].genes[0]
        l = self.genoma[1].genes[0]
        centers = self.genoma[3].genes
        gammas = self.genoma[4].genes
        hnn3 = HNN3(self.data_set, centers, gammas, q, l)
        return hnn3
    
    def update_score(self):
        if self.data_set.mode == "cls":
            self.score = self.__fitness_function_classification()
        else:
            self.score = self.__fitness_function_regression()

    def __str__(self):
        s = "<< ID: " + str(self.id) + ", SCORE: " + str(self.score)
        for i,v in enumerate(self.genoma):
            s = s + " { " + str(v) + " } "
        s += ">>"
        return s

if __name__ == "__main__":
    data_set = InputSet()
    data_set.load("hepatitis.data")
    ind = IndividualHNN3(data_set)
    ind.update_score()
    print ind
    for i in range(20):
        o = ind.mutate()
        print o
        o.update_score()
