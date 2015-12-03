import sys, os

from _prepscript_util import calc_md5

import _detection_algorithm_basic as da_basic
import _detection_algorithm_byuniqueness as da_uniqueness
import _detection_algorithm_bycohesion as da_cohesion
import _detection_algorithm_byapriori as da_apriori

MIN_LEN = 30

CCFX_PREP_EXT = ".ccfxprep"
CCFX_PREP_DIR = ".ccfxprepdir"

OUTPUT_EXTENSION = ".cldt"
DEFAULT_OUTPUT_FILE = "a.cldt"

DEFAULT_WORKER_THREAD = 0

MODE_DETECTION, MODE_COUNTING = xrange(0, 2)

CLONEKIND_NORMAL = 'normal'
CLOENKIND_UNIQUENESS = 'uniqueness'
CLONEKIND_COHESION = 'coheison'
CLONEKIND_APRIORI = 'apriori'

CLONEKIND_TO_MODULE = { 
    CLONEKIND_NORMAL: da_basic, 
    CLOENKIND_UNIQUENESS: da_uniqueness, 
    CLONEKIND_COHESION: da_cohesion,
    CLONEKIND_APRIORI: da_apriori }

COUNTKIND_VALIDTOKENS = 'validtokens'
COUNTKIND_CANDIDATES = 'candidates'
COUNTKIND_TOKENSET = 'tokenset'
COUNTKINDS = [ COUNTKIND_VALIDTOKENS, COUNTKIND_VALIDTOKENS, COUNTKIND_TOKENSET ]

