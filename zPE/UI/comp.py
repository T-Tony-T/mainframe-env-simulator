# this is the UI components file

import io_encap
# this package should implement the following APIs:
#
#   is_file(fn_list):           test if the fn_list corresponding to a file
#   is_dir(fn_list):            test if the fn_list corresponding to a directory
#
#   open_file(fn_list, mode):   open the file with the indicated mode
#
#   fetch(buff):                read content from the corresponding file to the zEditBuffer
#   flush(buff):                write content from the zEditBuffer to the corresponding file
# 

import os, sys, stat, time, copy
import pygtk
pygtk.require('2.0')
import gtk
import gobject, pango


######## ######## ######## ########
######## Supported Feature ########
######## ######## ######## ########

SUPPORT = { }
if gtk.gdk.screen_get_default().get_rgba_colormap():
    SUPPORT['rgba'] = True
else:
    SUPPORT['rgba'] = False


######## ######## ######## ########
########       z_ABC       ########
######## ######## ######## ########

class z_ABC(object):
    '''z Abstract Base Class:  Implemetation of a Signal-Like System'''
    @classmethod
    def register(cls, sig, callback, widget, *data):
        '''This function register a function to a signal-like string'''
        cls._auto_update[sig].append((widget, callback, data))

    @classmethod
    def unregister(cls, sig, widget):
        '''This function un-register a widget from a signal-like string'''
        reserve = []
        for item in cls._auto_update[sig]:
            if widget != item[0]:
                reserve.append(item)
        cls._auto_update[sig] = reserve

    @classmethod
    def clean_up(cls):
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

    @classmethod
    def emit(cls, sig, info = None):
        '''
        This function emit the signal to all registered object

        Caution: may cause multiple emission. To avoid that,
                 use emit_from() instead.
        '''
        for (widget, callback, data_list) in cls._auto_update[sig]:
            if info:
                callback(widget, info, *data_list)
            else:
                callback(widget, *data_list)

    @classmethod
    def emit_from(cls, sig, target, info = None):
        '''This function emit the signal to the indicated registered object'''
        for (widget, callback, data_list) in cls._auto_update[sig]:
            if target == widget:
                if info:
                    callback(widget, info, *data_list)
                else:
                    callback(widget, *data_list)



######## ######## ######## ########
########     zComboBox     ########
######## ######## ######## ########

class zComboBox(gtk.ComboBox):
    '''A Flat (Inline) ComboBox'''
    def __init__(self, model = None):
        super(zComboBox, self).__init__(model)


        self.set_property('can-default', False)
        self.set_property('can-focus', False)
        self.set_property('focus-on-click', False)
        self.set_property('has-frame', False)


    def set_char_len(self, str_len):
        ( char_w, char_h ) = self.create_pango_layout('w').get_pixel_size()
        ( cell_w, cell_h ) =  self.size_request()
        self.set_size_request(char_w * str_len, cell_h)



######## ######## ######## ########
########       zEdit       ########
######## ######## ######## ########

