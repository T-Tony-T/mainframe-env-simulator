# this is the text module (and their supports) of the zComponent package

import io_encap
# this module requires io_encap to have the following APIs:
#
#   norm_path_list(fn_list):    return the normalized absolute path
#   norm_path(full_path):       same as above; take a string as argument
#

import os, sys, re
import pygtk
pygtk.require('2.0')
import gtk
import gobject, pango


######## ######## ######## ######## ########
########         zUndoStack         ########
######## ######## ######## ######## ########

class zBufferChange(object):
    '''a node keeps track of the change in a text buffer. this is used to implement undo / redo system'''
    revert_action = {
        'i' : 'd',
        'd' : 'i',
        }

    def __init__(self, content, offset, action):
        '''
        content
            the content that changed from the last recorded state.

        offset
            the offset into the buffer of the change above.

        action
            'i' / 'a' : the indicated content is inserted / added to the buffer
            'd' / 'r' : the indicated content is deleted / removed from the buffer
        '''
        if not isinstance(content, str):
            raise ValueError('{0}: content need to be an string!'.format(content))
        self.content = content

        if not isinstance(offset, int) or offset < 0:
            raise ValueError('{0}: offset need to be a non-negative integer!'.format(offset))
        self.offset  = offset

        if action in [ 'i', 'a', ]:
            self.action = 'i'
        elif action in [ 'd', 'r', ]:
            self.action = 'd'
        else:
            raise ValueError(
                '{0}: action need to be "i" / "a" for insert / add, or "d" / "r" for delete / remove!'.format(action)
                )

    def __str__(self):
        if self.action == 'i':
            action = 'INSERT'
        else:
            action = 'DELETE'
        return '{0}: <<{1}>> AT offset {2}'.format(action, self.content, self.offset)


    def revert(self):
        return zBufferChange(self.content, self.offset, zBufferChange.revert_action[self.action])


class zAtomicChange(object):
    '''an atomic change (state) consists of a (list of) zBufferChange(s)'''
    def __init__(self, buff_changes):
        self.__state__ = []
        for change in buff_changes:
            self.__state__.append(change)

    def __str__(self):
        return ' => '.join([ str(change) for change in self.__state__ ])

    def __len__(self):
        return len(self.__state__)

    def __getitem__(self, key):
        return self.__state__[key]

    def append(self, new_change):
        self.__state__.append(new_change)

    def pop(self, index = -1):
        return self.__state__.pop(index)

    def revert(self):
        return zAtomicChange([ change.revert() for change in self.__state__ ][::-1])



class zUndoStack(object):
    '''an modified Emacs-Style Undo / Redo System implemeted using Stack (List)'''
    def __init__(self, init_content):
        self.clear(init_content)

    def __str__(self):
        rv_list = [ '[\n' ]
        for state in self.__stack:
            if self.is_saved(state):
                saved_indicator = '*'
            else:
                saved_indicator = ' '

            rv_list.append('{0}  {1:0>3}:  {2}\n'.format(saved_indicator, self.get_group_id(state), state))
        rv_list.append(']\n')

        return ''.join(rv_list)


    def clear(self, init_content = ''):
        '''reset the entire undo-stack'''
        init_state = zAtomicChange([ zBufferChange(init_content, 0, 'i') ])

        self.__stack = [ init_state ]
        self.__top   = 0        # top index (of the undo-stack)
        self.__undo  = 0        # current undo index

        self.__group = [        # any states within the same group are "equvilent"
            [ init_state ],
            ]
        self.__group_saved = 0  # the index of the group that state(s) is equvilent to the saved one


    def is_init(self):
        '''test whether the current state is an initial-state (no former edit)'''
        return self.__undo == 0

    def is_last(self):
        '''test whether the current state is an end-state (no former undo)'''
        return self.__undo == self.__top


    def is_saved(self, state = None):
        '''test whether the given state (current state, if not specified) is saved'''
        if not state:
            state = self.get_current_state()
        return state in self.__group[self.__group_saved]

    def get_group_id(self, state):
        '''retrieve the group ID for a specific state'''
        for indx in range(len(self.__group)):
            if state in self.__group[indx]:
                break
        return indx


    def get_current_state(self):
        '''retrieve the current state'''
        return self.__stack[-1]

    def save_current_state(self):
        '''mark the group of the current state as "saved"'''
        self.__group_saved = self.get_group_id(self.get_current_state())


    def new_state(self, new_state):
        '''push a new edit onto the stack'''
        self.__stack.append(new_state)
        self.__top  = len(self.__stack) - 1     # update the top index
        self.__undo = self.__top                # point the undo index to the top of the stack
        self.__group.append([ new_state ])      # add the new state into a new group

    def undo(self):
        '''push an "undo" onto the stack; this will *NOT* modified any buffer'''
        if self.is_init():
            return None # stack is at initial state, cannot undo

        undo_state = self.__stack[self.__undo].revert() # revert the state of undo index
        self.__stack.append(undo_state)                 # push the reverted state onto the stack

        self.__undo -= 1        # decrement the undo index to the previous state
        self.__group[self.get_group_id(self.__stack[self.__undo])].append(undo_state) # update group list

        return undo_state

    def redo(self):
        '''pop an "undo" out of the stack; this will *NOT* modified any buffer'''
        if self.is_last():
            return None # no former undo(s), cannot redo

        redo_state = self.__stack.pop() # pop the last state out of the stack

        self.__group[self.get_group_id(self.__stack[self.__undo])].remove(redo_state) # update group list
        self.__undo += 1        # increment the undo index to the next state

        return redo_state.revert()      # pop the reverted last state out of the stack



######## ######## ######## ######## ########
########       zCompletionDict      ########
######## ######## ######## ######## ########

