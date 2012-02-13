# this is the widget module of the zComponent package

from zBase import z_ABC

import os, sys, stat, time, copy, re
import pygtk
pygtk.require('2.0')
import gtk
import gobject, pango


######## ######## ######## ######## ########
########       zButton Family       ########
######## ######## ######## ######## ########
class zButton(gtk.Button):
    '''A gtk.Button that has additional methods'''
    def __init__(self, *arg):
        super(zButton, self).__init__(*arg)

    def __getattr__(self, name):
        if name == 'label':
            self.label = self.get_label_widget()
            return self.label

    ### overridden function definition
    def get_label_widget(self, current = None):
        if current == None:
            current = self

        try:
            if not len(current.get_children()):
                raise AttributeError
        except:
            if isinstance(current, gtk.Label):
                return current  # found the label
            else:
                return None     # end of the path

        for child in current.get_children():
            found = self.get_label_widget(child)
            if found:
                return found    # found in previous search
        return None             # not found at all

    def set_label_widget(self, label_widget):
        raise NotImplementedError('method not implemented!')


    def modify_font(self, font_desc):
        self.label.modify_font(font_desc)

    def modify_fg(self, state, color):
        self.label.modify_fg(state, color)
    ### overridden function definition

class zCheckButton(zButton, gtk.CheckButton):
    '''A gtk.CheckButton that has additional methods'''
    def __init__(self, *arg):
        super(zCheckButton, self).__init__(*arg)

class zRadioButton(zButton, gtk.RadioButton):
    '''A gtk.RadioButton that has additional methods'''
    def __init__(self, *arg):
        super(zRadioButton, self).__init__(*arg)

class zToggleButton(zButton, gtk.ToggleButton):
    '''A gtk.ToggleButton that has additional methods'''
    def __init__(self, *arg):
        super(zToggleButton, self).__init__(*arg)

class zToolButton(zButton):
    '''A flat ToolButton that can be embeded into, say, a Status Bar'''
    def __init__(self, label = ''):
        super(zToolButton, self).__init__(label)

        # internal (backup) variables
        self.set_label(label)
        self.__n_chars = -1
        self.__font_desc = None

        # set style to flat
        rcstyle = self.get_modifier_style()
        rcstyle.xthickness = 0  # no horizontal padding
        rcstyle.ythickness = 2  # set vertical padding to 2 pixels
        self.modify_style(rcstyle)

        self.set_relief(gtk.RELIEF_NONE)

        # set focus policy
        self.set_property('can-default', False)
        self.set_property('can-focus', False)


    ### overridden function definition
    def get_label(self):
        return self.__label

    def set_label(self, label):
        self.__label = label
        if self.__n_chars > 0:
            self.label.set_text('{0:<{1}}'.format(self.__label, self.__n_chars))
        else:
            self.label.set_text(label)

    def get_width_chars(self):
        return self.__n_chars

    def set_width_chars(self, n_chars):
        self.__n_chars = n_chars
        self.set_label(self.__label) # refresh label
        self.resize()


    def modify_font(self, font_desc):
        self.label.modify_font(font_desc)
        self.__font_desc = font_desc

        self.resize()


    def resize(self):
        if self.__n_chars < 0:
            return              # n_char not set

        pango_layout = self.label.create_pango_layout('w')
        pango_layout.set_font_description(self.__font_desc)

        ( char_w, char_h ) = pango_layout.get_pixel_size()

        self.set_size_request(char_w * self.__n_chars + 2, -1) # 2 for the border of the button itself
    ### overridden function definition


######## ######## ######## ######## ########
########        zColorPicker        ########
######## ######## ######## ######## ########

