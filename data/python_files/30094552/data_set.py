import sys
import os
import traceback
import random
import getpass
import tarfile
from threading import Thread, RLock
from subprocess import Popen, PIPE
if(sys.hexversion < 0x03000000):
	import Queue
else:
	import queue as Queue

from p_code_input_output.c_data_set import SequenceManipulation, c_tar_f 
from p_code_input_output.c_secondary_data_set import secStructManipulation
import ssh_connection

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
nr_local_worker = 5


def f_rand_p_list(p_list, max_p=300):
	""" Picks max_p proteins randomly from p_list which is given to it and
	    then, it fills the results to rand_p_list and returns it.

	    Arguments:
	    p_list -- the list to pick proteins from
	    max_p -- maximum number of proteins to pick

	    Note: p_list is assumed to be a list of proteins only

	"""
	try:
		tmp_p_list = list(p_list)
		random.shuffle(tmp_p_list)
		rand_p_list = []
		for i in range(max_p):
			rand_p_list.append(tmp_p_list[i])
	except IndexError, e:
		print i
		err_mes = ("max_p was greater than length of p_list." +
				"[f_rand_p_list]:" + str(e) + '\n')
		sys.stderr.write (err_mes)
	return rand_p_list


def c_new_ppi_set(all_ppi_p='', rand_p_list=None, ppi_p=''):
	""" Creates new ppi test set. It reads (all) ppis from a file, then 
	    picks the proteins pairs which are in the rand_p_list at it puts
	    them in the ppi_list. If an ppi_p is given, it writes the ppis to
	    that file as well.

		Arguments:
		all_ppi_p -- The path containing all ppis which the the test will
				   be made of (input)

		Keyword Arguments:
		ppi_p -- The path to the file which ppis are writen to (output)
	
	"""
	try:
		ppi_f = open(ppi_p, 'w')
		tmp_ppi_list = []
		ppi_list = []
		seqManip = SequenceManipulation()
		seqManip.r_ppi_list_from_f(ppi_p=all_ppi_p)
		ppi_list = seqManip.ppi_list
		print 'Start creating new test set'
		for ppi in ppi_list:
			for (p1, p2), v in ppi.items():
				pass
			p1_is = False
			p2_is = False
			for p in rand_p_list:
				if p1 == p:
					p1_is = True
				if p2 == p:
					p2_is = True
				if p1_is and p2_is: # Change and to or to have all inst
					tmp_ppi_list.append(ppi)	
					ppi_f.write(p1 + ' ' + p2 + ' ' + v + '\r\n')
					break
		print 'Finished creating new test set'
		ppi_list = tmp_ppi_list	
		ppi_f.close()
	except IOError,e:
		sys.stderr('cannot open the file' + str(e) + '\n')


def c_complement_ppi_set(p_list, max_ppi=5000, **kwargs):
	""" Creates a ppi set which is the complement of the existing p_list

	    Arguments:
	    p_list -- The set which the complement will be made of

	    Keyword Arguments:
	    ppi_p -- The path which the complement will be from
	    ppi_comp_p -- The path to the file which ppis are writen to 
				   (output)
	

	    Note: p_list is assumed to be a list of proteins only

	"""
	ppi_p = kwargs.get('ppi_p', None)
	seqManip = SequenceManipulation()
	seqManip.r_ppi_list_from_f(ppi_p=ppi_p)
	ppi_list = seqManip.ppi_list

	ppi_comp_p = kwargs.get('ppi_comp_p', None)
	ppi_comp_f = None
	non_inter = 'non-interacting'
	try:
		print 'Creating complement set [c_complement_ppi_set]'
		if ppi_list == []:
			raise RuntimeError("ppi_list has to be filled")
		if ppi_comp_p is not None:
			ppi_comp_f = open(ppi_comp_p, 'w')
		tmp_p_list = list(p_list)
		random.shuffle(tmp_p_list)

		comp_ppi_list = []
		tmp_comp_ppi_dict = {}

		while len(comp_ppi_list) != max_ppi:
			p1 = tmp_p_list[random.randint(0, len(tmp_p_list)-1)]
			p2 = tmp_p_list[random.randint(0, len(tmp_p_list)-1)]
			for ppi in ppi_list:
				if (p1, p2) in ppi:
					print p1, p2, 'in complement list ppi_list'
					break
			if ((p1, p2) in tmp_comp_ppi_dict or 
					(p2, p1) in tmp_comp_ppi_dict):
				print p1, p2, 'has already been added'
				continue
			if ppi_comp_f is not None:
				ppi_comp_f.write( p1 + ' ' + p2  + ' ' +
							   str(non_inter) + '\r\n')
			tmp_comp_ppi_dict[(p1, p2)] = non_inter
			comp_ppi_list.append({(p1, p2) : non_inter})

		print 'finished creating complement set'
	except IndexError,e:
		err_mes = ("max_p was greater than length of p_list." +
				 "[c_complement_ppi_set]:" + str(e) + '\n')
		sys.stderr.write (err_mes)
				
	except IOError, e:
		sys.stderr('cannot open the file [c_complement_ppi_set]' +
				 str(e) + '\n')
	return comp_ppi_list


