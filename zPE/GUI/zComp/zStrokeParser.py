# this is the key stroke parser module of the zComponent package

import zPE.GUI.io_encap as io_encap
# this module requires io_encap to have the following APIs:
#
#   norm_path(full_path):       return the normalized absolute path
#

import os, sys, re, copy

import pygtk
pygtk.require('2.0')
import gtk
import gobject


######## ######## ######## ######## ########
########    Pre-defined Constant    ########
######## ######## ######## ######## ########

KEY_BINDING_RULE_MKUP = {
    'emacs' :
'''<b>Meaning of the 'Stroke':</b>
  - 'C-x'   : press 'x' while holding Ctrl
  - 'C-M-x' : press 'x' while holding both Ctrl and Alt
  - 'C-x X' : first press 'x' while holding Ctrl, then
              press 'x' while holding Shift

<b>Limitation:</b>
  - Key sequence cannot start with M-x (run command),
    C-q (escape next key stroke), 'Enter' key, or any
    character you can find on the keyboard
  - Key sequence cannot contain C-g (cancel current action)
  - Only function keys can be prefixed by 'S-' (since they
    do not have "uppercase form"s). Note that 'S-' should be
    directly in front of the function key it associated with
  - Key sequence cannot contain more than one stand-alone
    (i.e. without prefix such as 'C-' or 'M-') function keys

<b>'Stroke' of Function Keys:</b>
  - BackSpace, *Enter*, Escape, Space, Tab
  - Insert, Delete, Home, End, Page_Up, Page_Down
  - Left, Right, Up, Down
  - F1 ~ F12
''',

    'vi'    : '''Not Implemented Yet''',

    'other' :
'''<b>Meaning of the 'Stroke':</b>
  - 'C-x'   : press 'x' while holding Ctrl
  - 'C-M-x' : press 'x' while holding both Ctrl and Alt

<b>Limitation:</b>
  - 'Stroke' cannot be 'Enter' key, 'Esc' key, or any
    character you can find on the keyboard
  - No space allowed in the 'Stroke' definition. Use the
    word 'Space' to bind the Space key on your keyboard
  - Only function keys can be prefixed by 'S-' (since they
    do not have "uppercase form"s). Note that 'S-' should be
    directly in front of the function key it associated with

<b>'Stroke' of Function Keys:</b>
  - BackSpace, *Enter*, *Escape*, Space, Tab
  - Insert, Delete, Home, End, Page_Up, Page_Down
  - Left, Right, Up, Down
  - F1 ~ F12
''',
    }


PUNCT_KEY_MAP = {
    'asciitilde'    : '~',
    'exclam'        : '!',
    'at'            : '@',
    'numbersign'    : '#',
    'dollar'        : '$',
    'percent'       : '%',
    'asciicircum'   : '^',
    'ampersand'     : '&',
    'asterisk'      : '*',
    'parenleft'     : '(',
    'parenright'    : ')',
    'underscore'    : '_',
    'plus'          : '+',
    'grave'         : '`',
    'minus'         : '-',
    'equal'         : '=',
    'braceleft'     : '{',
    'braceright'    : '}',
    'bar'           : '|',
    'bracketleft'   : '[',
    'bracketright'  : ']',
    'backslash'     : '\\',
    'colon'         : ':',
    'quotedbl'      : '"',
    'semicolon'     : ';',
    'apostrophe'    : "'",
    'less'          : '<',
    'greater'       : '>',
    'question'      : '?',
    'comma'         : ',',
    'period'        : '.',
    'slash'         : '/',
    }

FUNC_KEY_MAP = {                # the name (all caps) of the function key : the name gtk returns
    'BACKSPACE' : 'BackSpace',
    'ENTER'     : 'Enter', # is_func_key(stroke, 'Enter') will always be false; this entry is for normalizing func_key
    'ESCAPE'    : 'Escape',
    'SPACE'     : 'space',
    'TAB'       : 'Tab',

    'INSERT'    : 'Insert',
    'DELETE'    : 'Delete',
    'HOME'      : 'Home',
    'END'       : 'End',
    'PAGE_UP'   : 'Page_Up',
    'PAGE_DOWN' : 'Page_Down',

    'LEFT'      : 'Left',
    'RIGHT'     : 'Right',
    'UP'        : 'Up',
    'DOWN'      : 'Down',
    }

SP_FUNC_KEY_MAP = {
    'ACTIVATE'  : {
        'emacs' : 'Return',
#        'vi'    : 'Return',
        'other' : 'Return',
        },

    'CANCEL'  : {
        'emacs' : 'C-g',
#        'vi'    : '',
        'other' : 'Escape',
        },
    }
def is_func_key(stroke, func_key):
    func_key = func_key.upper()
    if func_key not in FUNC_KEY_MAP:
        return None
    return stroke.upper() == FUNC_KEY_MAP[func_key].upper()

