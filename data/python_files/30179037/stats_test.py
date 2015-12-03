import unittest
from nose.tools import eq_ as eq, ok_ as ok, raises, timed
import os, sys
import json

from genetix import Genetix
from genetix.storage import JSONFiles
import genetix.stats

# create with json storage
g = Genetix(JSONFiles('./json'))

class TestStats(unittest.TestCase):
    def setUp(self):
        # reference gene expected values
        with open('./json/reference_gene.json') as f:
            self.reference = json.load(f)
        # starter gene with 3 variants:
        self.gene = {
            'name': 'testgene',
            'count': 283,
            'goals': 88,
            'distinct': 215,
            'description': 'an example gene with 3 variants',
            'variants': [ {
                'name': 'variant1',
                'content': 'variant1 content',
                'distinct': 67,
                'count': 75,
                'goals': 32,
                'avg': 0.0,
                'countsq': 0.0,
                'weight': 0.0,
                'within': 0.0,
                'between': 0.0,
                'wavg': 10.0,
                'fitness': 0.0
            },
            {
                'name': 'variant2',
                'content': 'variant2 content',
                'distinct': 42,
                'count': 84,
                'goals': 22,
                'avg': 0.0,
                'countsq': 0.0,
                'weight': 0.0,
                'within': 0.0,
                'between': 0.0,
                'wavg': 10.0,
                'fitness': 0.0
            },
            {
                'name': 'variant3',
                'content': 'variant2 content',
                'distinct': 106,
                'count': 124,
                'goals': 34,
                'avg': 0.0,
                'countsq': 0.0,
                'weight': 0.0,
                'within': 0.0,
                'between': 0.0,
                'wavg': 10.0,
                'fitness': 0.0
            } ]
        }

    def test_weight(self):
        r = self.reference
        g.calculate(self.gene)
        expected = [ v['within'] for v in r['variants'] ]
        observed = [ v['within'] for v in self.gene['variants'] ]
        eq(observed, expected)

    def test_within(self):
        r = self.reference
        g.calculate(self.gene)
        expected = [ v['within'] for v in r['variants'] ]
        observed = [ v['within'] for v in self.gene['variants'] ]
        eq(observed, expected)

    def test_between(self):
        r = self.reference
        g.calculate(self.gene)
        expected = [ v['between'] for v in r['variants'] ]
        observed = [ v['between'] for v in self.gene['variants'] ]
        eq(observed, expected)

    def test_distinct(self):
        r = self.reference
        g.calculate(self.gene)
        g.stats.distinct(self.gene, 'variant1')
        eq(self.gene['variants'][0]['distinct'], r['variants'][0]['distinct'] + 1)
        eq(self.gene['distinct'], r['distinct'] + 1)

    def test_count(self):
        r = self.reference
        g.calculate(self.gene)
        g.stats.count(self.gene, 'variant1')
        eq(self.gene['variants'][0]['count'], r['variants'][0]['count'] + 1)
        eq(self.gene['count'], r['count'] + 1)

    def test_probabilities(self):
        expected = [0.011329647421372246, 0.012145382035711048, 0.015770869210550167]
        g.calculate(self.gene)
        observed = g.stats.probabilities(self.gene)
        eq(observed, expected)

    def test_wavg(self):
        r = self.reference
        g.calculate(self.gene)
        expected = [ v['wavg'] for v in r['variants'] ]
        observed = [ v['wavg'] for v in self.gene['variants'] ]
        eq(observed, expected)

    def test_avg(self):
        r = self.reference
        g.calculate(self.gene)
        expected = [ v['avg'] for v in r['variants'] ]
        observed = [ v['avg'] for v in self.gene['variants'] ]
        eq(observed, expected)

    def test_countsq(self):
        r = self.reference
        g.calculate(self.gene)
        expected = [ v['countsq'] for v in r['variants'] ]
        observed = [ v['countsq'] for v in self.gene['variants'] ]
        eq(observed, expected)

    def test_fitness_test(self):
        r = self.reference
        g.calculate(self.gene)
        #import ipdb; ipdb.set_trace()
        expected = [ v['fitness'] for v in r['variants'] ]
        #expected = [0.02453238676059355, 0.0, 0.0]
        observed = [ v['fitness'] for v in self.gene['variants'] ]
        eq(observed, expected)

    def test_lj_spin(self):
        expected = 0.045454545454545414
        observed = g.stats.lj_spin(7, 12, 15, 100)
        eq(observed, expected)

    def test_fspin(self):
        f = 1.380281690140845
        df1 = 71
        df2 = 28
        expected = 0.9988136336689538
        observed = g.stats.fspin(f, df1, df2)
        eq(observed, expected)

    def test_crate(self):
        control = (180, 35)
        expected = 0.19444444444444445
        observed = g.stats.crate(control)
        eq(observed, expected)

    def test_zscore(self):
        control = (182, 35)
        variant = (180, 45)
        expected = 1.3252611961151075
        observed = g.stats.zscore(control, variant)
        eq(observed, expected)

    def test_cumnormdist(self):
        zscore = 1.3252611961151075
        expected = 0.9091014037909785
        eq(g.stats.cumnormdist(zscore), expected)

    def test_sample_sizes(self):
        cr = 0.19444444444444445
        expected = [254, 707, 6365]
        eq(g.stats.sample_sizes(cr), expected)
