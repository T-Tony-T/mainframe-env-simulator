# modules that will be auto imported
import comp

import os, sys
import pygtk
pygtk.require('2.0')
import gtk


class BaseFrame(object):
    def delete_event(self, widget, event, data = None):
        # change FALSE to TRUE and the main window will not be destroyed
        # with a "delete_event".
        return False

    def destroy(self, widget, data = None):
        gtk.main_quit()

    def __init__(self):
        ### create top-level frame
        self.w = gtk.Window(gtk.WINDOW_TOPLEVEL)

        self.w.connect("delete_event", self.delete_event)
        self.w.connect("destroy", self.destroy)

        self.w.set_title("zPE - Mainframe Programming Environment Simulator")
        self.w.set_icon_from_file( os.path.join(
                os.path.dirname(__file__), "image", "icon_zPE.svg"
                ) )
        self.w.set_size_request(600, 400)

        self.agr = gtk.AccelGroup()
        self.w.add_accel_group(self.agr)

        ### create layout
        self.vbox = gtk.VBox()
        self.w.add(self.vbox)

        ### create menu bar
        self.mb = gtk.MenuBar()
        self.vbox.pack_start(self.mb, False, False, 0)

        ## file menu
        self.m_file = gtk.MenuItem("_File")
        self.sm_file = gtk.Menu()
        self.m_file.set_submenu(self.sm_file)
        self.mb.append(self.m_file)

        # file menu item - new
        self.mi_new = gtk.ImageMenuItem(gtk.STOCK_NEW, self.agr)
        self.sm_file.append(self.mi_new)
	 
        # file menu item - open
        self.mi_open = gtk.ImageMenuItem(gtk.STOCK_OPEN, self.agr)
        self.sm_file.append(self.mi_open)
	 
        # file menu item - separator
        self.sm_file.append(gtk.SeparatorMenuItem())
	 
        # file menu item - quit
        self.mi_quit = gtk.ImageMenuItem(gtk.STOCK_QUIT, self.agr)
        self.mi_quit.connect("activate", gtk.main_quit)
        self.sm_file.append(self.mi_quit)


        ## view menu
        self.m_view = gtk.MenuItem("_View")
        self.sm_view = gtk.Menu()
        self.m_view.set_submenu(self.sm_view)
        self.mb.append(self.m_view)
	 
        # view menu item - status bar
        self.mi_stat = gtk.CheckMenuItem("View Statusbar")
        self.mi_stat.set_active(True)
        self.mi_stat.connect("activate", self.on_status_active)
        self.sm_view.append(self.mi_stat)


        ### create status bar
        self.sb = gtk.Statusbar()
        self.sb.push(1, "Ready")
        self.vbox.pack_end(self.sb, False, False, 0)


        ### create main window
        self.mw = comp.MainWindow()
        self.vbox.pack_start(self.mw, True, True, 0)


        ### show all parts
        self.w.show_all()


    def toggle_status(self, widget):
        widget.set_active(not widget.active)
        self.on_status_active(widget)

    def on_status_active(self, widget):
        if widget.active:
            self.sb.show()
        else:
            self.sb.hide()


    def main(self):
        gtk.main()