def is_sp_func_key(stroke, func_key, style):
    func_key = func_key.upper()
    if func_key not in SP_FUNC_KEY_MAP:
        return None
    if style not in SP_FUNC_KEY_MAP[func_key]:
        return None
    return stroke.upper() == SP_FUNC_KEY_MAP[func_key][style].upper()


__BASE_PATTERN = {              # this is for internal use only; see KEY_RE_PATTERN below
    'func_key' : r'''
(?: BACKSPACE | BackSpace | backspace ) |
(?: ESCAPE    | Escape    | escape    ) |
(?: SPACE     | Space     | space     ) |
(?: TAB       | Tab       | tab       ) |

(?: INSERT    | Insert    | insert    ) |
(?: DELETE    | Delete    | delete    ) |
(?: HOME      | Home      | home      ) |
(?: END       | End       | end       ) |
(?: PAGE_UP   | Page_Up   | page_up   ) |
(?: PAGE_DOWN | Page_Down | page_down ) |

(?: LEFT      | Left      | left      ) |
(?: RIGHT     | Right     | right     ) |
(?: UP        | Up        | up        ) |
(?: DOWN      | Down      | down      ) |

(?: [Ff] (1[0-2] | [2-9]) )             # F1 ~ F12
''',

    'activate' : r''' ENTER | Enter | enter ''',        # for all styles
    'cancel_e' : r''' C-g ''',                          # only for style::emacs
    'cancel_o' : r''' ESCAPE | Escape | escape ''',     # only for style::other

    'printable' : r'''
[\x21-\x7e]                             # all chars that are printed on the keyboard
''',
    }

KEY_RE_PATTERN = {
    # comment '# 1' and '# 2' means '1' or '2'
    # comment '# 1' and '#   2' means '12' (1 followed by 2)
    'func_key' : r'''^(?:               # anchor to the start
{0}                                     #   function key
)$                                      #     anchor to the end
'''.format(__BASE_PATTERN['func_key']),

    'activate' : r'''^(?:               # anchor to the start
{0}                                     #   activate
)$                                      #      anchor to the end
'''.format(__BASE_PATTERN['activate']),

    'printable' : r'''^(?:              # anchor to the start
{0}                                     #   printable char
)$                                      #     anchor to the end
'''.format(__BASE_PATTERN['printable']),

    'combo' : r'''^(?:                  # anchor to the start
( C-M-(?:S-)? | [CM]-(?:S-)? | S- )     #   C-M-S- / C-S- / M-S- / S- (capture) followed by
( {0} | {1} )                           #     function key or printable char (capture) [check 'S-' vs 'printable' later]
)$                                      #       anchor to the end
'''.format(__BASE_PATTERN['func_key'], __BASE_PATTERN['printable']),

    'forbid_emacs' : r'''^(?:           # anchor to the start
{0}                                     #   cancel
)$                                      #     anchor to the end
'''.format(__BASE_PATTERN['cancel_e']),

    'forbid_emacs_init' : r'''^(?:      # anchor to the start
{0} |                                   #   printable char
M-x |                                   #   run command
C-q |                                   #   escape next stroke
{1} |                                   #   activate
{2}                                     #   cancel
)$                                      #     anchor to the end
'''.format(__BASE_PATTERN['printable'], __BASE_PATTERN['activate'], __BASE_PATTERN['cancel_e']),

    'forbid_other' : r'''^(?:           # anchor to the start
{0} |                                   #   printable char
{1} |                                   #   activate
{2}                                     #   cancel
)$                                      #     anchor to the end
'''.format(__BASE_PATTERN['printable'], __BASE_PATTERN['activate'], __BASE_PATTERN['cancel_o']),
    }

