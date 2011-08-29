# this is the base module of the zComponent package

import pango


######## ######## ######## ######## ########
########           z_ABC            ########
######## ######## ######## ######## ########

class z_ABC(object):
    '''z Abstract Base Class:  Implemetation of a Signal-Like System'''
    _auto_update = {
        # 'signal_like_string'  : [ (widget, callback, data_list), ... ]
        }

    _auto_update_blocked = [
        # 'signal_like_string'
        ]

    @classmethod
    def register(cls, sig, callback, widget, *data):
        '''
        This function register a function to a signal-like string.
        widget could be None to allow non-removable, global emission.
        '''
        cls._auto_update[sig].append((widget, callback, data))

    @classmethod
    def unregister(cls, sig, widget):
        '''This function un-register the widget from the signal-like string'''
        if not widget:
            return              # cannot unregister a global signal

        reserve = []
        for item in cls._auto_update[sig]:
            if widget != item[0]:
                reserve.append(item)
        cls._auto_update[sig] = reserve


    @classmethod
    def reg_add_registry(cls, sig):
        if sig not in cls._auto_update:
            cls._auto_update[sig] = [  ]

    @classmethod
    def reg_is_registered(cls, sig, widget):
        return ( sig    in  cls._auto_update  and
                 widget in [ item[0] for item in cls._auto_update[sig] ]
                 )

    @classmethod
    def reg_is_registered_globally(cls, sig):
        return ( sig  in  cls._auto_update  and
                 None in [ item[0] for item in cls._auto_update[sig] ]
                 )

    @classmethod
    def reg_block(cls, sig):
        '''This function block the signal to disable its emission'''
        if sig not in cls._auto_update_blocked:
            cls._auto_update_blocked.append(sig)

    @classmethod
    def reg_unblock(cls, sig):
        '''This function unblock the signal to enable its emission'''
        if sig in cls._auto_update_blocked:
            cls._auto_update_blocked.remove(sig)


    @classmethod
    def reg_clean_up(cls):
        '''This function un-register all invisible widgets from the list'''
        for sig in cls._auto_update:
            reserve = []
            for item in cls._auto_update[sig]:
                try:
                    if item[0].get_property('visible'):
                        reserve.append(item)
                except:
                    reserve.append(item)
            cls._auto_update[sig] = reserve


    @classmethod
    def reg_emit(cls, sig, info = None):
        '''
        This function emit the signal to all registered object

        Caution: may cause multiple emission. To avoid that,
                 use reg_emit_to() instead.
        '''
        if sig in cls._auto_update_blocked:
            return              # signal being blocked, early return

        for (w, cb, data) in cls._auto_update[sig]:
            if info:
                cb(w, info, *data)
            else:
                cb(w, *data)

    @classmethod
    def reg_emit_to(cls, sig, target, info = None):
        '''
        This function emit the signal to the indicated registered
        object, and all un-bounded objects (registered with None)
        '''
        if sig in cls._auto_update_blocked:
            return              # signal being blocked, early return

        for (w, cb, data) in cls._auto_update[sig]:
            if not w or w == target:
                if info:
                    cb(w, info, *data)
                else:
                    cb(w, *data)



######## ######## ######## ######## ########
########           zTheme           ########
######## ######## ######## ######## ########

class zTheme(z_ABC):
    '''The Theme Control Class Used by z* Classes'''
    DISC = {
        # no corresponding config for items in this dictionary
        'fn_len' : 16,
        }

    env = {
        'starting_path' : '~',
        }
    font = {
        'name' : 'Monospace',
        'size' : 12,
        }
    color_map = {
        # reguler
        'text'          : '#000000', # black
        'text_selected' : '#000000', # black
        'base'          : '#FBEFCD', # wheat - mod
        'base_selected' : '#FFA500', # orenge
        'status'        : '#808080', # gray
        'status_active' : '#C0C0C0', # silver
        # highlight
        'reserve'       : '#0000FF', # blue
        'comment'       : '#008000', # green
        'literal'       : '#FF0000', # red
        'label'         : '#808000', # olive
        }


    _auto_update = {
        # 'signal_like_string'  : [ (widget, callback, data_list), ... ]
        'update_font'           : [  ],
        'update_color_map'      : [  ],
        }

    ### signal-like auto-update function
    @staticmethod
    def _sig_update_font_modify(widget, weight = 1):
        widget.modify_font(
            pango.FontDescription('{0} {1}'.format(zTheme.font['name'], int(zTheme.font['size'] * weight)))
            )

    @staticmethod
    def _sig_update_font_property(widget, weight = 1):
        widget.set_property(
            'font-desc',
            pango.FontDescription('{0} {1}'.format(zTheme.font['name'], int(zTheme.font['size'] * weight)))
            )
    ### end of signal-like auto-update function


    @staticmethod
    def get_env():
        return zTheme.evn

    @staticmethod
    def set_env(dic):
        for (k, v) in dic.iteritems():
            if k in zTheme.env and v != zTheme.env[k]:
                zTheme.env[k] = v

    @staticmethod
    def get_font():
        return zTheme.font

    @staticmethod
    def set_font(dic):
        modified = False
        for (k, v) in dic.iteritems():
            if k in zTheme.font and v != zTheme.font[k]:
                modified = True
                zTheme.font[k] = v
        if modified:
            zTheme.reg_emit('update_font')

    @staticmethod
    def get_color_map():
        return zTheme.color_map

    @staticmethod
    def set_color_map(dic):
        modified = False
        for (k, v) in dic.iteritems():
            if k in zTheme.color_map and v != zTheme.color_map[k]:
                modified = True
                zTheme.color_map[k] = v
        if modified:
            zTheme.reg_emit('update_color_map')
