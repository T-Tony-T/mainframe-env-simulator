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

        self.ctrl_paned = {}
        self.ctrl_paned_id = {}

        self.ctrl_paned['lt'] = gtk.Frame()
        paned = gtk.HPaned()
        dummy = ( gtk.Layout(), gtk.Layout() )
        paned.pack1(dummy[0], False, True)
        paned.pack2(dummy[1], False, True)
        dummy[0].set_size_request(1, -1)
        dummy[1].set_size_request(1, -1)
        self.ctrl_paned['lt'].add(paned)

        self.ctrl_paned['rt'] = gtk.Frame()
        paned = gtk.HPaned()
        dummy = ( gtk.Layout(), gtk.Layout() )
        paned.pack1(dummy[0], False, True)
        paned.pack2(dummy[1], False, True)
        dummy[0].set_size_request(1, -1)
        dummy[1].set_size_request(1, -1)
        self.ctrl_paned['rt'].add(paned)

        self.ctrl_paned['tp'] = gtk.Frame()
        paned = gtk.VPaned()
        dummy = ( gtk.Layout(), gtk.Layout() )
        paned.pack1(dummy[0], False, True)
        paned.pack2(dummy[1], False, True)
        dummy[0].set_size_request(-1, 1)
        dummy[1].set_size_request(-1, 1)
        self.ctrl_paned['tp'].add(paned)

        self.ctrl_paned['bm'] = gtk.Frame()
        paned = gtk.VPaned()
        dummy = ( gtk.Layout(), gtk.Layout() )
        paned.pack1(dummy[0], False, True)
        paned.pack2(dummy[1], False, True)
        dummy[0].set_size_request(-1, 1)
        dummy[1].set_size_request(-1, 1)
        self.ctrl_paned['bm'].add(paned)

        self.mw_center = gtk.Frame()
        self.mw_center.add(MainWindowFrame())
        paned = None            # clear dummy var

        root_frame.attach(self.ctrl_paned['lt'], 0, 1, 1, 2, xoptions=gtk.SHRINK)
        root_frame.attach(self.ctrl_paned['rt'], 2, 3, 1, 2, xoptions=gtk.SHRINK)
        root_frame.attach(self.ctrl_paned['tp'], 1, 2, 0, 1, yoptions=gtk.SHRINK)
        root_frame.attach(self.ctrl_paned['bm'], 1, 2, 2, 3, yoptions=gtk.SHRINK)
        root_frame.attach(self.mw_center,        1, 2, 1, 2)

        self.ctrl_paned_id['lt'] = self.ctrl_paned['lt'].child.connect(
            'notify', self._sig_ctrl_move, self.mw_center, 'lt'
            )
        self.ctrl_paned_id['rt'] = self.ctrl_paned['rt'].child.connect(
            'notify', self._sig_ctrl_move, self.mw_center, 'rt'
            )
        self.ctrl_paned_id['tp'] = self.ctrl_paned['tp'].child.connect(
            'notify', self._sig_ctrl_move, self.mw_center, 'tp'
            )
        self.ctrl_paned_id['bm'] = self.ctrl_paned['bm'].child.connect(
            'notify', self._sig_ctrl_move, self.mw_center, 'bm'
            )


    def _sig_ctrl_move(self, widget, param_spec, target, pos):
        valid_exec = (param_spec.name == 'position')
        if not valid_exec:      # skip non-move action
            return
        try:
            if widget.__sig_ctrl_move_called != None and valid_exec:
                widget.__sig_ctrl_move_called += 1
        except:
            widget.__sig_ctrl_move_called = 0

        if widget.__sig_ctrl_move_called < 1: # skip the first run (on creation)
            return

        if pos in [ 'lt', 'rt', 'tp', 'bm' ]:
            paned = self.add_frame(target, pos) # target should be self.mw_center


    def add_frame(self, parent, pos):
        child = parent.child

        # retrive the ctrl paned and its parent
        paned_parent = self.ctrl_paned[pos]
        paned = self.ctrl_paned[pos].child

        # create new ctrl paned
        if pos in ('lt', 'rt'):
            new_paned = gtk.HPaned()
        else:
            new_paned = gtk.VPaned()

        # re-connect signals
        paned.disconnect(self.ctrl_paned_id[pos])
        paned.connect('notify', self._sig_ctrl_move, self.mw_center, 'ct')
        self.ctrl_paned_id[pos] = new_paned.connect(
            'notify', self._sig_ctrl_move, self.mw_center, pos
            )

        # re-parent the widgets
        child_1 = paned.get_child1()
        child_2 = paned.get_child2()
        paned.remove(child_1)
        paned.remove(child_2)
        new_paned.pack1(child_1, False, True)
        new_paned.pack2(child_2, False, True)

        parent.remove(child)
        paned_parent.remove(paned)

        if pos in ('lt', 'tp'):
            paned.pack1(MainWindowFrame(), True, True)
            paned.pack2(child, True, True)
        else:
            paned.pack1(child, True, True)
            paned.pack2(MainWindowFrame(), True, True)

        parent.add(paned)
        paned_parent.add(new_paned)

        # show all
        paned.set_position(-1)
        parent.show_all()
        paned_parent.show_all()
        return paned


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