# public API that can help validating a key sequence
def parse_key_binding(key_sequence, style):
    sequence = key_sequence.split()

    if style == 'emacs':
        # style::emacs
        if not len(sequence):
            return None

        if re.match(KEY_RE_PATTERN['forbid_emacs_init'], sequence[0], re.X):
            # not allow for re-define as starting of a combo
            return None

        for indx in range(len(sequence)):
            if re.match(KEY_RE_PATTERN['forbid_emacs'], sequence[indx], re.X):
                # not allow for re-define
                return None

            m_func_key  = re.match(KEY_RE_PATTERN['func_key'],  sequence[indx], re.X)
            m_activate  = re.match(KEY_RE_PATTERN['activate'],  sequence[indx], re.X)

            m_printable = re.match(KEY_RE_PATTERN['printable'], sequence[indx], re.X)
            m_combo     = re.match(KEY_RE_PATTERN['combo'],     sequence[indx], re.X)

            if not (m_func_key or m_activate or m_printable or m_combo):
                # not a func_key stroke, activate stroke, printable, nor a combo
                return None

            if m_combo:
                sq_prefix = m_combo.group(1)
                sq_stroke = m_combo.group(2)
            else:
                sq_prefix = ''
                sq_stroke = sequence[indx]

            # re-matching stroke part for normalization purpose
            m_func_key  = re.match(KEY_RE_PATTERN['func_key'],  sq_stroke, re.X)
            m_activate  = re.match(KEY_RE_PATTERN['activate'],  sq_stroke, re.X)

            if m_combo and sq_prefix[-2:] == 'S-' and not m_func_key:
                # 'S-' can only be in the prefix if followed by a func_key
                return None

            if m_func_key or m_activate:
                if indx != len(sequence) - 1:
                    # func_key stroke or activate stroke need to be the last stroke
                    return None
                elif m_func_key:
                    # normalize func_key stroke
                    sq_stroke = sq_stroke.upper()
                    if sq_stroke in FUNC_KEY_MAP:
                        sq_stroke = FUNC_KEY_MAP[sq_stroke]
                else:
                    # normalize activate stroke
                    sq_stroke = 'Enter'

            sequence[indx] = sq_prefix + sq_stroke

    elif style == 'vi':
        # style::vi
        return None             # not supported yet

    else:
        # style::other
        if len(sequence) != 1:
            # style::other must contain only 1 stroke
            return None

        if re.match(KEY_RE_PATTERN['forbid_other'], sequence[0], re.X):
            # not allow for re-define
            return None

        m_func_key  = re.match(KEY_RE_PATTERN['func_key'], sequence[0], re.X)
        m_combo     = re.match(KEY_RE_PATTERN['combo'],    sequence[0], re.X)

        if not (m_func_key or m_combo):
            # not a func_key stroke nor a combo
            return None

        if m_combo:
            sq_prefix = m_combo.group(1)
            sq_stroke = m_combo.group(2)
        else:
            sq_prefix = ''
            sq_stroke = sequence[0]

        # re-matching stroke part for normalization purpose
        m_func_key  = re.match(KEY_RE_PATTERN['func_key'],  sq_stroke, re.X)

        if m_func_key:
            # normalize func_key stroke
            sq_stroke = sq_stroke.upper()
            if sq_stroke in FUNC_KEY_MAP:
                sq_stroke = FUNC_KEY_MAP[sq_stroke]

        sequence[0] = sq_prefix + sq_stroke

    return sequence


######## ######## ######## ######## ########
########      zStrokeListener       ########
######## ######## ######## ######## ########