class zEdit(z_ABC, gtk.VBox):
    '''A Multi-Buffer Text Editor with an Internal File Browser'''
    __style = 'other'           # see zEdit.set_style()
    __key_binding = {}          # see zEdit.set_key_binding()

    __tab_on = False            # see zEdit.set_tab_on()
    __tab_grouped = False       # see zEdit.set_tab_grouped()


    _buff_sw_sig_id = {
        # combobox : sig_id
        }

    _focus = None

    _auto_update = {
        # 'signal_like_string'  : [ (widget, callback, data_list), ... ]
        'buffer_focus_in'       : [  ],
        'buffer_focus_out'      : [  ],

        'populate_popup'        : [  ],

        'update_tabbar'         : [  ],

        # for key binding
        'buffer_open'           : [  ],
        'buffer_save'           : [  ],
        'buffer_save_as'        : [  ],
        'buffer_close'          : [  ],

        'prog_show_config'      : [  ],
        'prog_show_error'       : [  ],
        'prog_show_help'        : [  ],
        'prog_show_about'       : [  ],
        'prog_quit'             : [  ],
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

        self.__on_init = True
        self.__on_mod_buff_list = False

        self.active_buffer = None
        self.sig_id = {}        # a dict holds all handler id

        self.ui_init_func = None
        self.need_init = None   # since no init_func is set at this time

        # layout of the frame:
        #
        #                   tabbar (can be turn off)
        #   +--+--+------+_/
        #   +--+--+------+_
        #   |+----------+| \
        #   ||          ||  center_shell
        #   ||          ||
        #   ||  center  ||
        #   ||          ||
        #   ||          ||
        #   |+----------+|
        #   +--+---------+
        #   |sw| bottom  |
        #   +--+---------+

        # create tabbar if turned on
        self.tab_on_current = False
        self.__tab_list = []    # list of gtk.Frame that contain gtk.ToolButton
        self.__tab_sig_map = {} # gtk.Frame : handler_id
        if zEdit.__tab_on:
            self._sig_update_tabbar()

        # create the status bar
        self.bottom_bg = gtk.EventBox()
        self.pack_end(self.bottom_bg, False, False, 0)
        self.bottom = gtk.HBox()
        self.bottom_bg.add(self.bottom)

        # create buffer switcher
        self.buffer_sw_tm = gtk.ListStore(str, bool) # define TreeModel
        self.buffer_sw = zComboBox(self.buffer_sw_tm)
        self.bottom.pack_start(self.buffer_sw, False, False, 0)

        self.buffer_sw_cell = gtk.CellRendererText()
        self.buffer_sw.pack_start(self.buffer_sw_cell, True)
        self.buffer_sw.add_attribute(self.buffer_sw_cell, "text", 0)
        self.buffer_sw_cell.props.ellipsize = pango.ELLIPSIZE_END

        self.buffer_sw.set_row_separator_func(self.__separator)

        # create the main window frame
        self.scrolled = gtk.ScrolledWindow()
        self.pack_start(self.scrolled, True, True, 0)
        self.scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.scrolled.set_placement(gtk.CORNER_TOP_RIGHT)

        self.center = None
        self.set_buffer(buffer_path, buffer_type)

        # connect auto-update items
        zEdit.register('update_tabbar', self._sig_update_tabbar, self)
        self._sig_update_tabbar()

        zEditBuffer.register('buffer_list_modified', zEdit._sig_buffer_list_modified, self)
        zEdit._sig_buffer_list_modified(self)

        zTheme.register('update_font', self._sig_update_font, self.buffer_sw_cell)
        self._sig_update_font()

        zTheme.register('update_color_map', self._sig_update_color_map, self)

        # connect signal
        zEdit._buff_sw_sig_id[self.buffer_sw] = self.buffer_sw.connect('changed', self._sig_buffer_changed)

        self.__on_init = False


    ### signal-like auto-update function
    def _sig_update_tabbar(self, widget = None):
        if zEdit.__tab_on:
            # turn on the tabbar
            if not self.tab_on_current:
                # tabbar off
                self.tabbar_bg = gtk.EventBox()
                if not self.__on_init:
                    self.remove(self.scrolled)
                self.pack_start(self.tabbar_bg, False, False, 0)
                if not self.__on_init:
                    self.pack_start(self.scrolled, True, True, 0)

                self.tabbar = gtk.HBox()
                self.tabbar_bg.add(self.tabbar)

                if self.__on_init:
                    self.tab_on_current = True
                    return      # rest will be done by the constructor

            # update buffer list
            zEdit._sig_buffer_list_modified(self, None, True)
            self.tabbar_bg.show_all()

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
                self.remove(self.tabbar_bg)
                for child in self.__tab_list:
                    child.child.disconnect(self.__tab_sig_map[child])

                self.__tab_list = []
                self.__tab_sig_map = {}
                self.tabbar_bg.hide_all()

                # retain focus
                if zEdit._focus:
                    zEdit._focus.grab_focus()
                else:
                    self.grab_focus()

                self.tab_on_current = False


    @staticmethod
    def _sig_buffer_list_modified(z_editor, new_buff = None, skip_sw = False):
        z_editor.__on_mod_buff_list = True

        ### for tabbar
        if zEdit.__tab_on:
            if not new_buff or not z_editor.is_focus():
                new_buff = z_editor.active_buffer

            z_editor.rebuild_tabbar(new_buff)
            z_editor.update_buffer_list_selected(True, False)

            z_editor.tabbar.show_all()

        ### for buffer switcher
        if skip_sw:
            z_editor.__on_mod_buff_list = False
            return              # early return

        # temporarily block combobox::changed signal
        for (k, v) in zEdit._buff_sw_sig_id.items():
            k.handler_block(v)

        # clear the list
        z_editor.buffer_sw_tm.clear()

        # add system-opened buffers
        for buff in zEditBuffer.buff_group['system']:
            z_editor.buffer_sw_tm.append([buff, False])
        # add user-opened buffers, if exist
        if len(zEditBuffer.buff_group['user']):
            # add separator: Not an Item, this item should not be seen
            z_editor.buffer_sw_tm.append(['NanI', True])
            # add user-opened buffers
            for buff in zEditBuffer.buff_group['user']:
                z_editor.buffer_sw_tm.append([buff, False])

        # unblock combobox::changed signal
        for (k, v) in zEdit._buff_sw_sig_id.items():
            k.handler_unblock(v)

        # set active
        z_editor.update_buffer_list_selected(False, True)

        z_editor.__on_mod_buff_list = False

    def update_buffer_list_selected(self, mask_tab = True, mask_sw = True):
        ### for tabbar
        if mask_tab and self.__tab_on:
            frame_list = self.tabbar.get_children()
            if self.active_buffer.name not in [ frame.child.get_label() for frame in frame_list ]:
                self.rebuild_tabbar(self.active_buffer)
                frame_list = self.tabbar.get_children()

            for frame in frame_list:
                if frame.child.get_label() == self.active_buffer.name:
                    frame.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
                    frame.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['reserve']))
                else:
                    frame.set_shadow_type(gtk.SHADOW_OUT)
                    frame.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['status']))

        ### for switcher
        if mask_sw:
            buffer_iter = self.buffer_sw_tm.get_iter_first()
            if buffer_iter:
                while self.buffer_sw_tm.get_value(buffer_iter, 0) != self.active_buffer.name:
                    buffer_iter = self.buffer_sw_tm.iter_next(buffer_iter)
                self.buffer_sw.set_active_iter(buffer_iter)

    def _sig_update_font(self, widget = None):
        zTheme._sig_update_font_property(self.buffer_sw_cell, 0.75)
        self.resize()

    def _sig_update_color_map(self, widget = None):
        self.center.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.center.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['base']))

        self.center.modify_text(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.center.modify_base(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['base']))

        self.center.modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse(zTheme.color_map['text_selected']))
        self.center.modify_base(gtk.STATE_SELECTED, gtk.gdk.color_parse(zTheme.color_map['base_selected']))

        if self.is_focus():
            self.update_theme_focus_in()
        else:
            self.update_theme_focus_out()

    def update_theme_focus_in(self):
        if self.tab_on_current:
            self.tabbar_bg.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['status_active']))
        self.bottom_bg.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['status_active']))
        self.buffer_sw_cell.set_property('background-gdk', gtk.gdk.color_parse(zTheme.color_map['status_active']))

    def update_theme_focus_out(self):
        if self.tab_on_current:
            self.tabbar_bg.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['status']))
        self.bottom_bg.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['status']))
        self.buffer_sw_cell.set_property('background-gdk', gtk.gdk.color_parse(zTheme.color_map['status']))
    ### end of signal-like auto-update function


    ### top-level signal
    def _sig_key_pressed(self, widget, event, data = None):
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

        if zEdit.__style == 'emacs':
            # style::emacs
            pass
        else:
            # style::other
            key_binding = zEdit.__key_binding
            reg_func = zEdit._auto_update
            if ( stroke in key_binding            and # is a binded key stroke
                 key_binding[stroke] in reg_func  and # is a valid functionality
                 len(reg_func[key_binding[stroke]])   # has registered functions
                 ):
                zEdit.emit(key_binding[stroke])
            else:
                return False

        return True
    ### end of top-level signal


    ### signal for center
    def _sig_button_press(self, widget, event, data = None):
        if event.button != 3:
            return

        # create the menu
        menu = gtk.Menu()

        # fill the menu
        ( tree_path, tree_col, tree_x, tree_y ) = widget.get_path_at_pos(int(event.x), int(event.y))
        model = widget.get_model()

        if tree_path is None:
            raise LookupError
        elif len(tree_path) > 0:
            iterator = model.get_iter(tree_path)
            obj = model[iterator][0]
        else:
            raise ValueError

        mi_open = gtk.MenuItem('_Open')
        menu.append(mi_open)
        mi_open.connect_object("activate", widget._sig_open_file, widget, tree_path, tree_col)

        # callback
        zEdit.emit_from('populate_popup', self.center, menu)

        # popup the menu
        menu.popup(None, None, None, event.button, event.time)


    def _sig_focus_in(self, widget, event):
        zEdit._focus = self

        if len(zEdit._auto_update['buffer_focus_in']):
            zEdit.emit('buffer_focus_in')
        self.update_theme_focus_in()

    def _sig_focus_out(self, widget, event):
        if len(zEdit._auto_update['buffer_focus_out']):
            zEdit.emit('buffer_focus_out')
        self.update_theme_focus_out()

    def _sig_tab_clicked(self, widget):
        buffer_name = widget.get_label()

        if buffer_name != self.active_buffer.name:
            buff = zEditBuffer.buff_list[buffer_name]
            self.set_buffer(buff.path, buff.type)

        # set focus
        if zEdit._focus and self.__on_mod_buff_list:
            zEdit._focus.grab_focus()
        else:
            self.grab_focus()
    ### end of signal for center


    ### signal for bottom
    def _sig_buffer_changed(self, combobox):
        # check for switcher items
        active_iter = combobox.get_active_iter()
        if not active_iter:
            return              # early return

        # switch buffer
        buffer_name = self.buffer_sw_tm.get_value(active_iter, 0)

        if buffer_name != self.active_buffer.name:
            buff = zEditBuffer.buff_list[buffer_name]
            self.set_buffer(buff.path, buff.type)

        # set focus
        if zEdit._focus and self.__on_mod_buff_list:
            zEdit._focus.grab_focus()
        else:
            self.grab_focus()
    ### end of signal for bottom


    ### overridden function definition
    @classmethod
    def clean_up(cls):
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

        reserve = {}
        for (k, v) in cls._buff_sw_sig_id.items():
            if k.get_property('visible'):
                reserve[k] = v
            else:
                k.disconnect(v)
        cls._buff_sw_sig_id = reserve


    def connect(self, sig, callback, *data):
        if sig not in zEdit._auto_update:
            return self.center.connect(sig, callback, *data)

        if self.active_buffer.type == 'file': # after re-write TextView, this should not be tested
            return self.center.connect(sig, callback, *data)

        zEdit.register(sig, callback, self.center, *data)
        return (sig, self.center)

    def disconnect(self, sig_id):
        if isinstance(sig_id, int):
            self.center.disconnect(sig_id)
        else:
            zEdit.unregister(sig, self.center)

    def is_focus(self):
        return self.center.is_focus()

    def grab_focus(self):
        self.center.grab_focus()

    def resize(self):
        self.buffer_sw.set_char_len(10)
    ### end of overridden function definition


    def rebuild_tabbar(self, target_buff):
        if not zEdit.__tab_on:
            return

        for child in self.__tab_list:
            # clear the current tabbar
            self.tabbar.remove(child)
            child.child.disconnect(self.__tab_sig_map[child])

        tab_list = []
        self.__tab_list = []
        self.__tab_sig_map = {}

        if ( target_buff.name in zEditBuffer.buff_group['system'] or
             not zEdit.__tab_grouped
             ):
            # add system-opened buffers
            for buff in zEditBuffer.buff_group['system']:
                tab_list.append(gtk.ToolButton(label = buff))
        if ( target_buff.name in zEditBuffer.buff_group['user'] or
             not zEdit.__tab_grouped
             ):
            # add user-opened buffers
            for buff in zEditBuffer.buff_group['user']:
                tab_list.append(gtk.ToolButton(label = buff))

        # add tabs to the tabbar
        for tab in tab_list:
            tab.set_property('can-default', False)
            tab.set_property('can-focus', False)

            frame = gtk.Frame()
            frame.add(tab)
            self.tabbar.pack_start(frame, False, False, 0)

            self.__tab_list.append(frame)
            self.__tab_sig_map[frame] = tab.connect('clicked', self._sig_tab_clicked)


    def exec_init_func(self):
        if self.need_init:
            self.ui_init_func(self)

    def set_init_func(self, ui_init_func):
        self.ui_init_func = ui_init_func
        self.need_init = True


    def get_buffer(self):
        return (self.active_buffer.path, self.active_buffer.type)

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
                widget = gtk.TextView()
            elif new_buff.type == 'dir':
                widget = zFileManager()
                self.sig_id['button_press'] = widget.connect('button-press-event', self._sig_button_press)
            else:
                raise KeyError

            # switch widget
            if self.center:
                zTheme.unregister('update_font', self.center)
                if self.active_buffer.type == 'dir':
                    self.center.disconnect(self.sig_id['button_press'])
                    zEdit.unregister('populate_popup', self.center)

                zTheme.unregister('update_font', self.center)
                self.center.disconnect(self.sig_id['focus_in'])
                self.center.disconnect(self.sig_id['focus_out'])
                self.center.disconnect(self.sig_id['key_press'])

                self.scrolled.remove(self.center)
            self.center = widget
            self.scrolled.add(self.center)

            zTheme.register('update_font', zTheme._sig_update_font_modify, self.center)
            self.sig_id['focus_in'] = self.center.connect('focus-in-event', self._sig_focus_in)
            self.sig_id['focus_out'] = self.center.connect('focus-out-event', self._sig_focus_out)
            self.sig_id['key_press'] = self.center.connect('key-press-event', self._sig_key_pressed)

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


    @staticmethod
    def get_key_binding():
        return zEdit.__key_binding

    @staticmethod
    def set_key_binding(dic):
        zEdit.__key_binding = copy.deepcopy(dic)

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
            zEdit.emit('update_tabbar')

    @staticmethod
    def get_tab_grouped():
        return zEdit.__tab_grouped

    @staticmethod
    def set_tab_grouped(setting):
        if zEdit.__tab_grouped != setting:
            zEdit.__tab_grouped = setting
            zEdit.emit('update_tabbar')


    ### supporting function
    def __separator(self, model, iterator, data = None):
        return model.get_value(iterator, 1)
    ### end of supporting function


