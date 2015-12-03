import sys
import os
import re
import traceback
import argparse
from multiprocessing import Pool


#from p_code_input_output.c_data_set import SequenceManipulation, c_tar_f 
from c_data_set import SequenceManipulation, c_tar_f 


class AminoSeqManip(SequenceManipulation):
	
	def __init__(self, **kwargs):
		super(AminoSeqManip, self).__init__(**kwargs)
		self.amino_p = kwargs.get('amino_p', None)
		self.amino_classes = {}
		self.pattern = ''
		self._cons_amino_class_pattern()
		self.con_tri = {}
		self._reset_con_tri()
		self.pc_dict = {} # A dictionary of proteins to their class group

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
			a_c_p = '[' + ' | '.join(a_c_d.keys()) + ']'

			self.amino_classes = a_c_d
			self.pattern = a_c_p
		except IOError:
			traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
										  sys.exc_info()[2])

	def _reset_con_tri(self):
		"""resets all the values of the con_tri dictionary to zeros"""
		l = self.amino_classes.items()
		for i in l:
			for j in l:
				for v in l:
					self.con_tri[i[0] + j[0] + v[0]] = 0

	def r_ps_dict_from_f(self, **kwargs):
		"""Creates sequences for the protein names from a given file.
			It has been overriden so calling the _f_pc_dict to 
			fill the pc_dict in this class
		
			Arguments:
			sep -- the separator used in the file
			
			Keyword Arguments:
			p_seq_p -- the path to the file which contains the protein 
					    names or use the one when init the object
		
		"""
		super(AminoSeqManip, self).r_ps_dict_from_f(**kwargs)
		self._f_pc_dict()

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
		keys = con_tri.keys()
		keys.sort()
		return map(con_tri.get, keys)

	def _f_pc_dict(self):
		""" This function fills the pc_dict which is basically a dict that
			has the mapping from protein to its classes (instead of the 
			sequence)
			It should be called after r_ps_dict_from_f

		"""
		if self.ps_dict == {}:
			err_mes = "ps_dict is empty it should be filled.[_f_pc_dict]\n"
			sys.stderr.write (err_mes)
			return 0
		for p, seq in self.ps_dict.items():
			# change the sequence to the class
			self.pc_dict[p] = self._sub_let_with_c(seq)

	def normalize(self, sep= ' ', **kwargs):
		""" This function normalizes the output of frequencies so they would be 
		    between 0 nand 1

			Arguments:
			sep -- the separator used in the file
			
			Keyword Arguments:
			ffi_p -- is the path frequencies to read
			nni_p -- the out path to normalized frequencies

		"""
		ffi_p = kwargs.get('ffi_p', self.ffi_p)
		nni_p = kwargs.get('nni_p', self.nni_p)
		ffi_f = None
		nni_f = None
		try:
			if nni_p is not None:
				nni_f = open(nni_p, 'w')

			if self.ffi_list != []:
				ffi_s = self.ffi_list
			else:
				if ffi_p is None:
					err_mes = "The path to ffi is wrong.[normalize]\n"
					sys.stderr.write (err_mes)
					return 0
				ffi_f = open(ffi_p, 'r')
				ffi_s = ffi_f

			print '\nstart normalization'
			# TODO FOR SOME RESOAN I WAS NOT NORMALIZING IT
			#self.nni_list = ffi_s 
			for ffi in ffi_s:
				if type(ffi) == dict:
					for (f1, f2), val in ffi.items():
						ffi = f1 + ' ' + f2 # + ' ' + val # No value in norm
				ffi = ffi.split(' ')

				ffi = map(lambda x: float(x), ffi)
				max_f = max(ffi)
				min_f = min(ffi)

				if max_f != 0:
					norm_ffi = map(lambda x: (x - min_f) / (max_f), ffi)
				else:
					norm_ffi = ffi

				#norm_ffi.append(val)
				str_norm_ffi = map(lambda x : str(x), norm_ffi)
				n_len = len(norm_ffi) / 2
				n1 = str_norm_ffi[:n_len]	
				n2 = str_norm_ffi[n_len:]	
				# val = str_norm_ffi[-1] # Val is known from befor
				n1 = ' '.join(n1)
				n2 = ' '.join(n2)
				self.nni_list.append({(n1, n2) : val})
				if nni_f is not None:
					nni_f.write(' '.join(str_norm_ffi) + ' ' + val)
			print 'finished normalization\n'
			if nni_f is not None:
				nni_f.close()

		except IOError,e:
			#sys.stderr('cannot open the file' + str(e) + '\n')
			traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
										  sys.exc_info()[2])
		return 1


