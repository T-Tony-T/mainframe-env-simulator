# this is the key stroke parser module of the zComponent package

import sys, re, copy

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

<b>'Stroke' of Function Keys:</b>
  - BackSpace, *Enter*, *Escape*, Space, Tab
  - Insert, Delete, Home, End, Page_Up, Page_Down
  - Left, Right, Up, Down
  - F1 ~ F12
''',
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
    'RIGHT'     : 'Rignt',
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
( BACKSPACE | BackSpace | backspace ) |
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
    'func_key' : r'''^(                 # anchor to the start
{0}                                     #   function key
)$                                      #     anchor to the end
'''.format(__BASE_PATTERN['func_key']),

    'activate' : r'''^(                 # anchor to the start
{0}                                     #   activate
)$                                      #      anchor to the end
'''.format(__BASE_PATTERN['activate']),

    'printable' : r'''^(                # anchor to the start
{0}                                     #   printable char
)$                                      #     anchor to the end
'''.format(__BASE_PATTERN['printable']),

    'combo' : r'''^(                    # anchor to the start
( C-M- | [CM]- )                        #   C-M- / C- / M- followed by
( {0} | {1} )                           #     function key or printable char
)$                                      #       anchor to the end
'''.format(__BASE_PATTERN['func_key'], __BASE_PATTERN['printable']),

    'forbid_emacs' : r'''^(             # anchor to the start
{0}                                     #   cancel
)$                                      #     anchor to the end
'''.format(__BASE_PATTERN['cancel_e']),

    'forbid_emacs_init' : r'''^(        # anchor to the start
{0} |                                   #   printable char
M-x |                                   #   run command
C-q |                                   #   escape next stroke
{1} |                                   #   activate
{2}                                     #   cancel
)$                                      #     anchor to the end
'''.format(__BASE_PATTERN['printable'], __BASE_PATTERN['activate'], __BASE_PATTERN['cancel_e']),

    'forbid_other' : r'''^(             # anchor to the start
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

            if m_func_key or m_activate:
                if indx != len(sequence) - 1:
                    # func_key stroke or activate stroke need to be the last stroke
                    return None
                elif m_func_key:
                    # normalize func_key stroke
                    sequence[indx] = sequence[indx].upper()
                    if sequence[indx] in FUNC_KEY_MAP:
                        sequence[indx] = FUNC_KEY_MAP[sequence[indx]]
                else:
                    # normalize activate stroke
                    sequence[indx] = 'Enter'

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

        m_func_key  = re.match(KEY_RE_PATTERN['func_key'],  sequence[0], re.X)
        m_combo     = re.match(KEY_RE_PATTERN['combo'],     sequence[0], re.X)

        if m_func_key:
            # normalize func_key stroke
            sequence[0] = sequence[0].upper()
            if sequence[0] in FUNC_KEY_MAP:
                sequence[0] = FUNC_KEY_MAP[sequence[0]]
        elif not m_combo:
            # not a func_key stroke nor a combo
            return None

    return sequence


######## ######## ######## ######## ########
########      zStrokeListener       ########
######## ######## ######## ######## ########

class zStrokeListener(gobject.GObject):
    '''
    A stroke parser that listens all key stroke and process them
    according to the pre-defined rules ()

    lookup structure:
        1) listen to all strokes defined in zStrokeListener.__key_func_binding (set by zStrokeListener.set_key_binding())

        2) for a successful catch, search `listener.is_enabled_func` for the function
           only if no match, fall through to search in `zStrokeListener.global_is_enabled_func`

           a) for a successful match while the value is set to True, the function is considered "enabled"
              search `self.func_callback_map` and `zSplitWindow.global_func_callback_map` for callback

              -) if matches, emit 'z_activate' and call the callback as class closure
                 (called after 'connect' handler but before 'connect_after' handler)

              -) if partially matches (match the start of a combo), emit 'z_activate'
                 with message 'z_combo'

              -) otherwise, emit 'z_cancel' with message 'function not implemented'

           b) if the matched value is False or no match at all, the function is considered "disabled"
              emit 'z_cancel' with message 'function is disabled'

        either 'z_activate' or 'z_cancel' require the callback to be:
          def callback(widget, msg, *data)
        where msg is a dict containing all messages generated during the parsing

        keys in msg:
          'style'               : the current key-binding style

          'widget'              : the widget that cause the signal to be emitted
          'stroke'              : the stroke that cause the signal to be emitted

          'return_msg'          : the message the listener returned;
                                  with 'z_cancel', it is usually a warning or an error message

          'combo_entering'      : whether the widget is on combo_entering (in the middle of a binded key sequence)
          'combo_content'       : the content of the command if on combo_entering; otherwise not accessable

          'entry_entering'      : whether the widget is on entry_entering (in the middle of typing a binded function name)
          'entry_content'       : the content of the command if on entry_entering; otherwise not accessable

        Note: in emacs style, an initial stroke of 'M-x' will cause 'z_activate' to be emitted with
              msg = { 'z_run_cmd' : widget }  [no other entrys in the dict so you probably want to check this first]
              this means you need to prepare an entry for getting the command as raw input from user.
    '''
    __gsignals__ = {
        'z_activate' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        'z_cancel'   : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        }
    def do_z_activate(self, msg):
        '''register self.__z_activate_callback to be the callback before emit 'z_activate' signal'''
        if self.__z_activate_callback:
            self.__z_activate_callback()


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


    def __init__(self, complete = None):
        '''
        complete = None
            the completion module the parser can use. If set, 'complete'
            will try fill the matching content and 'complete-list' will
            show a list of all matching terms.
        '''
        super(zStrokeListener, self).__init__()

        self.complete = complete

        self.listener_id = { # see is_listenning_on(), listen_on(), and listen_off() for more info
            # widget : handler_id for 'key-press-event'
            }

        self.is_enabled_func = {
            # func_name : defined_flag
            }

        self.func_callback_map = {
            # func_name : callback
            }

        self.__z_activate_callback = None

        # local vars for the listener
        self.__escaping = False
        self.__ctrl_char_map = {
            'C-I' : '\t',
            'C-J' : '\n',
            'C-M' : '\r',
            }

        self.__combo_entering = False
        self.__combo_content = ''
        self.__combo_widget_focus_id = None

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
        return widget in self.listener_id

    def listen_on(self, widget, task = None):
        '''
        task = None
            the task that the entry is asked to complete.
            Could be one of the following:
              -  None  : no special rules applied and pass 'Enter' keypress to the widget.
              - 'text' : apply text completion and pass 'Enter' keypress to the widget.

              - 'func' : apply function completion

              - 'path' : apply path completion
              - 'file' : same to 'path' except text entered must not be a dir.
              - 'dir'  : same to 'path' except text entered must not be a file.
        '''
        if self.is_listenning_on(widget):
            raise AssertionError('Listener already binded. use listen_off(widget) to remove it.')
        self.listener_id[widget] = widget.connect('key-press-event', self._sig_key_pressed, task)

    def listen_off(self, widget):
        if self.is_listenning_on(widget) and widget.handler_is_connected(self.listener_id[widget]):
            widget.disconnect(self.listener_id[widget])
            del self.listener_id[widget]

    def clear_all(self):
        for (w, h) in self.listener_id.iteritems():
            if w.handler_is_connected(h):
                w.disconnect(h)
        self.listener_id = {}   # clear the list


    # internal signals
    def _sig_kp_focus_out(self, widget, event):
        '''see _sig_key_pressed() [below] for more information'''
        if ( self.__combo_widget_focus_id  and
             widget.handler_is_connected(self.__combo_widget_focus_id)
             ):
            # widget switched during Commanding
            # cancel it
            self.__combo_entering = False
            self.__combo_content  = ''

            self.__kp_focus_out_rm(widget)

            self.emit('z_cancel', self.__build_msg(widget, 'focus', 'Quit'))

    def __kp_focus_out_rm(self, widget):
        '''see _sig_key_pressed() [below] for more information'''
        if ( self.__combo_widget_focus_id  and
             widget.handler_is_connected(self.__combo_widget_focus_id)
             ):
            widget.disconnect(self.__combo_widget_focus_id)
            self.__combo_widget_focus_id = None



    def _sig_key_pressed(self, widget, event, task):
#        self.__debug_print_maps()

        if event.type != gtk.gdk.KEY_PRESS:
            return False

        if event.is_modifier:
            return False

        ### generate stroke
        ctrl_mod_mask = gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK

        if (event.state & ctrl_mod_mask) == ctrl_mod_mask:
            stroke = 'C-M-' + gtk.gdk.keyval_name(event.keyval)

        elif event.state & gtk.gdk.CONTROL_MASK:
            stroke = 'C-' + gtk.gdk.keyval_name(event.keyval)

        elif event.state & gtk.gdk.MOD1_MASK:
            stroke = 'M-' + gtk.gdk.keyval_name(event.keyval)

        else:
            stroke = gtk.gdk.keyval_name(event.keyval)


        ### style-regardless checkings
        # check Cancelling
        if is_sp_func_key(stroke, 'CANCEL', self.get_style()):
            # with any style, this means 'cancel'
            self.emit('z_cancel', self.__build_msg(widget, stroke, 'Quit'))

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
            if task in [ None, 'text' ]:
                return False    # pass 'Enter' to the widget to handle

            elif task == 'func':
                # is on M-x commanding
                if self.__is_enabled_func(self.__entry_content):
                    # is a valid functionality

                    if self.__entry_content in self.func_callback_map:
                        # has registered function
                        self.__z_activate_callback = self.func_callback_map[self.__entry_content]
                        self.emit('z_activate', self.__build_msg(widget, stroke, ''))
                        self.__z_activate_callback = None

                    elif self.__entry_content in zStrokeListener.global_func_callback_map:
                        # has globally registered function
                        self.__z_activate_callback = zStrokeListener.global_func_callback_map[self.__entry_content]
                        self.emit('z_activate', self.__build_msg(widget, stroke, ''))
                        self.__z_activate_callback = None
                    else:
                        self.emit('z_cancel', self.__build_msg(
                                widget, stroke, '(function `{0}` not implemented)'.format(self.__entry_content)
                                ))
                else:
                    self.emit('z_cancel', self.__build_msg(
                            widget, stroke, '({0}: no such function)'.format(self.__entry_content)
                            ))

                # M-x cmd emitted, reset entering mode
                self.__entry_entering = False
                self.__entry_content  = ''

                return True

            text_entered = widget.get_text()
            if text_entered:
                if ( (task == 'file' and not os.path.isdir(text_entered) ) or
                     (task == 'dir'  and not os.path.isfile(text_entered)) or
                     task in [ 'path' ] # tasks that require no checkings
                     ):
                    self.emit('z_activate', self.__build_msg(widget, stroke, ''))
                elif self.complete:
                    self.complete.popup_comp_list()

            return True
        # no Activating

        ### style-specific checkings
        if self.get_style() == 'emacs':
            # style::emacs

            # check C-q Escaping
            if not self.__combo_entering and self.__escaping:
                try:
                    if widget.get_editable():
                        if re.match(r'^[\x20-\x7e]$', stroke):
                            insertion = stroke
                        elif stroke.upper() in self.__ctrl_char_map:
                            insertion = self.__ctrl_char_map[stroke.upper()]
                        else:
                            insertion = '' # ignore the rest ctrl chars

                        self.__insert_text(widget, insertion)
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
                if re.match(r'^[\x20-\x7e]$', stroke):
                    # regular keypress
                    self.__insert_text(widget ,stroke)
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
                    self.__escaping = True
                    return True
                # not reserved bindings

                # initiate Commanding
                self.__combo_entering = True
                self.__combo_widget_focus_id = widget.connect('focus-out-event', self._sig_kp_focus_out)
            # Commanding initiated


            # retrive previous combo, if there is any
            if self.__combo_content:
                # appand previous combo to stroke
                stroke = '{0} {1}'.format(self.__combo_content, stroke)


            # validate stroke sequence
            key_binding = zStrokeListener.__key_func_binding # make a reference

            if stroke in key_binding  and  self.__is_enabled_func(key_binding[stroke]):
                # is a valid functionality
                self.__combo_content = stroke
                self.__kp_focus_out_rm(widget) # release focus requirement

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
                    self.__kp_focus_out_rm(widget) # release focus requirement

                    if not self.__combo_content:
                        # initiate stroke, pass it on
                        self.__combo_entering = False
                        return False
                    else:
                        # has previous combo, eat the current combo
                        self.emit('z_cancel', self.__build_msg(
                                widget, stroke, stroke + ' is undefined!'
                                ))

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
                return True
            else:
                return False

        raise LookupError('{0}: key stroke not captured or processed.'.format(stroke))
    ### end of key stroke listener API


    ### supporting function
    def __build_msg(self, widget, stroke, return_msg):
        msg = {
            'style'             : self.get_style(),

            'widget'            : widget,
            'stroke'            : stroke,

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

    def __is_enabled_func(self, func):
        if func in self.is_enabled_func:
            # if locally registered, do not search in global settings
            return self.is_enabled_func[func]

        elif func in zStrokeListener.global_is_enabled_func:
            # if not locally registered but globally registered
            return zStrokeListener.global_is_enabled_func[func]
        else:
            # if neither locally nor globally registered
            return False


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


######## ######## ######## ######## ########
########          zComplete         ########
######## ######## ######## ######## ########

class zComplete(object):
    '''A gtk.Entry that has additional methods'''
    def __init__(self):

        self.__comp_list = []           # completion list
        self.__try_completing = 0       # how many times tring completion; reset to 0 if completion success