def c_balanced_complement_ppi_set(p_list, max_ppi=5000, **kwargs):
	""" Creates a balanced ppi set which is the complement of the 
	    existing p_list

	    Arguments:
	    p_list -- The set which the complement will be made of

	    Keyword Arguments:
	    ppi_p -- The path which the complement will be from
	    ppi_comp_p -- The path to the file which ppis are writen to 
				   (output)
	

	    Note: p_list is assumed to be a list of proteins only

	"""
	ppi_p = kwargs.get('ppi_p', None)
	seqManip = SequenceManipulation()
	print ppi_p
	seqManip.r_ppi_list_from_f(ppi_p=ppi_p)
	ppi_list = seqManip.ppi_list

	ppi_comp_p = kwargs.get('ppi_comp_p', None)
	ppi_comp_f = None
	non_inter = 'non-interacting'
	p_i, p_ni, p_both = check_for_balance(ppi_p) #Only interacting is filled
	try:
		print 'Creating complement set [c_complement_ppi_set]'
		if ppi_list == []:
			raise RuntimeError("ppi_list has to be filled")
		if ppi_comp_p is not None:
			ppi_comp_f = open(ppi_comp_p, 'w')
		tmp_p_list = list(p_list)
		random.shuffle(tmp_p_list)

		comp_ppi_list = []
		tmp_comp_ppi_dict = {}

		for p1, p_n in p_i.items():
			num_tried = 0 # Tried to generate a new set
			while p_i[p1] > 2:
				num_tried += 1
				if num_tried > 80:
					break # break in case too many times tried
				p2 = tmp_p_list[random.randint(0, len(tmp_p_list)-1)]
				if p1 == p2:
					continue
				if p2 not in p_i or p_i[p2] == 0:
					continue
				for_broke = False
				for ppi in ppi_list:
					if (p1, p2) in ppi:
						print p1, p2, 'in complement list ppi_list'
						for_broke = True
						break
				if for_broke:
					continue
				if ((p1, p2) in tmp_comp_ppi_dict or 
						(p2, p1) in tmp_comp_ppi_dict):
					print p1, p2, 'has already been added'
					continue
				if ppi_comp_f is not None:
					ppi_comp_f.write( p1 + ' ' + p2  + ' ' +
								   str(non_inter) + '\r\n')
				tmp_comp_ppi_dict[(p1, p2)] = non_inter
				comp_ppi_list.append({(p1, p2) : non_inter})
				# p_n -= 1
				p_i[p1] -= 1
				p_i[p2] -= 1
		print 'finished creating complement set'

	except IndexError,e:
		err_mes = ("max_p was greater than length of p_list." +
				 "[c_complement_ppi_set]:" + str(e) + '\n')
		sys.stderr.write (err_mes)
				
	except IOError, e:
		sys.stderr('cannot open the file [c_complement_ppi_set]' +
				 str(e) + '\n')
	return comp_ppi_list