class zStrokeListener(gobject.GObject):
    '''
    A stroke parser that listens all key stroke and process them
    according to the pre-defined rules.

    lookup strategy:
        0) listen on activate key and cancel key. if either is found, emit
           the corresponding signal with message 'Accept' / 'Quit'

        1) listen to all strokes in zStrokeListener.__key_func_binding
           (set by zStrokeListener.set_key_binding())

        2) for a successful catch, search `listener.is_enabled_func` for
           the function that is binded to the stroke; only if no match,
           fall through to search `zStrokeListener.global_is_enabled_func`

           a) for a successful match while the value is True, the function
              is considered "enabled". search `self.func_callback_map` and
              `zSplitWindow.global_func_callback_map` for callback

              -) if matches, emit 'z_activate' and call the callback as
                 class closure (called after 'connect' handler but before
                 'connect_after' handler)

              -) if partially matches (match the start of a combo), emit
                 'z_activate' with message 'z_combo'

              -) if no match at all, emit 'z_cancel' with message
                 'function not implemented'

           b) if the matched value is False or no match at all, the function
              is considered "disabled"; emit 'z_cancel' with message
              'function is disabled'

        either 'z_activate' or 'z_cancel' require the (connected) callback to be:
            def callback(widget, msg, *data)
        and the registered (binded) callback to be:
            def callback(msg)
        where msg is a dict containing all messages generated during
        the listenning process.

        keys in msg:
          'style'           : the current key-binding style

          'widget'          : the widget that cause the signal to be emitted
          'stroke'          : the stroke that cause the signal to be emitted

          'prev_cmd'        : the immidiate precedent command of the current one

          'return_msg'      : the message the listener returned;
                              with 'z_cancel', it's usually a warn / err msg

          'combo_entering'  : whether the widget is on combo_entering
                              (in the middle of a binded key sequence)
          'combo_content'   : the content of the command if on combo_entering
                              otherwise not accessable

          'entry_entering'  : whether the widget is on entry_entering (in the
                              middle of typing a binded function name)
          'entry_content'   : the content of the command if on entry_entering
                              otherwise not accessable

        Note:
            in emacs style, an initial stroke of 'M-x' will cause 'z_activate'
            to be emitted with  msg = { 'z_run_cmd' : widget }
            [no other entrys in the dict so you need to check this first]

            this means you need to prepare an entry for getting the command
            as raw input from user
    '''
    __gsignals__ = {
        'z_activate' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        'z_cancel'   : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        }
    def do_z_activate(self, msg):
        '''register self.__z_activate_callback to be the callback before emit 'z_activate' signal'''
        if self.__z_activate_callback:
            self.__z_activate_callback(msg)


    global_is_enabled_func = {
        # func_name : defined_flag
        }
    global_func_callback_map = {
        # func_name : callback
        }

    @staticmethod
    def global_add_func_registry(func_list):
        '''
        this manipulates the global bindings. use:
          obj.add_func_registry(func_list)
        if you only want to add the func_list to a
        specific parser object
        '''
        for func in func_list:
            if func not in zStrokeListener.global_is_enabled_func:
                zStrokeListener.global_is_enabled_func[func] = None

    @staticmethod
    def global_set_func_enabled(func_name, setting):
        '''
        this manipulates the global bindings. use:
          obj.set_func_enabled(func_name, setting)
        if you only want to add the func_key_binding
        to a specific parser object
        '''
        if func_name not in zStrokeListener.global_is_enabled_func:
            raise ReferenceError(''.join([
                        'Function not registered! Register it with: \n',
                        '\tzStrokeListener.global_add_func_registry( [ func_name ] )'
                        ]))
        zStrokeListener.global_is_enabled_func[func_name] = setting

    @staticmethod
    def global_register_func_callback(func_name, callback):
        '''
        this manipulates the global bindings. use:
          obj.register_func_callback(func_name, callback)
        if you only want to add the func_key_binding
        to a specific parser object
        '''
        if func_name not in zStrokeListener.global_is_enabled_func:
            raise ReferenceError(''.join([
                        'Function not registered! Register it with: \n',
                        '\tzStrokeListener.global_add_func_registry( [ func_name ] )'
                        ]))
        zStrokeListener.global_func_callback_map[func_name] = callback


    __style = 'other'           # see zStrokeListener.set_style()
    __key_func_binding = {}     # stroke-to-funcname binding; global; see zStrokeListener.set_key_binding()

    task_list = [               # all supported tasks
        'text', 'func', 'path', 'file', 'dir',
        ]

    def __init__(self):
        super(zStrokeListener, self).__init__()


        self.listener_id = { # see is_listenning_on(), listen_on(), and listen_off() for more info
            # widget : handler_id for 'key-press-event'
            }
        self.listen_task = { # see is_listenning_on(), listen_on(), and listen_off() for more info
            # widget : task
            }

        self.is_enabled_func = {
            # func_name : defined_flag
            }

        self.func_callback_map = {
            # func_name : callback
            }

        self.__z_activate_callback = None
        self.__z_prev_activate_cmd = None # see obj.invalidate_cmd() for more info


        # local vars for the listener
        self.__escaping = False
        self.__ctrl_char_map = {
            'SPACE' : ' ',
            'C-I'   : '\t',
            'C-J'   : '\n',
            'C-M'   : '\r',
            }

        self.__combo_entering = False
        self.__combo_content = ''

        self.__combo_focus_widget    = None
        self.__combo_focus_widget_id = None

        self.__entry_entering = False
        self.__entry_content = ''


    ### key stroke listener API
    @staticmethod
    def get_key_binding():
        return zStrokeListener.__key_func_binding

    @staticmethod
    def set_key_binding(dic):
        zStrokeListener.__key_func_binding = copy.deepcopy(dic)

    @staticmethod
    def get_style():
        return zStrokeListener.__style

    @staticmethod
    def set_style(style):
        zStrokeListener.__style = style


    def add_func_registry(self, func_list):
        for func in func_list:
            if func not in self.is_enabled_func:
                self.is_enabled_func[func] = None
        zStrokeListener.global_add_func_registry(func_list)

    def set_func_enabled(self, func_name, setting):
        if ( func_name not in self.is_enabled_func  and
             func_name not in zStrokeListener.global_is_enabled_func
             ):
            raise ReferenceError(''.join([
                        'Function not registered! Register it with: \n',
                        '\tself.add_func_registry( [ func_name ] ) or\n'
                        '\tzStrokeListener.global_add_func_registry( [ func_name ] )'
                        ]))
        self.is_enabled_func[func_name] = setting

    def register_func_callback(self, func_name, callback):
        '''this register a func name to an actual callback function'''
        if ( func_name not in self.is_enabled_func  and
             func_name not in zStrokeListener.global_is_enabled_func
             ):
            raise ReferenceError(''.join([
                        'Function not registered! Register it with: \n',
                        '\tself.add_func_registry( [ func_name ] )  or\n',
                        '\tzStrokeListener.global_add_func_registry( [ func_name ] )'
                        ]))
        self.func_callback_map[func_name] = callback


    def is_listenning_on(self, widget):
        return widget in self.listener_id and self.listen_task[widget] or None

    def block_listenning(self, widget):
        if self.is_listenning_on(widget) and widget.handler_is_connected(self.listener_id[widget]):
            widget.handler_block(self.listener_id[widget])

    def unblock_listenning(self, widget):
        if self.is_listenning_on(widget) and widget.handler_is_connected(self.listener_id[widget]):
            widget.handler_unblock(self.listener_id[widget])

    def listen_on(self, widget, task = 'text', init_widget = None):
        '''
        task = 'text'
          - 'text' : on activate, pass 'Enter' keypress to the widget to handle

          - 'func' : on activate, validate the function and invoke callback if success

          - 'path' : on activate, normalize the text entered
          - 'file' : on activate, normalize the text entered and enforce text entered not to be an exsiting dir
          - 'dir'  : on activate, normalize the text entered and enforce text entered not to be an exsiting file

        init_widget = None
            this is only useful when task = 'func' is set. in that case, the function name will be searched in
            init_widget's registry list, instead of widget's.
        '''
        if task not in zStrokeListener.task_list:
            raise ValueError('{0}: invalid task for zStrokeListener instance.'.format(task))

        if self.is_listenning_on(widget):
            raise AssertionError('Listener already binded. use listen_off(widget) to remove it.')

        self.listener_id[widget] = widget.connect('key-press-event', self._sig_key_pressed, task, init_widget)
        self.listen_task[widget] = task # also record the task being listenning

    def listen_off(self, widget):
        if self.is_listenning_on(widget) and widget.handler_is_connected(self.listener_id[widget]):
            widget.disconnect(self.listener_id[widget])
            del self.listener_id[widget]
            del self.listen_task[widget]

    def clear_all(self):
        self.clear_kp_focus_out()

        for (w, h) in self.listener_id.iteritems():
            if w.handler_is_connected(h):
                w.disconnect(h)
        self.listener_id = {}   # clear the list


    def clear_kp_focus_out(self):
        if self.__combo_focus_widget:
            widget = self.__combo_focus_widget # backup
            widget.emit('focus-out-event', gtk.gdk.Event(gtk.gdk.FOCUS_CHANGE))

            # wait for kp_focus_out to be removed
            while self.__combo_focus_widget:
                gtk.main_iteration(False)

            widget.emit('focus-in-event', gtk.gdk.Event(gtk.gdk.FOCUS_CHANGE))
            return True
        else:
            return False


    def invalidate_curr_cmd(self):
        self.__z_prev_activate_cmd = -1 # this value is not possible to occur under normal conditions

    def __update_last_cmd(self, cmd):
        if self.__z_prev_activate_cmd != -1:
            self.__z_prev_activate_cmd = cmd
        else:
            self.__z_prev_activate_cmd = None


    # internal signals
    def _sig_kp_focus_out(self, widget, event):
        '''see _sig_key_pressed() [below] for more information'''
        if ( self.__combo_focus_widget_id  and
             widget.handler_is_connected(self.__combo_focus_widget_id)
             ):
            # widget switched during Commanding
            # cancel it
            self.__combo_entering = False
            self.__combo_content  = ''

            self.__kp_focus_out_rm()

            self.emit('z_cancel', self.__build_msg(widget, 'focus', 'Quit'))
            self.__update_last_cmd('Quit')

    def __kp_focus_out_rm(self):
        '''see _sig_key_pressed() [below] for more information'''
        if ( self.__combo_focus_widget_id  and
             self.__combo_focus_widget.handler_is_connected(self.__combo_focus_widget_id)
             ):
            self.__combo_focus_widget.disconnect(self.__combo_focus_widget_id)

            self.__combo_focus_widget    = None
            self.__combo_focus_widget_id = None



    def _sig_key_pressed(self, widget, event, task, init_widget = None):