class zColorPicker(gtk.Table):
    '''A Firefox Style Color Picker'''
    default_color_matrix = [    # The one that FireFox is using
        [ '#FFFFFF', '#FFCCCC', '#FFCC99', '#FFFF99', '#FFFFCC', '#99FF99', '#99FFFF', '#CCFFFF', '#CCCCFF', '#FFCCFF', ],
        [ '#CCCCCC', '#FF6666', '#FF9966', '#FFFF66', '#FFFF33', '#66FF99', '#33FFFF', '#66FFFF', '#9999FF', '#FF99FF', ],
        [ '#C0C0C0', '#FF0000', '#FF9900', '#FFCC66', '#FFFF00', '#33FF33', '#66CCCC', '#33CCFF', '#6666CC', '#CC66CC', ],
        [ '#999999', '#CC0000', '#FF6600', '#FFCC33', '#FFCC00', '#33CC00', '#00CCCC', '#3366FF', '#6633FF', '#CC33CC', ],
        [ '#666666', '#990000', '#CC6600', '#CC9933', '#999900', '#009900', '#339999', '#3333FF', '#6600CC', '#993399', ],
        [ '#333333', '#660000', '#993300', '#996633', '#666600', '#006600', '#336666', '#000099', '#333399', '#663366', ],
        [ '#000000', '#330000', '#663300', '#663333', '#333300', '#003300', '#003333', '#006666', '#330099', '#330033', ],
        ]

    n_row = 7                   # number of rows in the above matrix
    n_col = 10                  # number of columns in the above matrix

    def __init__(self, callback):
        '''
        callback
            the callback function to be invoked when a color
            has been picked

            should be defined as:
                def callback(widget, color_code)
        '''
        super(zColorPicker, self).__init__(zColorPicker.n_row, zColorPicker.n_col, True)


        self.callback = callback
        self.__size_button = [ 30, 25 ]


        # build the matrix
        self.bttn_matrix = []
        for row in range(zColorPicker.n_row):
            self.bttn_matrix.append([])

            for col in range(zColorPicker.n_col):
                bttn = gtk.Button('')
                self.bttn_matrix[row].append(bttn)

                bttn.frame = gtk.Frame()
                bttn.color_code = zColorPicker.default_color_matrix[row][col]

                color = gtk.gdk.color_parse(bttn.color_code)
                style = bttn.get_style().copy()
                style.bg[gtk.STATE_NORMAL] = color
                style.bg[gtk.STATE_PRELIGHT] = color
                bttn.set_style(style)

                bttn.frame.add(bttn)
                self.attach(bttn.frame, col, col + 1, row, row + 1)

                bttn.sig_id_click = bttn.connect('clicked', self._sig_bttn_clicked)
                bttn.sig_id_enter = bttn.connect('enter', self._sig_bttn_enter)
                bttn.sig_id_leave = bttn.connect('leave', self._sig_bttn_leave)
                self._sig_bttn_leave(bttn)

        self.set_size_button(* self.get_size_button())


    ### signal definition
    def _sig_bttn_clicked(self, bttn):
        self.callback(bttn.color_code)

    def _sig_bttn_enter(self, bttn):
        bttn.frame.set_shadow_type(gtk.SHADOW_OUT)

    def _sig_bttn_leave(self, bttn):
        bttn.frame.set_shadow_type(gtk.SHADOW_NONE)
    ### end of signal definition

    def clean_up(self):
        for line in self.bttn_matrix:
            for bttn_frame in line:
                bttn = bttn_frame.child
                bttn.disconnect(bttn.sig_id_click)
                bttn.disconnect(bttn.sig_id_enter)
                bttn.disconnect(bttn.sig_id_leave)


    def get_size_button(self):
        return self.__size_button

    def set_size_button(self, w, h):
        mod = False

        if w != -1:
            mod = True
            self.__size_button[0] = w
        if h != -1:
            mod = True
            self.__size_button[1] = h

        if mod:
            for line in self.bttn_matrix:
                for bttn in line:
                    bttn.set_size_request(* self.__size_button)


######## ######## ######## ######## ########
########     zColorPickerButton     ########
######## ######## ######## ######## ########

