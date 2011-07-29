# this is the text module of the zComponent package

from zBase import z_ABC, zTheme

import os
import pygtk
pygtk.require('2.0')
import gtk
import gobject


######## ######## ######## ######## ########
########           zEntry           ########
######## ######## ######## ######## ########
class zEntry(gtk.Entry):
    '''A gtk.Entry that has additional methods'''
    def __init__(self):
        super(zEntry, self).__init__()

        self.__comp_list = []       # completion list
        self.__try_completing = 0   # how many times tring completion; reset to 0 if completion success

        self.__locked_widget = None # the widget that locks the entry


    ### public signal definition
    @staticmethod
    def _sig_key_pressed(entry, event, task = None):
        '''
        task = None
            the task that the entry is asked to complete.
            Could be one of the following:
              -  None  : no special rules applied.
              - 'path' : apply completion and checkings for getting a path.
              - 'file' : same to 'path' except text entered must not be a dir.
              - 'dir'  : same to 'path' except text entered must not be a file.
        '''
        if event.type != gtk.gdk.KEY_PRESS:
            return False

        if event.is_modifier:
            return False

        ctrl_mod_mask = gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK

        if (event.state & ctrl_mod_mask) == ctrl_mod_mask:
            stroke = 'C-M-' + gtk.gdk.keyval_name(event.keyval)

        elif event.state & gtk.gdk.CONTROL_MASK:
            stroke = 'C-' + gtk.gdk.keyval_name(event.keyval)

        elif event.state & gtk.gdk.MOD1_MASK:
            stroke = 'M-' + gtk.gdk.keyval_name(event.keyval)

        else:
            stroke = gtk.gdk.keyval_name(event.keyval)


        if stroke == 'C-g':
            # at any time, this means 'cancel'
            entry.__unlock()
            entry.set_text('')  # clear path to cancel
            return True
        elif stroke.upper() == 'RETURN':
            text_entered = entry.get_text()
            if text_entered:
                if ( (task == 'file' and not os.path.isdir(text_entered) ) or
                     (task == 'dir'  and not os.path.isfile(text_entered)) or
                     task in [ None, 'path' ] # tasks that require no checkings
                     ):
                    entry.__unlock()
                    return False # pass the 'enter' on to emit 'activate' signel
                else:
                    entry.popup_comp_list()
            return True
        elif stroke.upper() == 'TAB':
            entry.__try_completing += 1

            if task in [ 'path', 'dir', 'file' ]:
                curr_path = entry.get_text()
                if curr_path:
                    # normalize the path
                    curr_path = os.path.abspath(os.path.expanduser(curr_path))
                    # get the completion list
                    if os.path.isdir(curr_path):
                        entry.set_comp_list( os.listdir(curr_path) )
                        curr_name = ''
                    else:
                        ( curr_path, curr_name ) = os.path.split(curr_path)
                        entry.set_comp_list([ fn for fn in os.listdir(curr_path)
                                              if fn.startswith(curr_name)
                                              ])
                    if task == 'dir':
                        entry.set_comp_list([ fn for fn in entry.get_comp_list()
                                              if os.path.isdir(os.path.join(curr_path, fn))
                                              ])
                    # check for unique complete
                    if not entry.get_comp_list_len():
                        return True # no completion, early return
                    elif entry.get_comp_list_len() == 1:
                        # exact match, complete it
                        curr_path = os.path.join(curr_path, entry.get_comp_list()[0])
                        if os.path.isdir(curr_path):
                            curr_path += os.path.sep

                        entry.__try_completing = 0
                    else:
                        # check for max complete
                        for indx in range(len(curr_name), len(entry.get_comp_list()[0])):
                            next_char = entry.get_comp_list()[0][indx]
                            conflict = False
                            for item in entry.get_comp_list()[1:]:
                                if indx == len(item) or next_char != item[indx]:
                                    conflict = True
                                    break
                            if conflict:
                                break
                            else:
                                # has at least 1 char completed
                                entry.__try_completing = 0
                                curr_name += next_char
                        curr_path = os.path.join(curr_path, curr_name)
                        if entry.__try_completing > 1:
                            # more than one try
                            entry.popup_comp_list()

                    entry.__set_text(curr_path) # force to set the text
                    entry.set_position(-1)

            return True

        return False
    ### end of public signal definition


    ### overridden function definition
    def insert_text(self, text, widget = None):
        if self.is_locked() and self.__locked_widget != widget:
            raise AssertionError('Entry is locked. Permission denied.')

        pos = self.get_position()
        super(zEntry, self).insert_text(text, pos)
        self.set_position(pos + len(text))

    def set_text(self, text, widget = None):
        if self.is_locked() and self.__locked_widget != widget:
            raise AssertionError('Entry is locked. Permission denied.')

        self.__set_text(text)
    ### end of overridden function definition


    ### completion related functions
    def get_comp_list(self):
        return self.__comp_list

    def get_comp_list_len(self):
        return len(self.__comp_list)

    def set_comp_list(self, comp_list):
        self.__comp_list = comp_list

    def popup_comp_list(self):
        print 'list completion not implemented yet'
    ### end of completion related functions


    def is_locked(self):
        return self.__locked_widget

    def lock(self, widget):
        self.__locked_widget = widget

    def unlock(self, widget):
        if not self.__locked_widget:
            return              # no need to unlock, early return

        if widget == self.__locked_widget:
            self.__unlock()
        else:
            raise AssertionError('Cannot unlock the entry. Permission denied.')


    ### supporting functions
    def __set_text(self, text):
        super(zEntry, self).set_text(text)

    def __unlock(self):
        self.__locked_widget = None
    ### end of supporting functions


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
        self.__sig_id = {}          # stores all signals connected to the interactive line

        self.__lock_reset_func = None # see lock() and reset() for more information

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
    def connect(self, sig, callback, *data):
        if sig in self.__sig_id:
            raise ReferenceError('Already connected to a signal of the same type. Use reset() to disconnect all signals.')
        self.__sig_id[sig] = self.__line_interactive.connect(sig, callback, *data)

    def disconnect(self, handler):
        raise NotImplementedError('Method not implemented. Use reset() to disconnect all signals.')
    def handler_is_connected(self, handler):
        raise NotImplementedError('Method not implemented. Use reset() to disconnect all signals.')
    def handler_block(self, handler):
        raise NotImplementedError('Method not implemented. Use reset() to disconnect all signals.')
    def handler_unblock(self, handler):
        raise NotImplementedError('Method not implemented. Use reset() to disconnect all signals.')


    def is_focus(self):
        return self.__line_interactive.is_focus()

    def grab_focus(self):
        self.__line_interactive.grab_focus()


    def is_locked(self):
        return self.__line_interactive.is_locked()

    def lock(self, reset_func = None):
        '''if reset_func is set, it will be called when reset() is called'''
        if reset_func:
            self.__lock_reset_func = reset_func
        self.__line_interactive.lock(self)

    def unlock(self):
        self.__line_interactive.unlock(self)


    def clear(self):
        if self.is_locked():
            return
        self.set_text('', '')

    def reset(self):
        for (k, v) in self.__sig_id.iteritems():
            if self.__line_interactive.handler_is_connected(v):
                self.__line_interactive.disconnect(v)
        self.__sig_id = {}

        if self.__lock_reset_func:
            self.__lock_reset_func()
            self.__lock_reset_func = None

        self.unlock()
        self.set_editable(False)
        self.clear()


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
            self.__line_interactive.set_text(entry_text, self)
            self.__line_interactive.set_position(-1)
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
        self.__line_interactive.set_text(hlt_text, self)

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
        self.__line_interactive.set_text(blk_entry_text, self)

        # register the timer to alter the texts exactly once
        self.__set_alternation(1)
        gobject.timeout_add(
            int(period * 1000), self.__alternate_text,
            [ blk_hlt_text,   set_hlt_text   ],
            [ blk_entry_text, set_entry_text ]
            )


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
            self.__line_interactive.set_position(-1)

    def get_force_focus(self):
        return self.__force_focus

    def set_force_focus(self, setting):
        self.__force_focus = setting
        if setting:
            self.__line_interactive.handler_unblock(self.force_focus_id)
        else:
            self.__line_interactive.handler_block(self.force_focus_id)


    ### supporting function
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
        self.__line_interactive.set_text(entry_text[indx], self)

        self.__set_timer()

        return self.__n_alternation
    ### end of supporting function


######## ######## ######## ######## ########
########         zTextView          ########
######## ######## ######## ######## ########

class zTextView(z_ABC, gtk.TextView): # will be rewritten to get rid of gtk.TextView
    '''The Customized TextView that Support zEdit'''
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

    ### overridden function definition
    def insert_text(self, text, data = None):
        buff = self.get_buffer()
        buff.insert_at_cursor(text)

    def get_text(self):
        buff = self.get_buffer()
        buff.get_text()

    def set_text(self, text):
        buff = self.get_buffer()
        buff.set_text(text)
    ### end of overridden function definition


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
            lastline.reset()
            lastline.set_editable(True)
            lastline.set_force_focus(True)
            lastline.set_text('Write File: ', os.path.join(*path))
            lastline.connect('key-press-event', zEntry._sig_key_pressed, 'file')

            # lock the lastline until getting the path
            lastline.lock()
            while lastline.is_locked():
                gtk.main_iteration(False)
            ( msg, path ) = lastline.get_text()

            lastline.reset()
            self.grab_focus()

            if path:
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

        return buff.flush_to(path)


    def get_editor(self):
        return self.__editor_frame

    def set_editor(self, editor):
        self.__editor_frame = editor
