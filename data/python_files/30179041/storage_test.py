import unittest
from nose.tools import eq_ as eq, ok_ as ok, raises, timed
import os, sys
import json

from genetix import Genetix
from genetix.storage import JSONFiles
import genetix.stats

# create with json storage
g = Genetix(JSONFiles('./json'))

class TestStorage(unittest.TestCase):
    def setUp(self):
        # reference gene for expected values
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
                'goalsq': 0.0,
                'weight': 0.0,
                'within': 0.0,
                'between': 0.0,
                'wavg': 10.0,
                'fitness': 0.0,
                'countsq': 0.0
            },
            {
                'name': 'variant2',
                'content': 'variant2 content',
                'distinct': 42,
                'count': 84,
                'goals': 22,
                'avg': 0.0,
                'goalsq': 0.0,
                'weight': 0.0,
                'within': 0.0,
                'between': 0.0,
                'wavg': 10.0,
                'fitness': 0.0,
                'countsq': 0.0
            },
            {
                'name': 'variant3',
                'content': 'variant2 content',
                'distinct': 106,
                'count': 124,
                'goals': 34,
                'avg': 0.0,
                'goalsq': 0.0,
                'weight': 0.0,
                'within': 0.0,
                'between': 0.0,
                'wavg': 10.0,
                'fitness': 0.0,
                'countsq': 0.0
            } ]
        }

    def test_write(self):
        pass

    def test_read(self):
        pass

    def test_exists(self):
        pass
