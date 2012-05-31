# this is the frame module of the zComponent package

from zPE.GUI.zComp.z_support     import XPM, PIXBUF, SUPPORT

from zPE.GUI.zComp.zBase         import z_ABC, zTheme
from zPE.GUI.zComp.zEditorFrame  import zEdit
from zPE.GUI.zComp.zStrokeParser import zStrokeListener

import os, sys, time
import pygtk
pygtk.require('2.0')
import gtk
import gobject


######## ######## ######## ######## ########
########        zSplitWindow        ########
######## ######## ######## ######## ########

class zSplitWindow(z_ABC, gtk.Frame):
    '''A Split-Window Frame with DnD Splitting Supported'''
    global_func_list = [
        'window-split-horz',
        'window-split-vert',
        'window-delete',
        'window-delete-other',
        ]
    # only make the following function bindable, no actual binding applied
    zStrokeListener.global_add_func_registry(global_func_list)

    func_callback_map = {}      # if set, will override the default setting for newly added instance

    def func_callback_map_generator(self, frame):
        rv_dic = {
            'window-split-horz'   : lambda msg: self.window_split_horz(frame),
            'window-split-vert'   : lambda msg: self.window_split_vert(frame),
            'window-delete'       : lambda msg: self.window_delete(frame),
            'window-delete-other' : lambda msg: self.window_delete_other(frame),
            }
        if zSplitWindow.func_callback_map:
            for (k, v) in zSplitWindow.func_callback_map.iteritems():
                if k in zSplitWindow.global_func_list:
                    rv_dic[k] = v

        return rv_dic


    _auto_update = {
        # 'signal_like_string'  : [ callback, ... ]
        'frame_removed'         : [  ],
        }

    __handle_sz = max(
        gtk.HPaned().style_get_property('handle-size'),
        gtk.VPaned().style_get_property('handle-size')
        )

    def __init__(self,
                 frame = zEdit, frame_alist = [],
                 frame_init = (None, None),
                 frame_split_dup = None,
                 frame_sz_min = (50, 50)
                 ):
        '''
        frame = zEdit
            a construction function of a GtkWidget which will be
            the frame of the inner window.

            e.g. zComp.zSplitWindow(gtk.Label)

        frame_alist = []
            the argument list of the "frame".

            e.g. zComp.zSplitWindow(gtk.Label, ['Test Label'])

        frame_init = (None, None)
            a tuple containing two callback functions that will be
            called after every creation/destruction of the "frame"
            to initialize/un-initialize it
            (connect/disconnect signals, for example)

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
        super(zSplitWindow, self).__init__()


        self.frame = frame
        self.frame_alist = frame_alist
        self.frame_init = frame_init
        self.frame_split_dup = frame_split_dup
        self.frame_sz_min = frame_sz_min

        if issubclass(self.frame, zEdit) and not self.frame_alist:
            self.frame_alist = [ None, None, self.func_callback_map_generator ]

        # layout of the zSplitWindow:
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
        self.mw_new_child_frame = None

        # remove shadow
        self.set_shadow_type(gtk.SHADOW_NONE)
        self.mw_center.set_shadow_type(gtk.SHADOW_NONE)

        root_frame.attach(self.ctrl_bar['lt'], 0, 1, 1, 2, xoptions = gtk.SHRINK)
        root_frame.attach(self.ctrl_bar['rt'], 2, 3, 1, 2, xoptions = gtk.SHRINK)
        root_frame.attach(self.ctrl_bar['tp'], 1, 2, 0, 1, yoptions = gtk.SHRINK)
        root_frame.attach(self.ctrl_bar['bm'], 1, 2, 2, 3, yoptions = gtk.SHRINK)
        root_frame.attach(self.mw_center,      1, 2, 1, 2)

        # connect signals for center frame
        self.__alloc = None
        self.mw_center.__alloc = None

        self.connect('size-allocate', self._sig_realloc)
        self.mw_center.connect('size-allocate', self._sig_check_realloc)

        # connect signals for control-bars
        for pos in self.__ctrl_pos['a']:
            self.ctrl_bar[pos].set_property('can-default', False)
            self.ctrl_bar[pos].set_property('can-focus', False)
            self.ctrl_bar[pos].connect_object('clicked', self.window_split, self.mw_center, pos)
            self.ctrl_bar[pos].drag_source_set(gtk.gdk.BUTTON1_MASK, [], 0)
            self.ctrl_bar[pos].connect('drag_begin', self._sig_ctrl_drag, PIXBUF['empty'], pos)
            self.ctrl_bar[pos].connect('button-release-event', self._sig_ctrl_drop, pos)


    ### signal for resizing
    def _sig_realloc(self, widget, alloc):
        if self.__alloc != alloc:
            # allocation changed
            self.__alloc = alloc
            self.mw_center.__alloc = self.mw_center.get_allocation()

    def _sig_check_realloc(self, widget, alloc):
        ( req_w, req_h ) =  self.mw_center.size_request()
        alloc = self.mw_center.__alloc
        if not alloc:
            return              # not allocated, early return

        if alloc.height < req_h:
            # must be caused by adding frame
            self.window_delete(self.mw_new_child_frame)
            if self.__prev_active_frame:
                self.__prev_active_frame.grab_focus()
                sys.stderr.write('Warning: No room for new screens vertically!\n')

        if alloc.width < req_w:
            # no way to determine the cause, force resizing child
            self.mw_center.child.set_size_request(alloc.width - 4, -1)
    ### end of signal for resizing


    ### signal for DnD
    def _sig_ctrl_drag(self, widget, context, icon, pos):
        context.set_icon_pixbuf(icon, 0, 0)

        # create the shading-layer
        root = widget.get_root_window()
        screen = gtk.gdk.screen_get_default()

        alloc = self.mw_center.get_allocation()
        self.sd_w = alloc.width
        self.sd_h = alloc.height
        if SUPPORT['rgba']:
            visual = screen.get_rgba_visual()
            colormap = screen.get_rgba_colormap()
        else:
            if pos in self.__ctrl_pos['h']:
                self.sd_w = self.__handle_sz
            else:
                self.sd_h = self.__handle_sz
            visual = screen.get_rgb_visual()
            colormap = screen.get_rgb_colormap()

        self.sd_layer = gtk.gdk.Window(
            root, self.sd_w, self.sd_h,
            gtk.gdk.WINDOW_TEMP,
            gtk.gdk.ALL_EVENTS_MASK,
            gtk.gdk.INPUT_OUTPUT,
            '', 0, 0,
            visual, colormap, gtk.gdk.Cursor(gtk.gdk.PLUS),
            '', '', True
            )
        self.sd_layer.show()

        # create the cairo context
        self.sd_layer_cr = self.sd_layer.cairo_create()

        self.sd_layer_cr.set_line_width(1)
        # set shade color
        sd_fg_rgb = [ int(zTheme.color_map['text'][i:i+2], 16) / 255.0 # scale hex color code to [0, 1]
                      for i in [ 1, 3, 5 ] # starting index in pattern '#rrggbb'
                      ]
        sd_bg_rgb = [ int(zTheme.color_map['base'][i:i+2], 16) / 255.0 # scale hex color code to [0, 1]
                      for i in [ 1, 3, 5 ] # starting index in pattern '#rrggbb'
                      ]
        if SUPPORT['rgba']:
            alpha = 0.3
            self.sd_layer_cr.set_source_rgba(* (sd_fg_rgb + [ alpha ]))
        else:
            alpha = 0.5
            self.sd_layer_cr.set_source_rgb(* [ sd_fg_rgb[i] * alpha + sd_bg_rgb[i] * (1 - alpha) for i in range(3) ])

        # start the timer
        self.mw_center.timer = True
        gobject.timeout_add(20, self.__update_sd, pos)

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

        correct_pos = self.__correct_pos(
            ptr_pos,                              # the current ptr pos
            (0, 0),                               # the frame size - low bound
            (alloc.width, alloc.height),          # the frame size - high bound
            [sp + 20 for sp in self.frame_sz_min] # the min spacing + 20
            )

        # add paned if in center
        if correct_pos:
            paned = self.window_split(self.mw_center, pos)

            # re-position the newly added frame
            if pos in self.__ctrl_pos['h']:
                # - handle_sz cancel the width of the divider
                paned.set_position(correct_pos[0] - self.__handle_sz / 2)
            else:
                paned.set_position(correct_pos[1] - self.__handle_sz / 2)
    ### end of signal for DnD

    ### signal for center frame
    def _sig_div_drop(self, widget, event):
        for child in widget.get_children():
            alloc = child.get_allocation()
            if ( alloc.width < self.frame_sz_min[0] or
                 alloc.height < self.frame_sz_min[1]
                 ):
                # record focus
                focus = self.active_frame() # get focused frame
                if self.__active_frame(child):
                    focus = None # focus in child_rm, delete it

                # remove the child
                self.window_delete(child)

                # adjust focus
                if not focus:
                    self.grab_focus()
                else:
                    focus.grab_focus()
                break
    ### end of signal for center frame


    ### overridden function definition
    @classmethod
    def register(cls, sig, callback):
        '''This function register a function to a signal-like string'''
        cls._auto_update[sig].append(callback)

    @classmethod
    def unregister(cls, sig, callback):
        '''This function un-register a function from a signal-like string'''
        reserve = []
        for cb in cls._auto_update[sig]:
            if callback != cb:
                reserve.append(cb)
        cls._auto_update[sig] = reserve

    @classmethod
    def reg_emit(cls, sig):
        '''This function emit the signal to all registered object'''
        for cb in cls._auto_update[sig]:
            cb()

    def is_focus(self):
        return self.active_frame() != None

    def grab_focus(self):
        child = self.mw_center.child
        while not isinstance(child, self.frame):
            child = child.get_children()[0]
        child.grab_focus()
    ### end of overridden function definition


    ### split window manipulation
    def window_split(self, widget, pos):
        # setup backup point
        self.__prev_active_frame = self.active_frame() # only used in resuming focus on removing newly added frame

        if isinstance(widget, self.frame):
            # widget is a frame
            parent = widget.parent
            child = widget
        else:
            # widget is a container
            # for now, should always be self.mw_center
            parent = widget
            child = widget.child

        # create new paned
        if pos in self.__ctrl_pos['h']:
            paned = gtk.HPaned()
        else:
            paned = gtk.VPaned()

        # create new frame
        if self.frame_split_dup:
            self.mw_new_child_frame = self.new_frame_on_dup(self.frame_alist)
        else:
            self.mw_new_child_frame = self.new_frame(self.frame_alist)

        # re-parent the widgets
        parent.remove(child)
        if pos in self.__ctrl_pos['b']:
            paned.pack1(self.mw_new_child_frame, True, True)
            paned.pack2(child, True, True)
        else:
            paned.pack1(child, True, True)
            paned.pack2(self.mw_new_child_frame, True, True)

        if isinstance(parent, gtk.Paned):
            # parent is a paned
            if not parent.get_child1():
                parent.pack1(paned, True, True)
            else:
                parent.pack2(paned, True, True)
        else:
            # parent is not a paned
            parent.add(paned)

        # connect signals
        paned.connect('button-release-event', self._sig_div_drop)

        # show widgets
        parent.show_all()
        self.mw_new_child_frame.grab_focus()

        return paned


    def window_split_horz(self, frame):
        self.window_split(frame, 'rt')

    def window_split_vert(self, frame):
        self.window_split(frame, 'bm')

    def window_delete(self, child_rm):
        widget = child_rm.parent

        if widget == self.mw_center:    # the only frame
            widget.remove(child_rm)
            widget.add(self.new_frame(self.frame_alist))

        else:
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
                parent.remove(widget)
                if not parent.get_child1():
                    parent.pack1(child_kp, True, True)
                else:
                    parent.pack2(child_kp, True, True)

        # clean up
        child_rm.hide_all()
        zSplitWindow.reg_emit('frame_removed')

    def window_delete_other(self, frame):
        widget = frame.parent

        if widget == self.mw_center:    # the only frame
            return

        # get the frame off
        widget.remove(frame)

        # remove all other frames but the frame
        child_rm = self.mw_center.child
        self.mw_center.remove(child_rm)
        self.mw_center.add(frame)

        # clean up
        child_rm.hide_all()
        zSplitWindow.reg_emit('frame_removed')

        self.grab_focus()
    ### end of split window manipulation


    def active_frame(self):
        return self.__active_frame(self.mw_center)


    def new_frame(self, alist):
        # prepare frame info
        frame = self.frame(* alist)

        frame.set_init_func(self.frame_init)
        frame.exec_init_func()

        return frame

    def new_frame_on_dup(self, alist):
        # prepare frame info
        frame = self.frame_split_dup(self.active_frame(), alist)

        frame.set_init_func(self.frame_init)
        frame.exec_init_func()

        return frame


    ### supporting function
    def __active_frame(self, current):
        '''recursive function, should start with zSplitWindow.mw_center'''
        if isinstance(current, self.frame):
            if current.is_focus():
                return current  # found the frame
            else:
                return None     # end of the path

        for child in current.get_children():
            found = self.__active_frame(child)
            if found:
                return found    # found in previous search
        return None             # not found at all


    def __correct_pos(self, pos, limit_low, limit_high, spacing):
        '''all three args should all be tuples/lists with the same length'''
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


    def __update_sd(self, pos):
        '''used with `timer`'''
        if not self.mw_center.timer:
            return False

        # calculate position
        root = self.mw_center.get_root_window()
        alloc = self.mw_center.get_allocation()
        ( ptr_x,     ptr_y     ) = self.mw_center.get_pointer()
        ( ptr_abs_x, ptr_abs_y ) = root.get_pointer()[:2]
        ( base_x,    base_y    ) = ( ptr_abs_x - ptr_x, ptr_abs_y - ptr_y )

        # validate position
        correct_pos = self.__correct_pos(
            (ptr_x, ptr_y),                       # the current ptr pos
            (0, 0),                               # the frame size - low bound
            (alloc.width, alloc.height),          # the frame size - high bound
            [sp + 10 for sp in self.frame_sz_min] # the min spacing + 10
            )

        if correct_pos:
            self.sd_layer.show()
        else:
            self.sd_layer.hide()
            return True

        # draw on shading-layer
        if SUPPORT['rgba']:
            if pos == 'lt':
                self.sd_layer.move_resize(base_x,    base_y,    ptr_x,             self.sd_h        )
            elif pos == 'tp':
                self.sd_layer.move_resize(base_x,    base_y,    self.sd_w,         ptr_y            )
            elif pos == 'rt':
                self.sd_layer.move_resize(ptr_abs_x, base_y,    self.sd_w - ptr_x, self.sd_h        )
            else:
                self.sd_layer.move_resize(base_x,    ptr_abs_y, self.sd_w,         self.sd_h - ptr_y)
        else:
            if pos in self.__ctrl_pos['h']:
                self.sd_layer.move(ptr_abs_x - self.sd_w / 2, base_y)
            else:
                self.sd_layer.move(base_x, ptr_abs_y - self.sd_h / 2)

        self.sd_layer_cr.rectangle(0, 0, self.sd_w, self.sd_h)
        self.sd_layer.clear()
        self.sd_layer_cr.fill()


        return True
    ### end of supporting function
