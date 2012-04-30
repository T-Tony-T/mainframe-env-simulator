# this file defines the global configuarion and resources

import sys, os
import re

### Diagnostic Function Definition
RC = {
    'NORMAL'	: 0,            # Information
    'NOTIFY'    : 2,            # Notification
    'WARNING'	: 4,            # Warning
    'ERROR'	: 8,            # Error
    'SEVERE'	: 12,           # Severe Error
    'CRITICAL'	: 16,           # Critical Error
    'UNABLE'	: 20,           # Unable to Preceed
    }

DEBUG_MODE = [ False ]
def debug_mode(enable_debug = None):
    if enable_debug == None:
        return DEBUG_MODE[0]
    else:
        DEBUG_MODE[0] = enable_debug

def warn(*msg):
    sys.stderr.write(''.join(msg))

def abort(rc, *msg):
    '''
    Abort the entire program with the given return code and
    error message.

    Suggested Return Code:
       0: normal end
       1: currently not supported
       5: SPOOL error
       9: JCL error
      13: Linkage-Editor error
      90: Macro Pre-Processor error
      91: Assembler pass 1 error
      92: Assembler pass 2 error
      -1: zPE error
    '''
    sys.stderr.write(''.join(msg))
    sys.exit(rc)

def mark4future(feature):
    '''Mark the function as \"not implemented\".'''
    abort(1, ''.join(['\n\n!!! ', feature, ': feature not supported !!!\n\n']))



### Environment Variables

CONFIG_PATH = {
    'dir'       : os.path.join(os.path.expanduser('~'), '.zPE'),
    'rc'        : os.path.join(os.path.expanduser('~'), '.zPE', 'config'),
    'data'      : os.path.join(os.path.expanduser('~'), '.zPE', 'data'),
    'ICH70001I' : os.path.join(os.path.expanduser('~'), '.zPE', 'data', 'ICH70001I'),
    'SPOOL'     : os.path.join(os.path.expanduser('~'), '.zPE', 'data', 'SPOOL.sqlite'),
    }


### Program Definition

## Utility Mapping Definition
fmt_name_map   = {    'bw' : 'byte-word',    'hw' : 'half-word',
                      'fw' : 'full-word',    'dw' : 'double-word',
                      }
fmt_align_map  = {    'bw' : 1,    'hw' : 2,    'fw' : 4,    'dw' : 8,    }
align_fmt_map  = {    1 : 'bw',    2 : 'hw',    4 : 'fw',    8 : 'dw',    }


## Configuarion of the Simulator
Config = { }       # 'job_id' and 'tmp_id' should not be modified manually


## Regeister Definition
GPR_NUM = 16                    # number of general purpose registers

GPR = [ ]                       # general purpose registers
SPR = { }                       # special purpose registers


## SPOOL Pool
SP_MODE = {                     # SPOOL mode : display
    'i' : 'SYSIN',
    'o' : 'SYSOUT',
    '+' : 'KEPT',
    }

SP_DEFAULT     = [ 'JESMSGLG', 'JESJCL', 'JESYSMSG' ] # System Managed SPOOL
SP_DEFAULT_OUT = [ 'JESMSGLG', 'JESJCL', 'JESYSMSG' ] # SPOOLs that will be write out at the end
SP_DEFAULT_OUT_STEP = { # step name corresponding to the above list
    'JESMSGLG' : 'JES',
    'JESJCL'   : 'JES',
    'JESYSMSG' : 'JES',
    }

SPOOL = { }

SPOOL_CTRL_MAP = {
    # ctrl : line spacing
    None : 0,                   # space holder (for EJECT/SPACE N)
    '1'  : 1,                   # single spacing, new page
    ' '  : 1,                   # single spacing
    '0'  : 2,                   # double spacing
    '-'  : 3,                   # triple spacing
    }

## Identifier
SYSTEM = {
    'SYS'       : 'ZSUB',
    'SYST'      : 'Z S U B',
    'JES'       : 'JES2',
    'JEST'      : 'J E S 2',
    'NODE'      : 'ZPE@NIU',
    'NODET'     : 'Z P E @ N I U',
    }


