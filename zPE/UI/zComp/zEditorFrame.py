# this is the editor-frame module of the zComponent package

import io_encap
# this package should implement the following APIs:
#
#   is_binary(fn_list):         test if the fn_list corresponding to a binary file
#
#   is_file(fn_list):           test if the fn_list corresponding to a file
#   is_dir(fn_list):            test if the fn_list corresponding to a directory
#
#   new_file(fn_list):          create the file unless the fn_list corresponding to a file
#   new_dir(fn_list):           create the dir unless the fn_list corresponding to a directory
#
#   open_file(fn_list, mode):   open the file with the indicated mode
#
#   fetch(buff):                read content from the corresponding file to the zEditBuffer
#   flush(buff):                write content from the zEditBuffer to the corresponding file
#

from zBase import z_ABC, zTheme
from zFileManager import zDisplayPanel, zFileManager
from zText import zLastLine, zTextView
from zWidget import zComboBox, zTabbar

import os, copy, re
import pygtk
pygtk.require('2.0')
import gtk


######## ######## ######## ######## ########
########           zEdit            ########
######## ######## ######## ######## ########

class zEdit(z_ABC, gtk.VBox):
    '''A Multi-Buffer Text Editor with an Internal File Browser'''
    __style = 'other'           # see zEdit.set_style()
    __key_binding = {}          # see zEdit.set_key_binding()

    __tab_on = False            # see zEdit.set_tab_on()
    __tab_grouped = False       # see zEdit.set_tab_grouped()

    __last_line = None          # see zEdit.set_last_line()

    # see zEdit._sig_key_pressed() => 'emacs'
    __escaping = False
    __ctrl_char_map = {
        'C-I' : '\t',
        'C-J' : '\n',
        'C-M' : '\r',
        }

    # see zEdit._sig_key_pressed() => 'emacs'
    __commanding = False
    __command_content = ''
    __command_widget_focus_id = None

    # see zEdit._sig_key_pressed() => 'emacs'
    __mx_commanding = False
    __mx_command_content = ''
    @staticmethod
    def mx_commanding_reset():
        zEdit.__mx_commanding = False
        zEdit.__mx_command_content = ''

    __mx_command_prefix = 'M-x '

    _focus = None

    _auto_update = {
        # 'signal_like_string'  : [ (widget, callback, data_list), ... ]
        'buffer_focus_in'       : [  ],
        'buffer_focus_out'      : [  ],

        'populate_popup'        : [  ],

        'update_tabbar'         : [  ],

        # for key binding
        # use zEdit.reg_add_registry(reg)
        }

    def __init__(self, buffer_path = None, buffer_type = None):
        '''
        buffer_path
            a list of nodes representing the path of the file/buffer
            the editor is suppose to open.

            examples:
               OS    |          file             |             buffer_path
            ---------+---------------------------+-------------------------------------------
              Linux  | /home/user/doc/file       | [ '/', 'home', 'user', 'doc', 'file'    ]
             Windows | C:\User\Document\file.txt | [ 'C:\', 'User', 'Document', 'file.txt' ]

        buffer_type
            'file' : the buffer corresponds to a file (hopefully a text file) [read-write]
            'dir'  : the buffer corresponds to a directory [read-only]
            'disp' : the buffer corresponds to a display panel [read-only]

        Note:
          - any system-opened "file" buffer should has "None" as the ".path" property.
          - any system-opened "non-file" buffer should has "None" as the ".buffer" property.
        '''
        super(zEdit, self).__init__()


        if not zEdit.__last_line:
            zEdit.set_last_line(zLastLine())

        self.__on_init = True

        self.active_buffer = None
        self.sig_id = {}        # a dict holds all handler id

        self.ui_init_func = None
        self.need_init = None   # since no init_func is set at this time

        # layout of the frame:
        #
        #                   tabbar (can be turn off)
        #   +--+--+------+_/
        #   +--+--+------+_
        #   ||           | \
        #   ||           |  center_shell
        #   ||  center   |
        #   ||           |
        #   |+-----------|
        #   +--+---------+
        #   |sw| bottom  |
        #   +--+---------+

        # create tabbar if turned on
        self.tab_on_current = False
        if zEdit.__tab_on:
            self._sig_update_tabbar()

        # create the status bar
        self.bottom_bg = gtk.EventBox()
        self.pack_end(self.bottom_bg, False, False, 0)
        self.bottom = gtk.HBox()
        self.bottom_bg.add(self.bottom)

        # create buffer switcher
        self.buffer_sw = zComboBox()
        self.bottom.pack_start(self.buffer_sw, False, False, 0)

        self.buffer_sw.set_row_separator_func(self.__separator)

        # create the main window frame
        self.center_shell = None
        self.center = None
        self.set_buffer(buffer_path, buffer_type)

        # connect auto-update items
        zEdit.register('update_tabbar', self._sig_update_tabbar, self)

        zEditBuffer.register('buffer_removed', zEdit._sig_buffer_removed, self)
        zEditBuffer.register('buffer_list_modified', zEdit._sig_buffer_list_modified, self)
        zEdit._sig_buffer_list_modified(self)

        zTheme.register('update_font', self._sig_update_font, self.buffer_sw)
        self._sig_update_font()

        zTheme.register('update_color_map', self._sig_update_color_map, self)

        zComboBox.register('changed', self._sig_combo_changed, self.buffer_sw)


        self.__on_init = False


    ### signal-like auto-update function
    def _sig_update_tabbar(self, widget = None):
        if zEdit.__tab_on:
            # turn on the tabbar
            if not self.tab_on_current:
                # tabbar off
                self.tabbar = zTabbar()
                if not self.__on_init:
                    self.remove(self.center_shell)
                self.pack_start(self.tabbar, False, False, 0)
                if not self.__on_init:
                    self.pack_start(self.center_shell, True, True, 0)

                if self.__on_init:
                    self.tab_on_current = True
                    return      # rest will be done by the constructor

            # update buffer list
            zEdit._sig_buffer_list_modified(self, skip_sw = True)
            self.tabbar.show_all()

            # retain focus
            if zEdit._focus:
                zEdit._focus.grab_focus()
            else:
                self.grab_focus()

            self.tab_on_current = True

            # init focus theme
            if self.is_focus():
                self.update_theme_focus_in()
            else:
                self.update_theme_focus_out()
        else:
            # turn off the tabbar
            if self.tab_on_current:
                # tabbar on
                self.remove(self.tabbar)
                for tab in self.tabbar.get_tab_list():
                    zTabbar.unregister('changed', tab)

                self.tabbar.hide_all()
                self.tabbar = None

                # retain focus
                if zEdit._focus:
                    zEdit._focus.grab_focus()
                else:
                    self.grab_focus()

                self.tab_on_current = False


    @staticmethod
    def _sig_buffer_removed(z_editor, removed_buff_name):
        if z_editor.active_buffer.name == removed_buff_name:
            # the removed buffer is the current active one
            # find a substitude
            new_active_indx = z_editor.buffer_sw.index([removed_buff_name, False]) - 1
            if z_editor.buffer_sw.get_value(new_active_indx, 1) == True:
                # separator, search the other direction
                if len(zEditBuffer.buff_group['user']):
                    # has at least one other user buffer
                    new_active_indx += 2 # separater => +1 => current => +1 => next buffer
                else:
                    # no other user buffer
                    new_active_indx -= 1 # system buffer <= -1 <= separater

            # retrive the buffer info of the new active buffer
            new_active_name = z_editor.buffer_sw.get_value(new_active_indx, 0)
            new_active = zEditBuffer.buff_list[new_active_name]

            # switch to that buffer
            z_editor.set_buffer(new_active.path, new_active.type)

        # update the buffer list
        zEdit._sig_buffer_list_modified(z_editor)


    @staticmethod
    def _sig_buffer_list_modified(z_editor, new_buff = None, skip_sw = False):
        z_editor.__list_modified = True

        ### for tabbar
        if zEdit.__tab_on:
            if not new_buff or not z_editor.is_focus():
                new_buff = z_editor.active_buffer

            z_editor.rebuild_tabbar(new_buff)
            z_editor.update_buffer_list_selected(True, False)

            z_editor.tabbar.show_all()

        ### for buffer switcher
        if skip_sw:
            return              # early return

        # temporarily block combobox signals
        zComboBox.reg_block('changed')

        # clear the list
        z_editor.buffer_sw.clear()

        # add system-opened buffers
        for buff in zEditBuffer.buff_group['system']:
            z_editor.buffer_sw.append([buff, False])
        # add user-opened buffers, if exist
        if len(zEditBuffer.buff_group['user']):
            # add separator: Not an Item, this item should not be seen
            z_editor.buffer_sw.append(['NanI', True])
            # add user-opened buffers
            for buff in zEditBuffer.buff_group['user']:
                z_editor.buffer_sw.append([buff, False])

        # unblock combobox signals
        zComboBox.reg_unblock('changed')

        # set active
        z_editor.update_buffer_list_selected(False, True)

        z_editor.__list_modified = False


    def update_buffer_list_selected(self, mask_tab = True, mask_sw = True):
        ### for tabbar
        if mask_tab and self.__tab_on:
            if self.active_buffer.name not in self.tabbar.get_tab_label_list():
                self.rebuild_tabbar(self.active_buffer)

            self.tabbar.set_active(self.active_buffer.name)

        ### for switcher
        if mask_sw:
            self.buffer_sw.set_active([self.active_buffer.name, False])

    def _sig_update_font(self, widget = None):
        if self.tab_on_current:
            zTheme._sig_update_font_modify(self.tabbar, 0.75)
        zTheme._sig_update_font_modify(self.buffer_sw, 0.75)
        self.resize()

    def _sig_update_color_map(self, widget = None):
        if self.tab_on_current:
            self.tabbar.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['text']))
            self.tabbar.modify_fg(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['reserve']))

        self.center.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.center.modify_text(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.center.modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse(zTheme.color_map['text_selected']))

        self.center.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['base']))
        self.center.modify_base(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['base']))
        self.center.modify_base(gtk.STATE_SELECTED, gtk.gdk.color_parse(zTheme.color_map['base_selected']))

        self.buffer_sw.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.buffer_sw.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['status_active']))

        if self.is_focus():
            self.update_theme_focus_in()
        else:
            self.update_theme_focus_out()

    def update_theme_focus_in(self):
        if self.tab_on_current:
            self.tabbar.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['status_active']))
            self.tabbar.modify_bg(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['status_active']))
        self.bottom_bg.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['status_active']))

    def update_theme_focus_out(self):
        if self.tab_on_current:
            self.tabbar.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['status']))
            self.tabbar.modify_bg(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['status']))
        self.bottom_bg.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['status']))
    ### end of signal-like auto-update function


    ### top-level signal
    @staticmethod
    def _sig_kp_fo_rm(widget):
        '''see _sig_key_pressed() [below] for more information'''
        if ( zEdit.__command_widget_focus_id  and
             widget.handler_is_connected(zEdit.__command_widget_focus_id)
             ):
            widget.disconnect(zEdit.__command_widget_focus_id)
            zEdit.__command_widget_focus_id = None

    @staticmethod
    def _sig_key_pressed_focus_out(widget, event):
        '''see _sig_key_pressed() [below] for more information'''
        if ( zEdit.__command_widget_focus_id  and
             widget.handler_is_connected(zEdit.__command_widget_focus_id)
             ):
            # widget switched during Commanding
            # cancel it
            zEdit.__commanding = False
            zEdit.__command_content = ''
            widget.disconnect(zEdit.__command_widget_focus_id)
            zEdit.__command_widget_focus_id = None

            if zEdit.__mx_commanding:
                # on M-x Commanding
                # restore it
                zEdit.__last_line.blink_set('', 'Quit', 1, zEdit.__mx_command_prefix, zEdit.__mx_command_content)
            else:
                # no M-x commanding
                # reset lastline
                zEdit.__last_line.set_text('', 'Quit')


    @staticmethod
    def _sig_key_pressed(widget, event, data = None):
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

        key_binding = zEdit.__key_binding
        reg_func = zEdit._auto_update

        if zEdit.__style == 'emacs':
            # style::emacs

            # check C-q Escaping
            if not zEdit.__commanding and zEdit.__escaping:
                try:
                    if widget.get_editable():
                        if re.match(r'^[\x20-\x7e]$', stroke):
                            widget.insert_text(stroke, zEdit.__last_line)
                        elif stroke.upper() in zEdit.__ctrl_char_map:
                            widget.insert_text(zEdit.__ctrl_char_map[stroke.upper()], zEdit.__last_line)
                except:
                    pass
                zEdit.__escaping = False
                return True
            # no C-q Escaping

            # check C-g Cancelling
            if stroke == 'C-g': # at any time, this means 'cancel'
                zEdit.__commanding = False
                zEdit.__command_content = ''
                zEdit._sig_kp_fo_rm(widget)

                if ( zEdit.__mx_commanding  and                     # has M-x commanding, and
                     widget not in zEdit.__last_line.get_children() # focus not in lastline
                     ):
                    # must be commanding over M-x commanding
                    # restore M-x commanding
                    zEdit.__last_line.set_editable(True)
                    zEdit.__last_line.blink_set('', 'Quit', 1, zEdit.__mx_command_prefix, zEdit.__mx_command_content)
                else:
                    # no M-x commanding, or focus in lastline
                    # reset lastline
                    zEdit.mx_commanding_reset()

                    zEdit.__last_line.unlock()
                    zEdit.__last_line.set_editable(False)
                    zEdit.__last_line.set_text('', 'Quit')
                    if zEdit._focus:
                        zEdit._focus.grab_focus()
                return True
            # no C-g Cancelling

            # check M-x Commanding input
            if ( not zEdit.__commanding  and
                 zEdit.__mx_commanding   and
                 widget in zEdit.__last_line.get_children()
                 ):
                # on M-x Commanding, Commanding *MUST NOT* be initiated
                if re.match(r'^[\x20-\x7e]$', stroke):
                    # regular keypress
                    widget.insert_text(stroke, zEdit.__last_line)
                    zEdit.__mx_command_content = widget.get_text()
                    return True
                elif stroke.upper() == 'RETURN':
                    # Enter key pressed

                    # reset last line
                    zEdit.__last_line.reset() # this is to clear all bindings with the lastline

                    if zEdit.__mx_command_content in reg_func:
                        # is a valid functionality
                        if len(reg_func[zEdit.__mx_command_content]):
                            # has registered functions
                            zEdit._focus.grab_focus() # retain focus before emit the function
                            zEdit.reg_emit(zEdit.__mx_command_content)
                        else:
                            zEdit.__last_line.set_text(
                                '',
                                '(function `{0}` not implemented)'.format(zEdit.__mx_command_content)
                                )
                    else:
                        zEdit.__last_line.set_text(
                            '',
                            '({0}: no such function)'.format(zEdit.__mx_command_content)
                            )
                    zEdit.mx_commanding_reset()
                    if zEdit._focus:
                        zEdit._focus.grab_focus()
                    return True
            # no active M-x Commanding

            # check initiated Commanding
            if not zEdit.__commanding:
                # initiating stroke, check reserved bindings (M-x and C-q)
                if stroke == 'M-x':
                    if zEdit.__mx_commanding:
                        # already in M-x Commanding, warn it
                        zEdit.__last_line.blink('Warn: ', 'invalid key press!', 1)
                    else:
                        # initiate M-x Commanding
                        zEdit.__mx_commanding = True
                        zEdit.__last_line.set_text(zEdit.__mx_command_prefix, '')
                        zEdit.__last_line.set_editable(True)

                        zEdit.__last_line.connect('key-press-event', zEdit._sig_key_pressed)
                        zEdit.__last_line.lock(zEdit.mx_commanding_reset)
                    return True
                elif stroke == 'C-q':
                    # start C-q Escaping
                    zEdit.__escaping = True
                    return True
                # not reserved bindings

                # initiate Commanding
                if not zEdit.__mx_commanding:
                    zEdit.__last_line.clear()
                zEdit.__commanding = True
                zEdit.__command_widget_focus_id = widget.connect('focus-out-event', zEdit._sig_key_pressed_focus_out)
            # Commanding initiated

            # retrive previous combo, if there is any
            if zEdit.__command_content:
                # appand previous combo to stroke
                stroke = '{0} {1}'.format(zEdit.__command_content, stroke)

            # validate stroke sequence
            if ( stroke in key_binding  and       # is a binded key stroke
                 key_binding[stroke] in reg_func  # is a valid functionality
                 ):
                zEdit.__commanding = False
                zEdit.__command_content = ''
                zEdit._sig_kp_fo_rm(widget)
                zEdit.__last_line.clear()

                if len(reg_func[key_binding[stroke]]):
                    # has registered functions
                    zEdit.reg_emit(key_binding[stroke])
                else:
                    info = [ '', '(function `{0}` not implemented)'.format(key_binding[stroke]) ]

                    if zEdit.__mx_commanding:
                        # on M-x Commanding
                        # restore it after blink the msg
                        zEdit.__last_line.blink_set(
                            info[0], info[1], 1,
                            zEdit.__mx_command_prefix, zEdit.__mx_command_content
                            )
                    else:
                        # no M-x commanding
                        # print the msg
                        zEdit.__last_line.set_text(info[0], info[1])

                return True
            else:
                # not a valid stroke sequence so far
                found = False
                for key in key_binding:
                    if key.startswith(stroke):
                        # part of a valid stroke sequence
                        found = True
                        if not zEdit.__mx_commanding:
                            # display stroke if in echoing mode
                            zEdit.__last_line.set_text(stroke + ' ', None)
                        break

                if found:
                    zEdit.__command_content = stroke
                    return True
                else:
                    # not a valid stroke sequence *AT ALL*
                    zEdit.__commanding = False
                    zEdit._sig_kp_fo_rm(widget)

                    if not zEdit.__command_content:
                        # initiate stroke, pass it on
                        return False
                    else:
                        # has previous combo, eat the current combo
                        if zEdit.__mx_commanding:
                            # on M-x Commanding
                            # restore it
                            zEdit.__last_line.blink_set(
                                '', stroke + ' is undefined', 1,
                                zEdit.__mx_command_prefix, zEdit.__mx_command_content
                                )
                        else:
                            # no M-x commanding
                            # reset lastline
                            zEdit.__last_line.set_text('', stroke + ' is undefined')
                        zEdit.__command_content = ''
                        return True

        elif zEdit.__style == 'vi':
            # style::vi
            return False        # not implemetad yet

        else:
            # style::other
            if ( stroke in key_binding            and # is a binded key stroke
                 key_binding[stroke] in reg_func  and # is a valid functionality
                 len(reg_func[key_binding[stroke]])   # has registered functions
                 ):
                zEdit.reg_emit(key_binding[stroke])
                return True
            else:
                return False

        return False            # pass on any left-over (should not exist)
    ### end of top-level signal


    ### signal for center
    def _sig_button_press_browser(self, treeview, event, data = None):
        if event.button != 3:
            return

        # create the menu
        menu = gtk.Menu()

        # fill the menu
        try:
            ( tree_path, tree_col, dummy_x, dummy_y ) = treeview.get_path_at_pos(int(event.x), int(event.y))
        except:
            # not on a row; select the last row
            iterator = treeview.model.get_iter_first()
            while treeview.model.iter_next(iterator):
                iterator = treeview.model.iter_next(iterator)
            tree_path = treeview.model.get_path(iterator)
            tree_col = treeview.fn_tree_col
        treeview.set_cursor(tree_path)

        if tree_path is None:
            raise LookupError
        elif len(tree_path) > 0:
            iterator = treeview.model.get_iter(tree_path)
            filename = treeview.model.get_value(iterator, 0)
        else:
            raise ValueError

        mi_open = gtk.MenuItem('_Open')
        mi_new_file = gtk.MenuItem('_New File')
        mi_new_folder = gtk.MenuItem('New _Folder')
        mi_rename = gtk.MenuItem('_Rename')

        menu.append(mi_open)
        menu.append(mi_new_file)
        menu.append(mi_new_folder)
        menu.append(mi_rename)

        mi_open.connect_object('activate', self.center._sig_open_file_from_tree, treeview, tree_path)
        mi_new_file.connect_object('activate', self.center._sig_new_file, treeview, tree_path, 'file')
        mi_new_folder.connect_object('activate', self.center._sig_new_file, treeview, tree_path, 'dir')
        mi_rename.connect_object('activate', self.center._sig_rename_file, treeview, tree_path)

        # callback
        zEdit.reg_emit_from('populate_popup', self.center, menu)

        # popup the menu
        menu.popup(None, None, None, event.button, event.time)

    def _sig_button_press_textview(self, textview, menu):
        zEdit.reg_emit_from('populate_popup', self.center, menu)


    def _sig_focus_in(self, widget, event):
        zEdit._focus = self

        if len(zEdit._auto_update['buffer_focus_in']):
            zEdit.reg_emit('buffer_focus_in')
        self.update_theme_focus_in()

    def _sig_focus_out(self, widget, event):
        if len(zEdit._auto_update['buffer_focus_out']):
            zEdit.reg_emit('buffer_focus_out')
        self.update_theme_focus_out()

    def _sig_tab_clicked(self, tab):
        buffer_name = self.tabbar.get_label_of(tab)

        if buffer_name != self.active_buffer.name:
            buff = zEditBuffer.buff_list[buffer_name]
            self.set_buffer(buff.path, buff.type)

        # set focus
        if zEdit._focus:
            zEdit._focus.grab_focus()
        else:
            self.grab_focus()
    ### end of signal for center


    ### signal for bottom
    def _sig_combo_changed(self, combobox):
        # check for switcher items
        active_item = combobox.get_active()
        if not active_item:
            return              # early return

        # switch buffer
        buffer_name = active_item[0]

        if buffer_name != self.active_buffer.name:
            buff = zEditBuffer.buff_list[buffer_name]
            self.set_buffer(buff.path, buff.type)

        # set focus
        if zEdit._focus and self.__list_modified:
            zEdit._focus.grab_focus()
        else:
            self.grab_focus()
    ### end of signal for bottom


    ### overridden function definition
    @classmethod
    def reg_clean_up(cls):
        '''This function un-register all invisible widgets from the list'''
        for sig in cls._auto_update:
            reserve = []
            for item in cls._auto_update[sig]:
                try:
                    if item[0].get_property('visible'):
                        reserve.append(item)
                except:
                    reserve.append(item)
            cls._auto_update[sig] = reserve


    def connect(self, sig, callback, *data):
        if sig not in zEdit._auto_update:
            return self.center.connect(sig, callback, *data)

        zEdit.register(sig, callback, self.center, *data)
        return sig, self.center

    def disconnect(self, handler):
        if isinstance(handler, int):
            self.center.disconnect(handler)
        else:
            zEdit.unregister(handler, self.center)

    def handler_is_connected(self, handler):
        if isinstance(handler, int):
            return self.center.handler_is_connected(handler)
        else:
            return zEdit.reg_is_registered(sig, self.center)

    def handler_block(self, handler):
        if isinstance(handler, int):
            self.center.handler_block(handler)
        else:
            zEdit.reg_block(handler)

    def handler_unblock(self, handler):
        if isinstance(handler, int):
            self.center.handler_unblock(handler)
        else:
            zEdit.reg_unblock(handler)


    def is_focus(self):
        return self.center.is_focus()

    def grab_focus(self):
        self.center.grab_focus()

    def resize(self):
        self.buffer_sw.set_width_chars(zTheme.DISC['fn_len'])
    ### end of overridden function definition


    def rebuild_tabbar(self, target_buff):
        if not zEdit.__tab_on:
            return

        for tab in self.tabbar.get_tab_list():
            # clear the current tabbar
            self.tabbar.remove(tab)
            zTabbar.unregister('changed', tab)

        tab_label_list = []

        if ( target_buff.name in zEditBuffer.buff_group['system'] or
             not zEdit.__tab_grouped
             ):
            # add system-opened buffers
            tab_label_list.extend(zEditBuffer.buff_group['system'])
        if ( target_buff.name in zEditBuffer.buff_group['user'] or
             not zEdit.__tab_grouped
             ):
            # add user-opened buffers
            tab_label_list.extend(zEditBuffer.buff_group['user'])

        # add tabs to the tabbar
        for tab_label in tab_label_list:
            tab = self.tabbar.new_tab(tab_label)
            self.tabbar.append(tab)
            zTabbar.register('changed', self._sig_tab_clicked, tab)


    def exec_init_func(self):
        if self.need_init:
            self.ui_init_func(self)

    def exec_uninit_func(self):
        if self.ui_uninit_func:
            self.ui_uninit_func(self)

    def set_init_func(self, ui_init_func):
        self.ui_init_func = ui_init_func[0]
        self.ui_uninit_func = ui_init_func[1]
        if self.ui_init_func:
            self.need_init = True


    def get_buffer(self):
        return self.active_buffer.path, self.active_buffer.type

    def set_buffer(self, buffer_path, buffer_type):
        try:
            new_buff = zEditBuffer(buffer_path, buffer_type)
        except:
            zEditBuffer.restore()
            raise

        if new_buff == self.active_buffer:
            return              # no need to switch, early return

        if ( self.active_buffer == None or
             self.active_buffer.type != new_buff.type
             ):
            # widget need to be switched, mark for init unless no such func
            if self.need_init != None:
                self.need_init = True

            # create widget
            if new_buff.type == 'file':
                widget_shell = gtk.ScrolledWindow()
                widget_shell.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
                widget_shell.set_placement(gtk.CORNER_TOP_RIGHT)

                widget = zTextView(editor = self)
                widget_button_press_id = widget.center.connect('populate-popup', self._sig_button_press_textview)
                widget_key_press_id = {
                    widget : widget.connect('key-press-event', zEdit._sig_key_pressed),
                    }
            elif new_buff.type == 'dir':
                widget_shell = gtk.Frame()
                widget_shell.set_shadow_type(gtk.SHADOW_NONE)

                widget = zFileManager(editor = self)
                widget_button_press_id = widget.center.connect('button-press-event', self._sig_button_press_browser)
                widget_key_press_id = {
                    widget.path_entry : widget.path_entry.connect('key-press-event', zEdit._sig_key_pressed),
                    widget.treeview   : widget.treeview.connect('key-press-event', zEdit._sig_key_pressed),
                    }
            elif new_buff.type == 'disp':
                widget_shell = gtk.Frame()
                widget_shell.set_shadow_type(gtk.SHADOW_NONE)

                widget = zDisplayPanel(editor = self)
                widget_button_press_id = widget.center.connect('populate-popup', self._sig_button_press_textview)
                widget_key_press_id = {
                    widget.job_panel  : widget.job_panel.connect('key-press-event', zEdit._sig_key_pressed),
                    widget.step_panel : widget.step_panel.connect('key-press-event', zEdit._sig_key_pressed),
                    widget.center     : widget.center.connect('key-press-event', zEdit._sig_key_pressed),
                    }
            else:
                raise KeyError

            # switch widget
            if self.center:
                self.center.center.disconnect(self.sig_id['button_press'])
                self.exec_uninit_func()                

                zTheme.unregister('update_font', self.center)
                self.center.disconnect(self.sig_id['focus_in'])
                self.center.disconnect(self.sig_id['focus_out'])
                for (k, v) in self.sig_id['key_press'].iteritems():
                    k.disconnect(v)

                self.center_shell.remove(self.center)
                self.remove(self.center_shell)
            self.center_shell = widget_shell
            self.center = widget
            self.center_shell.add(self.center)
            self.pack_start(self.center_shell, True, True, 0)

            zTheme.register('update_font', zTheme._sig_update_font_modify, self.center)
            self.sig_id['focus_in'] = self.center.connect('focus-in-event', self._sig_focus_in)
            self.sig_id['focus_out'] = self.center.connect('focus-out-event', self._sig_focus_out)
            self.sig_id['key_press'] = widget_key_press_id
            self.sig_id['button_press'] = widget_button_press_id

            zTheme._sig_update_font_modify(self.center)
            self._sig_update_color_map()

        # switch buffer
        self.active_buffer = new_buff
        self.update_buffer_list_selected(True, True)

        # connect buffer
        if self.active_buffer.type == 'file':
            self.center.set_buffer(new_buff.buffer)
        elif self.active_buffer.type == 'dir':
            if self.active_buffer.path and io_encap.is_dir(self.active_buffer.path):
                self.center.set_folder(os.path.join(* self.active_buffer.path))

        if self.need_init:
            self.exec_init_func()
        self.show_all()


    def save_buffer(self, buff):
        return self.center.buffer_save(buff)

    def save_buffer_as(self, buff):
        return self.center.buffer_save_as(buff)

    def rm_buffer(self, buff, force = False):
        return zEditBuffer.rm_buffer(buff, force)


    @staticmethod
    def get_key_binding():
        return zEdit.__key_binding

    @staticmethod
    def set_key_binding(dic):
        zEdit.__key_binding = copy.deepcopy(dic)

    @staticmethod
    def get_last_line():
        return zEdit.__last_line

    @staticmethod
    def set_last_line(lastline):
        if zEdit.__last_line != lastline:
            if zEdit.__last_line:
                zEdit.__last_line.reset()
            zEdit.__last_line = lastline

    @staticmethod
    def get_style():
        return zEdit.__style

    @staticmethod
    def set_style(style):
        zEdit.__style = style

    @staticmethod
    def get_tab_on():
        return zEdit.__tab_on

    @staticmethod
    def set_tab_on(setting):
        if zEdit.__tab_on != setting:
            zEdit.__tab_on = setting
            zEdit.reg_emit('update_tabbar')

    @staticmethod
    def get_tab_grouped():
        return zEdit.__tab_grouped

    @staticmethod
    def set_tab_grouped(setting):
        if zEdit.__tab_grouped != setting:
            zEdit.__tab_grouped = setting
            zEdit.reg_emit('update_tabbar')


    ### supporting function
    def __separator(self, item):
        return item[1]
    ### end of supporting function


