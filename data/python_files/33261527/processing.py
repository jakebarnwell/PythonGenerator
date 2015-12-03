import icc.xray.analysis.scaling as scaling
import icc.xray.analysis.lines as lines
import sys
#import pygtk
#pygtk.require('2.0')
#import gtk, gobject, sys, os

def line_db_conn():
    if os.name!="nt":
        ldb=lines.Lines(dbname='/home/eugeneai/Development/codes/dispersive/data/lines.sqlite3')
    else:
        ldb=lines.Lines(dbname='C:\\dispersive\\data\\lines.sqlite3')
    return ldb

HOST='localhost'
PORT=12211
sprocessing=None
if __name__=="__main__" and len(sys.argv)==2 and sys.argv[1]=='server':
    from rpyc.core import SlaveService
    from rpyc.utils.server import ThreadedServer, ForkingServer
    print "Server", sys.argv
    SERVER = True
else:
    SERVER = True
    test_case=False
    import rpyc
    import os
    print "Client", sys.argv
    if not sys.argv[0].endswith('rpyc_classic.py'):
        SERVER = False
        import pygtk
        pygtk.require('2.0')
        import gtk, gobject, sys, os
        server=rpyc.classic.connect(HOST, PORT)
        sprocessing = server.modules['icc.xray.views.processing']
        print "Client:", server, sprocessing
        test_case=True


class Stub:
    pass

class Parameters(object):
    e_0 = 0.0086
    def __init__(self, model=None, view=None, client=None):
        #threading.Thread.__init__(self)
        global SERVER,sprocessing
        self.SERVER=SERVER
        print "Client-dat", client
        if client:
            self.model = client.model
            self.view = client.view
            self._methods=client._methods
            self._active=client._active
        else:
            self.model = model
            self.view = view
            if model == None:
                model=Stub()
                model.parameters=Stub()
                self.model=model
            if self.model.parameters == None:
                self.model.parameters = scaling.Parameters(model.channels)
            self._methods=[]
            self._active=False
            self.obj=sprocessing.Parameters(client=self)

    def set_progressbar(self, pb):
        self.progressbar=pb

    def set_max_step(self, steps):
        self.pb_max=steps
        self.set_fraction(0., steps)

    def set_step(self, step):
        self.pb_step=step
        self.set_fraction(step, self.pb_max)

    def reset_progress(self, steps=None):
        self.pb_step=0
        if steps:
            self.set_max_step(steps)
        else:
            self.set_fraction(step, self.pb_max)

    def next_step(self):
        self.pb_step+=1
        self.set_fraction(self.pb_step, self.pb_max)

    def set_fraction(self, step, steps=None):
        if steps != None:
            frac=float(step)/steps
        else:
            frac=step
        if hasattr(self, 'client_obj'):
            self.client_obj.set_fraction(frac)
        else:
            gtk.threads_enter()
            self.progressbar.set_fraction(frac)
            gtk.threads_leave()

    def server_methods(self, names):
        self._methods=names

    def methods(self, names):
        print self.SERVER
        self.obj.server_methods(names)

    def start(self):
        print "SERVER", self.SERVER
        self.run()

    def run(self):
        self.obj.server_run(self)

    def server_run(self, client):
        self._active=True
        self.client_obj=client
        o=self
        pref='server_'
        if not self.SERVER:
            o=self.obj
            pref=''
        for m in o._methods:
            m=pref+m
            getattr(o, m)()
        self.client_obj=None
        del self.client_obj
        self._active=False

    def scaling(self):
        return self.obj.server_scaling()

    def server_scaling(self):
        #While the stopthread event isn't setted, the thread keeps going on
        self.reset_progress(9)

        par=self.model.parameters
        ######pb=self.progressbar

        par.set_scale_lines(self.e_0, ['Mo'], 20.) # 20 keV max
        ldb=line_db_conn()
        par.set_line_db_conn(ldb)
        par.calculate(plot=False, pb=self.next_step)
        #par.scan_peakes_cwt(plot=True)

    def server_show(self):
        self.client_obj.show()

    def show(self):
        par=self.model.parameters
        elements=self.model.ptelements
        print "EL:", elements
        le=len(elements)
        if le:
            ldb=line_db_conn()
            ls = ldb.as_deltafun(order_by="keV", element=elements,
                    where="not l.name like 'M%' and keV<20.0")
            ls=list(ls)
        gtk.threads_enter()
        self.view.paint_model([self.model], draw=False)
        par.set_figure(self.view.ui.ax)
        if le:
            par.line_plot(ls, self.view.plot_options)
        self.view.ui.canvas.draw_idle()
        gtk.threads_leave()

    def refine(self):
        self.obj.refine()

    def server_refine(self):
        par=self.model.parameters
        elements=list(self.model.ptelements)
        self.server_scaling()
        self.reset_progress(3)
        par.refine_scale(elements=elements, pb=self.next_step)

    def background(self):
        self.obj.server_background()

    def server_background(self):
        par=self.model.parameters
        elements=list(self.model.ptelements)
        self.server_scaling()
        self.reset_progress(11)
        par.approx_background(elements=elements, pb=self.next_step)

    def stop(self):
        """Stop method, sets the event to terminate the thread's main loop"""
        #self.stopthread.set()

    def is_active(self):
        return self._active

if SERVER:
    '''
    t = ThreadedServer(SlaveService, hostname = 'localhost',
        port = PORT, #reuse_addr = True, # ipv6 = options.ipv6,
        #authenticator = options.authenticator, registrar = options.registrar,
        #auto_register = options.auto_register
        )
    t.logger.quiet = True
    t.start()
    '''
elif test_case:
    p=Parameters()
    print "OK"

