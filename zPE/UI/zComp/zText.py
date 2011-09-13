# this is the text module of the zComponent package

import io_encap
# this module requires io_encap to have the following APIs:
#
#   norm_path_list(fn_list):    return the normalized absolute path
#   norm_path(full_path):       same as above; take a string as argument
#

from zBase import z_ABC, zTheme
from zStrokeParser import zStrokeListener, zComplete
from zWidget import zKillRing, zPopupMenu

import os, sys, re
import pygtk
pygtk.require('2.0')
import gtk
import gobject


######## ######## ######## ######## ########
########        zSplitWords         ########
######## ######## ######## ######## ########

class zSplitWords(object):
    '''a text splitter'''
    def __init__(self, src = ''):
        self.src = src


    def index_split(self):
        self.len = len(self.src)

        self.res = []           # result holder
        self.indx = 0           # current char index
        self.__parse_begin()

        return self.res


    def split(self):
        return [ self.src[indx_s : indx_e]
                 for (indx_s, indx_e) in self.index_split()
                 ]


    ### supporting function
    def __parse_begin(self):
        while self.indx < self.len:
            # backup the current index
            self.indx_bkup = self.indx

            # process current char
            ch = self.src[self.indx]
            self.indx += 1

            if ch.isspace():    # whitespace out of a word, skip it
                continue

            # parse the word
            if ch == '"':       # start escaping matching
                self.__parse_in_quote()
            else:               # start normal matching
                self.__parse_in_word()

            # add the word to the result
            self.res.append( (self.indx_bkup, self.indx, ) )


    def __parse_in_quote(self):
        while self.indx < self.len:
            # process current char
            ch = self.src[self.indx]
            self.indx += 1

            if ch == '"':       # switch to normal matching
                self.__parse_in_word()
                return


    def __parse_in_word(self):
        while self.indx < self.len:
            # process current char
            ch = self.src[self.indx]
            self.indx += 1

            if ch == '"':       # switch to escaping matching
                self.__parse_in_quote()

            elif ch.isspace():  # whitespace in a word, end matching
                self.indx -= 1  # back up and leave space unhandled
                return
    ### end of supporting function


######## ######## ######## ######## ########
########           zEntry           ########
######## ######## ######## ######## ########