class zColorPickerButton(gtk.Frame):
    '''A Firefox Style Color Picker Button'''
    def __init__(self, active_scope, callback):
        '''
        active_scope
            the GtkEventBox widget that defines the active
            scope of the menu-popdown-on-click

        callback
            the callback function to be invoked when a color
            has been picked

            should be defined as:
                def callback(widget, color_code)
        '''
        super(zColorPickerButton, self).__init__()


        self.bttn = gtk.Button('')
        self.bttn.frame = self
        self.add(self.bttn)

        self.active_scope = active_scope
        self.callback = callback
        self.toplevel = self.active_scope.get_toplevel()

        self.__size_button = [ 45, 25 ]
        self.__size_menu_button = [ 30, 25 ]

        # create the popup menu
        self.menu = gtk.Window(gtk.WINDOW_POPUP)

        self.menu.set_transient_for(self.toplevel)
        self.menu.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_MENU)
        self.menu.set_destroy_with_parent(True)

        self.build_menu(rebuild = False)

        # connect signals
        self.active_scope.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.top_id = {
            'as' : [
                self.active_scope.connect('button-press-event', self._sig_popdown),
                ],
            'tl' : [
                self.toplevel.connect('configure-event', self._sig_popdown),
                self.toplevel.connect('focus-out-event', self._sig_popdown),
                self.toplevel.connect('window-state-event', self._sig_popdown),
                ],
            }
        self.bttn.connect('clicked', self._sig_popup)
        self.bttn.connect('enter', self._sig_bttn_enter)
        self.bttn.connect('leave', self._sig_bttn_leave)
        self._sig_bttn_leave(self.bttn)

        self.popdown()
        self.set_size_button(* self.get_size_button())
        self.set_size_menu_button(* self.get_size_menu_button())


    ### signal definition
    def _sig_popup(self, bttn):
        if self.is_shown:
            self.popdown()
        else:
            self.popup()

    def _sig_popdown(self, widget, event):
        self.popdown()
        return True


    def _sig_bttn_enter(self, bttn):
        bttn.frame.set_shadow_type(gtk.SHADOW_OUT)

    def _sig_bttn_leave(self, bttn):
        bttn.frame.set_shadow_type(gtk.SHADOW_NONE)
    ### end of signal definition


    ### overridden function definition
    def popup(self):
        self.is_shown = True

        # calculate position
        root = self.get_root_window()
        alloc = self.get_allocation()
        ( ptr_x,     ptr_y     ) = self.get_pointer()
        ( ptr_abs_x, ptr_abs_y ) = root.get_pointer()[:2]
        ( base_x,    base_y    ) = ( ptr_abs_x - ptr_x, ptr_abs_y - ptr_y )

        # popup the menu
        self.menu.show_all()
        bttn_alloc = self.color_picker.bttn_matrix[0][-1].get_allocation()
        self.menu.move(
            min(base_x, root.get_size()[0] - bttn_alloc.x - bttn_alloc.width),
            base_y + alloc.height
            )

        for handler in self.top_id['as']:
            self.active_scope.handler_unblock(handler)
        for handler in self.top_id['tl']:
            self.toplevel.handler_unblock(handler)
        self.active_scope.set_above_child(True)

    def popdown(self):
        for handler in self.top_id['as']:
            self.active_scope.handler_block(handler)
        for handler in self.top_id['tl']:
            self.toplevel.handler_block(handler)
        self.active_scope.set_above_child(False)

        self.menu.hide_all()
        self.is_shown = False

    def modify_bg(self, state, color):
        style = self.bttn.get_style().copy()
        style.bg[state] = color
        self.bttn.set_style(style)
    ### end of overridden function definition


    def build_menu(self, rebuild = True):
        if rebuild:
            # clean up
            self.color_picker.clean_up()
            self.menu.remove(self.color_picker)

        # build the menu
        self.color_picker = zColorPicker(self.menu_bttn_clicked)
        self.menu.add(self.color_picker)


    def menu_bttn_clicked(self, color_code):
        self.callback(self, color_code)
        self.popdown()


    def get_size_button(self):
        return self.__size_button

    def set_size_button(self, w, h):
        mod = False

        if w != -1:
            mod = True
            self.__size_button[0] = w
        if h != -1:
            mod = True
            self.__size_button[1] = h

        if mod:
            self.bttn.set_size_request(* self.__size_button)


    def get_size_menu_button(self):
        return self.color_picker.get_size_button()

    def set_size_menu_button(self, w, h):
        self.color_picker.set_size_button(w, h)


