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
    }

class BaseMode(object):
    '''
    Abstract Base Class for Major Editing Modes;
    Any major mode need to be derived from this class
    '''

    def __init__(self, mode = '__base_mode__', default = LC['default']):
        self.mode = mode
        self.default = default

    def __str__(self):
        '''return mode string'''
        return self.mode

    def align(self, line, pos):
        '''return aligned line'''
        raise AssertionError('require overridden')

    def comment(self, line):
        '''return the line with comment added / ajusted'''
        raise AssertionError('require overridden')

    def complete(self, line, pos):
        '''return the completion-list'''
        raise AssertionError('require overridden')

