# this contains everything about Macro parsing

import zPE

from time import strftime


MACRO_DEF = {
    # Macro_Name : generation_function(macro_arguments)
    }
MACRO_GEN = {
    # Line_Num : [ generated_lines ]
    }

SYS_VAR_SYMBOL = {
    '&SYSNDX'  : 0,    # a 4 digit auto-increment number, starting at 1
    '&SYSLIST' : [],   # refer to any positional parameter in a macro definition
    '&SYSDATE' : None, # date on which source module was assembled MM/DD/YY
    '&SYSTIME' : None, # time at which source module was assembled hh.mm
    '&SYSECT'  : None, # name of the current control section
    '&SYSPARM' : None, # need info
    }

VAR_SYMBOL = {
    # local_symbol : value
    }

IBM_MACRO = {
    'IF'     : lambda args: [
        ],
    'ELSEIF' : lambda args: [
        ],
    'ELSE'   : lambda: [
        ],
    'ENDIF'  : lambda: [
        ],

    'SELECT' : lambda args: [
        ],
    'WHEN'   : lambda args: [
        ],
    'ENDSEL' : lambda: [
        ],

    'DO'     : lambda args: [
        ],
    'ENDDO'  : lambda: [
        ],
    }


def macro_init():
    MACRO_DEF.update(IBM_MACRO)
    SYS_VAR_SYMBOL['&SYSDATE'] = strftime('%m/%d/%Y')
    SYS_VAR_SYMBOL['&SYSTIME'] = strftime('%H.%M')


def macro_parse(spi):
    for line in spi:
        field = zPE.resplit_sq('\s+', line[:-1], 3)