def check_for_balance(ppi_p, ppi_ni_p=None):
	seqManip = SequenceManipulation(ppi_p=ppi_p)
	seqManip.r_ppi_list_from_f();
	if ppi_ni_p is not None:
		seqManip.ppi_p = ppi_ni_p
		seqManip.r_ppi_list_from_f()
	ppi_list = seqManip.ppi_list
	p_i = {}
	p_ni = {}
	p_both = {}
	for ppi in ppi_list:
		for (p1, p2), i_ni in ppi.items():

			if p1 in p_both:
				if i_ni.startswith('interacting'):
					p_both[p1] = (p_both[p1][0]+1, p_both[p1][1])
				if i_ni.startswith('non-interacting'):
					p_both[p1] = (p_both[p1][0], p_both[p1][1]+1)
			else:
				if i_ni.startswith('interacting'):
					p_both[p1] = (1, 0)
				if i_ni.startswith('non-interacting'):
					p_both[p1] = (0, 1)

			if p2 in p_both:
				if i_ni.startswith('interacting'):
					p_both[p2] = (p_both[p2][0]+1, p_both[p2][1])
				if i_ni.startswith('non-interacting'):
					p_both[p2] = (p_both[p2][0], p_both[p2][1]+1)
			else:
				if i_ni.startswith('interacting'):
					p_both[p2] = (1, 0)
				if i_ni.startswith('non-interacting'):
					p_both[p2] = (0, 1)

			if i_ni.startswith('interacting'):
				if p1 in p_i:
					p_i[p1] += 1
				else:
					p_i[p1] = 1
				if p2 in p_i:
					p_i[p2] += 1
				else:
					p_i[p2] = 1

			if i_ni.startswith('non-interacting'):
				if p1 in p_ni:
					p_ni[p1] += 1
				else:
					p_ni[p1] = 1
				if p2 in p_ni:
					p_ni[p2] += 1
				else:
					p_ni[p2] = 1
	return p_i, p_ni, p_both
				

def c_rand_sets(p_seq_p, p_sec_p, all_yeast_p, ppi_p, comp_ppi_p, b=True):
	seqManip = secStructManipulation(
				p_seq_p=p_seq_p,
				p_sec_p=p_sec_p,
			)
	seqManip.r_ps_dict_from_f()
	seqManip.r_psec_dict_from_f()
	p_with_sec_list = []

	for p, sec in seqManip.psec_dict.items():
		if sec != 'NotFound\r\n':
			p_with_sec_list.append(p)

	# NOTE since max_p=len(p_with_sec_list) it generates all of ppi
	rand_p_list = f_rand_p_list(p_with_sec_list, len(p_with_sec_list))
	ppi_list = c_new_ppi_set(all_yeast_p, rand_p_list, ppi_p)
	# Generate complement of random test sets
	if not b:
		ppi_comp_list = c_complement_ppi_set(p_with_sec_list, ppi_p=ppi_p,
								ppi_comp_p=comp_ppi_p)
	else:
		ppi_comp_list = c_balanced_complement_ppi_set(
						p_with_sec_list,
						ppi_p=ppi_p,
						ppi_comp_p=comp_ppi_p)


def p_freq(ppi_l):

	p_freq_d = {}
	for ppi in ppi_l:
		for (p1, p2), i_ni in ppi.items():
			if p1 not in p_freq_d:
				p_freq_d[p1] = 1
			else:
				p_freq_d[p1] += 1

			if p2 not in p_freq_d:
				p_freq_d[p2] = 1
			else:
				p_freq_d[p2] += 1

	return p_freq_d.items()
	

###############################################################
###############################################################
#To for taking out the largest proteins

class WorkerStopToken:  # used to notify the worker to stop
		pass

class DatasetWorker(Thread):
	def __init__(self,name,job_queue,result_queue):
		Thread.__init__(self)
		self.name = name
		self.job_queue = job_queue
		self.result_queue = result_queue
	def run(self):
		while True:
			p_l = self.job_queue.get()
			if p_l is WorkerStopToken:
				###print 'closing ' + self.name
				self.job_queue.put(p_l)
				# print('worker {0} stop.'.format(self.name))
				break
			p_names = ' '.join(p_l)
			try:
				print self.name + ' Running ' + p_names
				success = self.run_one(p_names)
				if success is None: raise RuntimeError("Was not successful")
			except:
				# we failed, let others do that and we just quit
				traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
										  sys.exc_info()[2])
				self.job_queue.put(p_l)
				print('worker {0} quit.'.format(self.name))
				break
			else:
				self.result_queue.put((self.name, p_l[-1]))


