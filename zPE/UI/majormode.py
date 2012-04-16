# this is the "Major Editing Mode" selector
# each Major Mode is defined as an resource module in "zMajorMode" resource folder

from zPE.UI import min_import
from io_encap import norm_path, list_dir
from conf import CONFIG_PATH

import os, sys, inspect
SELF_PATH = os.path.split(inspect.getfile(inspect.currentframe()))

SEARCH_PATH = {
    'global' : norm_path(os.path.join(SELF_PATH[0], "zMajorMode")),
    'user'   : norm_path(CONFIG_PATH['dir']),
    }


MODE_MAP = {
    # mode_string : mode_object
    }

_base_ = min_import('zPE.UI.basemode', [ 'BaseMode' ], 0)

def load_mode(path):
    for fn in list_dir(path):
        [ mn, ext ] = os.path.splitext(fn) # Handles no-extension files, etc.
        if ext == '.py':
            cn = mn.title() + 'Mode'
            try:
                _cls_ = min_import(mn, [ cn ], -1, path)
                _obj_  = _cls_()
            except:
                sys.stderr.write('warn: {0}: Fail to load Major Mode Module.\n'.format(cn))
                continue            # ignore silently
            if isinstance(_obj_, _base_)  and  str(_obj_) not in MODE_MAP:
                MODE_MAP[str(_obj_)] = _obj_ # load the mode
            else:
                sys.stderr.write('warn: {0}: Invalid Major Mode Module.\n'.format(cn))

load_mode(SEARCH_PATH['user'])
load_mode(SEARCH_PATH['global'])

DEFAULT = {
    'scratch' : 'ASM Mode',     # scratch file
    'file'    : 'ASM Mode',     # regular file
    'dir'     : 'Text Mode',    # directory
    'disp'    : 'Text Mode',    # display panel
    }

def guess(text):
    '''guess the major mode from the text in the buffer'''
    if text and text[0].isdigit():
        return 'Text Mode'      # programming language usually does not start with an digit
    return 'ASM Mode' # currently only support ASSIST (next develop version: HL-ASM), thus hard-coded