class zCompletionDict(object):
    '''completion dictionary used for generating completion list'''
    def __init__(self, word_set):
        self.__root__ = { '' : False } # root cannot be end-of-word
        self.__cnt__  = 0
        self.update(word_set)


    def __contains__(self, word):
        sub = self.subdict(word)
        return sub and sub['']

    def __len__(self):
        return self.__cnt__


    def add(self, word):
        '''add a word into the dict'''
        if word in self:
            return              # no need to add, early return
        ptr = self.__root__
        for ch in word:
            ptr[ch] = ptr.has_key(ch) and ptr[ch] or { '' : False }
            ptr = ptr[ch]
        ptr[''] = True          # turn on end-of-word mark
        self.__cnt__ += 1


    def complete(self, word):
        '''return the list of all possible completions of the word'''
        sub = self.subdict(word)
        return sub and self.listify(word, sub) or [ ]


    def dump(self):
        return self.__root__


    def listify(self, prefix = '', subdict = None):
        if not subdict:
            subdict = self.dump()
        return [ ''.join(chlist) for chlist in self.__listify__([ prefix ], subdict) ]

    def __listify__(self, prefix, subdict):
        rv = [ ]
        if subdict['']:
            rv.append(prefix)
        for key in subdict.iterkeys():
            if not key:         # '' is end-of-word mark, ignore it
                continue
            rv.extend(self.__listify__(prefix + [ key ], subdict[key]))
        return rv


    def subdict(self, word):
        '''return the subdict with prefix equal to the given word, or None if not found'''
        ptr = self.__root__
        for ch in word:
            if not ch in ptr:
                return None
            ptr = ptr[ch]
        return ptr


    def update(self, word_set):
        '''update the dict with a set of words'''
        for word in word_set:
            self.add(word)



######## ######## ######## ######## ########
######## Text Field / Area Classes  ########
######## ######## ######## ######## ########

from zBase import z_ABC, zTheme
from zStrokeParser import zStrokeListener, zComplete
from zSyntaxParser import zSyntaxParser
from zWidget import zKillRing, zPopupMenu


######## ######## ######## ######## ########
########           zEntry           ########
######## ######## ######## ######## ########

