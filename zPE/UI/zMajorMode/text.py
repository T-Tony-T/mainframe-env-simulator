# Major Mode : Text Mode

from zPE.UI.basemode import BaseMode

class TextMode(BaseMode):
    def __init__(self, ast):
        super(TextMode, self).__init__(ast, 'Text Mode')

