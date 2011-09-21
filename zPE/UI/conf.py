from zComp.zStrokeParser import KEY_BINDING_RULE_MKUP
from zComp.zStrokeParser import parse_key_binding as zSP_PARSE_KEY_BINDING

import zComp.io_encap

import os, sys
import pygtk
pygtk.require('2.0')
import gtk

import copy                     # for deep copy
import pango                    # for parsing the font
import re                       # for parsing the string

# debug flags
__TRACE_KEY_SCAN = False


# constant that will be treated as false
STR_FALSE = [ '0', 'nil', 'false', 'False' ]

# get monospace font list
MONO_FONT = {
    # 'font family name' : pango.FontFamily object
    }

for font in gtk.gdk.pango_context_get().list_families():
    if font.is_monospace():
        MONO_FONT[font.get_name()] = font

# get html color mapping
COLOR_LIST = {
    'black'             : '#000000',
    'blue'              : '#0000FF',
    'brown'             : '#A52A2A',
    'coral'             : '#FF7F50',
    'cyan'              : '#00FFFF',
    'fuchsia'           : '#FF00FF',
    'gold'              : '#FFD700',
    'gray'              : '#808080',
    'grey'              : '#808080',
    'green'             : '#008000',
    'lime'              : '#00FF00',
    'magenta'           : '#FF00FF',
    'maroon'            : '#800000',
    'olive'             : '#808000',
    'orange'            : '#FFA500',
    'orchid'            : '#DA70D6',
    'pink'              : '#FFC0CB',
    'purple'            : '#800080',
    'red'               : '#FF0000',
    'silver'            : '#C0C0C0',
    'violet'            : '#EE82EE',
    'wheat'             : '#F5DEB3',
    'white'             : '#FFFFFF',
    'yellow'            : '#FFFF00',
    }

INVERSE_COLOR_LIST = dict( [ (v, k) for (k, v) in COLOR_LIST.iteritems() ] )

## Configurable Definition
DEFAULT = {
    'MISC' : {
        'KEY_BINDING'   : 'other',   # style ~ ( emacs, vi*, other )
                                     # note: vi mode not implemented

        'KILL_RING_SZ'  : 16,

        'TAB_ON'        : 0,
        'TAB_GROUPED'   : 1,
        },

    'FONT' : {
        'NAME'          : 'Monospace',
        'SIZE'          : 12,
        },

    'COLOR_MAP' : {
        'TEXT'          : '#000000', # black
        'TEXT_SELECTED' : '#000000', # black

        'BASE'          : '#FBEFCD', # wheat - mod
        'BASE_SELECTED' : '#FFA500', # orenge

        'STATUS'        : '#808080', # gray
        'STATUS_ACTIVE' : '#C0C0C0', # silver

        'RESERVE'       : '#0000FF', # blue
        'COMMENT'       : '#008000', # green
        'LITERAL'       : '#FF0000', # red
        'LABEL'         : '#808000', # olive
        },

    'ENV'       : {
        'STARTING_PATH' : '~',
        },
    }


DEFAULT_FUNC_KEY_BIND_KEY = [
    'emacs',
#    'vi',                       # not implenemted yet
    'other'
    ]