######## ######## ######## ######## ########
########         zKillRing          ########
######## ######## ######## ######## ########
class zKillRing(object):
    '''the kill-ring widget'''
    @classmethod
    def __init_kill_ring(cls):
        cls.__curr_corpse = None # for pop (resurrect)
        cls.__curr_grave  = 0    # for push (kill)

        cls.__kill_ring = [ None ] * cls.__capacity


    __capacity  = 16

    # the following should be exactly the same as cls.__init_kill_ring()
    __curr_corpse = None        # for pop (resurrect)
    __curr_grave  = 0           # for push (kill)

    __kill_ring = [ None ] * __capacity
    # the above should be exactly the same as cls.__init_kill_ring()

    __cb = {
        'primary'   : gtk.clipboard_get('PRIMARY'),
        'clipboard' : gtk.clipboard_get('CLIPBOARD'),
        }

    # record the current clipboards' content
    __cb_text = {
        'primary'   : __cb['primary'].wait_for_text(),
        'clipboard' : __cb['clipboard'].wait_for_text(),
        }


    @classmethod
    def is_empty(cls):
        return None == cls.__curr_corpse


    @classmethod
    def get_kill_ring_size(cls):
        return cls.__capacity

    @classmethod
    def set_kill_ring_size(cls, size):
        cls.__capacity  = size
        cls.__init_kill_ring()


    @classmethod
    def append_killing(cls, text):
        if cls.__kill_cb():     # successfully pushed whatever in the clipboard into the kill ring
            cls.kill(text)      # chain has been broken, no appending occur
        else:
            cls.__curr_grave = cls.__curr_corpse # kick out the last corpse
            cls.kill(cls.__kill_ring[cls.__curr_corpse] + text) # kill the appended version

    def prepend_killing(cls, text):
        if cls.__kill_cb():     # successfully pushed whatever in the clipboard into the kill ring
            cls.kill(text)      # chain has been broken, no prepending occur
        else:
            cls.__curr_grave = cls.__curr_corpse # kick out the last corpse
            cls.kill(text + cls.__kill_ring[cls.__curr_corpse]) # kill the prepended version

    @classmethod
    def kill(cls, text):
        cls.__kill_cb()                      # push whatever in the clipboard if the content has been changed
        cls.__cb['clipboard'].set_text(text) # push the text into system clipboard
        while cls.__cb['clipboard'].wait_for_text() != text:
            continue            # wait for system clipboard to sync
        cls.__kill_cb()         # push the just-added clipboard content into the kill ring

    @classmethod
    def resurrect(cls):
        cls.__kill_cb()                      # push whatever in the clipboard if the content has been changed

        if cls.is_empty():
            # kill-ring is empty, or clipboards' content changed
            if cls.__cb_text['primary']:
                # put primary clipboard text into kill-ring
                cls.kill(cls.__cb_text['primary'])

            elif cls.__cb_text['clipboard']:
                # put clipboard text into kill-ring
                cls.kill(cls.__cb_text['clipboard'])

        if cls.is_empty():
            return None
        else:
            return cls.__kill_ring[cls.__curr_corpse]

    @classmethod
    def circulate_resurrection(cls):
        if not cls.is_empty():
            # only if kill-ring is not empty
            cls.__curr_corpse = (cls.__curr_corpse - 1) % cls.__capacity
            while not cls.__kill_ring[cls.__curr_corpse]:
                # skip empty slot
                cls.__curr_corpse = (cls.__curr_corpse - 1) % cls.__capacity

            return cls.resurrect()  # ought to contain something from kill-ring, not from clipboard
        else:
            return None


    ### supporting functions
    @classmethod
    def __really_kill(cls, text):
        if text:
            cls.__kill_ring[cls.__curr_grave] = text

            # update indices
            cls.__curr_corpse = cls.__curr_grave
            cls.__curr_grave  = (cls.__curr_grave + 1) % cls.__capacity

            return True         # kill +1
        else:
            return False        # kill nothing

    @classmethod
    def __kill_cb(cls):
        c_text = cls.__cb['clipboard'].wait_for_text()

        if cls.__cb_text['clipboard'] != c_text:
            # check clipboard first
            killed = cls.__really_kill(c_text)  # try killing the new content
            cls.__cb_text['clipboard'] = c_text # synchronize the backup
        else:
            killed = False

        p_text = cls.__cb['primary'].wait_for_text()

        if not killed and cls.__cb_text['primary'] != p_text:
            # if no kill for clipboard, check primary
            killed = cls.__really_kill(p_text)  # try killing the new content
            cls.__cb_text['primary'] = p_text   # synchronize the backup

        return killed
    ### end of supporting functions


######## ######## ######## ######## ########
########         zPopupMenu         ########
######## ######## ######## ######## ########

