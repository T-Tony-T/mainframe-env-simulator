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

import os, sys, stat, time
import pygtk
pygtk.require('2.0')
import gtk
import gobject, pango



######## ######## ######## ######## 
########     LastLine      ######## 
######## ######## ######## ######## 

class LastLine(gtk.HBox):
    def __init__(self, label = ''):
        '''
        label
            the label in front of the last-line panel
        '''
        super(LastLine, self).__init__()


        self.__label = gtk.Label(label)
        self.pack_start(self.__label, False, False, 0)

        self.__line_fix = gtk.Label()
        self.pack_start(self.__line_fix, False, False, 0)

        self.__line_inter = gtk.Entry()
        self.pack_start(self.__line_inter, True, True, 0)

        self.__line_inter.set_has_frame(False)

        self.set_editable(False)


        # connect auto-update items
        zEdit.register('update_font', zEdit._sig_update_font_modify, self.__label)
        zEdit._sig_update_font_modify(self.__label)

        zEdit.register('update_font', zEdit._sig_update_font_modify, self.__line_fix)
        zEdit._sig_update_font_modify(self.__line_fix)

        zEdit.register('update_font', zEdit._sig_update_font_modify, self.__line_inter)
        zEdit._sig_update_font_modify(self.__line_inter)

        zEdit.register('update_theme', self._sig_update_theme, self)
        self._sig_update_theme()


    ### signal-like auto-update function
    def _sig_update_theme(self, widget = None):
        self.__line_fix.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['reserve']))

        self.__line_inter.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['text']))
        self.__line_inter.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['base']))

        self.__line_inter.modify_text(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zEdit.theme['text']))
        self.__line_inter.modify_base(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zEdit.theme['base']))
    ### end of signal-like auto-update function

    ### overloaded function definition
    def connect(self, sig, *data):
        return self.__line_inter.connect(sig, *data)
    ### end of overloaded function definition

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
        self.__line_inter.set_property('can_focus', setting)
        self.__line_inter.set_editable(setting)
        self.__line_inter.grab_focus()



######## ######## ######## ######## 
########    SplitScreen    ######## 
######## ######## ######## ######## 