class __CommandlineParser(object):
    def __init__(self, sys_argv):
        import getopt
        
        self.usage = """
usage: cldt OPTIONS files...
options
  -b num: minimum length (%(MIN_LEN)d).
  -d dir: source directory.
  -h: shows this message.
  -i filelist: filelist.
  -o output: output file (%(DEFAULT_OUTPUT_FILE)s).
  -v: verbose.
  --nowarn: suppresses warning messages.
  --threads=num: number of worker threads (%(DEFAULT_WORKER_THREAD)d).
  --ccfxprepdir=dir: searches ccfx's preprocessed files.
  --haltwhendone: falls into a halt (-like) state when detection is finished.
detection variations
  --apriori=num: apriori clone. code fragments are sets of substrings
    at least 'num' continuous bigtokens.
  --coheison: cohesion clone.
  --uniqueness: uniqueness clone.
countings
  --count=candidates: counts candidate code fragments for each file.
  --count=validtokens: counts (appearance of) valid tokens for each file.
  --count=tokenset: counts kinds of valid tokens in entire target.
"""[1:-1] % (globals())

        cmd = self
        
        cmd.files = []
        cmd.minLength = MIN_LEN
        cmd.outputFile = None
        cmd.workerThreads = DEFAULT_WORKER_THREAD
        cmd.cloneKind = None
        cmd.ccfxPrepDirs = []
        cmd.optionVerbose = None
        optionNoWarn = None
        cmd.aprioriGramLen = None
        cmd.mode = MODE_DETECTION
        cmd.countKind = None
        cmd.optionHalt = None
    
        if len(sys_argv) == 1:
            print cmd.usage
            sys.exit(0)
        
        opts, args = getopt.gnu_getopt(sys_argv[1:], "b:d:hi:o:v", 
                [ "uniqueness", "nowarn", "threads=", "cohesion", "ccfxprepdir=", 
                "apriori=", "count=", "haltwhendone" ])
        for k, v in opts:
            if k == "-h":
                print cmd.usage
                sys.exit(0)
            elif k == "-b":
                cmd.minLength = int(v)
            elif k == "-o":
                if cmd.outputFile: raise SystemError("option -o appeared twice")
                cmd.outputFile = v
            elif k == "--uniqueness":
                if cmd.cloneKind: raise SystemError("option --apriori, --coheison and --uniqueness are exclusive")
                cmd.cloneKind = CLOENKIND_UNIQUENESS
            elif k == "--cohesion":
                if cmd.cloneKind: raise SystemError("option --apriori, --coheison and --uniqueness are exclusive")
                cmd.cloneKind = CLONEKIND_COHESION
            elif k == "--apriori":
                if cmd.cloneKind: raise SystemError("option --apriori, --coheison and --uniqueness are exclusive")
                cmd.cloneKind = CLONEKIND_APRIORI
                cmd.aprioriGramLen = int(v)
            elif k == "--nowarn":
                optionNoWarn = True
            elif k == "--threads":
                cmd.workerThreads = int(v)
                assert cmd.workerThreads >= 0
            elif k == "--ccfxprepdir":
                cmd.ccfxPrepDirs.append(v)
            elif k == "-v":
                cmd.optionVerbose = True
            elif k == "-d":
                for root, _, files in os.walk(v):
                    files = filter(lambda f: f.endswith(".prep"), files)
                    cmd.files.extend(os.path.join(root, f) for f in files)
            elif k == "-i":
                f = open(v)
                try:
                    lines = f.readlines()
                finally: f.close()
                cmd.files.extend(filter(lambda L: not L.startswith("#"), (L.rstrip() for L in lines)))
            elif k == "--count":
                cmd.mode = MODE_COUNTING
                if cmd.countKind: raise SystemError("option --count specified twice")
                if v in COUNTKINDS:
                    cmd.countKind = v
                else:
                    raise SystemError("invalid argument for option --count")
            elif k == "--haltwhendone":
                cmd.optionHalt = True
                cmd.optionVerbose = True
            else:
                assert False
        cmd.files.extend(args)
        
        if cmd.files and cmd.ccfxPrepDirs:
            raise SystemError("option --ccfxprepdir can't be used with -d, -i or files")
        
        if cmd.cloneKind == CLONEKIND_APRIORI:
            if cmd.aprioriGramLen > cmd.minLength:
                raise SystemError("--apriori's argument should be <= minimum length (-b's argument)")
        if not cmd.files and not cmd.ccfxPrepDirs: raise SystemError("no file found or no file given")
        
        if cmd.mode == MODE_DETECTION:
            if not cmd.outputFile: cmd.outputFile = DEFAULT_OUTPUT_FILE
            if cmd.outputFile != "-" and not cmd.outputFile.endswith(OUTPUT_EXTENSION):
                cmd.outputFile += OUTPUT_EXTENSION
        elif cmd.mode == MODE_COUNTING:
            if not cmd.outputFile: cmd.outputFile = "-"
        else:
            assert False

        if cmd.optionVerbose:
            def log_write(s): sys.stderr.write(s); sys.stderr.flush()
        else:
            def log_write(s): pass
        cmd.log_write = log_write
        cmd.warning_write = sys.stderr.write if not optionNoWarn else None
        
        log_write and log_write("log> output file: %s\n" % cmd.outputFile)
        
        optionsDescription = []
        optionsDescription.append("minimum length: %d" % cmd.minLength)
        if not cmd.cloneKind: cmd.cloneKind = CLONEKIND_NORMAL
        if cmd.cloneKind == CLONEKIND_NORMAL: pass
        elif cmd.cloneKind == CLOENKIND_UNIQUENESS: optionsDescription.append("gap by: uniqueness")
        elif cmd.cloneKind == CLONEKIND_COHESION: optionsDescription.append("gap by: cohesion")
        elif cmd.cloneKind == CLONEKIND_APRIORI: 
            optionsDescription.append("gap by: apriori")
            optionsDescription.append("ngram size: %d" % cmd.aprioriGramLen)
        else:
            assert False
        cmd.optionsDescription = optionsDescription
        
        if log_write:
            for s in optionsDescription: log_write("log> %s\n" % s)

def read_prep_tokens(prepFilelName):
    inp = open(prepFilelName, "rb")
    tokens = [line.rstrip().split("\t")[2] for line in inp if not line.startswith("#")]
    #tokens = []
    #for line in inp:
    #    if line.startswith("#"): continue
    #    tokens.append(line.rstrip().split("\t")[2])
    inp.close()
    return tokens

