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

from zPE.util.global_config import GPR

def init(step):
    GPR[15] = 0    # set return code
    return GPR[15]
