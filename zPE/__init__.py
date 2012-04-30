# this is the top-level dummy package that
# holds everything together
# 
# zPE.base   defines the base system of the simulator
# zPE.GUI    defines the GUI component of the simulator
# zPE.util   defines the utility functions
# zPE.script contains the entry-point to CLI + GUI executables
# 

import pkg_resources

def pkg_info():
    return pkg_resources.require('mainframe-env-simulator')[0]

