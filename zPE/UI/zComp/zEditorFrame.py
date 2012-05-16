# this is the editor-frame module of the zComponent package

import io_encap
# this module requires io_encap to have the following APIs:
#
#   is_binary(fn_list):         test if the fn_list corresponding to a binary file
#
#   is_file(fn_list):           test if the fn_list corresponding to a file
#   is_dir(fn_list):            test if the fn_list corresponding to a directory
#
#   norm_path_list(fn_list):    return the normalized absolute path
#
#   fetch(buff):                read content from the corresponding file to the zEditBuffer
#   flush(buff):                write content from the zEditBuffer to the corresponding file
#

from zBase import z_ABC, zTheme
from zFileManager import zDisplayPanel, zFileManager
from zStrokeParser import zStrokeListener
from zSyntaxParser import zSyntaxParser
from zText import zLastLine, zTextView, zUndoStack, zBufferChange
from zWidget import zToolButton, zComboBox, zTabbar

import majormode

import os, copy, re
import pygtk
pygtk.require('2.0')
import gtk


######## ######## ######## ######## ########
########           zEdit            ########
######## ######## ######## ######## ########

class zEdit(z_ABC, gtk.VBox):
    '''A Multi-Buffer Text Editor with an Internal File Browser'''
    global_func_list = [
        'buffer-open',
        'buffer-save',
        'buffer-save-as',
        'buffer-close',

        'buffer-undo',
        'buffer-redo',

        'caps-on',
        'caps-off',

        'tabbar-mode',
        'tabbar-prev',
        'tabbar-next',
        ]
    # only make the following function bindable, no actual binding applied
    zStrokeListener.global_add_func_registry(global_func_list)

    func_callback_map = {}      # if set, will override the default setting for all newly added/switched instance

    __tab_on = False            # see zEdit.set_tab_on()
    __tab_grouped = False       # see zEdit.set_tab_grouped()

    __last_line = None          # see zEdit.set_last_line()

    focused_widget = None       # records the current focus (set by focus-in-event signal)

    _auto_update = {
        # 'signal_like_string'  : [ (widget, callback, data_list), ... ]
        'buffer_focus_in'       : [  ],
        'buffer_focus_out'      : [  ],

        'populate_popup'        : [  ],

        'update_tabbar'         : [  ],
        'tabbar_mode_toggled'   : [  ],
        }

    def __init__(self, buffer_path = None, buffer_type = None, local_func_binding_generator = None):
        '''
        buffer_path = None
            a list of nodes representing the path of the file/buffer
            the editor is suppose to open.

            examples:
               OS    |          file             |             buffer_path
            ---------+---------------------------+-------------------------------------------
              Linux  | /home/user/doc/file       | [ '/', 'home', 'user', 'doc', 'file'    ]
             Windows | C:\User\Document\file.txt | [ 'C:\', 'User', 'Document', 'file.txt' ]

        buffer_type = None
            'file' : the buffer corresponds to a file (hopefully a text file) [read-write]
            'dir'  : the buffer corresponds to a directory [read-only]
            'disp' : the buffer corresponds to a display panel [read-only]

        local_func_binding_generator = None
            a generator that take an zEdit instance as argument and return a func_callback_map
            binded to that instance. If None, no binding is applied.

        Note:
          - any system-opened "savable" buffer should has "None" as the ".path" property.
          - any system-opened "non-savable" buffer should has "None" as the ".buffer" property.
        '''
        super(zEdit, self).__init__()


        if not zEdit.__last_line:
            zEdit.set_last_line(zLastLine())

        self.__on_init = True

        self.active_buffer = None
        self.sig_id = {}        # a dict holds all handler id

        self.ui_init_func = None
        self.need_init = None   # since no init_func is set at this time

        self.default_func_callback = {
            # although works in most cases, ugly behavior.
            # rebind (overrid) them by setting zEdit.func_callback_map beforehand
            'buffer-open'    : lambda msg: self.set_buffer(None, 'dir'),
            'buffer-save'    : lambda msg: self.save_buffer(None),
            'buffer-save-as' : lambda msg: self.save_buffer_as(None),
            'buffer-close'   : lambda msg: self.rm_buffer(None),

            'buffer-undo'    : lambda msg: self.undo(),
            'buffer-redo'    : lambda msg: self.redo(),

            'caps-on'        : lambda msg: self.active_buffer.set_caps_on(True),
            'caps-off'       : lambda msg: self.active_buffer.set_caps_on(False),

            'tabbar-mode'    : lambda msg: zEdit.toggle_tabbar_mode(),
            'tabbar-prev'    : lambda msg: self.switch_tab_to('prev'),
            'tabbar-next'    : lambda msg: self.switch_tab_to('next'),
            }

        if zEdit.func_callback_map:
            for (k, v) in zEdit.func_callback_map.iteritems():
                if k in zEdit.global_func_list:
                    self.default_func_callback[k] = v

        if local_func_binding_generator:
            self.default_func_callback.update(local_func_binding_generator(self))


        # layout of the frame:
        #
        #                          tabbar (can be turn off)
        #   +--+--+--+----------+_/
        #   +--+--+--+----------+_
        #   ||                  | \
        #   ||                  |  center_shell
        #   ||      center      |
        #   ||                  |
        #   |+------------------|
        #   +-+-+--+--+-+-------+
        #   |w|m|sw|md|c|       |
        #   +-+-+--+--+-+-------+
        #    | | |  |  |
        #    | | |  |  +- buffer caps on / off flag
        #    | | |  +- buffer editing mode switcher
        #    | | +- buffer switcher
        #    | +- buffer modified flag
        #    +- buffer writeable flag

        # create tabbar if turned on
        self.tab_on_current = False
        if zEdit.__tab_on:
            self._sig_update_tabbar()

        # create the status bar
        self.bottom_bg = gtk.EventBox()
        self.pack_end(self.bottom_bg, False, False, 0)
        self.bottom = gtk.HBox()
        self.bottom_bg.add(self.bottom)

        # create flag buttons
        self.buffer_w = zToolButton('W')
        self.buffer_m = zToolButton('M')

        self.buffer_w.set_width_chars(1)
        self.buffer_m.set_width_chars(1)

        self.buffer_w.set_tooltip_markup("<tt>'-': writable\n'%': read-only</tt>")
        self.buffer_m.set_tooltip_markup("<tt>'-': not modified\n'*': modified</tt>")

        self.buffer_w.connect('clicked', self._sig_cycle_writable)
        self.buffer_m.connect('clicked', self._sig_cycle_modified)

        self.bottom.pack_start(self.buffer_w, False, False, 0)
        self.bottom.pack_start(self.buffer_m, False, False, 0)

        # create buffer switcher
        self.buffer_sw = zComboBox()
        self.bottom.pack_start(self.buffer_sw, False, False, 10)

        self.buffer_sw.set_row_separator_func(self.__separator)

        # create editing-mode switcher
        self.buffer_md = zComboBox()
        self.bottom.pack_start(self.buffer_md, False, False, 0)

        self.buffer_md.set_row_separator_func(self.__separator)
        for key in sorted(majormode.MODE_MAP.iterkeys()):
            self.buffer_md.append(['{0:<12}'.format(key), False, key])

        # create caps-on flag button
        self.buffer_c = zToolButton('C')
        self.buffer_c.set_width_chars(8)
        self.buffer_c.set_tooltip_markup('<tt>this has nothing to do with "Caps Lock" key</tt>')
        self.bottom.pack_start(self.buffer_c, False, False, 0)

        self.buffer_c.connect('clicked', self._sig_buffer_caps_toggled)

        # create the main window frame
        self.center_shell = None
        self.center = None
        self.set_buffer(buffer_path, buffer_type)

        # connect auto-update items
        zEdit.register('update_tabbar', self._sig_update_tabbar, self)

        zEditBuffer.register('buffer_modified_set', self._sig_buffer_modified_set, None)
        zEditBuffer.register('buffer_removed',      self._sig_buffer_removed,      None)

        zEditBuffer.register('buffer_mode_set',     self._sig_buffer_mode_set,     None)
        zEditBuffer.register('buffer_caps_set',     self._sig_buffer_caps_set,     None)

        zEditBuffer.register('buffer_list_modified', zEdit._sig_buffer_list_modified, self)
        zEdit._sig_buffer_list_modified(self)

        zTheme.register('update_font', self._sig_update_font, self)
        self._sig_update_font()

        zTheme.register('update_color_map', self._sig_update_color_map, self)

        zComboBox.register('changed', self._sig_combo_changed, self.buffer_sw)
        zComboBox.register('changed', self._sig_mode_changed,  self.buffer_md)


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
            if zEdit.focused_widget:
                zEdit.focused_widget.grab_focus()
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
                if zEdit.focused_widget:
                    zEdit.focused_widget.grab_focus()
                else:
                    self.grab_focus()

                self.tab_on_current = False


    def _sig_buffer_removed(self, widget, removed_buff_name):
        if self.active_buffer.name == removed_buff_name:
            # the removed buffer is the current active one
            # find a substitude
            new_active_indx = self.buffer_sw.index([removed_buff_name, False]) - 1
            if self.buffer_sw.get_value(new_active_indx, 1) == True:
                # separator, search the other direction
                if len(zEditBuffer.buff_group['user']):
                    # has at least one other user buffer
                    new_active_indx += 2 # separater => +1 => current => +1 => next buffer
                else:
                    # no other user buffer
                    new_active_indx -= 1 # system buffer <= -1 <= separater

            # retrieve the buffer info of the new active buffer
            new_active_name = self.buffer_sw.get_value(new_active_indx, 0)
            new_active = zEditBuffer.buff_list[new_active_name]

            # switch to that buffer
            self.set_buffer(new_active.path, new_active.type)

        # update the buffer list
        zEdit._sig_buffer_list_modified(self)


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
        zTheme._sig_update_font_modify(self.buffer_w,  0.85)
        zTheme._sig_update_font_modify(self.buffer_m,  0.85)
        zTheme._sig_update_font_modify(self.buffer_sw, 0.85)
        zTheme._sig_update_font_modify(self.buffer_md, 0.85)
        zTheme._sig_update_font_modify(self.buffer_c,  0.85)
        self.resize()

    def _sig_update_color_map(self, widget = None):
        # tabbar
        if self.tab_on_current:
            self.tabbar.modify_fg(gtk.STATE_NORMAL,   gtk.gdk.color_parse(zTheme.color_map['text']))
            self.tabbar.modify_fg(gtk.STATE_ACTIVE,   gtk.gdk.color_parse(zTheme.color_map['reserve']))

            self.tabbar.modify_fg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(zTheme.color_map['text']))
            self.tabbar.modify_bg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(zTheme.color_map['base_selected']))

        # center
        self.center.modify_text(gtk.STATE_NORMAL,   gtk.gdk.color_parse(zTheme.color_map['text']))
        self.center.modify_text(gtk.STATE_ACTIVE,   gtk.gdk.color_parse(zTheme.color_map['text_selected']))
        self.center.modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse(zTheme.color_map['text_selected']))

        self.center.modify_base(gtk.STATE_NORMAL,   gtk.gdk.color_parse(zTheme.color_map['base']))
        self.center.modify_base(gtk.STATE_ACTIVE,   gtk.gdk.color_parse(zTheme.color_map['base_selected']))
        self.center.modify_base(gtk.STATE_SELECTED, gtk.gdk.color_parse(zTheme.color_map['base_selected']))

        if self.active_buffer.type == 'file':
            for key in zTheme.color_map_fg_hilite_key:
                self.center.modify_fg_hilite(key, hilite = False)
            for key in zTheme.color_map_bg_hilite_key:
                self.center.modify_bg_hilite(key, hilite = False)
            self.center.hilite()

        # bottom
        self.buffer_w.modify_fg(gtk.STATE_NORMAL,   gtk.gdk.color_parse(zTheme.color_map['text']))
        self.buffer_w.modify_fg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.buffer_w.modify_bg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(zTheme.color_map['base_selected']))

        self.buffer_m.modify_fg(gtk.STATE_NORMAL,   gtk.gdk.color_parse(zTheme.color_map['text']))
        self.buffer_m.modify_fg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.buffer_m.modify_bg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(zTheme.color_map['base_selected']))

        self.buffer_sw.modify_fg(gtk.STATE_NORMAL,   gtk.gdk.color_parse(zTheme.color_map['text']))
        self.buffer_sw.modify_fg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.buffer_sw.modify_bg(gtk.STATE_NORMAL,   gtk.gdk.color_parse(zTheme.color_map['base']))          # for menu
        self.buffer_sw.modify_bg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(zTheme.color_map['base_selected'])) # for combo

        self.buffer_md.modify_fg(gtk.STATE_NORMAL,   gtk.gdk.color_parse(zTheme.color_map['text']))
        self.buffer_md.modify_fg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.buffer_md.modify_bg(gtk.STATE_NORMAL,   gtk.gdk.color_parse(zTheme.color_map['base']))          # for menu
        self.buffer_md.modify_bg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(zTheme.color_map['base_selected'])) # for combo

        self.buffer_c.modify_fg(gtk.STATE_NORMAL,   gtk.gdk.color_parse(zTheme.color_map['text']))
        self.buffer_c.modify_fg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.buffer_c.modify_bg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(zTheme.color_map['base_selected']))

        # focus relevant
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
        zEdit.reg_emit_to('populate_popup', self.center, menu)

        # popup the menu
        menu.popup(None, None, None, event.button, event.time)

    def _sig_button_press_textview(self, textview, menu):
        zEdit.reg_emit_to('populate_popup', self.center, menu)


    def _sig_focus_in(self, widget, event):
        zEdit.focused_widget = self

        if len(zEdit._auto_update['buffer_focus_in']):
            zEdit.reg_emit('buffer_focus_in')
        self.update_theme_focus_in()
        self._sig_buffer_modified_set()
        self._sig_buffer_mode_set()
        self._sig_buffer_caps_set()

    def _sig_focus_out(self, widget, event):
        if len(zEdit._auto_update['buffer_focus_out']):
            zEdit.reg_emit('buffer_focus_out')
        self.update_theme_focus_out()


    def _sig_listener_active(self, listener, msg, sig_type):
        if 'z_run_cmd' in msg:
            # M-x initiated
            zEdit.__last_line.start_mx_commanding(msg['z_run_cmd'])
            return

        widget = msg['widget']

        if sig_type == 'cancel':
            # on cancelling, clean up if needed
            try:
                widget.cancel_action()
            except:
                pass

            if msg['style'] == 'emacs':
                if ( zEdit.__last_line.is_mx_commanding()  and      # on M-x commanding, and
                     widget not in zEdit.__last_line.get_children() # focus not in lastline
                     ):
                    # must be commanding over M-x commanding
                    # restore M-x commanding
                    zEdit.__last_line.set_editable(True)
                    zEdit.__last_line.blink('', msg['return_msg'], 0.5)

                elif zEdit.__last_line.is_mx_commanding():
                    # focus in lastline (M-x commanding cancelled)
                    # reset lastline and retain focus
                    zEdit.__last_line.stop_mx_commanding()
                    zEdit.__last_line.set_text('', msg['return_msg'])

                    if zEdit.focused_widget:
                        zEdit.focused_widget.grab_focus()
                else:
                    # no M-x commanding, or focus in lastline (M-x commanding cancelled)
                    # reset lastline
                    zEdit.__last_line.set_text('', msg['return_msg'])


            elif msg['style'] == 'vi':
                pass            # not implemented yet

            else:
                pass
        else:
            # on activating, perform additional action if needed

            if msg['style'] == 'emacs':
                if widget in zEdit.__last_line.get_children(): # lastline activated, reset it
                    # reset last line
                    zEdit.__last_line.reset() # this is to clear all bindings with the lastline

                    # retain focus
                    if zEdit.focused_widget:
                        zEdit.focused_widget.grab_focus()

                if not zEdit.__last_line.is_mx_commanding():
                    if msg['return_msg'] == '':
                        zEdit.__last_line.set_text('', '')
                    elif msg['return_msg'] == 'z_combo':
                        zEdit.__last_line.set_text(msg['stroke'], '')

            elif msg['style'] == 'vi':
                pass            # not implemented yet

            else:
                pass


    def _sig_tab_clicked(self, tab):
        buffer_name = self.tabbar.get_label_of(tab)

        if buffer_name != self.active_buffer.name:
            buff = zEditBuffer.buff_list[buffer_name]
            self.set_buffer(buff.path, buff.type)

        # set focus
        if zEdit.focused_widget:
            zEdit.focused_widget.grab_focus()
        else:
            self.grab_focus()
    ### end of signal for center


    ### signal for bottom
    def _sig_cycle_writable(self, bttn):
        buff = self.active_buffer
        if buff.editable == None:
            return              # this means not allow to toggle
        buff.editable = not buff.editable
        self._sig_buffer_modified_set()

    def _sig_cycle_modified(self, bttn):
        buff = self.active_buffer
        if buff.modified:
            self.save_buffer(buff)
        else:
            buff.set_modified(True)


    def _sig_buffer_modified_set(self, widget = None):
        buff = self.active_buffer

        self.center.set_editable(buff.editable)
        if buff.editable:
            if buff.modified:
                self.buffer_w.set_label('*')
                self.buffer_m.set_label('*')
            else:
                self.buffer_w.set_label('-')
                self.buffer_m.set_label('-')
        else:
            # not writable
            self.buffer_w.set_label('%')
            if buff.modified:
                self.buffer_m.set_label('*')
            else:
                self.buffer_m.set_label('%')


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
        if zEdit.focused_widget and self.__list_modified:
            zEdit.focused_widget.grab_focus()
        else:
            self.grab_focus()


    def _sig_mode_changed(self, combobox):
        # check for switcher items
        active_item = combobox.get_active()
        if not active_item:
            return              # early return

        # get buffer info
        buff = self.active_buffer

        if active_item[2] != buff.major_mode:
            buff.switch_mode(active_item[2])

        # set focus
        if zEdit.focused_widget and self.__list_modified:
            zEdit.focused_widget.grab_focus()
        else:
            self.grab_focus()

    def _sig_buffer_mode_set(self, widget = None):
        # get current active item
        active_item = self.buffer_md.get_active()

        # get buffer info
        buff = self.active_buffer

        if not active_item  or  active_item[2] != buff.major_mode:
            self.buffer_md.set_active(['{0:<12}'.format(buff.major_mode), False, buff.major_mode])

        if buff.type == 'file':
            self.center.hilite()


    def _sig_buffer_caps_toggled(self, bttn):
        self.active_buffer.toggle_caps_on()

    def _sig_buffer_caps_set(self, widget = None):
        self.buffer_c.set_label([ 'Caps Off', 'Caps On ' ][self.caps_on()])
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
        if self.ui_init_func:
            self.ui_init_func(self)

    def exec_uninit_func(self):
        if self.ui_uninit_func:
            self.ui_uninit_func(self)

    def set_init_func(self, ui_init_func):
        self.ui_init_func = ui_init_func[0]
        self.ui_uninit_func = ui_init_func[1]


    def get_ast(self):
        return { 'syntax_tree' : self.active_buffer.ast, 'major_mode' : self.active_buffer.major_mode, }


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
            if self.ui_init_func:
                self.need_init = True

            # create widget
            if new_buff.type == 'file':
                widget_shell = gtk.ScrolledWindow()
                widget_shell.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
                widget_shell.set_placement(gtk.CORNER_TOP_RIGHT)

                widget = zTextView(editor = self)
                widget.listen_on_task('text')

                widget_button_press_id = widget.center.connect('populate-popup', self._sig_button_press_textview)

            elif new_buff.type == 'dir':
                widget_shell = gtk.Frame()
                widget_shell.set_shadow_type(gtk.SHADOW_NONE)

                widget = zFileManager(editor = self)
                widget.listener = zStrokeListener()
                widget.listener.listen_on(widget.treeview)
                widget.listener.listen_on(widget.path_entry)
                widget.treeview.listener   = widget.listener
                widget.path_entry.listener = widget.listener

                widget_button_press_id = widget.center.connect('button-press-event', self._sig_button_press_browser)

            elif new_buff.type == 'disp':
                widget_shell = gtk.Frame()
                widget_shell.set_shadow_type(gtk.SHADOW_NONE)

                widget = zDisplayPanel(editor = self)
                widget.listener = zStrokeListener()
                widget.listener.listen_on(widget.job_panel)
                widget.listener.listen_on(widget.step_panel)
                widget.listener.listen_on(widget.center)
                widget.job_panel.listener  = widget.listener
                widget.step_panel.listener = widget.listener
                widget.center.listener     = widget.listener

                widget_button_press_id = widget.center.connect('populate-popup', self._sig_button_press_textview)
            else:
                raise KeyError

            # switch widget
            if self.center:
                self.center.center.disconnect(self.sig_id['button_press'])
                self.center.listener.clear_all()
                for handler in self.center.listener_sig:
                    if self.center.listener.handler_is_connected(handler):
                        self.center.listener.disconnect(handler)

                self.exec_uninit_func()

                zTheme.unregister('update_font', self.center)
                self.center.disconnect(self.sig_id['focus_in'])
                self.center.disconnect(self.sig_id['focus_out'])

                self.center_shell.remove(self.center)
                self.remove(self.center_shell)
                self.center.hide_all()
                self.center.destroy()
            self.center_shell = widget_shell
            self.center = widget
            self.center_shell.add(self.center)
            self.pack_start(self.center_shell, True, True, 0)

            # enable the function bindings for the specific listener
            for func in self.default_func_callback:
                self.center.listener.set_func_enabled(func, True)
            # register callbacks for function bindings
            for (func, cb) in self.default_func_callback.iteritems():
                self.center.listener.register_func_callback(func, cb)
            self.center.listener_sig = [
                self.center.listener.connect('z_activate', self._sig_listener_active, 'activate'),
                self.center.listener.connect('z_cancel',   self._sig_listener_active, 'cancel'),
                ]

            zTheme.register('update_font', zTheme._sig_update_font_modify, self.center)
            self.sig_id['focus_in'] = self.center.connect('focus-in-event', self._sig_focus_in)
            self.sig_id['focus_out'] = self.center.connect('focus-out-event', self._sig_focus_out)
            self.sig_id['button_press'] = widget_button_press_id


        # switch buffer
        self.active_buffer = new_buff
        self.update_buffer_list_selected(True, True)

        # connect buffer
        if self.active_buffer.type == 'file':
            self.center.set_buffer(new_buff.buffer)

        elif self.active_buffer.type == 'dir':
            if self.active_buffer.path and io_encap.is_dir(self.active_buffer.path):
                self.center.set_folder(os.path.join(* self.active_buffer.path))

        elif self.active_buffer.type == 'disp':
            self.center.set_buffer(new_buff)

        if self.need_init:
            self.exec_init_func()
            self.need_init = False # init finished, don't do it again

        # focus self out and in since the context has changed
        self.center.emit('focus-out-event', gtk.gdk.Event(gtk.gdk.FOCUS_CHANGE))
        self.center.emit('focus-in-event', gtk.gdk.Event(gtk.gdk.FOCUS_CHANGE))

        # (re)set font and color theme
        zTheme._sig_update_font_modify(self.center)
        self._sig_update_color_map()

        self.show_all()


    def save_buffer(self, buff):
        if not buff:
            buff = self.active_buffer

        try:
            return self.center.buffer_save(buff)
        except:
            if buff.path:
                msg = '{0}: Fail to save buffer!'.format(os.path.join(* buff.path))
            else:
                msg = '{0}: Fail to save buffer!'.format(buff.name)
            self.__last_line.set_text('', msg)
            return None

    def save_buffer_as(self, buff):
        if not buff:
            buff = self.active_buffer

        try:
            return self.center.buffer_save_as(buff)
        except:
            if buff.path:
                msg = '{0}: Fail to save buffer to the target file!'.format(os.path.join(* buff.path))
            else:
                msg = '{0}: Fail to save buffer to the target file!'.format(buff.name)
            self.__last_line.set_text('', msg)
            return None

    def rm_buffer(self, buff, force = False):
        if not buff:
            buff = self.active_buffer

        try:
            return zEditBuffer.rm_buffer(buff, force)
        except:
            if buff.path:
                msg = '{0}: Fail to remove buffer!'.format(os.path.join(* buff.path))
            else:
                msg = '{0}: Fail to remove buffer!'.format(buff.name)
            self.__last_line.set_text('', msg)
            return None


    def undo(self):
        if self.active_buffer.editable:
            return self.center.buffer_undo()
        return False

    def redo(self):
        if self.active_buffer.editable:
            return self.center.buffer_redo()
        return False


    def caps_on(self):
        return self.active_buffer.caps_on


    @staticmethod
    def get_last_line():
        return zEdit.__last_line

    @staticmethod
    def set_last_line(lastline):
        zEdit.__last_line = lastline


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

    @staticmethod
    def toggle_tabbar_mode():
        if not zEdit.get_tab_on():
            # off -> on
            zEdit.set_tab_on(True)
            zEdit.set_tab_grouped(False)
        elif zEdit.get_tab_on() and not zEdit.get_tab_grouped():
            # on -> grouped
            zEdit.set_tab_grouped(True)
        else:
            # grouped -> off
            zEdit.set_tab_on(False)
            zEdit.set_tab_grouped(False)

        zEdit.reg_emit('tabbar_mode_toggled')

    def switch_tab_to(self, dest):
        if dest not in [ 'prev', 'next' ]:
            raise KeyError

        # make sure tabbar is on
        if not zEdit.get_tab_on():
            zEdit.set_tab_on(True)
            zEdit.reg_emit('tabbar_mode_toggled')

        # wait tabbar to be turned on
        while not self.tab_on_current:
            gtk.main_iteration(False)

        # retrieve tabbar info
        curr_tab = self.tabbar.get_active()
        tab_list = self.tabbar.get_tab_list()

        if dest == 'prev':
            self.tabbar.set_active(tab_list[ tab_list.index(curr_tab) - 1                 ])
        else:
            self.tabbar.set_active(tab_list[(tab_list.index(curr_tab) + 1) % len(tab_list)])

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
        'buffer_modified_set'     : [  ],
        'buffer_mode_set'         : [  ],
        'buffer_caps_set'         : [  ],
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
                self.path = None # buffer_path is "buffer.name", no information for "buffer.path"
                self.type = buffer_type
            else:
                # not system-opened buffer => error
                raise ValueError
        elif buffer_type in [ None, 'file' ]:
            # file with a path => user-opened buffer
            buff_group = 'user'
            self.path = os.path.split(io_encap.norm_path_list(buffer_path)) # normalize path
            self.name = self.path[-1]
            self.type = 'file'  # must be type::file
        else:
            # not type::file, must be system-opened buffer
            buff_group = 'system'
            self.name = zEditBuffer.DEFAULT_BUFFER[buffer_type]
            if buffer_type == 'disp':
                self.path = None
            else:               # dir
                self.path = buffer_path
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
        return self.reinit()


    def reinit(self):
        # initiated flags
        self.modified   = None # will be set after determining the content
        self.major_mode = None # will be set after determining the content
        self.caps_on    = None # will be set after determining the content
        self.ast        = None # will be set after content is 1st loaded

        # fetch content
        if self.type == 'file':
            self.buffer = gtk.TextBuffer()
            self.buffer.reloading = False
            self.__reload_buffer()
            self.set_caps_on(True)

            # connect internal signals
            self.buffer.connect('changed', self._sig_buffer_content_changed)

        elif self.type == 'dir':
            self.buffer   = None
            self.writable = False # whether can be saved
            self.editable = None  # whether can be modified
            self.set_modified(False)
            self.switch_mode(majormode.DEFAULT['dir'], skip_ast = True)
            self.set_caps_on(False)

        elif self.type == 'disp':
            self.buffer   = gtk.TextBuffer()
            self.buffer.reloading = False
            self.writable = False # whether can be saved
            self.editable = None  # whether can be modified
            self.set_modified(False)
            self.switch_mode(majormode.DEFAULT['disp'], skip_ast = True)
            self.set_caps_on(False)

            self.buffer.undo_stack = None # mark disp as non-undoable
        else:
            raise TypeError
        return self


    ### internal signal definition
    def _sig_buffer_content_changed(self, textbuff):
        self.set_modified(True)
    ### end of internal signal definition


    def set_modified(self, setting):
        if setting != self.modified:
            self.modified = setting
            zEditBuffer.reg_emit('buffer_modified_set')


    def switch_mode(self, mode, skip_ast = False):
        if mode != self.major_mode:
            self.major_mode = mode
            if self.type == 'file'  and  not skip_ast:
                self.ast.reparse(** majormode.MODE_MAP[self.major_mode].ast_map)
            zEditBuffer.reg_emit('buffer_mode_set')


    def set_caps_on(self, setting):
        if setting != self.caps_on:
            self.caps_on = setting
            zEditBuffer.reg_emit('buffer_caps_set')

    def toggle_caps_on(self):
        self.set_caps_on(not self.caps_on)


    @staticmethod
    def backup():
        while zEditBuffer._on_restore:
            gtk.main_iteration(False)

        zEditBuffer.__buff_list  = copy.copy(zEditBuffer.buff_list) # never deepcopy this, for this stores all zEditBuffer
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


    def reload(self):
        self.__reload_buffer()


    def flush(self):
        if not self.buffer:
            return self.name, '(Buffer not savable!)'

        elif self.path:
            # user-opened buffer
            fullpath = os.path.join(* self.path)
            self.mtime = None   # mark mtime unavailable

            if not self.writable:
                self.mtime = os.stat(fullpath).st_mtime
                raise ValueError('Buffer not writable! Try flush_to(path) instead.')

            elif not self.modified:
                self.mtime = os.stat(fullpath).st_mtime
                return fullpath, '(No changes need to be saved.)'

            elif io_encap.flush(self):
                self.set_modified(False)
                self.mtime = os.stat(fullpath).st_mtime

                self.buffer.undo_stack.save_current_state()
                return fullpath, 'buffer saved.'
            else:
                self.mtime = os.stat(fullpath).st_mtime
                return fullpath, '(Cannot save the buffer! Permission denied!)'
        else:
            # system-opened buffer
            if not self.modified:
                return self.name, '(No changes need to be saved.)'
            else:
                raise ValueError('Cannot find the path! Use flush_to(path) instead.')

    def flush_to(self, path, callback):
        '''
        path
            an list of path nodes (can be obtained by os.path.split())

        callback
            the callback function that will be called when a new buffer
            is created. it should be defined as:
                def callback(new_buff)
        '''
        if not self.buffer:
            return self.name, '(Buffer not savable!)'

        if self.path and io_encap.norm_path_list(self.path) == io_encap.norm_path_list(path):
            return self.flush() # no change in path, save directly

        fullpath = os.path.join(* path)
        if io_encap.is_file(path) and not os.access(fullpath, os.W_OK):
            return fullpath, '(Target not writable!)'

        # create a new buffer
        opened_buffs = zEditBuffer.buff_list.values()
        new_buff = zEditBuffer(path, 'file')
        if self.type != 'file': # src is not a file
            new_buff.switch_mode(majormode.DEFAULT['disp'])

        if new_buff in opened_buffs:
            # buffer already opened, refuse renaming
            return path[-1], '(Cannot write to an existing buffer!)'

        # transfer content to the new buffer
        new_buff.buffer.set_text(
            self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter(), False)
            )
        # transfer cursor place to the new buffer
        new_buff.buffer.place_cursor(new_buff.buffer.get_iter_at_offset(self.buffer.get_property('cursor-position')))

        # transfer undo-stack to the new buffer
        if self.type == 'file': # src is also a file
            # transfer undo stack over
            dummy_undo_stack           = new_buff.buffer.undo_stack
            new_buff.buffer.undo_stack = self.buffer.undo_stack
            self.buffer.undo_stack     = dummy_undo_stack # this is for rm_buffer() to work correctly

        # write the new buffer
        new_buff.flush()
        new_buff.__reload_buffer(dry_run = True) # reload the new buffer to set all flags
        if self.type != 'file': # src is not a file
            new_buff.editable = False # set it to be modified-protected

        # clean up
        if self.path:
            # user-opened buffer
            # move new_buff in front of self
            buff_group = zEditBuffer.buff_group['user']
            buff_group.insert(
                buff_group.index(self.name),
                buff_group.pop( buff_group.index(new_buff.name) )
                )

            zEditBuffer.rm_buffer(self, True)
        else:
            # system-opened buffer, cannot be renamed
            if self.name == '*scratch*':
                # scratch is being saved, clear it
                self.__reload_buffer()

        callback(new_buff)
        return os.path.join(* new_buff.path), 'buffer saved.'


    @staticmethod
    def rm_buffer(buff, force):
        if buff.name in zEditBuffer.buff_group['system']:
            # system-opened buffer, cannot be closed
            if buff.name == '*scratch*':
                # close the scratch means to reset its content
                buff.buffer.undo_stack.clear() # clear the undo-stack
                buff.__reload_buffer(dry_run = True)
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
            buff.buffer.undo_stack.clear() # user-opened buffer, must be a file
            zEditBuffer.reg_emit('buffer_removed', buff.name)
            return os.path.join(* buff.path), 'buffer closed'


    ### supporting function
    def __reload_buffer(self, dry_run = False):
        self.buffer.reloading = True # notify zTextView to wait for update
        if self.name == '*scratch*':
            # tmp buffer
            if not self.major_mode:
                self.switch_mode(majormode.DEFAULT['scratch'], skip_ast = True)
            mode = majormode.MODE_MAP[self.major_mode]

            self.buffer.set_text(mode.default['scratch'])
            self.buffer.place_cursor(self.buffer.get_start_iter())
            self.ast = zSyntaxParser(mode.default['scratch'], ** mode.ast_map)

            self.writable = False # whether can be saved
            self.editable = True  # whether can be modified

        elif io_encap.is_file(self.path):
            # existing file
            if io_encap.is_binary(self.path):
                raise TypeError('Cannot open a binary file.')

            # test permission
            fullpath = os.path.join(* self.path)
            if not os.access(fullpath, os.R_OK):
                raise AssertionError('Permission Denied: directory not readable!')

            if not io_encap.fetch(self):
                raise BufferError('Failed to fetch the content.')
            self.buffer.place_cursor(self.buffer.get_start_iter())

            buffer_text = self.buffer.get_text( self.buffer.get_start_iter(),
                                                self.buffer.get_end_iter(),
                                                False
                                                )
            if not self.major_mode:
                self.switch_mode(majormode.guess(buffer_text), skip_ast = True)
            mode = majormode.MODE_MAP[self.major_mode]

            self.ast = zSyntaxParser(buffer_text, ** mode.ast_map)

            self.writable = os.access(fullpath, os.W_OK) # whether can be saved
            self.editable = os.access(fullpath, os.W_OK) # whether can be modified
            self.mtime = os.stat(fullpath).st_mtime      # time modified
        else:
            # new file
            # passive alloc (copy on write)
            if not self.major_mode:
                self.switch_mode(majormode.DEFAULT['file'], skip_ast = True)
            mode = majormode.MODE_MAP[self.major_mode]

            self.ast = zSyntaxParser('', ** mode.ast_map)

            self.writable = True
            self.editable = True
            self.mtime = None

        if not dry_run:
            self.buffer.undo_stack = zUndoStack(
                self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter(), False)
                )
            self.buffer.connect('insert_text',  self.__sig_buffer_text_inserting)
            self.buffer.connect('delete_range', self.__sig_buffer_range_deleting)
        self.set_modified(False)
        self.buffer.reloading = False # notify zTextView to update


    def __sig_buffer_text_inserting(self, textbuffer, ins_iter, text, length):
        self.ast.update(
            zBufferChange(text, ins_iter.get_offset(), 'i')
            )

    def __sig_buffer_range_deleting(self, textbuffer, start_iter, end_iter):
        self.ast.update(
            zBufferChange(textbuffer.get_text(start_iter, end_iter, False), start_iter.get_offset(), 'd')
            )
    ### end of supporting function