DEFAULT_FUNC_KEY_BIND = {
    # need to be sync with "GUI_Readme.html"

    # split window manipulation; required by zSplitWindow
    'window_split_horz'     : {
        'emacs' : 'C-x 3',
        'vi'    : '',
        'other' : '',
        },
    'window_split_vert'     : {
        'emacs' : 'C-x 2',
        'vi'    : '',
        'other' : '',
        },
    'window_delete'         : {
        'emacs' : 'C-x 0',
        'vi'    : '',
        'other' : '',
        },
    'window_delete_other'   : {
        'emacs' : 'C-x 1',
        'vi'    : '',
        'other' : '',
        },

    # buffer manipulation; required by zEdit
    'buffer_open'           : {
        'emacs' : 'C-x C-f',
        'vi'    : '',
        'other' : 'C-o',
        },
    'buffer_save'           : {
        'emacs' : 'C-x C-s',
        'vi'    : '',
        'other' : 'C-s',
        },
    'buffer_save_as'        : {
        'emacs' : 'C-x C-w',
        'vi'    : '',
        'other' : 'C-S',
        },
    'buffer_close'          : {
        'emacs' : 'C-x k',
        'vi'    : '',
        'other' : 'F4',
        },

    'buffer_undo'           : {
        'emacs' : 'C-x u',
        'vi'    : '',
        'other' : 'C-z',
        },
    'buffer_redo'           : {
        'emacs' : '',
        'vi'    : '',
        'other' : 'C-y',
        },

    # tab manipulation; required by zEdit
    'tabbar_mode'           : {
        'emacs' : 'F7',
        'vi'    : '',
        'other' : 'F7',
        },
    'tabbar_prev'           : {
        'emacs' : 'C-Left',
        'vi'    : '',
        'other' : 'C-Left',
        },
    'tabbar_next'           : {
        'emacs' : 'C-Right',
        'vi'    : '',
        'other' : 'C-Right',
        },

    # editor related functions; required by zTextView and zEntry
    'complete'              : {
        'emacs' : 'Tab',
        'vi'    : '',
        'other' : 'Tab',
        },
    'complete_list'         : {
        'emacs' : 'M-/',
        'vi'    : '',
        'other' : '',
        },

    'backward_char'         : {
        'emacs' : 'C-b',
        'vi'    : '',
        'other' : '',
        },
    'backward_delete_char'  : {
        'emacs' : 'BackSpace',
        'vi'    : '',
        'other' : 'BackSpace',
        },
    'forward_char'          : {
        'emacs' : 'C-f',
        'vi'    : '',
        'other' : '',
        },
    'forward_delete_char'   : {
        'emacs' : 'Delete',
        'vi'    : '',
        'other' : 'Delete',
        },

    'backward_word'         : {
        'emacs' : 'M-b',
        'vi'    : '',
        'other' : '',
        },
    'backward_delete_word'  : {
        'emacs' : 'M-D',
        'vi'    : '',
        'other' : '',
        },
    'forward_word'          : {
        'emacs' : 'M-f',
        'vi'    : '',
        'other' : '',
        },
    'forward_delete_word'   : {
        'emacs' : 'M-d',
        'vi'    : '',
        'other' : '',
        },

    'backward_line'         : {
        'emacs' : 'C-a',
        'vi'    : '',
        'other' : '',
        },
    'backward_delete_line'  : {
        'emacs' : 'C-K',
        'vi'    : '',
        'other' : '',
        },
    'forward_line'          : {
        'emacs' : 'C-e',
        'vi'    : '',
        'other' : '',
        },
    'forward_delete_line'   : {
        'emacs' : 'C-k',
        'vi'    : '',
        'other' : '',
        },

    'backward_para'         : {
        'emacs' : 'M-{',
        'vi'    : '',
        'other' : '',
        },
    'backward_delete_para'  : {
        'emacs' : 'M-K',
        'vi'    : '',
        'other' : '',
        },
    'forward_para'          : {
        'emacs' : 'M-}',
        'vi'    : '',
        'other' : '',
        },
    'forward_delete_para'   : {
        'emacs' : 'M-k',
        'vi'    : '',
        'other' : '',
        },

    'kill_region'           : {
        'emacs' : 'C-w',
        'vi'    : '',
        'other' : 'C-x',
        },
    'kill_ring_save'        : {
        'emacs' : 'M-w',
        'vi'    : '',
        'other' : 'C-c',
        },
    'kill_ring_yank'        : {
        'emacs' : 'C-y',
        'vi'    : '',
        'other' : 'C-v',
        },
    'kill_ring_yank_pop'    : {
        'emacs' : 'M-y',
        'vi'    : '',
        'other' : '',
        },

    'set_mark_command'      : {
        'emacs' : 'C-@',
        'vi'    : '',
        'other' : '',
        },
    'set_mark_move_left'    : {
        'emacs' : 'S-Left',
        'vi'    : '',
        'other' : 'S-Left',
        },
    'set_mark_move_right'   : {
        'emacs' : 'S-Right',
        'vi'    : '',
        'other' : 'S-Right',
        },
    'set_mark_move_up'      : {
        'emacs' : 'S-Up',
        'vi'    : '',
        'other' : 'S-Up',
        },
    'set_mark_move_down'    : {
        'emacs' : 'S-Down',
        'vi'    : '',
        'other' : 'S-Down',
        },
    'set_mark_move_start'   : {
        'emacs' : 'S-Home',
        'vi'    : '',
        'other' : 'S-Home',
        },
    'set_mark_move_end'     : {
        'emacs' : 'S-End',
        'vi'    : '',
        'other' : 'S-End',
        },


    # functions that are not required by any z* module
    # top-level functions
    'prog_show_config'      : {
        'emacs' : 'C-c c',
        'vi'    : '',
        'other' : 'C-p',
        },
    'prog_show_error'       : {
        'emacs' : 'C-c e',
        'vi'    : '',
        'other' : 'C-J',
        },
    'prog_show_about'       : {
        'emacs' : '',
        'vi'    : '',
        'other' : '',
        },
    'prog_quit'             : {
        'emacs' : 'C-x C-c',
        'vi'    : '',
        'other' : 'C-q',
        },

    # zPE related functions
    'zPE_submit'            : {
        'emacs' : 'F9',
        'vi'    : '',
        'other' : 'F9',
        },
    'zPE_submit_with_JCL'   : {
        'emacs' : 'F8',
        'vi'    : '',
        'other' : 'F8',
        },
    }