def search_files(filePaths, ccfxPrepDirs, log_write=None):
    assert filePaths or ccfxPrepDirs
    
    sourceFilePaths = []
    prepFilePaths = []
    sourceExtensionSet = set()
    if ccfxPrepDirs:
        log_write and log_write("log> searching ccfx's preprocessed files...\n")
        for d in ccfxPrepDirs:
            prepDir = os.path.join(d, CCFX_PREP_DIR)
            prepExtension = None
            for root, _, files in os.walk(prepDir):
                sourceRoot = root.replace(prepDir, d, 1)
                files = filter(lambda f: f.endswith(CCFX_PREP_EXT), files)
                for f in files:
                    fsp = f.split(".")
                    if len(fsp) < 6: raise SystemError, "invalid preprocessed file name: %s" % os.path.join(root, f)
                    fext = ".".join(fsp[-4:])
                    if prepExtension and fext != prepExtension:
                        raise SystemError("two or more kinds of preprocessed files exist: %s,%s" \
                            ( prepExtension, fext ))
                    else:
                        prepExtension = fext
                    fext = "." + fsp[-5]; sourceExtensionSet.add(fext)
                    sourceFp = os.path.join(sourceRoot, ".".join(fsp[:-4])); sourceFilePaths.append(sourceFp)
                    prepFp = os.path.join(root, f); prepFilePaths.append(prepFp)
        if not prepExtension:
            raise SystemError("preprocessed files not found")
        log_write and log_write("log> preprocessed extension: %s\n" % prepExtension)
        log_write and log_write("log> source extensions: %s\n" % ",".join(sorted(sourceExtensionSet)))
        prepOptionDescription = [ "prepext: %s" % prepExtension ]
    else:
        log_write and log_write("log> searching .preprocessed files...\n")
        for fp in filePaths:
            if fp.endswith(".prep"):
                fsp = fp.split(".")
                if len(fsp) < 3: raise SystemError("invalid preprocessed file name: %s" % os.path.join(root, f))
                fext = "." + fsp[-2]; sourceExtensionSet.add(fext)
                souceFp = ".".join(fsp[:-1]); sourceFilePaths.append(souceFp)
                prepFilePaths.append(fp)
            else:
                fext = os.path.splitext(fp)[1]; sourceExtensionSet.add(fext)
                sourceFilePaths.append(fp)
                prepFp = fp + ".prep"
                if not os.path.exists(prepFp):
                    raise SystemError("no preprocessed file exists for: %s" % fp)
                prepFilePaths.append(prepFp)
        if not sourceExtensionSet:
            raise SystemError("preprocessed files not found")
        log_write and log_write("log> source extensions: %s\n" % ",".join(sorted(sourceExtensionSet)))
        prepOptionDescription = [ "prepext: %s" % ".prep" ]
    return sourceFilePaths, prepFilePaths, sourceExtensionSet, prepOptionDescription

