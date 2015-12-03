import os
import math
import re
import sys
import traceback
import sqlite3 as lite
import sys
import pickle
import pprint
import random

def rm_line (p, l_no):
	""" Remove a line in a file and rewrite it over it
	"""
	f = open (p, 'r')
	arr = [l for l in f]
	f.close()
	f = open (p, 'w')
	for i, l in enumerate(p):
		if i == l_no:
			f.write(l)	

def pos_neg ():
	""" Read positive and negative samples from a file. Also if there is 
		unwanted lines
	"""
	base_p = '/tmp/fisher/'
	dirs = os.listdir (base_p)
	p_p_list = []
	for path in dirs:
		pros = os.listdir (base_p+path)
		tmp_pros = ['.'.join (i.split('.')[:-1]) for i in pros]
		tmp_pros = list(set(tmp_pros))
		for s in tmp_pros:
			p_p_list.append (base_p+path+'/'+s)
	for p in p_p_list:
		_p = p+'.test'
		f_train = open(_p, 'r')
		arr = [l for l  in f_train]
		f_train.close()
		_s = [l.split()[-1] for l in arr]
		s = []
		for i, l in enumerate(_s):
			try:
				s.append(int(l))
			except:
				print(_p, i)
				rm_line (_p, i)
		pos, neg =0, 0
		for cls in s:
			if cls > 0:
				pos += 1
			if cls<0:
				neg += 1 
		print(_p, pos, neg)
	return p_p_list

def read_prots_fams(p):
	""" The file which reads the proteins from a simple text format
		
		args:
			p -- path to the file which includes the proteins
	"""
	all_aminos = [ 'P', 'G', 'E', 'K', 'R', 'Q', 'D', 'S', 'N', 'T', 
		'H', 'C', 'I', 'V', 'W', 'F', 'Y', 'A', 'L', 'M']

	try:
		tree_struct = {}
		f = open(p, 'r')
		arr = [l for l in f]
		prots, fams = [], []
		new_prot = ''
		for l in arr:
			if l.startswith('>'):
				if new_prot != '':
					has_aminos = [a for a in all_aminos if a in new_prot]
					if len(has_aminos)>0:
						prots.append(new_prot)
				fams.append(l.split(' ')[1])
				new_prot = ''
			else:
				new_prot += l[:-1]
		prots.append(new_prot) # Added for the last line
		fams = [l.split('.') for l in fams]
		return  prots, fams
	except IOError:
		traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
								  sys.exc_info()[2])


def put_in_db_2_tbls(prots, fams, db_p):
	""" The code to put the data into a database with 2 tables

		args:
			prots -- Proteins to put in, arr
			fams --	Families of the proteins to put in, arr
			db_p -- The path to the database
	"""
	fams_inst_str = []
	with lite.connect(db_p) as con:
		cur = con.cursor()
		cur.execute ('DROP TABLE IF EXISTS scop;');
		cur.execute ('DROP TABLE IF EXISTS fams;');
		cur.execute ('DROP TABLE IF EXISTS seqs;');
		cur.execute(
			'CREATE TABLE IF NOT EXISTS scop (' +
				'class TEXT,' + 
				' fold INTEGER,' +
				'super_family INTEGER,' +
				'family INTEGER,' +
				'seq TEXT' +
			');'
		)
		cur.execute(
			'CREATE TABLE IF NOT EXISTS fams (' +
				'id INTEGER PRIMARY KEY AUTOINCREMENT,' + 
				'class TEXT,' + 
				'fold INTEGER,' +
				'super_family INTEGER,' +
				'family INTEGER' +
			');'
		)
		cur.execute(
			'CREATE TABLE IF NOT EXISTS seqs (' + 
				' id INTEGER PRIMARY KEY AUTOINCREMENT,' + 
				' fams_id INTEGER,' + 
				' seq TEXT' + 
			');'
		)
		inst_scop = "INSERT INTO scop VALUES ('{0}', {1}, {2}, {3}, '{4}');"
		inst_fams = "INSERT INTO fams VALUES (NULL, '{0}', {1}, {2}, {3});"
		inst_seqs = "INSERT INTO seqs VALUES (NULL, {0}, '{1}');"
		for i in range(len(prots)):
			cls, fold, super_family, fam = fams[i]
			new_inst_scop = inst_scop.format(cls, fold, super_family, fam, prots[i])
			new_inst_fams = inst_fams.format(cls, fold, super_family, fam)
			fams_inst_str.append(new_inst_fams)
			cur.execute(new_inst_scop)
		# Save the set of unique families
		_fams = list(set(fams_inst_str))
		for f in _fams:
			cur.execute(f)
		for i in range(len(fams_inst_str)):
			fams_id = _fams.index(fams_inst_str[i]) + 1 # +1 is for starting 0
			new_inst_seqs = inst_seqs.format(fams_id, prots[i])
			cur.execute(new_inst_seqs)
	con.close()


