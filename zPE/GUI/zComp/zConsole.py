# this is the console module of the zComponent package

from zPE.GUI.zComp.zBase import zTheme

import os, sys
import pygtk
pygtk.require('2.0')
import gtk


######## ######## ######## ######## ########
########        zErrConsole         ########
######## ######## ######## ######## ########

class zErrConsole(gtk.Window):
    '''An Error Console Widget'''
    def __init__(self, title, show_on_change = False):
        '''
        title
            the title of the zErrConsole.

        show_on_change
            whether the zErrConsole should automatically show when
            new messages are added.
        '''
        super(zErrConsole, self).__init__()

        self.setup = True       # in setup phase, write to stderr as well

        self.set_destroy_with_parent(True)
        self.connect('delete_event', self._sig_close_console)

        self.set_title(title)


        # layout of the frame:
        #
        #   +-----------+_
        #   ||          | \
        #   ||          |  scrolled_window
        #   ||  center  |
        #   ||          |
        #   ||          |
        #   +-----+--+--+-- separator
        #   |     |bt|bt|
        #   +-----+--+--+

        layout = gtk.VBox()
        self.add(layout)

        # create center
        scrolled = gtk.ScrolledWindow()
        layout.pack_start(scrolled, True, True, 0)
        scrolled.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        scrolled.set_placement(gtk.CORNER_TOP_RIGHT)

        self.center = gtk.TextView()
        scrolled.add(self.center)
        self.center.set_wrap_mode(gtk.WRAP_CHAR)
        self.center.set_editable(False)
        self.center.set_cursor_visible(False)

        zTheme.register('update_font', zTheme._sig_update_font_modify, self.center, 0.85)
        zTheme._sig_update_font_modify(self.center, 0.85)
        zTheme.register('update_color_map', self._sig_update_color_map, self.center)
	self._sig_update_color_map()

        # separator
        layout.pack_start(gtk.HSeparator(), False, False, 2)

        # create bottom
        self.bottom = gtk.HBox()
        layout.pack_end(self.bottom, False, False, 0)

        self.bttn_clear = gtk.Button(stock = gtk.STOCK_CLEAR)
        self.bttn_clear.set_label('C_lear')
        self.bttn_close = gtk.Button(stock = gtk.STOCK_CLOSE)
        self.bttn_close.set_label('_Close')

        self.bttn_clear.connect('clicked', self._sig_clear)
        self.bttn_close.connect('clicked', self._sig_close_console)

        self.bottom.pack_start(gtk.Label(), True, True, 0)
        self.bottom.pack_end(self.bttn_close, False, False, 5)
        self.bottom.pack_end(self.bttn_clear, False, False, 5)

        # connect signal
        if show_on_change:
            self.center.get_buffer().connect('changed', self._sig_open_console)

        layout.show_all()
        self.resize()


    ### signal-like auto-update function
    def _sig_update_color_map(self, widget = None):
        self.center.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.center.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(zTheme.color_map['base']))

        self.center.modify_text(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['text']))
        self.center.modify_base(gtk.STATE_ACTIVE, gtk.gdk.color_parse(zTheme.color_map['base']))

        self.center.modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse(zTheme.color_map['text_selected']))
        self.center.modify_base(gtk.STATE_SELECTED, gtk.gdk.color_parse(zTheme.color_map['base_selected']))
    ### end of signal-like auto-update function


    ### signal definition
    def _sig_clear(self, widget):
        self.clear()

    def _sig_open_console(self, *arg):
        if not self.setup:
            self.open()

    def _sig_close_console(self, *arg):
        self.close()
        return True
    ### end of signal definition


    ### overridden function definition
    def clear(self):
        self.set_text('')

    def open(self):
        if self.get_property('visible'):
            self.window.show()
        else:
            self.show()

    def close(self):
        self.hide()

    def get_text(self):
        buff = self.center.get_buffer()
        return buff.get_text(buff.get_start_iter(), buff.get_end_iter())

    def set_text(self, text):
        self.center.get_buffer().set_text(text)

    def resize(self):
        ( char_w, char_h ) = self.center.create_pango_layout('w').get_pixel_size()

        ex_w = 2 # to "somewhat" cancel the border width, since there is no way to get that value
        scrolled = self.center.parent
        ex_w += scrolled.get_hscrollbar().style_get_property('slider-width')
        ex_w += scrolled.style_get_property('scrollbar-spacing')

        self.set_default_size(char_w * 80 + ex_w, char_h * 25)

    def write(self, text):
        buff = self.center.get_buffer()
        buff.insert(buff.get_end_iter(), text)
        if self.setup:
            sys.__stderr__.write(text)
    ### end of overridden function definition
