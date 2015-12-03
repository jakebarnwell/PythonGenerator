import unittest
from nose.tools import eq_ as eq, ok_ as ok, raises, timed
import os, sys
import json
from pprint import pprint

from genetix import Genetix
from genetix.storage import JSONFiles
import genetix.stats

# create with json storage
g = Genetix(JSONFiles('./json'))

class TestGenetix(unittest.TestCase):
    def setUp(self):
        # reference gene expected values
        with open('./json/reference_gene.json') as f:
            self.reference = json.load(f)
        # starter gene with 3 variants:
        self.gene = {
            u'name': u'testgene',
            u'count': 283,
            u'goals': 88,
            u'distinct': 215,
            u'description': u'an example gene with 3 variants',
            u'variants': [ {
                u'name': u'variant1',
                u'content': u'variant1 content',
                u'distinct': 67,
                u'count': 75,
                u'goals': 32,
                u'avg': 0.0,
                u'countsq': 0.0,
                u'weight': 0.0,
                u'within': 0.0,
                u'between': 0.0,
                u'wavg': 10.0,
                u'fitness': 0.0,
                u'countsq': 0.0
            },
            {
                u'name': u'variant2',
                u'content': u'variant2 content',
                u'distinct': 42,
                u'count': 84,
                u'goals': 22,
                u'avg': 0.0,
                u'countsq': 0.0,
                u'weight': 0.0,
                u'within': 0.0,
                u'between': 0.0,
                u'wavg': 10.0,
                u'fitness': 0.0,
                u'countsq': 0.0
            },
            {
                u'name': u'variant3',
                u'content': u'variant2 content',
                u'distinct': 106,
                u'count': 124,
                u'goals': 34,
                u'avg': 0.0,
                u'countsq': 0.0,
                u'weight': 0.0,
                u'within': 0.0,
                u'between': 0.0,
                u'wavg': 10.0,
                u'fitness': 0.0,
                u'countsq': 0.0
            } ]
        }

    def test_gene(self):
        expected = {
            'name': 'testing',
            'description': 'testgene description',
            'distinct': 0,
            'count': 0,
            'goals': 0,
            'variants': []
        }
        eq(g.gene('testing', 'testgene description'), expected)

    def test_variant(self):
        expected = {
           u'name': u'testvariant',
           u'content': u'testvariant content',
            u'distinct': 0,
            u'count': 0,
            u'goals': 0,
            u'avg': 0.0,
            u'countsq': 0,
            u'within': 0,
            u'between': 0.0,
            u'weight': 0.0,
            u'wavg': 10.0,
            u'fitness': 0.0,
            u'countsq': 0.0
        }
        eq(g.variant('testvariant', 'testvariant content'), expected)

    def test_calculate(self):
        g.calculate(self.gene)
        pprint(self.gene)
        pprint(self.reference)
        eq(self.gene, self.reference)
