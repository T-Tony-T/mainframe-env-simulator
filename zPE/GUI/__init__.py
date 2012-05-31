# this is the GUI-level dummy package that
# holds everything together
# 
# zPE.GUI.io_encap      contains wrapper functions for I/O
# zPE.GUI.majormode     major editing mode selector
# zPE.GUI.basemode      defines the BaseMode that every major mode need to be derived from
#
# zPE.GUI.zMajorMode    contains all pre-installed major modes
# zPE.GUI.image         contains all image/icon resources
#
# zPE.GUI.window        contains the entry-point (the GUI driver)
# zPE.GUI.conf          GUI configuation file
# zPE.GUI.zComp         contains all component/widget used in the GUI
# 

import os, sys, inspect
GUI_PGK_PATH = os.path.split(inspect.getfile(inspect.currentframe()))

def min_import(module, attr_list, import_level = -1, path = None):
    '''minimal-import of the given attr from the module'''
    if path and path not in sys.path:
        sys.path.insert(0, path)
        path = True
    else:
        path = False
    _temp = __import__(module, globals(), locals(), attr_list, import_level)
    if path:
        sys.path.pop(0)
    if len(attr_list) == 1:
        return eval('_temp.{0}'.format(attr_list[0]))
    return [ eval('_temp.{0}'.format(attr)) for attr in attr_list ]
