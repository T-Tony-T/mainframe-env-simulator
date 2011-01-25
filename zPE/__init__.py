import os, sys, pickle
import re

### Architectural Definition

JOB_ID_MIN = 10000              # the smallest job ID
JOB_ID_MAX = 65535              # the largest job ID
TMP_FILE_ID = 101               # the smallest tmp file identifier
GPR_NUM = 16                    # number of general purpose registers

def ck_label(lable):
    if len(lable) == 0:
        return True             # no lable
    if len(lable) > 8:
        return False            # label too long
    if re.match('[A-Z@#$][A-Z@#$0-9]+', lable).group(0) != lable:
        return False            # illegal character
    return True


### Program Definition

# Configurable Definition
DEFAULT = {
    'ADDR_MODE' : 31,           # hardware addressing mode: 31 bit

    'MEMORY_SZ' : '1024K',      # memory size: 1024 KB
    'MEM_MAX'   : 1048576,      # 1024K = 1024 * 1024 = 1048576

    'SPOOL_PATH' : '',          # SPOOL positon: current directory

    'ICH70001I' : {             # config list for ICH70001I
        'atime' : '00:00:00 ON THURSDAY, JANUARY 18, 2011',
                                # the start time of this project
        },
    }

Config = {
    'job_id'    : JOB_ID_MIN,
    'tmp_id'    : TMP_FILE_ID,  # next available tmp file identifier
    'addr_mode' : DEFAULT['ADDR_MODE'],
    'addr_max'  : 0,            # calculate on loading
    'memory_sz' : DEFAULT['MEMORY_SZ'],
                # in future, this may be controled by "// EXEC PGM=*,REGION="
    'mem_max'   : DEFAULT['MEM_MAX'],
    'spool_path': DEFAULT['SPOOL_PATH'],
    }

CONFIG_PATH = {
    'dir'       : os.path.join(os.environ['HOME'], '.zPE'),
    'rc'        : os.path.join(os.environ['HOME'], '.zPE', 'zPE.conf'),
    'data'      : os.path.join(os.environ['HOME'], '.zPE', 'data'),
    'ICH70001I' : os.path.join(os.environ['HOME'], '.zPE', 'data', 'ICH70001I'),
    }

def dump_ICH70001I(conf):
    __CK_CONFIG()
    __TOUCH_ICH70001I(conf)
    
def load_ICH70001I():
    __CK_CONFIG()
    return pickle.load(open(CONFIG_PATH['ICH70001I'], 'rb'))
    

def read_rc():
    __CK_CONFIG()

    for line in open(CONFIG_PATH['rc'], 'r'):
        (k, v) = re.split('[ \t]*=[ \t]*', line, maxsplit=1)

        if k == 'job_id':
            try:
                Config[k] = int(v) + 1
                if Config[k] < JOB_ID_MIN or Config[k] > JOB_ID_MAX:
                    Config[k] = JOB_ID_MIN
            except ValueError:
                Config[k] = JOB_ID_MIN
                sys.stderr.write('Warning: ' + v[:-1] +
                                 ': Invalid job ID.\n')

        elif k == 'addr_mode':
            try:
                Config[k] = int(v)
                if Config[k] not in [16, 31, 64]:
                    Config[k] = ADDR_MODE
            except ValueError:
                Config[k] = ADDR_MODE
                sys.stderr.write('Warning: ' + v[:-1] +
                                 ': Invalid address mode.\n')

        elif k == 'memory_sz':
            v = re.split('(\d+)', v)
            if len(v) == 2:
                Config[k] = int(v[1])
                Config['mem_max'] = Config['memory_sz']
            elif (len(v) == 3) and ('K' in re.split('\s', v[2].upper())):
                Config[k] = v[1] + 'K'
                Config['mem_max'] = int(v[1]) * 1024
            else:
                sys.stderr.write('Warning: ' + v[:-1] +
                                 ': Invalid memory size.\n')

        elif k == 'spool_path':
            if os.path.isdir(v[:-1]):
                Config['spool_path'] = v[:-1]
            else:
                sys.stderr.write('Warning: ' + v[:-1] +
                                 ': Invalid SPOOL path.\n')

    Config['addr_max'] = 2 ** Config['addr_mode']
    __TOUCH_RC()


