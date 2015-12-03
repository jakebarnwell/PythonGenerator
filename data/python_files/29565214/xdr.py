
import tests
import os, sys
import subprocess
import itertools
import numpy as np

import xdr
import theormsd


def get_rmsds(xtcname, topol):
    xvgname = '/tmp/test.xvg'
    ndxname = os.path.join(tests.mydir, 'test.ndx')
    cmd     = 'g_rms -f %(xtc)s -s %(topol)s -n %(ndx)s -o %(xvg)s' % {
        'xtc'   : xtcname,
        'topol' : topol,
        'ndx'   : ndxname,
        'xvg'   : xvgname }

    with open('/dev/null', 'w') as fd:
        subprocess.check_call(cmd.split(), stdout=fd, stderr=fd)

    nframes = 751
    rmsds = np.zeros(751)
    ignore_starts = set('# @'.split())
    with open(xvgname) as fd:
        for i, l in enumerate(itertools.imap(str.strip, fd)):
            if l[0] in ignore_starts: continue
            rmsds[i] = float(l.split()[-1])

    os.unlink(xvgname)
    return rmsds

def test_XTCFile():
    xtcin  = os.path.join(tests.mydir, 'test.xtc')
    xtcout = '/tmp/testout.xtc'

    with xdr.XTCFile(xtcin) as fdin, xdr.XTCFile(xtcout, 'w', overwrite=True) as fdout:
        for fr, frame in enumerate(fdin):
            fdout.write(frame)

    topol    = os.path.join(tests.mydir, 'test.pdb')
    rmsds    = get_rmsds(xtcin, topol)
    expected = get_rmsds(xtcout, topol)

    if not (rmsds == expected).all():
        return False, 'Written RMSDs do not equal expected values'

    os.unlink(xtcout)
    return True, ()


def test_TRRFile():
    trrin = os.path.join(tests.mydir, 'test.trr')
    xtcout = '/tmp/testout.xtc'

    with xdr.TRRFile(trrin) as trr, xdr.XTCFile(xtcout, 'w', overwrite=True) as xtc:
        for fr, frame in enumerate(trr):
            xtcframe = xdr.XTCFrame(frame.coords, fr, frame.time, box=frame.box)
            xtc.write(xtcframe)

    topol    = os.path.join(tests.mydir, 'test.pdb')
    rmsds    = get_rmsds(trrin, topol)
    expected = get_rmsds(xtcout, topol)

    diff = abs(rmsds - expected)
    epsilon = 10E-5

    if diff.max() > epsilon:
        return False, 'Written RMSDs do not equal expected values. Max diff: %s e: %s' % (diff.max(), epsilon)

    return True, ()


tests.run(test_XTCFile,
          test_TRRFile)
