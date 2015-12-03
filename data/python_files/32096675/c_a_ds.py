import sys
import os
import math
import re
import traceback
import pprint
from multiprocessing import Pool

from c_hf import read_prots_fams



class AminoSeqManip:
	
	def __init__(self, **kwargs):
		self.amino_p = kwargs.get('amino_p', None)
		self.amino_classes = {}
		self.pattern = ''
		self._cons_amino_class_pattern()
		self.con_tri = {}

		self.pc_dict = {} # A dictionary of proteins to their class group
		self._reset_con_tri()


		self.s_list = []
		self.c_list = []
		self.f_list = []
		self.n_list = []
		#These are the paths which are used in the project
		self.p_p = kwargs.get('p_p', None)
		self.s_p = kwargs.get('s_p', None)
		self.c_p = kwargs.get('c_p', None)
		self.f_p = kwargs.get('f_p', None)
		self.n_p = kwargs.get('n_p', None)
		self.libsvm_p = kwargs.get('libsvm_p', None)
		self.arff_p = kwargs.get('arff_p', None)

	def _cons_amino_class_pattern(self):
		"""Constructs the pattern used in _find_freq and the 
			self.amino_classes from a given file
		"""
		try:
			a_cs = []
			a_c_d = {}
			a_c_p = ''
			p = re.compile('[\r\n,\n]')
			f = open(self.amino_p, 'r')
			for l in f:
				l = p.sub ('', l)
				a_cs.append(l)
				tmp_a = [c for c in l]
				a_c_d[l[0]] = '[' + ' | '.join(tmp_a) + ']'
			a_c_p = '[' + ' | '.join(list(a_c_d.keys())) + ']'

			self.amino_classes = a_c_d
			self.pattern = a_c_p
		except IOError:
			traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
										  sys.exc_info()[2])

	def _reset_con_tri(self):
		"""resets all the values of the con_tri dictionary to zeros"""
		l = list(self.amino_classes.items())
		for i in l:
			for j in l:
				for v in l:
					self.con_tri[i[0] + j[0] + v[0]] = 0


	def _sub_let_with_c(self,string):
		"""  Replaces the amino acids in the string given to it to the 7
			classes of amino acids
		"""
		# Note that subn function returns a tuple and the first element is
		# the substituded string
		string = [string]
		for k,v in self.amino_classes.items():
			tmp_p = re.compile(v, re.I) # Ignore Case
			string = tmp_p.subn(k,string[0])
		return string[0]


	def r_p_list_from_f(self, sep=' ', **kwargs):
		"""Creates a dictionary of proteins and their classes
		
			Arguments:
			sep -- The separator used in the file to separate the lines

			Keyword Arguments:
			prot_p -- The path to the file which contains the proteins
					or it uses the one from when init the object

		
		"""
		prot_p = kwargs.get('prot_p',self.p_p)
		if prot_p is None:
			err_mes = "The path to ppi  is wrong.[r_ppi_list_from_f]\n"
			sys.stderr.write (err_mes)
			return 0
		try:
			prot_f = open(prot_p, 'r')
			p = re.compile('[\r\n,\n]')
			for line in prot_f:
				line = p.sub ('', line)
				b_line = line.split(' ')
				if len(b_line) != 2:
					continue
				b_line = [a for a in b_line if a != '']
				self.s_list.append( {b_line[0]:b_line[1]} )
		except IOError as e:
			#sys.stderr('cannot open the file' + str(e) + '\n')
			traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
										  sys.exc_info()[2])
		return 1
	

	def f_c_sub_s_with_c(self, sep=' ', **kwargs):
		"""  Substitues all the letters in a given file or ssi list with 
			the amino acid classes, and puts them in the c list in the
			same order.

			Keyword Arguments:
			s_p -- If specified, it uses this file instead of s_list
			c_p -- If specified, the substitued classes are written here

		"""
		s_p = kwargs.get('s_p', self.s_p)
		c_p = kwargs.get('c_p', self.c_p)
		s_f = None
		c_f = None
		try:
			if self.s_list != []:
				s_s = self.s_list
			else:
				if s_p is None:
					err_mes = ("The path to s_p is wrong." + 
							"[f_c_sub_s_with_c]\n")
					sys.stderr.write (err_mes)
					return 0
				s_f = open(s_p, 'r')
				s_s = s_f
			if c_p is not None:
				c_f = open(c_p,'w') 

			print("Start filling c list")
			for seq in s_s:
				if type(seq) == dict:
					for s, val in seq.items():
						seq = s + ' ' + val + '\r\n'
				b_line = re.split(sep, seq)
				c = self._sub_let_with_c(b_line[0])		
				val = b_line[1]
				c_line = c + ' ' + val 
				if c_f is not None:
					c_f.write(c_line)
				self.c_list.append({c: val})	
			if c_f is not None:
				c_f.close()
			if s_f is not None:
				s_f.close()
			print("Finished filling c list")
		except IOError as e:
			print('cannot open the file',e)

	def sub_c_with_f(self, sep=' ', **kwargs):
		"""  Substitutes amino classes with frequencies and in the sorted 
			form from 111 to 777

			Arguments:
			sep -- the separator used in the file
			
			Keyword Arguments:
			f_p -- is the path to write the output to	
			c_p -- is the path to amino acids class file to read 

		"""
		c_p = kwargs.get('c_p', self.c_p)
		f_p = kwargs.get('f_p', self.f_p)
		c_f = None
		freq_f = None


		try:
			if self.c_list != []:
				c_s = self.c_list	
			else:
				if c_p is None:
					err_mes = "The path to c is wrong.[sub_c_with_f]\n"
					sys.stderr.write (err_mes)
					return 0
				c_f = open(c_p, 'r')
				c_s = c_f

			if f_p is not None:
				freq_f = open(f_p,'w')	
			print('Start substituding classes with frequencies')
			for line_i, c in enumerate(c_s):
				if type(c) == dict:
					for c, val in c.items():
						c = c + ' ' + val
				b_line = re.split(sep, c)
				self._reset_con_tri()
				f = self._find_freq(c_text=b_line[0])
				sort_f = self._sort_conjoint_triad(f)	

				# Adding the results of interacting or non-interacting to 
				# the last element 
				sort_f = [str(a) for a in sort_f]
				sort_f = ' '.join(sort_f)
				if freq_f is not None:
					freq_f.write(sort_f + ' ' +  b_line[1])
				self.f_list.append( {sort_f : b_line[1]} )
			print('Finished substituding classes with frequencies')
			if freq_f is not None:
				freq_f.close()
			if c_f is not None:
				c_f.close()
		except IOError as e:
			#sys.stderr('cannot open the file' + str(e) + '\n')
			traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
										  sys.exc_info()[2])
		return 1

	def _find_freq(self, c_text):
		"""  Returns an array of conjoint_triad which basically shows the 
			number of frequencies 
		"""
		p = (r'(?=(' + self.pattern + '{3}))')
		matches = re.finditer(p, c_text)
		results = [match.group(1)  for match in matches]
		self._reset_con_tri()
		for freq in results:
			freq = str(freq)
			self.con_tri[freq] = self.con_tri[freq] + 1
		return self.con_tri

	def _sort_conjoint_triad(self,con_tri):
		keys = list(con_tri.keys())
		keys.sort()
		return list(map(con_tri.get, keys))


	def normalize(self, sep= ' ', **kwargs):
		""" This function normalizes the output of frequencies so they would be 
			between 0 nand 1

			Arguments:
			sep -- the separator used in the file
			
			Keyword Arguments:
			f_p -- is the path frequencies to read
			n_p -- the out path to normalized frequencies

		"""
		f_p = kwargs.get('f_p', self.f_p)
		n_p = kwargs.get('n_p', self.n_p)
		freq_f = None
		n_f = None
		try:
			if n_p is not None:
				n_f = open(n_p, 'w')

			if self.f_list != []:
				f_s = self.f_list
			else:
				if f_p is None:
					err_mes = "The path to ffi is wrong.[normalize]\n"
					sys.stderr.write (err_mes)
					return 0
				freq_f = open(f_p, 'r')
				f_s = freq_f
			print('\nstart normalization')
			for f in f_s:
				if type(f) == dict:
					for tmp_f1, val in f.items():
						ffi = tmp_f1 + ' ' + val
				f = ffi.split(' ')

				f = [float(x) for x in f]
				max_f = max(f[:-1])
				min_f = min(f[:-1])

				norm_f = [(x - min_f) / (max_f) for x in f[:-1]]

				norm_f.append(f[-1])
				str_norm_f = [str(x) for x in norm_f]
				n = str_norm_f[:-1]
				val = str_norm_f[-1]
				n = ' '.join(n)
				self.n_list.append({n : val})
				if n_f is not None:
					n_f.write(' '.join(str_norm_f) + '\n')
			print('finished normalization\n')
			if n_f is not None:
				n_f.close()
		except IOError as e:
			#sys.stderr('cannot open the file' + str(e) + '\n')
			traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
										  sys.exc_info()[2])
		return 1

	def libsvm_format(self, **kwargs):
		"""formats a file to an acceptable format for libsvm
		
			Keywords Arguments:
			n_p -- the path from which the ffis are read from 
			libsvm_p -- the path to write the output to

		"""
		n_p = kwargs.get('n_p', self.n_p)
		libsvm_p = kwargs.get('libsvm_p', self.libsvm_p)
		if libsvm_p is None:
			err_mes = "The path to libsvm is wrong.[libsvm_format]\n"
			sys.stderr.write (err_mes)
			return 0
		n_f = None
		try:
			if n_p is not None:
				n_f = open(n_p,'r')
				n_s = n_f
			else:
				if self.n_list == []:
					raise Exception
				n_s = self.n_list
				
			libsvm_f = open(libsvm_p,'w')
			print("Start changing the format to libsvm")
			for n in n_s:
				#TODO Test to see if it works for secondary and non secondary
				if type(n) is dict:
					for tmp_n, v in n.items():
						n = tmp_n + " " + v
				freqs = n.split(" ")
				#l_formatted = freqs[-1]
				i_ni = float(freqs[-1])
				l_formatted =  '+1' if i_ni == 1 else '-1'
				#l_formatted = l_formatted[0]
				for label_num, freq in enumerate(freqs[0:-1]):
					label_num += 1
					if l_formatted != '':
						l_formatted += " "+str(label_num)+":"+str(freq)
					else :
						l_formatted = str(label_num)+":"+str(freq)
				l_formatted += "\n"
				libsvm_f.write(l_formatted)

			print("Finish changing the format to libsvm")
			if n_f is not None:
				n_f.close()
			libsvm_f.close() 
		except Exception as e:
			#sys.stderr(str(e)+" [libsvm_format]\n")
			traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
										  sys.exc_info()[2])