######## ######## ######## ########
########    zEditBuffer    ########
######## ######## ######## ########

class zEditBuffer(z_ABC):
    '''The Centralized Buffer Allocator and Controller that Supports zEdit Class'''
    DEFAULT_BUFFER = {
        None   : '*scratch*',
        'file' : '*scratch*',
        'dir'  : '*browser*',
        }
    SYSTEM_BUFFER = {
        '*scratch*' : 'file',
        '*browser*' : 'dir',
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
                self.path = None # path is ".name", no information for ".path"
                self.type = buffer_type
            else:
                # not system-opened buffer => error
                raise ValueError
        elif buffer_type in [ None, 'file' ]:
            # file with a path => user-opened buffer
            buff_group = 'user'
            self.name = buffer_path[-1]
            self.path = buffer_path
            self.type = 'file'  # must be type::file
        else:
            # not type::file, must be system-opened buffer
            buff_group = 'system'
            self.name = zEditBuffer.DEFAULT_BUFFER[buffer_type]
            self.path = buffer_path # not type::file, no limitation on ".path" property
            self.type = buffer_type

        # update buffer list
        if self.type == 'file':
            # only record type::file for user-opened buffer
            no_rec = True           # assume first encounter of the name
            if self.name in zEditBuffer.buff_rec:
                # name is recorded, check for duplication
                for [name, path, opened] in zEditBuffer.buff_rec[self.name]:
                    if path == self.path:
                        # same path ==> has record
                        no_rec = False

                        if opened:
                            # return old file reference
                            return zEditBuffer.buff_list[name] # early return
                        else:
                            # re-open it
                            self.name = name
                            break
                if no_rec:
                    # no duplication, generate new name of the new file
                    self.name += "(" + str(len(zEditBuffer.buff_rec[self.name])) + ")"

            if no_rec:
                # name not in record, add it
                zEditBuffer.buff_rec[self.name] = [ (self.name, self.path, True) ]
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
        zEditBuffer.emit('buffer_list_modified', self)

        # fetch content
        if self.type == 'file':
            self.buffer = gtk.TextBuffer()

            if self.name == '*scratch*':
                # tmp buffer
                self.buffer.set_text(
'''//*
//* This buffer is for notes you don't want to save.
//* If you want to create a file, use {0}
//* or save this buffer explicitly.
//*
'''.format('"Open a New Buffer"')
)
            elif io_encap.is_file(self.path):
                # existing file
                if not io_encap.fetch(self):
                    raise BufferError
            else:
                # new file
                pass
            self.modified = False
        elif buffer_type == 'dir':
            self.buffer = None
            self.modified = None
        else:
            raise TypeError

        return self


    @staticmethod
    def backup():
        if zEditBuffer._on_restore:
            gtk.main_iteration()

        zEditBuffer.__buff_list  = copy.copy(zEditBuffer.buff_list) # never deepcopy this
        zEditBuffer.__buff_group = copy.deepcopy(zEditBuffer.buff_group)
        zEditBuffer.__buff_rec   = copy.deepcopy(zEditBuffer.buff_rec)


    @staticmethod
    def restore():
        zEditBuffer._on_restore = True

        zEditBuffer.buff_list  = copy.copy(zEditBuffer.__buff_list) # never deepcopy this
        zEditBuffer.buff_group = copy.deepcopy(zEditBuffer.__buff_group)
        zEditBuffer.buff_rec   = copy.deepcopy(zEditBuffer.__buff_rec)

        zEditBuffer.emit('buffer_list_modified')

        zEditBuffer._on_restore = False


######## ######## ######## ########
########    zErrConsole    ########
######## ######## ######## ########

class zErrConsole(gtk.Window):
    '''An Error Console Widget'''
    def __init__(self, title, show_on_change = False):
        '''
        title
            the title of the zErrConsole.

        show_on_change
            whether the zErrConsole should automatically show when
            new messages are added.
        '''
        super(zErrConsole, self).__init__()

        self.setup = True       # in setup phase, write to stderr as well

        self.set_destroy_with_parent(True)
        self.connect("delete_event", self._sig_close_console)

        self.set_title(title)


        # layout of the frame:
        # 
        #   +------------+_
        #   |+----------+| \
        #   ||          ||  scrolled_window
        #   ||          ||
        #   ||  center  ||
        #   ||          ||
        #   ||          ||
        #   |+----------+|
        #   +------+--+--+-- separator
        #   |      |bt|bt|
        #   +------+--+--+

        layout = gtk.VBox()
        self.add(layout)

        # create center
        scrolled = gtk.ScrolledWindow()
        layout.pack_start(scrolled, True, True, 0)
        scrolled.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        scrolled.set_placement(gtk.CORNER_TOP_RIGHT)

        self.center = gtk.TextView()
        scrolled.add(self.center)
        self.center.set_wrap_mode(gtk.WRAP_CHAR)
        self.center.set_editable(False)
        self.center.set_cursor_visible(False)

        zTheme.register('update_font', zTheme._sig_update_font_modify, self.center, 0.85)
        zTheme._sig_update_font_modify(self.center, 0.85)
        zTheme.register('update_color_map', self._sig_update_color_map, self.center)
	self._sig_update_color_map()

        # separator
        layout.pack_start(gtk.HSeparator(), False, False, 2)

        # create bottom
        self.bottom = gtk.HBox()
        layout.pack_end(self.bottom, False, False, 0)

        self.bttn_clear = gtk.Button(stock = gtk.STOCK_CLEAR)
        self.bttn_clear.set_label('C_lear')
        self.bttn_close = gtk.Button(stock = gtk.STOCK_CLOSE)
        self.bttn_close.set_label('_Close')

        self.bttn_clear.connect('clicked', self._sig_clear)
        self.bttn_close.connect('clicked', self._sig_close_console)

        self.bottom.pack_start(gtk.Label(), True, True, 0)
        self.bottom.pack_end(self.bttn_close, False, False, 5)
        self.bottom.pack_end(self.bttn_clear, False, False, 5)

        # connect signal
        if show_on_change:
            self.center.get_buffer().connect('changed', self._sig_open_console)

        layout.show_all()
        self.resize()


    ### signal-like auto-update function
    def _sig_update_color_map(self, widget = None):
        self.center.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.center.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['base']))

        self.center.modify_text(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.center.modify_base(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['base']))

        self.center.modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse(zTheme.color_map['text_selected']))
        self.center.modify_base(gtk.STATE_SELECTED, gtk.gdk.color_parse(zTheme.color_map['base_selected']))
    ### end of signal-like auto-update function


    ### signal definition
    def _sig_clear(self, widget):
        self.clear()

    def _sig_open_console(self, *arg):
        if not self.setup:
            self.open()

    def _sig_close_console(self, *arg):
        self.close()
        return True
    ### end of signal definition


    ### overridden function definition
    def clear(self):
        self.set_text('')

    def open(self):
        if self.get_property('visible'):
            self.window.show()
        else:
            self.show()

    def close(self):
        self.hide()

    def get_text(self):
        buff = self.center.get_buffer()
        return buff.get_text(buff.get_start_iter(), buff.get_end_iter())

    def set_text(self, text):
        self.center.get_buffer().set_text(text)

    def resize(self):
        ( char_w, char_h ) = self.center.create_pango_layout('w').get_pixel_size()

        ex_w = 2 # to "somewhat" cancel the border width, since there is no way to get that value
        scrolled = self.center.parent
        ex_w += scrolled.get_hscrollbar().style_get_property('slider-width')
        ex_w += scrolled.style_get_property('scrollbar-spacing')

        self.set_default_size(char_w * 80 + ex_w, char_h * 25)

    def write(self, text):
        buff = self.center.get_buffer()
        buff.insert(buff.get_end_iter(), text)
        if self.setup:
            sys.__stderr__.write(text)
    ### end of overridden function definition