# File Definition
def conv_path(fn):
    return re.split('\.', fn)

def create_dir(path):
    if os.path.isdir(path):
        return None
    else:
        os.makedirs(path)

def is_file(dsn):
    return os.path.isfile(os.path.join(* dsn))

def is_dir(dsn):
    return os.path.isdir(os.path.join(* dsn))

def open_file(dsn, mode):
    return open(os.path.join(* dsn), mode)


# JCL Definition
JCL = {
    # fetched when parsing JCL
    'owner'     : '*OWNER',
    'jobname'   : '*JOBNAME',
    'job'       : 'JOB*****',
    'jobstart'  : 'start time:',
    'jobend'    : 'end time:',
    'step'      : [],           # each item is of type "Step"
    'read_cnt'  : 0,
    'card_cnt'  : 0,
    }

class Step:                     # for JCL['step']
    def __init__(self, name, pgm = '', proc = '', parm = ''):
        self.name = name
        self.pgm = pgm
        self.proc = proc
        self.parm = parm
        self.start = 'start time:'
        self.dd = {}

    def append_dd(self, ddname, dd):
        if ddname in self.dd:
            sys.stderr.write('Error: ' + ddname + ': Duplicated DD names.\n')
            sys.exit(44)
        for k,v in dd.items():
            if k not in ['SYSOUT', 'DSN', 'DISP']:
                sys.stderr.write('Error: ' + k + '=' + v +
                                 ': Un-recognized key\n')
                sys.exit(44)
        self.dd[ddname] = [len(self.dd), dd]
        

# Program Supported
PGM_SUPPORTED = {         # all supported programs and their bindings
    'ASSIST'  : 'zPE.pgm.ASSIST.main',
    'IEFBR14' : 'pass',
    }

def LIST_PGM():                # list all supported languages out
    print 'All programs (PGM) that are currently supported:'
    print '  ASSIST     -- Assembler using ASSIST'
    print


# SPOOL Definition
SPOOL = {                       # defaultly opened spools; path will be modified
    'JESMSGLG' : [[], 'o', ['01_JESMSGLG']],
    'JESJCL'   : [[], 'o', ['02_JESJCL']],
    'JESYSMSG' : [[], 'o', ['03_JESYSMSG']],
    }

def new_spool(key, mode, path = []):
    # check uniqueness
    if key in SPOOL:
        sys.stderr.write('Error: ' + key + ': SPOOL name conflicts.\n')
        sys.exit(-1)

    # check mode
    if mode not in ['i', 'o', 't']:
        sys.stderr.write('Error: ' + mode + ': Invalid SPOOL mode.\n')
        sys.exit(-1)

    # check path auto-generation
    if len(path) == 0:
        while True:
            conflict = False
            path = [ Config['spool_path'],
                     JCL['jobname'] + '.' + JCL['job'],
                     'D{0:0>7}'.format(Config['tmp_id']) ]
            Config['tmp_id'] += 1
            # check for file conflict
            for k,v in SPOOL.items():
                if v[2] == path:
                    conflict = True
                    break
            if not conflict:
                break

    SPOOL[key] = [[], mode, path]


### Supporting Function

def __CK_CONFIG():
    if not os.path.isdir(CONFIG_PATH['data']):
        os.makedirs(CONFIG_PATH['data'])
    if not os.path.isfile(CONFIG_PATH['rc']):
        __TOUCH_RC()
    if not os.path.isfile(CONFIG_PATH['ICH70001I']):
        __TOUCH_ICH70001I()

def __TOUCH_ICH70001I(conf = DEFAULT['ICH70001I']):
    pickle.dump(conf, open(CONFIG_PATH['ICH70001I'], 'wb'))

def __TOUCH_RC():
    fp = open(CONFIG_PATH['rc'], 'w')
    fp.write('job_id = ' + str(Config['job_id']) + '\n')
    fp.write('addr_mode = ' + str(Config['addr_mode']) + '\n')
    fp.write('memory_sz = ' + Config['memory_sz'] + '\n')
    if Config['spool_path'] != '':
        fp.write('spool_path = ' + Config['spool_path'] + '\n')
    fp.close()

