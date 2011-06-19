# this is the UI components file

import os, sys
import pygtk
pygtk.require('2.0')
import gtk


class MainWindow(gtk.Frame):
    def __init__(self):
        super(MainWindow, self).__init__()

        # layout of the frame:
        # 
        #   0 1          2 3
        # 0 +-+----------+-+ 0
        #   | |    top   | |
        # 1 +-+----------+-+ 1
        #   | |          | |
        #   |l|   Main   |r|
        #   |e|  Window  |i|
        #   |f|  Center  |g|
        #   |t|          |h|
        #   | |          |t|
        # 2 +-+----------+-+ 2
        #   | |  bottom  | |
        # 3 +-+----------+-+ 3
        #   0 1          2 3

        root_frame = gtk.Table(3, 3, False)
        self.add(root_frame)

        self.bttn_lt = gtk.Button()
        self.bttn_rt = gtk.Button()
        self.bttn_tp = gtk.Button()
        self.bttn_bm = gtk.Button()
        self.mw_center = gtk.Frame()
        self.mw_center.add(MainWindowFrame())

        root_frame.attach(self.bttn_lt, 0, 1, 1, 2, xoptions=0)
        root_frame.attach(self.bttn_rt, 2, 3, 1, 2, xoptions=0)
        root_frame.attach(self.bttn_tp, 1, 2, 0, 1, yoptions=0)
        root_frame.attach(self.bttn_bm, 1, 2, 2, 3, yoptions=0)
        root_frame.attach(self.mw_center, 1, 2, 1, 2)

        self.bttn_lt.connect_object("clicked", self.add_frame, self.mw_center, "lt")
        self.bttn_rt.connect_object("clicked", self.add_frame, self.mw_center, "rt")
        self.bttn_tp.connect_object("clicked", self.add_frame, self.mw_center, "tp")
        self.bttn_bm.connect_object("clicked", self.add_frame, self.mw_center, "bm")



    def add_frame(self, parent, pos):
        child = parent.child
        if pos in ("lt", "rt"):
            paned = gtk.HPaned()
        else:
            paned = gtk.VPaned()
        parent.remove(child)
        parent.add(paned)
        if pos in ("lt", "tp"):
            paned.pack1(MainWindowFrame(), True, False)
            paned.pack2(child, True, False)
        else:
            paned.pack1(child, True, False)
            paned.pack2(MainWindowFrame(), True, False)
        parent.show_all()



class MainWindowFrame(gtk.VBox):
    def __init__(self):
        super(MainWindowFrame, self).__init__()

        self.center = gtk.Frame()
        self.pack_start(self.center, True, True, 0)

        self.bottom = gtk.Button("test")
        self.pack_end(self.bottom, False, False, 0)
