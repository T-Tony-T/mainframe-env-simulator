# Major Mode : Asm Mode

from zPE.UI.basemode import BaseMode

LC = {                          # local config
    'default' : {
        'JCL-header' : '''
//KC00NIUA JOB ,'DEFAULT ASSIST JCL',MSGCLASS=H
//STEP1    EXEC PGM=ASSIST
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
'''[1:],

        'JCL-tailer' : '''
/*
//
'''[1:],

        'scratch'    : '''* (test this)
* This buffer is for notes you don't want to save.
* If you want to create a file, do that with
*   {0}
* or save this buffer explicitly.
*
'''.format('"Open a New Buffer" -> Right Click -> "New File"')
        },


    'ast-map' : {
        'pos_rlvnt'     : {
            'LN-CMMNT'  : r'(\*.+)',
            'LN-LABEL'  : r'([a-zA-Z][a-zA-Z0-9]*)',
            'INSTRUCT'  : r'(?:[a-zA-Z][a-zA-Z0-9]*)? +([a-zA-Z]+).*',
            'END-CMMNT' : r'(?:[a-zA-Z][a-zA-Z0-9]*)? +(?:[a-zA-Z]+ +){2}(.+)',
            },
        'non_split'     : {
            'QUOTE'     : ( "'", "'" ),
            },
        'key_words' : {
            'OPERATOR'  : ( r'([*/+-]).*', 0 ),
            'LABEL'     : ( r'([a-zA-Z][a-zA-Z0-9]*).*', 0 ),
            'NUMBER'    : ( r'([0-9]+(?:\.[0-9]+)?).*', 0 ),
            'CONSTANT'  : ( r"(=?[0-9]*[CGXBFHEDLPZAYSVQ](?:L[0-9]+)?(:?'[^']*')?)", 0 ),
            },
        'level_dlm' : {
            'PAREN'     : ( '(', ')' ),
            },
        },
    }


class AsmMode(BaseMode):
    def __init__(self):
        super(AsmMode, self).__init__('ASM Mode', LC['default'], LC['ast-map'])


    def align(self, line, ast):
        '''
        line
            the tuple of the format (line_number, line_content, cursor_offset)
        ast
            the abstract syntax tree associated with the buffer

        return
            aligned line tuple, or None if nothing need to be changed
        '''
        print 'ASM Mode :: align ~', line, ast
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
        print 'ASM Mode :: comment ~', line, ast
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
        print 'ASM Mode :: complete ~', line, ast
        return [ ]


    def hilite(self, ast):
        '''
        ast
            the abstract syntax tree associated with the buffer

        return
            the highlight tag info list
        '''
        return [ ]
