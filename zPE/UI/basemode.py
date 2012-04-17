# this is the templete Major Editing Mode
# every Major Mode need to be derived from this mode

LC = {                          # local config
    'default' : {
        'JCL-header' : '''
//KC00NIUA JOB ,'DEFAULT DUMMY JCL',MSGCLASS=H
//STEP1    EXEC PGM=IEFBR14
//DUMMY    DD *
'''[1:],

        'JCL-tailer' : '''
/*
//
'''[1:],

        'scratch'    : '''
  This buffer is for notes you don't want to save.
  If you want to create a file, do that with
    {0}
  or save this buffer explicitly.

'''.format('"Open a New Buffer" -> Right Click -> "New File"'),
        },


    'ast-map' : {
        'pos_rlvnt' : { },
        'non_split' : { },
        'key_words' : { },
        'level_dlm' : { },
        },
    }

class BaseMode(object):
    '''
    Abstract Base Class for Major Editing Modes;
    Any major mode need to be derived from this class
    '''

    from zComp.zText import zBufferChange, zAtomicChange, zCompletionDict

    # define all completion dictionary here
    _cp_dict_ = {
        }

    def __init__(self, mode = '__base_mode__', default = LC['default'], ast_map = LC['ast-map']):
        '''
        mode
            the mode string of the major editing mode
        default
            a dictionary containing the following mappings:
                'JCL-header' : the header part of default JCL
                'JCL-tailer' : the tailer part of default JCL
                'scratch'    : the default text to display when the
                               scratch buffer is (re)loaded
        ast_map
            a dictionary containing the following mappings:
            (precedence high -> low)
                'pos_rlvnt'  : position-relevant regular expression mapping
                               (empty dict for context-free languages)
                'non_split'  : AST minimal unit delimiter mapping
                               (empty dict unless absolutely needed)
                'key_words'  : AST reserved word mapping
                'level_dlm'  : AST level delimiter mapping

            see zPE.UI.zComp.zSyntaxParser.zSyntaxParser() for detailed info
        '''
        self.mode    = mode
        self.default = default
        self.ast_map = ast_map


    def __str__(self):
        '''return mode string'''
        return self.mode


    def align(self, line, ast):
        '''
        line
            the tuple of the format (line_number, line_content, cursor_offset)
        ast
            the abstract syntax tree associated with the buffer

        return
            an zAtomicChange object indicating what need to be changed, or
            None if nothing need to be changed
        '''
        return None


    def comment(self, line, ast):
        '''
        line
            the tuple of the format (line_number, line_content, cursor_offset)
        ast
            the abstract syntax tree associated with the buffer

        return
            the line tuple with comment added / ajusted, or None if nothing need to be changed
        '''
        return None


    def complete(self, line, ast):
        '''
        line
            the tuple of the format (line_number, line_content, cursor_offset)
        ast
            the abstract syntax tree associated with the buffer

        return
            the completion-list
        '''
        return [ ]


    def hilite(self, ast):
        '''
        ast
            the abstract syntax tree associated with the buffer

        return
            the highlight tag info list, where each tag entry is
            (abs_pos_s, hilite_key, abs_pos_e)
        '''
        return [ ]
