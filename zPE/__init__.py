# this is the System Level Definition
# any Subsystem will not effect the behaviour of functions in this file

# modules that will be auto imported
import core, pgm, conf
from core.excptn import *       # pull all exceptions over
from conf import RC             # pull Return Code definition over

import os, sys, re
import pkg_resources


### Diagnostic Function Definition
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

def pkg_info():
    return pkg_resources.require('mainframe-env-simulator')[0]


### Utility Mapping Definition
fmt_name_map   = {    'bw' : 'byte-word',    'hw' : 'half-word',
                      'fw' : 'full-word',    'dw' : 'double-word',
                      }
fmt_align_map  = {    'bw' : 1,    'hw' : 2,    'fw' : 4,    'dw' : 8,    }
align_fmt_map  = {    1 : 'bw',    2 : 'hw',    4 : 'fw',    8 : 'dw',    }


### Utility Function Definition

## constant type conversion

def c2x(src):
    return core.asm.X_.tr(core.asm.C_(src).dump())

def x2c(src):
    return core.asm.C_.tr(core.asm.X_(src).dump())

def b2x(src):
    return core.asm.X_.tr(core.asm.B_(src).dump())

def h2x(src):
    return core.asm.X_.tr(core.asm.H_(src).dump())

def f2x(src):
    return core.asm.X_.tr(core.asm.F_(src).dump())


## interger conversion

def p2i(src):
    return core.asm.P_.tr_val(core.asm.X_(src).dump())

def i2p(src):
    return core.asm.X_.tr(core.asm.P_(str(src)).dump())

def h2i(src):
    return int(src, 16)

def h2i_sign(src):
    res = h2i(src)
    if h2i(src[0]) & 0b1000:    # sign bit on, negative
        res -= ( 0b1 << (len(src) * 4) )
    return res

def i2h(src):
    return re.split(r'[xL]', hex(src))[1].upper()

def i2h_sign(src, precision):
    '''precision is measured in number of hex digits'''
    if src < 0:
        cmp2 = ( 0b1 << (precision * 4) ) + src # 2's complement
        res = i2h(cmp2)
    else:
        res = i2h(src)
    return '{0:0>{1}}'.format(res[-precision:], precision)

def i2i_sign(src, precision_in, precision_out):
    '''precision is measured in number of hex digits'''
    if precision_in == precision_out: # no need to convert
        return src

    cmp2_in   = 0b1 << (precision_in  * 4)
    cmp2_out  = 0b1 << (precision_out * 4)

    mask_in   = cmp2_in  - 1    # all 1s
    mask_out  = cmp2_out - 1    # all 1s

    if precision_in > precision_out: # reduce precision, mask off extra bits
        return src & mask_out

    sign_in = cmp2_in >> 1      # sign bit of src

    if src & sign_in:           # src negative
        src = cmp2_out - ((cmp2_in - src) & mask_in) # 2's complement
    return src & mask_out


## dictionary manipulation

def dic_append_list(dic, key, value):
    if key not in dic:
        dic[key] = []
    dic[key].append(value)

def dic_find_key(dic, val):
    '''Return the (first) key of the dic that has the given val'''
    return [k for (k, v) in dic.iteritems() if v == val][0]


## mask manipulation

def listify_mask(mask_hex):
    '''Convert an (hex) mask to an index list containing positions of 1-bit'''
    mask = '{0:0>4}'.format(bin(int(mask_hex, 16))[2:])
    return [ i for i in range(4) if mask[i] == '1' ]


## string manipulation

def fixed_width_split(width, src_str, flags = 0):
    return re.findall(''.join([ r'.{', str(width), r'}|.+' ]), src_str, flags)

def resplit(pattern, string, skip_l, skip_r, maxsplit = 0):
    '''
    Split the string using the given pattern like re.split(),
    except when the patten is in between skip_l and skip_r.

    There are three pre-defined skip-pattern:
      resplit_sq ==> single quotes
      resplit_dq ==> double quotes
      resplit_pp ==> pair(s) of parentheses


    Note:
      - Only include the chars as they are in skip_l/r.
        do not escape special chars.
        (no '\' unless that is one of the boundary char)
    '''
    if len(skip_l) != len(skip_r):
        raise ValueError
    return __SKIP_SPLIT(pattern, string, skip_l, skip_r, maxsplit)

def resplit_index(split_src, split_fields, field_index):
    indx_s = 0
    for i in range(field_index):
        indx_s = ( split_src.index(split_fields[i], indx_s) + # start pos
                   len(split_fields[i])                       # length
                   )
    return split_src.index(split_fields[field_index], indx_s)

def resplit_sq(pattern, string, maxsplit = 0):
    '''See resplit() for detials'''
    return resplit(pattern, string, "'", "'", maxsplit)

def resplit_dq(pattern, string, maxsplit = 0):
    '''See resplit() for detials'''
    return resplit(pattern, string, '"', '"', maxsplit)

def resplit_pp(pattern, string, maxsplit = 0):
    '''See resplit() for detials'''
    return resplit(pattern, string, '(', ')', maxsplit)


SPOOL_ENCODE_MAP = {
    '\0' : '^@',
    '^'  : '^^',
    }