class zEntry(gtk.Entry):
    '''A gtk.Entry that has additional methods'''
    global_func_list = [
        'align-or-complete',
        'complete',
        'complete-list',

        'backward-char',
        'backward-delete-char',
        'forward-char',
        'forward-delete-char',

        'backward-word',
        'backward-delete-word',
        'forward-word',
        'forward-delete-word',

        'backward-line',
        'backward-delete-line',
        'forward-line',
        'forward-delete-line',

        'backward-para',
        'backward-delete-para',
        'forward-para',
        'forward-delete-para',

        'kill-region',
        'kill-ring-save',
        'kill-ring-yank',
        'kill-ring-yank-pop',

        'set-mark-command',
        'set-mark-move-left',
        'set-mark-move-right',
        'set-mark-move-up',
        'set-mark-move-down',
        'set-mark-move-start',
        'set-mark-move-end',
        'set-mark-select-all',
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
            'align-or-complete'     : lambda msg: self.complete(), # no align available anyway
            'complete'              : lambda msg: self.complete(),
            'complete-list'         : lambda msg: self.complete_list(),

            'backward-char'         : lambda msg: self.backward(       'char'),
            'backward-delete-char'  : lambda msg: self.backward_delete('char', msg),
            'forward-char'          : lambda msg: self.forward(        'char'),
            'forward-delete-char'   : lambda msg: self.forward_delete( 'char', msg),

            'backward-word'         : lambda msg: self.backward(       'word'),
            'backward-delete-word'  : lambda msg: self.backward_delete('word', msg),
            'forward-word'          : lambda msg: self.forward(        'word'),
            'forward-delete-word'   : lambda msg: self.forward_delete( 'word', msg),

            'backward-line'         : lambda msg: self.backward(       'line'),
            'backward-delete-line'  : lambda msg: self.backward_delete('line', msg),
            'forward-line'          : lambda msg: self.forward(        'line'),
            'forward-delete-line'   : lambda msg: self.forward_delete( 'line', msg),

            'backward-para'         : lambda msg: self.backward(       'para'),
            'backward-delete-para'  : lambda msg: self.backward_delete('para', msg),
            'forward-para'          : lambda msg: self.forward(        'para'),
            'forward-delete-para'   : lambda msg: self.forward_delete( 'para', msg),

            'kill-region'           : lambda msg: self.kill_ring_manip('kill', msg),
            'kill-ring-save'        : lambda msg: self.kill_ring_manip('save', msg),
            'kill-ring-yank'        : lambda msg: self.kill_ring_manip('yank', msg),
            'kill-ring-yank-pop'    : lambda msg: self.kill_ring_manip('ypop', msg),

            'set-mark-command'      : lambda msg: self.set_mark(),
            'set-mark-move-left'    : lambda msg: self.set_mark(append = 'left'),
            'set-mark-move-right'   : lambda msg: self.set_mark(append = 'right'),
            'set-mark-move-up'      : lambda msg: self.set_mark(append = 'up'),
            'set-mark-move-down'    : lambda msg: self.set_mark(append = 'down'),
            'set-mark-move-start'   : lambda msg: self.set_mark(append = 'start'),
            'set-mark-move-end'     : lambda msg: self.set_mark(append = 'end'),
            'set-mark-select-all'   : lambda msg: ( self.set_mark(-1),
                                                    self.set_position(0)
                                                    ),
            }
        for (func, cb) in self.default_func_callback.iteritems():
            self.__listener.register_func_callback(func, cb)

        self.connect('button-press-event',   self._sig_button_press)
        self.connect('button-release-event', self._sig_button_release)

        self.mouse_motion_id = self.connect('motion_notify_event', self._sig_mouse_motion)
        self.handler_block(self.mouse_motion_id)


    ### overridden signal definition
    def _sig_move_cursor(self, entry, step, count, extend_selection):
        curr_pos = self.get_position()
        self.select_region(curr_pos, curr_pos) # move cursor to the actual cursor position
        return False           # pass the rest to the default handler


    def _sig_button_press(self, widget, event):
        clicked_pos = self.get_layout().get_line(0).x_to_index(int(
                ( event.x - self.get_layout_offsets()[0] ) * pango.SCALE
                ))
        max_pos = self.get_text_length()

        if clicked_pos[0]:
            clicked_pos = clicked_pos[1] + 1 # +1 to move to end of the char
        else:
            if clicked_pos[1]:
                clicked_pos = max_pos # at end
            else:
                clicked_pos = 0 # at beginning

        if event.button == 1:
            # left click
            if event.type == gtk.gdk.BUTTON_PRESS:
                # single click
                self.unset_mark()
                self.set_position(clicked_pos)

                self.__mouse_motion_init_pos = clicked_pos # used to initiate selection mark
                self.handler_unblock(self.mouse_motion_id)

            elif event.type == gtk.gdk._2BUTTON_PRESS:
                # double click, select word
                start_pos = clicked_pos
                end_pos   = clicked_pos
                letter = r'[a-zA-Z0-9_]'

                while start_pos > 0 and ( self.is_word_start(start_pos, letter) or self.is_out_word(start_pos, letter) ):
                    # if is at word-start or out of any word (but not the start of buffer), move to previous char
                    start_pos -= 1
                else:
                    if start_pos > 0 and start_pos == clicked_pos:
                        # if not at the start of buffer, and the loop never executed
                        start_pos = self.__get_word_start(clicked_pos, letter)

                while end_pos < max_pos and ( self.is_word_end(end_pos, letter) or self.is_out_word(end_pos, letter) ):
                    # if is at word-end or out of any word (but not the start of buffer), move to next char
                    end_pos += 1
                else:
                    if end_pos < max_pos and end_pos == clicked_pos:
                        # if not at the end of buffer, and the loop never executed
                        end_pos = self.__get_word_end(clicked_pos, letter)

                self.set_mark(start_pos)
                self.set_position(end_pos)

            elif event.type == gtk.gdk._3BUTTON_PRESS:
                # triple click, select line
                self.set_mark(0)
                self.set_position(max_pos)

        elif event.button == 2:
            # middle click
            self.set_position(clicked_pos)
            self.kill_ring_manip('yank', None)

        elif event.button == 3:
            # right click
            menu = zPopupMenu()

            mi_cut = gtk.MenuItem('Cu_t')
            menu.append(mi_cut)
            if self.get_editable() and self.get_has_selection():
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
            if self.get_editable() and zKillRing.resurrect():
                mi_paste.connect('activate', lambda *arg: self.kill_ring_manip('yank', None))
            else:
                mi_paste.set_property('sensitive', False)

            mi_select_all = gtk.MenuItem('Select _All')
            menu.append(mi_select_all)
            mi_select_all.connect('activate', lambda *arg: (self.set_mark(-1), self.set_position(0)))

            menu.show_all()
            menu.popup(None, None, None, event.button, event.time)

            self.emit('populate_popup', menu)

        if not self.is_focus():
            self.grab_focus()
        return True             # stop the default handler

    def _sig_mouse_motion(self, widget, event):
        new_pos = self.get_layout().get_line(0).x_to_index(int(
                ( event.x - self.get_layout_offsets()[0] ) * pango.SCALE
                ))
        if new_pos[0]:
            new_pos = new_pos[1] + 1 # +1 to move to end of the char
        else:
            if new_pos[1]:
                new_pos = new_pos[1] + 2 # at end
            else:
                new_pos = 0     # at beginning

        self.set_position(new_pos)

        if ( not self.get_has_selection()  and          # no selection was set
             new_pos != self.__mouse_motion_init_pos    # position changed
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
        return self.task_listenning() != None

    def task_listenning(self):
        return self.__listener.is_listenning_on(self)

    def block_listenning(self):
        self.__listener.block_listenning(self)

    def unblock_listenning(self):
        self.__listener.unblock_listenning(self)

    def listen_on_task(self, task = None, init_widget = None):
        self.__listener.listen_on(self, task, init_widget)

    def listen_off(self):
        self.__listener.listen_off(self)


    def insert_text(self, text, always_insert = False):
        if ( self.get_overwrite_mode() and # overwrite mode
             not always_insert
             ):
            # un-select selection region, if any
            self.cancel_action()

            # replace text
            pos = self.get_position()
            self.delete_text(pos, pos + len(text))
            super(zEntry, self).insert_text(text, pos)
        else:                           # insert mode
            # clear selection region, if any
            sel = self.get_selection_bounds()
            if sel:
                self.delete_text(* sel)

            # insert text
            pos = self.get_position()
            super(zEntry, self).insert_text(text, pos)
        # move cursor over
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

            if msg['prev_cmd'] == 'backward-delete-{0}'.format(task):
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

            if msg['prev_cmd'] == 'forward-delete-{0}'.format(task):
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
            if msg['prev_cmd'] in [ 'kill-ring-yank', 'kill-ring-yank-pop' ]:
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
            start = zSyntaxParser( self.get_chars(0, curr),
                                   non_split = { 'DQUOTE' : ( 0, '"', '"' ), 'SQUOTE' : ( 0, "'", "'" ), }
                                   ).get_word_bounds(curr, conn_back = True)[0]

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
            start = zSyntaxParser( self.get_chars(0, curr),
                                   non_split = { 'DQUOTE' : ( 0, '"', '"' ), 'SQUOTE' : ( 0, "'", "'" ), }
                                   ).get_word_bounds(curr, conn_back = True)[0]

        self.select_region(start, curr)
        self.delete_selection()
        self.unset_mark()
        self.insert_text(word, always_insert = True)


    def is_word_start(self, pos = None, letter = r'\S'):
        if pos == None:
            pos = self.get_position()
        return self.__test_cursor_anchor(pos, False, True, letter)

    def is_in_word(self, pos = None, letter = r'\S'):
        if pos == None:
            pos = self.get_position()
        return self.__test_cursor_anchor(pos, True, True, letter)

    def is_word_end(self, pos = None, letter = r'\S'):
        if pos == None:
            pos = self.get_position()
        return self.__test_cursor_anchor(pos, True, False, letter)

    def is_out_word(self, pos = None, letter = r'\S'):
        if pos == None:
            pos = self.get_position()
        return self.__test_cursor_anchor(pos, False, False, letter)


    def get_mark(self):
        return self.__selection_mark

    def set_mark(self, where = None, append = ''):
        if not append:
            self.unset_mark()

        if where == None:
            where = self.get_position()

        max_pos = self.get_text_length()
        while where < 0:
            where += max_pos

        if not self.get_has_selection():
            self.__selection_mark = where

        # for set_mark_*
        if append:
            if append == 'left' and where > 0:
                where -= 1
            elif append == 'right' and where < max_pos:
                where += 1
            elif append in [ 'up', 'start' ]:
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

    import majormode as __mode__

    target_buffer = {           # source-target matching for duoble-buffering system
        'disp' : 'true',
        'true' : 'disp',
        }

    global_func_list = [
        'align-line',
        'align-region',
        'align-or-complete',
        'complete',
        'complete-list',

        'backward-char',
        'backward-delete-char',
        'forward-char',
        'forward-delete-char',

        'backward-word',
        'backward-delete-word',
        'forward-word',
        'forward-delete-word',

        'backward-line',
        'backward-delete-line',
        'forward-line',
        'forward-delete-line',

        'backward-para',
        'backward-delete-para',
        'forward-para',
        'forward-delete-para',

        'kill-region',
        'kill-ring-save',
        'kill-ring-yank',
        'kill-ring-yank-pop',

        'set-mark-command',
        'set-mark-move-left',
        'set-mark-move-right',
        'set-mark-move-up',
        'set-mark-move-down',
        'set-mark-move-start',
        'set-mark-move-end', 
        'set-mark-select-all',
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

        # initialize vars
        self.set_editor(editor)
        self.center = self

        # initialize double-buffering buffers
        self.buff = {
            'disp' : super(zTextView, self).get_buffer(),
            'true' : None,
            }

        self.buff['disp'].create_tag(
            'selected',
            foreground = zTheme.color_map['text_selected'],
            background = zTheme.color_map['base_selected']
            )

        for key in zTheme.color_map_fg_hilite_key:
            self.buff['disp'].create_tag(
                key, foreground = zTheme.color_map[key]
                )
        for key in zTheme.color_map_bg_hilite_key:
            self.buff['disp'].create_tag(
                key, background = zTheme.color_map[key]
                )

        self.__state_swap = {
            'state' : zAtomicChange([]), # the state to hold (multiple) buffer change(s)
            'more'  : False,             # flag indicate whether the above state is ended
            }
        self.__buff_watcher = { # need to be disconnected in destroy()
            'disp' : [
                self.buff['disp'].connect('insert_text',  self._sig_buffer_text_inserting, 'disp'),
                self.buff['disp'].connect('delete_range', self._sig_buffer_range_deleting, 'disp'),
                ],
            'hilite' : [        # this will use self.__state_swap to obtain buffer state information
                self.buff['disp'].connect_after('insert_text',  self._sig_disp_text_inserted),
                self.buff['disp'].connect_after('delete_range', self._sig_disp_range_deleted),
                ],
            'misc' : [
                self.buff['disp'].connect_after('mark-set', self._sig_mark_set),
                ],
            }

        # set up stroke listener
        self.completer = zComplete(self, append_space = True)
        self.__listener = zStrokeListener() # default listener
        self.listener = self.__listener     # interface listener

        # customize proporties
        self.set_editable(True) # default editable
        self.set_left_margin(5) # leave 5px at left
        self.set_right_margin(5)# leave 5px at right

        # register callbacks for function bindings
        self.default_func_callback = {
            'align-line'            : lambda msg: self.align_line(),
            'align-region'          : lambda msg: self.align_region(),
            'align-or-complete'     : lambda msg: self.align_or_complete(),
            'complete'              : lambda msg: self.complete(),
            'complete-list'         : lambda msg: self.complete_list(),

            'backward-char'         : lambda msg: self.backward(       'char'),
            'backward-delete-char'  : lambda msg: self.backward_delete('char', msg),
            'forward-char'          : lambda msg: self.forward(        'char'),
            'forward-delete-char'   : lambda msg: self.forward_delete( 'char', msg),

            'backward-word'         : lambda msg: self.backward(       'word'),
            'backward-delete-word'  : lambda msg: self.backward_delete('word', msg),
            'forward-word'          : lambda msg: self.forward(        'word'),
            'forward-delete-word'   : lambda msg: self.forward_delete( 'word', msg),

            'backward-line'         : lambda msg: self.backward(       'line'),
            'backward-delete-line'  : lambda msg: self.backward_delete('line', msg),
            'forward-line'          : lambda msg: self.forward(        'line'),
            'forward-delete-line'   : lambda msg: self.forward_delete( 'line', msg),

            'backward-para'         : lambda msg: self.backward(       'para'),
            'backward-delete-para'  : lambda msg: self.backward_delete('para', msg),
            'forward-para'          : lambda msg: self.forward(        'para'),
            'forward-delete-para'   : lambda msg: self.forward_delete( 'para', msg),

            'kill-region'           : lambda msg: self.kill_ring_manip('kill', msg),
            'kill-ring-save'        : lambda msg: self.kill_ring_manip('save', msg),
            'kill-ring-yank'        : lambda msg: self.kill_ring_manip('yank', msg),
            'kill-ring-yank-pop'    : lambda msg: self.kill_ring_manip('ypop', msg),

            'set-mark-command'      : lambda msg: self.set_mark(),
            'set-mark-move-left'    : lambda msg: self.set_mark(append = 'left'),
            'set-mark-move-right'   : lambda msg: self.set_mark(append = 'right'),
            'set-mark-move-up'      : lambda msg: self.set_mark(append = 'up'),
            'set-mark-move-down'    : lambda msg: self.set_mark(append = 'down'),
            'set-mark-move-start'   : lambda msg: self.set_mark(append = 'start'),
            'set-mark-move-end'     : lambda msg: self.set_mark(append = 'end'),
            'set-mark-select-all'   : lambda msg: ( self.set_mark(self.buff['disp'].get_end_iter()),
                                                    self.place_cursor(self.buff['disp'].get_start_iter()),
                                                    ),
            }
        for (func, cb) in self.default_func_callback.iteritems():
            self.__listener.register_func_callback(func, cb)

        # connect overridden signals
        self.connect('button-press-event',   self._sig_button_press)
        self.connect('button-release-event', self._sig_button_release)

        self.mouse_motion_id = self.connect('motion_notify_event', self._sig_mouse_motion)
        self.handler_block(self.mouse_motion_id)

        # start watching selection
        gobject.timeout_add(20, self.__watch_selection)


    ### overridden signal definition
    def _sig_mark_set(self, widget, iter, textmark, offset = None):
        if textmark.get_name() == 'insert': # is the cursor
            # get current line coordinates
            if offset < 0:
                offset  = iter.get_offset()
            else:
                iter = self.buff['disp'].get_iter_at_offset(offset)
            ln_cord = self.get_line_yrange(iter)
            if not ln_cord or not ln_cord[1]:
                # fail to get line height, register for next checking
                gobject.timeout_add(10, lambda: self._sig_mark_set(widget, iter, textmark, offset))
                # since self._sig_mark_set() always return False, each timeout will be terminated right away
                return False
            line_c = ln_cord[0] / ln_cord[1]
            self.buff['true'].place_cursor( # backup cursor position
                self.buff['true'].get_iter_at_offset(offset)
                )

            # get window capacity
            win_rect = self.get_visible_rect()
            nlines = (win_rect.height + ln_cord[1] / 4) / ln_cord[1]
                                # a line of more than 75% shown count as 1 line

            if nlines >= 7:     # 7+  lines shown, using 3-line adjustment
                adjust = 3
            elif nlines >= 5:   # 5~7 lines shown, using 2-line adjustment
                adjust = 2
            elif nlines >= 3:   # 3~4 lines shown, using 1-line adjustment
                adjust = 1
            else:               # 1~2 lines shown, do not adjust anything
                return False

            # get line position
            space_req   = adjust * ln_cord[1]
            space_above = ln_cord[0] - win_rect.y
            space_below = win_rect.height - space_above - ln_cord[1]
            scroll_up   = space_above < space_below and space_above < space_req
            scroll_down = space_above > space_below and space_below < space_req

            # scroll to the calculated position, if needed
            if scroll_up or scroll_down:
                scroll_pos = scroll_up and max(0, ln_cord[0] - space_req) or (ln_cord[0] + space_req)
                self.scroll_to_iter(self.get_line_at_y(scroll_pos)[0], 0)
        return False

    def _sig_buffer_text_inserting(self, textbuffer, ins_iter, text, length, src):
        invalid = re.findall(r'[^\x00-\xff]', text.decode('utf8'))
        if invalid:
            textbuffer.emit_stop_by_name('insert_text')
            raise ValueError(''.join([ "Invalid characher(s) in the text: '", "', '".join(invalid), "'" ]))
        change = zBufferChange(text, ins_iter.get_offset(), 'i')
        self.__sync_buff(zTextView.target_buffer[src], change)

    def _sig_buffer_range_deleting(self, textbuffer, start_iter, end_iter, src):
        change = zBufferChange(textbuffer.get_text(start_iter, end_iter, False), start_iter.get_offset(), 'd')
        self.__sync_buff(zTextView.target_buffer[src], change)

    def _sig_disp_text_inserted(self, textbuffer, ins_iter, text, length):
        if not self.__state_swap['more']:
            self.hilite()

    def _sig_disp_range_deleted(self, textbuffer, start_iter, end_iter):
        if not self.__state_swap['more']:
            self.hilite()


    def _sig_button_press(self, widget, event):
        clicked_iter = self.get_iter_at_location(
            * self.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, int(event.x), int(event.y))
              )

        if event.button == 1:
            # left click
            if event.type == gtk.gdk.BUTTON_PRESS:
                # single click
                self.unset_mark()
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
            if not self.get_has_selection():
                self.place_cursor(clicked_iter)
            menu = zPopupMenu()

            if self.get_editable():
                undo_stack = self.buff['true'].undo_stack
            else:
                undo_stack = None

            mi_undo = gtk.MenuItem('_Undo')
            menu.append(mi_undo)
            if undo_stack and not undo_stack.is_init():
                mi_undo.connect('activate', lambda *arg: self.buffer_undo())
            else:
                mi_undo.set_property('sensitive', False)

            mi_redo = gtk.MenuItem('_Redo')
            menu.append(mi_redo)
            if undo_stack and not undo_stack.is_last():
                mi_redo.connect('activate', lambda *arg: self.buffer_redo())
            else:
                mi_redo.set_property('sensitive', False)

            menu.append(gtk.SeparatorMenuItem())

            mi_cut = gtk.MenuItem('Cu_t')
            menu.append(mi_cut)
            if self.get_editable() and self.get_has_selection():
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
            if self.get_editable() and zKillRing.resurrect():
                mi_paste.connect('activate', lambda *arg: self.kill_ring_manip('yank', None))
            else:
                mi_paste.set_property('sensitive', False)

            mi_select_all = gtk.MenuItem('Select _All')
            menu.append(mi_select_all)
            mi_select_all.connect('activate', lambda *arg: (
                    self.set_mark(self.buff['disp'].get_end_iter()),
                    self.place_cursor(self.buff['disp'].get_start_iter()),
                    ))

            menu.show_all()
            menu.popup(None, None, None, event.button, event.time)

            self.emit('populate_popup', menu)

        if not self.is_focus():
            self.grab_focus()
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
    def destroy(self):
        for key in self.__buff_watcher:
            for handler in self.__buff_watcher[key]:
                if self.buff['disp'].handler_is_connected(handler):
                    self.buff['disp'].disconnect(handler)
                if self.buff['true'].handler_is_connected(handler):
                    self.buff['true'].disconnect(handler)
        super(zTextView, self).destroy()


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
        return self.task_listenning() != None

    def task_listenning(self):
        return self.__listener.is_listenning_on(self)

    def block_listenning(self):
        self.__listener.block_listenning(self)

    def unblock_listenning(self):
        self.__listener.unblock_listenning(self)

    def listen_on_task(self, task = None, init_widget = None):
        self.__listener.listen_on(self, task, init_widget)

    def listen_off(self):
        self.__listener.listen_off(self)


    def insert_text(self, text, always_insert = False):
        if self.get_editor().caps_on():
            text = text.upper()
        if ( self.get_overwrite() and # overwrite mode
             not always_insert
             ):
            # un-select selection region, if any
            self.cancel_action()

            # replace text
            start_iter = self.get_cursor_iter()
            line_end   = self.get_cursor_iter()
            self.forward_to_line_end(line_end)
            end_iter   = self.get_cursor_iter()
            end_iter.forward_chars(len(text))

            self.__state_swap['more'] = True
            if line_end.compare(end_iter) < 0:
                self.buff['disp'].delete(start_iter, line_end)
            else:
                self.buff['disp'].delete(start_iter, end_iter)
            self.__state_swap['more'] = False
            self.buff['disp'].insert_at_cursor(text)
        else:                           # insert mode
            # clear selection region, if any
            sel = self.get_selection_bounds()
            if sel:
                self.delete_selection()

            # insert text
            self.buff['disp'].insert_at_cursor(text)

    def get_text(self):
        return self.buff['disp'].get_text(self.buff['disp'].get_start_iter(), self.buff['disp'].get_end_iter(), False)

    def set_text(self, text, no_scrolling = False):
        self.buff['disp'].set_text(text)
        if not no_scrolling:
            self.place_cursor(self.get_cursor_iter(use_backup = True))


    def get_has_selection(self):
        return self.get_mark() != None

    def get_selection_bound(self):
        if self.get_has_selection():
            return self.buff['disp'].get_iter_at_mark(self.get_mark())
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
            self.buff['disp'].delete(* sel)
            self.unset_mark()


    def modify_base(self, state, color):
        super(zTextView, self).modify_base(state, color)
        if state == gtk.STATE_SELECTED:
            tag_table = self.buff['disp'].get_tag_table()
            tag_table.remove(tag_table.lookup('selected'))
            self.buff['disp'].create_tag(
                'selected',
                foreground = zTheme.color_map['text_selected'],
                background = zTheme.color_map['base_selected']
                )

    def modify_text(self, state, color):
        super(zTextView, self).modify_text(state, color)
        if state == gtk.STATE_SELECTED:
            tag_table = self.buff['disp'].get_tag_table()
            tag_table.remove(tag_table.lookup('selected'))
            self.buff['disp'].create_tag(
                'selected',
                foreground = zTheme.color_map['text_selected'],
                background = zTheme.color_map['base_selected']
                )

    def modify_fg_hilite(self, hilite_type, hilite = True):
        tag_table = self.buff['disp'].get_tag_table()
        tag_table.remove(tag_table.lookup(hilite_type))
        self.buff['disp'].create_tag(
            hilite_type, foreground = zTheme.color_map[hilite_type]
            )
        if hilite:
            self.hilite()

    def modify_bg_hilite(self, hilite_type, hilite = True):
        tag_table = self.buff['disp'].get_tag_table()
        tag_table.remove(tag_table.lookup(hilite_type))
        self.buff['disp'].create_tag(
            hilite_type, background = zTheme.color_map[hilite_type]
            )
        if hilite:
            self.hilite()


    def get_buffer(self):
        if self.buff['true']:
            return self.buff['true']
        else:
            return self.buff['disp']

    def set_buffer(self, buff, dry_run = False):
        if not dry_run:
            if self.buff['true']:
                for handler in self.__buff_watcher['true']:
                    if self.buff['true'].handler_is_connected(handler):
                        self.buff['true'].disconnect(handler)

            self.buff['true'] = buff
            self.__buff_watcher['true'] = [ # need to be disconnect in destroy()
                self.buff['true'].connect('insert_text',  self._sig_buffer_text_inserting, 'true'),
                self.buff['true'].connect('delete_range', self._sig_buffer_range_deleting, 'true'),
                ]

        # replace the content of the current display buffer
        self.__sync_buff_start('disp')

        self.buff['disp'].set_text(
            self.buff['true'].get_text(self.buff['true'].get_start_iter(), self.buff['true'].get_end_iter(), False)
            )
        self.unset_mark()
        self.place_cursor(self.get_cursor_iter(use_backup = True))

        self.__sync_buff_end('disp')


    # no overridden for get_editable()
    def set_editable(self, setting):
        super(zTextView, self).set_editable(setting)

        # enable/disable the editor related function bindings
        for func in zTextView.global_func_list:
            self.__listener.set_func_enabled(func, setting)


    def place_cursor(self, where):
        self.buff['disp'].place_cursor(where)
        self._sig_mark_set(self.buff['disp'], where, self.buff['disp'].get_insert())

    def place_cursor_at_offset(self, offset):
        self.place_cursor(self.buff['disp'].get_iter_at_offset(offset))
    ### end of overridden function definition


    ### editor related API
    def apply_change(self, buff, change, get_iter_func):
        if change.action == 'i':
            buff.insert(
                get_iter_func(change.offset),
                change.content
                )
        else:
            buff.delete(
                get_iter_func(change.offset),
                get_iter_func(change.offset + len(change.content)),
                )

    def align_line(self):
        ast  = self.get_ast()
        buff = self.buff['disp']

        if not ast  or  not ast['syntax_tree']: # cannot align
            return

        line_tuple = self.get_current_line()
        state = self.__mode__.MODE_MAP[ast['major_mode']].align(line_tuple, ast['syntax_tree'])
        if state:
            self.__state_swap['more'] = True
            for change in state[:-1]:
                self.apply_change(buff, change, lambda offset: buff.get_iter_at_line_offset(line_tuple[0], offset))
            self.__state_swap['more'] = False
            self.apply_change(buff, state[-1], lambda offset: buff.get_iter_at_line_offset(line_tuple[0], offset))
        # move cursor to line end, if no outstanding data in between
        cursor = self.get_cursor_iter()
        eoline = cursor.copy()
        self.forward_to_line_end(eoline)
        if self.buff['disp'].get_text(cursor, eoline).isspace():
            self.place_cursor(eoline)


    def align_region(self):
        sel = self.get_selection_bounds()
        if not sel:             # no selection region
            return              # early return
        ast = self.get_ast()
        buff = self.buff['disp']

        if not ast  or  not ast['syntax_tree']: # cannot align
            return

        mode = self.__mode__.MODE_MAP[ast['major_mode']]
        changed = False
        self.__state_swap['more'] = True
        for line_num in range(sel[0].get_line(), sel[1].get_line() + 1):
            line_tuple = self.get_line_at(line_num)
            if not line_tuple[1]: # empty line
                continue          # skip it
            state = mode.align(line_tuple, ast['syntax_tree'])
            if state:
                for change in state:
                    self.apply_change(buff, change, lambda offset: buff.get_iter_at_line_offset(line_tuple[0], offset))
                changed = True
        if changed:
            last_change = self.__state_swap['state'].pop() # pop out last change
            # revert last change
            self.apply_change(buff, last_change.revert(), buff.get_iter_at_offset)
            self.__state_swap['state'].pop() # pop out the revertion of last change
            self.__state_swap['more'] = False
            # re-apply last change
            self.apply_change(buff, last_change, buff.get_iter_at_offset)
            self.unset_mark()       # cancel selection

    def align_or_complete(self):
        if self.is_word_end():
            self.complete()
        else:
            self.align_line()


    def hilite(self):
        ast  = self.get_ast()
        buff = self.buff['disp']

        if not ast  or  not ast['syntax_tree']: # cannot highlight
            return

        # clear previous highlighting tags
        iter_s = buff.get_start_iter()
        iter_e = buff.get_end_iter()
        for key in zTheme.color_map_fg_hilite_key:
            buff.remove_tag_by_name(key, iter_s, iter_e)
        for key in zTheme.color_map_bg_hilite_key:
            buff.remove_tag_by_name(key, iter_s, iter_e)

        # apply new highlighting tags
        for (pos_s, key, pos_e) in self.__mode__.MODE_MAP[ast['major_mode']].hilite(ast['syntax_tree']):
            buff.apply_tag_by_name(
                key,
                buff.get_iter_at_offset(pos_s),
                buff.get_iter_at_offset(pos_e)
                )


    def buffer_undo(self):
        return self.__buffer_undo('undo')

    def buffer_redo(self):
        return self.__buffer_undo('redo')


    def backward(self, task):
        self.place_cursor(self.__backward(task, extend_selection = True))

    def backward_delete(self, task, msg):
        target_iter = self.__backward(task)
        if task != 'char':
            text_to_kill = self.buff['disp'].get_text(target_iter, self.get_cursor_iter())

            if msg['prev_cmd'] == 'backward-delete-{0}'.format(task):
                zKillRing.prepend_killing(text_to_kill)
            else:
                zKillRing.kill(text_to_kill)

        self.buff['disp'].delete(target_iter, self.get_cursor_iter())
        self.unset_mark()

    def forward(self, task):
        self.place_cursor(self.__forward(task, extend_selection = True))

    def forward_delete(self, task, msg):
        curr_iter   = self.get_cursor_iter()
        target_iter = self.__forward(task)
        if curr_iter.equal(target_iter):
            return
        if task != 'char':
            text_to_kill = self.buff['disp'].get_text(self.get_cursor_iter(), target_iter)

            if msg['prev_cmd'] == 'forward-delete-{0}'.format(task):
                zKillRing.append_killing(text_to_kill)
            else:
                zKillRing.kill(text_to_kill)

        self.buff['disp'].delete(curr_iter, target_iter)
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
                kr.kill(self.buff['disp'].get_text(sel[0], sel[1], False))

                if task == 'kill':
                    self.buff['disp'].delete(* sel)
            else:
                self.get_editor().get_last_line().set_text('', '(mark is not set now)')

        elif task == 'yank':
            yanked_text = kr.resurrect()

            if yanked_text:
                start_pos = self.get_cursor_pos()
                self.insert_text(yanked_text)
                end_pos   = self.get_cursor_pos()

                self.__prev_yank_bounds = ( start_pos, end_pos )
            else:
                self.__prev_yank_bounds = ( )
        else:
            if msg['prev_cmd'] in [ 'kill-ring-yank', 'kill-ring-yank-pop' ]:
                yanked_text = kr.circulate_resurrection()

                if yanked_text:
                    self.buff['disp'].delete(
                        self.buff['disp'].get_iter_at_offset(self.__prev_yank_bounds[0]),
                        self.buff['disp'].get_iter_at_offset(self.__prev_yank_bounds[1])
                        )

                    start_pos = self.get_cursor_pos()
                    self.insert_text(yanked_text)
                    end_pos   = self.get_cursor_pos()

                    self.__prev_yank_bounds = ( start_pos, end_pos )
                else:
                    self.__prev_yank_bounds = ( )
            else:
                self.get_editor().get_last_line().set_text('', '(previous command was not a yank)')
                self.__listener.invalidate_curr_cmd()

        self.unset_mark()


    def get_cursor_pos(self, target = 'disp'):
        return self.buff[target].get_property('cursor-position')

    def get_cursor_iter(self, use_backup = False):
        if use_backup:
            return self.buff['disp'].get_iter_at_offset(self.get_cursor_pos('true'))
        return self.buff['disp'].get_iter_at_mark(self.buff['disp'].get_insert())


    def get_line_at(self, line_iter):
        if isinstance(line_iter, int):
            line_iter = self.buff['disp'].get_iter_at_line(line_iter)
        start_iter = line_iter.copy()
        end_iter   = line_iter.copy()

        start_iter.set_line_offset(0)
        self.forward_to_line_end(end_iter)

        return ( line_iter.get_line(),
                 self.buff['disp'].get_text(start_iter, end_iter, False),
                 line_iter.get_line_offset(),
                 )

    def set_line_at(self, line_iter, line_tuple):
        if isinstance(line_iter, int):
            line_iter = self.buff['disp'].get_iter_at_line(line_iter)
        start_iter = line_iter.copy()
        end_iter   = line_iter.copy()

        start_iter.set_line_offset(0)
        self.forward_to_line_end(end_iter)

        # replace the current line with the new line
        self.__state_swap['more'] = True
        self.buff['disp'].delete(start_iter, end_iter)
        self.__state_swap['more'] = False
        self.buff['disp'].insert(start_iter, line_tuple[1])
        self.place_cursor(self.buff['disp'].get_iter_at_line_offset(line_tuple[0], line_tuple[2]))

    def get_current_line(self):
        return self.get_line_at(self.get_cursor_iter())

    def set_current_line(self, line_tuple):
        self.set_line_at(self.get_cursor_iter(), line_tuple)


    def get_current_word(self):
        ast = self.get_ast()
        end_iter = self.get_cursor_iter()

        if ast  and  ast['syntax_tree']:
            ( indx, node ) = ast['syntax_tree'].get_word_node(end_iter.get_offset())

        if indx == None: # cannot use AST, fall back to regular fetch mode
            start_iter = self.get_cursor_iter()

            # move start back to the word start
            start_iter.backward_word_start()

            return self.buff['disp'].get_text(start_iter, end_iter, False)
        else:
            return node.text

    def set_current_word(self, word):
        ast = self.get_ast()
        end_iter = self.get_cursor_iter()

        if ast  and  ast['syntax_tree']:
            ( indx, node ) = ast['syntax_tree'].get_word_node(end_iter.get_offset())

        if indx == None: # cannot use AST, fall back to regular fetch mode
            start_iter = self.get_cursor_iter()

            # move start back to the word start
            start_iter.backward_word_start()
        else:
            start_iter = self.buff['disp'].get_iter_at_offset(end_iter.get_offset() - len(node.text))

        # replace the current word with the new word, if differs
        old_word = self.buff['disp'].get_text(start_iter, end_iter, False)
        if old_word == word:
            return              # no need to set, early return
        if word.startswith(old_word):
            # appending to old word
            self.insert_text(word[len(old_word):])
            return              # this is a speed-up for completion
        self.__state_swap['more'] = True
        self.buff['disp'].delete(start_iter, end_iter)
        self.__state_swap['more'] = False
        self.buff['disp'].insert(start_iter, word)


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
        return self.buff['disp'].get_mark('selection_start')

    def set_mark(self, where = None, append = ''):
        if not append:
            self.unset_mark()

        if not where:
            where = self.get_cursor_iter()

        if not self.get_has_selection():
            self.buff['disp'].create_mark('selection_start', where, False)
            self.buff['disp'].create_mark('selection_end', where, False) # for internal usage

            self.__mark_move_vert_offset = self.get_cursor_iter().get_line_offset()

            self.get_editor().get_last_line().set_text('', 'Mark set')

        # for set_mark_*
        if append:
            if append == 'left':
                where.backward_char()
                self.__mark_move_vert_offset = where.get_line_offset()

            elif append == 'right':
                where.forward_char()
                self.__mark_move_vert_offset = where.get_line_offset()

            elif append == 'start':
                where = self.buff['disp'].get_start_iter()

            elif append == 'end':
                where = self.buff['disp'].get_end_iter()

            else:
                if append == 'up':
                    where.backward_line()
                else:
                    where.forward_line()
                if self.__mark_move_vert_offset < where.get_chars_in_line():
                    # move the cursor to the recorded offset, as long as its valid
                    where.set_line_offset(self.__mark_move_vert_offset)
                else:
                    self.forward_to_line_end(where)

            self.place_cursor(where)

    def unset_mark(self):
        if self.get_has_selection():
            self.buff['disp'].delete_mark_by_name('selection_start')
            self.buff['disp'].delete_mark_by_name('selection_end') # for internal usage

            self.__mark_move_vert_offset = None

            self.buff['disp'].remove_tag_by_name(
                'selected', self.buff['disp'].get_start_iter(), self.buff['disp'].get_end_iter()
                )


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

    def get_ast(self):
        return self.get_editor().get_ast()

    def set_editor(self, editor):
        self.__editor_frame = editor


    ### supporting function
    def __buffer_undo(self, action):
        buff  = self.buff['true']
        if action == 'undo':
            state = buff.undo_stack.undo()
        else:
            state = buff.undo_stack.redo()

        if state:
            self.__state_swap['more'] = True
            for change in state[:-1]:
                self.apply_change(buff, change, buff.get_iter_at_offset)
            self.__state_swap['more'] = False
            self.apply_change(buff, state[-1], buff.get_iter_at_offset)

            self.place_cursor_at_offset(state[0].offset) # place cursor at end of first change

            # test saved state
            if self.buff['true'].undo_stack.is_saved():
                self.get_editor().active_buffer.set_modified(False)

            return True
        return False


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
            if not target_iter.is_start()  and  self.is_para_start(self.buff['disp'], target_iter):
                # not at buffer start but at para start, move to prev line
                target_iter.backward_line()

            target_iter = self.get_para_start(self.buff['disp'], target_iter)

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
            if not target_iter.is_end()  and  self.is_para_end(self.buff['disp'], target_iter):
                # not at buffer end but at para end, move to next line
                target_iter.forward_line()

            target_iter = self.get_para_end(self.buff['disp'], target_iter)

        else:
            raise KeyError('{0}: invalid task for delete pattern.'.format(task))

        return target_iter


    def __sync_buff_start(self, target):
        for handler in self.__buff_watcher[target]:
            if self.buff[target].handler_is_connected(handler):
                self.buff[target].handler_block(handler)

    def __sync_buff_end(self, target):
        for handler in self.__buff_watcher[target]:
            if self.buff[target].handler_is_connected(handler):
                self.buff[target].handler_unblock(handler)

    def __sync_buff(self, target, change = None):
        self.__sync_buff_start(target) # start synchronizing

        if change:
            self.__state_swap['state'].append(change)
            if not self.__state_swap['more']:
                # no more to append, process the state
                if target == 'true'  and  self.buff['true'].undo_stack:
                    # new state applied on true buffer, record it
                    self.buff['true'].undo_stack.new_state(self.__state_swap['state'])
                self.__state_swap['state'] = zAtomicChange([]) # reset swap area

        self.apply_change(self.buff[target], change, self.buff[target].get_iter_at_offset)
        self.__sync_buff_end(target) # synchronizing ended


    def __watch_selection(self):
        if self.get_has_selection():
            # clear previous selection
            iter_start = self.buff['disp'].get_iter_at_mark(self.get_mark())
            iter_end   = self.buff['disp'].get_iter_at_mark(self.buff['disp'].get_mark('selection_end'))
            self.buff['disp'].remove_tag_by_name('selected', iter_start, iter_end)

            # update new selection
            iter_end = self.get_cursor_iter()
            self.buff['disp'].move_mark_by_name('selection_end', iter_end) # move end mark
            self.buff['disp'].apply_tag_by_name('selected', iter_start, iter_end)

        return True             # keep watching until dead


    def __watch_true_buff_reload(self):
        if self.buff['true'].reloading:
            return True

        self.set_buffer(self.buff['true'], dry_run = True) # notify completion of modification
        return False
    ### end of supporting function
