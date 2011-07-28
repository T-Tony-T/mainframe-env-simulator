# this is the supporting module of the zComponent package

import pygtk
pygtk.require('2.0')
import gtk


######## ######## ######## ######## ########
########     Supported Feature      ########
######## ######## ######## ######## ########

SUPPORT = { }
if gtk.gdk.screen_get_default().get_rgba_colormap():
    SUPPORT['rgba'] = True
else:
    SUPPORT['rgba'] = False


######## ######## ######## ######## ########
########        XPM & PixBuf        ########
######## ######## ######## ######## ########

XPM = {                         # inline xpm definition
    'empty' : [
        "1 1 2 1",
        " 	c None",
        ".	c #000000",
        " "
        ],

    'folder' : [
        "17 16 7 1",
        "  c #000000",
        ". c #808000",
        "X c yellow",
        "o c #808080",
        "O c #c0c0c0",
        "+ c white",
        "@ c None",
        "@@@@@@@@@@@@@@@@@",
        "@@@@@@@@@@@@@@@@@",
        "@@+XXXX.@@@@@@@@@",
        "@+OOOOOO.@@@@@@@@",
        "@+OXOXOXOXOXOXO. ",
        "@+XOXOXOXOXOXOX. ",
        "@+OXOXOXOXOXOXO. ",
        "@+XOXOXOXOXOXOX. ",
        "@+OXOXOXOXOXOXO. ",
        "@+XOXOXOXOXOXOX. ",
        "@+OXOXOXOXOXOXO. ",
        "@+XOXOXOXOXOXOX. ",
        "@+OOOOOOOOOOOOO. ",
        "@                ",
        "@@@@@@@@@@@@@@@@@",
        "@@@@@@@@@@@@@@@@@"
        ],

    'file' : [
        "12 12 3 1",
        "  c #000000",
        ". c #ffff04",
        "X c #b2c0dc",
        "X        XXX",
        "X ...... XXX",
        "X ......   X",
        "X .    ... X",
        "X ........ X",
        "X .   .... X",
        "X ........ X",
        "X .     .. X",
        "X ........ X",
        "X .     .. X",
        "X ........ X",
        "X          X"
        ],
    }

PIXBUF = {}                     # pixbuf definition
for key in XPM:
    PIXBUF[key] = gtk.gdk.pixbuf_new_from_xpm_data(XPM[key])
