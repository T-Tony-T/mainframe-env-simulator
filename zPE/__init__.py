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


# JCL Definition
JCL = {
    # fetched when parsing JCL
    'owner'     : None,         # 'owner_id'
    'jobname'   : None,         # 'job_name'
    'job'       : None,         # 'JOB*****'
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
DISP_ACTION = [ 'KEEP', 'DELETE', 'PASS', 'CATLG', 'UNCATLG' ]
DD_MODE = {
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
                self.__items = {}
                self.__indxs = []

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
                # parse DISP if presented
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

            def key(self, indx):
                return self.__indxs[indx]

            def mode(self, key):
                return DD_MODE[self.__items[key]['DISP'][0]]

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


# JES Definition
JES = {                         # JES storage management map
    'instream'  : 'JES2',       # '// DD *|DATA'
    'outstream' : 'JES2',       # '// DD SYSOUT='
    'file'      : 'SMS',        # '// DD DSN='
    'tmp'       : 'SMS',        # '// DD other'
    }

# converts "ABCD.EFG" to ["ABCD", "EFG"]
def conv_path(fn):
    return re.split('\.', fn)

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

    fp = open_file(sp.fn_list, 'w', sp.f_type)
    cnt = 0
    for line in sp.spool:
        fp.write(line)
        cnt += 1
    return cnt



# Program Supported
PGM_SUPPORTED = {         # all supported programs and their bindings
    'ASSIST'  : 'zPE.pgm.ASSIST.init',
    'IEFBR14' : 'pass',
    }

def LIST_PGM():                # list all supported languages out
    print 'All programs (PGM) that are currently supported:'
    print '  ASSIST     -- Assembler using ASSIST'
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