class zPopupMenu(gtk.Menu):
    def __init__(self):
        super(zPopupMenu, self).__init__()

        self.popdown_cb      = None
        self.popdown_cb_args = ()

        self.set_property('reserve-toggle-size', False)

        self.__reset_w_arg()


    def register_popdown_cb(self, callback, *data):
        self.popdown_cb      = callback
        self.popdown_cb_args = data

    def popdown(self):
        if self.popdown_cb:
            self.popdown_cb(* self.popdown_cb_args)
        super(zPopupMenu, self).popdown()

    def popup_given(self, attached_widget, w_alloc = None):
        '''
        attached_widget
            the widget that popups this menu

        w_allco = None
            a list of (x, y, width, height) that describes the geometry
            of the attached widget. they are:
              - x       x displacement of the menu into attached_widget
              - y       y displacement of the menu into attached_widget
              - width   width of attached_widget
              - height  height of attached_widget

            if not set, the position will be decided by
              ( 0, 0,
                attached_widget.get_allocation().width,
                attached_widget.get_allocation().height
                )
        '''
        # retrieve info for the attached widget
        self.__attached_widget = attached_widget

        if w_alloc:
            self.__w_x      = w_alloc[0]
            self.__w_y      = w_alloc[1]
            self.__w_width  = w_alloc[2]
            self.__w_height = w_alloc[3]
        else:
            alloc = attached_widget.get_allocation()
            self.__w_x      = 0
            self.__w_y      = 0
            self.__w_width  = alloc.width
            self.__w_height = alloc.height

        # popup the menu according to the given info
        self.popup(None, None, self.__menu_position_below_or_above, 1, 0)
        self.__reset_w_arg()


    ### supporting function
    def __menu_position_below_or_above(self, menu):
        # calculate request height
        h_req = menu.get_style().ythickness * 2
        for mi in menu.get_children():
            h_req += mi.size_request()[1]

        # calculate position
        toplevel = self.__attached_widget.get_toplevel()
        root     = self.__attached_widget.get_root_window()

        ( ptr_x,     ptr_y     ) = self.__attached_widget.get_pointer()
        ( ptr_rel_x, ptr_rel_y ) = toplevel.get_pointer() # reletive position to toplevel
        ( ptr_abs_x, ptr_abs_y ) = root.get_pointer()[:2] # absolute position to root

        ( top_x,  top_y  ) = (ptr_abs_x - ptr_rel_x,          ptr_abs_y - ptr_rel_y         ) # top-left coords of toplevel
        ( base_x, base_y ) = (ptr_abs_x - ptr_x + self.__w_x, ptr_abs_y - ptr_y + self.__w_y) # top-left coords of widget

        # check room
        room_below = root.get_size()[1] - base_y - self.__w_height
        room_above = base_y - top_y # should not go above the top border of the toplevel

        menu.set_size_request(self.__w_width, -1)

        if h_req >= room_below and room_above > room_below:
            # not enough room below, and room above is larger then room below
            # pop above
            if room_above < h_req:
                menu.set_size_request(self.__w_width, room_above) # limit the height of the menu
                return base_x, top_y, False
            else:
                return base_x, base_y - h_req, False
        else:
            # room below is enough, or larger then room above
            # pop below
            return base_x, base_y + self.__w_height, False


    def __reset_w_arg(self):
        self.__attached_widget = None

        self.__w_x      = 0
        self.__w_y      = 0
        self.__w_height = -1
        self.__w_width  = -1
    ### end of supporting function


######## ######## ######## ######## ########
########         zComboBox          ########
######## ######## ######## ######## ########

