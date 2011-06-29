import os, sys
import re


## Configurable Definition
DEFAULT = {
    'FONT_SZ'   : '12',
    }

Config = {
    'font_sz'   : DEFAULT['FONT_SZ'],
    }

CONFIG_PATH = {
    'dir'       : os.path.join(os.environ['HOME'], '.zPE'),
    'gui_rc'    : os.path.join(os.environ['HOME'], '.zPE', 'gui.conf'),
    }

def read_rc():
    __CK_CONFIG()

    for line in open(CONFIG_PATH['gui_rc'], 'r'):
        (k, v) = re.split('[ \t]*=[ \t]*', line, maxsplit=1)
        ok = False

        if k == 'font_sz':
            try:
                Config[k] = str(int(v))
            except ValueError:
                Config[k] = DEFAULT['FONT_SZ']
                sys.stderr.write('CONFIG WARNING: ' + v[:-1] +
                                 ': Invalid font size.\n')

    __TOUCH_RC()



### Supporting Function

def __CK_CONFIG():
    if not os.path.isfile(CONFIG_PATH['gui_rc']):
        __TOUCH_RC()


def __TOUCH_RC():
    fp = open(CONFIG_PATH['gui_rc'], 'w')
    fp.write('font_sz = ' + str(Config['font_sz']) + '\n')
    fp.close()

