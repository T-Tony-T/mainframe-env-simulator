# Major Mode : Text Mode

from zPE.GUI.basemode import BaseMode

LC = {                          # local config
    'ast-map' : {
        'pos_rlvnt' : { },
        'non_split' : {
            'DQUOTE' : ( 0, '"', '"', ),
            'SQUOTE' : ( 0, "'", "'", ),
            },
        'key_words' : { },
        'level_dlm' : { },
        },
    }


class TextMode(BaseMode):
    def __init__(self):
        super(TextMode, self).__init__('Text Mode', ast_map = LC['ast-map'])

