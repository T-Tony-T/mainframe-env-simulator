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

import os, sys
import pygtk
pygtk.require('2.0')
import gtk
import gobject, pango


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

        # layout of the frame:
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
        frame.connect('focus-in-event', self._sig_focus_in)
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

    def _sig_focus_in(self, widget, event):
        pass # mark
    ### end of signal for center frame

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
        paned.set_property('can_focus', False)

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
        new_child.connect('focus-in-event', self._sig_focus_in)

        # show widgets
        parent.show_all()
        new_child.grab_focus()

        return paned

    def new_frame(self, alist):
        # prepare frame info
        frame = self.frame(* alist)

        if self.frame_init:
            self.frame_init(frame)

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
        'text'          : '#000000',
        'text-selected' : '#000000',
        'base'          : '#FBEFCD',#'#FFF7EA',
        'base-selected' : '#FFA500',
        'status'        : '#A9A297',
        'status-active' : '#D9D2C7',
        }

    __auto_update = {
        # 'signal_like_string'  : [ (widget, callback, data_list), ... ]
        'update_buffer_list'    : [  ],
        'update_font'           : [  ],
        'update_theme'          : [  ],
        }

    def __init__(self, buffer_path = None, buffer_type = None):
        super(zEdit, self).__init__()
        self.active_buffer = None

        # create the main window frame
        self.scrolled = gtk.ScrolledWindow()
        self.pack_start(self.scrolled, True, True, 0)
        self.scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.scrolled.set_placement(gtk.CORNER_TOP_RIGHT)

        self.center = None
        self.set_buffer(buffer_path, buffer_type)

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
        self.buffer_sw.set_row_separator_func(self.separator)

        # connect auto-update items
        self.register('update_buffer_list', zEdit._sig_update_buffer_list)
        zEdit._sig_update_buffer_list(self)
        self.register('update_font', zEdit._sig_update_font)
        zEdit._sig_update_font(self)
        self.register('update_theme', zEdit._sig_update_theme)
        zEdit._sig_update_theme(self)

        # connect signal
        self.center.connect('focus-in-event', self._sig_focus_in)
        self.center.connect('focus-out-event', self._sig_focus_out)
        self.buffer_sw.connect('changed', self._sig_buffer_changed)

    ### signal-like auto-update function
    def register(self, sig, callback, *data):
        '''This function register a function to a signal-like string'''
        zEdit.__auto_update[sig].append((self, callback, data))

    @staticmethod
    def emit(sig):
        '''This function emit the signal to all registered object'''
        for (widget, callback, data_list) in zEdit.__auto_update[sig]:
            callback(widget, *data_list)

    @staticmethod
    def _sig_update_buffer_list(widget):
        # clear the list
        widget.buffer_sw_tm.clear()

        # add system-opened buffers
        for buff in zEditBuffer.buff_group['system']:
            widget.buffer_sw_tm.append([buff, False])
        # add user-opened buffers, if exist
        if len(zEditBuffer.buff_group['user']):
            # add separator: Not an Item, this item should not be seen
            widget.buffer_sw_tm.append(['NanI', True])
            # add user-opened buffers
            for buff in zEditBuffer.buff_group['user']:
                widget.buffer_sw_tm.append([buff, False])

        # set active
        buffer_iter = widget.buffer_sw_tm.get_iter_first()
        while widget.buffer_sw_tm.get_value(buffer_iter, 0) != widget.active_buffer.name:
            buffer_iter = widget.buffer_sw_tm.iter_next(buffer_iter)
        widget.buffer_sw.set_active_iter(buffer_iter)
        
    @staticmethod
    def _sig_update_font(widget):
        widget.center.modify_font(
            pango.FontDescription('{0} {1}'.format(zEdit.font['name'], zEdit.font['size']))
            )

        widget.buffer_sw_cell.set_property(
            'font-desc',
            pango.FontDescription('{0} {1}'.format(zEdit.font['name'], int(zEdit.font['size'] * 0.75)))
            )

    @staticmethod
    def _sig_update_theme(widget):
        widget.center.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['text']))
        widget.center.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['base']))

        widget.center.modify_text(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zEdit.theme['text']))
        widget.center.modify_base(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zEdit.theme['base']))

        widget.center.modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse(zEdit.theme['text-selected']))
        widget.center.modify_base(gtk.STATE_SELECTED, gtk.gdk.color_parse(zEdit.theme['base-selected']))

        if widget.is_focus():
            widget.bottom_bg.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['status-active']))
        else:
            widget.bottom_bg.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['status']))
    ### end of signal-like auto-update function


    ### signal for center
    def _sig_focus_in(self, widget, event):
        self.bottom_bg.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['status-active']))

    def _sig_focus_out(self, widget, event):
        self.bottom_bg.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(zEdit.theme['status']))
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
    def connect(self, sig, *data):
        return self.center.connect(sig, *data)

    def is_focus(self):
        return self.center.is_focus()

    def grab_focus(self):
        self.center.grab_focus()
    ### end of overloaded function definition


    def get_buffer(self):
        return (self.active_buffer.path, self.active_buffer.type)

    def set_buffer(self, buffer_path, buffer_type):
        # switch buffer
        new_buff = zEditBuffer(buffer_path, buffer_type)

        if ( self.active_buffer == None or
             self.active_buffer.type != new_buff.type
             ):
            # create widget
            if new_buff.type == 'textview':
                widget = gtk.TextView()
            else:
                raise KeyError

            # switch widget
            if self.center:
                self.remove(self.center)
            self.center = widget
            self.scrolled.add(self.center)

        if new_buff != self.active_buffer:
            self.active_buffer = new_buff

        # connect buffer
        if self.active_buffer.type == 'textview':
            self.center.set_buffer(new_buff.buffer)

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

    def separator(self, model, iter, data = None):
        return model.get_value(iter, 1)


