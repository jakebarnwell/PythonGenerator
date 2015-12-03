import sys
import pickle
import os
from multiprocessing import Pool

import numpy as np
from PyML import *
from PyML import SparseDataSet


from feat_sel import rank_feat


def train_test(ds_path):
	data = SparseDataSet(ds_path)
	g, c, fold = 0.25, 128, 2
	##################################################
	#### This part of the code does Does statistical 
	#### feature selection ...
	#labels = np.array([int(n) for n in data.labels.L])
	#ranks = rank_feat(data.getMatrix().T, labels)
	#ranks = [(abs(r),i) for i, r in enumerate(ranks)]
	#ranks.sort()
	#ranks.reverse()
	#feats = [f[1] for f in ranks]
	#data.keepFeatures(feats[:2662])

	data.attachKernel('gaussian', gamma = g)
	s=SVM(C=c)
	r = s.cv(data, numFolds=fold)
	o = open(ds_path+'.pkl', 'wb')
	pickle.dump(r, o)
	o.close();
	print ds_path


if __name__ == '__main__':
	ds_ps = '/tmp/ecnoded_dir/'
	dss = os.listdir(ds_ps)
	dss = [ds_ps+p for p in dss]
	pool = Pool(8)
	pool.map(train_test, dss)
