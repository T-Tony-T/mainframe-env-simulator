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

        'scratch'    : '''*
* This buffer is for notes you don't want to save.
* If you want to create a file, do that with
*   {0}
* or save this buffer explicitly.
*
'''.format('"Open a New Buffer" -> Right Click -> "New File"')
        },
    }


class AsmMode(BaseMode):
    def __init__(self, ast):
        super(AsmMode, self).__init__(ast, 'ASM Mode', LC['default'])


    def align(self, line):
        '''
        line
            the tuple of the format (line_number, line_content, cursor_offset)

        return
            aligned line tuple, or None if nothing need to be changed
        '''
        print 'ASM Mode :: align ~', line
        return None


    def comment(self, line):
        '''
        line
            the tuple of the format (line_number, line_content, cursor_offset)

        return
            the line tuple with comment added / ajusted, or None if nothing need to be changed
        '''
        print 'ASM Mode :: comment ~', line
        return None


    def complete(self, line):
        '''
        line
            the tuple of the format (line_number, line_content, cursor_offset)

        return
            the completion-list
        '''
        print 'ASM Mode :: complete ~', line
        return [ ]


    def hilite(self):
        '''
        line
            the tuple of the format (line_number, line_content, cursor_offset)

        return
            the highlight tag info list
        '''
        return [ ]
