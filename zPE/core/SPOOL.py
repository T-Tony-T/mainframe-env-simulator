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

class Spool(object):
    def __init__(self, spool, mode, f_type, fn_list, label):
        self.spool = spool      # [ line_1, line_2, ... ]
        self.mode = mode        # one of the MODE keys
        self.f_type = f_type    # one of the zPE.JES keys
        self.fn_list = fn_list  # [ dir_1, dir_2, ... , file ]
        self.label = label      # the file name on PC


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
                   ', lbl : ' + str(self.label))

    def __getitem__(self, (ln, indx)):
        return self.spool[ln][indx]

    def __setitem__(self, (ln, indx), val):
        if isinstance(indx, int):
            in_s = indx
            in_e = indx + 1
        else:                   # must be slice
            (in_s, in_e, step) = indx.indices(len(self.spool[ln]))

        self.spool[ln] = '{0}{1}{2}'.format(
            self.spool[ln][:in_s],
            val,
            self.spool[ln][in_e:]
            )
# end of Spool Definition

# SPOOL pool
DEFAULT = [ 'JESMSGLG', 'JESJCL', 'JESYSMSG' ]

SPOOL = {
    'JESMSGLG' : Spool([], 'o', 'outstream', None, ['01_JESMSGLG']),
    'JESJCL'   : Spool([], 'o', 'outstream', None, ['02_JESJCL']),
    'JESYSMSG' : Spool([], 'o', 'outstream', None, ['03_JESYSMSG']),
    }


def empty():
    return (len(SPOOL) == 0)

def sz():
    return len(SPOOL)

def dict():
    return SPOOL.items()

def list():
    return SPOOL.keys()

def new(key, mode, f_type, path = [], label = []):
    # check uniqueness
    if key in SPOOL:
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

    # check label binding
    if len(label) == 0:
        label = path

    SPOOL[key] = Spool([], mode, f_type, path, label)
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

def label_of(key):
    if key in SPOOL:
        return SPOOL[key].label
    else:
        return None
