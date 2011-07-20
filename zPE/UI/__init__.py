# modules that will be auto imported
import comp, conf

import os, sys, copy, re
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
        self.__key_binding_func = {
            'buffer_open'               : lambda *arg: self._sig_buff_manip(None, 'open'),

            'prog_show_config'          : lambda *arg: self.config_window.open(),
            'prog_show_error'           : lambda *arg: self.err_console.open(),
            'prog_quit'                 : lambda *arg: self._sig_quit(None),
            }


        ### redirect STDOUT and STDERR to the error console
        self.err_console = comp.zErrConsole('zPE Error Console', True)
        sys.stdout = self.err_console
        sys.stderr = self.err_console

        ### retrive GUI configuration
        conf.read_rc()
        self.config_window = ConfigWindow()
        self.config_window.load_rc()

        ### create top-level frame
        self.root = gtk.Window(gtk.WINDOW_TOPLEVEL)

        self.root.connect("delete_event", self.delete_event)
        self.root.connect("destroy", self._sig_quit)

        self.root.set_title("zPE - Mainframe Programming Environment Simulator")
        self.root.set_icon_from_file( os.path.join(
                os.path.dirname(__file__), "image", "icon_zPE.gif"
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

        self.toolbar.insert(self.tool_config, 5)
        self.toolbar.insert(self.tool_err_console, 6)
        self.toolbar.insert(self.tool_quit, 7)

        ## connect auto-update items
        comp.zEdit.register('buffer_focus_in', self._sig_buffer_focus_in, self)

        comp.zSplitScreen.register('frame_removed', comp.zEdit.reg_clean_up)
        comp.zSplitScreen.register('frame_removed', comp.zEditBuffer.reg_clean_up)
        comp.zSplitScreen.register('frame_removed', comp.zTheme.reg_clean_up)


        ## connect signals
        self.tool_buff_open.connect('clicked', self._sig_buff_manip, 'open')

        self.tool_config.connect('clicked', self.__key_binding_func['prog_show_config'])
        self.tool_err_console.connect('clicked', self.__key_binding_func['prog_show_error'])
        self.tool_quit.connect('clicked', self.__key_binding_func['prog_quit'])


        ### create main window
        self.mw = comp.zSplitScreen(comp.zEdit, [], self.frame_init, self.frame_split_dup)
        w_vbox.pack_start(self.mw, True, True, 0)


        ### create last-line
        self.lastline = comp.zLastLine('z# ')
        w_vbox.pack_end(self.lastline, False, False, 0)

        # add the last-line to the editor
        comp.zEdit.set_last_line(self.lastline)

        ### set accel

        ## for root window
        self.set_accel()

        ## for config window
        self.agr_conf = gtk.AccelGroup()
        self.config_window.add_accel_group(self.agr_conf)

        # ESC ==> close
        self.agr_conf.connect_group(
            gtk.keysyms.Escape,
            0,
            gtk.ACCEL_VISIBLE,
            lambda *s: self.config_window.close()
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
        buff = self.mw.active_frame().active_buffer
        is_file = (buff.type == 'file')
        is_dir  = (buff.type == 'dir')

        # update toolbar
        self.tool_buff_open.set_property('sensitive', not is_dir)
        self.tool_buff_save.set_property('sensitive', is_file and buff.modified)
        self.tool_buff_save_as.set_property('sensitive', is_file and buff.modified)
        self.tool_buff_close.set_property('sensitive', is_file)
    ### end of signal-like auto-update function


    ### top level signals
    def _sig_buff_manip(self, widget, task):
        # get current buffer
        frame = self.mw.active_frame()
        buff = frame.active_buffer

        if task == 'open':
            if buff.type != 'dir':
                if buff.path:
                    frame.set_buffer(buff.path[:-1], 'dir')
                else:
                    frame.set_buffer(None, 'dir')
        elif task == 'save':
            pass
        elif task == 'save-as':
            pass
        elif task == 'close':
            pass
        else:
            raise KeyError


    def _sig_quit(self, widget, data = None):
        #########################
        # check save here       #
        #########################
        gtk.main_quit()
    ### end of top level signals


    ### signals for SplitScreen
    def _sig_popup_manip(self, widget, menu, data = None):
        menu.append(gtk.SeparatorMenuItem())
        menu.append(gtk.MenuItem("test"))
        menu.show_all()
    ### end of signals for SplitScreen


    ### callback functions for SplitScreen
    def frame_init(self, frame):
        frame.connect('populate_popup', self._sig_popup_manip)

    def frame_split_dup(self, frame):
        if frame:
            new_frame = comp.zEdit(* frame.get_buffer())
        else:
            new_frame = comp.zEdit()

        return new_frame
    ### end of callback functions for SplitScreen


    ### key binding
    def set_accel(self):
        for (k, v) in conf.Config['FUNC_BINDING'].items():
            if k in self.__key_binding_func:
                comp.zEdit.register(k, self.__key_binding_func[k], self)
    ### end of key binding


    def main(self):
        gtk.main()



######## ######## ######## ########
########      Config       ########
######## ######## ######## ########

class ConfigWindow(gtk.Window):
    def __init__(self):
        super(ConfigWindow, self).__init__()

        self.set_destroy_with_parent(True)
        self.connect("delete_event", self._sig_cancel_mod)

        self.set_title('zPE Config')

        # lists for managing font
        self.__label = {
            'TAB' : [],         # weight = 1.2
            'FRAME' : [],       # weight = 1
            'LABEL' : [],       # weight = 0.8
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

        self.tabbar_on =      gtk.CheckButton('Show Tabbar         ')
        self.tabbar_grouped = gtk.CheckButton('Group Tabs in Tabbar')

        self.__label['LABEL'].append(self.get_label_widget(self.tabbar_on))
        self.__label['LABEL'].append(self.get_label_widget(self.tabbar_grouped))

        ct_gui_tab.child.pack_start(self.tabbar_on, False, False, 5)
        ct_gui_tab.child.pack_start(self.tabbar_grouped, False, False, 5)

        self.tabbar_on.connect('toggled', self._sig_tabbar_on)
        self.tabbar_grouped.connect('toggled', self._sig_tabbar_grouped)

        # Font
        self.__label['FRAME'].append(gtk.Label('Font'))
        ct_gui_font = gtk.Frame()
        ct_gui_font.set_label_widget(self.__label['FRAME'][-1])
        ct_gui.pack_start(ct_gui_font, False, False, 10)

        ct_gui_font.add(gtk.HBox())

        self.font_sw = {}
        self.font_sw_tm = {}
        font_sw_cell = {}

        for key in conf.Config['FONT']:
            self.font_sw_tm[key] = gtk.ListStore(type(conf.Config['FONT'][key]))
            self.font_sw[key] = gtk.ComboBox(self.font_sw_tm[key])
            font_sw_cell[key] = gtk.CellRendererText()

            self.font_sw[key].pack_start(font_sw_cell[key], True)
            self.font_sw[key].add_attribute(font_sw_cell[key], "text", 0)

            self.__label['LABEL'].append(gtk.Label('{0}:'.format(key.title())))
            ct_gui_font.child.pack_start(self.__label['LABEL'][-1], False, False, 5)
            ct_gui_font.child.pack_start(self.font_sw[key], False, False, 5)

            self.font_sw[key].connect('changed', self._sig_font_changed)

        for font in conf.MONO_FONT:
            self.font_sw_tm['name'].append([font])
        for size in range(6, 73):
            self.font_sw_tm['size'].append([size])

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

            self.__label['LABEL'].append(gtk.Label('{0:<{1}}'.format(key.replace('_', ' ').title(), label_len[col])))

            self.color_entry[key] = gtk.Entry(7)
            self.color_picker[key] = comp.zColorPicker(self.__ebox, self._sig_color_selected)

            self.color_entry[key].set_property('width-chars', 7)
            self.color_picker[key].set_size_button(45, -1)

            self.__entry.append(self.color_entry[key])

            col *= 3            # each column has 3 sub-column: label, entry, and picker
            ct_gui_theme.child.attach(self.__label['LABEL'][-1], 0 + col, 1 + col, row, 1 + row, xoptions=gtk.SHRINK)
            ct_gui_theme.child.attach(self.color_entry[key],     1 + col, 2 + col, row, 1 + row, xoptions=gtk.SHRINK)
            ct_gui_theme.child.attach(self.color_picker[key],    2 + col, 3 + col, row, 1 + row, xoptions=gtk.SHRINK)

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
        self.key_style['emacs'] = gtk.RadioButton(None,                    'Emacs Mode')
        self.key_style['vi']    = gtk.RadioButton(self.key_style['emacs'], 'Vi(m) Mode')
        self.key_style['other'] = gtk.RadioButton(self.key_style['emacs'], 'Other     ')

        for key in self.key_style_key:
            self.__label['LABEL'].append(self.get_label_widget(self.key_style[key]))

            ct_key_style.child.pack_start(self.key_style[key], False, False, 15)

            self.key_style[key].connect('toggled', self._sig_key_style_toggled, key)

        # Binding
        self.__label['FRAME'].append(gtk.Label('Key Bindings'))
        ct_key_binding = gtk.Frame()
        ct_key_binding.set_label_widget(self.__label['FRAME'][-1])
        ct_key.pack_start(ct_key_binding, False, False, 10)

        ct_key_binding.add(gtk.VBox())

        # +---------------+
        # |  key binding  |
        # |     rules     |
        # +---------------+
        # |+-------+-----+|
        # ||| func | key ||
        # |||      |     ||
        # |+-------+-----+|
        # +---------------+
        self.key_binding_rule = {
            'emacs' :
'''Meaning of the 'Stroke' name:
  - 'C-x'   : press 'x' while holding Ctrl
  - 'C-M-x' : press 'x' while holding both Ctrl and Alt
  - 'C-x X' : first press 'x' while holding Ctrl, then press 'x' while holding Shift

Limitation:
  - Key sequence cannot start with M-x (run command), C-q (escape next key stroke), or any character you can find on the keyboard
  - Key sequence cannot contain C-g (cancel current action)
  - Key sequence cannot contain more than one stand-alone (without prefix 'C-' or 'M-') function keys (listed below)

'Stroke' name of Function Keys:
  - BackSpace, Enter, Escape, Space, Tab
  - Insert, Delete, Home, End, Page_Up, Page_Down
  - Left, Right, Up, Down
  - F1 ~ F12
''',
            'vi'    : '''Not Implemented Yet''',
            'other' :
'''Meaning of the 'Stroke' name:
  - 'C-x'   : press 'x' while holding Ctrl
  - 'C-M-x' : press 'x' while holding both Ctrl and Alt
  - 'X'     : press 'x' while holding Shift

Limitation:
  - No space allowed in the 'Stroke' definition. Use 'Space' to bind the Space key on your keyboard

'Stroke' name of Function Keys:
  - BackSpace, Enter, Escape, Space, Tab
  - Insert, Delete, Home, End, Page_Up, Page_Down
  - Left, Right, Up, Down
  - F1 ~ F12
''',
            }
        self.key_binding_help = gtk.Label()
        self.key_binding_help.set_line_wrap(True)
        self.__label['LABEL'].append(self.key_binding_help)

        ct_key_binding_scroll = gtk.ScrolledWindow()
        ct_key_binding_scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        ct_key_binding_scroll.set_placement(gtk.CORNER_TOP_RIGHT)
        ct_key_binding_scroll.set_size_request(-1, 128)

        ct_key_binding.child.pack_start(self.key_binding_help, False, False, 2)
        ct_key_binding.child.pack_start(ct_key_binding_scroll, True, True, 2)

        n_func = len(conf.DEFAULT_FUNC_KEY_BIND)
        ct_key_binding_table = gtk.Table(n_func, 2, False)
        ct_key_binding_scroll.add_with_viewport(ct_key_binding_table)

        self.key_stroke_entry = {}
        row = 0
        for func in sorted(conf.DEFAULT_FUNC_KEY_BIND.keys()):
            self.__label['LABEL'].append(gtk.Label(func))

            self.key_stroke_entry[func] = gtk.Entry()

            self.__entry.append(self.key_stroke_entry[func])

            ct_key_binding_table.attach(self.__label['LABEL'][-1],   0, 1, row, row + 1, xoptions=gtk.SHRINK)
            ct_key_binding_table.attach(self.key_stroke_entry[func], 1, 2, row, row + 1, xoptions=gtk.SHRINK)
            row += 1

            self.key_stroke_entry[func].connect('activate', self._sig_key_stroke_changed, func)


        ### separator
        layout.pack_start(gtk.HSeparator(), False, False, 2)


        ### create bottom
        self.bottom = gtk.HBox()
        layout.pack_end(self.bottom, False, False, 0)

        ## create buttons
        self.bttn_default = gtk.Button(stock = gtk.STOCK_CLEAR)
        self.bttn_default.set_label('_Default')
        self.bttn_revert = gtk.Button(stock = gtk.STOCK_REVERT_TO_SAVED)
        self.bttn_revert.set_label('_Revert')

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

        ### show
        self.__ebox.show_all()


    ### top-level signal definition
    def _sig_clear_rc(self, *arg):
        conf.init_rc()          # re-initiate config
        conf.write_rc()         # write changes
        self.load_rc()

    def _sig_open_console(self, *arg):
        self.open()

    def _sig_reload_rc(self, *arg):
        conf.Config = copy.deepcopy(self.config_bkup) # restore the backup setting
        self.load_rc()

    def _sig_save_config(self, *arg):
        conf.write_rc()         # write changes
        conf.read_rc()          # validate new config
        self.close()

    def _sig_cancel_mod(self, *arg):
        self._sig_reload_rc()   # cancel changes
        self.close()
        return True
    ### end of top-level signal definition

    ### signal for GUI
    def _sig_tabbar_on(self, bttn):
        conf.Config['MISC']['tab_on'] = bttn.get_active()
        comp.zEdit.set_tab_on(conf.Config['MISC']['tab_on'])
        self.tabbar_grouped.set_property('sensitive', conf.Config['MISC']['tab_on'])

    def _sig_tabbar_grouped(self, bttn):
        conf.Config['MISC']['tab_grouped'] = bttn.get_active()
        comp.zEdit.set_tab_grouped(conf.Config['MISC']['tab_grouped'])

    def _sig_font_changed(self, combo):
        new_font = {}
        for key in conf.Config['FONT']:
            font_iter = self.font_sw[key].get_active_iter()
            if not font_iter:
                return          # early return
            new_font[key] = self.font_sw_tm[key].get_value(font_iter, 0)

        conf.Config['FONT'] = new_font
        comp.zTheme.set_font(conf.Config['FONT'])

    def _sig_color_entry_activate(self, entry, key):
        color_code = entry.get_text()
        if not re.match('^#[0-9a-fA-F]{6}$', color_code):
            entry.set_text('')
            return
        self.set_color_modify(key, color_code)
        comp.zTheme.set_color_map(conf.Config['COLOR_MAP'])

    def _sig_color_selected(self, widget, color_code):
        for key in self.color_picker:
            if widget == self.color_picker[key]:
                break
        self.set_color_modify(key, color_code)
        comp.zTheme.set_color_map(conf.Config['COLOR_MAP'])
    ### end of signal for GUI


    ### signal for KeyBinding
    def _sig_key_style_toggled(self, radio, key):
        if radio.get_active() and key in conf.DEFAULT_FUNC_KEY_BIND_KEY:
            conf.Config['MISC']['key_binding'] = key
            conf.init_key_binding()
            comp.zEdit.set_style(conf.Config['MISC']['key_binding'])
            comp.zEdit.set_key_binding(conf.Config['KEY_BINDING'])

    def _sig_key_stroke_changed(self, entry, func):
        stroke = entry.get_text()
        seq = conf.parse_key_binding(stroke)
        if not seq:
            entry.set_text('')

    ### end of signal for KeyBinding


    ### overloaded function definition
    def open(self):
        if self.get_property('visible'):
            self.window.show()
        else:
            self.config_bkup = copy.deepcopy(conf.Config) # backup settings
            self.load_rc()
            self.show()

    def close(self):
        self.hide()
    ### end of overloaded function definition


    ### support function definition
    def load_rc(self):
        conf.Config = copy.deepcopy(conf.Config)

        # GUI->Tabbar
        self.tabbar_on.set_active(conf.Config['MISC']['tab_on'])
        self.tabbar_grouped.set_active(conf.Config['MISC']['tab_grouped'])
        self.tabbar_grouped.set_property('sensitive', conf.Config['MISC']['tab_on'])

        # GUI->Font
        self.select_font(conf.Config['FONT'])

        # GUI->Theme
        for key in self.color_entry:
            self.set_color_modify(key, conf.Config['COLOR_MAP'][key])
        comp.zTheme.set_color_map(conf.Config['COLOR_MAP'])

        # KeyBinding->Style
        for key in self.key_style_key:
            if key not in conf.DEFAULT_FUNC_KEY_BIND_KEY:
                self.key_style[key].set_property('sensitive', False)
                self.key_style[key].set_active(True)
            else:
                self.key_style[key].set_property('sensitive', True)
        self.key_style[conf.Config['MISC']['key_binding']].set_active(True)


    def select_font(self, font_dic):
        for key in font_dic:
            font_iter = self.font_sw_tm[key].get_iter_first()
            if not font_iter:
                return          # early return

            while self.font_sw_tm[key].get_value(font_iter, 0) != font_dic[key]:
                if not font_iter:
                    return      # early return
                font_iter = self.font_sw_tm[key].iter_next(font_iter)
            self.font_sw[key].set_active_iter(font_iter)


    def set_color_modify(self, key, color_code):
        self.color_entry[key].set_text(color_code.upper())
        self.color_picker[key].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(color_code))
        self.color_picker[key].modify_bg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse(color_code))

        conf.Config['COLOR_MAP'][key] = color_code
    ### end of support function definition


    ### utility function definition
    def get_label_widget(self, current):
        try:
            if not len(current.get_children()):
                raise AttributeError
        except:
            if isinstance(current, gtk.Label):
                return current  # found the label
            else:
                return None     # end of the path

        for child in current.get_children():
            found = self.get_label_widget(child)
            if found:
                return found    # found in previous search
        return None             # not found at all


    def set_font_modify(self, widget, font, size = None):
        if size:
            font += ' {}'.format(size)
        widget.modify_font(pango.FontDescription(font))
    ### end of utility function definition