def query_fetch_rows(query, db_p):
	con = lite.connect(db_p)
	with con:
		cur = con.cursor()
		cur.execute(query)
		rows = cur.fetchall()
	return rows


def read_largest_p(p='/tmp/data.pkl'):
	""" Reads the data from the binanry file which has an array in it and
		finds the largest super_families and returns it
	"""
	f = open(p, 'rb')
	p_class = pickle.load(f)
	sf_large_prots = []
	for c in p_class:
		prots_in_sf = []
		for i, fold in enumerate(p_class[c]):
			#print ()
			#print ('fold', i,'has', len(fold), 'super_family')
			for j, sf in enumerate(fold):
				#print ('	super_family', j, 'has', len(sf), 'family')
				sum_prot_in_sf = 0
				for k, f in enumerate(sf):
					#print ('	 family', k, 'has', len(f), 'proteins')
					sum_prot_in_sf += len(f)
				#print ('>>in total a',i,j, 'has', sum_prot_in_sf, 'protein')
				prots_in_sf.append((sum_prot_in_sf, c, sf))
			#print ()
		prots_in_sf.sort()
		prots_in_sf.reverse()
		sf_large_prots.append(prots_in_sf[0])
		sf_large_prots.append(prots_in_sf[1])
		sf_large_prots.append(prots_in_sf[2])
		sf_large_prots.append(prots_in_sf[3])
	return sf_large_prots




def save_bin_2tbls_arr(db_p, out_bin_f='/tmp/data.pkl'):
	""" Reads the data from the database given in the db_p and saves them in 
		indented arrays

		args:
			db_p -- the path to the database
			out_bin_f -- the path to the output binary
		
	"""
	fams_db = 'fams'
	seqs_db = 'seqs'
	p_class = {'a':0, 'b':0, 'c':0, 'd':0, 'e':0, 'f':0, 'g':0}
	for cls in p_class:
		query = "SELECT fold FROM {0} WHERE class='{1}' ORDER BY fold ASC;"
		query = query.format(fams_db, cls)
		rows = query_fetch_rows(query, db_p)
		folds = [r[0] for r in rows]
		folds = list(set(folds))
		super_family = []
		for i, fold in enumerate(folds):
			query =  " SELECT class, fold, super_family, family FROM {0} "
			query += " WHERE class='{1}' and fold={2} "
			query += " ORDER BY super_family ASC;"
			query = query.format(fams_db, cls, fold)
			rows = query_fetch_rows(query, db_p)
			sfs = [r[2] for r in rows]
			sfs = list(set(sfs))
			sf_l = []
			for i, sf in enumerate(sfs):
				query =  " SELECT id, family FROM {0} "
				query += " WHERE class='{1}' and fold={2} and super_family={3}"
				query += " ORDER BY family ASC;"
				query = query.format(fams_db, cls, fold, sf)
				rows = query_fetch_rows(query, db_p)
				fs = [r[1] for r in rows]
				fs = list(set(fs))
				ids = [r[0] for r in rows]
				ids = list(set(fs))
				fam_l = []
				for i, _id in enumerate(ids):
					query =  " SELECT distinct seq FROM {0} "
					query += " WHERE fams_id={1};"
					query = query.format(seqs_db, _id)
					rows = query_fetch_rows(query, db_p)
					rows = [r[0] for r in rows] # first elem of tuples
					fam_l.append(rows)
				sf_l.append(fam_l)
			super_family.append(sf_l)
		p_class[cls] = super_family
	o = open(out_bin_f, 'wb')
	pickle.dump(p_class, o)


