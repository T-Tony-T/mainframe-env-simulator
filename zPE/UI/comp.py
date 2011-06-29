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


class SplitScreen(gtk.Frame):
    def __init__(self,
                 frame, frame_alist = [],
                 frame_init = None,
                 frame_split_dup = None,
                 frame_sz_min = (40, 40)
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
        self.active_frame = self.new_frame(self.frame_alist) # keep track of the focus
        self.mw_center.add(self.active_frame)

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
        gobject.timeout_add(20, self.update_mw, pos)

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
            [sp + 10 for sp in self.frame_sz_min] # the min spacing + 10
            )

        # add paned if in center
        if correct_pos:
            paned = self.add_paned(self.mw_center, pos)

            # re-position the newly added frame
            if pos in self.__ctrl_pos['h']:
                # -6 to cancel the width of the divider
                paned.set_position(correct_pos[0] - 6)
            else:
                paned.set_position(correct_pos[1] - 6)
    ### end of signal for DnD

    ### signal for MWF
    def _sig_div_drop(self, widget, event):
        for child in widget.get_children():
            alloc = child.get_allocation()
            if ( alloc.width < self.frame_sz_min[0] or
                 alloc.height < self.frame_sz_min[1]
                 ):
                self.rm_frame(widget, child)
                break
    ### end of signal for MWF

    def add_paned(self, parent, pos):
        child = parent.child

        # create new paned
        if pos in self.__ctrl_pos['h']:
            paned = gtk.HPaned()
        else:
            paned = gtk.VPaned()

        # create new frame
        if self.frame_split_dup:
            new_child = self.frame_split_dup(self.active_frame)
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

        parent.show_all()
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

    def update_mw(self, pos):
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
######## ######## ######## ######## 
######## ######## ######## ######## 


class zEdit(gtk.VBox):
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
        self.bottom = gtk.HBox()
        self.pack_end(self.bottom, False, False, 0)

        # create buffer switcher
        self.buffer_sw_tm = gtk.ListStore(str, bool) # define TreeModel
        for buff in zEditBuffer.SYSTEM_BUFFER:  # add all system-opened buffers
            self.buffer_sw_tm.append([buff, False])
        self.buffer_sw_tm.append(['NanI', True]) # not an item, this item should not be seen

        self.buffer_sw = gtk.ComboBox(self.buffer_sw_tm)
        self.bottom.pack_start(self.buffer_sw, False, False, 0)

        self.buffer_sw_cell = gtk.CellRendererText()
        self.buffer_sw.pack_start(self.buffer_sw_cell, True)
        self.buffer_sw.add_attribute(self.buffer_sw_cell, "text", 0)
        self.buffer_sw.set_row_separator_func(self.separater)

        # init the switcher
        self.buffer_iter = self.buffer_sw_tm.get_iter_first()
        while self.buffer_sw_tm.get_value(self.buffer_iter, 0) != zEditBuffer.DEFAULT_BUFFER:
            self.buffer_iter = self.buffer_sw_tm.iter_next(self.buffer_iter)
        self.buffer_sw.set_active_iter(self.buffer_iter)

        # set font
        self.set_font('monospace', 10) # default font


    def connect_center(self, sig, cb):
        if sig in [ 'populate-popup' ]:
            if self.active_buffer.type == 'textview':
                return self.center.connect(sig, cb)

    def separater(self, model, iter, data = None):
        return model.get_value(iter, 1)

    def get_font(self):
        return self.font

    def set_font(self, font_name, font_size):
        self.font = ( font_name, font_size )

        self.center.modify_font(
            pango.FontDescription('{0} {1}'.format(font_name, font_size))
            )

        self.buffer_sw_cell.set_property(
            'font-desc',
            pango.FontDescription('{0} {1}'.format(font_name, int(font_size * 0.75)))
            )

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


class zEditBuffer(object):
    DEFAULT_BUFFER = '*scratch*'
    SYSTEM_BUFFER = {
        '*scratch*' : 'textview',
        }
    buff_list = {
        # 'buff_sys'    : zEditBuffer()
        # 'buff_user'   : zEditBuffer()
        # 'buff_sys(1)' : zEditBuffer()
        # 'buff_sys(2)' : zEditBuffer()
        #  ...
        }
    buff_group = {
        'system' : [], # [ 'buff_sys', 'buff_sys(1)', 'buff_sys(2)', ]
        'user'   : [], # [ 'buff_user', ]
        }
    buff_rec = { # no-removal record
        # 'buff_sys'  : [ ( 'buff_sys',    buff_path, opened ),
        #                 ( 'buff_sys(1)', buff_path, opened ),
        #                 ( 'buff_sys(2)', buff_path, opened ),
        #                 ],
        # 'buff_user' : [ ( 'buff_user',  buff_user_path, opened ),
        #                 ],
        #  ...
        }

    def __new__(cls, buffer_path = None, buffer_type = None):
        self = object.__new__(cls)
        if buffer_path == None:
            buffer_path = self.DEFAULT_BUFFER

        buff_group = 'user'     # assume user-opened buffer
        if isinstance(buffer_path, str):
            self.name = buffer_path
            if buffer_path in self.SYSTEM_BUFFER:
                # system-opened buffer
                buff_group = 'system'
                self.path = None
                self.type = self.SYSTEM_BUFFER[self.name]
            else:       # treat as a single node, add [] around
                self.path = [ buffer_path ]
                self.type = buffer_type
        else:
            self.name = buffer_path[-1]
            self.path = buffer_path
            self.type = buffer_type

        no_rec = True           # assume first encounter of the name
        if self.name in self.buff_rec:
            # name is recorded, check for duplication
            for [name, path, opened] in self.buff_rec[self.name]:
                if path == self.path:
                    # same path ==> has record
                    no_rec = False

                    if opened:
                        # return old file reference
                        return self.buff_list[name] # early return
                    else:
                        # re-open it
                        self.name = name
                        break
            if no_rec:
                # no duplication, generate new name of the new file
                self.name += "(" + str(len(self.buff_rec[self.name])) + ")"

        if no_rec:
            # name not in record, add it
            self.buff_rec[self.name] = [ (self.name, self.path, True) ]
        self.buff_list[self.name] = self
        self.buff_group[buff_group].append(self.name)

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