def c_ds(args):
	a = args[0]
	ppi_p =  args[1]
	out_d = args[2]
	name = args[3]
	p_seq_p = os.path.join(
				os.path.abspath('../data'),
				'p_seq_dict_yeast_154828_formatted.txt'
			)
	p_sec_p = os.path.join(
				os.path.abspath('../data'),
				'yeast_p_sec_struct_dict__formatted.txt'
			)
	#name = ('yeast','p1_r1')
	amino_p = os.path.join(
				os.path.abspath('../data/alphabets'),
				a
			)
	a = '_'.join(a.split('.')[:2])
	print amino_p
	libsvm_p = os.path.join(
				os.path.abspath('.'),
				'_'.join(name) + '_' + a + '_libsvm_iff.txt'
			)
	if not os.path.exists(out_d):
		os.mkdir(out_d)
	libsvm_p = out_d + '/' + '_'.join(name) + '_'+a+'_libsvm_iff.txt'
	seqManip = AminoSeqManip(
			p_seq_p=p_seq_p,
			p_sec_p=p_sec_p,
			amino_p=amino_p,
			ppi_p=ppi_p,
			#ssi_p=ssi_p,
			#cci_p=cci_p,
			#ffi_p=ffi_p,
			#nni_p=nni_p,
			#libsvm_p = libsvm_p,
			)
	seqManip.r_ps_dict_from_f()
	seqManip.r_ppi_list_from_f();
	seqManip.f_ssi_list();
	seqManip.f_cci_sub_s_with_c()
	seqManip.sub_c_with_f()
	seqManip.normalize()
	seqManip.libsvm_format(libsvm_p = libsvm_p)
	#libsvm_p = libsvm_p.split('/')[-1] #To prevent extra folders
	#c_tar_f(libsvm_p, rm_orig=True)
	print len(seqManip.ps_dict)
	print len(seqManip.ppi_list)
	print len(seqManip.ssi_list)
	print len(seqManip.cci_list)
	print len(seqManip.ffi_list)



if __name__ == '__main__':
	parser = argparse.ArgumentParser(
		description='Creates the amino acid groups.')
	parser.add_argument('in_path', metavar='in_path', type=str,
					help='The input file which includes interacting proteins')
	parser.add_argument('out_dir', metavar='out_dir', type=str,
					help='The output directory -- will be created')
	parser.add_argument('output', metavar='output', type=str, nargs=1,
					help='The output directory -- will be created')
	parser.add_argument('--alphabet', metavar='alph', type=str, default=None,
					help='Give the name of the schema such as ab.')
	parser.add_argument('--notalph', metavar='not alph', type=str,
					default=None,
					help='Give the name of the schema such as ab.')
	parser.add_argument('--asize', metavar='alph_size', type=str, default=None,
					help='Give the size of the schema such as 7.')
	args = parser.parse_args()
	out_d = args.out_dir # 'encoded_dir'
	in_p =  args.in_path # '../data/30k.txt'
	out_name = (args.output) # ('yeast','30k')
	amino_p_l = os.listdir('../data/alphabets')
	if args.alphabet is not None:
		amino_p_l = [l for l in amino_p_l if l.startswith(args.alphabet)]
	if args.asize is not None:
		amino_p_l = [l for l in amino_p_l if l.endswith('.'+args.asize+'.txt')]
	if args.notalph is not None:
		amino_p_l = [l for l in amino_p_l if not 
			l.startswith(args.notalph)]
	print amino_p_l
	if not os.path.exists(out_d):
		os.mkdir(out_d)
	c_ds_args = [(l, in_p, out_d, out_name) for l in amino_p_l]
	pool = Pool(4)
	pool.map(c_ds, c_ds_args)
