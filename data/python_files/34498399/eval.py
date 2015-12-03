import code
import glob
import os
import pickle
import random
import score
import mbrtrain
import shutil
import sys
import re
import math
import errno

from mbrtrain import *
from score import Score
    

def compute_boundaries(n, N):
    s1 = N/n
    s2 = s1 + 1
    n2 = N - n*s1
    n1 = n - n2
    last1 = n1 * s1
    boundaries = range(0, last1, s1) + range(last1, N+1, s2)
    return boundaries
    

def parse_filenames():
    data_files = {}
    for name in glob.glob(os.path.join(score.OUTPUT_DIR, "*.pkl")):
        (front, data_file) = os.path.split(name)
        m = re.search('(.+)_([a-zA-Z]+)\.pkl', data_file)
        if m:
            directory = m.group(1)
            genre = m.group(2)
            data_files.setdefault(directory, []).append((genre, name))
    return data_files

def read_scores(data_file):
    try:
        with open(data_file) as fd:
            scores = pickle.load(fd)
        print "Opened " + data_file
    
    except IOError, e:
        print "Could not open pkl file", e
        return False

    sentences = []
    n_sentences = len(scores.B[0][0])
    for k in xrange(n_sentences):
        s = Sentence()
        s.w = 1
        
        bestscore = -inf
        bestengine = None
        for engine in scores.ref_scores:
            if scores.ref_scores[engine][k] > bestscore:
                bestengine = engine
                bestscore = scores.ref_scores[engine][k]
        
        for i, B_i in enumerate(scores.B):
            tln = translation()
            tln.engine = scores.engine_i_to_name[i]
            tln.features = [B_ij[k] for B_ij in B_i]
            tln.score = scores.ref_scores[tln.engine][k]
            if tln.engine == bestengine:
                tln.metric = 1
            else:
                tln.metric = 0
            s.tlns.append(tln)
        sentences.append(s)
    return (scores, sentences)

def write_trans_to_file(directory, genre, engines, boundaries, cs_trans, oc_trans):
    input_dir = os.path.join(score.INPUT_DIR, directory)
    output_dir = os.path.join(score.OUTPUT_DIR, directory)
    try:
        os.makedirs(output_dir)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise
    test_in = {}
    for eng in engines:
        name = os.path.join(input_dir, '%s-%s.txt' % (genre, eng))
        test_in[eng] = open(name, 'r')

    ref_in_name = os.path.join(input_dir, '%s-ref.txt' % genre)
    ref_in = open(ref_in_name, 'r')
    metric_name = os.path.join(output_dir, '%s-sentence-stats.txt' % genre)
    metric_out = open(metric_name, 'w')
    avg_metric = {}
    engines2 = engines + ['cs']

    metric_out.write('testset ')
    for eng in engines2:
        metric_out.write('%10s' % eng)
    metric_out.write('\n')
    metric_out.write('------------------------------------------------\n')

    for i in xrange(0, len(boundaries)-1):
        test_out = {}
        trans = {}
        metric = {}
        for eng in engines:
            name = os.path.join(output_dir, '%s-%s-%d.txt' % (genre, eng, i))
            test_out[eng] = open(name, 'w')
        cs_out_name = os.path.join(output_dir, '%s-cs-%d.txt' % (genre, i))
        cs_out = open(cs_out_name, 'w')
        oc_out_name = os.path.join(output_dir, '%s-oc-%d.txt' % (genre, i))
        oc_out = open(oc_out_name, 'w') 
        ref_out_name = os.path.join(output_dir, '%s-ref-%d.txt' % (genre, i))
        ref_out = open(ref_out_name, 'w')
        
        head = boundaries[i]
        tail = boundaries[i+1]
        
        for j in xrange(head, tail):
            for eng in engines:
                trans[eng] = test_in[eng].readline()
                test_out[eng].write(trans[eng])
            cs_line = trans[cs_trans[j]]
            oc_line = trans[oc_trans[j]]
            if oc_trans[j] == cs_trans[j]:
                metric['cs'] = metric.get('cs', 0) + 1
            metric[oc_trans[j]] = metric.get(oc_trans[j], 0) + 1
            cs_out.write(cs_line)
            oc_out.write(oc_line)
            for k in xrange(0, 4):
               line = ref_in.readline()
               ref_out.write(line)

        for eng in engines:
            test_out[eng].close()
        metric_out.write('%2d      ' % i)
        for eng in engines2:
            m = metric.get(eng, 0)
            metric_out.write('%10d' % m)
            avg_metric[eng] = avg_metric.get(eng, 0) + m
        metric_out.write('\n')
        ref_out.close()
        cs_out.close()
        oc_out.close()
    for eng in engines:
        test_in[eng].close()
    metric_out.write('------------------------------------------------\n')
    metric_out.write('average:')
    for eng in engines2:
        m = avg_metric.get(eng, 0) / (len(boundaries) - 1)
        metric_out.write('%10.1f' % m)
    metric_out.write('\n')
    ref_in.close()
    metric_out.close()