def c_pos_train_test_set(large_super_fams, num_prots, train_p, test_p):
	""" Given the list of super families, it randomly picks parts of them as the
		train set and some of it as the test set and it is used for POSITIVES
		
		args:
			large_super_fams -- the array containing prots
			train_p -- the output path for train set
			test_p -- the output path for test set
	"""
	try:
		train_f = open(train_p, 'w')
		test_f = open(test_p, 'w')
		random.shuffle(large_super_fams)
		train_len = 0 
		for i, fam in  enumerate(large_super_fams):
			if  train_len + len(fam) < num_prots*2/3:
				for p in fam:
						train_f.write(str(p)+' 1\n')
				train_len += len(fam)
			else:
				for p in fam:
					test_f.write(str(p)+' 1\n')
		train_f.close()
		test_f.close()			
	except IOError:
		traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
								  sys.exc_info()[2])


def c_neg_train_test_set(fams, cls, length, train_p, test_p):
	""" Given an indented dict/list, this function flattens it and 
		returns a randomly chosen set of them as the results

		args:
			fams -- the indented array containing prots
			train_p -- the output path for train set
			test_p -- the output path for test set
	"""
	all_p = []
	for c in p_class:
		if c == cls:
			continue
		for i, fold in enumerate(p_class[c]):
			#print ()
			#print ('fold', i,'has', len(fold), 'super_family')
			for j, sf in enumerate(fold):
				#print ('	super_family', j, 'has', len(sf), 'family')
				sum_prot_in_sf = 0
				for k, f in enumerate(sf):
					#print ('	 family', k, 'has', len(f), 'proteins')
					sum_prot_in_sf += len(f)
				#print ('>>in total a',i,j, 'has', sum_prot_in_sf, 'protein')
					for prot in f:
						all_p.append(prot)
			#print ()
	try:
		train_f = open(train_p, 'a+')
		test_f = open(test_p, 'a+')
		random.shuffle(all_p)
		for i in range(length):
			if i<= length*2/3:
				train_f.write(all_p[i]+' -1\n')
			else:
				test_f.write(all_p[i]+' -1\n')
		train_f.close()
		test_f.close()
	except IOError:
		traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
								  sys.exc_info()[2])


def main():
	pass
	#p, fams = read_prots_fams('../data/astral_scop_45.txt')
	#put_in_db_2_tbls(p, fams, '../data/astral_scop_45.db)


if __name__ == '__main__':
	db_p = '../data/astral_scop_45.db'
	db_p = '../data/astral_scop_1.75.db'
	#p, fams = read_prots_fams('../data/scopdom.txt')
	#p, fams = read_prots_fams('../data/astral_scop_45.txt')
	#p, fams = read_prots_fams('../data/astral_scop_1.75.txt')
	#put_in_db_2_tbls(p, fams, db_p)
	#save_bin_2tbls_arr(db_p) # Creates the /tmp/data.pkl from the db_p

	f = open('/tmp/data.pkl', 'rb')
	p_class = pickle.load(f)
	f.close()
	large_class = read_largest_p()
	#large_class.sort()
	#large_class.reverse()
	#last = []
	i = 1
	for length, cls, sf in large_class:
		s = sum([len(fam) for fam in sf])
		print(i ,cls, length, len(sf), s)
		i += 1
		#last = sf
		c_pos_train_test_set(sf, length,
			'sf_train_test/' + cls + '_' + str(length) + '.train',
			'sf_train_test/' + cls + '_' + str(length) + '.test')
		c_neg_train_test_set(p_class, cls, length,
			'sf_train_test/' + cls + '_' + str(length) + '.train',
			'sf_train_test/' + cls + '_' + str(length) + '.test')