######## ######## ######## ######## ########
########        zEditBuffer         ########
######## ######## ######## ######## ########

class zEditBuffer(z_ABC):
    '''The Centralized Buffer Allocator and Controller that Supports zEdit Class'''
    DEFAULT_BUFFER = {
        None   : '*scratch*',
        'file' : '*scratch*',
        'dir'  : '*browser*',
        'disp' : '*S D S F*',
        }
    SYSTEM_BUFFER = {
        '*scratch*' : 'file',
        '*browser*' : 'dir',
        '*S D S F*' : 'disp',
        }
    buff_list = {
        # 'buff_user'    : zEditBuffer()
        # 'buff_sys'     : zEditBuffer()
        # 'buff_user(1)' : zEditBuffer()
        # 'buff_another' : zEditBuffer()
        # 'buff_user(2)' : zEditBuffer()
        #  ...
        }
    buff_group = {              # group::user should only contain type::file
        'system' : [], # [ 'buff_sys', ]
        'user'   : [], # [ 'buff_user', 'buff_user(1)', 'buff_another', 'buff_user(2)', ]
        }
    buff_rec = { # no-removal record
        # 'buff_sys'     : [ ( 'buff_sys',     None,              opened ),
        #                    ],
        # 'buff_user'    : [ ( 'buff_user',    buff_user_0_path,  opened ),
        #                    ( 'buff_user(1)', buff_user_1_path,  opened ),
        #                    ( 'buff_user(2)', buff_user_2_path,  opened ),
        #                    ],
        # 'buff_another' : [ ( 'buff_another', buff_another_path, opened ),
        #                    ],
        #  ...
        }

    _auto_update = {
        # 'signal_like_string'  : [ (widget, callback, data_list), ... ]
        'buffer_list_modified'    : [  ],
        'buffer_removed'          : [  ],
        }

    _on_restore = False

    def __new__(cls, buffer_path = None, buffer_type = None):
        self = object.__new__(cls)

        zEditBuffer.backup()

        if buffer_path == None:
            # no path => system-opened buffer
            buffer_path = zEditBuffer.DEFAULT_BUFFER[buffer_type]
            buffer_type = zEditBuffer.SYSTEM_BUFFER[buffer_path]

        # init buffer properties
        if isinstance(buffer_path, str):
            # path not a list, check for name
            if ( buffer_path in zEditBuffer.SYSTEM_BUFFER and
                 buffer_type == zEditBuffer.SYSTEM_BUFFER[buffer_path]
                 ):
                # both name and type match => system-opened buffer
                buff_group = 'system'
                self.name = buffer_path
                self.path = None # path is "buffer.name", no information for "buffer.path"
                self.type = buffer_type
            else:
                # not system-opened buffer => error
                raise ValueError
        elif buffer_type in [ None, 'file' ]:
            # file with a path => user-opened buffer
            buff_group = 'user'
            self.name = buffer_path[-1]
            self.path = os.path.split( # normalize path
                os.path.abspath(os.path.expanduser(
                        os.path.join(* buffer_path)
                        ))
                )
            self.type = 'file'  # must be type::file
        else:
            # not type::file, must be system-opened buffer
            buff_group = 'system'
            self.name = zEditBuffer.DEFAULT_BUFFER[buffer_type]
            self.path = buffer_path # not type::file, no limitation on "buffer.path" property
            self.type = buffer_type

        # update buffer list
        if self.type == 'file':
            # only record type::file for user-opened buffer
            no_rec = True           # assume first encounter of the name
            rec_name = self.name    # this is used as the key of zEditBuffer.buff_rec
            if self.name in zEditBuffer.buff_rec:
                # name is recorded, check for duplication
                for (name, path, opened) in zEditBuffer.buff_rec[self.name]:
                    if path == self.path:
                        # same path ==> has record
                        no_rec = False

                        if opened:
                            # return old file reference
                            return zEditBuffer.buff_list[name] # early return
                        else:
                            # re-open it
                            self.name = name
                            # mark the buffer "opened"
                            rec_list = zEditBuffer.buff_rec[rec_name]
                            for indx in range(len(rec_list)):
                                if rec_list[indx][0] == self.name:
                                    rec_list[indx] = rec_list[indx][:-1] + (True,)
                                    break
                            break
                if no_rec:
                    # no duplication, generate new name of the new file
                    self.name += '({0})'.format(len(zEditBuffer.buff_rec[self.name]))

            if no_rec:
                # name not in record, add it
                if rec_name not in zEditBuffer.buff_rec:
                    zEditBuffer.buff_rec[rec_name] = [  ]
                zEditBuffer.buff_rec[rec_name].append( (self.name, self.path, True) )
            zEditBuffer.buff_list[self.name] = self

            zEditBuffer.buff_group[buff_group].append(self.name)

        elif buff_group == 'system':
            # system-opened non-type::file buffer
            if self.name in zEditBuffer.buff_rec:
                # name is recorded, update it
                zEditBuffer.buff_list[self.name].path = self.path
                return zEditBuffer.buff_list[self.name] # early return

            # name not in record, add it
            zEditBuffer.buff_rec[self.name] = [ (self.name, None, None) ]
            zEditBuffer.buff_list[self.name] = self

            zEditBuffer.buff_group[buff_group].append(self.name)
        else:
            raise SystemError   # this should never happen
        zEditBuffer.reg_emit('buffer_list_modified', self)

        # fetch content
        self.modified = None
        if self.type == 'file':
            self.buffer = gtk.TextBuffer()

            if self.name == '*scratch*':
                # tmp buffer
                zEditBuffer._reset_scratch()
            elif io_encap.is_file(self.path):
                # existing file
                if io_encap.is_binary(self.path):
                    raise TypeError('Cannot open a binary file.')
                if not io_encap.fetch(self):
                    raise BufferError('Failed to fetch the content.')
            else:
                # new file
                pass            # passive alloc (copy on write)
            self.set_modified(False)

            # connect internal signals
            self.buffer.connect('changed', self._sig_buffer_changed)

        elif buffer_type in [ 'dir', 'disp' ]:
            self.buffer = None
            self.set_modified(None)
        else:
            raise TypeError

        return self


    ### internal signal definition
    def _sig_buffer_changed(self, textbuff):
        self.set_modified(True)
    ### end of internal signal definition


    def set_modified(self, setting):
        if setting != self.modified:
            self.modified = setting
            # mark, emit signel here
            # remember to check `None`


    @staticmethod
    def backup():
        while zEditBuffer._on_restore:
            gtk.main_iteration(False)

        zEditBuffer.__buff_list  = copy.copy(zEditBuffer.buff_list) # never deepcopy this
        zEditBuffer.__buff_group = copy.deepcopy(zEditBuffer.buff_group)
        zEditBuffer.__buff_rec   = copy.deepcopy(zEditBuffer.buff_rec)


    @staticmethod
    def restore():
        zEditBuffer._on_restore = True

        zEditBuffer.buff_list  = copy.copy(zEditBuffer.__buff_list) # never deepcopy this
        zEditBuffer.buff_group = copy.deepcopy(zEditBuffer.__buff_group)
        zEditBuffer.buff_rec   = copy.deepcopy(zEditBuffer.__buff_rec)

        zEditBuffer.reg_emit('buffer_list_modified')

        zEditBuffer._on_restore = False


    def flush(self):
        if self.path:
            full_path = os.path.join(* self.path)
            if not self.modified:
                return full_path, '(No changes need to be saved.)'
            elif io_encap.flush(self):
                self.set_modified(False)
                return full_path, 'buffer saved.'
            else:
                return full_path, '(Cannot save the buffer! Permission denied!)'
        else:
            if not self.modified:
                return self.name, '(No changes need to be saved.)'
            else:
                raise ValueError('Cannot find the path! Use flush_to(path) instead.')

    def flush_to(self, path):
        if self.path and os.path.samefile(os.path.join(* self.path), os.path.join(* path)):
            return self.flush()

        if self.name in zEditBuffer.buff_group['system']:
            # system-opened buffer, cannot be renamed

            # create a new buffer
            new_buff = zEditBuffer(path, 'file')
            if new_buff in zEditBuffer.buff_list.itervalues():
                # buffer already opened, refuse renaming
                return path[-1], '(Cannot write to an existing buffer!)'

            

        print self.name, self.type, self.path, path


    @staticmethod
    def rm_buffer(buff, force):
        if buff.name in zEditBuffer.buff_group['system']:
            # system-opened buffer, cannot be closed
            if buff.name == '*scratch*':
                # close the scratch means to reset its content
                zEditBuffer._reset_scratch()
                return buff.name, 'buffer cleared'
            return buff.name, 'cannot close system buffer'
        elif buff.modified and not force:
            # buffer content modified but not a force removal
            raise ValueError('Buffer content has been modified!')
        else:
            # remove the buffer from all records
            del zEditBuffer.buff_list[buff.name]
            zEditBuffer.buff_group['user'].remove(buff.name)

            # mark the buffer "closed"
            rec_list = zEditBuffer.buff_rec[buff.path[-1]]
            for indx in range(len(rec_list)):
                if rec_list[indx][0] == buff.name:
                    rec_list[indx] = rec_list[indx][:-1] + (False,)
                    break

            # notify all registered editors
            zEditBuffer.reg_emit('buffer_removed', buff.name)
            return os.path.join(* buff.path), 'buffer closed'

    @staticmethod
    def _reset_scratch():
        zEditBuffer.buff_list['*scratch*'].buffer.set_text(
'''//*
//* This buffer is for notes you don't want to save.
//* If you want to create a file, do that with
//*   {0}
//* or save this buffer explicitly.
//*
'''.format('"Open a New Buffer" -> Right Click -> "New File"')
)