Config = {}

def init_rc_all():
    init_rc()
    init_key_binding()

def init_rc():
    Config['MISC'] = {
        'key_binding'   : DEFAULT['MISC']['KEY_BINDING'],

        'kill_ring_sz'  : DEFAULT['MISC']['KILL_RING_SZ'],

        'tab_on'        : DEFAULT['MISC']['TAB_ON'],
        'tab_grouped'   : DEFAULT['MISC']['TAB_GROUPED'],
        }

    Config['FONT'] = {
        'name'          : DEFAULT['FONT']['NAME'],
        'size'          : DEFAULT['FONT']['SIZE'],
        }

    Config['COLOR_MAP'] =  {
        'text'          : DEFAULT['COLOR_MAP']['TEXT'],
        'text_selected' : DEFAULT['COLOR_MAP']['TEXT_SELECTED'],

        'base'          : DEFAULT['COLOR_MAP']['BASE'],
        'base_selected' : DEFAULT['COLOR_MAP']['BASE_SELECTED'],

        'status'        : DEFAULT['COLOR_MAP']['STATUS'],
        'status_active' : DEFAULT['COLOR_MAP']['STATUS_ACTIVE'],

        'reserve'       : DEFAULT['COLOR_MAP']['RESERVE'],
        'comment'       : DEFAULT['COLOR_MAP']['COMMENT'],
        'literal'       : DEFAULT['COLOR_MAP']['LITERAL'],
        'label'         : DEFAULT['COLOR_MAP']['LABEL'],
        }

    Config['ENV']       = {
        'starting_path' : zComp.io_encap.norm_path( DEFAULT['ENV']['STARTING_PATH'] ),
        }

def init_key_binding():
    kb_style = Config['MISC']['key_binding']
    Config['FUNC_BINDING'] = dict(
        zip( DEFAULT_FUNC_KEY_BIND.keys(),
             [ v[kb_style] for v in DEFAULT_FUNC_KEY_BIND.itervalues() ]
             )
        )
    Config['KEY_BINDING'] = dict((v, k) for (k, v) in Config['FUNC_BINDING'].iteritems())
    if '' in Config['KEY_BINDING']:
        del Config['KEY_BINDING'][''] # remove empty binding


CONFIG_PATH = {
    'dir'       : os.path.join(os.environ['HOME'], '.zPE'),
    'gui_rc'    : os.path.join(os.environ['HOME'], '.zPE', 'gui.conf'),
    'key_emacs' : os.path.join(os.environ['HOME'], '.zPE', 'key.emacs'),
#    'key_vi'    : os.path.join(os.environ['HOME'], '.zPE', 'key.vi'),
    'key_other' : os.path.join(os.environ['HOME'], '.zPE', 'key.other'),
    }

def read_rc_all():
    read_rc()
    read_key_binding()


