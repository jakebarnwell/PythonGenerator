import re
import os
import copy
import traceback
import time

import numpy


from p_code_input_output.c_secondary_data_set import secStructManipulation
from p_code_input_output.c_a_ds import AminoSeqManip

def r_binding_sites(binding_sites_p):
	""" Reads the binding sites from a file given, and returns
		an array of binding sites in the format of 
		{p1_name: (start_index, end_index)}
		
		Arguments:
			binding_sites_p -- Path to the file which contains binding sites
	"""
	try:
		binding_sites_f = open(binding_sites_p, 'r')
		binding_sites_f.readline() # Throw away useless line
		binding_sites_arr = []
		for line in binding_sites_f:
			regexp = re.compile('[\r\n, \n]')
			line = regexp.sub('', line)
			b_line = line.split('\t')
			# Infor in each line of proteins
			p1, p2 = b_line[0], b_line[1]
			p1_b_start, p1_b_end = int(b_line[2]), int(b_line[3])
			p2_b_start, p2_b_end = int(b_line[4]), int(b_line[5])
			binding_sites_arr.append({(p1, p2): ((p1_b_start, p1_b_end),
												(p2_b_start, p2_b_end))})
		return binding_sites_arr
	except IOError,e:
		#sys.stderr('cannot open the file' + str(e) + '\n')
		traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
													sys.exc_info()[2])


def _get_bs_nbs_if_exist(p_name, dict_chk, p_b_start, p_b_end):
	""" Returns bindig sites and the two non binding sites in protein given
		
		Arguments:
		p_name -- Name of protein given
		dict_chk -- Dict in which checks for protein name
		p_b_start -- Start of binding site in the protein
		p_b_end -- End of binding site in the protein

	"""
	bs, nbs1, nbs2= '', '', ''
	if p_name in dict_chk:
		p_seq = dict_chk[p_name]
		if p_seq.startswith('NotFound'):
			p_b_start, p_b_end = 0, 8
		bs = p_seq[p_b_start:p_b_end]
		nbs1 = p_seq[0:p_b_start]
		nbs2 = p_seq[p_b_end:]
	else:
		raise Exception("Does not Exist in Shen")
	return bs, nbs1, nbs2
		


def c_seq_mainp_bs_nbs(p_seq_p, p_sec_p, amino_p, binding_sites_arr):
	""" Creates and return two AminoSeqManip objects one is the one including
		binding sites, the other contains non binding sites 

		Arguments:
			p_seq_p -- Path to a file of protein to sequences
			p_sec_p -- Path to a file of protein to secondary structures
			amino_p -- Path to the file which contains the amino acids mappings
	"""
	seqManip = AminoSeqManip(
					p_seq_p=p_seq_p,
					p_sec_p=p_sec_p,
					amino_p=amino_p,
				)
	seqManip.r_ps_dict_from_f()
	#seqManip.f_ssi_list();
	#seqManip.f_cci_sub_s_with_c()
	bs_seqManip = copy.deepcopy(seqManip)
	nbs_seqManip = copy.deepcopy(seqManip)
	dict_cmp = seqManip.pc_dict
	for p1_p2_bs in binding_sites_arr:
		((p1,p2), ((p1_s, p1_e), (p2_s, p2_e))) = p1_p2_bs.items()[0]
		p1_b, p1_nb1, p1_nb2 = _get_bs_nbs_if_exist(p1, dict_cmp, p1_s, p1_e)
		p2_b, p2_nb1, p2_nb2 = _get_bs_nbs_if_exist(p2, dict_cmp, p2_s, p2_e)
		bs_seqManip.ssi_list.append( {(p1_b, p2_b): 'interacting'} )
		nbs_seqManip.ssi_list.append( {(p1_nb1, p2_nb1): 'interacting'} )
		nbs_seqManip.ssi_list.append( {(p1_nb2, p2_nb2): 'interacting'} )
	bs_seqManip.f_cci_sub_s_with_c()
	bs_seqManip.sub_c_with_f()
	bs_seqManip.normalize()
	nbs_seqManip.f_cci_sub_s_with_c()
	nbs_seqManip.sub_c_with_f()
	nbs_seqManip.normalize()
	return bs_seqManip, nbs_seqManip


