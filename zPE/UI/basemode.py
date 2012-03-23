# this is the templete Major Editing Mode
# every Major Mode need to be derived from this mode

class BaseMode(object):
    '''
    Abstract Base Class for Major Editing Modes;
    Any major mode need to be derived from this class
    '''

    def __init__(self, mode = '__base_mode__'):
        self.mode = mode

    def __str__(self):
        '''return mode string'''
        return self.mode.title()

    def align(self, line, pos):
        '''return aligned line'''
        raise AssertionError('require overridden')

