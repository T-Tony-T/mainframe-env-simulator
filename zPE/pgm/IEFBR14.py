################################################################
# Program Name:
#     IEFBR14
#
# Purpose:
#     directly return to the caller
#
# Parameter:
#     none
#
# Input:
#     none
# Output:
#     none
#
# Return Code:
#     00000000  unconditionally
# Return Value:
#     none
################################################################

import zPE

def init(step):
    zPE.core.reg.GPR[15] = 0    # set return code
    return zPE.core.reg.GPR[15]