######## ######## ######## ########
########   zFileManager    ########
######## ######## ######## ########

class zFileManager(gtk.TreeView):
    '''A Light-Weighted File Manager Used by zEdit Class'''
    folderxpm = [
        "17 16 7 1",
        "  c #000000",
        ". c #808000",
        "X c yellow",
        "o c #808080",
        "O c #c0c0c0",
        "+ c white",
        "@ c None",
        "@@@@@@@@@@@@@@@@@",
        "@@@@@@@@@@@@@@@@@",
        "@@+XXXX.@@@@@@@@@",
        "@+OOOOOO.@@@@@@@@",
        "@+OXOXOXOXOXOXO. ",
        "@+XOXOXOXOXOXOX. ",
        "@+OXOXOXOXOXOXO. ",
        "@+XOXOXOXOXOXOX. ",
        "@+OXOXOXOXOXOXO. ",
        "@+XOXOXOXOXOXOX. ",
        "@+OXOXOXOXOXOXO. ",
        "@+XOXOXOXOXOXOX. ",
        "@+OOOOOOOOOOOOO. ",
        "@                ",
        "@@@@@@@@@@@@@@@@@",
        "@@@@@@@@@@@@@@@@@"
        ]
    folderpb = gtk.gdk.pixbuf_new_from_xpm_data(folderxpm)

    filexpm = [
        "12 12 3 1",
        "  c #000000",
        ". c #ffff04",
        "X c #b2c0dc",
        "X        XXX",
        "X ...... XXX",
        "X ......   X",
        "X .    ... X",
        "X ........ X",
        "X .   .... X",
        "X ........ X",
        "X .     .. X",
        "X ........ X",
        "X .     .. X",
        "X ........ X",
        "X          X"
        ]
    filepb = gtk.gdk.pixbuf_new_from_xpm_data(filexpm)

    column_names = ['Name', 'Size', 'Last Changed']

    def __init__(self, dname = None):
        super(zFileManager, self).__init__()


        # create the TreeViewColumns to display the data
        cell_data_funcs = (None, self.__file_size, self.__file_last_changed)

        self.fm_column = [None] * len(zFileManager.column_names)

        cellpb = gtk.CellRendererPixbuf()
        self.fm_column[0] = gtk.TreeViewColumn(self.column_names[0], cellpb)
        self.fm_column[0].set_cell_data_func(cellpb, self.__file_pixbuf)

        cell = gtk.CellRendererText()
        self.fm_column[0].pack_start(cell, False)
        self.fm_column[0].set_cell_data_func(cell, self.__file_name)

        self.append_column(self.fm_column[0])

        for n in range(1, len(self.column_names)):
            cell = gtk.CellRendererText()
            self.fm_column[n] = gtk.TreeViewColumn(self.column_names[n], cell)
            if n == 1:
                cell.set_property('xalign', 1.0)
            self.fm_column[n].set_cell_data_func(cell, cell_data_funcs[n])
            self.append_column(self.fm_column[n])

        # connect signal
        self.connect('row-activated', self._sig_open_file)

        # set cwd
        self.set_folder(dname)


    ### signal definition
    def _sig_open_file(self, treeview, tree_path, column):
        model = self.get_model()
        iterator = model.get_iter(tree_path)

        file_name = model.get_value(iterator, 0)
        file_path = os.path.join(self.dirname, file_name)

        file_stat = os.stat(file_path)
        if stat.S_ISDIR(file_stat.st_mode):
            self.set_folder(file_path)
        elif stat.S_ISREG(file_stat.st_mode):
            self.open_file([self.dirname, file_name])
    ### end of signal definition


    ### overridden function definition
    def grab_focus(self):
        super(zFileManager, self).grab_focus()
        self.set_cursor((0,))
    ### end of overridden function definition


    def open_file(self, fn_list):
        self.parent.parent.set_buffer(fn_list, 'file')


    def set_folder(self, dname=None):
        if not dname:
            self.dirname = os.path.expanduser('~')
        else:
            self.dirname = os.path.abspath(dname)

        files = [f for f in os.listdir(self.dirname) if f[0] <> '.']
        files.sort()
        files = ['..'] + files
        listmodel = gtk.ListStore(object)
        for f in files:
            listmodel.append([f])
        self.set_model(listmodel)
        self.grab_focus()


    ### supporting function
    def __file_pixbuf(self, column, cell, model, iterator):
        filename = os.path.join(self.dirname, model.get_value(iterator, 0))
        filestat = os.stat(filename)
        if stat.S_ISDIR(filestat.st_mode):
            pb = zFileManager.folderpb
        else:
            pb = zFileManager.filepb
        cell.set_property('pixbuf', pb)


    def __file_name(self, column, cell, model, iterator):
        cell.set_property('text', model.get_value(iterator, 0))


    def __file_size(self, column, cell, model, iterator):
        filename = os.path.join(self.dirname, model.get_value(iterator, 0))
        filestat = os.stat(filename)
        size = filestat.st_size
        if size < 1024:
            size = '{0}.0'.format(size) # the extra '.0' is required to pass the parser
            unit = 'B'
        elif size < 1048576:            # 1024 ^ 2
            size = '{0:.1f}'.format(size / 1024.0)
            unit = 'K'
        elif size < 1073741824:         # 1024 ^ 3
            size = '{0:.1f}'.format(size / 1048576.0)
            unit = 'M'
        else:
            size = '{0:.1f}'.format(size / 1073741824.0)
            unit = 'G'
        if size[-2:] == '.0':
            size = size[:-2]
        cell.set_property('text', size + unit)


    def __file_last_changed(self, column, cell, model, iterator):
        filename = os.path.join(self.dirname, model.get_value(iterator, 0))
        filestat = os.stat(filename)
        cell.set_property('text', time.ctime(filestat.st_mtime))
    ### end of supporting function