class zEntry(gtk.Entry):
    '''A gtk.Entry that has additional methods'''
    global_func_list = [
        'complete',
        'complete_list',

        'backward_char',
        'backward_delete_char',
        'forward_char',
        'forward_delete_char',

        'backward_word',
        'backward_delete_word',
        'forward_word',
        'forward_delete_word',

        'backward_line',
        'backward_delete_line',
        'forward_line',
        'forward_delete_line',

        'backward_para',
        'backward_delete_para',
        'forward_para',
        'forward_delete_para',

        'kill_region',
        'kill_ring_save',
        'kill_ring_yank',
        'kill_ring_yank_pop',

        'set_mark_command',
        'set_mark_prepend',
        'set_mark_prepend_line',
        'set_mark_append',
        'set_mark_append_line',
        ]
    # only make the following function bindable, no actual binding applied
    zStrokeListener.global_add_func_registry(global_func_list)

    def __init__(self):
        super(zEntry, self).__init__()

        self.completer = zComplete(self)
        self.__listener = zStrokeListener() # default listener
        self.listener = self.__listener     # interface listener

        self.__selection_mark = None
        self.connect('move-cursor', self._sig_move_cursor)
        gobject.timeout_add(20, self.__watch_selection)

        self.set_editable(True) # default editable

        # register callbacks for function bindings
        self.default_func_callback = {
            'complete'              : lambda msg: self.complete(),
            'complete_list'         : lambda msg: self.complete_list(),

            'backward_char'         : lambda msg: self.backward(       'char'),
            'backward_delete_char'  : lambda msg: self.backward_delete('char', msg),
            'forward_char'          : lambda msg: self.forward(        'char'),
            'forward_delete_char'   : lambda msg: self.forward_delete( 'char', msg),

            'backward_word'         : lambda msg: self.backward(       'word'),
            'backward_delete_word'  : lambda msg: self.backward_delete('word', msg),
            'forward_word'          : lambda msg: self.forward(        'word'),
            'forward_delete_word'   : lambda msg: self.forward_delete( 'word', msg),

            'backward_line'         : lambda msg: self.backward(       'line'),
            'backward_delete_line'  : lambda msg: self.backward_delete('line', msg),
            'forward_line'          : lambda msg: self.forward(        'line'),
            'forward_delete_line'   : lambda msg: self.forward_delete( 'line', msg),

            'backward_para'         : lambda msg: self.backward(       'para'),
            'backward_delete_para'  : lambda msg: self.backward_delete('para', msg),
            'forward_para'          : lambda msg: self.forward(        'para'),
            'forward_delete_para'   : lambda msg: self.forward_delete( 'para', msg),

            'kill_region'           : lambda msg: self.kill_ring_manip('kill', msg),
            'kill_ring_save'        : lambda msg: self.kill_ring_manip('save', msg),
            'kill_ring_yank'        : lambda msg: self.kill_ring_manip('yank', msg),
            'kill_ring_yank_pop'    : lambda msg: self.kill_ring_manip('ypop', msg),

            'set_mark_command'      : lambda msg: self.set_mark(),
            'set_mark_prepend'      : lambda msg: self.set_mark(append = 'left'),
            'set_mark_prepend_line' : lambda msg: self.set_mark(append = 'up'),
            'set_mark_append'       : lambda msg: self.set_mark(append = 'right'),
            'set_mark_append_line'  : lambda msg: self.set_mark(append = 'down'),
            }
        for (func, cb) in self.default_func_callback.iteritems():
            self.__listener.register_func_callback(func, cb)

        self.connect('button-press-event',   self._sig_button_press)
        self.connect('button-release-event', self._sig_button_release)


    ### overridden signal definition
    def _sig_move_cursor(self, entry, step, count, extend_selection):
        curr_pos = self.get_position()
        self.select_region(curr_pos, curr_pos) # move cursor to the actual cursor position
        return False           # pass the rest to the default handler


    def _sig_button_press(self, widget, event):
        if event.button == 1:
            # left click
            if event.type == gtk.gdk.BUTTON_PRESS:
                # single click
                return False    # pass to the default handler

            elif event.type == gtk.gdk._2BUTTON_PRESS:
                # double click, select word
                self.unset_mark()
                return False    # pass to the default handler

            elif event.type == gtk.gdk._3BUTTON_PRESS:
                # triple click, select line
                self.unset_mark()
                return False    # pass to the default handler

        elif event.button == 2:
            # middle click
            self.kill_ring_manip('yank', None)

        elif event.button == 3:
            # right click
            menu = zPopupMenu()

            mi_cut = gtk.MenuItem('Cu_t')
            menu.append(mi_cut)
            if self.get_has_selection():
                mi_cut.connect('activate', lambda *arg: self.kill_ring_manip('kill', None))
            else:
                mi_cut.set_property('sensitive', False)

            mi_copy = gtk.MenuItem('_Copy')
            menu.append(mi_copy)
            if self.get_has_selection():
                mi_copy.connect('activate', lambda *arg: self.kill_ring_manip('save', None))
            else:
                mi_copy.set_property('sensitive', False)

            mi_paste = gtk.MenuItem('_Paste')
            menu.append(mi_paste)
            if zKillRing.resurrect():
                mi_paste.connect('activate', lambda *arg: self.kill_ring_manip('yank', None))
            else:
                mi_paste.set_property('sensitive', False)

            mi_select_all = gtk.MenuItem('Select _All')
            menu.append(mi_select_all)
            mi_select_all.connect('activate', lambda *arg: (self.set_mark(0), self.set_position(-1)))

            menu.show_all()
            menu.popup(None, None, None, event.button, event.time)

            self.emit('populate_popup', menu)

        return True             # stop the default handler

    def _sig_button_release(self, widget, event):
        if event.button == 1:
            # left click
            sel = super(zEntry, self).get_selection_bounds()
            if sel:
                if sel[0] == self.get_position():
                    self.set_mark(sel[1])
                    self.set_position(sel[0])
                else:
                    self.set_mark(sel[0])
                    self.set_position(sel[1])

        self.__listener.invalidate_curr_cmd()
    ### end of overridden signal definition


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


    def is_alternative_listenning(self):
        return self.__listener != self.listener

    def is_listenning(self):
        return self.__listener.is_listenning_on(self)

    def block_listenning(self):
        self.__listener.block_listenning(self)

    def unblock_listenning(self):
        self.__listener.unblock_listenning(self)

    def listen_on_task(self, task = None, init_widget = None):
        self.__listener.listen_on(self, task, init_widget)

    def listen_off(self):
        self.__listener.listen_off(self)


    def insert_text(self, text):
        # clear selection region, if any
        sel = self.get_selection_bounds()
        if sel:
            self.delete_text(* sel)

        # insert text
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
        self.cancel_action()
        super(zEntry, self).set_text(text)
        self.set_position(-1)


    def get_has_selection(self):
        return self.get_mark() != None

    def get_selection_bound(self):
        if self.get_has_selection():
            return self.get_mark()
        else:
            return None

    def get_selection_bounds(self):
        if self.get_has_selection():
            bound = self.get_selection_bound()
            ins   = self.get_position()
            if bound > ins:
                return ( ins, bound, )
            else:
                return ( bound, ins, )
        else:
            return ()


    # no overridden for get_editable()
    def set_editable(self, setting):
        super(zEntry, self).set_editable(setting)
        self.set_property('can-default', setting)
        self.set_property('can-focus', setting)

        # enable/disable the editor related function bindings
        for func in zEntry.global_func_list:
            self.__listener.set_func_enabled(func, setting)
    ### end of overridden function definition


    ### editor related API
    def backward(self, task):
        self.set_position(self.__backward(task, extend_selection = True))

    def backward_delete(self, task, msg):
        target_pos = self.__backward(task)
        if task != 'char':
            text_to_kill = self.get_chars(target_pos, self.get_position())

            if msg['prev_cmd'] == 'backward_delete_{0}'.format(task):
                zKillRing.prepend_killing(text_to_kill)
            else:
                zKillRing.kill(text_to_kill)

        self.delete_text(target_pos, self.get_position())
        self.unset_mark()

    def forward(self, task):
        self.set_position(self.__forward(task, extend_selection = True))

    def forward_delete(self, task, msg):
        target_pos = self.__forward(task)
        if task != 'char':
            text_to_kill = self.get_chars(self.get_position(), target_pos)

            if msg['prev_cmd'] == 'forward_delete_{0}'.format(task):
                zKillRing.append_killing(text_to_kill)
            else:
                zKillRing.kill(text_to_kill)

        self.delete_text(self.get_position(), target_pos)
        self.unset_mark()


    def kill_ring_manip(self, task, msg):
        kr = zKillRing()

        if task in [ 'kill', 'save' ]:
            if self.get_has_selection():
                sel = self.get_selection_bounds()
                kr.kill(self.get_chars(* sel))

                if task == 'kill':
                    self.delete_text(* sel)

        elif task == 'yank':
            if self.get_has_selection():
                self.insert_text('')
            yanked_text = kr.resurrect()

            if yanked_text:
                start_pos = self.get_position()
                self.insert_text(yanked_text)
                end_pos   = self.get_position()

                self.__prev_yank_bounds = ( start_pos, end_pos )
            else:
                self.__prev_yank_bounds = ( )
        else:
            if msg['prev_cmd'] in [ 'kill_ring_yank', 'kill_ring_yank_pop' ]:
                yanked_text = kr.circulate_resurrection()

                if yanked_text:
                    self.delete_text(* self.__prev_yank_bounds)

                    start_pos = self.get_position()
                    self.insert_text(yanked_text)
                    end_pos   = self.get_position()

                    self.__prev_yank_bounds = ( start_pos, end_pos )
                else:
                    self.__prev_yank_bounds = ( )
            else:
                self.__listener.invalidate_curr_cmd()

        self.unset_mark()


    def get_current_word(self, letter = None):
        curr = self.get_position()
        if curr == 0:
            # at start of entry
            start = 0
        elif letter:
            # pattern is offered, use it
            start = self.__get_word_start(curr, letter)
        else:
            # pattern not offered, use unquoted-space as separater
            start = zSplitWords(self.get_chars(0, curr)).index_split()[-1][0]

        return self.get_chars(start, curr)

    def set_current_word(self, word, letter = None):
        curr = self.get_position()

        if curr == 0:
            # at start of entry
            start = 0
        elif letter:
            # pattern is offered, use it
            start = self.__get_word_start(curr, letter)
        else:
            # pattern not offered, use unquoted-space as separater
            start = zSplitWords(self.get_chars(0, curr)).index_split()[-1][0]

        self.select_region(start, curr)
        self.delete_selection()
        self.unset_mark()
        self.insert_text(word)


    def is_word_start(self, letter = r'\S'):
        return self.__test_cursor_anchor(self.get_position(), False, True, letter)

    def is_in_word(self, letter = r'\S'):
        return self.__test_cursor_anchor(self.get_position(), True, True, letter)

    def is_word_end(self, letter = r'\S'):
        return self.__test_cursor_anchor(self.get_position(), True, False, letter)

    def is_out_word(self, letter = r'\S'):
        return self.__test_cursor_anchor(self.get_position(), False, False, letter)


    def get_mark(self):
        return self.__selection_mark

    def set_mark(self, where = None, append = ''):
        if not append:
            self.unset_mark()

        if where == None:
            where = self.get_position()

        if not self.get_has_selection():
            self.__selection_mark = where

        # for set_mark_*
        if append:
            max_pos = self.get_text_length()

            if append == 'left' and where > 0:
                where -= 1
            elif append == 'right' and where < max_pos:
                where += 1
            elif append == 'up':
                where = 0
            else:
                where = max_pos

            self.set_position(where)

    def unset_mark(self):
        if self.get_has_selection():
            curr_pos = self.get_position()
            self.select_region(curr_pos, curr_pos)
            self.__selection_mark = None


    def cancel_action(self):
        self.unset_mark()
    ### end of editor related API


    ### supporting function
    def __backward(self, task, extend_selection = False):
        sel = self.get_selection_bounds()

        if sel and not extend_selection:
            target_pos = sel[1]
            self.select_region(target_pos, target_pos)
        else:
            target_pos = self.get_position()

        if task == 'char':
            if sel and not extend_selection:
                target_pos = sel[0]
            else:
                target_pos -= 1

        elif task == 'word':
            letter = r'[a-zA-Z0-9]'
            if self.is_out_word(letter) or self.is_word_start(letter):
                # outside of a word, or at word start => move to prev work end
                target_pos = self.__get_word_start(target_pos, r'[^a-zA-Z0-9]')
            # move to word start
            target_pos = self.__get_word_start(target_pos, letter)

        elif task in [ 'line', 'para' ]:
            target_pos = 0

        else:
            raise KeyError('{0}: invalid task for delete pattern.'.format(task))

        return target_pos

    def __forward(self, task, extend_selection = False):
        sel = self.get_selection_bounds()

        if sel and not extend_selection:
            target_pos = sel[0]
            self.select_region(target_pos, target_pos)
        else:
            target_pos = self.get_position()

        if task == 'char':
            if sel and not extend_selection:
                target_pos = sel[1]
            else:
                target_pos += 1

        elif task == 'word':
            letter = r'[a-zA-Z0-9]'
            if self.is_out_word(letter) or self.is_word_end(letter):
                # outside of a word, or at word end => move to next work start
                target_pos = self.__get_word_end(target_pos, r'[^a-zA-Z0-9]')
            # move to word start
            target_pos = self.__get_word_end(target_pos, letter)

        elif task in [ 'line', 'para' ]:
            target_pos = -1

        else:
            raise KeyError('{0}: invalid task for delete pattern.'.format(task))

        return target_pos


    def __get_word_start(self, pos, letter = r'\S'):
        if not pos:
            return 0            # at start of the entry
        if not re.match(letter, self.get_chars(pos - 1, pos)):
            raise ValueError('outside of word or at word start')

        while pos > 0 and re.match(letter, self.get_chars(pos - 1, pos)):
            pos -= 1
        return pos

    def __get_word_end(self, pos, letter = r'\S'):
        max_pos = self.get_text_length()
        if pos == max_pos:
            return pos          # at end of the entry
        if not re.match(letter, self.get_chars(pos, pos + 1)):
            raise ValueError('outside of word or at word end')

        while pos < max_pos and re.match(letter, self.get_chars(pos, pos + 1)):
            pos += 1
        return pos

    def __test_cursor_anchor(self, pos, prev_w, next_w, letter = r'\S'):
        prev = self.get_chars(pos - 1, pos)
        next = self.get_chars(pos, pos + 1)

        return (
            prev_w == bool(re.match(letter, prev)) and
            next_w == bool(re.match(letter, next))
            )


    def __watch_selection(self):
        if self.get_has_selection():
            self.select_region(self.get_mark(), self.get_position())

        return True             # keep watching until dead
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

        self.__binding_frame = None

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
        self.__locked = False         # if locked, map `set_text()` to `blink()`

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
                # release the lock
                self.__unlock()
                self.set_editable(False)
                self.clear()
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

        # release the lock
        self.__unlock()
        self.set_editable(False)
        self.clear()


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
        if msg['widget'].get_property('visible'):
            msg['widget'].grab_focus()
        else:
            try:
                self.get_binding_frame().grab_focus()
            except:
                pass
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
        self.__response_msg = None
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
            self.blink(hlt_text, entry_text, 1)
        else:
            self.__line_highlight.set_text(hlt_text)
            self.__line_interactive.set_text(entry_text)
    ### end of overridden function definition


    def bind_to(self, frame):
        self.__binding_frame = frame

    def get_binding_frame(self):
        return self.__binding_frame


    def blink(self, hlt_text, entry_text, period = 0.5):
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

