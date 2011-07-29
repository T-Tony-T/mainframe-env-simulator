# this is the System Level Definition
# any Subsystem will not effect the behaviour of functions in this file

# modules that will be auto imported
import core, pgm, conf

import os, sys
import re

### Diagnostic Function Definition
def abort(rc, *msg):
    '''
    Abort the entire program with the given return code and
    error message.

    Suggested Return Code:
       0: normal end
       1: currently not supported
       5: SPOOL error
       9: JCL error
      90: Assembler pass 1 error
      92: Assembler pass 2 error
      -1: zPE error
    '''
    sys.stderr.write(''.join(msg))
    sys.exit(rc)

def mark4future(feature):
    '''Mark the function as \"not implemented\".'''
    abort(1, ''.join(['\n\n!!! ', feature, ': feature not supported !!!\n\n']))


### Utility Function Definition
def dic_find_key(dic, val):
    '''Return the (first) key of the dic that has the given val'''
    return [k for k, v in dic.iteritems() if v == val][0]

def resplit_sq(pattern, string, maxsplit = 0):
    '''See resplit() for detials'''
    return resplit(pattern, string, "'", "'", maxsplit)

def resplit_dq(pattern, string, maxsplit = 0):
    '''See resplit() for detials'''
    return resplit(pattern, string, '"', '"', maxsplit)

def resplit_sp(pattern, string, maxsplit = 0):
    '''See resplit() for detials'''
    return resplit(pattern, string, '(', ')', maxsplit)

def resplit(pattern, string, skip_l, skip_r, maxsplit = 0):
    '''
    Split the string using the given pattern like re.split(),
    except when the patten is in between skip_l and skip_r.

    There are three pre-defined skip-pattern:
      resplit_sq ==> single quotes
      resplit_dq ==> double quotes
      resplit_sp ==> single pair of parentheses


    Note: 
      - Only include the chars as they are in skip_l/r.
        do not escape special chars.
        (no '\' unless that is one of the boundary char)

      - If the pattern contains the "skip pattern", then
        the functions behaves exactly the same as re.split()
    '''
    if len(skip_l) != len(skip_r):
        raise ValueError
    for ch in skip_l:
        if ch in pattern:
            return re.split(pattern, string, maxsplit)
    for ch in skip_r:
        if ch in pattern:
            return re.split(pattern, string, maxsplit)
    return __SKIP_SPLIT(pattern, string, skip_l, skip_r, maxsplit)


### Architectural Definition

def bad_label(label):
    '''
    Return:
      - the position (start at 1) of the first invalid char
      - 0 if all good
      - None if no label
    '''
    if len(label) == 0:
        return None             # no lable
    if len(label) > 8:
        return 9                # label too long
    if not re.match('[A-Z@#$]', label[0]):
        return 1                # first character not legal
    for indx in range(1, len(label)):
        if not re.match('[A-Z@#$0-9]', label[indx]):
            return indx         # (indx+1)th character not legal
    return 0                    # all good


## Return Code
RC = conf.RC



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


## JCL Definition
JCL = {
    # fetched when parsing JCL
    'jobname'   : None,         # 'job_name'
    'owner'     : None,         # the first 7 chars of jobname
    'class'     : None,         # the last char of jobname
    'accinfo'   : None,         # the accounting information
    'pgmer'     : None,         # the name of the programmer
    'regoin'    : None,         # the regoin of the entire job
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
    def __init__(self, name, pgm, proc,
                 region = None,
                 parm = ''
                 ):
        if region == None:
            region = conf.Config['memory_sz']

        # begining of inner class definition
        class DDlist(object):   # inner class for JCL['step'][*].dd
            def __init__(self):
                self.__items = {} # { ddname : { 'DSN' : '*', 'DISP' = [,,] } }
                self.__indxs = [] # [ ddname ]

            def append(self, ddname, ddcard):
                if not isinstance(ddname, str):
                    abort(9, 'Error: ', ddname, ': Invalid DD name.\n')
                if ddname in self.__items:
                    abort(9, 'Error: ', ddname, ': Duplicated DD names.\n')
                for k,v in ddcard.iteritems():
                    if k not in ['SYSOUT', 'DSN', 'DISP']:
                        abort(9, 'Error: ', k, '=', v,
                              ': Un-recognized option\n')
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
                self.__items[ddname] = ddcard
                self.__indxs.append(ddname)

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
                    abort(9, 'Error: ', key, ': Invalid key/index.\n')

            def __setitem__(self, key, val):
                if isinstance(key, str):
                    if key not in self.__items:
                        abort(9, 'Error: ', key, ': DD name not found.\n')
                    self.__items[key] = val
                elif isinstance(key, int):
                    self.__items[self.__indxs[key]] = val
                else:
                    abort(9, 'Error: ', key, ': Invalid key.\n')
        # end of inner class definition

        self.name = name        # 'step_name'
        self.pgm = pgm          # PGM='pgm_name'
        self.proc = proc        # [PROG=]'prog_name'
        self.procname = ''      # not applied now
        self.region = region    # REGION=xxxx[K|M]
        self.parm = parm        # PARM='parm_list'
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

def conv_path(fn):
    '''Converts "ABCD.EFG" to ["ABCD", "EFG"]'''
    return re.split('\.', fn)

def conv_back(fn_list):
    '''Converts ["ABCD", "EFG"] to "ABCD.EFG"'''
    return '.'.join(fn_list)

def is_file(dsn):
    return os.path.isfile(os.path.join(* dsn))

def is_dir(dsn):
    return os.path.isdir(os.path.join(* dsn))

def open_file(dsn, mode, f_type):
    '''Open the target file in regardless of the existance'''
    return eval(''.join(['core.', JES[f_type], '.open_file']))(dsn, mode)

def flush(sp):
    '''Flush the indicated SPOOL to the indicated file'''
    if sp.mode == 'i':
        return -1

    fp = open_file(sp.real_path, 'w', sp.f_type)
    cnt = 0
    for line in sp.spool:
        fp.write(line)
        cnt += 1
    fp.close()
    return cnt


## Program Supported
PGM_SUPPORTED = {         # all supported programs and their bindings
    'ASMA90'    : 'zPE.pgm.ASMA90.init',
    'ASSIST'    : 'zPE.pgm.ASSIST.init',
    'HEWLDRGO'  : 'zPE.pgm.HEWLDRGO.init',
    'LOADER'    : 'zPE.pgm.HEWLDRGO.init', # alias to HEWLDRGO

    'IEFBR14'   : 'zPE.pgm.IEFBR14.init',
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


### Supporting Function

def __SKIP_SPLIT(pattern, string, skip_l, skip_r, maxsplit):
    true_pttn = '^[^{0}{1}]*?(?:(?:'.format(
        ''.join(skip_l), ''.join(skip_r)
        )
    for indx in range(len(skip_l)):
        true_pttn += '(?:[{0}][^{0}{1}]*[{1}])|'.format(
            skip_l[indx], skip_r[indx]
            )
    true_pttn = true_pttn[:-1]  # remove the last '|'
    true_pttn += ')[^{0}{1}]*?)*({2})'.format(
        ''.join(skip_l), ''.join(skip_r), pattern
        )

    rv = []
    reminder = string

    while True:
        if (maxsplit == 0) or len(rv) < maxsplit:
            # more to go
            res = re.search(true_pttn, reminder)
            if res != None:     # search succeed
                rv.append(reminder[:res.start(1)])
                reminder = reminder[res.end(1):]
            else:               # search failed
                rv.append(reminder)
                break
        else:
            # reach length limit
            rv.append(reminder)
            break
    return rv
