# this contains everything about Macro parsing

from zPE.util import *
from zPE.util.global_config import *

import zPE.base.core.asm

from asma90_macro_sys1_maclib import MACRO_DEF as MACRO_DEF_SYS1

from time import strftime


MACRO_DEF = {
    # Macro_Name : generation_function(macro_arguments)
    }
MACRO_ERR = {
    # SYSNDX : error_msg
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

SEQ_SYMBOL = {
    # sequence_symbol : line_num
    }


def macro_init():
    SYS_VAR_SYMBOL['&SYSDATE'] = strftime('%m/%d/%Y')
    SYS_VAR_SYMBOL['&SYSTIME'] = strftime('%H.%M')


def macro_parse(spi):
    if not spi.empty():
        __scanning(spi)

def __scanning(spi, line_num = 0):
    # MACRO definition section
    while line_num < len(spi):
        line_num += 1           # start at line No. 1
        line = spi[line_num - 1]

        field = resplit_sq(r'\s+', line[:-1], 3)

        # non-instruction stuff
        if len(field) < 2:
            continue

        # starting point of macro definition
        elif field[1] == 'MACRO':
            line_num = __defining(spi, line_num + 1)

        # first non-macro-def statement -> end of the current section
        else:
            line_num -= 1       # put back the line just read
            break               # goto the next section

    # ASM section
    while line_num < len(spi):
        line_num += 1           # start at line No. 1
        line = spi[line_num - 1]

        field = resplit_sq(r'\s+', line[:-1], 3)

        # non-instruction stuff
        if len(field) < 2:
            continue

        # machine instruction
        elif zPE.base.core.asm.valid_op(field[1]):
            continue

        # ASM instruction
        elif zPE.base.core.asm.valid_ins(field[1]):
            continue

        # in-line macro
        elif field[1] in MACRO_DEF:
            pass                # expend here

        # lib macro
        elif field[1] in MACRO_DEF_SYS1:
            pass                # expend here


def __defining(spi, line_num):
    while line_num < len(spi):
        line_num += 1           # start at line No. 1
        line = spi[line_num - 1]

        field = resplit_sq(r'\s+', line[:-1], 3)
# try parsing .labels and &labels
#        var_lbl = zPE.bad_(field[0])

        # comment
        if field[0].startswith('.*'):
            continue

        # check instruction
        if len(field) < 2:
            abort(90, 'Error: ', line[:-1], ': Invalid macro statement.\n')

        # ending point of macro definition
        elif field[1] == 'MEND':
            return line_num