def read_rc():
    init_rc()
    __CK_CONFIG()

    label = None
    for line in open(CONFIG_PATH['gui_rc'], 'r'):
        if line.isspace():      # skip empty line
            continue

        line = line[:-1]        # get rid of the '\n'

        if line in [ '[MISC]', '[FONT]', '[COLOR_MAP]', '[ENV]' ]:
            label = line[1:-1]  # retrive the top-level key
            continue

        if not label:
            continue            # no top-level key so far, skip the line

        (k, v) = re.split('[ \t]*=[ \t]*', line, maxsplit=1)

        if label == 'MISC':
            if k == 'key_binding':
                if v in DEFAULT_FUNC_KEY_BIND_KEY:
                    Config[label][k] = v
                else:
                    Config[label][k] = DEFAULT['MISC']['KEY_BINDING']
                    sys.stderr.write('CONFIG WARNING: {0}: Invalid key binding style.\n'.format(v))

            elif k == 'kill_ring_sz':
                try:
                    v = int(v)
                    if v >= 1:
                        Config[label][k] = v
                    else:
                        sys.stderr.write('CONFIG WARNING: {0}: Kill-ring size must be at least 1.\n'.format(v))
                except ValueError:
                    Config[label][k] = DEFAULT['MISC']['KILL_RING_SZ']
                    sys.stderr.write('CONFIG WARNING: {0}: Invalid kill-ring size.\n'.format(v))

            elif k == 'tab_on':
                if v and v not in STR_FALSE:
                    Config[label][k] = 1
                else:
                    Config[label][k] = 0

            elif k == 'tab_grouped':
                if v and v not in STR_FALSE:
                    Config[label][k] = 1
                else:
                    Config[label][k] = 0

        elif label == 'FONT':
            if k == 'name':
                found = False
                for font in MONO_FONT:
                    if font == v:
                        Config[label][k] = v
                        found = True
                        break

                if not found:
                    sys.stderr.write('CONFIG WARNING: {0}: Invalid font name.\n'.format(v))

            elif k == 'size':
                try:
                    Config[label][k] = int(v)
                except ValueError:
                    Config[label][k] = DEFAULT['FONT_SZ']
                    sys.stderr.write('CONFIG WARNING: {0}: Invalid font size.\n'.format(v))

        elif label == 'COLOR_MAP':
            if v.lower() in COLOR_LIST:
                v_ty = 'name'
                v = COLOR_LIST[v]
            else:
                v_ty = 'code'

            v = v.upper()       # convert hex color code to all upper case
            if not re.match('#[0-9A-F]{6}', v):
                sys.stderr.write('CONFIG WARNING: {0}: Invalid color {1}.\n'.format(v, v_ty))
                continue

            # valid color, check key
            if k in Config[label]:
                Config[label][k] = v
            else:
                sys.stderr.write('CONFIG WARNING: {0}: Invalid color mapping.\n'.format(k))

        elif label == 'ENV':
            if k == 'starting_path':
                tmp_v = zComp.io_encap.norm_path(v)
                if os.path.isdir(tmp_v):
                    Config[label][k] = tmp_v
                else:
                    Config[label][k] = zComp.io_encap.norm_path( DEFAULT['ENV']['STARTING_PATH'] )
                    sys.stderr.write('CONFIG WARNING: {0}: Invalid starting path.\n'.format(v))

    write_rc()


def read_key_binding():
    __CK_KEY()

    # retrive all valid functions
    Config['FUNC_BINDING'] = dict(zip(DEFAULT_FUNC_KEY_BIND.keys(), [''] * len(DEFAULT_FUNC_KEY_BIND)))
    Config['KEY_BINDING'] = {}

    # parse key binding file
    for line in open(CONFIG_PATH[ 'key_{0}'.format(Config['MISC']['key_binding']) ], 'r'):
        line = line[:-1]        # get rid of the '\n'

        (k, v) = re.split('[ \t]*=[ \t]*', line, maxsplit=1)

        if __TRACE_KEY_SCAN:
            sys.stderr.write('\n== Style::{0} => {1}:\n'.format(Config['MISC']['key_binding'], line))

        if not v:
            continue

        seq = parse_key_binding(v)
        if not seq:
            sys.stderr.write('CONFIG WARNING: {0}: Invalid key sequence.\n'.format(v))
            continue

        key_sequence_add(k, seq, force_override = True, force_rebind = True, warning = True)

        if __TRACE_KEY_SCAN:
            sys.stderr.write('   Func => Key:\n')
            for k,v in Config['FUNC_BINDING'].iteritems():
                sys.stderr.write('       {0} : {1}\n'.format(k, v))
            sys.stderr.write('   Key => Func:\n')
            for k,v in Config['KEY_BINDING'].iteritems():
                sys.stderr.write('       {0} : {1}\n'.format(k, v))

    write_key_binding()


