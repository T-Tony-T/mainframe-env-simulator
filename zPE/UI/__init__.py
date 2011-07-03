# modules that will be auto imported
import comp, conf

import os, sys
import pygtk
pygtk.require('2.0')
import gtk


class BaseFrame(object):
    def delete_event(self, widget, event, data = None):
        # change FALSE to TRUE and the main window will not be destroyed
        # with a "delete_event".
        return False

    def __init__(self):
        conf.read_rc()

        ### create top-level frame
        self.root = gtk.Window(gtk.WINDOW_TOPLEVEL)

        self.root.connect("delete_event", self.delete_event)
        self.root.connect("destroy", self._sig_quit)

        self.root.set_title("zPE - Mainframe Programming Environment Simulator")
        self.root.set_icon_from_file( os.path.join(
                os.path.dirname(__file__), "image", "icon_zPE.svg"
                ) )
        self.root.set_size_request(800, 560)

        ### create layout
        w_vbox = gtk.VBox()
        self.root.add(w_vbox)

        ### create toolbar
        self.toolbar = gtk.Toolbar()
        w_vbox.pack_start(self.toolbar, False, False, 0)

        self.toolbar.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        self.toolbar.set_style(gtk.TOOLBAR_ICONS)
        self.toolbar.set_tooltips(True)

        ## create toolbar buttons
        self.tool_buff_open = gtk.ToolButton(gtk.STOCK_OPEN)
        self.tool_buff_open.set_tooltip_text('Open a New Buffer')
        self.tool_buff_save = gtk.ToolButton(gtk.STOCK_SAVE)
        self.tool_buff_save.set_tooltip_text('Save Current Buffer')
        self.tool_buff_save_as = gtk.ToolButton(gtk.STOCK_SAVE_AS)
        self.tool_buff_save_as.set_tooltip_text('Save Current Buffer As ...')
        self.tool_buff_close = gtk.ToolButton(gtk.STOCK_CLOSE)
        self.tool_buff_close.set_tooltip_text('Close Current Buffer')

        self.tool_quit = gtk.ToolButton(gtk.STOCK_QUIT)
        self.tool_quit.set_tooltip_text('Quit the Simulator')

        ## insert toolbar buttons
        self.toolbar.insert(self.tool_buff_open, 0)
        self.toolbar.insert(self.tool_buff_save, 1)
        self.toolbar.insert(self.tool_buff_save_as, 2)
        self.toolbar.insert(self.tool_buff_close, 3)
        self.toolbar.insert(gtk.SeparatorToolItem(), 4)
        self.toolbar.insert(self.tool_quit, 5)

        ## connect signals
        self.tool_quit.connect('clicked', self._sig_quit)


        ### create main window
        self.mw = comp.SplitScreen(comp.zEdit, [], self.frame_init, self.frame_split_dup)
        w_vbox.pack_start(self.mw, True, True, 0)


        ### create last-line
        self.lastline = comp.LastLine('z# ')
        w_vbox.pack_end(self.lastline, False, False, 0)

        ### set accel
        self.agr = gtk.AccelGroup()
        self.root.add_accel_group(self.agr)

        # C-q ==> fouce quit
        self.agr.connect_group(
            gtk.gdk.keyval_from_name('q'),
            gtk.gdk.CONTROL_MASK,
            gtk.ACCEL_VISIBLE,
            lambda *s: self._sig_quit(None)
            )

        ### show all parts
        self.agr.lock()
        w_vbox.set_focus_chain((self.mw, self.lastline)) # prevent toolbar from getting focus
        self.root.show_all()


    ### top level signals
    def _sig_quit(self, widget, data = None):
        #########################
        # check save here       #
        #########################
        gtk.main_quit()
    ### end of top level signals


    ### signals for SplitScreen
    def _sig_popup_manip(self, widget, menu):
        menu.append(gtk.SeparatorMenuItem())
        menu.append(gtk.MenuItem("test"))
        menu.show_all()
    ### end of signals for SplitScreen


    ### callback functions for SplitScreen
    def frame_init(self, frame):
        frame.set_font({ 'name' : 'monospace', 'size' : conf.Config['font_sz'] })
        frame.ct_pop_id = frame.connect('populate-popup', self._sig_popup_manip)

    def frame_split_dup(self, frame):
        if frame:
            new_frame = comp.zEdit(* frame.get_buffer())
        else:
            new_frame = comp.zEdit()

        self.frame_init(new_frame)
        return new_frame
    ### end of callback functions for SplitScreen



    def main(self):
        gtk.main()