#        self.__debug_print_maps()

        if event.type != gtk.gdk.KEY_PRESS:
            return False

        if event.is_modifier:
            return False

        ### generate stroke
        ctrl_mod_mask = gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK

        # check and re-map punctuation mark
        key_name = gtk.gdk.keyval_name(event.keyval)
        if key_name in PUNCT_KEY_MAP:
            # punctuation
            key_name = PUNCT_KEY_MAP[key_name]

        elif key_name.upper() in FUNC_KEY_MAP:
            # function key
            if event.state & gtk.gdk.SHIFT_MASK:
                # only check SHIFT modifier when a function key is pressed
                key_name = 'S-' + key_name

        elif len(key_name) == 1 and key_name.isalpha():
            # letters
            if (event.state & gtk.gdk.LOCK_MASK) == gtk.gdk.LOCK_MASK:
                key_name = key_name.swapcase()

        if (event.state & ctrl_mod_mask) == ctrl_mod_mask:
            stroke = 'C-M-' + key_name

        elif event.state & gtk.gdk.CONTROL_MASK:
            stroke = 'C-' + key_name

        elif event.state & gtk.gdk.MOD1_MASK:
            stroke = 'M-' + key_name

        else:
            stroke = key_name

        if task == 'func':
            self.__entry_entering = True


        # initialize the editable flag
        try:
            w_editable = widget.get_editable()
        except:
            w_editable = None

        ### style-regardless checkings
        # check Cancelling
        if is_sp_func_key(stroke, 'CANCEL', self.get_style()):
            # with any style, this means 'cancel'
            if not init_widget or task != 'func':
                # init_widget not set, or in regular mode (non-mx-mode)
                init_widget = widget
            self.emit('z_cancel', self.__build_msg(init_widget, stroke, 'Quit'))
            self.__update_last_cmd('Quit')

            # on cancelling, reset all modes
            self.__combo_entering = False
            self.__combo_content  = ''

            self.__entry_entering = False
            self.__entry_content  = ''

            return True
        # no Cancelling

        # check Activating
        if ( not self.__combo_entering  and                       # must not on combo-entering, and
             is_sp_func_key(stroke, 'ACTIVATE', self.get_style()) # the activate kay is pressed
             ):
            if task == 'text':
                return False    # pass 'Enter' to the widget to handle

            elif task == 'func':
                # is on M-x commanding
                self.__entry_content = widget.get_text() # update the content backup
                if not init_widget: # set the responing widget
                    init_widget = widget

                local_is_enabled_func   = init_widget.listener.is_enabled_func
                local_func_callback_map = init_widget.listener.func_callback_map

                if self.__is_enabled_func(self.__entry_content, local_is_enabled_func):
                    # is a valid functionality

                    if self.__entry_content in local_func_callback_map:
                        # has registered function
                        self.__z_activate_callback = local_func_callback_map[self.__entry_content]
                        self.emit('z_activate', self.__build_msg(init_widget, stroke, 'Accept'))
                        self.__z_activate_callback = None

                    elif self.__entry_content in zStrokeListener.global_func_callback_map:
                        # has globally registered function
                        self.__z_activate_callback = zStrokeListener.global_func_callback_map[self.__entry_content]
                        self.emit('z_activate', self.__build_msg(init_widget, stroke, 'Accept'))
                        self.__z_activate_callback = None
                    else:
                        self.emit('z_cancel', self.__build_msg(
                                init_widget, stroke, '(function `{0}` not implemented)'.format(self.__entry_content)
                                ))
                else:
                    self.emit('z_cancel', self.__build_msg(
                            init_widget, stroke, '({0}: no such function)'.format(self.__entry_content)
                            ))

                # record the function the init_widget is trying to invoke
                init_widget.listener.__update_last_cmd(self.__entry_content)

                # M-x cmd emitted, reset entering mode
                self.__entry_entering = False
                self.__entry_content  = ''

                return True

            # must be 'file', 'dir', or 'path'
            path_entered = widget.get_text()
            if path_entered:
                # normalize path
                if '"' in path_entered:
                    path_entered = path_entered.replace('"', '')
                path_entered = io_encap.norm_path(path_entered)
                widget.set_text(path_entered)

                if ( (task == 'file' and not os.path.isdir(path_entered) ) or
                     (task == 'dir'  and not os.path.isfile(path_entered)) or
                     (task == 'path')
                     ):
                    self.emit('z_activate', self.__build_msg(widget, stroke, 'Accept'))
                    self.__update_last_cmd('Activate')

                elif self.__is_enabled_func('complete-list'):
                    # list completion is enabled, execute it if mapped
                    if 'complete-list' in self.func_callback_map:
                        self.func_callback_map['complete-list']()
                    elif 'complete-list' in zStrokeListener.global_func_callback_map:
                        zStrokeListener.global_func_callback_map['complete-list']()

            return True
        # no Activating


        ### style-specific checkings
        if self.get_style() == 'emacs':
            # style::emacs

            # check C-q Escaping
            if self.__escaping: # this should guarantee no combo is entering
                try:
                    if w_editable:
                        if self.__is_printable(stroke):
                            insertion = stroke

                        elif stroke.upper() in self.__ctrl_char_map:
                            insertion = self.__ctrl_char_map[stroke.upper()]

                        else:
                            insertion = '' # ignore the rest ctrl chars

                        self.__insert_text(widget, insertion)
                    else:
                        pass    # no need to handle C-q escaping when the widget is not editable
                except:
                    pass # if anything goes wrong, give up the escaping

                self.__escaping = False
                return True
            # no C-q Escaping

            # check M-x Commanding input
            if ( not self.__combo_entering  and
                 self.__entry_entering
                 ):
                # on M-x Commanding, Commanding *MUST NOT* be initiated
                if self.__is_printable(stroke):
                    # regular keypress
                    self.__insert_text(widget , stroke)
                    return True
                elif self.__is_space(stroke):
                    # space
                    self.__insert_text(widget , ' ')
                    return True
                else:
                    # leave the rest checking to commanding
                    pass
            # no active M-x Commanding, or stroke is passed on

            # check initiated Commanding
            if not self.__combo_entering:
                # initiating stroke, check reserved bindings (M-x and C-q)
                if stroke == 'M-x':
                    self.emit('z_activate', { 'z_run_cmd' : widget })
                    return True

                elif stroke == 'C-q':
                    # start C-q Escaping
                    if w_editable:
                        self.__escaping = True
                    else:
                        pass    # no need to handle C-q escaping when the widget is not editable
                    return True

                # not reserved bindings, check forbidden bindings (printable)
                elif self.__is_printable(stroke):
                    # is a printable
                    if w_editable:
                        self.__insert_text(widget, stroke)
                    else:
                        self.emit('z_activate', self.__build_msg(widget, stroke, ''))
                    return True

                # not any reserved or forbidden bindings
                # initiate Commanding
                self.__combo_entering = True
                self.__combo_focus_widget    = widget
                self.__combo_focus_widget_id = widget.connect('focus-out-event', self._sig_kp_focus_out)
            # Commanding initiated

            # on commanding
            # retrieve previous combo, if there is any
            if self.__combo_content:
                # appand previous combo to stroke
                stroke = '{0} {1}'.format(self.__combo_content, stroke)


            # validate stroke sequence
            key_binding = zStrokeListener.__key_func_binding # make a reference

            if stroke in key_binding  and  self.__is_enabled_func(key_binding[stroke]):
                # is a valid functionality
                self.__combo_content = stroke
                self.__kp_focus_out_rm() # release focus requirement

                if key_binding[stroke] in self.func_callback_map:
                    # has registered functions
                    self.__z_activate_callback = self.func_callback_map[key_binding[stroke]]
                    self.emit('z_activate', self.__build_msg(widget, stroke, ''))
                    self.__z_activate_callback = None

                elif key_binding[stroke] in zStrokeListener.global_func_callback_map:
                    # has globally registered function
                    self.__z_activate_callback = zStrokeListener.global_func_callback_map[key_binding[stroke]]
                    self.emit('z_activate', self.__build_msg(widget, stroke, ''))
                    self.__z_activate_callback = None
                else:
                    self.emit('z_cancel', self.__build_msg(
                            widget, stroke, '(function `{0}` not implemented)'.format(key_binding[stroke])
                            ))

                # record the function the widget is trying to invoke
                self.__update_last_cmd(key_binding[stroke])

                # cmd emitted, reset combo mode
                self.__combo_entering = False
                self.__combo_content  = ''

                return True
            else:
                # not a valid stroke sequence so far
                found = False
                for key in key_binding:
                    if key.startswith(stroke):
                        # part of a valid stroke sequence
                        self.emit('z_activate', self.__build_msg(widget, stroke, 'z_combo'))

                        found = True
                        break

                if found:
                    self.__combo_content = stroke
                    return True
                else:
                    # not a valid stroke sequence *AT ALL*
                    self.__kp_focus_out_rm() # release focus requirement

                    if not self.__combo_content:
                        # initiate stroke, do not eat it
                        self.__combo_entering = False

                        if self.__is_space(stroke):
                            # space
                            if w_editable:
                                self.__insert_text(widget , ' ')
                            else:
                                self.emit('z_activate', self.__build_msg(widget, ' ', ''))
                            return True
                        else:
                            # not regular keypress nor space, pass it to the widget
                            self.__update_last_cmd(None)
                            return False
                    else:
                        # has previous combo, eat the current combo
                        self.emit('z_cancel', self.__build_msg(
                                widget, stroke, stroke + ' is undefined!'
                                ))
                        self.__update_last_cmd(None)

                        # cmd terminated, reset combo mode
                        self.__combo_entering = False
                        self.__combo_content  = ''

                        return True

        elif self.get_style() == 'vi':
            # style::vi
            return False        # not implemetad yet

        else:
            # style::other
            key_binding = zStrokeListener.__key_func_binding # make a reference

            if ( stroke in key_binding  and                 # is a binded key stroke
                 self.__is_enabled_func(key_binding[stroke])# is a valid functionality
                 ):
                if key_binding[stroke] in self.func_callback_map:
                    # has registered functions
                    self.__z_activate_callback = self.func_callback_map[key_binding[stroke]]
                    self.emit('z_activate', self.__build_msg(widget, stroke, ''))
                    self.__z_activate_callback = None

                elif key_binding[stroke] in zStrokeListener.global_func_callback_map:
                    # has globally registered function
                    self.__z_activate_callback = zStrokeListener.global_func_callback_map[key_binding[stroke]]
                    self.emit('z_activate', self.__build_msg(widget, stroke, ''))
                    self.__z_activate_callback = None
                else:
                    self.emit('z_cancel', self.__build_msg(
                            widget, stroke, '(function `{0}` not implemented)'.format(key_binding[stroke])
                            ))
                # record the function the widget is trying to invoke
                self.__update_last_cmd(key_binding[stroke])

                return True
            else:
                if self.__is_printable(stroke):
                    # regular keypress
                    if w_editable:
                        self.__insert_text(widget , stroke)
                    else:
                        self.emit('z_activate', self.__build_msg(widget, stroke, ''))
                    return True
                elif self.__is_space(stroke):
                    # space
                    if w_editable:
                        self.__insert_text(widget , ' ')
                    else:
                        self.emit('z_activate', self.__build_msg(widget, ' ', ''))
                    return True
                else:
                    # not regular keypress nor space, pass it to the widget
                    self.__update_last_cmd(None)
                    return False

        raise LookupError('{0}: key stroke not captured or processed.\n\tPlease report this as a bug.'.format(stroke))
    ### end of key stroke listener API


    ### supporting function
    def __build_msg(self, widget, stroke, return_msg):
        msg = {
            'style'             : self.get_style(),

            'widget'            : widget,
            'stroke'            : stroke,
            'prev_cmd'          : self.__z_prev_activate_cmd,

            'return_msg'        : return_msg,
            }

        if self.__combo_entering:
            msg['combo_entering'] = True
            msg['combo_content']  = self.__combo_content
        else:
            msg['combo_entering'] = False

            if self.__entry_entering:
                msg['entry_entering'] = True
                msg['entry_content']  = self.__entry_content
            else:
                msg['entry_entering'] = False

        return msg

    def __insert_text(self, widget, insertion):
        widget.insert_text(insertion)
        if self.__entry_entering:
            # update the content backup
            self.__entry_content = widget.get_text()

        # update prev_cmd
        self.__update_last_cmd(None)


    def __is_enabled_func(self, func, local_list = None):
        if not local_list:
            local_list = self.is_enabled_func
        if func in local_list:
            # if locally registered, do not search in global settings
            return local_list[func]

        elif func in zStrokeListener.global_is_enabled_func:
            # if not locally registered but globally registered
            return zStrokeListener.global_is_enabled_func[func]
        else:
            # if neither locally nor globally registered
            return False

    def __is_printable(self, stroke):
        return re.match(KEY_RE_PATTERN['printable'], stroke, re.X)

    def __is_space(self, stroke):
        return is_func_key(stroke, 'Space')


    def __debug_print_maps(self):
        sys.stderr.write('==== zStrokeListener Debugger :: Print Maps ====\n')

        sys.stderr.write('\nzStrokeListener.__key_func_binding:\n')
        for (k, v) in zStrokeListener.__key_func_binding.iteritems():
            sys.stderr.write('  {0:<16} => {1}\n'.format(k, v))

        enabled  = []
        disabled = []
        for (k, v) in self.is_enabled_func.iteritems():
            if v:
                enabled.append(k)
            else:
                disabled.append(k)
        sys.stderr.write('\nself.is_enabled_func: [enabled]\n')
        for indx in range(len(enabled)):
            sys.stderr.write('  {0:<22}'.format(enabled[indx] + ','))
            if indx % 3 == 2:
                sys.stderr.write('\n')
        sys.stderr.write('\nself.is_enabled_func: [disabled]\n')
        for indx in range(len(disabled)):
            sys.stderr.write('  {0:<22}'.format(disabled[indx] + ','))
            if indx % 3 == 2:
                sys.stderr.write('\n')

        enabled  = []
        disabled = []
        for (k, v) in zStrokeListener.global_is_enabled_func.iteritems():
            if v:
                enabled.append(k)
            else:
                disabled.append(k)
        sys.stderr.write('\nzStrokeListener.global_is_enabled_func: [enabled]\n')
        for indx in range(len(enabled)):
            sys.stderr.write('  {0:<22}'.format(enabled[indx] + ','))
            if indx % 3 == 2:
                sys.stderr.write('\n')
        sys.stderr.write('\nzStrokeListener.global_is_enabled_func: [disabled]\n')
        for indx in range(len(disabled)):
            sys.stderr.write('  {0:<22}'.format(disabled[indx] + ','))
            if indx % 3 == 2:
                sys.stderr.write('\n')

        sys.stderr.write('\nself.func_callback_map:\n')
        for (k, v) in self.func_callback_map.iteritems():
            sys.stderr.write('  {0:<21} => {1}\n'.format(k, v))

        sys.stderr.write('\n================================================\n')
    ### end of supporting function
gobject.type_register(zStrokeListener)
