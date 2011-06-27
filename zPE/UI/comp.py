 # this is the UI components file

import zPE

import os, sys
import pygtk
pygtk.require('2.0')
import gtk
import gobject


class MainWindow(gtk.Frame):
    def __init__(self):
        super(MainWindow, self).__init__()

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

        self.__mw_frame_sz = (40, 40) # the minimum size required for each MainWindowFrame
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
        self.mw_center.add(MainWindowFrame())

        root_frame.attach(self.ctrl_bar['lt'], 0, 1, 1, 2, xoptions=gtk.SHRINK)
        root_frame.attach(self.ctrl_bar['rt'], 2, 3, 1, 2, xoptions=gtk.SHRINK)
        root_frame.attach(self.ctrl_bar['tp'], 1, 2, 0, 1, yoptions=gtk.SHRINK)
        root_frame.attach(self.ctrl_bar['bm'], 1, 2, 2, 3, yoptions=gtk.SHRINK)
        root_frame.attach(self.mw_center,        1, 2, 1, 2)

        # connect signals for the control-bars
        drag_icon = gtk.gdk.pixbuf_new_from_file(
            os.path.join(os.path.dirname(__file__), "image", "min_empty.gif")
            )
        for pos in self.__ctrl_pos['a']:
            self.ctrl_bar[pos].set_property('can_focus', False)
            self.ctrl_bar[pos].connect_object('clicked', self.add_frame, self.mw_center, pos)
            self.ctrl_bar[pos].drag_source_set(gtk.gdk.BUTTON1_MASK, [], 0)
            self.ctrl_bar[pos].connect('drag_begin', self._sig_ctrl_drag, drag_icon, pos)
            self.ctrl_bar[pos].connect('button-release-event', self._sig_ctrl_drop)

        self.mw_center.drag_dest_set(gtk.DEST_DEFAULT_HIGHLIGHT, [], 0)
        self.mw_center.connect('drag_motion', self._sig_mw_motion)
        self.mw_center.connect('drag_drop', self._sig_mw_drop)


    def _sig_ctrl_drag(self, widget, context, icon, pos):
        context.set_icon_pixbuf(icon, 0, 0)

        # create the cairo context
        self.mw_center.cr = self.mw_center.window.cairo_create()

        self.mw_center.cr.set_line_width(1)
        self.mw_center.cr.set_source_rgba(0, 0, 0, 0.3)

        alloc = self.mw_center.get_allocation()
        base = self.mw_center.translate_coordinates(widget.get_toplevel(), 0, 0)
        self.mw_center.cr.rectangle(base[0], base[1], alloc.width - 2, alloc.height - 2)
        self.mw_center.cr.clip()

        # start the timer
        self.mw_center.timer = True
        gobject.timeout_add(20, self.update_mw, pos)

    def _sig_ctrl_drop(self, widget, event):
        # stop the timer
        self.mw_center.timer = False

    def _sig_mw_motion(self, widget, context, x, y, time):
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True

    def _sig_mw_drop(self, widget, context, x, y, time):
        pos = zPE.dic_find_key(self.ctrl_bar, context.get_source_widget())
        paned = self.add_frame(self.mw_center, pos)

        # re-position the newly added frame
        alloc = self.mw_center.get_allocation()
        (correct_x, correct_y) = self._correct_pos(
            (x, y),                                     # the current ptr pos
            (alloc.width, alloc.height),                # the frame size
            [sp + 10 for sp in self.__mw_frame_sz]      # the min spacing + 10
            )
        if pos in self.__ctrl_pos['h']:
            # -6 to cancel the width of the divider
            paned.set_position(correct_x - 6)
        else:
            paned.set_position(correct_y - 6)

        context.finish(True, False, time)
        return True

    def _sig_div_drop(self, widget, event):
        for child in widget.get_children():
            alloc = child.get_allocation()
            if ( alloc.width < self.__mw_frame_sz[0] or
                 alloc.height < self.__mw_frame_sz[1]
                 ):
                self.rm_frame(widget, child)
                break

    def add_frame(self, parent, pos):
        child = parent.child

        # create new paned
        if pos in self.__ctrl_pos['h']:
            paned = gtk.HPaned()
        else:
            paned = gtk.VPaned()

        # re-parent the widgets
        parent.remove(child)
        if pos in self.__ctrl_pos['b']:
            paned.pack1(MainWindowFrame(), True, True)
            paned.pack2(child, True, True)
        else:
            paned.pack1(child, True, True)
            paned.pack2(MainWindowFrame(), True, True)
        parent.add(paned)

        # connect signals
        paned.connect('button-release-event', self._sig_div_drop)

        parent.show_all()
        return paned

    def rm_frame(self, widget, child_rm):
        if widget == self.mw_center:    # the only frame
            widget.remove(child_rm)
            widget.add(MainWindowFrame)
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
        self.mw_center.queue_draw()
        while gtk.events_pending():
            gtk.main_iteration()

        if not self.mw_center.timer:
            return False

        alloc = self.mw_center.get_allocation()
        ( x, y ) = self.mw_center.get_pointer()
        ( base_x, base_y ) = self.mw_center.translate_coordinates(
            self.mw_center.get_toplevel(), 0, 0
            )

        if pos == 'lt':
            self.mw_center.cr.rectangle(base_x,     base_y,     x,           alloc.height)
        elif pos == 'tp':
            self.mw_center.cr.rectangle(base_x,     base_y,     alloc.width, y           )
        elif pos == 'rt':
            self.mw_center.cr.rectangle(base_x + x, base_y,     alloc.width, alloc.height)
        else:
            self.mw_center.cr.rectangle(base_x,     base_y + y, alloc.width, alloc.height)
        self.mw_center.cr.fill()

        return True

    # all three args should all be tuples/lists with the same length
    def _correct_pos(self, pos, size, spacing):
        ct_pos = [None] * len(pos)
        for i in range(len(pos)):
            if pos[i] < spacing[i]:
                ct_pos[i] = spacing[i]
            elif pos[i] > size[i] - spacing[i]:
                ct_pos[i] = size[i] - spacing[i]
            else:
                ct_pos[i] = pos[i]
        return ct_pos


class MainWindowFrame(gtk.VBox):
    def __init__(self, widget = None):
        super(MainWindowFrame, self).__init__()

        if widget:
            self.center = widget
        else:
            self.center = gtk.Label("TEST")

        self.pack_start(self.center, True, True, 0)

        self.bottom = gtk.Button('test')
        self.pack_end(self.bottom, False, False, 0)
