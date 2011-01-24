import os, sys
import re

### Architectural Definition

JOB_ID_MIN = 10000              # the smallest job ID
JOB_ID_MAX = 65535              # the largest job ID
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
ADDR_MODE = 31                  # default hardware addressing mode
MEMORY_SZ = "1024K"             # default memory size: 1024K
MEM_MAX = 1048576               # 1024K = 1024 * 1024 = 1048576

Config = {
    'job_id' : JOB_ID_MIN,
    'tmp_id' : 101,             # used to identify each tmp file
    'addr_mode' : ADDR_MODE,
    'addr_max' : 0,             # calculate on loading
    'memory_sz' : MEMORY_SZ,
    'mem_max' : MEM_MAX,
    }

CONFIG_FILE = os.path.join(os.environ['HOME'], '.zPErc')

def Read_Config():
    fp = open(CONFIG_FILE, 'r')
    for line in fp:
        (k, v) = re.split('[ \t]*=[ \t]*', line, maxsplit=1)

        if k == 'job_id':
            try:
                Config[k] = int(v) + 1
                if Config[k] < JOB_ID_MIN or Config[k] > JOB_ID_MAX:
                    Config[k] = JOB_ID_MIN
            except ValueError:
                Config[k] = JOB_ID_MIN

        elif k == 'addr_mode':
            try:
                Config[k] = int(v)
                if Config[k] not in [16, 31, 64]:
                    Config[k] = ADDR_MODE
            except ValueError:
                Config[k] = ADDR_MODE

        elif k == 'memory_sz':
            v = re.split('(\d+)', v)
            if len(v) == 2:
                Config[k] = int(v[1])
                Config['mem_max'] = Config['memory_sz']
            elif (len(v) == 3) and ('K' in re.split('\s', v[2].upper())):
                Config[k] = v[1] + 'K'
                Config['mem_max'] = int(v[1]) * 1024
            else:
                Config[k] = MEMORY_SZ
                Config['mem_max'] = MEM_MAX

    Config['addr_max'] = 2 ** Config['addr_mode']
    Touch_Config();

    
def Touch_Config():
    fp = open(CONFIG_FILE, 'w')
    fp.write('job_id = ' + str(Config['job_id']) + '\n')
    fp.write('addr_mode = ' + str(Config['addr_mode']) + '\n')
    fp.write('memory_sz = ' + Config['memory_sz'] + '\n')
    fp.close()


# File Definition
def open_file(dsn, mode):
    return open(os.path.join(* dsn), mode)

def conv_path(fn):
    return re.split('\.', fn)


# JCL Definition
JCL = {
    # fetched when parsing JCL
    'owner'     : '*OWNER',
    'jobname'   : '*JOBNAME',
    'job'       : 'JOB*****',
    'step'      : [],           # each item is of type "Step"
    'card_cnt'  : 0,
    }

class Step:                     # for JCL['step']
    def __init__(self, name, pgm = '', proc = '', parm = ''):
        self.name = name
        self.pgm = pgm
        self.proc = proc
        self.parm = parm
        self.dd = []

    def append_dd(self, dd):
        for k,v in dd.items():
            if k not in ['name', 'sysout', 'dsn', 'disp']:
                sys.stderr.write('Error: ' + k + '=' + v +
                                 ': Un-recognized key\n')
                sys.exit(44)
        self.dd.append(dd)
        

# Program Supported
PGM_SUPPORTED = {         # all supported programs and their bindings
    'ASSIST' : 'zPE.pgm.ASSIST.main',
    }

def LIST_PGM():                # list all supported languages out
    print 'All programs (PGM) that are currently supported:'
    print '  ASSIST     -- Assembler using ASSIST'
    print


# SPOOL Definition
SPOOL = {
    'JESMSGLG' : [[], 'o', ['1_JESMSGLG']],
    'JESJCL'   : [[], 'o', ['2_JESJCL']],
    'JESYSMSG' : [[], 'o', ['3_JESYSMSG']],
    }

def new_spool(key, mode, path = []):
    if key in SPOOL:
        sys.stderr.write('Error: ' + key + ': SPOOL name conflicts.\n')
        sys.exit(-1)
    if mode not in ['i', 'o', 't']:
        sys.stderr.write('Error: ' + mode + ': Invalid SPOOL mode.\n')
        sys.exit(-1)
    if len(path) == 0:
        while True:
            conflict = False
            path = ['D{0:0>7}'.format(Config['tmp_id'])]
            Config['tmp_id'] += 1
            # check for file conflict
            for k,v in SPOOL.items():
                if v[2] == path:
                    conflict = True
                    break
            if not conflict:
                break
        
    SPOOL[key] = [[], mode, path]