## JCL Definition
JCL = {
    # fetched when parsing JCL
    'jobname'   : None,         # 'job_name'
    'owner'     : None,         # the first 7 chars of jobname
    'class'     : None,         # the last char of jobname
    'accinfo'   : None,         # the accounting information
    'pgmer'     : None,         # the name of the programmer
    'time'      : None,         # the estimated amount of CPU time needed
    'regoin'    : None,         # the regoin of the entire job
    'jobid'     : None,         # 'JOB*****'
    'spool_path': '',           # the path that all tmp files are allocated
    'jobstat'   : None,         # the status of the job
    'jobstart'  : None,         # timestamp
    'jobend'    : None,         # timestamp
    'step'      : [],           # each item is of type "JobStep"
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

class JobStep(object):          # for JCL['step'][*]
    def __init__(self, name, pgm, proc,
                 time = None, region = None,
                 parm = ''
                 ):
        if time == None:
            time = Config['time_limit']
        if region == None:
            region = Config['memory_sz']

        # begining of inner class definition
        class DDlist(object):   # inner class for JCL['step'][*].dd
            def __init__(self):
                self.__items = {} # { ddname : [ { 'DSN' : '*', 'DISP' = [,,] },
                                  #              { ... }, # concatenated DD
                                  #              ] }
                self.__indxs = [] # [ ddname ]

            def append(self, ddname, ddcard, tmp_sp):
                if not isinstance(ddname, str):
                    abort(9, 'Error: ', ddname, ': Invalid DD name.\n')
                if ddname in self.__items:
                    abort(9, 'Error: ', ddname, ': Duplicated DD names.\n')
                for (k, v) in ddcard.iteritems():
                    if k not in ['SYSOUT', 'DSN', 'DISP']:
                        abort(9, 'Error: ', k, '=', v,
                              ': Un-recognized option\n')
                ddcard['TMP_SP'] = tmp_sp

                # parse DISP
                if ddcard['DISP'] != '':
                    if ddcard['DISP'][0] == '(':
                        disp = re.split(',', ddcard['DISP'][1:-1])
                    else:
                        disp = [ddcard['DISP']]
                    if disp[0] not in DISP_STATUS:  # check status
                        abort(9, 'Error: ', disp[0], ': Invalid DISP status.\n')
                    if len(disp) == 1:              # check normal
                        disp.append(DISP_STATUS[disp[0]])
                    if disp[1] not in DISP_ACTION:
                        abort(9, 'Error: ', disp[1], ': Invalid DISP action.\n')
                    if len(disp) == 2:              # check abnormal
                        disp.append(disp[1])
                    if disp[2] not in DISP_ACTION:
                        abort(9, 'Error: ', disp[2], ': Invalid DISP action.\n')
                    ddcard['DISP'] = disp
                else:
                    ddcard['DISP'] = ['','','']
                # add STAT
                ddcard['STAT'] = DD_STATUS['init']
                if ddname:      # new dd
                    self.__indxs.append(ddname)
                    self.__items[ddname] = [ ddcard ]
                else:           # dd concatenation
                    self.__indxs.append(self.__indxs[-1])
                    self.__items[self.__indxs[-1]].append(ddcard)

            def remove(self, key):
                if isinstance(key, str):
                    del self.__items[key]
                    self.__indxs.remove(key)
                elif isinstance(key, int):
                    del self.__items[self.__indxs.pop(key)]
                else:
                    abort(9, 'Error: ', key, ': Invalid key/index.\n')

            def dict(self):
                return self.__items

            def list(self):
                return self.__indxs

            def is_concat(self, key):
                return (len(self.__getitem__(key)) > 1)

            def index(self, key):
                return self.__indxs.index(key)

            def key(self, indx):
                return self.__indxs[indx]

            def mode(self, key):
                ddcard = self.__items[key]
                if len(ddcard) == 1:
                    return DD_MODE[ddcard[0]['DISP'][0]]
                else:
                    return DD_MODE['SHR'] # concatenated DDs, read-only

            def get_act(self, key, rc = 0):
                ddcard = self.__items[key]
                if len(ddcard) > 1:
                    return 'DELETE' # concatenated DDs, DELETE no matter what
                if rc == 0:
                    return ddcard[0]['DISP'][1]
                else:
                    return ddcard[0]['DISP'][2]

            def __len__(self):
                return len(self.__items)

            def __getitem__(self, key):
                if isinstance(key, str):
                    return self.__items[key]
                elif isinstance(key, int):
                    return self.__items[self.__indxs[key]]
                else:
                    abort(9, 'Error: ', key, ': Invalid key/index.\n')

            def __setitem__(self, key, val):
                if isinstance(key, str):
                    if key not in self.__items:
                        abort(9, 'Error: ', key, ': DD name not found.\n')
                elif isinstance(key, int):
                    key = self.__indxs[key]
                else:
                    abort(9, 'Error: ', key, ': Invalid key.\n')
                # perform the replacement
                cnt = self.__indxs.count(key)
                if cnt > 1:     # concatenated DDs
                    indx = self.__indxs.index(key)
                    for i in range(cnt): # remove all dd name indexing
                        self.__indxs.remove(key)
                    self.__indxs.insert(indx, key) # add back the index
                self.__items[key] = [ val ]
        # end of inner class definition

        self.name = name        # 'step_name'
        self.pgm  = pgm         # PGM='pgm_name'
        self.proc = proc        # [PROG=]'prog_name'
        self.procname = ''      # not applied now
        self.time = time        # TIME=(m,s)
        self.region = region    # REGION=xxxx[K|M]
        self.parm = parm        # PARM='parm_list'
        self.start = None       # timestamp
        self.end   = None       # timestamp
        self.rc = None          # return code
        self.dd = DDlist()
# end of JobStep Definition


## JES Definition

JES = {                         # JES storage management map
    'instream'  : 'JES2',       # '// DD *|DATA'
    'outstream' : 'JES2',       # '// DD SYSOUT='
    'file'      : 'SMS',        # '// DD DSN='
    'tmp'       : 'SMS',        # '// DD other'
    }


### Program Supported
PGM_SUPPORTED = {         # all supported programs and their bindings
    'ASMA90'    : 'zPE.base.pgm.ASMA90.init',
    'ASSIST'    : 'zPE.base.pgm.ASSIST.init',
    'HEWLDRGO'  : 'zPE.base.pgm.HEWLDRGO.init',
    'LOADER'    : 'zPE.base.pgm.HEWLDRGO.init', # alias to HEWLDRGO

    'IEFBR14'   : 'zPE.base.pgm.IEFBR14.init',
    }

def LIST_PGM():
    '''List all supported languages out'''
    print 'All programs (PGM) that are currently supported:'
    print '  ASMA90     -- High-Level Assembler'
    print '  ASSIST     -- ASSIST Assembler'
    print '  HEWLDRGO   -- Loader'
    print
    print 'Utilities:'
    print '  IEFBR14    -- System utility that DOES NOTHING'
    print
