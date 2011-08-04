# modules that will be auto imported
import zComp, conf
import zPE.conf

import os, sys, copy, re, subprocess
import pygtk
pygtk.require('2.0')
import gtk
import pango


class BaseFrame(object):
    def delete_event(self, widget, event, data = None):
        # change FALSE to TRUE and the main window will not be destroyed
        # with a "delete_event".
        return False


    def __init__(self):
        self.__global_key_binding_func = {
            'prog_show_config'          : lambda *arg: ( self.config_window.open(), self.lastline.clear(), ),
            'prog_show_error'           : lambda *arg: ( self.err_console.open(),   self.lastline.clear(), ),
            'prog_quit'                 : lambda *arg: self._sig_quit(None),

            'zPE_submit'                : lambda *arg: self._sig_submit(None, 'direct'),
#            'zPE_submit_with_JCL'       : lambda *arg: self._sig_submit(None, 'wrap'),
            }

        # enable the global bindings for all listeners
        zComp.zStrokeListener.global_add_func_registry(self.__global_key_binding_func.keys())
        for func in self.__global_key_binding_func:
            zComp.zStrokeListener.global_set_func_enabled(func, True)

        # register callbacks for function bindings
        for (func, cb) in self.__global_key_binding_func.iteritems():
            zComp.zStrokeListener.global_register_func_callback(func, cb)

        # override the default behavior of the buffer manipulation
        zComp.zEdit.func_callback_map = {
            'buffer_open'               : lambda *arg: self._sig_buff_manip(None, 'open'),
            'buffer_save'               : lambda *arg: self._sig_buff_manip(None, 'save'),
            'buffer_save_as'            : lambda *arg: self._sig_buff_manip(None, 'save-as'),
            'buffer_close'              : lambda *arg: self._sig_buff_manip(None, 'close'),
            }
        # override the default behavior of the split-window manipulation
        zComp.zSplitWindow.func_callback_map = {
            'window_split_horz'         : lambda *arg: self._sig_sw_manip(None, 'split_horz'),
            'window_split_vert'         : lambda *arg: self._sig_sw_manip(None, 'split_vert'),
            'window_delete'             : lambda *arg: self._sig_sw_manip(None, 'delete'),
            'window_delete_other'       : lambda *arg: self._sig_sw_manip(None, 'delete_other'),
            }

        ### redirect STDOUT and STDERR to the error console
        self.err_console = zComp.zErrConsole('zPE Error Console', True)
        sys.stdout = self.err_console
        sys.stderr = self.err_console

        ### retrive configuration
        self.config_window = ConfigWindow()
        self.config_window.load_rc()

        ### create top-level frame
        self.root = gtk.Window(gtk.WINDOW_TOPLEVEL)

        self.root.connect('delete_event', self.delete_event)
        self.root.connect('destroy', self._sig_quit)

        self.root.set_title('zPE - Mainframe Programming Environment Simulator')
        self.root.set_icon_from_file( os.path.join(
                os.path.dirname(__file__), 'image', 'icon_zPE.gif'
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
        self.toolbar.set_icon_size(gtk.ICON_SIZE_LARGE_TOOLBAR)
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
        # ------------------------
        bttn_icon = gtk.image_new_from_file(
            os.path.join(os.path.dirname(__file__), 'image', 'window_split_horz.png')
            )
        self.tool_win_split_horz = gtk.ToolButton(bttn_icon)
        self.tool_win_split_horz.set_tooltip_text('Split Current Focused Window Horizontally')
        bttn_icon = gtk.image_new_from_file(
            os.path.join(os.path.dirname(__file__), 'image', 'window_split_vert.png')
            )
        self.tool_win_split_vert = gtk.ToolButton(bttn_icon)
        self.tool_win_split_vert.set_tooltip_text('Split Current Focused Window Vertically')
        bttn_icon = gtk.image_new_from_file(
            os.path.join(os.path.dirname(__file__), 'image', 'window_delete.png')
            )
        self.tool_win_delete = gtk.ToolButton(bttn_icon)
        self.tool_win_delete.set_tooltip_text('Close Current Focused Frame')
        bttn_icon = gtk.image_new_from_file(
            os.path.join(os.path.dirname(__file__), 'image', 'window_delete_other.png')
            )
        self.tool_win_delete_other = gtk.ToolButton(bttn_icon)
        self.tool_win_delete_other.set_tooltip_text('Close All Frames but the Current One')
        # ------------------------
        bttn_icon = gtk.image_new_from_file(
            os.path.join(os.path.dirname(__file__), 'image', 'submit.png')
            )
        self.tool_submit = gtk.ToolButton(bttn_icon)
        self.tool_submit.set_tooltip_text('Submit the Job File')
        bttn_icon = gtk.image_new_from_file(
            os.path.join(os.path.dirname(__file__), 'image', 'submit_test.png')
            )
        self.tool_submit_wrap = gtk.ToolButton(bttn_icon)
        self.tool_submit_wrap.set_tooltip_text('Test Run the Job File With Default JCL')
        # ------------------------
        self.tool_config = gtk.ToolButton(gtk.STOCK_PREFERENCES)
        self.tool_config.set_tooltip_text('Show the Config Window')
        self.tool_err_console = gtk.ToolButton(gtk.STOCK_DIALOG_WARNING)
        self.tool_err_console.set_tooltip_text('Show the Error Console')
        self.tool_quit = gtk.ToolButton(gtk.STOCK_QUIT)
        self.tool_quit.set_tooltip_text('Quit the Simulator')

        ## insert toolbar buttons
        self.toolbar.insert(self.tool_buff_open, 0)
        self.toolbar.insert(self.tool_buff_save, 1)
        self.toolbar.insert(self.tool_buff_save_as, 2)
        self.toolbar.insert(self.tool_buff_close, 3)

        self.toolbar.insert(gtk.SeparatorToolItem(), 4)

        self.toolbar.insert(self.tool_win_split_horz, 5)
        self.toolbar.insert(self.tool_win_split_vert, 6)
        self.toolbar.insert(self.tool_win_delete, 7)
        self.toolbar.insert(self.tool_win_delete_other, 8)

        self.toolbar.insert(gtk.SeparatorToolItem(), 9)

        self.toolbar.insert(self.tool_submit, 10)
        self.toolbar.insert(self.tool_submit_wrap, 11)

        self.toolbar.insert(gtk.SeparatorToolItem(), 12)

        self.toolbar.insert(self.tool_config, 13)
        self.toolbar.insert(self.tool_err_console, 14)
        self.toolbar.insert(self.tool_quit, 15)

        ## connect signals
        self.tool_buff_open.connect(   'clicked', self._sig_buff_manip, 'open')
        self.tool_buff_save.connect(   'clicked', self._sig_buff_manip, 'save')
        self.tool_buff_save_as.connect('clicked', self._sig_buff_manip, 'save-as')
        self.tool_buff_close.connect(  'clicked', self._sig_buff_manip, 'close')

        self.tool_win_split_horz.connect(  'clicked', self._sig_sw_manip, 'split_horz')
        self.tool_win_split_vert.connect(  'clicked', self._sig_sw_manip, 'split_vert')
        self.tool_win_delete.connect(      'clicked', self._sig_sw_manip, 'delete')
        self.tool_win_delete_other.connect('clicked', self._sig_sw_manip, 'delete_other')

        self.tool_submit.connect('clicked', self._sig_submit, 'direct')
#        self.tool_submit_wrap.connect('clicked', self._sig_submit, 'wrap')

        self.tool_config.connect('clicked', self.__global_key_binding_func['prog_show_config'])
        self.tool_err_console.connect('clicked', self.__global_key_binding_func['prog_show_error'])
        self.tool_quit.connect('clicked', self.__global_key_binding_func['prog_quit'])


        ### create main window
        self.mw = zComp.zSplitWindow(zComp.zEdit, [], (self.frame_init, self.frame_uninit), self.frame_split_dup)
        w_vbox.pack_start(self.mw, True, True, 0)
        zComp.zDisplayPanel.set_db_all(os.path.join(zPE.conf.CONFIG_PATH['SPOOL']))


        ## connect auto-update items
        zComp.zEdit.register(      'buffer_focus_in',     self._sig_buffer_focus_in,     None) # register globally
        zComp.zEditBuffer.register('buffer_modified_set', self._sig_buffer_modified_set, None) # register globally

        zComp.zSplitWindow.register('frame_removed', zComp.zEdit.reg_clean_up)
        zComp.zSplitWindow.register('frame_removed', zComp.zEditBuffer.reg_clean_up)
        zComp.zSplitWindow.register('frame_removed', zComp.zTheme.reg_clean_up)


        ### create last-line
        self.lastline = zComp.zLastLine('z# ')
        w_vbox.pack_end(self.lastline, False, False, 0)

        # add the last-line to the editor
        zComp.zEdit.set_last_line(self.lastline)
        self.lastline.bind_to(self.mw)


        ### set accel

        ## for config window
        self.agr_conf = gtk.AccelGroup()
        self.config_window.add_accel_group(self.agr_conf)

        # ESC ==> close
        self.agr_conf.connect_group(
            gtk.keysyms.Escape,
            0,
            gtk.ACCEL_VISIBLE,
            lambda *s: self.config_window._sig_cancel_mod()
            )

        ## for error console
        self.agr_err = gtk.AccelGroup()
        self.err_console.add_accel_group(self.agr_err)

        # ESC ==> close
        self.agr_err.connect_group(
            gtk.keysyms.Escape,
            0,
            gtk.ACCEL_VISIBLE,
            lambda *s: self.err_console.close()
            )

        ### show all parts
        self.agr_err.lock()
        w_vbox.set_focus_chain((self.mw, self.lastline)) # prevent toolbar from getting focus
        self.root.show_all()

        self.err_console.setup = False # signal the end of the setup phase; no more stderr
        if self.err_console.get_text():
            self.err_console.open()


    ### signal-like auto-update function
    def _sig_buffer_focus_in(self, widget = None):
        # get current buffer
        try:
            buff = self.mw.active_frame().active_buffer
        except:
            return
        is_file = (buff.type == 'file')
        is_dir  = (buff.type == 'dir')
        is_disp = (buff.type == 'disp')

        # update toolbar
        self.tool_buff_open.set_property(   'sensitive', not is_dir)
        self.tool_buff_save.set_property(   'sensitive', is_file and buff.modified)
        self.tool_buff_save_as.set_property('sensitive', is_file or is_disp)
        self.tool_buff_close.set_property(  'sensitive', is_file)

        self.tool_submit.set_property(     'sensitive', buff.path)
        self.tool_submit_wrap.set_property('sensitive', buff.path)

    def _sig_buffer_modified_set(self, widget = None):
        # get current buffer
        frame = self.mw.active_frame()
        if not frame:
            return              # cannot get active frame, early return

        buff = frame.active_buffer
        is_file = (buff.type == 'file')
        is_disp = (buff.type == 'disp')

        self.tool_buff_save.set_property(   'sensitive', is_file and buff.modified)
        self.tool_buff_save_as.set_property('sensitive', is_file or is_disp)
    ### end of signal-like auto-update function


    ### top level signals
    def remove_buffer(self, buff, frame):
        if buff.modified and buff.path:
            response = self.lastline.run_confirm(
                '"{0}" has been modified, save it?'.format(os.path.join(* buff.path)),
                [ 'y', 'w', 'n', '!', 'q', 'c', ],
                'y'
                )
            frame.grab_focus()
            if response in [ 'q', 'c' ]:
                if self.mw.active_frame():
                    self.mw.active_frame().grab_focus()
                else:
                    self.mw.grab_focus()
                return None
            elif response in [ 'y', 'w' ]:
                need_save = True
            else:
                need_save = False
        else:
            need_save = False

        if need_save:
            frame.save_buffer(buff)
            msg = frame.rm_buffer(buff)
        else:
            # force quit (without saving)
            msg = frame.rm_buffer(buff, force = True)

        return msg

    def _sig_buff_manip(self, widget, task):
        self.lastline.clear()

        # get current buffer
        frame = self.mw.active_frame()
        if not frame:
            raise AssertionError('The main window is not focused!')
        buff = frame.active_buffer

        if task == 'open':
            if buff.type != 'dir':
                if buff.path:
                    frame.set_buffer(buff.path[:-1], 'dir')
                else:
                    frame.set_buffer(None, 'dir')
                msg = None
            else:
                msg = buff.name, '(Already in browser mood.)'

        elif task == 'save':
            msg = frame.save_buffer(buff)

        elif task == 'save-as':
            msg = frame.save_buffer_as(buff)

        elif task == 'close':
            msg = self.remove_buffer(buff, frame)
        else:
            raise KeyError

        if msg:
            self.lastline.set_text('', '{0}: {1}'.format(* msg))
        else:
            if self.lastline.get_text()[0] != '':
                self.lastline.clear()

        return self.lastline.get_text()[1]


    def _sig_quit(self, widget, data = None):
        self.lastline.clear()

        # reference to buffer list
        buff_list = zComp.zEditBuffer.buff_list
        buff_group = zComp.zEditBuffer.buff_group['user']

        # close all user-opened buffer
        for buff in [ buff_list[name] for name in buff_group ]:
            if not buff.modified:
                continue        # skip non-modified buffer

            # create a dummy frame
            frame = zComp.zEdit(buff.path, buff.type)

            if not self.remove_buffer(buff, frame):
                if self.mw.active_frame():
                    self.mw.active_frame().grab_focus()
                else:
                    self.mw.grab_focus()
                return          # cancel quit

        # all user-opened buffer closed, quit
        gtk.main_quit()


    def _sig_sw_manip(self, widget, task):
        self.lastline.clear()

        frame = self.mw.active_frame()
        if not frame:
            raise AssertionError('The main window is not focused!')

        if task == 'split_horz':
            self.mw.window_split_horz(frame)
        elif task == 'split_vert':
            self.mw.window_split_vert(frame)
        elif task == 'delete':
            self.mw.window_delete(frame)
            self.mw.grab_focus() # focus will be lost for sure
        elif task == 'delete_other':
            self.mw.window_delete_other(frame)
        else:
            raise KeyError


    def _sig_submit(self, widget, task):
        self.lastline.clear()

        frame = self.mw.active_frame()
        if not frame:
            raise AssertionError('The main window is not focused!')
        buff = frame.active_buffer

        if buff.type == 'file' and buff.path:
            pathname = zComp.io_encap.norm_path_list(buff.path[:-1])
            basename = buff.path[-1]
        elif buff.type == 'dir':
            try:
                (pathname, basename) = frame.center.get_active_item()
            except:
                raise AssertionError('Cannot fetch the submission information.')

            if not zComp.io_encap.is_file( (pathname, basename) ):
                return          # dir selection is not a file, early return
        else:
            return              # not a file nor an dir, early return

        if task == 'wrap':
            pass                # wrap the file here

        zsub = subprocess.Popen(['zsub', basename], cwd = pathname,
                                stdout = subprocess.PIPE, stderr = subprocess.PIPE
                                )
        rc = zsub.wait()
        sys.stderr.write(zsub.stderr.read())

        if rc not in zPE.conf.RC.itervalues():
            # something weird happened
            sys.stderr.write(zsub.stdout.read())

            self.lastline.set_text(
                '', '{0}: JOB submitted but aborted with {1}.'.format(basename, rc)
                )
        else:
            self.lastline.set_text(
                '', '{0}: JOB submitted with ID={1}, return value is {2}.'.format(basename, zPE.conf.fetch_job_id(), rc)
                )

        return self.lastline.get_text()[1]
    ### end of top level signals


    ### signals for SplitWindow
    def _sig_popup_manip(self, widget, menu):
        buff_type = widget.get_editor().active_buffer.type
        if buff_type == 'file':
            if widget.get_editor().active_buffer.path:
                is_file = True
            else:
                is_file = False
        elif buff_type == 'dir':
            fullpath = widget.get_active_item()
            if fullpath and zComp.io_encap.is_file(fullpath):
                is_file = True
            else:
                is_file = False
        else:
            is_file = False

        mi_submit = gtk.MenuItem('_Submit the Job File')
        mi_submit.set_property('sensitive', is_file)
        mi_submit_wrap = gtk.MenuItem('_Test Run the Job File')
        mi_submit_wrap.set_property('sensitive', is_file)

        mi_split_horz = gtk.MenuItem('Split Horizontally <_3>')
        mi_split_vert = gtk.MenuItem('Split Vertically <_2>')
        mi_delete = gtk.MenuItem('Close Current Frame <_0>')
        mi_delete_other = gtk.MenuItem('Close Other Frames <_1>')

        menu.append(gtk.SeparatorMenuItem())

        menu.append(mi_submit)
        menu.append(mi_submit_wrap)

        menu.append(gtk.SeparatorMenuItem())

        menu.append(mi_split_horz)
        menu.append(mi_split_vert)
        menu.append(mi_delete)
        menu.append(mi_delete_other)

        mi_submit.connect('activate', self._sig_submit, 'direct')
#        mi_submit_wrap.connect('activate', self._sig_submit, 'wrap')

        mi_split_horz.connect('activate', self._sig_sw_manip, 'split_horz')
        mi_split_vert.connect('activate', self._sig_sw_manip, 'split_vert')
        mi_delete.connect('activate', self._sig_sw_manip, 'delete')
        mi_delete_other.connect('activate', self._sig_sw_manip, 'delete_other')

        menu.show_all()
    ### end of signals for SplitWindow


    ### callback functions for SplitWindow
    def frame_init(self, frame):
        frame.init_sig = {
            'populate_popup' : frame.connect('populate_popup', self._sig_popup_manip),
            }

    def frame_uninit(self, frame):
        for init_sig in frame.init_sig:
            frame.disconnect(init_sig)

    def frame_split_dup(self, frame):
        if frame:
            new_frame = zComp.zEdit(* frame.get_buffer())
        else:
            new_frame = zComp.zEdit()

        return new_frame
    ### end of callback functions for SplitWindow


    def main(self):
        gtk.main()



######## ######## ######## ########
########      Config       ########
######## ######## ######## ########

class ConfigWindow(gtk.Window):
    def __init__(self):
        super(ConfigWindow, self).__init__()

        self.set_destroy_with_parent(True)
        self.connect('delete_event', self._sig_cancel_mod)

        self.set_title('zPE Config')

        # retrive configs
        conf.read_rc_all()
        zPE.conf.read_rc(dry_run = True)

        # lists for managing font
        self.__label = {
            'TAB' : [],
            'FRAME' : [],
            'LABEL' : [],
            }
        self.__entry = []


        # layout of the frame:
        #
        #   +--+--+--+---+_
        #   +--+--+--+---+ \
        #   |            |  tab
        #   |            |
        #   |   center   |
        #   |            |
        #   |            |
        #   +------+--+--+-- separator
        #   |      |bt|bt|
        #   +------+--+--+

        self.__ebox = gtk.EventBox()
        self.__ebox.set_visible_window(False)
        self.add(self.__ebox)

        layout = gtk.VBox()
        self.__ebox.add(layout)

        ### create center
        center = gtk.Notebook()
        layout.pack_start(center, True, True, 0)

        ## GUI
        ct_gui = gtk.VBox()
        self.__label['TAB'].append(gtk.Label('GUI'))
        center.append_page(ct_gui, self.__label['TAB'][-1])

        # Tabbar
        self.__label['FRAME'].append(gtk.Label('Tabbar'))
        ct_gui_tab = gtk.Frame()
        ct_gui_tab.set_label_widget(self.__label['FRAME'][-1])
        ct_gui.pack_start(ct_gui_tab, False, False, 10)

        ct_gui_tab.add(gtk.HBox())

        self.tabbar_on =      zComp.zCheckButton('Show Tabbar         ')
        self.tabbar_grouped = zComp.zCheckButton('Group Tabs in Tabbar')

        self.__label['LABEL'].append(self.tabbar_on.get_label_widget())
        self.__label['LABEL'].append(self.tabbar_grouped.get_label_widget())

        ct_gui_tab.child.pack_start(self.tabbar_on, False, False, 10)
        ct_gui_tab.child.pack_start(self.tabbar_grouped, False, False, 10)

        self.tabbar_on.connect('toggled', self._sig_tabbar_on)
        self.tabbar_grouped.connect('toggled', self._sig_tabbar_grouped)

        # Font
        self.__label['FRAME'].append(gtk.Label('Font'))
        ct_gui_font = gtk.Frame()
        ct_gui_font.set_label_widget(self.__label['FRAME'][-1])
        ct_gui.pack_start(ct_gui_font, False, False, 10)

        ct_gui_font.add(gtk.HBox())

        self.font_sw = {}
        for key in conf.Config['FONT']:
            self.font_sw[key] = gtk.combo_box_new_text()

            self.__label['LABEL'].append(gtk.Label('{0}:'.format(key.title())))
            ct_gui_font.child.pack_start(self.__label['LABEL'][-1], False, False, 10)
            ct_gui_font.child.pack_start(self.font_sw[key], False, False, 10)

            self.font_sw[key].connect('changed', self._sig_font_changed)

        for font in conf.MONO_FONT:
            self.font_sw['name'].append_text(font)
        for size in range(6, 73):
            self.font_sw['size'].append_text(str(size))

        # Theme
        self.__label['FRAME'].append(gtk.Label('Theme'))
        ct_gui_theme = gtk.Frame()
        ct_gui_theme.set_label_widget(self.__label['FRAME'][-1])
        ct_gui.pack_start(ct_gui_theme, False, False, 10)

        ct_gui_theme.add(gtk.Table(3, 6, False))
        ct_gui_theme.child.set_col_spacings(5)

        color_pos = {
            # +--------+--------+
            # |   -1   |   +1   |
            # +--------+--------+
            # |   -2   |   +2   |
            # +--------+--------+
            # |   -3   |   +3   |
            # +--------+--------+
            'text'          : -1, # len = 4
            'text_selected' : +1, # len = 13

            'base'          : -2, # len = 4
            'base_selected' : +2, # len = 13

            'status'        : -3, # len = 6
            'status_active' : +3, # len = 13
            }
        label_len = [ 6, 13 ]   # [ max_len[col_0], max_len[col_1] ]

        self.color_entry = {}
        self.color_picker = {}

        for key in color_pos:
            row = abs(color_pos[key])
            col = (row + color_pos[key]) / (row + row)

            self.__label['LABEL'].append(gtk.Label(' {0:<{1}}'.format(key.replace('_', ' ').title(), label_len[col])))

            self.color_entry[key] = gtk.Entry(7)
            self.color_picker[key] = zComp.zColorPickerButton(self.__ebox, self._sig_color_selected)

            self.color_entry[key].set_property('width-chars', 7)
            self.color_picker[key].set_size_button(35, -1)

            self.__entry.append(self.color_entry[key])

            col *= 3            # each column has 3 sub-column: label, entry, and picker
            ct_gui_theme.child.attach(self.__label['LABEL'][-1], 0 + col, 1 + col, row, 1 + row, xoptions = gtk.SHRINK)
            ct_gui_theme.child.attach(self.color_entry[key],     1 + col, 2 + col, row, 1 + row, xoptions = gtk.SHRINK)
            ct_gui_theme.child.attach(self.color_picker[key],    2 + col, 3 + col, row, 1 + row, xoptions = gtk.SHRINK)

            self.color_entry[key].connect('activate', self._sig_color_entry_activate, key)


        ## KeyBinding
        ct_key = gtk.VBox()
        self.__label['TAB'].append(gtk.Label('Key Binding'))
        center.append_page(ct_key, self.__label['TAB'][-1])

        # Style
        self.__label['FRAME'].append(gtk.Label('Key Binding Sytle'))
        ct_key_style = gtk.Frame()
        ct_key_style.set_label_widget(self.__label['FRAME'][-1])
        ct_key.pack_start(ct_key_style, False, False, 10)

        ct_key_style.add(gtk.HBox())

        self.key_style_key = [ 'emacs', 'vi', 'other' ]
        self.key_style = {}
        self.key_style['emacs'] = zComp.zRadioButton(None,                    'Emacs Mode')
        self.key_style['vi']    = zComp.zRadioButton(self.key_style['emacs'], 'Vi(m) Mode')
        self.key_style['other'] = zComp.zRadioButton(self.key_style['emacs'], 'Other     ')

        for key in self.key_style_key:
            self.__label['LABEL'].append(self.key_style[key].get_label_widget())

            ct_key_style.child.pack_start(self.key_style[key], False, False, 15)

            self.key_style[key].connect('toggled', self._sig_key_style_toggled, key)

        # Binding
        self.__label['FRAME'].append(gtk.Label('Key Bindings'))
        ct_key_binding = gtk.Frame()
        ct_key_binding.set_label_widget(self.__label['FRAME'][-1])
        ct_key.pack_start(ct_key_binding, False, False, 10)

        ct_key_binding.add(gtk.VBox())

        # +-----------------+
        # || +------+-----+ |
        # || |      |     | |
        # || | func | key | |
        # || |      |     | |
        # || +------+-----+ |
        # +------+----------+
        # | help |    entry |
        # +------+----------+

        ct_key_binding_scroll = gtk.ScrolledWindow()
        ct_key_binding_scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        ct_key_binding_scroll.set_placement(gtk.CORNER_TOP_RIGHT)
        ct_key_binding_scroll.set_size_request(-1, 128)

        ct_key_binding_entry = gtk.HBox()

        ct_key_binding.child.pack_start(ct_key_binding_scroll, True, True, 0)
        ct_key_binding.child.pack_start(ct_key_binding_entry, True, True, 0)

        n_func = len(conf.DEFAULT_FUNC_KEY_BIND)
        ct_key_binding_table = gtk.Table(n_func, 2, True)
        ct_key_binding_table.set_col_spacings(15)
        ct_key_binding_scroll.add_with_viewport(ct_key_binding_table)

        self.kb_function = {}
        self.kb_stroke = {}
        row = 0
        for func in sorted(conf.DEFAULT_FUNC_KEY_BIND.iterkeys()):
            self.kb_function[func] = zComp.zToggleButton('  ' + func, False)
            self.kb_stroke[func] = gtk.Label('')

            bttn = self.kb_function[func]
            style = bttn.get_style().copy()
            style.bg[gtk.STATE_PRELIGHT] = style.bg[gtk.STATE_ACTIVE]
            bttn.set_style(style)

            self.__label['LABEL'].append(self.kb_function[func].get_label_widget())
            self.__label['LABEL'][-1].set_alignment(0, 0.5)
            self.__label['LABEL'].append(self.kb_stroke[func])
            self.__label['LABEL'][-1].set_alignment(0, 0.5)

            kb_stroke_frame = gtk.Frame()
            kb_stroke_frame.add(self.kb_stroke[func])

            ct_key_binding_table.attach(self.kb_function[func], 0, 1, row, row + 1, xoptions = gtk.FILL)
            ct_key_binding_table.attach(kb_stroke_frame,        1, 2, row, row + 1, xoptions = gtk.FILL)
            row += 1

            self.kb_function[func].connect('toggled', self._sig_key_stroke_change_request, func)

        self.kb_rules = gtk.Button('Rules <_h>')
        ct_key_binding_entry.pack_start(self.kb_rules, False, False, 10)

        self.kb_rules_dialog = gtk.Dialog('', None, 0, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        self.kb_rules_dialog_content = gtk.Label('')
        self.kb_rules_dialog_content.hbox = gtk.HBox()
        self.kb_rules_dialog_content.hbox.pack_start(self.kb_rules_dialog_content, False, False, 0)
        self.kb_rules_dialog.vbox.pack_start(self.kb_rules_dialog_content.hbox, False, False, 0)
        self.kb_rules_dialog.vbox.show_all()
        self.kb_rules_dialog.set_has_separator(True)
        self.kb_rules_dialog.connect('response', lambda *arg: self.kb_rules_dialog.hide())
        self.kb_rules_dialog.connect('delete_event', lambda *arg: self.kb_rules_dialog.hide() or True)

        self.kb_default = gtk.Button('_Default')
        self.kb_default.set_tooltip_text('Reset the Key Binding for the Current Style (Revertible)')
        ct_key_binding_entry.pack_start(self.kb_default, False, False, 10)

        self.__label['LABEL'].append(gtk.Label('Stroke:'))
        ct_key_binding_entry.pack_start(self.__label['LABEL'][-1], False, False, 10)

        self.kb_stroke_entry = gtk.Entry()
        self.kb_stroke_entry.set_property('sensitive', False)
        self.kb_stroke_entry.modify_text(gtk.STATE_INSENSITIVE, gtk.gdk.color_parse('#000000'))
        self.__entry.append(self.kb_stroke_entry)
        ct_key_binding_entry.pack_start(self.kb_stroke_entry, False, False, 0)

        self.kb_rules.connect('clicked', self._sig_key_stroke_help)
        self.kb_default.connect('clicked', self._sig_key_stroke_clear)
        self.kb_stroke_entry.connect('activate', self._sig_key_stroke_entered)


        ## Editor
        ct_editor = gtk.VBox()
        self.__label['TAB'].append(gtk.Label('Editor'))
        center.append_page(ct_editor, self.__label['TAB'][-1])

        # append this tab later


        ## System
        ct_system = gtk.VBox()
        self.__label['TAB'].append(gtk.Label('System'))
        center.append_page(ct_system, self.__label['TAB'][-1])

        # Architecture
        self.__label['FRAME'].append(gtk.Label('Architecture'))
        ct_system_arch = gtk.Frame()
        ct_system_arch.set_label_widget(self.__label['FRAME'][-1])
        ct_system.pack_start(ct_system_arch, False, False, 10)

        ct_system_arch.add(gtk.Table(2, 2, False))
        ct_system_arch.child.set_col_spacings(10)

        self.addr_mode_sw = gtk.combo_box_new_text()
        self.memory_sz_entry = gtk.Entry()

        for mode in zPE.conf.POSSIBLE_ADDR_MODE:
            self.addr_mode_sw.append_text(str(mode))
        self.memory_sz_entry.set_property('width-chars', 10)

        self.__label['LABEL'].append(gtk.Label(' Simulator Address Mode:           '))
        ct_system_arch.child.attach(self.__label['LABEL'][-1], 0, 1, 0, 1, xoptions = gtk.SHRINK)
        ct_system_arch.child.attach(self.addr_mode_sw,         1, 2, 0, 1, xoptions = gtk.FILL)

        self.__label['LABEL'].append(gtk.Label(' Default Allocation of Memory Size:'))
        ct_system_arch.child.attach(self.__label['LABEL'][-1], 0, 1, 1, 2, xoptions = gtk.SHRINK)
        ct_system_arch.child.attach(self.memory_sz_entry,      1, 2, 1, 2, xoptions = gtk.FILL)

        self.addr_mode_sw.connect('changed', self._sig_addr_mode_changed)
        self.memory_sz_entry.connect('activate', self._sig_memory_sz_entered)


        ### separator
        layout.pack_start(gtk.HSeparator(), False, False, 2)


        ### create bottom
        self.bottom = gtk.HBox()
        layout.pack_end(self.bottom, False, False, 0)

        ## create buttons
        self.bttn_default = gtk.Button(stock = gtk.STOCK_CLEAR)
        self.bttn_default.set_use_underline(False) # no accel for this button
        self.bttn_default.set_label('Default')
        self.bttn_default.set_tooltip_text('Reset *ALL* Configurations to Default Values\n' +
                                           'Note: This Can Cause Un-Revertible Key Binding Reset!')
        self.bttn_revert = gtk.Button(stock = gtk.STOCK_REVERT_TO_SAVED)
        self.bttn_revert.set_label('_Revert')
        self.bttn_revert.set_tooltip_text('Revert All Changes Made in the Current Session')

        self.bttn_cancel = gtk.Button(stock = gtk.STOCK_CANCEL)
        self.bttn_cancel.set_label('_Cancel')
        self.bttn_save = gtk.Button(stock = gtk.STOCK_APPLY)
        self.bttn_save.set_label('_Save')

        ## add buttons to bottom
        self.bottom.pack_start(self.bttn_default, False, False, 5)
        self.bottom.pack_start(self.bttn_revert, False, False, 5)
        self.bottom.pack_start(gtk.Label(), True, True, 0)
        self.bottom.pack_end(self.bttn_save, False, False, 5)
        self.bottom.pack_end(self.bttn_cancel, False, False, 5)

        ## connect signals
        self.bttn_default.connect('clicked', self._sig_clear_rc)
        self.bttn_revert.connect('clicked', self._sig_reload_rc)

        self.bttn_cancel.connect('clicked', self._sig_cancel_mod)
        self.bttn_save.connect('clicked', self._sig_save_config)


        ### update config window fonts
        for label in self.__label['TAB']:
            self.set_font_modify(label, 'Serif')
        for label in self.__label['FRAME']:
            self.set_font_modify(label, 'Serif')
        for label in self.__label['LABEL']:
            self.set_font_modify(label, 'Monospace')

        for entry in self.__entry:
            self.set_font_modify(entry, 'Monospace')

        self.set_font_modify(self.kb_rules_dialog_content, 'Monospace')

        ### show
        self.__ebox.show_all()


    ### top-level signal definition
    def _sig_clear_rc(self, *arg):
        conf.reset_key_binding() # reset all key bindings
        conf.init_rc_all()       # re-initiate GUI config
        zPE.conf.init_rc()       # re-initiate zsub config
        self.load_rc()

    def _sig_open_console(self, *arg):
        self.open()

    def _sig_reload_rc(self, *arg):
        conf.Config = copy.deepcopy(self.config_bkup)          # restore the GUI backup setting
        zPE.conf.Config = copy.deepcopy(self.zsub_config_bkup) # restore the zsub backup setting
        self.load_rc()

    def _sig_save_config(self, *arg):
        conf.write_rc_all()              # write changes for GUI
        conf.read_rc_all()               # validate new GUI config
        zPE.conf.write_rc()              # write changes for zsub
        zPE.conf.read_rc(dry_run = True) # validate new zsub config
        self.close()

    def _sig_cancel_mod(self, *arg):
        self._sig_reload_rc()   # cancel changes
        self.close()
        return True
    ### end of top-level signal definition

    ### signal for GUI
    def _sig_tabbar_on(self, bttn):
        conf.Config['MISC']['tab_on'] = bttn.get_active()
        zComp.zEdit.set_tab_on(conf.Config['MISC']['tab_on'])
        self.tabbar_grouped.set_property('sensitive', conf.Config['MISC']['tab_on'])

    def _sig_tabbar_grouped(self, bttn):
        conf.Config['MISC']['tab_grouped'] = bttn.get_active()
        zComp.zEdit.set_tab_grouped(conf.Config['MISC']['tab_grouped'])

    def _sig_font_changed(self, combo):
        new_font = {}
        for key in conf.Config['FONT']:
            font_val = self.font_sw[key].get_active_text()
            if not font_val:
                return          # early return
            new_font[key] = font_val
        new_font['size'] = int(new_font['size'])

        conf.Config['FONT'] = new_font
        zComp.zTheme.set_font(conf.Config['FONT'])

    def _sig_color_entry_activate(self, entry, key):
        color_code = entry.get_text()
        if not re.match('^#[0-9a-fA-F]{6}$', color_code):
            entry.set_text('')
            return
        self.set_color_modify(key, color_code)
        zComp.zTheme.set_color_map(conf.Config['COLOR_MAP'])

    def _sig_color_selected(self, widget, color_code):
        for key in self.color_picker:
            if widget == self.color_picker[key]:
                break
        self.set_color_modify(key, color_code)
        zComp.zTheme.set_color_map(conf.Config['COLOR_MAP'])
    ### end of signal for GUI


    ### signal for KeyBinding
    def _sig_key_style_toggled(self, radio, key):
        if radio.get_active() and key in conf.DEFAULT_FUNC_KEY_BIND_KEY:
            conf.Config['MISC']['key_binding'] = key

            conf.read_key_binding()

            zComp.zStrokeListener.set_style(conf.Config['MISC']['key_binding'])
            zComp.zStrokeListener.set_key_binding(conf.Config['KEY_BINDING'])

            self.load_binding()


    def _sig_key_stroke_change_request(self, tggl_bttn, func):
        active = tggl_bttn.get_active()
        if active:
            # self push down
            if self.kb_stroke_entry.get_property('sensitive'):
                # entry already sensitive; register self to replace the first button
                old_func = self.kb_stroke_entry.func_editing
                self.kb_stroke_entry.func_editing = func
                self.kb_function[old_func].set_active(False)
            else:
                # entry not sensitive, register self
                self.kb_stroke_entry.func_editing = func

            # prepare the entry
            self.kb_stroke_entry.set_text('')
            self.kb_stroke_entry.editing_done = False
        else:
            # self pop up
            if self.kb_stroke_entry.func_editing == func:
                if self.kb_stroke_entry.editing_done:
                    # editing done
                    self.kb_stroke_entry.func_editing = None
                else:
                    # editing cancelled
                    self.kb_stroke_entry.func_editing = None
                    self.kb_stroke_entry.set_text('< cancelled >')
            else:
                # being cancelled by another button
                return          # no change need to make, early return

        # clean up
        self.kb_stroke_entry.set_property('sensitive', active)
        self.kb_stroke_entry.grab_focus()

    def _sig_key_stroke_entered(self, entry):
        stroke = entry.get_text()
        if not stroke:
            # clear binding
            conf.func_binding_rm(entry.func_editing)
            self.kb_stroke[entry.func_editing].set_text('')
            entry.set_text('< removed >')
        else:
            # validate stroke
            seq = conf.parse_key_binding(stroke)
            if not seq:
                binding_is_valid = False

            try:
                if conf.key_sequence_add(
                    entry.func_editing, seq,
                    force_override = False,
                    force_rebind = True,
                    warning = False
                    ):
                    # key sequence added
                    zComp.zEdit.set_key_binding(conf.Config['KEY_BINDING'])
                    binding_is_valid = True
                else:
                    binding_is_valid = None
            except ValueError as (err_type, err_msg, err_func, err_stroke):
                if err_type == 'override':
                    md = gtk.MessageDialog(
                        self, 
                        gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, 
                        gtk.BUTTONS_NONE,
                        'Conflicted key binding!'
                        )
                    md.format_secondary_text('Override the old one ({0})?'.format(err_func))
                    md.add_buttons('_Override', gtk.RESPONSE_ACCEPT, '_Cancel', gtk.RESPONSE_CANCEL)
                    md_id = md.run()
                    if md_id == gtk.RESPONSE_ACCEPT:
                        if conf.key_sequence_add(
                            entry.func_editing, seq,
                            force_override = True,
                            force_rebind = True,
                            warning = False
                            ):
                            # key sequence added
                            zComp.zEdit.set_key_binding(conf.Config['KEY_BINDING'])
                            self.kb_stroke[err_func].set_text('') # clear conflict binding text
                            binding_is_valid = True
                        else:
                            sys.stderr.write('Warning: Fail to override the binding!\n')
                            binding_is_valid = None
                    else:
                        binding_is_valid = False
                    md.destroy()

            # process stroke
            if binding_is_valid:
                # accept the normalized stroke
                self.kb_stroke[entry.func_editing].set_text(' '.join(seq))
                entry.set_text('< accepted >')
            elif binding_is_valid == False:
                # cancel
                entry.set_text('< invalid >')
            else:
                entry.set_text('< no change >')

        # pop up the registered button
        entry.editing_done = True
        self.kb_function[entry.func_editing].set_active(False)


    def _sig_key_stroke_help(self, bttn):
        self.kb_rules_dialog.show()

    def _sig_key_stroke_clear(self, bttn):
        conf.init_key_binding()
        self.load_binding()
    ### end of signal for KeyBinding


    ### signal for System
    def _sig_addr_mode_changed(self, combo):
        addr_val = combo.get_active_text()
        if not addr_val:
            return          # early return

        zPE.conf.Config['addr_mode'] = int(addr_val)
        zPE.conf.Config['addr_max'] = 2 ** zPE.conf.Config['addr_mode']

    def _sig_memory_sz_entered(self, entry):
        try:
            sz = zPE.conf.parse_region(entry.get_text())
        except:
            entry.set_text(zPE.conf.Config['memory_sz'])
            raise

        zPE.conf.Config['memory_sz'] = sz
        entry.set_property('sensitive', False) # remove focus
        entry.set_text(zPE.conf.Config['memory_sz'])
        entry.set_property('sensitive', True)  # retain edibility
    ### end of signal for System


    ### overloaded function definition
    def open(self):
        if self.get_property('visible'):
            self.window.show()
        else:
            self.config_bkup = copy.deepcopy(conf.Config)          # backup GUI settings
            self.zsub_config_bkup = copy.deepcopy(zPE.conf.Config) # backup zsub settings
            self.load_rc()
            self.show()


    def close(self):
        self.kb_rules_dialog.hide()
        self.hide()
    ### end of overloaded function definition


    ### public API definition
    def load_rc(self):
        # GUI->Tabbar
        self.tabbar_on.set_active(conf.Config['MISC']['tab_on'])
        self.tabbar_grouped.set_active(conf.Config['MISC']['tab_grouped'])
        self.tabbar_grouped.set_property('sensitive', conf.Config['MISC']['tab_on'])

        # GUI->Font
        for key in conf.Config['FONT']:
            self.select_combo_item(self.font_sw[key], conf.Config['FONT'][key])

        # GUI->Theme
        for key in self.color_entry:
            self.set_color_modify(key, conf.Config['COLOR_MAP'][key])
        zComp.zTheme.set_color_map(conf.Config['COLOR_MAP'])

        # KeyBinding->Style
        for key in self.key_style_key:
            if key not in conf.DEFAULT_FUNC_KEY_BIND_KEY:
                self.key_style[key].set_property('sensitive', False)
                self.key_style[key].set_active(True)
            else:
                self.key_style[key].set_property('sensitive', True)
        self.key_style[conf.Config['MISC']['key_binding']].set_active(True)

        # KeyBinding->Binding
        self.load_binding()

        # System->Architecture
        self.select_combo_item(self.addr_mode_sw, zPE.conf.Config['addr_mode'])
        self.memory_sz_entry.set_text(zPE.conf.Config['memory_sz'])


    def load_binding(self):
        style = conf.Config['MISC']['key_binding']
        self.kb_rules_dialog.set_title('Style::{0}'.format(style.title()))
        self.kb_rules_dialog_content.set_markup(conf.KEY_BINDING_RULE_MKUP[style])
        for (k, v) in self.kb_stroke.iteritems():
            v.set_text(conf.Config['FUNC_BINDING'][k])
    ### end of public API definition


    ### support function definition
    def set_color_modify(self, key, color_code):
        self.color_entry[key].set_text(color_code.upper())
        self.color_picker[key].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(color_code))
        self.color_picker[key].modify_bg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(color_code))

        conf.Config['COLOR_MAP'][key] = color_code
    ### end of support function definition


    ### utility function definition
    def select_combo_item(self, combo, item):
        tm = combo.get_model()

        tm_iter = tm.get_iter_first()
        if not tm_iter:
            return          # early return

        while tm.get_value(tm_iter, 0) != str(item):
            if not tm_iter:
                return      # early return
            tm_iter = tm.iter_next(tm_iter)
        combo.set_active_iter(tm_iter)


    def set_font_modify(self, widget, font, size = None):
        if size:
            font += ' {}'.format(size)
        widget.modify_font(pango.FontDescription(font))
    ### end of utility function definition
