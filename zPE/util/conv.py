# this wraps around conversion fuctions defined in zPE.base.core.asm

import zPE.base.core.asm as asm
from zPE.util import h2i, h2i_sign, i2h, i2h_sign, i2i_sign

## constant type conversion

def c2x(src):
    return asm.X_.tr(asm.C_(src).dump())

def x2c(src):
    return asm.C_.tr(asm.X_(src).dump())

def b2x(src):
    return asm.X_.tr(asm.B_(src).dump())

def h2x(src):
    return asm.X_.tr(asm.H_(src).dump())

def f2x(src):
    return asm.X_.tr(asm.F_(src).dump())


## interger conversion

def p2i(src):
    return asm.P_.tr_val(asm.X_(src).dump())

def i2p(src):
    return asm.X_.tr(asm.P_(str(src)).dump())
