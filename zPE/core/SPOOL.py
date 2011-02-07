# this is a simplification of the
# "Simultaneous Peripheral Operations OnLine"

# in future, may switch to "mmap" 

import zPE

import os, sys


MODE = {                        # SPOOL mode : display
    'i' : 'SYSIN',
    'o' : 'SYSOUT',
    '+' : 'KEPT',
    }

## Simultaneous Peripheral Operations On-line
class Spool(object):
    def __init__(self, spool, mode, f_type, fn_list, zPEfn):
        self.spool = spool      # [ line_1, line_2, ... ]
        self.mode = mode        # one of the MODE keys
        self.f_type = f_type    # one of the zPE.JES keys
        self.fn_list = fn_list  # [ dir_1, dir_2, ... , file ]
        self.zPEfn = zPEfn      # the file name in zPE, same format as above


    # the following methods are for Spool.spool
    def empty(self):
        return (len(self.spool) == 0)

    def append(self, *phrase):
        self.spool.append(''.join(phrase))

    def rmline(self, indx):
        if indx < len(self.spool):
            del self.spool[indx]

    def __str__(self):
        return str('mode : ' + self.mode +
                   ', type : ' + self.f_type +
                   ', fn : ' + str(self.fn_list) +
                   ', lbl : ' + str(self.zPEfn))

    def __getitem__(self, key):
        if isinstance(key, int):        # key = ln
            return self.spool[key]
        else:                           # key = (ln, indx/slice)
            return self.spool[key[0]][key[1]]

    def __setitem__(self, key, val):
        if isinstance(key, int):        # key = ln
            self.spool[key] = val
        else:
            if isinstance(key[1], int): # key = (ln, indx)
                in_s = key[1]
                in_e = key[1] + 1
            else:                       # key = (ln, slice)
                (in_s, in_e, step) = key[1].indices(len(self.spool[key[0]]))
            self.spool[key[0]] = '{0}{1}{2}'.format(
                self.spool[key[0]][:in_s],
                val,
                self.spool[key[0]][in_e:]
                )
# end of Spool Definition


## SPOOL Pool
DEFAULT = [ 'JESMSGLG', 'JESJCL', 'JESYSMSG' ]

SPOOL = {
    'JESMSGLG' : Spool([], 'o', 'outstream', None, ['01_JESMSGLG']),
    'JESJCL'   : Spool([], 'o', 'outstream', None, ['02_JESJCL']),
    'JESYSMSG' : Spool([], 'o', 'outstream', None, ['03_JESYSMSG']),
    }


## Interface Functions
def empty():
    return (len(SPOOL) == 0)

def sz():
    return len(SPOOL)

def dict():
    return SPOOL.items()

def list():
    return SPOOL.keys()

def new(key, mode, f_type, path = [], zPEfn = []):
    # check uniqueness
    if key in SPOOL:
        if ( (f_type == 'file') and (mode in ['i', '+']) and
             (path == path_of[key]) and (zPEfn == zPEfn_of(key))
             ):
            return SPOOL[key]   # passed from previous step
        sys.stderr.write('Error: ' + key + ': SPOOL name conflicts.\n')
        sys.exit(-1)

    # check SPOOL mode
    if mode not in ['i', 'o', '+']:
        sys.stderr.write('Error: ' + mode + ': Invalid SPOOL mode.\n')
        sys.exit(-1)

    # check SPOOL type
    if f_type not in zPE.JES:
        sys.stderr.write('Error: ' + f_type + ': invalid SPOOL types.\n')
        sys.exit(-1)

    # check path auto-generation
    if len(path) == 0:
        while True:
            conflict = False
            path = [ zPE.Config['spool_dir'],
                     zPE.Config['spool_path'],
                     'D{0:0>7}.?'.format(zPE.Config['tmp_id']) ]
            zPE.Config['tmp_id'] += 1
            # check for file conflict
            for k,v in dict():
                if v.fn_list == path:
                    conflict = True
                    break
            if not conflict:
                break

    # check zPEfn binding
    if len(zPEfn) == 0:
        zPEfn = path

    SPOOL[key] = Spool([], mode, f_type, path, zPEfn)
    return SPOOL[key]

def remove(key):
    if key in SPOOL:
        del SPOOL[key]

def retrive(key):
    if key in SPOOL:
        return SPOOL[key]
    else:
        return None

def mode_of(key):
    if key in SPOOL:
        return SPOOL[key].mode
    else:
        return None

def type_of(key):
    if key in SPOOL:
        return SPOOL[key].f_type
    else:
        return None

def path_of(key):
    if key in SPOOL:
        return SPOOL[key].fn_list
    else:
        return None

def zPEfn_of(key):
    if key in SPOOL:
        return SPOOL[key].zPEfn
    else:
        return None
