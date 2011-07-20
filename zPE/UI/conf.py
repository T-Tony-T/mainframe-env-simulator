import os, sys
import pygtk
pygtk.require('2.0')
import gtk

import copy                     # for deep copy
import pango                    # for parsing the font
import re                       # for parsing the string


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

INVERSE_COLOR_LIST = dict( [ (v, k) for (k, v) in COLOR_LIST.items() ] )

## Configurable Definition
DEFAULT = {
    'MISC' : {
        'KEY_BINDING'   : 'other',   # style ~ ( emacs, vi*, other )
                                     # note: vi mode not implemented

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
    }


DEFAULT_FUNC_KEY_BIND_KEY = [
    'emacs',
#    'vi',                       # not implenemted yet
    'other'
    ]
DEFAULT_FUNC_KEY_BIND = {
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
    'prog_quit'             : {
        'emacs' : 'C-x C-c',
        'vi'    : '',
        'other' : 'C-q',
        },
    }

Config = {}

def init_rc():
    Config['MISC'] = {
        'key_binding'   : DEFAULT['MISC']['KEY_BINDING'],

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
    init_key_binding()

def init_key_binding():
    kb_style = Config['MISC']['key_binding']
    Config['FUNC_BINDING'] = dict(
        zip( DEFAULT_FUNC_KEY_BIND.keys(),
             [ v[kb_style] for v in DEFAULT_FUNC_KEY_BIND.values() ]
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

def read_rc():
    __CK_CONFIG()
    init_rc()

    label = None
    for line in open(CONFIG_PATH['gui_rc'], 'r'):
        line = line[:-1]        # get rid of the '\n'

        if line in [ '[MISC]', '[FONT]', '[COLOR_MAP]' ]:
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

    init_key_binding()
    for line in open(CONFIG_PATH[ 'key_{0}'.format(Config['MISC']['key_binding']) ], 'r'):
        line = line[:-1]        # get rid of the '\n'

        (k, v) = re.split('[ \t]*=[ \t]*', line, maxsplit=1)

        seq = parse_key_binding(v)
        if not seq:
            sys.stderr.write('CONFIG WARNING: {0}: Invalid key sequence.\n'.format(v))
            continue

        v = ' '.join(seq)       # normalize the key sequence

        if k not in Config['FUNC_BINDING']:
            sys.stderr.write('CONFIG WARNING: {0}: Invalid key binding.\n'.format(k))
        else:
            if Config['FUNC_BINDING'][k] == v:
                continue        # alread in, skip

            # remove conflict v
            if v in Config['KEY_BINDING']:
                old_k = Config['KEY_BINDING'][v] # could be empty
                del Config['KEY_BINDING'][v]     # remove v
            else:
                old_k = ''      # old_k not found

            old_v = Config['FUNC_BINDING'][k] # will never be empty
            if old_v in Config['KEY_BINDING']:
                del Config['KEY_BINDING'][old_v] # remove old_v

            # reset conflict k
            Config['FUNC_BINDING'][k] = ''
            if old_k:
                Config['FUNC_BINDING'][old_k] = ''

            # add new k and v
            Config['FUNC_BINDING'][k] = v
            Config['KEY_BINDING'][v] = k

    write_rc()


__BASE_PATTERN = {
    'func_key' : r'''
( BACKSPACE | BackSpace | backspace ) |
( ENTER     | Enter     | enter     ) |
( ESCAPE    | Escape    | escape    ) |
( SPACE     | Space     | space     ) |
( TAB       | Tab       | tab       ) |

( INSERT    | Insert    | insert    ) |
( DELETE    | Delete    | delete    ) |
( HOME      | Home      | home      ) |
( END       | End       | end       ) |
( PAGE_UP   | Page_Up   | page_up   ) |
( PAGE_DOWN | Page_Down | page_down ) |

( LEFT      | Left      | left      ) |
( RIGHT     | Rignt     | right     ) |
( UP        | Up        | up        ) |
( DOWN      | Down      | down      ) |

( [Ff] (1[0-2] | [2-9]) )               # F1 ~ F12
''',

    'printable' : r'''
[\x21-\x7e]                             # all chars that are printed on the keyboard
''',
    }

__PATTERN = {
    # comment '# 1' and '# 2' means '1' or '2'
    # comment '# 1' and '#   2' means '12' (1 followed by 2)
    'func_key' : r'''^(                 # anchor to the beginning
{0}                                     #   function key
)$                                      #     anchor to the end
'''.format(__BASE_PATTERN['func_key']),

    'printable' : r'''^(                # anchor to the beginning
{0}                                     #   printable char
)$                                      #     anchor to the end
'''.format(__BASE_PATTERN['printable']),

    'combo' : r'''^(                    # anchor to the beginning
( C-M- | [CM]- )                        #   C-M- / C- / M- followed by
( {0} | {1} )                           #     function key or printable char
)$                                      #       anchor to the end
'''.format(__BASE_PATTERN['func_key'], __BASE_PATTERN['printable']),

    'forbid_emacs' : r'''^(             # anchor to the beginning
C-g                                     #   cancel
)$                                      #     anchor to the end
''',

    'forbid_emacs_init' : r'''^(        # anchor to the beginning
{0} |                                   #   printable char
M-x |                                   #   run command
C-g |                                   #   cancel
C-q                                     #   escape next stroke
)$                                      #     anchor to the end
'''.format(__BASE_PATTERN['printable']),
    }

def parse_key_binding(key_sequence):
    sequence = key_sequence.split()

    if Config['MISC']['key_binding'] == 'emacs':
        # style::emacs
        if not len(sequence):
            return None

        if re.match(__PATTERN['forbid_emacs_init'], sequence[0], re.X):
            # not allow for re-define as starting of a combo
            return None

        for indx in range(len(sequence)):
            if re.match(__PATTERN['forbid_emacs'], sequence[indx], re.X):
                # not allow for re-define
                return None

            m_func_key  = re.match(__PATTERN['func_key'],  sequence[indx], re.X)
            m_printable = re.match(__PATTERN['printable'], sequence[indx], re.X)
            m_combo     = re.match(__PATTERN['combo'],     sequence[indx], re.X)

            if not (m_func_key or m_printable or m_combo):
                # not a func_key stroke, printable, nor a combo
                return None

            if m_func_key and indx != len(sequence) - 1:
                # func_key stroke is not the last stroke
                return None

    elif Config['MISC']['key_binding'] == 'vi':
        # style::vi
        return None             # not supported yet

    else:
        # style::other
        if len(sequence) != 1:
            # style::other must contain only 1 stroke
            return None

    return sequence


def write_rc():
    __CK_CONFIG()

    __TOUCH_RC()
    __TOUCH_KEY()


### Supporting Function

def __CK_CONFIG():
    if not os.path.isfile(CONFIG_PATH['gui_rc']):
        __TOUCH_RC()
#    if not os.path.isfile(CONFIG_PATH['key_emacs']):
#        __TOUCH_KEY('emacs')
#    if not os.path.isfile(CONFIG_PATH['key_vi']):
#        __TOUCH_KEY('vi')
    if not os.path.isfile(CONFIG_PATH['key_other']):
        __TOUCH_KEY('other')


def __TOUCH_RC():
    fp = open(CONFIG_PATH['gui_rc'], 'w')

    label = 'MISC'
    fp.write('[{0}]\n'.format(label))
    for key in sorted(Config[label].iterkeys()):
        fp.write('{0} = {1}\n'.format(key, Config[label][key]))

    label = 'FONT'
    fp.write('[{0}]\n'.format(label))
    for key in sorted(Config[label].iterkeys()):
        fp.write('{0} = {1}\n'.format(key, Config[label][key]))

    label = 'COLOR_MAP'
    fp.write('[{0}]\n'.format(label))
    for key in sorted(Config[label].iterkeys()):
        value = Config[label][key]
        if value in INVERSE_COLOR_LIST:
            value = INVERSE_COLOR_LIST[value]
        fp.write('{0} = {1}\n'.format(key, value))

    fp.close()


def __TOUCH_KEY(style = None):
    if not style:
        style = Config['MISC']['key_binding']
    fp = open(CONFIG_PATH[ 'key_{0}'.format(style) ], 'w')
    for func in sorted(Config['FUNC_BINDING'].iterkeys()):
        fp.write('{0} = {1}\n'.format(func, Config['FUNC_BINDING'][func]))
    fp.close()
