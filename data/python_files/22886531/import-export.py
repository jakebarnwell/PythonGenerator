import sys
from Pyblio import Selection, Sort

how = sys.argv [2]

if how == '': how = None

a = bibopen (sys.argv [3], how)

f = open (sys.argv [4], 'w')

# write out in the key order
sel = Selection.Selection (sort = Sort.Sort ([Sort.KeySort ()]))
it  = sel.iterator (a.iterator ())

bibwrite (it, out = f, how = a.id)