class SplitScreen(gtk.Frame):
    def __init__(self,
                 frame, frame_alist = [],
                 frame_init = None,
                 frame_split_dup = None,
                 frame_sz_min = (50, 50)
                 ):
        '''
        frame
            a construction function of a GtkWidget which will be
            the frame of the inner window.

            e.g. comp.SplitScreen(gtk.Label)

        frame_alist = []
            the argument list of the "frame".

            e.g. comp.SplitScreen(gtk.Label, ['Test Label'])

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
        super(SplitScreen, self).__init__()


        self.frame = frame
        self.frame_alist = frame_alist
        self.frame_init = frame_init
        self.frame_split_dup = frame_split_dup
        self.frame_sz_min = frame_sz_min

        # layout of the SplitScreen:
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
            self.ctrl_bar[pos].set_property('can_focus', False)
            self.ctrl_bar[pos].connect_object('clicked', self.add_paned, self.mw_center, pos)
            self.ctrl_bar[pos].drag_source_set(gtk.gdk.BUTTON1_MASK, [], 0)
            self.ctrl_bar[pos].connect('drag_begin', self._sig_ctrl_drag, drag_icon, pos)
            self.ctrl_bar[pos].connect('button-release-event', self._sig_ctrl_drop, pos)


    ### signal for DnD
    def _sig_ctrl_drag(self, widget, context, icon, pos):
        context.set_icon_pixbuf(icon, 0, 0)

        # create the shading-layer
        root = widget.get_root_window()
        (root_w, root_h) = root.get_size()
        screen = widget.get_toplevel().get_screen()
        self.sd_layer = gtk.gdk.Window(
            root, root_w, root_h,
            gtk.gdk.WINDOW_TEMP,
            gtk.gdk.ALL_EVENTS_MASK,
            gtk.gdk.INPUT_OUTPUT,
            '', 0, 0,
            screen.get_rgba_visual(), screen.get_rgba_colormap(), gtk.gdk.Cursor(gtk.gdk.PLUS),
            '', '', True
            )
        self.sd_layer.show()

        # create the cairo context
        self.sd_layer_cr = self.sd_layer.cairo_create()

        self.sd_layer_cr.set_line_width(1)
        self.sd_layer_cr.set_source_rgba(0, 0, 0, 0.3)

        # limit the drawing area
        alloc = self.mw_center.get_allocation()
        ( ptr_x,     ptr_y     ) = self.mw_center.get_pointer()
        ( ptr_abs_x, ptr_abs_y ) = self.sd_layer.get_pointer()[:2]
        ( base_x,    base_y    ) = ( ptr_abs_x - ptr_x, ptr_abs_y - ptr_y )

        self.sd_layer_cr.rectangle(base_x, base_y, alloc.width, alloc.height)
        self.sd_layer_cr.clip()

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

        correct_pos = self._correct_pos(
            ptr_pos,                              # the current ptr pos
            (0, 0),                               # the frame size - low bound
            (alloc.width, alloc.height),          # the frame size - high bound
            [sp + 20 for sp in self.frame_sz_min] # the min spacing + 20
            )

        # add paned if in center
        if correct_pos:
            paned = self.add_paned(self.mw_center, pos)

            # re-position the newly added frame
            handle_sz = paned.style_get_property('handle-size')
            if pos in self.__ctrl_pos['h']:
                # - handle_sz cancel the width of the divider
                paned.set_position(correct_pos[0] - handle_sz)
            else:
                paned.set_position(correct_pos[1] - handle_sz)
    ### end of signal for DnD

    ### signal for center frame
    def _sig_div_drop(self, widget, event):
        for child in widget.get_children():
            alloc = child.get_allocation()
            if ( alloc.width < self.frame_sz_min[0] or
                 alloc.height < self.frame_sz_min[1]
                 ):
                self.rm_frame(widget, child)
                break
    ### end of signal for center frame


    ### overloaded function definition
    def is_focus(self):
        return self.active_frame(self.mw_center) != None

    def grab_focus(self):
        child = self.mw_center.child
        while not isinstance(child, self.frame):
            child = child.get_children()[0]
        child.grab_focus()
    ### end of overloaded function definition


    def active_frame(self, current):
        if isinstance(current, self.frame):
            if current.is_focus():
                return current  # found the frame
            else:
                return None     # end of the path

        for child in current.get_children():
            found = self.active_frame(child)
            if found:
                return found    # found in previous search
        return None             # not found at all

    def add_paned(self, parent, pos):
        child = parent.child

        # create new paned
        if pos in self.__ctrl_pos['h']:
            paned = gtk.HPaned()
        else:
            paned = gtk.VPaned()

        # create new frame
        if self.frame_split_dup:
            new_child = self.frame_split_dup(self.active_frame(self.mw_center))
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
        frame.set_init(self.frame_init)
        frame.exec_init()

        return frame

    def rm_frame(self, widget, child_rm):
        if widget == self.mw_center:    # the only frame
            widget.remove(child_rm)
            widget.add(self.new_frame())
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


    def update_sd(self, pos):
        if not self.mw_center.timer:
            return False

        # calculate position
        alloc = self.mw_center.get_allocation()
        ( ptr_x,     ptr_y     ) = self.mw_center.get_pointer()
        ( ptr_abs_x, ptr_abs_y ) = self.sd_layer.get_pointer()[:2]
        ( base_x,    base_y    ) = ( ptr_abs_x - ptr_x, ptr_abs_y - ptr_y )

        self.sd_layer.clear()

        # validate position
        correct_pos = self._correct_pos(
            (ptr_x, ptr_y),                       # the current ptr pos
            (0, 0),                               # the frame size - low bound
            (alloc.width, alloc.height),          # the frame size - high bound
            [sp + 10 for sp in self.frame_sz_min] # the min spacing + 10
            )
        if not correct_pos:
            return True

        # draw on shading-layer
        if pos == 'lt':
            self.sd_layer_cr.rectangle(base_x,    base_y,    ptr_x,               alloc.height        )
        elif pos == 'tp':
            self.sd_layer_cr.rectangle(base_x,    base_y,    alloc.width,         ptr_y               )
        elif pos == 'rt':
            self.sd_layer_cr.rectangle(ptr_abs_x, base_y,    alloc.width - ptr_x, alloc.height        )
        else:
            self.sd_layer_cr.rectangle(base_x,    ptr_abs_y, alloc.width,         alloc.height - ptr_y)

        self.sd_layer_cr.fill()

        return True

    # all three args should all be tuples/lists with the same length
    def _correct_pos(self, pos, limit_low, limit_high, spacing):
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


######## ######## ######## ######## 
########       zEdit       ######## 
######## ######## ######## ######## 


class zEdit(gtk.VBox):
    font = {
        'name' : 'monospace',
        'size' : 12,
        }
    theme = {
        # reguler
        'text'          : '#000000', # black
        'text-selected' : '#000000', # black
        'base'          : '#FBEFCD', # wheat - mod
        'base-selected' : '#FFA500', # orenge
        'status'        : '#808080', # gray
        'status-active' : '#C0C0C0', # silver
        # highlight
        'reserve'       : '#0000FF', # blue
        'comment'       : '#008000', # green
        'literal'       : '#FF0000', # red
        'label'         : '#808000', # olive
        }

    __auto_update = {
        # 'signal_like_string'  : [ (widget, callback, data_list), ... ]
        'update_buffer_list'    : [  ],
        'update_font'           : [  ],
        'update_theme'          : [  ],
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
        self.active_buffer = None
        self.ui_init = None

        # layout of the frame:
        # 
        #   +------------+_
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

        # create the status bar
        self.bottom_bg = gtk.EventBox()
        self.pack_end(self.bottom_bg, False, False, 0)
        self.bottom = gtk.HBox()
        self.bottom_bg.add(self.bottom)

        # create buffer switcher
        self.buffer_sw_tm = gtk.ListStore(str, bool) # define TreeModel
        self.buffer_sw = gtk.ComboBox(self.buffer_sw_tm)
        self.bottom.pack_start(self.buffer_sw, False, False, 0)
        self.buffer_sw.set_property('focus-on-click', False)

        self.buffer_sw_cell = gtk.CellRendererText()
        self.buffer_sw.pack_start(self.buffer_sw_cell, True)
        self.buffer_sw.add_attribute(self.buffer_sw_cell, "text", 0)

        self.buffer_sw.set_row_separator_func(self.__separator)

        # create the main window frame
        self.scrolled = gtk.ScrolledWindow()
        self.pack_start(self.scrolled, True, True, 0)
        self.scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.scrolled.set_placement(gtk.CORNER_TOP_RIGHT)

        self.center = None
        self.set_buffer(buffer_path, buffer_type)

        # connect auto-update items
        zEdit.register('update_buffer_list', zEdit._sig_update_buffer_list, self.buffer_sw, self)
        zEdit.register('update_font', zEdit._sig_update_font_property, self.buffer_sw_cell, 0.75)
        zEdit.register('update_theme', self._sig_update_theme, self)

        zEdit._sig_update_buffer_list(self.buffer_sw, self)
        zEdit._sig_update_font_property(self.buffer_sw_cell, 0.75)
        self._sig_update_theme()

        # connect signal
        self.buffer_sw.connect('changed', self._sig_buffer_changed)

    ### signal-like auto-update function
    @staticmethod
    def register(sig, callback, widget, *data):
        '''This function register a function to a signal-like string'''
        zEdit.__auto_update[sig].append((widget, callback, data))

    @staticmethod
    def unregister(sig, widget):
        '''This function un-register a widget from a signal-like string'''
        for item in zEdit.__auto_update[sig]:
            zEdit.__auto_update[sig].remove(item)

    @staticmethod
    def emit(sig):
        '''This function emit the signal to all registered object'''
        for (widget, callback, data_list) in zEdit.__auto_update[sig]:
            callback(widget, *data_list)

    @staticmethod
    def _sig_update_buffer_list(combo, z_editor):
        tm = combo.get_model()

        # clear the list
        tm.clear()

        # add system-opened buffers
        for buff in zEditBuffer.buff_group['system']:
            tm.append([buff, False])
        # add user-opened buffers, if exist
        if len(zEditBuffer.buff_group['user']):
            # add separator: Not an Item, this item should not be seen
            tm.append(['NanI', True])
            # add user-opened buffers
            for buff in zEditBuffer.buff_group['user']:
                tm.append([buff, False])

        # set active
        buffer_iter = tm.get_iter_first()
        while tm.get_value(buffer_iter, 0) != z_editor.active_buffer.name:
            buffer_iter = tm.iter_next(buffer_iter)
        combo.set_active_iter(buffer_iter)
        
    @staticmethod
    def _sig_update_font_modify(widget, weight = 1):
        widget.modify_font(
            pango.FontDescription('{0} {1}'.format(zEdit.font['name'], int(zEdit.font['size'] * weight)))
            )

    @staticmethod
    def _sig_update_font_property(widget, weight = 1):
        widget.set_property(
            'font-desc',
            pango.FontDescription('{0} {1}'.format(zEdit.font['name'], int(zEdit.font['size'] * weight)))
            )

    def _sig_update_theme(self, widget = None):
        self.center.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['text']))
        self.center.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['base']))

        self.center.modify_text(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zEdit.theme['text']))
        self.center.modify_base(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zEdit.theme['base']))

        self.center.modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse(zEdit.theme['text-selected']))
        self.center.modify_base(gtk.STATE_SELECTED, gtk.gdk.color_parse(zEdit.theme['base-selected']))

        if self.is_focus():
            self.update_theme_focus_in()
        else:
            self.update_theme_focus_out()

    def update_theme_focus_in(self):
        self.bottom_bg.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['status-active']))
        self.buffer_sw_cell.set_property('background-gdk', gtk.gdk.color_parse(zEdit.theme['status-active']))

    def update_theme_focus_out(self):
        self.bottom_bg.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['status']))
        self.buffer_sw_cell.set_property('background-gdk', gtk.gdk.color_parse(zEdit.theme['status']))
    ### end of signal-like auto-update function


    ### signal for center
    def _sig_focus_in(self, widget, event):
        self.update_theme_focus_in()

    def _sig_focus_out(self, widget, event):
        self.update_theme_focus_out()
    ### end of signal for center


    ### signal for bottom
    def _sig_buffer_changed(self, combobox):
        active_iter = combobox.get_active_iter()
        if not active_iter:
            return              # early return
        buffer_name = self.buffer_sw_tm.get_value(active_iter, 0)
        buff = zEditBuffer.buff_list[buffer_name]
        self.set_buffer(buff.path, buff.type)
        # set focus
        self.grab_focus()
    ### end of signal for bottom


    ### overloaded function definition
    def connect(self, sig, callback, *data):
        [ trans_sig, trans_callback ] = zEdit.__trans_signal(
            self.active_buffer.type, sig, callback
            )
        return self.center.connect(trans_sig, trans_callback, *data)

    def is_focus(self):
        return self.center.is_focus()

    def grab_focus(self):
        self.center.grab_focus()
    ### end of overloaded function definition


    def exec_init(self):
        if self.ui_init:
            self.ui_init(self)

    def set_init(self, ui_init):
        self.ui_init = ui_init


    def get_buffer(self):
        return (self.active_buffer.path, self.active_buffer.type)

    def set_buffer(self, buffer_path, buffer_type):
        # switch buffer
        new_buff = zEditBuffer(buffer_path, buffer_type)

        if ( self.active_buffer == None or
             self.active_buffer.type != new_buff.type
             ):
            # create widget
            if new_buff.type == 'file':
                widget = gtk.TextView()
            elif new_buff.type == 'dir':
                widget = zFileManager()
            else:
                raise KeyError

            # switch widget
            if self.center:
                zEdit.unregister('update_font', self.center)
                self.center.disconnect(self.focus_in_id)
                self.center.disconnect(self.focus_out_id)
                self.scrolled.remove(self.center)
            self.center = widget
            self.scrolled.add(self.center)
            zEdit.register('update_font', zEdit._sig_update_font_modify, self.center)
            self.focus_in_id = self.center.connect('focus-in-event', self._sig_focus_in)
            self.focus_out_id = self.center.connect('focus-out-event', self._sig_focus_out)
            zEdit._sig_update_font_modify(self.center)

        if new_buff != self.active_buffer:
            self.active_buffer = new_buff

        # connect buffer
        if self.active_buffer.type == 'file':
            self.center.set_buffer(new_buff.buffer)
        elif self.active_buffer.type == 'dir':
            pass
            if self.active_buffer.path and io_encap.is_dir(self.active_buffer.path):
                self.center.set_folder(os.path.join(* self.active_buffer.path))

        self.exec_init()
        self._sig_update_theme()
        self.show_all()


    def get_font(self):
        return zEdit.font

    def set_font(self, dic):
        for k,v in dic.items():
            if k in zEdit.font:
                zEdit.font[k] = v
        zEdit.emit('update_font')

    def get_theme(self):
        return zEdit.theme

    def set_theme(self, dic):
        for k,v in dic.items():
            if k in zEdit.theme:
                zEdit.font[k] = v
        zEdit.emit('update_theme')


    ### supporting function
    def __separator(self, model, iterator, data = None):
        return model.get_value(iterator, 1)

    @staticmethod
    def __trans_signal(buffer_type, sig, callback):
        if buffer_type == 'file':
            return [ sig, callback ]
        elif buffer_type == 'dir':
            if sig == 'populate-popup':
                return [ 'button-press-event', zEdit.__trans_popup(callback) ]

    @staticmethod
    def __trans_popup(func):
        def new_func(treeview, event, data = None):
            if event.button != 3:
                return

            # create the menu
            menu = gtk.Menu()

            # fill the menu
            paths = treeview.get_path_at_pos(int(event.x), int(event.y))
            model = treeview.get_model()

            if paths is None:
                raise LookupError
            elif len(paths) > 0:
                iterator = model.get_iter(paths[0])
                obj = model[iterator][0]
            else:
                raise ValueError

            menu.append(gtk.MenuItem('Open "{0}"'.format(obj)))

            # callback
            func(treeview, menu, data)

            # popup the menu
            menu.popup(None, None, None, event.button, event.time)
        return new_func
    ### end of supporting function



class zEditBuffer(object):
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

    def __new__(cls, buffer_path = None, buffer_type = None):
        self = object.__new__(cls)

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
        zEdit.emit('update_buffer_list')

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


######## ######## ######## ######## 
########   zFileManager    ######## 
######## ######## ######## ######## 

class zFileManager(gtk.TreeView):
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
    def _sig_open_file(self, treeview, path, column):
        model = self.get_model()
        iterator = model.get_iter(path)
        filename = os.path.join(self.dirname, model.get_value(iterator, 0))
        filestat = os.stat(filename)
        if stat.S_ISDIR(filestat.st_mode):
            self.set_folder(filename)
    ### end of signal definition


    ### overloaded function definition
    def grab_focus(self):
        super(zFileManager, self).grab_focus()
        self.set_cursor((0,))
    ### end of overloaded function definition


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
