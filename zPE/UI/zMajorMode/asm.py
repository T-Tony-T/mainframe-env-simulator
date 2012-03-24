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
    def __init__(self):
        super(AsmMode, self).__init__('ASM Mode', LC['default'])