######## ######## ######## ########
########     zLastLine     ########
######## ######## ######## ########

class zLastLine(gtk.HBox):
    '''An Emacs Style Last-Line Statusbar'''
    def __init__(self, label = ''):
        '''
        label
            the label in front of the last-line panel
        '''
        super(zLastLine, self).__init__()


        self.__label = gtk.Label(label)
        self.pack_start(self.__label, False, False, 0)

        self.__line_fix = gtk.Label()
        self.pack_start(self.__line_fix, False, False, 0)

        self.__line_inter = gtk.Entry()
        self.pack_start(self.__line_inter, True, True, 0)

        self.__line_inter.set_has_frame(False)

        self.set_editable(False)


        # connect auto-update items
        zTheme.register('update_font', zTheme._sig_update_font_modify, self.__label)
        zTheme._sig_update_font_modify(self.__label)

        zTheme.register('update_font', zTheme._sig_update_font_modify, self.__line_fix)
        zTheme._sig_update_font_modify(self.__line_fix)

        zTheme.register('update_font', zTheme._sig_update_font_modify, self.__line_inter)
        zTheme._sig_update_font_modify(self.__line_inter)

        zTheme.register('update_color_map', self._sig_update_color_map, self)
        self._sig_update_color_map()


    ### signal-like auto-update function
    def _sig_update_color_map(self, widget = None):
        self.__line_fix.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['reserve']))

        self.__line_inter.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.__line_inter.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['base']))

        self.__line_inter.modify_text(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.__line_inter.modify_base(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['base']))
    ### end of signal-like auto-update function

    ### overridden function definition
    def connect(self, sig, *data):
        return self.__line_inter.connect(sig, *data)
    ### end of overridden function definition

    def get_label(self):
        return self.__label.get_text()

    def set_label(self, string):
        self.__label.set_text(string)

    def set_highlight_text(self, string):
        self.__line_fix.set_markup('<b>{0}</b>'.format(string))

    def get_text(self):
        return self.__line_inter.get_text()

    def set_text(self, string):
        self.__line_inter.set_text(string)

    def set_editable(self, setting):
        self.__line_inter.set_property('can-default', setting)
        self.__line_inter.set_property('can-focus', setting)
        self.__line_inter.set_editable(setting)
        self.__line_inter.grab_focus()



