# this is the text module of the zComponent package

from zBase import z_ABC, zTheme
from zStrokeParser import zStrokeListener, zComplete

import os, re
import pygtk
pygtk.require('2.0')
import gtk
import gobject


######## ######## ######## ######## ########
########           zEntry           ########
######## ######## ######## ######## ########

class zEntry(gtk.Entry):
    '''A gtk.Entry that has additional methods'''
    global_func_list = [
        'complete',             # complete the current typing
        'complete_list',        # show completion list of the current typing;
                                # whether set of not, two successive fail in complete will cause the list to show

        'delete_char_backward', # delete prev char
        'delete_char_forward',  # delete next char

        'delete_word_backward', # delete to start of curr word, or delete prev word if not in one
        'delete_word_forward',  # delete to end of curr word, or delete next word if not in one

        'delete_line_backward', # delete to start of curr line, or delete curr line if at line end
        'delete_line_forward',  # delete to end of curr line, or delete curr line if at line start,

        'delete_para_backward', # delete to start of curr para, or delete prev para if not in one or at para start
        'delete_para_forward',  # delete to end of curr para, or delete next para if not in one or at para end
        ]
    # only make the following function bindable, no actual binding applied
    zStrokeListener.global_add_func_registry(global_func_list)

    def __init__(self):
        super(zEntry, self).__init__()

        self.completer = zComplete(self)
        self.listener = zStrokeListener()

        self.set_editable(True) # default editable

        # register callbacks for function bindings
        self.default_func_callback = {
            'complete'              : lambda *arg: self.complete(),
            'complete_list'         : lambda *arg: self.complete_list(),
        
            'delete_char_backward'  : lambda *arg: self.delete_backward('char'),
            'delete_char_forward'   : lambda *arg: self.delete_forward( 'char'),
            'delete_word_backward'  : lambda *arg: self.delete_backward('word'),
            'delete_word_forward'   : lambda *arg: self.delete_forward( 'word'),
            'delete_line_backward'  : lambda *arg: self.delete_backward('line'),
            'delete_line_forward'   : lambda *arg: self.delete_forward( 'line'),
            'delete_para_backward'  : lambda *arg: self.delete_backward('para'),
            'delete_para_forward'   : lambda *arg: self.delete_forward( 'para'),
            }
        for (func, cb) in self.default_func_callback.iteritems():
            self.listener.register_func_callback(func, cb)


    ### overridden function definition
    def complete(self):
        self.completer.complete()

    def complete_list(self):
        self.completer.complete_list()

    def set_completion_task(self, task):
        if task not in zComplete.task_list:
            raise ValueError('{0}: invalid task for zComplete instance.'.format(task))
        else:
            self.completer.set_completion_task(task)


    def is_listenning(self):
        return self.listener.is_listenning_on(self)

    def listen_on_task(self, task = None, init_widget = None):
        self.listener.listen_on(self, task, init_widget)

    def listen_off(self):
        self.listener.listen_off(self)


    def insert_text(self, text):
        pos = self.get_position()
        super(zEntry, self).insert_text(text, pos)
        self.set_position(pos + len(text))


    # no overridden for is_focus()
    def grab_focus(self):
        pos = self.get_position()
        super(zEntry, self).grab_focus()
        self.set_position(pos)


    # no overridden for get_text()
    def set_text(self, text):
        super(zEntry, self).set_text(text)
        self.set_position(-1)


    # no overridden for get_editable()
    def set_editable(self, setting):
        super(zEntry, self).set_editable(setting)
        self.set_property('can-default', setting)
        self.set_property('can-focus', setting)

        # enable/disable the editor related function bindings
        for func in zEntry.global_func_list:
            self.listener.set_func_enabled(func, setting)
    ### end of overridden function definition


    ### editor related API
    def delete_backward(self, task = 'char'):
        end_pos = self.get_position()

        if task == 'char':
            start_pos = end_pos - 1

        elif task == 'word':
            letter = r'[a-zA-Z0-9]'
            start_pos = end_pos
            if self.is_out_word(letter) or self.is_word_start(letter):
                # outside of a word, or at word start => move to prev work end
                start_pos = self.__get_word_start(start_pos, r'[^a-zA-Z0-9]')
            # move to word start
            start_pos = self.__get_word_start(start_pos, letter)

        elif task in [ 'line', 'para' ]:
            start_pos = 0

        else:
            raise KeyError('{0}: invalid task for delete pattern.'.format(task))

        self.delete_text(start_pos, end_pos)

    def delete_forward(self, task = 'char'):
        start_pos = self.get_position()

        if task == 'char':
            end_pos = start_pos + 1

        elif task == 'word':
            letter = r'[a-zA-Z0-9]'
            end_pos = start_pos
            if self.is_out_word(letter) or self.is_word_end(letter):
                # outside of a word, or at word end => move to next work start
                end_pos = self.__get_word_end(end_pos, r'[^a-zA-Z0-9]')
            # move to word start
            end_pos = self.__get_word_end(end_pos, letter)

        elif task in [ 'line', 'para' ]:
            end_pos = -1

        else:
            raise KeyError('{0}: invalid task for delete pattern.'.format(task))

        self.delete_text(start_pos, end_pos)


    def get_current_word(self, letter = r'\S'):
        curr = self.get_position()
        start = self.__get_word_start(curr, letter)
        return self.get_chars(start, curr)

    def set_current_word(self, word, letter = r'\S'):
        curr = self.get_position()
        start = self.__get_word_start(curr, letter)

        self.select_region(start, curr)
        self.delete_selection()
        self.insert_text(word)


    def is_word_start(self, letter = r'\S'):
        return self.__test_cursor_anchor(self.get_position(), False, True, letter)

    def is_in_word(self, letter = r'\S'):
        return self.__test_cursor_anchor(self.get_position(), True, True, letter)

    def is_word_end(self, letter = r'\S'):
        return self.__test_cursor_anchor(self.get_position(), True, False, letter)

    def is_out_word(self, letter = r'\S'):
        return self.__test_cursor_anchor(self.get_position(), False, False, letter)
    ### end of editor related API


    ### supporting function
    def __get_word_start(self, pos, letter = r'\S'):
        if not pos:
            return 0            # at start of the entry
        if not re.match(letter, self.get_chars(pos - 1, pos)):
            raise ValueError('outside of word or at word start')

        while pos > 0 and re.match(letter, self.get_chars(pos - 1, pos)):
            pos -= 1
        return pos

    def __get_word_end(self, pos, letter = r'\S'):
        if pos == self.get_text_length():
            return pos          # at end of the entry
        if not re.match(letter, self.get_chars(pos, pos + 1)):
            raise ValueError('outside of word or at word end')

        while pos > 0 and re.match(letter, self.get_chars(pos, pos + 1)):
            pos += 1
        return pos

    def __test_cursor_anchor(self, pos, prev_w, next_w, letter = r'\S'):
        prev = self.get_chars(pos - 1, pos)
        next = self.get_chars(pos, pos + 1)

        return (
            prev_w == bool(re.match(letter, prev)) and
            next_w == bool(re.match(letter, next))
            )
    ### end of supporting function


