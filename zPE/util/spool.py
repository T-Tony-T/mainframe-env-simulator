# this defines the SPOOL access methods

from global_config import SP_DEFAULT, SP_DEFAULT_OUT, SP_DEFAULT_OUT_STEP, SPOOL, SPOOL_CTRL_MAP

def empty():
    return (len(SPOOL) == 0)

def sz():
    return len(SPOOL)

def dict():
    return SPOOL.items()

def list():
    return SPOOL.keys()

def retrieve(key):
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
        return SPOOL[key].virtual_path
    else:
        return None

def real_path_of(key):
    if key in SPOOL:
        return SPOOL[key].real_path
    else:
        return None
