# this defines the basic assembler instruction set
# need to be concatenated with either ASSIST instruction set
# or ASMA90 instruction set

import zPE

import os, sys


# op-code look-up table
op_code = {
    '' : '',
    }


def run(step):
    print ('exec ' + step.pgm + ' in ' +
           os.path.join(* step.dd['STEPLIB']['DSN']) + ' . . .')
    return -1