######## ######## ######## ########
########   zSplitScreen    ########
######## ######## ######## ########

class zSplitScreen(z_ABC, gtk.Frame):
    '''A Split-Screen Frame with DnD Splitting Supported'''
    _auto_update = {
        # 'signal_like_string'  : [ callback, ... ]
        'frame_removed'         : [  ],
        }

    __handle_sz = max(
        gtk.HPaned().style_get_property('handle-size'),
        gtk.VPaned().style_get_property('handle-size')
        )

    def __init__(self,
                 frame = zEdit, frame_alist = [],
                 frame_init = None,
                 frame_split_dup = None,
                 frame_sz_min = (50, 50)
                 ):
        '''
        frame = zEdit
            a construction function of a GtkWidget which will be
            the frame of the inner window.

            e.g. comp.zSplitScreen(gtk.Label)

        frame_alist = []
            the argument list of the "frame".

            e.g. comp.zSplitScreen(gtk.Label, ['Test Label'])

        frame_init = None
            a callback function that will be called after every
            creation of the "frame" to initialize it
            (connect signals, for example)

            if set to None, no action will applied

            the callback function should be:
                def callback(frame):
                    ...

        frame_split_dup = None
            a callback function that will be called after every
            split of the screen to duplicate the original "frame"

            if set to None, a default "frame" will be created

            the callback function should be:
                def callback(frame):
                    ...
                    return new_frame

        frame_sz_min
            the minimum size required for each "frame"
        '''
        super(zSplitScreen, self).__init__()


        self.frame = frame
        self.frame_alist = frame_alist
        self.frame_init = frame_init
        self.frame_split_dup = frame_split_dup
        self.frame_sz_min = frame_sz_min

        # layout of the zSplitScreen:
        # 
        #   0 1          2 3
        # 0 +-+----------+-+ 0
        #   | |    tp    | |
        # 1 +-+----------+-+ 1
        #   | |          | |
        #   | |          | |
        #   |l|    mw    |r|
        #   |t|          |t|
        #   | |          | |
        #   | |----------| |
        # 2 +-+----------+-+ 2
        #   | |    bm    | |
        # 3 +-+----------+-+ 3
        #   0 1          2 3

        root_frame = gtk.Table(3, 3, False)
        self.add(root_frame)

        self.sd_layer = None    # init shading-layer to None

        self.__ctrl_pos = {
            'a' : ( 'lt', 'rt', 'tp', 'bm', ), # all
            'b' : ( 'lt',       'tp',       ), # begin
            'e' : (       'rt',       'bm', ), # end
            'h' : ( 'lt', 'rt',             ), # horizontal
            'v' : (             'tp', 'bm', ), # vertical
            }
        self.ctrl_bar = {}
        self.ctrl_bar['lt'] = gtk.Button()
        self.ctrl_bar['rt'] = gtk.Button()
        self.ctrl_bar['tp'] = gtk.Button()
        self.ctrl_bar['bm'] = gtk.Button()
        self.mw_center = gtk.Frame()
        frame = self.new_frame(self.frame_alist) # keep track of the focus
        self.mw_center.add(frame)

        # remove shadow
        self.set_shadow_type(gtk.SHADOW_NONE)
        self.mw_center.set_shadow_type(gtk.SHADOW_NONE)

        root_frame.attach(self.ctrl_bar['lt'], 0, 1, 1, 2, xoptions=gtk.SHRINK)
        root_frame.attach(self.ctrl_bar['rt'], 2, 3, 1, 2, xoptions=gtk.SHRINK)
        root_frame.attach(self.ctrl_bar['tp'], 1, 2, 0, 1, yoptions=gtk.SHRINK)
        root_frame.attach(self.ctrl_bar['bm'], 1, 2, 2, 3, yoptions=gtk.SHRINK)
        root_frame.attach(self.mw_center,      1, 2, 1, 2)

        # connect signals for control-bars
        drag_icon = gtk.gdk.pixbuf_new_from_file(
            os.path.join(os.path.dirname(__file__), "image", "min_empty.gif")
            )
        for pos in self.__ctrl_pos['a']:
            self.ctrl_bar[pos].set_property('can-default', False)
            self.ctrl_bar[pos].set_property('can-focus', False)
            self.ctrl_bar[pos].connect_object('clicked', self.add_paned, self.mw_center, pos)
            self.ctrl_bar[pos].drag_source_set(gtk.gdk.BUTTON1_MASK, [], 0)
            self.ctrl_bar[pos].connect('drag_begin', self._sig_ctrl_drag, drag_icon, pos)
            self.ctrl_bar[pos].connect('button-release-event', self._sig_ctrl_drop, pos)


    ### signal for DnD
    def _sig_ctrl_drag(self, widget, context, icon, pos):
        context.set_icon_pixbuf(icon, 0, 0)

        # create the shading-layer
        root = widget.get_root_window()
        screen = gtk.gdk.screen_get_default()

        alloc = self.mw_center.get_allocation()
        self.sd_w = alloc.width
        self.sd_h = alloc.height
        if SUPPORT['rgba']:
            visual = screen.get_rgba_visual()
            colormap = screen.get_rgba_colormap()
        else:
            if pos in self.__ctrl_pos['h']:
                self.sd_w = self.__handle_sz
            else:
                self.sd_h = self.__handle_sz
            visual = screen.get_rgb_visual()
            colormap = screen.get_rgb_colormap()

        self.sd_layer = gtk.gdk.Window(
            root, self.sd_w, self.sd_h,
            gtk.gdk.WINDOW_TEMP,
            gtk.gdk.ALL_EVENTS_MASK,
            gtk.gdk.INPUT_OUTPUT,
            '', 0, 0,
            visual, colormap, gtk.gdk.Cursor(gtk.gdk.PLUS),
            '', '', True
            )
        self.sd_layer.show()

        # create the cairo context
        self.sd_layer_cr = self.sd_layer.cairo_create()

        self.sd_layer_cr.set_line_width(1)
        # set shade color
        sd_fg_rgb = [ int(zTheme.color_map['text'][i:i+2], 16) / 255.0 # scale hex color code to [0, 1]
                      for i in [ 1, 3, 5 ] # starting index in pattern '#rrggbb'
                      ]
        sd_bg_rgb = [ int(zTheme.color_map['base'][i:i+2], 16) / 255.0 # scale hex color code to [0, 1]
                      for i in [ 1, 3, 5 ] # starting index in pattern '#rrggbb'
                      ]
        if SUPPORT['rgba']:
            alpha = 0.3
            self.sd_layer_cr.set_source_rgba(* (sd_fg_rgb + [ alpha ]))
        else:
            alpha = 0.5
            self.sd_layer_cr.set_source_rgb(* [ sd_fg_rgb[i] * alpha + sd_bg_rgb[i] * (1 - alpha) for i in range(3) ])

        # start the timer
        self.mw_center.timer = True
        gobject.timeout_add(20, self.update_sd, pos)

    def _sig_ctrl_drop(self, widget, event, pos):
        # remove the shading-layer
        if self.sd_layer:
            self.sd_layer.destroy()
            self.sd_layer = None

        # stop the timer
        self.mw_center.timer = False

        # calculate position
        alloc = self.mw_center.get_allocation()
        ptr_pos = self.mw_center.get_pointer()

        correct_pos = self.__correct_pos(
            ptr_pos,                              # the current ptr pos
            (0, 0),                               # the frame size - low bound
            (alloc.width, alloc.height),          # the frame size - high bound
            [sp + 20 for sp in self.frame_sz_min] # the min spacing + 20
            )

        # add paned if in center
        if correct_pos:
            paned = self.add_paned(self.mw_center, pos)

            # re-position the newly added frame
            if pos in self.__ctrl_pos['h']:
                # - handle_sz cancel the width of the divider
                paned.set_position(correct_pos[0] - self.__handle_sz / 2)
            else:
                paned.set_position(correct_pos[1] - self.__handle_sz / 2)
    ### end of signal for DnD

    ### signal for center frame
    def _sig_div_drop(self, widget, event):
        for child in widget.get_children():
            alloc = child.get_allocation()
            if ( alloc.width < self.frame_sz_min[0] or
                 alloc.height < self.frame_sz_min[1]
                 ):
                # record focus
                focus = self.active_frame() # get focused frame
                if self.__active_frame(child):
                    focus = None # focus in child_rm, delete it

                # remove the child
                self.rm_frame(widget, child)

                # adjust focus
                if not focus:
                    self.grab_focus()
                else:
                    focus.grab_focus()
                break
    ### end of signal for center frame


    ### overridden function definition
    @classmethod
    def register(cls, sig, callback):
        '''This function register a function to a signal-like string'''
        cls._auto_update[sig].append(callback)

    @classmethod
    def unregister(cls, sig, callback):
        '''This function un-register a function from a signal-like string'''
        reserve = []
        for cb in cls._auto_update[sig]:
            if callback != cb:
                reserve.append(cb)
        cls._auto_update[sig] = reserve

    @classmethod
    def emit(cls, sig):
        '''This function emit the signal to all registered object'''
        for cb in cls._auto_update[sig]:
            cb()

    def is_focus(self):
        return self.active_frame() != None

    def grab_focus(self):
        child = self.mw_center.child
        while not isinstance(child, self.frame):
            child = child.get_children()[0]
        child.grab_focus()
    ### end of overridden function definition


    def active_frame(self):
        return self.__active_frame(self.mw_center)

    def add_paned(self, parent, pos):
        child = parent.child

        # create new paned
        if pos in self.__ctrl_pos['h']:
            paned = gtk.HPaned()
        else:
            paned = gtk.VPaned()

        # create new frame
        if self.frame_split_dup:
            new_child = self.new_frame_on_dup()
        else:
            new_child = self.new_frame(self.frame_alist)

        # re-parent the widgets
        parent.remove(child)
        if pos in self.__ctrl_pos['b']:
            paned.pack1(new_child, True, True)
            paned.pack2(child, True, True)
        else:
            paned.pack1(child, True, True)
            paned.pack2(new_child, True, True)
        parent.add(paned)

        # connect signals
        paned.connect('button-release-event', self._sig_div_drop)

        # show widgets
        parent.show_all()
        new_child.grab_focus()

        return paned

    def new_frame(self, alist):
        # prepare frame info
        frame = self.frame(* alist)

        frame.set_init_func(self.frame_init)
        frame.exec_init_func()

        return frame

    def new_frame_on_dup(self):
        # prepare frame info
        frame = self.frame_split_dup(self.active_frame())

        frame.set_init_func(self.frame_init)
        frame.exec_init_func()

        return frame

    def rm_frame(self, widget, child_rm):
        if widget == self.mw_center:    # the only frame
            widget.remove(child_rm)
            widget.add(self.new_frame())

            # clean up
            child_rm.hide_all()
            zSplitScreen.emit('frame_removed')
            return              # early return

        # not the only frame, get parent and child info
        parent = widget.get_parent()
        if child_rm == widget.get_child1():
            child_kp = widget.get_child2() 
        else:
            child_kp = widget.get_child1() 

        # remove both child
        widget.remove(child_rm)
        widget.remove(child_kp)

        if parent == self.mw_center:    # parent is mw_center
            parent.remove(widget)
            parent.add(child_kp)
        else:                           # parent is paned
            if widget == parent.get_child1():
                add_cmd = 'parent.pack1(child_kp, True, True)'
            else:
                add_cmd = 'parent.pack2(child_kp, True, True)'
            parent.remove(widget)
            eval(add_cmd)

        # clean up
        child_rm.hide_all()
        zSplitScreen.emit('frame_removed')


    def update_sd(self, pos):
        if not self.mw_center.timer:
            return False

        # calculate position
        root = self.mw_center.get_root_window()
        alloc = self.mw_center.get_allocation()
        ( ptr_x,     ptr_y     ) = self.mw_center.get_pointer()
        ( ptr_abs_x, ptr_abs_y ) = root.get_pointer()[:2]
        ( base_x,    base_y    ) = ( ptr_abs_x - ptr_x, ptr_abs_y - ptr_y )

        # validate position
        correct_pos = self.__correct_pos(
            (ptr_x, ptr_y),                       # the current ptr pos
            (0, 0),                               # the frame size - low bound
            (alloc.width, alloc.height),          # the frame size - high bound
            [sp + 10 for sp in self.frame_sz_min] # the min spacing + 10
            )

        if correct_pos:
            self.sd_layer.show()
        else:
            self.sd_layer.hide()
            return True

        # draw on shading-layer
        if SUPPORT['rgba']:
            if pos == 'lt':
                self.sd_layer.move_resize(base_x,    base_y,    ptr_x,             self.sd_h        )
            elif pos == 'tp':
                self.sd_layer.move_resize(base_x,    base_y,    self.sd_w,         ptr_y            )
            elif pos == 'rt':
                self.sd_layer.move_resize(ptr_abs_x, base_y,    self.sd_w - ptr_x, self.sd_h        )
            else:
                self.sd_layer.move_resize(base_x,    ptr_abs_y, self.sd_w,         self.sd_h - ptr_y)
        else:
            if pos in self.__ctrl_pos['h']:
                self.sd_layer.move(ptr_abs_x - self.sd_w / 2, base_y)
            else:
                self.sd_layer.move(base_x, ptr_abs_y - self.sd_h / 2)

        self.sd_layer_cr.rectangle(0, 0, self.sd_w, self.sd_h)
        self.sd_layer.clear()
        self.sd_layer_cr.fill()


        return True


    ### supporting function
    def __active_frame(self, current):
        '''recursive function, should start with zSplitScreen.mw_center'''
        if isinstance(current, self.frame):
            if current.is_focus():
                return current  # found the frame
            else:
                return None     # end of the path

        for child in current.get_children():
            found = self.__active_frame(child)
            if found:
                return found    # found in previous search
        return None             # not found at all

    def __correct_pos(self, pos, limit_low, limit_high, spacing):
        '''all three args should all be tuples/lists with the same length'''
        ct_pos = [None] * len(pos)
        for i in range(len(pos)):
            if pos[i] < limit_low[i] or pos[i] > limit_high[i]:
                return None

            if pos[i] < limit_low[i] + spacing[i]:
                ct_pos[i] = limit_low[i] + spacing[i]
            elif pos[i] > limit_high[i] - spacing[i]:
                ct_pos[i] = limit_high[i] - spacing[i]
            else:
                ct_pos[i] = pos[i]
        return ct_pos
    ### end of supporting function