class zComboBox(z_ABC, zToolButton):
    '''A Flat (Inline) ComboBox'''
    _auto_update = {
        # 'signal_like_string'  : [ (widget, callback, data_list), ... ]
        'changed'               : [  ],
        }
    def __init__(self):
        super(zComboBox, self).__init__()

        # init item list
        self.__item_list = [
            # [ col_0, col_1, ... ]
            #  ...
            ]
        self.active_item = None
        self.effective_column = 0
        self.row_separator_func = None

        # init menu
        self.menu = None
        self.color_fg = {}      # state : color
        self.color_bg = {}      # state : color

        # set style
        self.set_border_width(0)
        self.set_property('can-default', False)
        self.set_property('can-focus', False)
        self.child.set_alignment(0, 0.5) # set text alignment on button

        # connect signals
        self.connect('clicked', self._sig_combo_clicked)

    ### signal definition
    def _sig_combo_clicked(self, widget):
        self.popup()

    def _sig_item_selected(self, widget, indx):
        self.popdown()

        if self.active_item == indx:
            return              # no need to change, early return

        self.set_active_indx(indx)
    ### end of signal definition


    ### overridden function definition
    def insert(self, indx, item):
        self.__item_list.insert(indx, item)
        if self.active_item == None:
            self.set_active_indx(indx)
        zComboBox.reg_emit_to('changed', self)

    def prepend(self, item):
        self.insert(0, item)

    def append(self, item):
        self.insert(len(self.__item_list), item)

    def reorder(self, new_order):
        item_list = []
        for indx in new_order:
            item_list.append(self.__item_list[indx])
        self.__item_list = item_list
        self.active_item = new_order.index(self.active_item)

    def move_after(self, src_indx, dest_indx):
        if src_indx >= dest_indx:
            dest_indx += 1
        self.insert(dest_indx, self.__item_list.pop(src_indx))

    def move_before(self, src_indx, dest_indx):
        if src_indx >= dest_indx:
            dest_indx -= 1
        self.insert(dest_indx, self.__item_list.pop(src_indx))

    def remove(self, indx):
        self.__item_list.pop(indx)
        if indx == self.active_item:
            self.set_active(None)
        zComboBox.reg_emit_to('changed', self)

    def clear(self):
        self.__item_list = []
        self.set_active(None)
        zComboBox.reg_emit_to('changed', self)

    def index(self, item):
        try:
            return self.__item_list.index(item)
        except:
            return None


    def modify_fg(self, state, color):
        super(zComboBox, self).modify_fg(state, color)
        self.color_fg[state] = color

    def modify_bg(self, state, color):
        super(zComboBox, self).modify_bg(state, color)
        self.color_bg[state] = color


    def popup(self):
        # create the menu
        self.menu = zPopupMenu()

        # fill the menu
        for indx in range(len(self.__item_list)):
            item = self.__item_list[indx]

            if self.row_separator_func and self.row_separator_func(item):
                self.menu.append(gtk.SeparatorMenuItem())
            else:
                mi = gtk.MenuItem(item[self.effective_column], False)
                self.menu.append(mi)
                mi.connect('activate', self._sig_item_selected, indx)

                # modify the text and background color of each menu item
                for (k, v) in self.color_fg.iteritems():
                    mi.child.modify_fg(k, v)

        # modify the background color of the menu
        for (k, v) in self.color_bg.iteritems():
            self.menu.modify_bg(k, v)

        self.menu.show_all()
        self.menu.popup_given(self)

    def popdown(self):
        self.menu.popdown()
        self.menu = None


    def get_active(self):
        if self.active_item != None:
            return self.__item_list[self.active_item]
        else:
            return None

    def set_active(self, item):
        self.set_active_indx(self.index(item))

    def get_active_indx(self):
        return self.active_item

    def set_active_indx(self, indx):
        if indx == self.active_item:
            return
        try:
            self.set_label(self.__item_list[indx][self.effective_column])
            self.active_item = indx
        except:
            self.set_label('')
            self.active_item = None
        zComboBox.reg_emit_to('changed', self)


    def set_label(self, label):
        w = self.get_width_chars()
        if w > 0 and len(label) > w:
            label = label[:w-2] + '..'
        super(zComboBox, self).set_label(label)


    def get_value(self, indx, col):
        try:
            return self.__item_list[indx][col]
        except:
            return None

    def set_value(self, indx, col, item):
        self.__item_list[indx][col] = item

        if indx == self.active_item:
            self.set_active(indx)


    def set_width_chars(self, n_chars):
        super(zComboBox, self).set_width_chars(n_chars)
        self.set_label(self.get_label())


    def set_row_separator_func(self, callback):
        '''
        the callback function should be defined as:
            def callback(item)
        where "item" is the item been inserted/prepended/appended

        the callback should return True if the row shall be
        treated as separator; otherwise, False should be returned
        '''
        self.row_separator_func = callback
    ### end of overridden function definition


    def get_effective_column(self):
        return self.effective_column

    def set_effective_column(self, col):
        self.effective_column = col


######## ######## ######## ######## ########
########          zTabbar           ########
######## ######## ######## ######## ########