def spool_encode(src):
    rv = []
    while True:
        res = re.search(r'[\0^]', src)
        if res != None:         # search succeed
            rv.append(src[:res.start()])
            rv.append(SPOOL_ENCODE_MAP[src[res.start():res.end()]])
            src = src[res.end():]
        else:                   # search failed
            rv.append(src)
            break
    return ''.join(rv)

SPOOL_DECODE_MAP = {
    '^@' : '\0',
    '^^' : '^',
    }
def spool_decode(src):
    rv = []
    while True:
        res = re.search(r'\^[@^]', src)
        if res != None:         # search succeed
            rv.append(src[:res.start()])
            rv.append(SPOOL_DECODE_MAP[src[res.start():res.end()]])
            src = src[res.end():]
        else:                   # search failed
            rv.append(src)
            break
    return ''.join(rv)
def spool_decode_printable(src):
    return re.sub(r'[^\x20-\x7e\n]', u'\u220e', spool_decode(src))


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


SPOOL_CTRL_MAP = {
    # ctrl : line spacing
    None : 0,                   # space holder (for EJECT/SPACE N)
    '1'  : 1,                   # single spacing, new page
    ' '  : 1,                   # single spacing
    '0'  : 2,                   # double spacing
    '-'  : 3,                   # triple spacing
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
                 time = None, region = None,
                 parm = ''
                 ):
        if time == None:
            time = conf.Config['time_limit']
        if region == None:
            region = conf.Config['memory_sz']

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
    while not fn_list[0]:       # remove leading empty nodes
        del fn_list[0]
    return '.'.join(fn_list)

def is_file(dsn):
    return os.path.isfile(os.path.join(* dsn))

def is_dir(dsn):
    return os.path.isdir(os.path.join(* dsn))

def is_pds(dsn):                # PDS is currently mapped to flat directory
    return is_dir(dsn)

def open_file(dsn, mode, f_type):
    '''Open the target file in regardless of the existance'''
    return eval(''.join(['core.IO_', JES[f_type], '.open_file']))(dsn, mode)

def fill(sp, path):
    '''Load the indicated SPOOL from the indicated file, treated as FB 80'''
    if sp.mode != 'i':
        return -1

    fp = open_file(path, 'rb', 'file')
    content = fp.read()         # read the entire file as binary
    fp.close()

    if re.search(r'[^\x0a\x0d\x20-\x7e]', content):
        # turely binary file, treated as Fixed-Block 80
        lines = fixed_width_split(80, content, re.S) # S for . to match all
    else:
        # actually ascii file, break lines on \r, \n, or both
        lines = re.split(r'\r\n|\r|\n', content)
        if not lines[-1]:
            lines.pop()         # remove empty line at the end, if any
    for line in lines:
        sp.append(line, '\n')
    return len(line)

def flush(sp):
    '''Flush the indicated SPOOL to the indicated file'''
    if sp.mode == 'i':
        return -1

    mode = 'w'
    for line in sp.spool:
        if '\0' in line:        # is binary file
            mode = 'wb'
            break
    fp = open_file(sp.real_path, mode, sp.f_type)

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

def __SKIP_SPLIT(pattern, string, skip_l, skip_r, maxsplit = 0):
    '''skip_l/r must be iterable items with corresponding pairs of dlms'''
    rv = []
    reminder = re.findall('.', string)
    current  = []               # current parsing part
    current_splitable = []      # ground level of current parsing part
    current_splitless = []      # upper levels of current parsing part
    expected = []               # expected dlm stack

    while reminder:
        if maxsplit:
            split_quota = maxsplit - len(rv)
        else:
            split_quota = 0
        next_char = reminder.pop(0)

        if split_quota >= 0:
            # more to go
            if expected:
                # waiting for ending dlm, no checking for pattern
                if next_char == expected[-1]:
                    # ending dlm encountered, return previous level
                    expected.pop()
                elif next_char in skip_l:
                    # starting dlm encountered, goto next level
                    expected.append(skip_r[skip_l.index(next_char)])
                current_splitless.append(next_char)

            elif next_char in skip_l:
                # starting dlm first encountered, check current
                if current:
                    res = re.split(
                        pattern,
                        ''.join(current_splitable),
                        split_quota
                        )
                    if len(res) > 1:
                        res[0] = ''.join(current_splitless + res[:1])
                        rv.extend(res[:-1])

                        current = res[-1:]
                        current_splitable = []
                        current_splitless = res[-1:]
                    else:
                        current_splitless.extend(current_splitable)
                        current_splitable = []
                # go to next level
                current_splitless.append(next_char)
                expected.append(skip_r[skip_l.index(next_char)])

            else:
                # ground level
                current_splitable.append(next_char)

            current.append(next_char)
        else:
            # reach length limit
            break

    if maxsplit:
        split_quota = maxsplit - len(rv)
    else:
        split_quota = 0
    if split_quota >= 0  and  current:
        res = re.split(pattern, ''.join(current_splitable), split_quota)
        if len(res) > 1:
            res[0] = ''.join(current_splitless + res[:1])
            rv.extend(res[:-1])
            reminder = res[-1:] + reminder
        else:
            reminder = current + reminder
    else:
        reminder = current + reminder
    rv.append(''.join(reminder))
    return rv