class SSHDatasetWorker(DatasetWorker):
	def __init__(self,name,job_queue,result_queue,host, ppi_p):
		DatasetWorker.__init__(self,name,job_queue,result_queue)
		self.host = host
		self.cwd = os.getcwd()
		self.ppi_p = ppi_p
		self.py_exe = 'python'
		self.py_code = 'rm_p_from_file.py'
	def run_one(self, p_names):
		py_path = "export PYTHONPATH=/home/ba2g09/workspace/summer_internship;"
		cmd_str = 'ssh -x {0} "' + py_path + 'cd {1}; {2} {3} -i {4} {5}"'
		cmdline = cmd_str.format(self.host, self.cwd, self.py_exe, self.py_code,
						self.ppi_p , p_names)
		print cmdline
		result = Popen(cmdline,shell=True,stdout=PIPE).stdout
		for line in result.readlines():
			if str(line).find("Finish changing the format to libsvm") != -1:
				return True


class LocalDatasetWorker(DatasetWorker):
	def __init__(self,name,job_queue,result_queue, ppi_p):
		DatasetWorker.__init__(self,name,job_queue,result_queue)
		self.ppi_p = ppi_p
		self.py_exe = 'python'
		self.py_code = 'rm_p_from_file.py'
	def run_one(self, p_names):
		cmd_str = '{0} {1} -i {2} {3}'
		cmdline = cmd_str.format(self.py_exe, self.py_code, self.ppi_p, 
								p_names)
		print cmdline
		result = Popen(cmdline,shell=True,stdout=PIPE).stdout
		for line in result.readlines():
			if str(line).find("Finish changing the format to libsvm") != -1:
				return True


def rm_p_from_ppi_l(ppi_l, p):

	ret_ppi_l = []
	for ppi in ppi_l:
		for (p1, p2), i_ni in ppi.items():
			pass
		if p1 == p or p2 == p:
			continue
		ret_ppi_l.append(ppi)
	return ret_ppi_l


def rm_p_from_f_write(ppi_p, p_l):

	p_seq_p = os.path.join(
				os.path.abspath('../data'),
				'p_seq_dict_yeast_154828_formatted.txt'
			)
	p_sec_p = os.path.join(
				os.path.abspath('../data'),
				'yeast_p_sec_struct_dict__formatted.txt'
			)
	seqManip = SequenceManipulation(
					p_seq_p=p_seq_p,
					p_sec_p=p_sec_p,
					ppi_p=ppi_p,
			   )
	seqManip.r_ps_dict_from_f()
	seqManip.r_ppi_list_from_f();
	ppi_l = seqManip.ppi_list

	tmp_ppi_l = list(ppi_l)
	for p in p_l:
		tmp_ppi_l = rm_p_from_ppi_l(tmp_ppi_l, p)

	seqManip = SequenceManipulation(
					p_seq_p=p_seq_p,
					p_sec_p=p_sec_p,
			   )
	seqManip.r_ps_dict_from_f()
	seqManip.ppi_list = tmp_ppi_l	
	seqManip.f_ssi_list();
	seqManip.f_cci_sub_s_with_c()
	seqManip.sub_c_with_f()
	seqManip.normalize()
	seqManip.libsvm_format(libsvm_p=p_l[-1]+'.txt') #output is protein name
	c_tar_f(p_l[-1]+'.txt', rm_orig=True)


def sort_l(p_freq_l):
	ret_freq_l = []
	for i, (p, freq) in enumerate(p_freq_l):
		if ret_freq_l == []:
			ret_freq_l.append({p:freq})
		else:
			for ret_i, p_freq in enumerate(ret_freq_l):
				for ret_p, ret_freq in p_freq.items():
					 pass
				if ret_freq > freq:
					if ret_i + 1 == len(ret_freq_l):
						ret_freq_l.insert(ret_i, ({p:freq}))
						break
					continue
				else:
					ret_freq_l.insert(ret_i, ({p:freq}))
					break
	ret_freq_l.reverse()
	return ret_freq_l


