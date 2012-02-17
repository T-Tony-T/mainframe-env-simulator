# this is a simplification of the
# "Simultaneous Peripheral Operations OnLine"

# in future, may switch to "mmap"

import sys                      # for sys.maxsize

import zPE


MODE = {                        # SPOOL mode : display
    'i' : 'SYSIN',
    'o' : 'SYSOUT',
    '+' : 'KEPT',
    }

## Simultaneous Peripheral Operations On-line
class Spool(object):
    def __init__(self, spool, spdid, mode, f_type, virtual_path, real_path):
        self.spool = spool      # [ line_1,  line_2,  ... ]
        self.spdid = spdid      # [ ln_id_1, ln_id_2, ... ] // deck id
                                # digit (line number) for input SPOOL
                                # label (tp-label) for expanded input
                                # none for output SPOOL
        # the above two need to be in sync (if modifiey manually)
        self.mode = mode        # one of the MODE keys
        self.f_type = f_type    # one of the zPE.JES keys
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


## SPOOL Pool
DEFAULT     = [ 'JESMSGLG', 'JESJCL', 'JESYSMSG' ] # System Managed SPOOL
DEFAULT_OUT = [ 'JESMSGLG', 'JESJCL', 'JESYSMSG' ] # SPOOLs that will be write out at the end
DEFAULT_OUT_STEP = { # step name corresponding to the above list
    'JESMSGLG' : 'JES',
    'JESJCL'   : 'JES',
    'JESYSMSG' : 'JES',
    }

SPOOL = {
    'JESMSGLG' : Spool([], [], 'o', 'outstream', None, ['JESMSGLG']),
    'JESJCL'   : Spool([], [], 'o', 'outstream', None, ['JESJCL']),
    'JESYSMSG' : Spool([], [], 'o', 'outstream', None, ['JESYSMSG']),
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

def new(key, mode, f_type, path = [], real_path = []):
    # check uniqueness
    if key in SPOOL:
        if ( (f_type == 'file') and (mode in ['i', '+']) and
             (path == path_of[key]) and (real_path == real_path_of(key))
             ):
            return SPOOL[key]   # passed from previous step
        zPE.abort(5, 'Error: ', key, ': SPOOL name conflicts.\n')

    # check SPOOL mode
    if mode not in ['i', 'o', '+']:
        zPE.abort(5, 'Error: ', mode, ': Invalid SPOOL mode.\n')

    # check SPOOL type
    if f_type not in zPE.JES:
        zPE.abort(5, 'Error: ', f_type, ': invalid SPOOL types.\n')

    # check path auto-generation
    if len(path) == 0:
        while True:
            conflict = False
            path = [ zPE.JCL['spool_path'],
                     'D{0:0>7}.?'.format(zPE.conf.Config['tmp_id'])
                     ]
            zPE.conf.Config['tmp_id'] += 1
            # check for file conflict
            for (k, v) in dict():
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
        load(key)
    return SPOOL[key]

def load(key):
    if key not in SPOOL:
        zPE.abort(5, 'Error: ', key, ': invalid DD name.\n')
    sp = SPOOL[key]
    if sp.f_type != 'file'  or  sp.mode != 'i':
        zPE.abort(5, 'Error: ', key, ': invalid try for loading input DD.\n')
    zPE.load_fb80(SPOOL[key])


def remove(key):
    if key in SPOOL:
        del SPOOL[key]

def replace(key, spool):
    SPOOL[key] = spool
    return SPOOL[key]

def pretend(dest, src):
    SPOOL[dest] = SPOOL[src]
    return SPOOL[dest]

def retrieve(key):
    if key in SPOOL:
        return SPOOL[key]
    else:
        return None

def register_write(key, step):
    if key not in DEFAULT_OUT:
        DEFAULT_OUT.append(key)
        DEFAULT_OUT_STEP[key] = step
        return True
    else:
        return False

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
        return SPOOL[key].virtual_path
    else:
        return None

def real_path_of(key):
    if key in SPOOL:
        return SPOOL[key].real_path
    else:
        return None
