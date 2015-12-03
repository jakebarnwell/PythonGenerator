import os
import jsonrpc
import socket
from library import configure

from svnup import update
from invalidate import invalidate
from catalog import index

from sensible.loginit import logger
log = logger(os.path.basename(__file__))

class Dispatcher(object):

    def __init__(self, broker_url):        
        self.broker = jsonrpc.Client(broker_url) 
        
    def run(self):
        msg = cmd = ''
        try:
            msg = self.broker.send()
        except socket.error, e:
            log.error(str(e))
        
        if msg:
            log.debug('message:', msg)
            cmd, arg = msg.split(':')
            if cmd:
                cmd_name = 'do_%s' % cmd
                m = getattr(self, cmd_name, None)
                if m:
                    try:
                        msg = m(arg)
                    except Exception, e:
                        log.exception(str(e))
                    else:
                        log.info(msg)
                else:
                    log.error('Unknown command: %s:%s' % (cmd, arg))
            else:
                log.error('Unknown message: %s' % msg)


    def do_update(self, arg):
        return update(arg)
        
    def do_invalidate(self, arg):
        return invalidate(arg)
        
    def do_index(self, arg):
        return index(arg)

def main():
    config = configure()
    d = Dispatcher(config.get('broker_url'))
    d.run()
    
if __name__ == '__main__':
    log.info('Dispatcher: starting...')
    main()