def key_sequence_add(func, seq,
                     force_override = False, # redefine function with different stroke
                     force_rebind = False,   # rebind stroke with different function
                     warning = True          # print warning msg to stderr
                     ):
    stroke = ' '.join(seq)      # normalize the key sequence

    if func not in Config['FUNC_BINDING']:
        # undefined function
        if warning:
            sys.stderr.write('CONFIG WARNING: {0}: Invalid key binding.\n'.format(func))
        return None
    else:
        if Config['FUNC_BINDING'][func] == stroke:
            # same binding as before
            return False

        # remove conflict stroke
        if stroke in Config['KEY_BINDING']:
            # key sequence defined for another function
            msg = 'CONFIG WARNING: {0}: Key sequence already binded.\n'.format(stroke)
            if not force_override:
                raise ValueError('override', msg, Config['KEY_BINDING'][stroke], stroke)
            if warning:
                sys.stderr.write(msg)
            old_func = Config['KEY_BINDING'][stroke] # will never be empty, unless in 'else' part
            del Config['KEY_BINDING'][stroke]        # remove stroke
        else:
            old_func = ''       # old_func not found

        old_stroke = Config['FUNC_BINDING'][func] # could be empty
        if old_stroke:
            # has previously defined stroke
            msg = 'CONFIG WARNING: {0}: Redifing key binding for the function.\n'.format(func)
            if not force_rebind:
                raise ValueError('rebind', msg, func, old_stroke)
            if warning:
                sys.stderr.write(msg)
            del Config['KEY_BINDING'][old_stroke] # remove old_stroke

        # reset conflict func
        Config['FUNC_BINDING'][func] = ''
        if old_func:
            Config['FUNC_BINDING'][old_func] = ''

        # add new func and stroke
        Config['FUNC_BINDING'][func] = stroke
        Config['KEY_BINDING'][stroke] = func

        return True

def func_binding_rm(func):
    if func not in Config['FUNC_BINDING']:
        raise KeyError('CONFIG WARNING: {0}: Not a valid function.\n'.format(func))
    old_strock = Config['FUNC_BINDING'][func]

    Config['FUNC_BINDING'][func] = ''
    if old_strock:
        del Config['KEY_BINDING'][old_strock]


def parse_key_binding(key_sequence):
    return zSP_PARSE_KEY_BINDING(key_sequence, Config['MISC']['key_binding'])

def reset_key_binding():
    for style in DEFAULT_FUNC_KEY_BIND_KEY:
        func_binding = dict(
            zip( DEFAULT_FUNC_KEY_BIND.keys(),
                 [ v[style] for v in DEFAULT_FUNC_KEY_BIND.itervalues() ]
                 )
            )
        __TOUCH_KEY(style, func_binding)


def write_rc_all():
    write_rc()
    write_key_binding()

def write_rc():
    __TOUCH_RC()

def write_key_binding():
    __TOUCH_KEY()


### Supporting Function

def __CK_CONFIG():
    if not os.path.isfile(CONFIG_PATH['gui_rc']):
        __TOUCH_RC()


def __CK_KEY():
    style = Config['MISC']['key_binding']
    style_path = 'key_{0}'.format(style)

    if not os.path.isfile(CONFIG_PATH[style_path]):
        init_key_binding()
        __TOUCH_KEY()



def __TOUCH_RC():
    fp = open(CONFIG_PATH['gui_rc'], 'w')

    for label in [ 'MISC', 'ENV', 'FONT' ]:
        fp.write('[{0}]\n'.format(label))
        for key in sorted(Config[label].iterkeys()):
            fp.write('{0} = {1}\n'.format(key, Config[label][key]))
        fp.write('\n')

    label = 'COLOR_MAP'
    fp.write('[{0}]\n'.format(label))
    for key in sorted(Config[label].iterkeys()):
        value = Config[label][key]
        if value in INVERSE_COLOR_LIST:
            value = INVERSE_COLOR_LIST[value]
        fp.write('{0} = {1}\n'.format(key, value))
    fp.write('\n')

    fp.close()


def __TOUCH_KEY(style = None, func_binding = None):
    if not style or not func_binding:
        style = Config['MISC']['key_binding']
        func_binding = copy.copy(Config['FUNC_BINDING'])
    style_path = 'key_{0}'.format(style)

    fp = open(CONFIG_PATH[style_path], 'w')
    for func in sorted(func_binding.iterkeys()):
        fp.write('{0} = {1}\n'.format(func, func_binding[func]))
    fp.close()