class zTabbar(z_ABC, gtk.EventBox):
    '''A Flat (Inline) Tabbar'''
    _auto_update = {
        # 'signal_like_string'  : [ (widget, callback, data_list), ... ]
        'changed'               : [  ],
        }
    def __init__(self):
        super(zTabbar, self).__init__()


        self.active_tab = None
        self.tab_fg = {}        # state : color
        self.tab_bg = {}        # state : color
        self.tab_font = None


        # layout of the frame:
        #
        #   +--+-------------------+--+
        #   |lt| scrollable tabbar |rt|
        #   +--+-------------------+--+

        # create frame
        frame = gtk.HBox()
        self.scroll_left = zButton('<')
        self.viewport = gtk.Viewport()
        self.scroll_right = zButton('>')

        self.viewport.set_shadow_type(gtk.SHADOW_NONE)
        self.viewport.hadj = self.viewport.get_hadjustment()
        self.viewport.hadj_preserve = None
        self.viewport.scrolling = False
        self.viewport.start_scrolling = False

        self.scroll_left.set_property('can_focus', False)
        self.scroll_right.set_property('can_focus', False)
        self.scroll_left.set_property('can_default', False)
        self.scroll_right.set_property('can_default', False)

        self.add(frame)
        frame.pack_start(self.scroll_left, False, False, 0)
        frame.pack_start(self.viewport, True, True, 0)
        frame.pack_end(self.scroll_right, False, False, 0)


        # create tabbar
        self.tab_box = gtk.HBox()
        self.viewport.add(self.tab_box)


        # connect scroll buttons with viewport
        self.viewport.connect('size-allocate', self._sig_size_changed)

        self.viewport.hadj_sig_id = self.viewport.hadj.connect('value-changed', self._sig_hadj_modified)

        self.scroll_left.click_id  = self.scroll_left.connect('clicked', self._sig_scroll_viewport_once, -25)
        self.scroll_right.click_id = self.scroll_right.connect('clicked', self._sig_scroll_viewport_once, 25)

        self.scroll_left.connect('pressed', self._sig_scroll_viewport, -10)
        self.scroll_left.connect('released', self._sig_stop_scroll_viewport)
        self.scroll_right.connect('pressed', self._sig_scroll_viewport, 10)
        self.scroll_right.connect('released', self._sig_stop_scroll_viewport)


    ### signal definition
    def _sig_hadj_modified(self, adjustment):
        if self.viewport.hadj_preserve != None:
            self.viewport.hadj.handler_block(self.viewport.hadj_sig_id)
            self.viewport.hadj.set_value(self.viewport.hadj_preserve)
            self.viewport.hadj.handler_unblock(self.viewport.hadj_sig_id)
        else:
            self.viewport.hadj_preserve = self.viewport.hadj.get_value() # save preservation


    def _sig_size_changed(self, container, alloc):
        pos = self.viewport.hadj.get_value()
        ( pos_valid, new_pos ) = self.validate_tabbar_pos()

        if pos > 0 and not pos_valid:
            # left not fully shown *but* right edge not attached
            self.scroll_viewport_by(new_pos - pos)

        self.scroll_to_active_tab()


    def _sig_scroll_viewport_once(self, bttn, increment):
        if not self.viewport.start_scrolling:
            self.scroll_viewport_by(increment)

    def _sig_scroll_viewport(self, bttn, increment):
        # start the timer
        self.viewport.scrolling = True
        gobject.timeout_add(41, self.loop_scroll_viewport_by, increment)
        # 1 s / 41 ms = 24.39 fps

    def _sig_stop_scroll_viewport(self, bttn):
        # stop the timer
        self.viewport.scrolling = False
        # unblock 'clicked'
        self.viewport.start_scrolling = False


    def _sig_toggled(self, tab):
        if self.active_tab == tab:
            tab.handler_block(tab.sig_id)       # block signal until active statue modified
            tab.set_active(True)
            tab.handler_unblock(tab.sig_id)     # unblock signal
        else:
            self.set_active(tab)

        # scroll to the active tab, if not fully shown
        self.scroll_to_active_tab()
    ### end of signal definition


    ### overridden function definition
    def append(self, tab):
        self.tab_box.pack_start(tab, False, False, 0)
        self.validate_tabbar_pos()

    def remove(self, tab):
        self.tab_box.remove(tab)
        tab.disconnect(tab.sig_id)
        self.validate_tabbar_pos()


    def modify_font(self, font_desc):
        for tab in self.get_tab_list():
            tab.modify_font(font_desc)
        self.tab_font = font_desc

        self.scroll_left.modify_font(font_desc)
        self.scroll_right.modify_font(font_desc)

    def modify_fg(self, state, color):
        for tab in self.get_tab_list():
            tab.modify_fg(state, color)
        self.tab_fg[state] = color


    def modify_bg(self, state, color):
        super(zTabbar, self).modify_bg(state, color)
        self.viewport.modify_bg(state, color)

        for tab in self.get_tab_list():
            tab.modify_bg(state, color)
        self.tab_bg[state] = color


    def get_active(self):
        return self.active_tab

    def set_active(self, tab):
        '''can take a zToggleButton or a label as argument'''
        for iter_tab in self.get_tab_list():
            iter_tab.handler_block(iter_tab.sig_id) # block signal until active statue modified

            if ( (isinstance(tab, str) and self.get_label_of(iter_tab) == tab) or
                 iter_tab == tab
                 ):
                if isinstance(tab, str):
                    tab = iter_tab
                iter_tab.set_active(True)
                state = gtk.STATE_ACTIVE
            else:
                iter_tab.set_active(False)
                state = gtk.STATE_NORMAL

            if state in self.tab_fg and gtk.STATE_PRELIGHT not in self.tab_fg:
                iter_tab.modify_fg(gtk.STATE_PRELIGHT, self.tab_fg[state])

            iter_tab.handler_unblock(iter_tab.sig_id) # unblock signal

        if not self.active_tab or self.active_tab != tab:
            self.active_tab = tab
            zTabbar.reg_emit_to('changed', tab)
    ### end of overridden function definition


    def new_tab(self, tab_label):
        tab = zToggleButton()
        tab.set_label(tab_label)

        tab.set_property('can-default', False)
        tab.set_property('can-focus', False)

        tab.modify_font(self.tab_font)
        for state in self.tab_fg:
            tab.modify_fg(state, self.tab_fg[state])
        for state in self.tab_bg:
            tab.modify_bg(state, self.tab_bg[state])

        tab.sig_id = tab.connect('toggled', self._sig_toggled)

        return tab


    def get_tab_list(self):
        return self.tab_box.get_children()

    def get_tabbar_len(self):
        ( last_pos, last_len ) = self.get_tab_alloc(-1)
        return last_pos + last_len

    def get_tab_alloc(self, tab_or_indx):
        '''return (x, width) of the given tab/index, or (-1, -1) if tab/index is invalid.'''
        tab_list = self.get_tab_list()

        if isinstance(tab_or_indx, zToggleButton):
            # is a zTab, check if it is in the list
            if tab_or_indx in tab_list:
                target_tab = tab_or_indx
            else:
                return -1, -1   # not a valid tab, early return
        else:
            # treated as index, try to fetch the corresponding zTab
            try:
                target_tab = tab_list[tab_or_indx]
            except:
                return -1, -1   # not a valid tab, early return

        tab_pos = 0
        for tab in tab_list:
            if tab == target_tab:
                return tab_pos, tab.size_request()[0]
            else:
                tab_pos += tab.size_request()[0]


    def get_label_of(self, tab):
        return tab.label.get_text()

    def set_label_of(self, tab, label):
        tab.label.set_text(label)

    def get_tab_label_list(self):
        return [ self.get_label_of(tab) for tab in self.get_tab_list() ]


    def validate_tabbar_pos(self, pos = None):
        if pos == None:
            pos = self.viewport.hadj.get_value()

        valid = True

        alloc = self.viewport.get_allocation()
        if alloc.x == -1:
            # not allocated
            self.scroll_left.set_property('sensitive', False)
            self.scroll_right.set_property('sensitive', False)
            return False, 0
        tab_len = self.get_tabbar_len()

        # validate lower bound
        if pos <= 0:
            pos = 0
            valid = False
            self.scroll_left.set_property('sensitive', False)
        else:
            self.scroll_left.set_property('sensitive', True)

        # validate upper bound
        if pos >= tab_len - alloc.width:
            pos = max(0, tab_len - alloc.width)
            valid = False
            self.scroll_right.set_property('sensitive', False)
        else:
            self.scroll_right.set_property('sensitive', True)

        return valid, pos


    ### viewport scrolling function
    def loop_scroll_viewport_by(self, increment):
        if not self.viewport.scrolling:
            return False

        # start scrolling, block 'clicked'
        self.viewport.start_scrolling = True
        return self.scroll_viewport_by(increment)

    def scroll_to_active_tab(self):
        alloc = self.viewport.get_allocation()
        ( tab_pos, tab_len ) = self.get_tab_alloc(self.active_tab)
        current_pos = self.viewport.hadj.get_value()

        if tab_pos < current_pos:
            # left not shown
            increment = tab_pos - current_pos
        elif tab_pos + tab_len > current_pos + alloc.width:
            # right not shown
            increment = (tab_pos + tab_len) - (current_pos + alloc.width)
        else:
            # fully shown
            increment = 0
        self.scroll_viewport_by(increment)

    def scroll_viewport_by(self, increment):
        if not increment:
            return False        # no increment, early return

        pos = self.viewport.hadj.get_value()
        ( pos_valid, new_pos ) = self.validate_tabbar_pos(pos + increment)

        self.viewport.hadj_preserve = None # clear preservation
        self.viewport.hadj.set_value(new_pos)
        return pos_valid
    ### end of viewport scrolling function
