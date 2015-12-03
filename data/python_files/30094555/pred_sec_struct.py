import os
import shutil
import sys
import re
import traceback
import getpass
import random
from multiprocessing import Process
from threading import Thread
from subprocess import Popen, PIPE
if(sys.hexversion < 0x03000000):
	import Queue
else:
	import queue as Queue

from c_only_secondary_data_set import secStructOnlyManipulation
import ssh_connection

psipred_exe = '/home/ba2g09/psi_pred/runpsipred'


ssh_workers = (
			['zombie'] * 5 +
			['lich'] * 5 +
			['shark'] * 5 +
			['skeleton'] * 5 +
			['ghoul'] * 5 +
			['whale'] * 5 +
			['porpoise'] * 5 +
			['seal'] * 5 +
			['banshee'] * 1 +
			['bass'] * 5 +
			['butterfish'] * 5 +
			['bream'] * 5 +
			['chard'] * 5 +
			['clam'] * 5 +
			['conch'] * 5 +
			['walrus'] * 5 +
			['manatee'] * 5 +
			['mummy'] * 5 +
			['wraith'] * 5 +
			['kelp'] * 5 +
			['octopus'] * 5 +
			['eel'] * 5 +
			['pumpkin'] * 5 +
			['potato'] * 5 +
			['cockle'] * 5 +
			['seacucumber'] * 5 +
			['seapineapple'] * 5 +
			['crab'] * 5 +
			['crayfish'] * 5 +
			['cuttlefish'] * 5 +
			['blowfish'] * 5 +
			['bluefish'] * 5 +
			['celery'] * 5 +
			['pignut'] * 5 +
			['parsnip'] * 5 +
			['swede'] * 5 +
			['sweetpepper'] * 5 +
			['sprout'] * 5 +
			['spinach'] * 5 +
			['brill'] * 5 
			)


def c_ps_file(p, seq, path_to):
	if not path_to.endswith('/'):
		path_to += '/'
	try:
		p_f = open(path_to + p + '.fasta', 'w')
		p_f.write('>' + p + '\n')
		p = re.compile('[\r\n, \n]')
		seq = p.sub ('', seq)
		p_f.write(seq)
		p_f.close()
	except IOError:
			traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
										  sys.exc_info()[2])


def c_all_ps_files(ps_dict, psec_dict, dest_dir='tmp_pseq_for_prediction'):
	try:
		os.mkdir(dest_dir)
		for p, seq in ps_dict.items():
			if p in psec_dict:
				if psec_dict[p].startswith('NotFound'):
					c_ps_file(p, seq, dest_dir)
					#print p, cnt
			if p not in psec_dict:
				c_ps_file(p, seq, dest_dir)
				#print p, cnt
	except OSError:
			traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
										  sys.exc_info()[2])


class WorkerStopToken:  # used to notify the worker to stop
		pass


class Worker(Thread):
	def __init__(self, name, job_queue, result_queue):
		Thread.__init__(self)
		self.name = name
		self.job_queue = job_queue
		self.result_queue = result_queue
	def run(self):
		while True:
			prot_p = self.job_queue.get()
			if prot_p is WorkerStopToken:
				###print 'closing ' + self.name
				self.job_queue.put(prot_p)
				# print('worker {0} stop.'.format(self.name))
				break
			try:
				done = self.run_one(prot_p)
				print self.name + ' Running ' + prot_p
				if done is None: raise RuntimeError("Could not Finish")
			except:
				# we failed, let others do that and we just quit
				traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
										  sys.exc_info()[2])
				self.job_queue.put(prot_p)
				print('worker {0} quit.'.format(self.name))
				break
			else:
				self.result_queue.put((self.name, prot_p, done))


class LocalWorker(Worker):
	def run_one(self, prot_p):
		###print self.name + ' Running :' + prot_p
		cmdline = ('{0} {1}'.format(psipred_exe, prot_p))
		result = Popen(cmdline,shell=True,stdout=PIPE).stdout
		for line in result.readlines():
			#print line
			if str(line).find("Finished.") != -1:
				###print self.name + ' Finished :' + prot_p
				return 1


class SSHWorker(Worker):
	def __init__(self,name,job_queue,result_queue,host):
		Worker.__init__(self,name,job_queue,result_queue)
		self.host = host
		self.cwd = os.getcwd()
	def run_one(self, prot_p):
		cmd_str = 'ssh -x {0} "cd {1}; {2} {3}"'
		cmdline = cmd_str.format(self.host, self.cwd, psipred_exe, prot_p)
		print cmdline
		result = Popen(cmdline,shell=True,stdout=PIPE).stdout
		for line in result.readlines():
			#print line
			if str(line).find("Finished.") != -1:
				###print self.name + ' Finished :' + prot_p
				return 1