def evaluate(n):
    data_files = parse_filenames()
    for directory in data_files:
        for (genre, data_file) in data_files[directory]:
            (scores, sentences) = read_scores(data_file)
            engines = sentences[0].engines()
            boundaries = compute_boundaries(n, len(sentences))
            cs_trans = []
            oc_trans = []
            for i in xrange(1, len(boundaries)):
                head = boundaries[i-1]
                tail = boundaries[i]
                train_set = sentences[0:head] + sentences[tail+1:]
                test_set = sentences[head:tail]
                (wt, metric) = train_weight(len(scores.ref_scores), len(scores.B[0]), train_set)
                cs_trans += apply_consensus(wt, test_set)
                oc_trans += apply_oracle(test_set)
            write_trans_to_file(directory, genre, engines, boundaries, cs_trans, oc_trans)


EVAL_DATASETS = ['bn', 'nw', 'ps', 'wb']
EVAL_ENGINES = ['cs', 'gl', 'ms', 'oc', 'st']
EVAL_IN_DIR = os.path.join(score.OUTPUT_DIR, 'web3_plain')
EVAL_OUT_DIR = os.path.join(score.OUTPUT_DIR, 'scores')

def concat_cross_validation_folds():
    for dataset in EVAL_DATASETS:
        for engine in EVAL_ENGINES + ['ref']:
            file_prefix = os.path.join(EVAL_IN_DIR, "{0}-{1}".format(dataset, engine))
            file_list = sorted(glob.glob(file_prefix + "-*.txt"))

            with open(file_prefix + '.txt', 'w') as out_fd:
                for f in file_list:
                    with open(f) as in_fd:
                        shutil.copyfileobj(in_fd, out_fd)


def evaluate_engine_scores():
    concat_cross_validation_folds()
    ref_scores = {}
    avg_scores = {}

    print 'Average scores:'
    for dataset in EVAL_DATASETS:
        print '\t {0} dataset:'.format(dataset)
        ref_scores[dataset] = {}
        avg_scores[dataset] = {}
        path = os.path.join(EVAL_IN_DIR, dataset)
        s = Score(path)
        test_list = ["{0}-{1}.txt".format(path, engine) for engine in EVAL_ENGINES]
        ref_file = path + "-ref.txt"


        (file1, file2, line_counts) = s.BatchFiles(test_list, [ref_file])
        output_file = s.ComputeMeteorScores(file1, file2, n_refs=4)
        results = s.UnbatchResults(output_file, test_list, [ref_file], line_counts)
        for i, r in enumerate(results):
            len(r) == 1 or Die("Multiple results for only 1 reference")
            engine_name = EVAL_ENGINES[i]
            ref_scores[dataset][engine_name] = r[0]
            avg_scores[dataset][engine_name] = float(sum(r[0])) / len(r[0])
            print '\t\t {0} engine: {1}'.format(engine_name, avg_scores[dataset][engine_name])
            

    out_dir = os.path.join(score.OUTPUT_DIR, "results")
    pickle.dump(ref_scores, open(os.path.join(out_dir, 'ref_scores.pkl'), 'w'))
    pickle.dump(avg_scores, open(os.path.join(out_dir, 'avg_scores.pkl'), 'w'))



if __name__ == "__main__":
    # evaluate(5) # uncomment to re-evaluate
    evaluate_engine_scores()
