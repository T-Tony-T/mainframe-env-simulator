# this is the "Major Editing Mode" selector
# each Major Mode is defined as an resource module in "zMajorMode" resource folder

from io_encap import norm_path
from conf import CONFIG_PATH

import os, sys, inspect
SELF_PATH = os.path.split(inspect.getfile(inspect.currentframe()))

SEARCH_PATH = {
    'global' : norm_path(os.path.join(SELF_PATH[0], "zMajorMode")),
    'user'   : norm_path(CONFIG_PATH['dir']),
    }

if SEARCH_PATH['user'] not in sys.path:
    sys.path.append(SEARCH_PATH['user'])
if SEARCH_PATH['global'] not in sys.path:
    sys.path.append(SEARCH_PATH['global'])


MODE_MAP = {
    # mode_string : mode_object
    }

_temp = __import__('zPE.UI.basemode', globals(), locals(), [ 'BaseMode' ], -1)
_base = _temp.BaseMode
for fn in os.listdir(SEARCH_PATH['user']) + os.listdir(SEARCH_PATH['global']):
    mn, ext = os.path.splitext(fn) # Handles no-extension files, etc.
    if ext == '.py':
        cn = mn.title() + 'Mode'
        _temp = __import__(mn, globals(), locals(), [ cn ], -1)
        try:
            _obj  = eval('_temp.{0}'.format(cn))()
        except:
            continue            # ignore silently
        if isinstance(_obj, _base)  and  str(_obj) not in MODE_MAP:
            MODE_MAP[str(_obj)] = _obj # load the mode
        else:
            sys.stderr.write('warn: {0}: Invalid Major Mode Module.\n'.format(cn))