#Run the following for multi threaded run
def main_psipred(prot_p_l, nr_local_worker):
	global ssh_workers
	jobs = prot_p_l
	total_jobs = 0
	job_queue = Queue.Queue(0)
	result_queue = Queue.Queue(0)

	for prot_p in jobs:
		total_jobs += 1
		#print prot_p
		job_queue.put(prot_p)
	job_queue._put = job_queue.queue.appendleft
	print 'Total jobs:',  total_jobs

	#Get password for ssh connections
	password = getpass.getpass('Password:')
	if password != '':
		hostnames = ssh_workers
		ssh_connector = ssh_connection.SSHConnection(hostnames_l=hostnames,
						password=password)
		# make connection to ssh workers first
		ssh_connector.conn_to_clients_wait()
		ssh_workers = ssh_connector.conn_l
		random.shuffle(ssh_workers)
		# fire ssh workers
		if ssh_workers:
			for host in ssh_workers:
				SSHWorker(host,job_queue,result_queue,host).start()

	# fire local workers
	for i in range(nr_local_worker):
		LocalWorker('local' + str(i), job_queue, result_queue).start()

	done_jobs = {}
	for prot_p  in jobs:
		#while prot_p not in done_jobs:
		#print '^'*50
		#print 'Came for', prot_p
		#NOTE that get waites untile the queue has an item in it
		(worker, prot_p,  done) = result_queue.get()
		#print 'Got', prot_p
		#print '_'*50
		done_jobs[prot_p] = done

		nr_done_jobs = len(done_jobs)
		perc = nr_done_jobs * 100.0 / total_jobs
		perc = round(perc, 3)
		state = ("["+ str(nr_done_jobs) + " out of " + str(total_jobs) +
					" " + str(perc)+"%]")
		result = '[{0}] {1}'.format(worker, prot_p)
		print(result + "|" + state)

	print 'Done'
	job_queue.put(WorkerStopToken)

#NOTE Does not do anything just changes one file (Not USED)
def run_psipred(prot_p):
	cmd_line = psipred_exe + ' ' + prot_p
	print cmd_line
	result = Popen(cmd_line, shell=True, stdout=PIPE).stdout
	for line in result.readlines():
		print line


def read_sec_ss2_format(ss2_path):
	try:
		ss2_f = open(ss2_path, 'r')
		sec = ''
		for l in ss2_f:
			l_arr = l.split()
			if len(l_arr) == 6:
				if l_arr[2] == 'H':
					sec += 'h'
				elif l_arr[2] == 'E':
					sec += 'b'
				else:
					sec += '_'
		ss2_f.close()
		return sec
	except IOError,e:
		#sys.stderr('cannot open the file' + str(e) + '\n')
		traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
									  sys.exc_info()[2])


def c_all_sec_f(all_prot_d, sec_dir, res_p='all_p_sec_dict.txt'):
	all_p = {}
	res_f = open(res_p, 'w')
	ss2 = filter(lambda a: a.endswith('.ss2'), os.listdir(sec_dir))

	for p, sec in all_prot_d.items():
		if sec.startswith('NotFound'):
			path = p+'.ss2'
			if path in ss2:
				sec = read_sec_ss2_format(path) + '\r\n'
		all_p[p] = sec
		res_f.write(p + '\t' + sec)


def mv_done_prots_to(des_p='done_jobs', src_p='.'):
	""" Moves the proteins of fasta format which have been predicted to a
		destination directory

		des_p -- path to move the done files to


	"""
	assert os.path.exists(des_p), 'The des_p does not exists'
	assert os.path.exists(src_p), 'The src_p does not exists'
	a = os.listdir(src_p)
	fasta_l = filter(lambda i: i.endswith('.fasta'), a)
	ss_l = filter(lambda i: i.endswith('.ss'), a)
	ss2_l = filter(lambda i: i.endswith('.ss2'), a)
	horiz_l = filter(lambda i: i.endswith('.horiz'), a)
	for ss2 in ss2_l:
		p = ss2.split('.')[0]
		fasta = p + '.fasta'
		ss = p + '.ss'
		horiz = p + '.horiz'
		if fasta not in fasta_l:
			print fasta, 'not in fasta list'	
			continue
		if ss not in ss_l:
			print ss, 'not in ss list'	
			continue
		if horiz not in horiz_l:
			print horiz, 'not in horiz list'	
			continue
		shutil.move(fasta, des_p)
		shutil.move(ss, des_p)
		shutil.move(ss2, des_p)
		shutil.move(horiz, des_p)





if __name__ == '__main__':
	"""
	#NOTE uncomment for create files
	#Put every protein in a list in a file format fasta
	p_seq_p = os.path.join(
				os.path.abspath('../data'),
				'p_seq_dict_yeast_154828_formatted.txt'
			)
	p_sec_p = os.path.join(
				os.path.abspath('../data'),
				'yeast_p_sec_struct_dict__formatted.txt'
			)

	seqManip = secStructOnlyManipulation(
				p_seq_p=p_seq_p,
				p_sec_p=p_sec_p,
			)
	seqManip.r_ps_dict_from_f()
	seqManip.r_psec_dict_from_f()
	c_all_ps_files(seqManip.ps_dict, seqManip.psec_dict)
	print len(seqManip.ps_dict)
	print len(seqManip.psec_dict)
	#####################################################
	"""
	"""
	#NOTE uncomment to predict secondary struct of all 
	#of the files in the current folder
	files = os.listdir('.')
	files = filter(lambda a : a.endswith('fasta'), files)
	main_psipred(files, 0)
	#####################################################
	"""
	"""
	###########################################
	# Moves the .ss2, .horiz, .ss and the .fasta connect to them, into a dest_p
	#mv_done_prots_to()
	###########################################
	"""
	#Note uncomment to replace the NotFound secondary sttuctures
	#in the dictionary with the predicited one and write to files
	#in the CURRENT directory
	data_p = '/home/ba2g09/workspace/summer_internship/data'
	p_seq_p = os.path.join(
				os.path.abspath(data_p),
				'p_seq_dict_yeast_154828_formatted.txt'
			)
	p_sec_p = os.path.join(
				os.path.abspath(data_p),
				'yeast_p_sec_struct_dict__formatted.txt'
			)
	seqManip = secStructOnlyManipulation(
				p_seq_p=p_seq_p,
				p_sec_p=p_sec_p,
			)
	seqManip.r_ps_dict_from_f()
	seqManip.r_psec_dict_from_f()
	c_all_sec_f(seqManip.psec_dict, '.')