#NOTE Run the following to create the ppi without higher ones
def mt_rm_large_ps(ppi_p, num_rm=10):

	global ssh_workers, nr_local_worker
	ret_ppi_lists_d = {}
	p_seq_p = os.path.join(
				os.path.abspath('../data'),
				'p_seq_dict_yeast_154828_formatted.txt'
			)
	p_sec_p = os.path.join(
				os.path.abspath('../data'),
				'yeast_p_sec_struct_dict__formatted.txt'
			)
	seqManip = SequenceManipulation(
					p_seq_p=p_seq_p,
					p_sec_p=p_sec_p,
					ppi_p=ppi_p,
			   )
	seqManip.r_ps_dict_from_f()
	seqManip.r_ppi_list_from_f();
	ppi_l = seqManip.ppi_list
	p_freq_l =  sort_l(p_freq(ppi_l))

	# put jobs in queue
	total_jobs = 0
	job_queue = Queue.Queue(0)
	result_queue = Queue.Queue(0)
	top_p_freq = p_freq_l[-num_rm:]
	jobs = []

	p_removed = []
	for tmp_p_freq in top_p_freq:
		for p, freq in tmp_p_freq.items():
			pass
		total_jobs += 1
		p_removed.append(p)
		#jobs.append(p)
		jobs.append(list(p_removed))
		#job_queue.put(p)
		job_queue.put(list(p_removed))
		print p

	#Connect to hosts first
	hostnames = set(ssh_workers) #removing the extras
	hostnames = list(hostnames)

	password = getpass.getpass('Password:')
	if password != '':
		ssh_connector = ssh_connection.SSHConnection(hostnames_l=hostnames,
						password=password)
		# make connection to ssh workers first
		ssh_connector.conn_to_clients_wait()
		ssh_workers = ssh_connector.conn_l
		random.shuffle(ssh_workers)
		# fire ssh workers
		if ssh_workers:
			for host in ssh_workers:
				SSHDatasetWorker(host,job_queue,result_queue,host,ppi_p).start()

	for num in range(nr_local_worker):
		LocalDatasetWorker(str(num), job_queue, result_queue, ppi_p).start()

	done_jobs = {}
	#result_f = open('_'.join(p_removed)+'.txt', 'w')
	result_p = str(len(p_removed)) + '_results_cur.out' 
	result_f = open(result_p, 'w')

	for p  in jobs:
		#while p not in done_jobs:
		print '^'*50
		print 'Came for', p
		#NOTE that get waites untile the queue has an item in it
		(worker, p) = result_queue.get()
		print 'Got', p
		print '_'*50
		done_jobs[p] = 1
		#cnt_p = count_lines(p+'.txt') #Num of proteins
		cnt_p = count_lines(p+'.txt.tar.gz') #Num of proteins
		result_f.write('{0} {1} {2} \n'.format(worker, p, cnt_p))
		result_f.flush()

		nr_done_jobs = len(done_jobs)
		perc = nr_done_jobs * 100.0 / total_jobs
		perc = round(perc, 3)
		state = ("["+ str(nr_done_jobs) + " out of " + str(total_jobs) +
					" " + str(perc)+"%]")
		result = '[{0}] {1} {2}'.format(worker, p, cnt_p)
		print(result + "|" + state)

	job_queue.put(WorkerStopToken)
	if password != '':
			ssh_connector.close_clients()

	return ret_ppi_lists_d


def count_lines(p=''):
	if p.endswith('.tar.gz'):
		tar = tarfile.open(p, 'r:gz')
		f = tar.extractfile(p[:-7])
	else:
		f = open(p, 'r')
	count = 0
	for l in f:
		count += 1
	return count
		

