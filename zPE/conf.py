# this is the System Level Configuration

from core.mem import parse_region

import os, sys, pickle
import re


### Architectural Definition
JOB_ID_MIN = 10000              # the smallest job ID
JOB_ID_MAX = 65535              # the largest job ID
TMP_FILE_ID = 101               # the smallest tmp file identifier


### Configurable Definition
POSSIBLE_ADDR_MODE = [ 16, 31, 64, ]

DEFAULT = {
    'ADDR_MODE' : 31,           # hardware addressing mode: 31 bit

    'MEMORY_SZ' : '1024K',      # memory size: 1024 KB

    'LN_P_PAGE' : 60,           # line per page for output

    'SPOOL_DIR' : '.',          # SPOOL positon: current directory

    'ICH70001I' : {             # config list for ICH70001I
        'atime' : '00:00:00 ON THURSDAY, JANUARY 18, 2011',
                                # the start time of this project
        },
    }

Config = { }

def init_rc():
    Config['job_id']     = JOB_ID_MIN
    Config['tmp_id']     = TMP_FILE_ID  # next available tmp file identifier

    Config['addr_mode']  = DEFAULT['ADDR_MODE']
    Config['addr_max']   = 0            # calculate on loading

    Config['memory_sz']  = DEFAULT['MEMORY_SZ']
                                # can be altered by "// JOB ,*,REGION=*"
                                # can be overridden by "// EXEC *,REGION=*"

    Config['spool_dir']  = DEFAULT['SPOOL_DIR']
    Config['spool_path'] = None # the folder that contains all SPOOL output
                                # for a specific JOB;
                                # will be set after JOB card is read


CONFIG_PATH = {
    'dir'       : os.path.join(os.environ['HOME'], '.zPE'),
    'rc'        : os.path.join(os.environ['HOME'], '.zPE', 'config'),
    'data'      : os.path.join(os.environ['HOME'], '.zPE', 'data'),
    'ICH70001I' : os.path.join(os.environ['HOME'], '.zPE', 'data', 'ICH70001I'),
    }

def dump_ICH70001I(conf):
    __CK_CONFIG()
    __TOUCH_ICH70001I(conf)
    
def load_ICH70001I():
    __CK_CONFIG()
    return pickle.load(open(CONFIG_PATH['ICH70001I'], 'rb'))
    

def read_rc(dry_run = False):
    __CK_CONFIG()
    init_rc()

    for line in open(CONFIG_PATH['rc'], 'r'):
        (k, v) = re.split('[ \t]*=[ \t]*', line, maxsplit=1)
        ok = False

        if k == 'job_id':
            try:
                Config[k] = int(v)
                if not dry_run:
                    Config[k] += 1 # increment the ID number

                if JOB_ID_MIN < Config[k] and Config[k] < JOB_ID_MAX:
                    ok = True
            except ValueError:
                pass

            if not ok:
                Config[k] = JOB_ID_MIN
                sys.stderr.write('CONFIG WARNING: ' + v[:-1] +
                                 ': Invalid job ID.\n')
        elif k == 'addr_mode':
            try:
                Config[k] = int(v)
                if Config[k] in POSSIBLE_ADDR_MODE:
                    ok = True
            except ValueError:
                pass

            if not ok:
                Config[k] = DEFAULT['ADDR_MODE']
                sys.stderr.write('CONFIG WARNING: ' + v[:-1] +
                                 ': Invalid address mode.\n')
        elif k == 'memory_sz':
            try:
                Config[k] = parse_region(v)
                ok = True
            except SyntaxError as e_msg:
                sys.stderr.write('CONFIG WARNING: {0}: \n  {1}\n'.format(v[:-1], e_msg))
            except ValueError as e_msg:
                sys.stderr.write('CONFIG WARNING: {0}: \n  {1}\n'.format(v[:-1], e_msg))

            if not ok:
                Config[k] = DEFAULT['MEMORY_SZ']
        elif k == 'spool_dir':
            path = os.path.normpath(os.path.normcase(v[:-1]))
            if os.path.isdir(os.path.abspath(os.path.expanduser(path))):
                Config['spool_dir'] = path
            else:
                sys.stderr.write('Warning: ' + v[:-1] +
                                 ': Invalid SPOOL dir path.\n')
                Config[k] = DEFAULT['SPOOL_DIR']

    Config['addr_max'] = 2 ** Config['addr_mode']
    write_rc()

def write_rc():
    __TOUCH_RC()


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
    if Config['spool_dir'] != '':
        fp.write('spool_dir = ' + Config['spool_dir'] + '\n')
    fp.close()
