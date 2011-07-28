# this is the zComponent package

from z_support    import *

from zBase        import *
from zConsole     import *
from zEditorFrame import *
from zFileManager import *
from zFrame       import *
from zText        import *
from zWidget      import *

import pygtk
pygtk.require('2.0')
import gtk


######## ######## ######## ######## ########
########        MODULE INIT         ########
######## ######## ######## ######## ########

# change gtk settings
settings = gtk.settings_get_default()
settings.set_property('gtk-show-input-method-menu', False)
settings.set_property('gtk-show-unicode-menu', False)

# set default theme
gtk.rc_parse_string('''
style 'zTheme' {
    GtkButton::focus-line-width = 0
    GtkButton::focus-padding = 0

    GtkPaned::handle-size = 8
}
widget '*' style 'zTheme'
''')

# open default buffers
for buff_name, buff_type in zEditBuffer.SYSTEM_BUFFER.iteritems():
    zEditBuffer(buff_name, buff_type)