######## ######## ######## ########
########      zTheme       ########
######## ######## ######## ########

class zTheme(z_ABC):
    '''The Theme Control Class Used by z* Classes'''
    font = {
        'name' : 'Monospace',
        'size' : 12,
        }
    color_map = {
        # reguler
        'text'          : '#000000', # black
        'text_selected' : '#000000', # black
        'base'          : '#FBEFCD', # wheat - mod
        'base_selected' : '#FFA500', # orenge
        'status'        : '#808080', # gray
        'status_active' : '#C0C0C0', # silver
        # highlight
        'reserve'       : '#0000FF', # blue
        'comment'       : '#008000', # green
        'literal'       : '#FF0000', # red
        'label'         : '#808000', # olive
        }


    _auto_update = {
        # 'signal_like_string'  : [ (widget, callback, data_list), ... ]
        'update_font'           : [  ],
        'update_color_map'      : [  ],
        }

    ### signal-like auto-update function
    @staticmethod
    def _sig_update_font_modify(widget, weight = 1):
        widget.modify_font(
            pango.FontDescription('{0} {1}'.format(zTheme.font['name'], int(zTheme.font['size'] * weight)))
            )

    @staticmethod
    def _sig_update_font_property(widget, weight = 1):
        widget.set_property(
            'font-desc',
            pango.FontDescription('{0} {1}'.format(zTheme.font['name'], int(zTheme.font['size'] * weight)))
            )
    ### end of signal-like auto-update function


    @staticmethod
    def get_font():
        return zTheme.font

    @staticmethod
    def set_font(dic):
        modified = False
        for (k, v) in dic.items():
            if k in zTheme.font and v != zTheme.font[k]:
                modified = True
                zTheme.font[k] = v
        if modified:
            zTheme.emit('update_font')

    @staticmethod
    def get_color_map():
        return zTheme.color_map

    @staticmethod
    def set_color_map(dic):
        modified = False
        for (k, v) in dic.items():
            if k in zTheme.color_map and v != zTheme.color_map[k]:
                modified = True
                zTheme.color_map[k] = v
        if modified:
            zTheme.emit('update_color_map')


######## ######## ######## ######## 
########    MODULE INIT    ######## 
######## ######## ######## ######## 

# change gtk settings
settings = gtk.settings_get_default()
settings.set_property('gtk-show-input-method-menu', False)
settings.set_property('gtk-show-unicode-menu', False)

# set default theme
gtk.rc_parse_string('''
style 'zTheme' {
    GtkButton::focus-line-width = 0
    GtkButton::focus-padding = 0

    GtkComboBox::appears-as-list = 1

    GtkPaned::handle-size = 8
}
widget '*' style 'zTheme'
''')

# open default buffers
for buff_name, buff_type in zEditBuffer.SYSTEM_BUFFER.items():
    zEditBuffer(buff_name, buff_type)
