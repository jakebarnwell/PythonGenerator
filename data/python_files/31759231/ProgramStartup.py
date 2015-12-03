import sys
import signal
import string
import Tkinter
import netsvc

try:
  import Pmw
except:
  print "This program requires the Python Megawidgets (Pmw) module."
  print "Pmw can be obtained free from 'http://pmw.sourceforge.net'."
  sys.exit()

class Reaper(netsvc.Agent):

  def __init__(self,root):

    netsvc.Agent.__init__(self)
    self.root = root
    self.subscribeShutdown(self.quit)

  def quit(self,type):
    if type == netsvc.SHUTDOWN_ARRIVED:
      self.root.quit()

try:
  import threading
except:
  print "Your version of Python does not include support for threading."
  sys.exit()

if not netsvc.threadingEnabled():
  print "Your version of OSE does not include support for threading."
  sys.exit()

if len(sys.argv) != 2:
  print "Usage: netspy hostname:port"
  sys.exit()

def run(window):
  try:
    dispatcher = netsvc.Dispatcher()

    dispatcher.disableWarnings()

    dispatcher.monitor(signal.SIGINT)

    root = Pmw.initialise()
    root.withdraw()

    main = window(root)

    root.update()

    target = sys.argv[1]

    try:
      group = ""
      group,address = string.splitfields(target,'@')
    except:
      host,port = string.splitfields(target,':')
    else:
      host,port = string.splitfields(address,':')

    exchange = netsvc.Exchange(netsvc.EXCHANGE_CLIENT,group)
    exchange.connect(host,int(port),5)

    reaper = Reaper(root)

    dispatcher.task().start()

    root.deiconify()
    root.update_idletasks()

    root.mainloop()

  finally:
    dispatcher.task().stop()
    dispatcher.task().wait()