def return_one_arr_from_dict(freq_arr, len_empty):
	empty_arr = map(lambda a: 0, range(len_empty))
	return_arr = []
	for p1_p2 in freq_arr:
		(p1, p2), r = p1_p2.items()[0]
		p1_arr, p2_arr = p1.split(' '), p2.split(' ')
		p1_arr = map(lambda a:float(a), p1_arr)
		p2_arr = map(lambda a:float(a), p2_arr)
		if p1_arr != empty_arr:
			return_arr.append(p1_arr)
		if p2_arr != empty_arr:
			return_arr.append(p2_arr)
	return return_arr


def dist_two_p(p1, p2):
	""" Returns the distance between two arrays of protein frequencies
		
		Arguments:
		p1_freq -- The array representing p1
		p2_freq -- The array representing p2
	"""
	p1, p2 = numpy.array(p1), numpy.array(p2)
	dist = numpy.linalg.norm(p1-p2)
	return dist


def dist_p_from_rest(p1, p_arr):
	""" Returns the array of the distance of a protein from the rest

		Arguments:
		p1 -- The array representing p1
		p_arr -- The array of arrays which representing the rest of proteins
	"""
	dist_arr = []
	for p in p_arr:
		dist_arr.append(dist_two_p(p1, p))
	return dist_arr


def dist_p_from_two_arrs(p1, bs_arr, nbs_arr):
	""" Returns the average of distance of the protein for binding site 
		proteins and non-binding sites proteins

		Arguments:
		p1 -- The array representing p1
		bs_arr -- The array of arrays which representing binding-sites
		nbs_arr -- The array of arrays which representing the non-binding-sites
	"""
	bs_dists = dist_p_from_rest(p1, bs_arr)
	nbs_dists = dist_p_from_rest(p1, nbs_arr)
	bs_avg = sum(bs_dists)/ len(bs_dists)
	nbs_avg = sum(nbs_dists)/ len(nbs_dists)
	return bs_avg, nbs_avg

def dist_arr_from_arr(bs_arr, nbs_arr):
	""" Retruns the average distanes of elements in the binding sites array
		compared to the non binding sites array

		Arguments:
		bs_arr -- The array of arrays which representing binding-sites
		nbs_arr -- The array of arrays which representing the non-binding-sites
	"""
	dist_arr = [] 
	for bs in bs_arr:
		dist_arr.append(dist_p_from_two_arrs(bs, bs_arr, nbs_arr))
	return dist_arr

if __name__ == '__main__':
	p_seq_p = os.path.join(
                os.path.abspath('../data'),
                'p_seq_dict_yeast_154828_formatted.txt'
                #'p_seq_dict_human_binding_sites.txt'
            )
	p_sec_p = os.path.join(
                os.path.abspath('../data'),
                #'yeast_p_sec_struct_dict__formatted.txt'
                'yeast_p_sec_struct_dict__predicted.txt'
            )
	binding_sites_p = os.path.join(
                os.path.abspath('../data'),
                'binding_sites_265.txt'
                #'binding_sites_h.txt'
            )
	amino_p_l = os.listdir('../data/alphabets')
	amino_p_l = filter(lambda a: a.startswith('ab'), amino_p_l)
	encoding_d_arr = []
	cnt, total_len = 0, len(amino_p_l)
	for a in amino_p_l:
		print 50* '-'
		cnt += 1
		start_time = time.time()
		amino_p = os.path.join(
				os.path.abspath('../data/alphabets'),
				a
			)
		bs_arr = r_binding_sites(binding_sites_p)
		bs, nbs = c_seq_mainp_bs_nbs(p_seq_p, p_sec_p, amino_p, bs_arr)
		len_empty_arr = len(bs.amino_classes)**3
		bs_1d_arr = return_one_arr_from_dict(bs.nni_list, len_empty_arr)
		nbs_1d_arr = return_one_arr_from_dict(nbs.nni_list, len_empty_arr)
		d_arr = dist_arr_from_arr(bs_1d_arr, nbs_1d_arr)
		bs_d, nbs_d = [], []
		for (d1, d2) in d_arr:
			bs_d.append(d1)
			nbs_d.append(d2)
		encoding_d_arr.append((sum(bs_d), sum(nbs_d)))
		a = '_'.join(a.split('.')[:2])
		print 'Time', a, 'is', (time.time() - start_time), cnt, '/', total_len
		print 50* '-'
