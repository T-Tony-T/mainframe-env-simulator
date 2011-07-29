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

        self.try_completing = 0 # how many times tring completion; reset to 0 if completion success


    def insert_text(self, text):
        pos = self.get_position()
        super(gtk.Entry, self).insert_text(text, pos)
        self.set_position(pos + len(text))


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


        self.__sig_id = {}      # stores all signals connected to the interactive line

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
        self.__locked = False   # if locked, all `set_*()` refer to `blink()`

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


    ### public signal definition
    @staticmethod
    def _sig_key_pressed(widget, event, task = 'path'):
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
            widget.lastline.unlock()
            widget.lastline.set_text('', '')
            return True
        elif stroke.upper() == 'RETURN':
            if widget.get_text():
                widget.lastline.unlock()
            else:
                widget.lastline.blink_text()
            return True
        elif stroke.upper() == 'TAB':
            widget.try_completing += 1

            if task == 'path':
                curr_path = widget.get_text()
                if curr_path:
                    # normalize the path
                    curr_path = os.path.abspath(os.path.expanduser(curr_path))
                    # get the completion list
                    if os.path.isdir(curr_path):
                        comp_list = os.listdir(curr_path)
                        curr_name = ''
                    else:
                        ( curr_path, curr_name ) = os.path.split(curr_path)
                        comp_list = [ fn for fn in os.listdir(curr_path) if fn.startswith(curr_name) ]
                    # check for unique complete
                    if len(comp_list) == 1:
                        # exact match, complete it
                        curr_path = os.path.join(curr_path, comp_list[0])
                        if os.path.isdir(curr_path):
                            curr_path += os.path.sep

                        widget.try_completing = 0
                    else:
                        # check for max complete
                        for indx in range(len(curr_name), len(comp_list[0])):
                            next_char = comp_list[0][indx]
                            conflict = False
                            for item in comp_list[1:]:
                                if indx == len(item) or next_char != item[indx]:
                                    conflict = True
                                    break
                            if conflict:
                                break
                            else:
                                # has at least 1 char completed
                                widget.try_completing = 0
                                curr_name += next_char
                        curr_path = os.path.join(curr_path, curr_name)
                        if widget.try_completing > 1:
                            # more than one try
                            print 'list completion not implemented yet'

                    widget.set_text(curr_path)
                    widget.set_position(-1)

            return True

        return False
    ### end of public signal definition


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
        return self.__locked

    def lock(self):
        self.__locked = True

    def unlock(self):
        self.__locked = False


    def clear(self):
        if self.is_locked():
            return
        self.set_text('', '')

    def reset(self):
        for (k, v) in self.__sig_id.iteritems():
            if self.__line_interactive.handler_is_connected(v):
                self.__line_interactive.disconnect(v)
        self.__sig_id = {}

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
            self.__line_interactive.set_text(entry_text)
            self.__line_interactive.set_position(-1)
    ### end of overridden function definition


    def blink(self, hlt_text, entry_text, period = 1):
        self.blink_set(
            hlt_text, entry_text, period,
            self.__line_highlight.get_text(), self.__line_interactive.get_text()
            )

    def blink_text(self, period = 0.09):
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
        self.__line_interactive.set_text(entry_text[indx])

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
    def insert_text(self, text):
        buff = self.get_buffer()
        buff.insert_at_cursor(text)
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
            lastline.connect('key-press-event', zLastLine._sig_key_pressed, 'path')

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

        print path


    def get_editor(self):
        return self.__editor_frame

    def set_editor(self, editor):
        self.__editor_frame = editor