def fisher_scop(rb_p, dir_p):
	f = open (rb_p, "r")
	f_arr = [l.split("\t") for l in f]
	f_arr = f_arr[2:]
	train_pos, train_neg, test_pos, test_neg, sets_p = [], [], [], [], []
	base_out_p = '/tmp/fisher/' # The path to where sets have been set
	base_enc_out_p = '/tmp/fisher_out/' # Prepare directories for encoded data
	if not os.path.exists (base_out_p):
		os.mkdir (base_out_p)
	if not os.path.exists (base_enc_out_p):
		os.mkdir (base_enc_out_p)
	for l in f_arr:
		train_pos.append (l[4])
		train_neg.append (l[5])
		test_pos.append (l[6])
		test_neg.append (l[7])
		sets_p.append (l[1])
		if not os.path.exists (base_out_p+l[1]):
			os.mkdir (base_out_p+l[1])
		if not os.path.exists (base_enc_out_p+l[1]):
			os.mkdir (base_enc_out_p+l[1])
	for i in range(len(train_pos)):
		print('{0} / {1}'.format(i+1, len(train_pos)))
		train_arr, test_arr= [], []
		# train_pos_f = open (dir_p+train_pos[i], 'r')
		# train_neg_f = open (dir_p+train_neg[i], 'r')
		# test_pos_f = open (dir_p+test_pos[i], 'r')
		# test_neg_f = open (dir_p+test_neg[i], 'r')
		train_pos_f, fam = read_prots_fams (dir_p+train_pos[i])
		train_neg_f, fam = read_prots_fams (dir_p+train_neg[i])
		test_pos_f, fam = read_prots_fams (dir_p+test_pos[i])
		test_neg_f, fam = read_prots_fams (dir_p+test_neg[i])
		[train_arr.append (l+' 1\n') for l in train_pos_f]
		[train_arr.append (l+' -1\n') for l in train_neg_f]
		[test_arr.append (l+' 1\n') for l in test_pos_f]
		[test_arr.append (l+' -1\n') for l in test_neg_f]
		name = train_pos[i].split('/')[-1].split('.')
		name = '.'.join(name[:-2])
		train_out_f = open(base_out_p+sets_p[i]+'/'+name+'.train', 'w')
		test_out_f = open(base_out_p+sets_p[i]+'/'+name+'.test', 'w')
		for l in train_arr:
			train_out_f.write(l)
		for l in test_arr:
			test_out_f.write(l)
		train_out_f.close()
		test_out_f.close()


