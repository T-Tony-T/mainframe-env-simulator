# this is the System Level Definition
# any Subsystem will not effect the behaviour of functions in this file

# modules that will be auto imported
import core, pgm

import os, sys, pickle
import re

### Architectural Definition

JOB_ID_MIN = 10000              # the smallest job ID
JOB_ID_MAX = 65535              # the largest job ID
TMP_FILE_ID = 101               # the smallest tmp file identifier

def bad_label(label):
    if len(label) == 0:
        return None             # no lable
    if len(label) > 8:
        return True             # label too long
    if re.match('[A-Z@#$][A-Z@#$0-9]+', label).group(0) != label:
        return True             # illegal character
    return False

## Return Code
RC = {
    'NORMAL'    : 0,
    'WARNING'   : 4,
    'ERROR'     : 8,
    'SERIOUS'   : 12,
    'SEVERE'    : 16,
    }



### Program Definition

## Identifier
SYSTEM = {
    'SYS'       : 'ZSUB',
    'SYST'      : 'Z S U B',
    'JES'       : 'JES2',
    'JEST'      : 'J E S 2',
    'NODE'      : 'ZPE@NIU',
    'NODET'     : 'Z P E @ N I U',
    }

## Configurable Definition
DEFAULT = {
    'ADDR_MODE' : 31,           # hardware addressing mode: 31 bit

    'MEMORY_SZ' : '1024K',      # memory size: 1024 KB
    'MEM_MAX'   : 1048576,      # 1024K = 1024 * 1024 = 1048576

    'LN_P_PAGE' : 60,           # line per page for output

    'SPOOL_DIR' : '',           # SPOOL positon: current directory

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
    'spool_dir' : DEFAULT['SPOOL_DIR'],
    'spool_path': None,         # will be set after JOB card is read
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

        elif k == 'spool_dir':
            if os.path.isdir(v[:-1]):
                Config['spool_dir'] = v[:-1]
            else:
                sys.stderr.write('Warning: ' + v[:-1] +
                                 ': Invalid SPOOL dir path.\n')

    Config['addr_max'] = 2 ** Config['addr_mode']
    __TOUCH_RC()


## JCL Definition
JCL = {
    # fetched when parsing JCL
    'jobname'   : None,         # 'job_name'
    'owner'     : None,         # the first 7 chars of jobname
    'class'     : None,         # the last char of jobname
    'accinfo'   : None,         # the accounting information
    'pgmer'     : None,         # the name of the programmer
    'jobid'     : None,         # 'JOB*****'
    'jobstat'   : None,         # the status of the job
    'jobstart'  : None,         # time object
    'jobend'    : None,         # time object
    'step'      : [],           # each item is of type "Step"
    'read_cnt'  : 0,            # lines read in
    'card_cnt'  : 0,            # cards read in
    }

DD_STATUS = { 'init' : 0, 'normal' : 1, 'abnormal' : 2 }
DISP_STATUS = {                 # status : action_normal
    'NEW' : 'DELETE',
    'OLD' : 'KEEP',
    'SHR' : 'KEEP',
    'MOD' : 'KEEP',
    }
DISP_ACTION = {                 # action : display
    'KEEP'      : 'RETAINED',
    'DELETE'    : 'DELETED',
    'PASS'      : 'PASSED',
    'CATLG'     : 'CATLGED',
    'UNCATLG'   : 'UNCATLGED',
    }
DD_MODE = {                     # DD mode : SPOOL mode
    'NEW' : 'o',
    'OLD' : 'o',
    'SHR' : 'i',
    'MOD' : '+',
    }

class Step(object):             # for JCL['step'][*]
    def __init__(self, name, pgm = '', proc = '', parm = ''):
        # begining of inner class definition
        class DDlist(object):   # inner class for JCL['step'][*].dd
            def __init__(self):
                self.__items = {} # { ddname : { 'DSN' : '*', 'DISP' = [,,] } }
                self.__indxs = [] # [ ddname ]

            def append(self, ddname, ddcard):
                if not isinstance(ddname, str):
                    sys.stderr.write('Error: ' + ddname +
                                     ': Invalid DD name.\n')
                    sys.exit(44)
                if ddname in self.__items:
                    sys.stderr.write('Error: ' + ddname +
                                     ': Duplicated DD names.\n')
                    sys.exit(44)
                for k,v in ddcard.items():
                    if k not in ['SYSOUT', 'DSN', 'DISP']:
                        sys.stderr.write('Error: ' + k + '=' + v +
                                         ': Un-recognized option\n')
                        sys.exit(44)
                # parse DISP
                if ddcard['DISP'] != '':
                    if ddcard['DISP'][0] == '(':
                        disp = re.split(',', ddcard['DISP'][1:-1])
                    else:
                        disp = [ddcard['DISP']]
                    if disp[0] not in DISP_STATUS:  # check status
                        sys.stderr.write('Error: ' + disp[0] +
                                         ': Invalid DISP status.\n')
                        sys.exit(41)
                    if len(disp) == 1:              # check normal
                        disp.append(DISP_STATUS[disp[0]])
                    if disp[1] not in DISP_ACTION:
                        sys.stderr.write('Error: ' + disp[1] +
                                         ': Invalid DISP action.\n')
                        sys.exit(41)
                    if len(disp) == 2:              # check abnormal
                        disp.append(disp[1])
                    if disp[2] not in DISP_ACTION:
                        sys.stderr.write('Error: ' + disp[2] +
                                         ': Invalid DISP action.\n')
                        sys.exit(41)
                    ddcard['DISP'] = disp
                else:
                    ddcard['DISP'] = ['','','']
                # add STAT
                ddcard['STAT'] = DD_STATUS['init']
                self.__items[ddname] = ddcard
                self.__indxs.append(ddname)

            def remove(self, key):
                if isinstance(key, str):
                    del self.__items[key]
                    self.__indxs.remove(key)
                elif isinstance(key, int):
                    del self.__items[self.__indxs.pop(key)]
                else:
                    sys.stderr.write('Error: ' + key +
                                     ': Invalid key/index.\n')
                    sys.exit(44)

            def dict(self):
                return self.__items

            def list(self):
                return self.__indxs

            def index(self, key):
                return self.__indxs.index(key)

            def key(self, indx):
                return self.__indxs[indx]

            def mode(self, key):
                return DD_MODE[self.__items[key]['DISP'][0]]

            def get_act(self, key, rc = 0):
                if rc == 0:
                    return self.__items[key]['DISP'][1]
                else:
                    return self.__items[key]['DISP'][2]

            def __len__(self):
                return len(self.__indxs)

            def __getitem__(self, key):
                if isinstance(key, str):
                    return self.__items[key]
                elif isinstance(key, int):
                    return self.__items[self.__indxs[key]]
                else:
                    sys.stderr.write('Error: ' + key +
                                     ': Invalid key/index.\n')
                    sys.exit(44)

            def __setitem__(self, key, val):
                if isinstance(key, str):
                    if key not in self.__items:
                        sys.stderr.write('Error: ' + key +
                                         ': DD name not found.\n')
                        sys.exit(44)
                    self.__items[key] = val
                elif isinstance(key, int):
                    self.__items[self.__indxs[key]] = val
                else:
                    sys.stderr.write('Error: ' + key +
                                     ': Invalid key.\n')
                    sys.exit(44)
        # end of inner class definition

        self.name = name        # 'step_name'
        self.pgm = pgm          # PGM='pgm_name'
        self.proc = proc        # [PROG=]'prog_name'
        self.procname = ''      # not applied now
        self.parm = parm        # PARM=(parm_list)
        self.start = None       # time object
        self.rc = None          # return code
        self.dd = DDlist()
# end of Step Definition


## JES Definition
JES = {                         # JES storage management map
    'instream'  : 'JES2',       # '// DD *|DATA'
    'outstream' : 'JES2',       # '// DD SYSOUT='
    'file'      : 'SMS',        # '// DD DSN='
    'tmp'       : 'SMS',        # '// DD other'
    }

# converts "ABCD.EFG" to ["ABCD", "EFG"]
def conv_path(fn):
    return re.split('\.', fn)

def conv_back(fn_list):
    return '.'.join(fn_list)

def is_file(dsn):
    return os.path.isfile(os.path.join(* dsn))

def is_dir(dsn):
    return os.path.isdir(os.path.join(* dsn))

# open the target file in regardless of the existance
def open_file(dsn, mode, f_type):
    return eval('core.' + JES[f_type] + '.open_file')(dsn, mode)

# flush the indicated SPOOL to the indicated File
def flush(sp):
    if sp.mode == 'i':
        return -1

    fp = open_file(sp.zPEfn, 'w', sp.f_type)
    cnt = 0
    for line in sp.spool:
        fp.write(line)
        cnt += 1
    return cnt


## Program Supported
PGM_SUPPORTED = {         # all supported programs and their bindings
    'ASSIST'    : 'zPE.pgm.ASSIST.init',

    'IEFBR14'   : 'zPE.pgm.IEFBR14.init',
    }

def LIST_PGM():                # list all supported languages out
    print 'All programs (PGM) that are currently supported:'
    print '  ASSIST     -- Assembler using ASSIST'
    print
    print 'Utilities:'
    print '  IEFBR14    -- System utility that DO NOTHING'
    print


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