def main():
    cmd = __CommandlineParser(sys.argv)
    log_write = cmd.log_write
    warning_write = cmd.warning_write
    min_len = cmd.minLength
    
    sourceFilePaths, prepFilePaths, sourceExtensionSet, prepOptionDescription = \
            search_files(cmd.files, cmd.ccfxPrepDirs, log_write)
    
    assert len(sourceFilePaths) == len(prepFilePaths)
    if log_write: log_write("log> reading preprocessed files...\n")
    filePaths = [] # file index -> path
    filePrepTokenSeqs = [] # file index -> tokenseq
    filePrepChecksums = [] # file index -> checksum of preprocessed file
    skippedFileIndices = []
    for fi, ( filePath, prepPath ) in enumerate(zip(sourceFilePaths, prepFilePaths)):
        filePaths.append(filePath)
        try:
            prepTokenSeq = read_prep_tokens(prepPath)
            filePrepTokenSeqs.append(prepTokenSeq)
            filePrepChecksums.append(calc_md5(prepPath))
        except IOError:
            warning_write and warning_write("warning> can't read preprocessed file of: %s\n" % filePath)
            skippedFileIndices.append(fi)
            filePrepTokenSeqs.append([])
    
    log_write and log_write("log> read preprocessed files: %d\n" % (len(filePrepTokenSeqs) - len(skippedFileIndices)))
    if skippedFileIndices: log_write and log_write("log> skipped preprocessed files: %d\n" % len(skippedFileIndices))
    
    def output_open():
        if cmd.outputFile != "-":
            output = open(cmd.outputFile, "w")
            return output.write, output.close
        else:
            def nop(): pass
            return sys.stdout.write, nop
        
    m = CLONEKIND_TO_MODULE[cmd.cloneKind]
    if cmd.mode == MODE_DETECTION:
        if cmd.cloneKind != CLONEKIND_APRIORI:
            cloneclass_iter = m.detect_cloneclass(filePrepTokenSeqs, min_len, 
                    log_write=log_write, warning_write=warning_write, workerThreads=cmd.workerThreads)
        else:
            cloneclass_iter = m.detect_cloneclass(filePrepTokenSeqs, min_len, cmd.aprioriGramLen,
                    log_write=log_write, warning_write=warning_write, workerThreads=cmd.workerThreads)
        
        log_write and log_write("log> writing clone sets...\n")
        
        output_write, output_close = output_open()
        for s in cmd.optionsDescription + prepOptionDescription: output_write("#%s\n" % s)
        
        output_write("files:\n")
        is_skipped_file_index = set(skippedFileIndices).__contains__
        for fi, filePath in enumerate(filePaths): 
            if is_skipped_file_index(fi):
                output_write("%d\t%s\t-\t-\n" % ( fi+1, filePath ))
            else:
                output_write("%d\t%s\t%d\t%s\n" % 
                        ( fi+1, filePath, len(filePrepTokenSeqs[fi]), filePrepChecksums[fi] ))
        
        output_write("clone classes:\n")
        for cc in cloneclass_iter():
            output_write("{\n")
            for i, ccItem in enumerate(cc):
                if i > 0: output_write("--\n")
                for fi, tokenIndexRanges in ccItem:
                    r = ",".join(("%d+%d" % ( pos+1, length )) for pos, length in tokenIndexRanges)
                    output_write("%d\t%s\n" % ( fi+1, r ))
            output_write("}\n")
        output_close()
    elif cmd.mode == MODE_COUNTING:
        countingFunction = None
        title = None
        if cmd.countKind == COUNTKIND_VALIDTOKENS:
            countingFunction = m.count_valid_tokens
            title = "bigtoken count"
        elif cmd.countKind == COUNTKIND_CANDIDATES:
            countingFunction = m.count_candidates
            title = "candidate count"
        elif cmd.countKind == COUNTKIND_TOKENSET:
            countingFunction = m.count_tokenset
            title = "bigtoken tokenset"
        else:
            assert False
        
        fi_count_iter = countingFunction(filePrepTokenSeqs, min_len, 
                log_write=log_write, warning_write=warning_write, workerThreads=cmd.workerThreads)
            
        output_write, output_close = output_open()
        for s in cmd.optionsDescription + prepOptionDescription: output_write("#%s\n" % s)
        output_write("%s\n" % title)
        is_skipped_file_index = set(skippedFileIndices).__contains__
        totalCount = 0
        for fi, count in fi_count_iter():
            if fi == -1:
                totalCount = count
                break # for fi
            else:
                filePath = filePaths[fi]
                if is_skipped_file_index(fi):
                    output_write("%d\t%s\t-\n" % ( fi+1, filePath ))
                else:
                    output_write("%d\t%s\t%d\n" % ( fi+1, filePath, count ))
                totalCount += count
        output_write("total\t-\t%d\n" % totalCount)
        output_close()
    else:
        assert False
    
    log_write and log_write("log> done.\n")
    
    if cmd.optionHalt:
        import time
        while True: time.sleep(0.5)

if __name__ == '__main__':
    main()