def prep_fisher_datasets ():
	base_p = '/tmp/fisher/'
	base_out_p = '/tmp/fisher_out/'
	dirs = os.listdir (base_p)
	full_p = []
	p_p_list = []
	libsvm_p_list = []
	for path in dirs:
		pros = os.listdir (base_p+path)
		tmp_pros = ['.'.join (i.split('.')[:-1]) for i in pros]
		tmp_pros = list(set(tmp_pros))
		for s in tmp_pros:
			p_p_list.append (base_p+path+'/'+s)
			libsvm_p_list.append (base_out_p+path+'/'+s)
	amino_p_l = os.listdir('../data/alphabets')
	amino_p_l = [a for a in amino_p_l if a.startswith('lz-bl')]
	args = []
	for i, p in enumerate(p_p_list):
		out_p = libsvm_p_list[i]
		for a in amino_p_l:
			amino_p = os.path.join(
						os.path.abspath('../data/alphabets'),
						a
					)
			a = '_'.join (a.split('.')[:2])
			train_out = out_p + '.' + a + '.' + 'train'
			test_out = out_p + '.' + a + '.' + 'test'
			args.append ((p+'.train', p+'.test', amino_p, train_out, test_out))
	return args


def encode_prots(args):
	p_p_train = args[0]
	libsvm_p_train = args[3]
	amino_p = args[2]
	p_p_test = args[1]
	libsvm_p_test = args[4]
	seqManip = AminoSeqManip(
			amino_p=amino_p,
			p_p=p_p_train,
			)
	seqManip.r_p_list_from_f()
	seqManip.f_c_sub_s_with_c()
	seqManip.sub_c_with_f()
	seqManip.normalize()
	seqManip.libsvm_format(libsvm_p = libsvm_p_train)
	seqManip = AminoSeqManip(
			amino_p=amino_p,
			p_p= p_p_test,
			)
	seqManip.r_p_list_from_f()
	seqManip.f_c_sub_s_with_c()
	seqManip.sub_c_with_f()
	seqManip.normalize()
	seqManip.libsvm_format(libsvm_p = libsvm_p_test)
	print(libsvm_p_train)
	return libsvm_p_train


if __name__ == '__main__':
	fisher_scop('../data/fisher-scop-data/scop-experiment.rdb', '../data/fisher-scop-data/')
	args = prep_fisher_datasets()
	pool = Pool(processes=21)              # start 4 worker processes
	pool.map(encode_prots, args)          # prints "[0, 1, 4,..., 81]"
