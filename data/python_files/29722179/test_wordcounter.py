import unittest
from cStringIO import StringIO

from wordcounter import sortWords
from wordcounter import countWords
from wordcounter import cleanWords
from wordcounter import printWords
from wordcounter import readFile


class TestWordCounter(unittest.TestCase):

    def testSortWords(self):
        words = [['a', 1], ['c', 2], ['b', 3], ['e', 1], ['d', 1], ['f', 1]]
        got = sortWords(words)
        expect = [['b', 3], ['c', 2], ['a', 1], ['d', 1], ['e', 1], ['f', 1]]
        self.assertEqual(got, expect)

    def testCleanWords(self):
        words = ['a', 'frank', '.why', '1bc', 'bd3', "don't", 'but.', '123',
                 'Frank', 'I', '.']
        got = cleanWords(words)
        expect = ['a', 'frank', 'why', '1bc', 'bd3', "don't", 'but', '123',
                  'frank', 'I']
        self.assertEqual(got, expect)

    def testCountWords(self):
        words = ['a', 'frank', 'why', "don't", 'but', 'a', 'frank', 'why',
                 'frank', 'frank']
        got = countWords(words)
        expect = [['a', 2], ['frank', 4], ['why', 2], ['but', 1], ["don't", 1]]
        self.assertEqual(got, expect)

    def testReadFile(self):
        tempfile = StringIO()
        tempfile.write('abc 123 the')
        tempfile.seek(0)
        got = readFile(tempfile)

        expect = ['abc', '123', 'the']
        self.assertEqual(got, expect)
        tempfile.close()

    def testPrintWords(self):
        tempfile = StringIO()
        words = [('b', 3), ('c', 2), ('a', 1), ('d', 0)]
        printWords(tempfile, words)
        tempfile.seek(0)
        got = tempfile.read()
        expect = '3 b\n2 c\n1 a\n0 d\n'
        self.assertEqual(got, expect)
        tempfile.close()

if __name__ == '__main__':
    unittest.main()