class zEditBuffer(object):
    DEFAULT_BUFFER = '*scratch*'
    SYSTEM_BUFFER = {
        '*scratch*' : 'textview',
        }
    buff_list = {
        # 'buff_user'    : zEditBuffer()
        # 'buff_sys'     : zEditBuffer()
        # 'buff_user(1)' : zEditBuffer()
        # 'buff_another' : zEditBuffer()
        # 'buff_user(2)' : zEditBuffer()
        #  ...
        }
    buff_group = {
        'system' : [], # [ 'buff_sys', ]
        'user'   : [], # [ 'buff_user', 'buff_user(1)', 'buff_another', 'buff_user(2)', ]
        }
    buff_rec = { # no-removal record
        # 'buff_sys'     : [ ( 'buff_sys',  buff_sys_path, opened ),
        #                    ],
        # 'buff_user'    : [ ( 'buff_user',    buff_user_0_path, opened ),
        #                    ( 'buff_user(1)', buff_user_1_path, opened ),
        #                    ( 'buff_user(2)', buff_user_2_path, opened ),
        #                    ],
        # 'buff_another' : [ ( 'buff_another',  buff_another_path, opened ),
        #                    ],
        #  ...
        }

    def __new__(cls, buffer_path = None, buffer_type = None):
        self = object.__new__(cls)
        if buffer_path == None:
            buffer_path = zEditBuffer.DEFAULT_BUFFER

        buff_group = 'user'     # assume user-opened buffer
        if isinstance(buffer_path, str):
            self.name = buffer_path
            if buffer_path in zEditBuffer.SYSTEM_BUFFER:
                # system-opened buffer
                buff_group = 'system'
                self.path = None
                self.type = zEditBuffer.SYSTEM_BUFFER[self.name]
            else:       # treat as a single node, add [] around
                self.path = [ buffer_path ]
                self.type = buffer_type
        else:
            self.name = buffer_path[-1]
            self.path = buffer_path
            self.type = buffer_type

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
        zEdit.emit('update_buffer_list')

        # fetch content
        if buffer_type == 'textview':
            self.buffer = gtk.TextBuffer()

            if self.name == '*scratch*':
                # tmp buffer
                self.buffer.set_text(
'''//*
//* This buffer is for notes you don't want to save.
//* If you want to create a file, use 'File' -> 'New'
//* or save this buffer explicitly.
//*
'''
)
            elif io_encap.is_file(self.path):
                # existing file
                if not io_encap.fetch(self):
                    raise ValueError
            else:
                # new file
                pass
            self.modified = False
        else:
            self.buffer = None
            self.modified = None

        return self

######## ######## ######## ######## 
########    MODULE INIT    ######## 
######## ######## ######## ######## 

# change gtk settings
settings = gtk.settings_get_default()
settings.set_property('gtk-show-input-method-menu', False)
settings.set_property('gtk-show-unicode-menu', False)

settings.set_property('gtk-cursor-blink', False)

# open default buffers
for buff_name, buff_type in zEditBuffer.SYSTEM_BUFFER.items():
    zEditBuffer(buff_name, buff_type)