######## ######## ######## ######## ########
########         zLastLine          ########
######## ######## ######## ######## ########

class zLastLine(gtk.HBox):
    '''An Emacs Style Last-Line Statusbar'''
    def __init__(self, label = ''):
        '''
        label
            the label in front of the last-line panel
        '''
        super(zLastLine, self).__init__()

        self.__n_alternation = 0    # initiate the blinking counter to 0
        self.__response_msg = None  # used by run() and run_confirm()

        # create widgets
        self.__label = gtk.Label(label)
        self.pack_start(self.__label, False, False, 0)

        self.__line_highlight = gtk.Label()
        self.pack_start(self.__line_highlight, False, False, 0)

        self.__line_interactive = zEntry()
        self.__line_interactive.lastline = self
        self.pack_start(self.__line_interactive, True, True, 0)

        self.__line_interactive.set_has_frame(False)

        # init flags
        self.__editable = None
        self.__force_focus = None

        self.__mx_commanding = False

        self.__lock_reset_func = None # see lock() and reset() for more information
        self.__locked = False         # if locked, all `set_*()` refer to `blink()`

        # connect auto-update items
        zTheme.register('update_font', zTheme._sig_update_font_modify, self.__label)
        zTheme._sig_update_font_modify(self.__label)

        zTheme.register('update_font', zTheme._sig_update_font_modify, self.__line_highlight, 0.85)
        zTheme._sig_update_font_modify(self.__line_highlight, 0.85)

        zTheme.register('update_font', zTheme._sig_update_font_modify, self.__line_interactive, 0.85)
        zTheme._sig_update_font_modify(self.__line_interactive, 0.85)

        zTheme.register('update_color_map', self._sig_update_color_map, self)
        self._sig_update_color_map()

        # connect signal
        self.force_focus_id = self.__line_interactive.connect('focus-out-event', self._sig_focus_out)

        self.set_editable(False)


    ### internal signals
    def _sig_comfirm(self, entry, event, choice):
        if event.type != gtk.gdk.KEY_PRESS:
            return False

        # check modifier
        if ( event.is_modifier or
             (event.state & gtk.gdk.CONTROL_MASK) or
             (event.state & gtk.gdk.MOD1_MASK   )
             ):
            return True         # eat all modifiers

        if gtk.gdk.keyval_name(event.keyval).upper() == 'RETURN':
            response = entry.get_text()
            if response in choice:
                self.__response_msg = response
                self.reset()    # release the lock
            else:
                entry.set_text('')

            return True         # eat the enter


    def _sig_entry_activate(self, listener, msg, sig_type):
        if not ( ( sig_type == 'cancel'
                   )  or
                 ( sig_type == 'activate'  and
                   msg['return_msg'] == 'Accept' # this guarantee a real activate keypress
                   )
                 ):
            return

        if sig_type == 'activate':
            # reserve the content before resetting
            self.__response_msg = self.get_text()
        else:
            # set the msg and leave the text empty
            self.__response_msg = (msg['return_msg'], '')

        self.reset()


    def _sig_mx_activate(self, listener, msg, sig_type):
        if not ( ( sig_type == 'cancel'
                   )  or
                 ( sig_type == 'activate'  and
                   msg['return_msg'] == 'Accept' # this guarantee a real activate keypress
                   )
                 ):
            return

        self.reset()            # clear all bindings with the lastline
        if sig_type == 'cancel':
            self.set_text('', msg['return_msg'])

        # retain focus
        msg['widget'].grab_focus()
    ### end of internal signals


    ### signal-like auto-update function
    def _sig_update_color_map(self, widget = None):
        self.__line_highlight.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['reserve']))

        self.__line_interactive.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.__line_interactive.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['base']))

        self.__line_interactive.modify_text(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.__line_interactive.modify_base(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['base']))
    ### end of signal-like auto-update function


    ### focus related signal
    def _sig_focus_out(self, widget, event):
        self.blink_text()
    ### end of focus related signal


    ### overridden function definition
    def is_focus(self):
        return self.__line_interactive.is_focus()

    def grab_focus(self):
        self.__line_interactive.grab_focus()


    def clear(self):
        if self.is_locked():
            return
        self.set_text('', '')

    def is_locked(self):
        return self.__locked

    def reset(self):
        self.__unlock()
        self.set_editable(False)
        self.clear()

    def run(self, task, reset_func = None):
        '''if reset_func is set, it will be called when reset() is called'''
        if self.is_locked():
            raise AssertionError('lastline has already been locked.')

        # lock the last line for input
        self.set_editable(True)
        self.set_force_focus(True)

        self.__line_interactive.set_completion_task(task)
        self.__line_interactive.listen_on_task(task)

        sig_1 = self.__line_interactive.listener.connect('z_activate', self._sig_entry_activate, 'activate')
        sig_2 = self.__line_interactive.listener.connect('z_cancel',   self._sig_entry_activate, 'cancel')
        self.__lock(reset_func)

        # wait for its unlock
        while self.is_locked():
            gtk.main_iteration(False)

        # clean up
        self.__line_interactive.listen_off()
        if self.__line_interactive.listener.handler_is_connected(sig_1):
            self.__line_interactive.listener.disconnect(sig_1)
        if self.__line_interactive.listener.handler_is_connected(sig_2):
            self.__line_interactive.listener.disconnect(sig_2)

        return self.__response_msg

    def run_confirm(self, msg, choice, default = None):
        '''
        msg
            what you want to display. choice list will be appended

        choice
            a list / tuple consists of all choices

        default
            the default choice being filled in at start
            if not set, use choice[0] as default
        '''
        if self.is_locked():
            raise AssertionError('lastline has already been locked.')

        # prepare the lastline for confirming
        msg = '{0} ({1} or {2}) '.format(msg, ', '.join(choice[:-1]), choice[-1])
        if not default:
            default = choice[0]

        self.set_editable(True)
        self.set_force_focus(True)

        self.set_text(msg, default)
        self.__line_interactive.select_region(0, -1)

        # lock the last line for input
        sig_id = self.__line_interactive.connect('key-press-event', self._sig_comfirm, choice)
        self.__lock(None)

        # wait for its unlock
        while self.is_locked():
            gtk.main_iteration(False)

        # clean up
        if self.__line_interactive.handler_is_connected(sig_id):
            self.__line_interactive.disconnect(sig_id)

        return self.__response_msg
        

    def get_label(self):
        return self.__label.get_text()

    def set_label(self, string):
        self.__label.set_text(string)

    def get_text(self):
        return self.__line_highlight.get_text(), self.__line_interactive.get_text()

    def set_text(self, hlt_text, entry_text):
        if hlt_text == None:
            hlt_text = self.__line_highlight.get_text()
        if entry_text == None:
            entry_text = self.__line_interactive.get_text()

        if self.is_locked():
            self.blink(hlt_text, entry_text)
        else:
            self.__line_highlight.set_text(hlt_text)
            self.__line_interactive.set_text(entry_text)
    ### end of overridden function definition


    def blink(self, hlt_text, entry_text, period = 1):
        if self.__n_alternation:
            return              # already on blinking, early return

        self.blink_set(
            hlt_text, entry_text, period,
            self.__line_highlight.get_text(), self.__line_interactive.get_text()
            )

    def blink_text(self, period = 0.09):
        if self.__n_alternation:
            return              # already on blinking, early return

        hlt_text = self.__line_highlight.get_text()
        entry_text = self.__line_interactive.get_text()

        # initial set
        self.__line_highlight.set_text('')
        self.__line_interactive.set_text(hlt_text)

        # register the timer to alter the texts three times
        self.__set_alternation(2)
        gobject.timeout_add(
            int(period * 1000), self.__alternate_text,
            [ '',       hlt_text   ],
            [ hlt_text, entry_text ]
            )

        self.set_editable(True, ignore_focus = True)

    def blink_set(self,
                  blk_hlt_text, blk_entry_text,
                  period = 1,
                  set_hlt_text = '', set_entry_text = ''
                  ):
        if self.__n_alternation:
            return              # already on blinking, early return

        # initial set
        self.__line_highlight.set_text(blk_hlt_text)
        self.__line_interactive.set_text(blk_entry_text)

        # register the timer to alter the texts exactly once
        self.__set_alternation(1)
        gobject.timeout_add(
            int(period * 1000), self.__alternate_text,
            [ blk_hlt_text,   set_hlt_text   ],
            [ blk_entry_text, set_entry_text ]
            )


    def is_mx_commanding(self):
        return self.__mx_commanding

    def start_mx_commanding(self, init_widget):
        if self.is_mx_commanding():
            # already in M-x Commanding, warn it
            self.blink('Warn: ', 'invalid key press!', 1)

        elif self.__line_interactive.is_listenning():
            raise AssertionError('lastline is listenning on another task!')

        elif self.is_locked():
            raise AssertionError('lastline is locked! permission denied!')

        else:
            # initiate M-x Commanding
            self.__mx_commanding = True
            self.set_text('M-x ', '')
            self.set_editable(True)

            self.__line_interactive.set_completion_task('func')
            self.__line_interactive.listen_on_task('func', init_widget)

            self.__mx_sig = [
                self.__line_interactive.listener.connect('z_activate', self._sig_mx_activate, 'activate'),
                self.__line_interactive.listener.connect('z_cancel',   self._sig_mx_activate, 'cancel'),
                ]

            self.__lock(self.stop_mx_commanding)

    def stop_mx_commanding(self):
        for handler in self.__mx_sig:
            if self.__line_interactive.handler_is_connected(handler):
                self.__line_interactive.disconnect(handler)

        self.__line_interactive.listen_off()

        self.__mx_commanding = False


    def get_editable(self):
        return self.__editable

    def set_editable(self, setting, ignore_focus = False):
        if self.__editable == setting:
            return              # no need to change, early return

        self.__editable = setting
        if not setting and not ignore_focus:
            self.set_force_focus(False)
        self.__line_interactive.set_property('can-default', setting)
        self.__line_interactive.set_property('can-focus', setting)
        self.__line_interactive.set_editable(setting)
        if setting and not ignore_focus:
            self.grab_focus()

    def get_force_focus(self):
        return self.__force_focus

    def set_force_focus(self, setting):
        self.__force_focus = setting
        if setting:
            self.__line_interactive.handler_unblock(self.force_focus_id)
        else:
            self.__line_interactive.handler_block(self.force_focus_id)


    ### supporting function
    def __lock(self, reset_func):
        self.__lock_reset_func = reset_func
        self.__locked = True

    def __unlock(self):
        if self.__lock_reset_func:
            self.__lock_reset_func()
            self.__lock_reset_func = None
        self.__locked = False


    def __set_alternation(self, n_blink):
        self.__set_timer(n_blink * 2 - 1)

    def __set_timer(self, n_alternation = None):
        if n_alternation:
            self.__n_alternation = n_alternation
        else:
            self.__n_alternation -= 1

        self.set_editable(not self.__n_alternation, ignore_focus = self.__n_alternation)


    def __alternate_text(self, hlt_text, entry_text):
        while gtk.events_pending():
            gtk.main_iteration(False)

        indx = self.__n_alternation % 2

        self.__line_highlight.set_text(hlt_text[indx])
        self.__line_interactive.set_text(entry_text[indx])

        self.__set_timer()

        return self.__n_alternation
    ### end of supporting function


