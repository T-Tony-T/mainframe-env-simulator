import os, sys
import pygtk
pygtk.require('2.0')
import gtk

import copy                     # for deep copy
import pango                    # for parsing the font
import re                       # for parsing the string


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

        'TAB_ON'        : 'off',     # ( on, off )
        'TAB_MODE'      : 'group',   # ( all, group )
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


DEFAULT_FUNC_KEY_BIND = {
    'emacs' : {
        'buffer_open'           : 'C-x C-f',
#        'buffer_save'           : '',
#        'buffer_save_as'        : '',
#        'buffer_close'          : '',

        'prog_show_config'      : 'C-c c',
        'prog_show_error'       : 'C-c e',
        'prog_quit'             : 'C-x C-c',
        },

#    'vi' : {
#        'prog_quit'             : ':q',
#        'prog_force_quit'       : ':q!',
#        'prog_save_quit'        : ':qw',
#        },

    'other' : {
        'buffer_open'           : 'C-o',
#        'buffer_save'           : '',
#        'buffer_save_as'        : '',
#        'buffer_close'          : '',

        'prog_show_config'      : 'C-p',
        'prog_show_error'       : 'C-J',
        'prog_quit'             : 'C-q',
        },
    }

Config = {
    'MISC' : {
        'key_binding'   : DEFAULT['MISC']['KEY_BINDING'],

        'tab_on'        : DEFAULT['MISC']['TAB_ON'],
        'tab_mode'      : DEFAULT['MISC']['TAB_MODE'],
        },

    'FONT' : {
        'name'          : DEFAULT['FONT']['NAME'],
        'size'          : DEFAULT['FONT']['SIZE'],
        },

    'COLOR_MAP' : {
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
        },

    'FUNC_BINDING' : {
        # will be filled after MISC::key_binding is read
        # func_name : key_sequence_string
        },

    'KEY_BINDING' : {
        # key_sequence_string : func_name
        }
    }


CONFIG_PATH = {
    'dir'       : os.path.join(os.environ['HOME'], '.zPE'),
    'gui_rc'    : os.path.join(os.environ['HOME'], '.zPE', 'gui.conf'),
    'key_emacs' : os.path.join(os.environ['HOME'], '.zPE', 'key.emacs'),
#    'key_vi'    : os.path.join(os.environ['HOME'], '.zPE', 'key.vi'),
    'key_other' : os.path.join(os.environ['HOME'], '.zPE', 'key.other'),
    }

def read_rc():
    __CK_CONFIG()

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
                if v in DEFAULT_FUNC_KEY_BIND:
                    Config[label][k] = v
                else:
                    Config[label][k] = DEFAULT['MISC']['KEY_BINDING']
                    sys.stderr.write('CONFIG WARNING: {0}: Invalid key binding style.\n'.format(v))

            elif k == 'tab_on':
                if v in [ 'on', 'off' ]:
                    Config[label][k] = v
                else:
                    Config[label][k] = DEFAULT['MISC']['TAB_ON']
                    sys.stderr.write('CONFIG WARNING: {0}: Invalid TAB switch.\n'.format(v))

            elif k == 'tab_mode':
                if v in [ 'all', 'group' ]:
                    Config[label][k] = v
                else:
                    Config[label][k] = DEFAULT['MISC']['TAB_MODE']
                    sys.stderr.write('CONFIG WARNING: {0}: Invalid TAB mode.\n'.format(v))

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

    Config['FUNC_BINDING'] = copy.deepcopy(DEFAULT_FUNC_KEY_BIND[ Config['MISC']['key_binding'] ])
    for line in open(CONFIG_PATH[ 'key_{0}'.format(Config['MISC']['key_binding']) ], 'r'):
        line = line[:-1]        # get rid of the '\n'

        (k, v) = re.split('[ \t]*=[ \t]*', line, maxsplit=1)

        seq = parse_key_binding(v)
        if not seq:
            sys.stderr.write('CONFIG WARNING: {0}: Invalid key sequence.\n'.format(v))
            continue

        v = ' '.join(seq)       # normalize the key sequence

        if k in Config['FUNC_BINDING']:
            if v not in Config['KEY_BINDING']:
                Config['FUNC_BINDING'][k] = v
                Config['KEY_BINDING'][v] = k
            else:
                sys.stderr.write('CONFIG WARNING: {0} = {1}: Conflict with {2} = {1}\n'.format(
                        k, v, Config['KEY_BINDING'][v]
                        ))
        else:
            sys.stderr.write('CONFIG WARNING: {0}: Invalid key binding.\n'.format(k))

    write_rc()


__PATTERN = {
    'terminal' : '''
( BACKSPACE | BackSpace | backspace ) |
( ESCAPE    | Eseape    | escape    ) |
( ENTER     | Enter     | enter     ) |
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

( [Ff] (1[0-2] | [2-9]) )       # F1 ~ F12
''',

    'combo' : '''
( C-M-. | [CM]-. )              # C-M-. / C-. / M-.
''',

    'forbid_emacs' : '''M-x | C-g''',
    }

def parse_key_binding(key_sequence):
    sequence = key_sequence.split()

    if Config['MISC']['key_binding'] == 'other':
        # style::other
        if len(sequence) != 1:
            # style::other must contain only 1 stroke
            return None
    else:
        # style::emacs
        if len(sequence) > 1:
            return None

        for indx in range(len(sequence)):
            if re.match(__PATTERN['forbid_emacs'], sequence[indx], re.VERBOSE):
                # not allow for re-define
                return None

            m_terminal = re.match(__PATTERN['terminal'], sequence[indx], re.VERBOSE)
            m_combo    = re.match(__PATTERN['combo'],    sequence[indx], re.VERBOSE)

            if not (m_terminal or m_combo):
                # not a terminal stroke nor a combo
                return None

            if m_terminal and indx != len(sequence) - 1:
                # terminal stroke is not the last stroke
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
