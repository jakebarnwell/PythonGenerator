import unittest                    # Import unittest framework
import add                         # Import add.py (from ../src/)
import subtract                    # Import subtract.py (from ../src/)
from trig import sincos            # Import sincos.py (from ../src/trig/)
from text import hello, goodbye    # Import hello.py, goodbye.py (from ../src/text/)

# Returns the unittest.TestSuite objects for each module in tests list 
def math_suite():
    ''' Define test suite for math features'''
    # Modules to load TestCases from to put into the TestSuite instance 
    tests = [add, subtract, sincos]
    return unittest.TestSuite(map(unittest.TestLoader().loadTestsFromModule, tests))

# Returns the unittest.TestSuite objects for each module in tests list 
def text_suite():
    ''' Define test suite for text features'''
    # Modules to load TestCases from to put into the TestSuite instance 
    tests = [hello, goodbye]
    return unittest.TestSuite(map(unittest.TestLoader().loadTestsFromModule, tests))

# Create the all_tests variable as a Test Suite
all_tests = unittest.TestSuite()

# Add math_suite which will test math features
# "A TestSuite instance can be added to a TestSuite just as a TestCase instance
#  can be added to a TestSuite."
#    -- http://docs.python.org/library/unittest.html#organizing-test-code
all_tests.addTest(math_suite())

# Add text_suite which will test text features
all_tests.addTest(text_suite())

# Run the tests all together
unittest.TextTestRunner(descriptions=2,verbosity=2).run(all_tests)
