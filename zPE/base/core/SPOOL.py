# this is a simplification of the
# "Simultaneous Peripheral Operations OnLine"

# in future, may switch to "mmap"

from zPE.util.global_config import *
import zPE.util.spool

import IO_JES2, IO_SMS

import sys                      # for sys.maxsize
import re


## Simultaneous Peripheral Operations On-line
class Spool(object):
    def __init__(self, spool, spdid, mode, f_type, virtual_path, real_path):
        self.spool = spool      # [ line_1,  line_2,  ... ]
        self.spdid = spdid      # [ ln_id_1, ln_id_2, ... ] // deck id
                                # digit (line number) for input SPOOL
                                # label (tp-label) for expanded input
                                # none for output SPOOL
        # the above two need to be in sync (if modifiey manually)
        self.mode = mode        # one of the SP_MODE keys
        self.f_type = f_type    # one of the JES keys
        self.virtual_path = virtual_path
                                # path recognized within zPE;
                                # [ dir_1, dir_2, ... , file ]
        self.real_path = real_path
                                # path in the actual file system;
                                # same format as above

    # the following methods are for Spool.spool
    def empty(self):
        return (self.__len__() == 0)


    def append(self, *phrase, **option):
        self.insert(sys.maxsize, *phrase, **option)

    def insert(self, indx, *phrase, **option):
        self.spool.insert(indx, ''.join(phrase))
        if 'deck_id' not in option:
            option['deck_id'] = None
        self.spdid.insert(indx, option['deck_id'])

    def pop(self, indx = -1):
        line = self.spool.pop(indx)
        did  = self.spdid.pop(indx)
        return ( line, did, )

    def push(self, pop_res, indx = sys.maxsize):
        self.spool.insert(indx, pop_res[0])
        self.spdid.insert(indx, pop_res[1])


    def __str__(self):
        return ''.join([
                'mode : ',   self.mode,
                ', type : ', self.f_type,
                ', v_fn : ', str(self.virtual_path),
                ', r_fn : ', str(self.real_path)
                ])

    def __len__(self):
        return len(self.spool)

    def __getitem__(self, key):
        if isinstance(key, int):        # key = ln
            return self.spool[key]
        else:                           # key = (ln, indx/slice)
            return self.spool[key[0]][key[1]]

    def deck_id(self, key):
        return self.spdid[key]

    def __setitem__(self, key, val):
        if isinstance(key, int):        # key = ln
            self.spool[key] = val
        else:
            if isinstance(key[1], int): # key = (ln, indx)
                in_s = key[1]
                while in_s < 0:
                    in_s += len(self.spool[key[0]])
                in_e = in_s + 1
            else:                       # key = (ln, slice)
                (in_s, in_e, step) = key[1].indices(len(self.spool[key[0]]))
            self.spool[key[0]] = '{0}{1}{2}'.format(
                self.spool[key[0]][:in_s],
                val,
                self.spool[key[0]][in_e:]
                )
# end of Spool Definition


## Initialize the default SPOOL
for k in SP_DEFAULT_OUT:
    if k not in SPOOL:
        SPOOL[k] = Spool([], [], 'o', 'outstream', None, [k])


## Interface Functions
def pop_new(key, mode, f_type, path = [], real_path = []):
    sp = new(key, mode, f_type, path, real_path)
    remove(key)
    return sp

def new(key, mode, f_type, path = [], real_path = []):
    # check uniqueness
    if key in SPOOL:
        if ( (f_type == 'file') and (mode in ['i', '+']) and
             (path == path_of[key]) and (real_path == real_path_of(key))
             ):
            return SPOOL[key]   # passed from previous step
        abort(5, 'Error: ', key, ': SPOOL name conflicts.\n')

    # check SPOOL mode
    if mode not in ['i', 'o', '+']:
        abort(5, 'Error: ', mode, ': Invalid SPOOL mode.\n')

    # check SPOOL type
    if f_type not in JES:
        abort(5, 'Error: ', f_type, ': invalid SPOOL types.\n')

    # check path auto-generation
    if len(path) == 0:
        while True:
            conflict = False
            path = [ JCL['spool_path'],
                     'D{0:0>7}.?'.format(Config['tmp_id'])
                     ]
            Config['tmp_id'] += 1
            # check for file conflict
            for (k, v) in zPE.util.spool.dict():
                if v.virtual_path == path:
                    conflict = True
                    break
            if not conflict:
                break

    # check real_path binding
    if len(real_path) == 0:
        real_path = path

    SPOOL[key] = Spool([], [], mode, f_type, path, real_path)
    if f_type == 'file'  and  mode == 'i':
        load(key, mode, f_type, real_path)
    return SPOOL[key]


def open_file(dsn, mode, f_type):
    '''Open the target file in regardless of the existance'''
    return eval(''.join(['IO_', JES[f_type], '.open_file']))(dsn, mode)

def rm_file(dsn, f_type):
    '''Remove the target file in regardless of the existance'''
    return eval(''.join(['IO_', JES[f_type], '.rm_file']))(dsn)

def load(key, mode, f_type, real_path):
    if key not in SPOOL:
        abort(5, 'Error: ', key, ': invalid DD name.\n')
    if mode == 'o':
        abort(5, 'Error: ', key,
              ': try to load data into output SPOOL.\n')
    if f_type != 'file':
        abort(5, 'Error: ', key,
              ': try to load data from non-file object.\n')
    __fill(SPOOL[key], real_path)

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


def remove(key):
    if key in SPOOL:
        del SPOOL[key]

def replace(key, spool):
    SPOOL[key] = spool
    return SPOOL[key]

def pretend(dest, src):
    SPOOL[dest] = SPOOL[src]
    return SPOOL[dest]

def register_write(key, step):
    if key not in SP_DEFAULT_OUT:
        SP_DEFAULT_OUT.append(key)
        SP_DEFAULT_OUT_STEP[key] = step
        return True
    else:
        return False


### Supporting Functions

def __fill(sp, path):
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

