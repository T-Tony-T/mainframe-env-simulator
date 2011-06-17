# this is the UI components file

import os, sys
import pygtk
pygtk.require('2.0')
import gtk


class MainWindowFrame(gtk.Frame):
    def __init__(self):
        super(MainWindowFrame, self).__init__()

        self.table = gtk.Table(3, 3, False)
        self.add(self.table)

        self.bttn_up = gtk.Button()
        self.bttn_down = gtk.Button()
        self.bttn_left = gtk.Button()
        self.bttn_right = gtk.Button()

        self.table.attach(
            self.bttn_up,
            1, 2, 0, 1,
            yoptions=gtk.FILL
            )
        self.table.attach(
            self.bttn_down,
            1, 2, 2, 3,
            yoptions=gtk.FILL
            )
        self.table.attach(
            self.bttn_left,
            0, 1, 1, 2,
            xoptions=gtk.FILL
            )
        self.table.attach(
            self.bttn_right,
            2, 3, 1, 2,
            xoptions=gtk.FILL
            )


class MainWindow(gtk.Frame):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.mw = MainWindowFrame()
        self.add(self.mw)