class zTextView(z_ABC, gtk.TextView): # do *NOT* use obj.get_buffer.set_modified(), which is used internally
    '''The Customized TextView that Support zEdit'''
    # debug flags
    debug_sync = False
    debug_sync_timestamp = 0

    global_object_cnt = 0       # see self.obj_id

    global_func_list = [
        'complete',
        'complete_list',

        'backward_char',
        'backward_delete_char',
        'forward_char',
        'forward_delete_char',

        'backward_word',
        'backward_delete_word',
        'forward_word',
        'forward_delete_word',

        'backward_line',
        'backward_delete_line',
        'forward_line',
        'forward_delete_line',

        'backward_para',
        'backward_delete_para',
        'forward_para',
        'forward_delete_para',

        'kill_region',
        'kill_ring_save',
        'kill_ring_yank',
        'kill_ring_yank_pop',

        'set_mark_command',
        'set_mark_prepend',
        'set_mark_prepend_line',
        'set_mark_append',
        'set_mark_append_line',
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

        zTextView.global_object_cnt += 1
        self.obj_id = zTextView.global_object_cnt

        # initialize vars
        self.set_editor(editor)
        self.center = self

        # initialize double-buffering buffers
        self.disp_buff = super(zTextView, self).get_buffer()
        self.true_buff = None

        self.disp_buff.create_tag('selected', background = self.get_style().bg[gtk.STATE_SELECTED])
        gobject.timeout_add(20, self.__watch_selection)

        self.disp_buff.connect('modified_changed', self._sig_buffer_modified, 'disp')


        # set up stroke listener
        self.completer = zComplete(self)
        self.__listener = zStrokeListener() # default listener
        self.listener = self.__listener     # interface listener

        # customize proporties
        self.set_editable(True) # default editable

        # register callbacks for function bindings
        self.default_func_callback = {
            'complete'              : lambda msg: self.complete(),
            'complete_list'         : lambda msg: self.complete_list(),

            'backward_char'         : lambda msg: self.backward(       'char'),
            'backward_delete_char'  : lambda msg: self.backward_delete('char', msg),
            'forward_char'          : lambda msg: self.forward(        'char'),
            'forward_delete_char'   : lambda msg: self.forward_delete( 'char', msg),

            'backward_word'         : lambda msg: self.backward(       'word'),
            'backward_delete_word'  : lambda msg: self.backward_delete('word', msg),
            'forward_word'          : lambda msg: self.forward(        'word'),
            'forward_delete_word'   : lambda msg: self.forward_delete( 'word', msg),

            'backward_line'         : lambda msg: self.backward(       'line'),
            'backward_delete_line'  : lambda msg: self.backward_delete('line', msg),
            'forward_line'          : lambda msg: self.forward(        'line'),
            'forward_delete_line'   : lambda msg: self.forward_delete( 'line', msg),

            'backward_para'         : lambda msg: self.backward(       'para'),
            'backward_delete_para'  : lambda msg: self.backward_delete('para', msg),
            'forward_para'          : lambda msg: self.forward(        'para'),
            'forward_delete_para'   : lambda msg: self.forward_delete( 'para', msg),

            'kill_region'           : lambda msg: self.kill_ring_manip('kill', msg),
            'kill_ring_save'        : lambda msg: self.kill_ring_manip('save', msg),
            'kill_ring_yank'        : lambda msg: self.kill_ring_manip('yank', msg),
            'kill_ring_yank_pop'    : lambda msg: self.kill_ring_manip('ypop', msg),

            'set_mark_command'      : lambda msg: self.set_mark(),
            'set_mark_prepend'      : lambda msg: self.set_mark(append = 'left'),
            'set_mark_prepend_line' : lambda msg: self.set_mark(append = 'up'),
            'set_mark_append'       : lambda msg: self.set_mark(append = 'right'),
            'set_mark_append_line'  : lambda msg: self.set_mark(append = 'down'),
            }
        for (func, cb) in self.default_func_callback.iteritems():
            self.__listener.register_func_callback(func, cb)

        # connect overridden signals
        self.connect('button-press-event',   self._sig_button_press)
        self.connect('button-release-event', self._sig_button_release)

        self.mouse_motion_id = self.connect('motion_notify_event', self._sig_mouse_motion)
        self.handler_block(self.mouse_motion_id)


    ### overridden signal definition
    def _sig_buffer_modified(self, buff, src):
        zTextView.debug_sync_timestamp += 1
        debug_timestamp = zTextView.debug_sync_timestamp

        if zTextView.debug_sync:
            debug_header = '{0},{1}'.format(self.obj_id, debug_timestamp)
            sys.stderr.write('<span>\n{0}: {1} changed\n'.format(debug_header, src))

        need_return = False
        if not self.true_buff:
            # no true_buff set, no need to sync
            if zTextView.debug_sync:
                sys.stderr.write('{0}: true buff not set\n'.format(debug_header))
            need_return = True
        if self.__on_sync:
            # on synchronization, ignore new request
            if zTextView.debug_sync:
                sys.stderr.write('{0}: self on synchronization\n'.format(debug_header))
            need_return = True

        if need_return:
            if zTextView.debug_sync:
                sys.stderr.write('</span>\n')
            return

        if zTextView.debug_sync:
            sys.stderr.write('{0}: disp: {1}\n'.format(debug_header, self.disp_buff.get_modified()))
            sys.stderr.write('{0}: true: {1}\n'.format(debug_header, self.true_buff.get_modified()))

        self.__sync_buff_from(src, debug_timestamp)

        if zTextView.debug_sync:
            sys.stderr.write('{0}: all done\n'.format(debug_header))
            sys.stderr.write('</span>\n')


    def _sig_button_press(self, widget, event):
        clicked_iter = self.get_iter_at_location(
            * self.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, int(event.x), int(event.y))
              )

        if event.button == 1:
            # left click
            if event.type == gtk.gdk.BUTTON_PRESS:
                # single click
                self.place_cursor(clicked_iter)

                self.__mouse_motion_init_pos = clicked_iter # used to initiate selection mark
                self.handler_unblock(self.mouse_motion_id)

            elif event.type == gtk.gdk._2BUTTON_PRESS:
                # double click, select word
                start_iter = clicked_iter.copy()
                end_iter   = clicked_iter.copy()

                start_iter.backward_word_start()
                end_iter.forward_word_end()

                self.set_mark(start_iter)
                self.place_cursor(end_iter)

            elif event.type == gtk.gdk._3BUTTON_PRESS:
                # triple click, select line
                start_iter = clicked_iter.copy()
                end_iter   = clicked_iter.copy()

                start_iter.set_line_offset(0)
                self.forward_to_line_end(end_iter)

                self.set_mark(start_iter)
                self.place_cursor(end_iter)

        elif event.button == 2:
            # middle click
            self.place_cursor(clicked_iter)
            self.kill_ring_manip('yank', None)

        elif event.button == 3:
            # right click
            self.place_cursor(clicked_iter)
            menu = zPopupMenu()

            mi_cut = gtk.MenuItem('Cu_t')
            menu.append(mi_cut)
            if self.get_has_selection():
                mi_cut.connect('activate', lambda *arg: self.kill_ring_manip('kill', None))
            else:
                mi_cut.set_property('sensitive', False)

            mi_copy = gtk.MenuItem('_Copy')
            menu.append(mi_copy)
            if self.get_has_selection():
                mi_copy.connect('activate', lambda *arg: self.kill_ring_manip('save', None))
            else:
                mi_copy.set_property('sensitive', False)

            mi_paste = gtk.MenuItem('_Paste')
            menu.append(mi_paste)
            if zKillRing.resurrect():
                mi_paste.connect('activate', lambda *arg: self.kill_ring_manip('yank', None))
            else:
                mi_paste.set_property('sensitive', False)

            mi_select_all = gtk.MenuItem('Select _All')
            menu.append(mi_select_all)
            mi_select_all.connect('activate', lambda *arg: (
                    self.set_mark(self.disp_buff.get_end_iter()),
                    self.place_cursor(self.disp_buff.get_start_iter()),
                    ))

            menu.show_all()
            menu.popup(None, None, None, event.button, event.time)

            self.emit('populate_popup', menu)

        return True             # stop the default handler

    def _sig_mouse_motion(self, widget, event):
        new_iter = self.get_iter_at_location(
            * self.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, int(event.x), int(event.y))
              )
        self.place_cursor(new_iter)

        if ( not self.get_has_selection()  and                  # no selection was set
             not new_iter.equal(self.__mouse_motion_init_pos)   # position changed
             ):
            self.set_mark(self.__mouse_motion_init_pos)

    def _sig_button_release(self, widget, event):
        if event.button == 1:
            # left click
            self.handler_block(self.mouse_motion_id)
            self.__mouse_motion_init_pos = None

        self.__listener.invalidate_curr_cmd()
    ### end of overridden signal definition


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


    def is_alternative_listenning(self):
        return self.__listener != self.listener

    def is_listenning(self):
        return self.__listener.is_listenning_on(self)

    def block_listenning(self):
        self.__listener.block_listenning(self)

    def unblock_listenning(self):
        self.__listener.unblock_listenning(self)

    def listen_on_task(self, task = None, init_widget = None):
        self.__listener.listen_on(self, task, init_widget)

    def listen_off(self):
        self.__listener.listen_off(self)


    def insert_text(self, text):
        # clear selection region, if any
        sel = self.get_selection_bounds()
        if sel:
            self.delete_selection()

        # insert text
        self.disp_buff.insert_at_cursor(text)

    def get_text(self):
        return self.disp_buff.get_text(self.disp_buff.get_start_iter(), self.disp_buff.get_end_iter(), False)

    def set_text(self, text):
        self.disp_buff.set_text(text)
        self.place_cursor(self.disp_buff.get_start_iter())


    def get_has_selection(self):
        return self.get_mark() != None

    def get_selection_bound(self):
        if self.get_has_selection():
            return self.disp_buff.get_iter_at_mark(self.get_mark())
        else:
            return None

    def get_selection_bounds(self):
        if self.get_has_selection():
            bound = self.get_selection_bound()
            ins   = self.get_cursor_iter()
            if bound.get_offset() > ins.get_offset():
                return ( ins, bound, )
            else:
                return ( bound, ins, )
        else:
            return ()

    def select_range(self, ins, bound):
        self.set_mark(bound)
        self.place_cursor(ins)

    def delete_selection(self):
        sel = self.get_selection_bounds()
        if sel:
            self.disp_buff.delete(* sel)
            self.unset_mark()


    def modify_base(self, state, color):
        super(zTextView, self).modify_base(state, color)
        if state == gtk.STATE_SELECTED:
            old_tag = self.disp_buff.get_tag_table().lookup('selected')
            self.disp_buff.get_tag_table().remove(old_tag)
            self.disp_buff.create_tag('selected', background = color)


    def get_buffer(self):
        if self.true_buff:
            return self.true_buff
        else:
            return self.disp_buff

    def set_buffer(self, buff, dry_run = False):
        if self.true_buff and not dry_run:
            if self.true_buff.handler_is_connected(self.__true_buff_watcher):
                self.true_buff.disconnect(self.__true_buff_watcher)

        if buff.get_modified():           # mark true buff "synchronized"
            buff.set_modified(False)

        if not dry_run:
            self.true_buff = buff
            self.__true_buff_watcher = self.true_buff.connect('modified_changed', self._sig_buffer_modified, 'true')

        self.__sync_buff_from('true')
        self.unset_mark()
        self.place_cursor(self.disp_buff.get_start_iter())


    # no overridden for get_editable()
    def set_editable(self, setting):
        super(zTextView, self).set_editable(setting)

        # enable/disable the editor related function bindings
        for func in zTextView.global_func_list:
            self.__listener.set_func_enabled(func, setting)


    def place_cursor(self, where):
        self.disp_buff.place_cursor(where)
    ### end of overridden function definition


    ### editor related API
    def backward(self, task):
        self.place_cursor(self.__backward(task, extend_selection = True))

    def backward_delete(self, task, msg):
        target_iter = self.__backward(task)
        if task != 'char':
            text_to_kill = self.disp_buff.get_text(target_iter, self.get_cursor_iter())

            if msg['prev_cmd'] == 'backward_delete_{0}'.format(task):
                zKillRing.prepend_killing(text_to_kill)
            else:
                zKillRing.kill(text_to_kill)

        self.disp_buff.delete(target_iter, self.get_cursor_iter())
        self.unset_mark()

    def forward(self, task):
        self.place_cursor(self.__forward(task, extend_selection = True))

    def forward_delete(self, task, msg):
        target_iter = self.__forward(task)
        if task != 'char':
            text_to_kill = self.disp_buff.get_text(self.get_cursor_iter(), target_iter)

            if msg['prev_cmd'] == 'forward_delete_{0}'.format(task):
                zKillRing.append_killing(text_to_kill)
            else:
                zKillRing.kill(text_to_kill)

        self.disp_buff.delete(self.get_cursor_iter(), target_iter)
        self.unset_mark()


    def forward_to_line_end(self, iterator):
        '''always move the iter to the end of the current line'''
        if not iterator.ends_line():
            # not already at line-end
            iterator.forward_to_line_end()


    def kill_ring_manip(self, task, msg):
        kr = zKillRing()

        if task in [ 'kill', 'save' ]:
            if self.get_has_selection():
                sel = self.get_selection_bounds()
                kr.kill(self.disp_buff.get_text(sel[0], sel[1], False))

                if task == 'kill':
                    self.disp_buff.delete(* sel)
            else:
                self.get_editor().get_last_line().set_text('', '(mark is not set now)')

        elif task == 'yank':
            yanked_text = kr.resurrect()

            if yanked_text:
                start_pos = self.get_cursor_iter().get_offset()
                self.insert_text(yanked_text)
                end_pos   = self.get_cursor_iter().get_offset()

                self.__prev_yank_bounds = ( start_pos, end_pos )
            else:
                self.__prev_yank_bounds = ( )
        else:
            if msg['prev_cmd'] in [ 'kill_ring_yank', 'kill_ring_yank_pop' ]:
                yanked_text = kr.circulate_resurrection()

                if yanked_text:
                    self.disp_buff.delete(
                        self.disp_buff.get_iter_at_offset(self.__prev_yank_bounds[0]),
                        self.disp_buff.get_iter_at_offset(self.__prev_yank_bounds[1])
                        )

                    start_pos = self.get_cursor_iter().get_offset()
                    self.insert_text(yanked_text)
                    end_pos   = self.get_cursor_iter().get_offset()

                    self.__prev_yank_bounds = ( start_pos, end_pos )
                else:
                    self.__prev_yank_bounds = ( )
            else:
                self.get_editor().get_last_line().set_text('', '(previous command was not a yank)')
                self.__listener.invalidate_curr_cmd()

        self.unset_mark()


    def get_cursor_iter(self):
        return self.disp_buff.get_iter_at_mark(self.disp_buff.get_insert())


    def get_current_word(self):
        start_iter = self.get_cursor_iter()
        end_iter   = self.get_cursor_iter()

        # move start back to the word start
        start_iter.backward_word_start()

        return self.disp_buff.get_text(start_iter, end_iter, False)

    def set_current_word(self, word):
        start_iter = self.get_cursor_iter()
        end_iter   = self.get_cursor_iter()

        # move start back to the word start
        start_iter.backward_word_start()

        # replace the current word with the new word
        self.disp_buff.delete(start_iter, end_iter)
        self.disp_buff.insert_text(start_iter, word)


    def is_word_start(self):
        return self.get_cursor_iter().starts_word()

    def is_in_word(self):
        return self.get_cursor_iter().inside_word()

    def is_word_end(self):
        return self.get_cursor_iter().ends_word()


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


    def get_mark(self):
        return self.disp_buff.get_mark('selection_start')

    def set_mark(self, where = None, append = ''):
        if not append:
            self.unset_mark()

        if not where:
            where = self.get_cursor_iter()

        if not self.get_has_selection():
            self.disp_buff.create_mark('selection_start', where, False)
            self.disp_buff.create_mark('selection_end', where, False) # for internal usage

            self.get_editor().get_last_line().set_text('', 'Mark set')

        # for set_mark_*
        if append:
            if append == 'left':
                where.backward_char()
            elif append == 'right':
                where.forward_char()
            else:
                line_offset = self.disp_buff.get_iter_at_mark(self.get_mark()).get_line_offset()
                if append == 'up':
                    where.backward_line()
                else:
                    where.forward_line()
                max_offset = where.get_chars_in_line()
                if line_offset < max_offset:
                    where.set_line_offset(line_offset)
                else:
                    self.forward_to_line_end(where)

            self.place_cursor(where)

    def unset_mark(self):
        if self.get_has_selection():
            self.disp_buff.delete_mark_by_name('selection_start')
            self.disp_buff.delete_mark_by_name('selection_end') # for internal usage
            self.disp_buff.remove_tag_by_name('selected', self.disp_buff.get_start_iter(), self.disp_buff.get_end_iter())


    def cancel_action(self):
        self.unset_mark()
    ### end of editor related API


    def buffer_save(self, z_buffer):
        try:
            return z_buffer.flush()
        except:
            return self.buffer_save_as(z_buffer)

    def buffer_save_as(self, z_buffer):
        lastline = self.get_editor().get_last_line()
        if z_buffer.path:
            path = z_buffer.path
        else:
            path = [ zTheme.env['starting_path'], '']

        if lastline.get_property('visible'):
            lastline.reset()    # force to clear all other actions
            lastline.set_text('Write File: ', os.path.join(*path))

            # lock the lastline until getting the path
            ( msg, path ) = lastline.run('file')
            self.grab_focus()

            if path:
                if z_buffer.path and io_encap.norm_path_list(z_buffer.path) == path:
                    return z_buffer.flush() # no change in filename, save it directly

                if os.path.isfile(path): # target already exist, confirm overwritting
                    response = lastline.run_confirm(
                        '"{0}" exists on disk, overwrite it?'.format(path),
                        [ 'y', 'w', 'n', '!', 'q', 'c', ],
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
                path = os.path.split(io_encap.norm_path(chooser.get_filename()))
                chooser.destroy()
            else:
                chooser.destroy()
                return None     # cancelled

        return z_buffer.flush_to(path, lambda z_buffer: self.get_editor().set_buffer(z_buffer.path, z_buffer.type))


    def get_editor(self):
        return self.__editor_frame

    def set_editor(self, editor):
        self.__editor_frame = editor


    ### supporting function
    def __backward(self, task, extend_selection = False):
        sel = self.get_selection_bounds()

        if sel and not extend_selection:
            target_iter = sel[1]
            self.select_range(target_iter, target_iter)
        else:
            target_iter = self.get_cursor_iter()

        if task == 'char':
            if sel and not extend_selection:
                target_iter = sel[0]
            else:
                target_iter.backward_char()

        elif task == 'word':
            target_iter.backward_word_start()

        elif task == 'line':
                target_iter.set_line_offset(0)

        elif task == 'para':
            # check for para start
            if not target_iter.is_start()  and  self.is_para_start(self.disp_buff, target_iter):
                # not at buffer start but at para start, move to prev line
                target_iter.backward_line()

            target_iter = self.get_para_start(self.disp_buff, target_iter)

        else:
            raise KeyError('{0}: invalid task for delete pattern.'.format(task))

        return target_iter

    def __forward(self, task, extend_selection = False):
        sel = self.get_selection_bounds()

        if sel and not extend_selection:
            target_iter = sel[0]
            self.select_range(target_iter, target_iter)
        else:
            target_iter = self.get_cursor_iter()

        if task == 'char':
            if sel and not extend_selection:
                target_iter = sel[1]
            else:
                target_iter.forward_char()

        elif task == 'word':
            target_iter.forward_word_end()

        elif task == 'line':
            if not extend_selection and target_iter.starts_line():
                # is at line-start (delete mode), return line-start of next line (curr line will be removed entirely)
                target_iter.forward_line()
            elif not extend_selection and target_iter.ends_line():
                # already at line-end (delete mode), return line-start of next line (new-line char will be removed)
                target_iter.forward_line()
            else:
                # not at line-end or in select mode, return line-end
                self.forward_to_line_end(target_iter)

        elif task == 'para':
            # check for para end
            if not target_iter.is_end()  and  self.is_para_end(self.disp_buff, target_iter):
                # not at buffer end but at para end, move to next line
                target_iter.forward_line()

            target_iter = self.get_para_end(self.disp_buff, target_iter)

        else:
            raise KeyError('{0}: invalid task for delete pattern.'.format(task))

        return target_iter


    def __sync_buff_from(self, src, debug_timestamp = 0):
        self.__on_sync = True   # start synchronizing

        if zTextView.debug_sync:
            debug_header = '{0},{1}'.format(self.obj_id, debug_timestamp)
            sys.stderr.write('<span>\n{0}: sync from {1}: started\n'.format(debug_header, src))
            sys.stderr.write('{0}: disp: {1}\n'.format(debug_header, self.disp_buff.get_modified()))
            sys.stderr.write('{0}: true: {1}\n'.format(debug_header, self.true_buff.get_modified()))

        if src == 'true':
            if self.true_buff.reloading:
                # add a watcher to wait true for completing modification
                gobject.timeout_add(20, self.__watch_true_buff_reload)

            if self.true_buff.get_modified():
                # on modifying, pass
                if zTextView.debug_sync:
                    sys.stderr.write('{0}: true on modifying, pass\n'.format(debug_header))
                    sys.stderr.write('</span>\n')
                self.__on_sync = False  # stop synchronizing
                return
            else:
                buff_src  = self.true_buff
                buff_dest = self.disp_buff
        else:
            if not self.disp_buff.get_modified():
                # already modified, pass
                if zTextView.debug_sync:
                    sys.stderr.write('{0}: disp already modified, pass\n'.format(debug_header))
                    sys.stderr.write('</span>\n')
                self.__on_sync = False  # stop synchronizing
                return
            else:
                buff_src  = self.disp_buff
                buff_dest = self.true_buff

        text = buff_src.get_text(
                buff_src.get_start_iter(), buff_src.get_end_iter(), False
                )
        if zTextView.debug_sync:
            sys.stderr.write('{0}: src text retrived: {1} chars\n'.format(debug_header, len(text)))
        buff_dest.set_text(text)
        if zTextView.debug_sync:
            sys.stderr.write('{0}: dest text set: {1} chars\n'.format(
                        debug_header,
                        len(buff_dest.get_text(buff_dest.get_start_iter(), buff_dest.get_end_iter(), False)
                            )))

        # reset modified watcher
        if src != 'true':
            # do not reset src if that is the true buffer
            buff_src.set_modified(False)
        buff_dest.set_modified(False)

        if zTextView.debug_sync:
            sys.stderr.write('{0}: disp: {1}\n'.format(debug_header, self.disp_buff.get_modified()))
            sys.stderr.write('{0}: true: {1}\n'.format(debug_header, self.true_buff.get_modified()))
            sys.stderr.write('{0}: sync finished\n'.format(debug_header))
            sys.stderr.write('</span>\n')

        self.__on_sync = False  # stop synchronizing


    def __watch_selection(self):
        if self.get_has_selection():
            # clear previous selection
            iter_start = self.disp_buff.get_iter_at_mark(self.get_mark())
            iter_end   = self.disp_buff.get_iter_at_mark(self.disp_buff.get_mark('selection_end'))
            self.disp_buff.remove_tag_by_name('selected', iter_start, iter_end)

            # update new selection
            iter_end = self.get_cursor_iter()
            self.disp_buff.move_mark_by_name('selection_end', iter_end) # move end mark
            self.disp_buff.apply_tag_by_name('selected', iter_start, iter_end)

        return True             # keep watching until dead


    def __watch_true_buff_reload(self):
        if self.true_buff.reloading:
            return True

        self.set_buffer(self.true_buff, dry_run = True) # notify completion of modification
        return False
    ### end of supporting function
