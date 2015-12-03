import sys
import traceback
import os
from os import path, popen
from operator import itemgetter
from sys import platform
from time import sleep

gnuplot_exe_list = [r'"C:\Program Files\gnuplot\pgnuplot.exe"', "/usr/bin/gnuplot","/usr/local/bin/gnuplot"]


class gnuplot:
	def __init__(self, term='onscreen'):
		# -persists leave plot window on screen after gnuplot terminates
		if platform == 'win32':
			cmdline = gnuplot_exe
			self.__dict__['screen_term'] = 'windows'
		else:
			cmdline = gnuplot_exe + ' -persist'
			self.__dict__['screen_term'] = 'x11'
		self.__dict__['iface'] = popen(cmdline,'w')
		self.set_term(term)

	def set_term(self, term):
		if term=='onscreen':
			self.writeln("set term %s" % self.screen_term)
		else:
			#term must be either x.ps or x.png
			if term.find('.ps')>0:
				self.writeln("set term postscript eps color 22")
			elif term.find('.png')>0:
				self.writeln("set term png")
			else:
				print("You must set term to either *.ps or *.png")
				raise SystemExit
			self.output = term
		
	def writeln(self,cmdline):
		self.iface.write(cmdline + '\n')

	def __setattr__(self, attr, val):
		if type(val) == str:
			self.writeln('set %s \"%s\"' % (attr, val))
		else:
			print("Unsupport format:", attr, val)
			raise SystemExit

	#terminate gnuplot
	def __del__(self):
		self.writeln("quit")
		self.iface.flush()
		self.iface.close()

	def __repr__(self):
		return "<gnuplot instance: output=%s>" % term

	#data is a list of [x,y]
	def plotline(self, data):
		self.writeln("plot \"-\" notitle with lines linewidth 1")
		for i in range(len(data)):
			self.writeln("%f %f" % (data[i][0], data[i][1]))
			sleep(0) #delay
		self.writeln("e")
		if platform=='win32':
			sleep(3)


def read_pred(res_p):
	try:
		res_f = open(res_p, 'r')
	except IOError:
		traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
								  sys.exc_info()[2])
	pred_l = []
	dec_l = []
	for l in res_f:
		bl = l.split()
		if len(bl) == 2:
			if bl[0].find('dec_values') != -1:
				dec_l.append(float(bl[1]))
			elif bl[0].find('pred_results') != -1: 
					pred_l.append(float(bl[1]))	
	return pred_l,  dec_l


def read_act(act_p):
	try:
		act_f = open(act_p, 'r')
	except IOError:
		traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
								  sys.exc_info()[2])
	act_l = []
	for l in act_f:
		act_l.append(float(l.split(' ')[0]))
	return act_l


def get_tp_tn(pred_l, actu_l):
	tp_l = []; tn_l = []
	tp1 = 0; fp1 = 0; tn0 = 0; fn0 = 0;
	for i, pred in enumerate(pred_l):
		if pred == actu_l[i]:
			if pred == 1:
				tp1 += 1
				tp_l.append(pred)
			elif pred == -1:
				tn0 += 1
				tn_l.append(pred)
		else:
			if pred == 1:
				fn0 += 1
			elif pred == -1:
				fp1 += 1
	print 'TP  ', 'FP    ', 'TN  ', 'FN   '
	print tp1, fp1, tn0, fn0
	return tp_l, tn_l


def check_gnuplot_exe():
	global gnuplot_exe
	gnuplot_exe = None
	for g in gnuplot_exe_list:
		if path.exists(g.replace('"','')):
			gnuplot_exe=g
			break
	if gnuplot_exe == None:
		print("You must add correct path of 'gnuplot' into gnuplot_exe_list")
		raise SystemExit


def plot_roc(deci, label, output, title):
	#count of postive and negative labels
	db = []
	pos, neg = 0, 0 		
	for i in range(len(label)):
		if label[i]>0:
			pos+=1
		else:	
			neg+=1
		db.append([deci[i], label[i]])

	#sorting by decision value
	db = sorted(db, key=itemgetter(0), reverse=True)

	#calculate ROC 
	xy_arr = []
	tp, fp = 0., 0.			#assure float division
	for i in range(len(db)):
		if db[i][1]>0:		#positive
			tp+=1
		else:
			fp+=1
		xy_arr.append([fp/neg,tp/pos])

	#area under curve
	aoc = 0.			
	prev_x = 0
	for x,y in xy_arr:
		if x != prev_x:
			aoc += (x - prev_x) * y
			prev_x = x
	print aoc

	"""
	#begin gnuplot
	if title == None:
		title = output
	#also write to file
	g = gnuplot(output)
	g.xlabel = "False Positive Rate"
	g.ylabel = "True Positive Rate"
	g.title = "ROC curve of %s (AUC = %.4f)" % (title,aoc)
	g.plotline(xy_arr)
	#display on screen
	s = gnuplot('onscreen')
	s.xlabel = "False Positive Rate"
	s.ylabel = "True Positive Rate"
	s.title = "ROC curve of %s (AUC = %.4f)" % (title,aoc)
	s.plotline(xy_arr)
	"""
	return aoc



def process_options(argv=sys.argv):
	
	usage = """
			python plot_roc.py -a actualFiles -p prediction files
		"""

	are_act, are_pred = False, False
	act, pred = [], []
	if len(argv) < 2:
		print(usage)
		sys.exit(1)

	i = 1
	while i < len(argv) :
		if argv[i] == "-a":
			are_act = True
			are_pred = False
		elif argv[i] == "-p":
			are_act = False
			are_pred = True
		elif are_act:
			assert os.path.exists(argv[i]),"dataset not found"
			act.append(argv[i])
		elif are_pred:
			assert os.path.exists(argv[i]),"dataset not found"
			pred.append(argv[i])
		i = i + 1

	if len(act) == 0 or len(pred) == 0:
		raise RuntimeError("The paths are empty cannot be empty.")

	return act, pred 



if __name__ == '__main__':
	p_rocs = {}
	act, pred = process_options()
	for i in range(len(act)):
		actu_l = read_act(act[i])
		pred_l, dec_values = read_pred(pred[i])
		print '_'*10
		print pred[i], act[i]
		#print len(pred_l), len(actu_l), len(dec_values)
		tp_l, tn_l = get_tp_tn(pred_l, actu_l)
		#print len(tp_l), len(tn_l)
		print '_'*10
		#check_gnuplot_exe()
		p = act[i]
		aoc = plot_roc(dec_values, actu_l, p+'.png', p)
		p_rocs[p] = aoc
	for p, aoc in p_rocs.items():
		print p, aoc
