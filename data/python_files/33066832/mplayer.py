import os
import subprocess
import os.path
import atexit
import errno
from subprocess import PIPE
from fcntl import fcntl, F_GETFL, F_SETFL
from time import time, sleep
from uuid import uuid4 as genuuid
from time import time

class MPlayerAnswerError(Exception):
    pass

class MPlayerNoAnswerError(Exception):
    pass

class MPlayerController(object):
    def __init__(self):
        print("It's making an MPLAYER!")
        # get a hold of a "dev/null" file
        DEVNULL = open('/dev/null', 'wb')

        # start mplayer
        args = ['mplayer', '-slave', '-idle', '-quiet']
        self.mplayer = subprocess.Popen(args, stdin=PIPE, stdout=PIPE, stderr=DEVNULL, close_fds=True)

        # set the std out to non-blocking
        fl = fcntl(self.mplayer.stdout, F_GETFL)
        fcntl(self.mplayer.stdout, F_SETFL, fl | os.O_NONBLOCK)

    def __del__(self):
        print('---KILLING MPLAYER---')
        self.mplayer.stdout.read()
        self.mplayer.terminate()
        self.mplayer.wait()

    def doCmd(self, args, answer_phrase=None, timeout=2.0):
        # consume any left-over crud
        try:
            part = self.mplayer.stdout.read()
#            if part:
#                print('discarding', part)
        except IOError as e:
            pass

#        print('Doing CMD', args)
        cmdbytes = (' '.join([x.replace(' ', '\ ') for x in args] + ['\n']))
        self.mplayer.stdin.write(cmdbytes)

        if answer_phrase == None:
            return

        # only wait for a response for timeout seconds
        answer = ''
        start_time = time()
        while True:
            try:
                part = self.mplayer.stdout.read() # NOTE: using non-blocking FD, so this will return '' rather than block
            except IOError as e:
                if e.errno == errno.EAGAIN:
                    part = ''
                else:
                    print("IOERROR", e)
                    break

            if part == '':
                if time()-start_time >= timeout:
                    break

                sleep(0.01) # don't steal CPU from the guy we want to answer us
                continue

            answer += part
            # throw out useless lines till we get to our answer
            while '\n' in answer:
                line, rest = answer.split('\n', 1)
                if line.startswith('ANS_ERROR'):
                    raise MPlayerAnswerError(line[10:])
                elif line.startswith(answer_phrase):
#                    print('Got answer', line)
                    return line[len(answer_phrase)+1:]

                # discard pointless lines
#                print('discarding', line)
                answer = rest

        raise MPlayerNoAnswerError('Got no response from Mplayer')

    def playFile(self, path):
        self.doCmd(['loadfile', path], answer_phrase='Starting playback', timeout=10.0)

    def stop(self):
        self.doCmd(['stop'])
        sleep(0.5) # want the vid to have stopped before we return

    @property
    def playing(self):
        try:
            self.doCmd(['pausing_keep_force', 'get_property', 'filename'], 'ANS_filename')
            return True
        except MPlayerAnswerError:
            return False

    @property
    def paused(self):
        return (self.doCmd(['pausing_keep_force', 'get_property', 'pause'], 'ANS_pause')).lower() == 'yes'
    @paused.setter
    def paused(self, val):
        # mplayer only has toggle, so get current state and adjust accordingly
        cp = self.paused
        if cp != val:
            self.doCmd(['pause'])

    @property
    def duration(self):
        return self.doCmd(['pausing_keep_force', 'get_property', 'length'], 'ANS_length')

    @property
    def position(self):
        return float(self.doCmd(['pausing_keep_force', 'get_property', 'time_pos'], 'ANS_time_pos'))
    @position.setter
    def position(self, val):
        self.doCmd(['pausing_keep_force', 'set_property', 'time_pos', str(val)])