######## ######## ######## ######## ########
########         zTextView          ########
######## ######## ######## ######## ########

class zTextView(z_ABC, gtk.TextView): # will be rewritten to get rid of gtk.TextView
    '''The Customized TextView that Support zEdit'''

    global_func_list = [
        'complete',             # complete the current typing
        'complete_list',        # show completion list of the current typing;
                                # whether set of not, two successive fail in complete will cause the list to show

        'delete_char_backward', # delete prev char
        'delete_char_forward',  # delete next char

        'delete_word_backward', # delete to start of curr word, or delete prev word if not in one
        'delete_word_forward',  # delete to end of curr word, or delete next word if not in one

        'delete_line_backward', # delete to start of curr line, or delete curr line if at line end
        'delete_line_forward',  # delete to end of curr line, or delete curr line if at line start,

        'delete_para_backward', # delete to start of curr para, or delete prev para if not in one or at para start
        'delete_para_forward',  # delete to end of curr para, or delete next para if not in one or at para end
        ]
    # only make the following function bindable, no actual binding applied
    zStrokeListener.global_add_func_registry(global_func_list)

    _auto_update = {
        # 'signal_like_string'  : [ (widget, callback, data_list), ... ]
        }
    def __init__(self, editor = None):
        '''
        editor = None
            the editor frame that contains this textview
        '''
        super(zTextView, self).__init__()

        self.set_editor(editor)
        self.center = self

        self.completer = zComplete(self)
        self.listener = zStrokeListener()

        self.set_editable(True) # default editable

        # register callbacks for function bindings
        self.default_func_callback = {
            'complete'              : lambda *arg: self.complete(),
            'complete_list'         : lambda *arg: self.complete_list(),
        
            'delete_char_backward'  : lambda *arg: self.delete_backward('char'),
            'delete_char_forward'   : lambda *arg: self.delete_forward( 'char'),
            'delete_word_backward'  : lambda *arg: self.delete_backward('word'),
            'delete_word_forward'   : lambda *arg: self.delete_forward( 'word'),
            'delete_line_backward'  : lambda *arg: self.delete_backward('line'),
            'delete_line_forward'   : lambda *arg: self.delete_forward( 'line'),
            'delete_para_backward'  : lambda *arg: self.delete_backward('para'),
            'delete_para_forward'   : lambda *arg: self.delete_forward( 'para'),
            }
        for (func, cb) in self.default_func_callback.iteritems():
            self.listener.register_func_callback(func, cb)


    ### overridden function definition
    def complete(self):
        self.completer.complete()

    def complete_list(self):
        self.completer.complete_list()

    def set_completion_task(self, task):
        if task not in zComplete.task_list:
            raise ValueError('{0}: invalid task for zComplete instance.'.format(task))
        else:
            self.completer.set_completion_task(task)


    def is_listenning(self):
        return self.listener.is_listenning_on(self)

    def listen_on_task(self, task = None, init_widget = None):
        self.listener.listen_on(self, task, init_widget)

    def listen_off(self):
        self.listener.listen_off(self)


    def insert_text(self, text):
        buff = self.get_buffer()
        buff.insert_at_cursor(text)

    def get_text(self):
        buff = self.get_buffer()
        return buff.get_text(buff.get_start_iter(), buff.get_end_iter(), False)

    def set_text(self, text):
        buff = self.get_buffer()
        buff.set_text(text)


    # no overridden for get_editable()
    def set_editable(self, setting):
        super(zTextView, self).set_editable(setting)

        # enable/disable the editor related function bindings
        for func in zTextView.global_func_list:
            self.listener.set_func_enabled(func, setting)
    ### end of overridden function definition


    ### editor related API
    def delete_backward(self, task = 'char'):
        buff = self.get_buffer()

        start_iter = buff.get_iter_at_mark(buff.get_insert())
        end_iter   = buff.get_iter_at_mark(buff.get_insert())

        if task == 'char':
            start_iter.backward_char()

        elif task == 'word':
            start_iter.backward_word_start()

        elif task == 'line':
            if start_iter.ends_line():
                # is at line-end, remove the entire line
                start_iter.backward_line()
                self.forward_to_line_end(start_iter)
            else:
                # not at line-end, delete to the line-start
                start_iter.set_line_offset(0)

        elif task == 'para':
            # check for para start
            if not end_iter.is_start()  and  self.is_para_start(buff, start_iter):
                # not at buffer start but at para start, move to prev line
                start_iter.backward_line()

            start_iter = self.get_para_start(buff, start_iter)

        else:
            raise KeyError('{0}: invalid task for delete pattern.'.format(task))

        buff.delete(start_iter, end_iter)

    def delete_forward(self, task = 'char'):
        buff = self.get_buffer()

        start_iter = buff.get_iter_at_mark(buff.get_insert())
        end_iter   = buff.get_iter_at_mark(buff.get_insert())

        if task == 'char':
            end_iter.forward_char()

        elif task == 'word':
            end_iter.forward_word_end()

        elif task == 'line':
            if end_iter.starts_line():
                # is at line-start, remove the entire line
                end_iter.forward_line()
            elif end_iter.ends_line():
                # already at line-end, remove the new-line char
                end_iter.forward_line()
            else:
                # not at line-end, delete to the line-end
                self.forward_to_line_end(end_iter)

        elif task == 'para':
            # check for para end
            if not end_iter.is_end()  and  self.is_para_end(buff, end_iter):
                # not at buffer end but at para end, move to next line
                end_iter.forward_line()

            end_iter = self.get_para_end(buff, end_iter)

        else:
            raise KeyError('{0}: invalid task for delete pattern.'.format(task))

        buff.delete(start_iter, end_iter)


    def forward_to_line_end(self, iterator):
        '''always move the iter to the end of the current line'''
        if not iterator.ends_line():
            # not already at line-end
            iterator.forward_to_line_end()


    def get_current_word(self):
        buff = self.get_buffer()
        start_iter = buff.get_iter_at_mark(buff.get_insert())
        end_iter   = buff.get_iter_at_mark(buff.get_insert())

        # move start back to the word start
        start_iter.backward_word_start()

        return buff.get_text(start_iter, end_iter, False)

    def set_current_word(self, word):
        buff = self.get_buffer()
        start_iter = buff.get_iter_at_mark(buff.get_insert())
        end_iter   = buff.get_iter_at_mark(buff.get_insert())

        # move start back to the word start
        start_iter.backward_word_start()

        # replace the current word with the new word
        buff.delete(start_iter, end_iter)
        buff.insert_text(start_iter, word)


    def is_word_start(self):
        buff = self.get_buffer()
        return buff.get_iter_at_mark(buff.get_insert()).starts_word()

    def is_in_word(self):
        buff = self.get_buffer()
        return buff.get_iter_at_mark(buff.get_insert()).inside_word()

    def is_word_end(self):
        buff = self.get_buffer()
        return buff.get_iter_at_mark(buff.get_insert()).ends_word()


    def is_in_para(self, buff, iterator):
        ln_s = iterator.copy()
        ln_s.set_line_offset(0)
        ln_e = ln_s.copy()
        self.forward_to_line_end(ln_e)

        return re.search(r'[\x21-\x7e]', buff.get_text(ln_s, ln_e)) # whether the curr line contains any visible char(s)

    def is_para_end(self, buff, iterator):
        if not self.is_in_para(buff, iterator):
            return False        # not in para           =>  not at para end
        elif iterator.is_end():
            return True         # end of buffer         =>  end of para
        elif not iterator.ends_line():
            return False        # not at line end       =>  not at para end

        # at line end, test next line (exist since at line end but not buffer end)
        ln_next = iterator.copy()
        ln_next.forward_line()

        if self.is_in_para(buff, ln_next):
            return False        # next line in para     =>  not at para end
        else:
            return True

    def get_para_end(self, buff, iterator):
        ln_iter = iterator.copy()
        ln_indx = ln_iter.get_line()

        # skip between-para space
        while not self.is_in_para(buff, ln_iter):
            # not in any para, keep move next
            ln_iter.forward_line()

            if ln_indx == ln_iter.get_line():
                # not moving, at last line
                self.forward_to_line_end(ln_iter)
                return ln_iter  # return end of last line
            else:
                ln_indx = ln_iter.get_line()

        # go to line just pass para end
        while self.is_in_para(buff, ln_iter):
            # in para, keep move next
            ln_iter.forward_line()

            if ln_indx == ln_iter.get_line():
                # not moving, at last line
                self.forward_to_line_end(ln_iter)
                return ln_iter  # return end of last line
            else:
                ln_indx = ln_iter.get_line()

        ln_iter.backward_line() # back to last line of para
        self.forward_to_line_end(ln_iter)
        return ln_iter          # return end of last line


    def is_para_start(self, buff, iterator):
        if not self.is_in_para(buff, iterator):
            return False        # not in para           =>  not at para start
        elif iterator.is_start():
            return True         # start of buffer       =>  start of para
        elif not iterator.starts_line():
            return False        # not at line start     =>  not at para start

        # at line start, test prev line (exist since at line start but not buffer start)
        ln_prev = iterator.copy()
        ln_prev.backward_line()

        if self.is_in_para(buff, ln_prev):
            return False        # prev line in para     =>  not at para start
        else:
            return True

    def get_para_start(self, buff, iterator):
        ln_iter = iterator.copy()
        ln_indx = ln_iter.get_line()

        # skip between-para space
        while not self.is_in_para(buff, ln_iter):
            # not in any para, keep move prev
            ln_iter.backward_line()

            if ln_indx == ln_iter.get_line():
                # not moving, at first line
                return ln_iter  # return start of first line
            else:
                ln_indx = ln_iter.get_line()

        # go to line just above para start
        while self.is_in_para(buff, ln_iter):
            # in para, keep move prev
            ln_iter.backward_line()

            if ln_indx == ln_iter.get_line():
                # not moving, at first line
                return ln_iter  # return start of first line
            else:
                ln_indx = ln_iter.get_line()

        ln_iter.forward_line() # back to first line of para
        return ln_iter          # return start of last line
    ### end of editor related API


    def buffer_save(self, buff):
        try:
            return buff.flush()
        except:
            return self.buffer_save_as(buff)

    def buffer_save_as(self, buff):
        lastline = self.get_editor().get_last_line()
        if buff.path:
            path = buff.path
        else:
            path = [ os.path.expanduser('~'), '']

        if lastline.get_property('visible'):
            lastline.reset()    # force to clear all other actions
            lastline.set_text('Write File: ', os.path.join(*path))

            # lock the lastline until getting the path
            ( msg, path ) = lastline.run('file')
            self.grab_focus()

            if path:
                if buff.path and os.path.samefile(os.path.join(* buff.path), path):
                    return buff.flush() # no change in filename, save it directly

                if os.path.isfile(path): # target already exist, confirm overwritting
                    response = lastline.run_confirm(
                        '"{0}" exists on disk, overwrite it?'.format(path),
                        [ 'y', 'n', 'w', 'q', '!', ],
                        'n'
                        )
                    self.grab_focus()
                    if response not in [ 'y', 'w' ]:
                        return None
                path = os.path.split(path)
            else:
                return None     # cancelled
        else:
            chooser = gtk.FileChooserDialog(
                'Save As...', None,
                gtk.FILE_CHOOSER_ACTION_SAVE,
                ( gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                  gtk.STOCK_SAVE,   gtk.RESPONSE_OK
                  )
                )
            chooser.set_default_response(gtk.RESPONSE_OK)
            chooser.set_current_folder(os.path.join(* path[:-1]))
            chooser.set_current_name(path[-1])

            if chooser.run() == gtk.RESPONSE_OK:
                path = os.path.split(chooser.get_filename())
                chooser.destroy()
            else:
                chooser.destroy()
                return None     # cancelled

        return buff.flush_to(path, lambda buff: self.get_editor().set_buffer(buff.path, buff.type))


    def get_editor(self):
        return self.__editor_frame

    def set_editor(self, editor):
        self.__editor_frame = editor
