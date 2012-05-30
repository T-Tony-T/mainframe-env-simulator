# this is the "Major Editing Mode" selector
# each Major Mode is defined as an resource module in "zMajorMode"
# resource folder, or in user's config folder (~/.zPE/)

from zPE.GUI import min_import, GUI_PGK_PATH
from zPE.GUI.io_encap import norm_path, list_dir

from zPE.GUI.conf import CONFIG_PATH, MODE_MAP, DEFAULT_BUFF_MODE_MAP as DEFAULT

import os, sys

SEARCH_PATH = {
    'global' : norm_path(os.path.join(GUI_PGK_PATH[0], "zMajorMode")),
    'user'   : norm_path(CONFIG_PATH['dir']),
    }


# BaseMode need to be imported the EXACT SAME WAY as other modes are
_base_ = min_import('zPE.GUI.basemode', [ 'BaseMode' ], 0)

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

def guess(text):
    '''guess the major mode from the text in the buffer'''
    if text and text[0].isdigit():
        return 'Text Mode'      # programming language usually does not start with an digit
    return 'ASM Mode' # currently only support ASSIST (next develop version: HL-ASM), thus hard-coded