if __name__ == '__main__':

	"""
	#########################################################################
	ppi_p = os.path.join(os.path.abspath('.'), 'yeastP1.txt')
	ppi_p_ni = os.path.join(os.path.abspath('.'), 'yeastN_random1.txt')
	p_i, p_ni ,p_both = check_for_balance(ppi_p, ppi_p_ni)

	eq_n = 0
	neq_n = 0
	for p, (i_n, ni_n) in p_both.items():
		if i_n == ni_n-1:
			eq_n += 1
		elif i_n == ni_n+1:
			eq_n += 1
		elif i_n == ni_n:
			eq_n += 1
		else:
			neq_n += 1
	print eq_n, neq_n, 'random eq'

	p_exists = 0
	p_nexists = 0
	for p, ni_n in p_ni.items():
		if p in p_i:
			p_exists += 1
		else:
			p_nexists += 1
	print p_exists, p_nexists, 'random exists'
	#########################################################################
	ppi_p = os.path.join(os.path.abspath('.'), 'yeastP1.txt')
	ppi_p_ni = os.path.join(os.path.abspath('.'), 'yeastN_balance1.txt')
	bp_i, bp_ni ,bp_both = check_for_balance(ppi_p, ppi_p_ni)

	eq_n = 0
	neq_n = 0
	for p, (i_n, ni_n) in bp_both.items():
		if i_n == ni_n-1:
			eq_n += 1
		elif i_n == ni_n+1:
			eq_n += 1
		elif i_n == ni_n:
			eq_n += 1
		else:
			neq_n += 1
	print eq_n, neq_n, 'balance eq'

	p_exists = 0
	p_nexists = 0
	for p, ni_n in bp_ni.items():
		if p in bp_i:
			p_exists += 1
		else:
			p_nexists += 1
	print p_exists, p_nexists, 'balance exists'
	#########################################################################
	ppi_p = os.path.join(os.path.abspath('.'), 'tmp_set.txt')
	ppi_p_ni = os.path.join(os.path.abspath('.'), 'tmp_comp_set.txt')
	tp_i, tp_ni ,tp_both = check_for_balance(ppi_p, ppi_p_ni)

	eq_n = 0
	neq_n = 0
	for p, (i_n, ni_n) in tp_both.items():
		if i_n == ni_n-1:
			eq_n += 1
		elif i_n == ni_n+1:
			eq_n += 1
		elif i_n == ni_n:
			eq_n += 1
		else:
			neq_n += 1
	print eq_n, neq_n, 'comp eq'

	p_exists = 0
	p_nexists = 0
	for p, ni_n in tp_ni.items():
		if p in tp_i:
			p_exists += 1
		else:
			p_nexists += 1
	print  p_exists, p_nexists, 'comp exists'
	#########################################################################
	"""
	"""
	##########################################################################
	####################### Generate random test sets ########################
	##########################################################################
	p_seq_p = os.path.join(
				os.path.abspath('../data'),
				'p_seq_dict_yeast_154828_formatted.txt'
			)
	p_sec_p = os.path.join(
				os.path.abspath('../data'),
				'yeast_p_sec_struct_dict__formatted.txt'
			)
	all_yeast_p = os.path.join(
			os.path.abspath('../data/'), 
			'yeast_154828.txt'
		)
	tmp_ppi_p = os.path.join(
				os.path.abspath('.'),
				'test_tmp_set.txt'
			  )
	tmp_comp_ppi_p = os.path.join(
					os.path.abspath('.'),
					'test_tmp_comp_set.txt'
				  )

	c_rand_sets(p_seq_p, p_sec_p, all_yeast_p, tmp_ppi_p, tmp_comp_ppi_p)
	##########################################################################
	####################### Generate random test sets ########################
	##########################################################################
	ppi_p = os.path.join(os.path.abspath('.'), 'test_tmp_set.txt')
	ppi_p_ni = os.path.join(os.path.abspath('.'), 'test_tmp_comp_set.txt')
	tp_i, tp_ni ,tp_both = check_for_balance(ppi_p, ppi_p_ni)

	eq_n = 0
	neq_n = 0
	for p, (i_n, ni_n) in tp_both.items():
		if i_n == ni_n-1:
			eq_n += 1
		elif i_n == ni_n+1:
			eq_n += 1
		elif i_n == ni_n:
			eq_n += 1
		else:
			neq_n += 1
	print eq_n, neq_n, 'comp eq'
	"""
	
	##########################################################################
	#############Create ppi without the high interacting proteins#############
	##########################################################################
	mt_rm_large_ps('tmp/y_p1_r1.txt', 25)
