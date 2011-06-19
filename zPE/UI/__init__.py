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
        self.root = gtk.Window(gtk.WINDOW_TOPLEVEL)

        self.root.connect("delete_event", self.delete_event)
        self.root.connect("destroy", self.destroy)

        self.root.set_title("zPE - Mainframe Programming Environment Simulator")
        self.root.set_icon_from_file( os.path.join(
                os.path.dirname(__file__), "image", "icon_zPE.svg"
                ) )
        self.root.set_size_request(600, 400)

        agr = gtk.AccelGroup()
        self.root.add_accel_group(agr)

        ### create layout
        w_vbox = gtk.VBox()
        self.root.add(w_vbox)

        ### create menu bar
        self.menubar = gtk.MenuBar()
        w_vbox.pack_start(self.menubar, False, False, 0)

        ## file menu
        m_file = gtk.MenuItem("_File")
        sm_file = gtk.Menu()
        m_file.set_submenu(sm_file)
        self.menubar.append(m_file)

        # file menu item - new
        mi_new = gtk.ImageMenuItem(gtk.STOCK_NEW, agr)
        sm_file.append(mi_new)
	 
        # file menu item - open
        mi_open = gtk.ImageMenuItem(gtk.STOCK_OPEN, agr)
        sm_file.append(mi_open)
	 
        # file menu item - separator
        sm_file.append(gtk.SeparatorMenuItem())
	 
        # file menu item - quit
        mi_quit = gtk.ImageMenuItem(gtk.STOCK_QUIT, agr)
        mi_quit.connect("activate", gtk.main_quit)
        sm_file.append(mi_quit)


        ## view menu
        m_view = gtk.MenuItem("_View")
        sm_view = gtk.Menu()
        m_view.set_submenu(sm_view)
        self.menubar.append(m_view)
	 
        # view menu item - status bar
        mi_stat = gtk.CheckMenuItem("View Statusbar")
        mi_stat.set_active(True)
        mi_stat.connect("activate", self.on_status_active)
        sm_view.append(mi_stat)


        ### create status bar
        self.statusbar = gtk.Statusbar()
        self.statusbar.push(1, "Ready")
        w_vbox.pack_end(self.statusbar, False, False, 0)


        ### create main window
        self.mw = comp.MainWindow()
        w_vbox.pack_start(self.mw, True, True, 0)


        ### show all parts
        self.root.show_all()


    def toggle_status(self, widget):
        widget.set_active(not widget.active)
        self.on_status_active(widget)

    def on_status_active(self, widget):
        if widget.active:
            self.statusbar.show()
        else:
            self.statusbar.hide()


    def main(self):
        gtk.main()
