import os, sys
import re


## Configurable Definition
DEFAULT = {
    'FONT_SZ'   : '12',
    'TAB_ON'    : 'off',
    'TAB_MODE'  : 'group',
    }

Config = {
    'font_sz'   : DEFAULT['FONT_SZ'],
    'tab_on'    : DEFAULT['TAB_ON'],
    'tab_mode'  : DEFAULT['TAB_MODE'],
    }

CONFIG_PATH = {
    'dir'       : os.path.join(os.environ['HOME'], '.zPE'),
    'gui_rc'    : os.path.join(os.environ['HOME'], '.zPE', 'gui.conf'),
    }

def read_rc():
    __CK_CONFIG()

    for line in open(CONFIG_PATH['gui_rc'], 'r'):
        (k, v) = re.split('[ \t]*=[ \t]*', line, maxsplit=1)

        v = v[:-1]

        if k == 'font_sz':
            try:
                Config[k] = str(int(v))
            except ValueError:
                Config[k] = DEFAULT['FONT_SZ']
                sys.stderr.write('CONFIG WARNING: ' + v +
                                 ': Invalid font size.\n')

        if k == 'tab_on':
            if v in [ 'on', 'off' ]:
                Config[k] = v
            else:
                Config[k] = DEFAULT['TAB_ON']
                sys.stderr.write('CONFIG WARNING: ' + v +
                                 ': Invalid TAB switch.\n')
        if k == 'tab_mode':
            if v in [ 'all', 'group' ]:
                Config[k] = v
            else:
                Config[k] = DEFAULT['TAB_MODE']
                sys.stderr.write('CONFIG WARNING: ' + v +
                                 ': Invalid TAB mode.\n')

    __TOUCH_RC()


def write_rc():
    __CK_CONFIG()
    __TOUCH_RC()


### Supporting Function

def __CK_CONFIG():
    if not os.path.isfile(CONFIG_PATH['gui_rc']):
        __TOUCH_RC()


def __TOUCH_RC():
    fp = open(CONFIG_PATH['gui_rc'], 'w')
    fp.write('font_sz = ' + Config['font_sz'] + '\n')
    fp.write('tab_on = ' + Config['tab_on'] + '\n')
    fp.write('tab_mode = ' + Config['tab_mode'] + '\n')
    fp.close()

