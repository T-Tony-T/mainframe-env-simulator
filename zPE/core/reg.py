# this is the definition and the implementation of Registers
# currently defines: GPR, PSW

import zPE

import os, sys
import re
from ctypes import *            # for Union and C-Style array


## General Purpose Register
class GPR(Union):
    _fields_ = [
        ('long', c_ulong),
        ('bytes', c_ubyte * 4),
        ]

    def __getitem__(self, key):
        if key == 0:
            return self.long    # 0 to get the entire register
        else:
            return self.bytes[(4-key)%4] # reverse the byte order

    def __setitem__(self, key, val):
        if key == 0:
            self.long = val
        else:
            self.bytes[(4-key)%4] = val

    def __str__(self):
        return '{0:0>8}'.format(hex(self.long)[2:-1])

    def positive(self):
        # 0x80000000 will mask off all but the sign bit
        if self.long & int('80000000', 16) == 0:
            return True
        else:
            return False
    def negative(self):
        return not self.positive
# end of GPR class definition

## Program Status Word
PSW_MODE = { 'EC' : 1, 'BC' : 0 }
# EC: Extended Control Mode, 31-bit addressing
# BC: Basic Control Mode, 24-bit addressing

class PSW(object):
    def __init__(self, C = 0):
        if C == PSW_MODE['EC']:
            self.__full_init(
                0, 1, 0, None,
                0, 0, PSW_MODE['EC'], 0, 1, 1,
                1, None, None,
                0, 0, 0
                )
        else:
            self.__full_init(
                None, None, None, 0,
                0, 0, PSW_MODE['BC'], 0, 1, 1,
                None, 0, 0,
                0, 0, 0
                )

    def __full_init(self, R, T, I, Channel_masks,
                    E, PSW_key, C, M, W, P,
                    S, Interruption_code, ILC,
                    CC, Program_mask, Instruct_addr
                    ):
        # EC only:
        self.R = R              # (R) Program event recording mask
        self.T = T              # (T = 1) DAT mode
        self.I = I              # (I) Input/output mask
        # BC only:
        self.Channel_masks = Channel_masks
                                # 64: Channel 0 mask
                                # 32: Channel 1 mask
                                # 16: Channel 2 mask
                                #  8: Channel 3 mask
                                #  4: Channel 4 mask
                                #  2: Channel 5 mask
                                #  1: Mask for channel 6 and up

        # EC + BC:
        self.E = E              # (E) External mask
        self.PSW_key = PSW_key
        self.C = C              # (C = 0) Control mode:
                                #      0 -> Basic Control mode
                                #      1 -> Extended Control mode
        self.M = M              # (M) Machine check mask
        self.W = W              # (W = 1) Wait state
        self.P = P              # (P = 1) Problem state

        # EC only:
        self.S = S              # (S = 1) Secondary space mode
        # BC only:
        self.Interruption_code = Interruption_code
        self.ILC = ILC          # (ILC) Instruction length code

        # EC + BC:
        self.CC = CC            # (CC) Condition code
        self.Program_mask = Program_mask
                                #  8: Fixed point overflow mask
                                #  4: Decimal overflow mask
                                #  2: Exponent underflow mask
                                #  1: Significance mask
        self.Instruct_addr = Instruct_addr
    # end of __full_init()

    def dump_bin(self):
        if self.C == PSW_MODE['EC']:
            return (
                ''.join([
                # 1st word
                '0{0}000{1}{2}{3}'.format(self.R, self.T, self.I, self.E),  #  8
                '{0:0>4}'.format(bin(self.PSW_key)[2:]),                    # 12
                '{0}{1}{2}{3}'.format(self.C, self.M, self.W, self.P),      # 16
                '{0}0{1:0>2}'.format(self.S, bin(self.CC)[2:]),             # 20
                '{0:0>4}'.format(bin(self.Program_mask)[2:]),               # 24
                '00000000',                                                 # 32
                ]),
                ''.join([
                # 2nd word
                '00000000',                                                 #  8
                '{0:0>24}'.format(bin(self.Instruct_addr)[2:])              # 32
                ])
                )
        else:
            return (
                ''.join([
                # 1st word
                '{0:0>7}{1}'.format(bin(self.Channel_masks)[2:], self.E),   #  8
                '{0:0>4}'.format(bin(self.PSW_key)[2:]),                    # 12
                '{0}{1}{2}{3}'.format(self.C, self.M, self.W, self.P),      # 16
                '{0:0>16}'.format(bin(self.Interruption_code)[2:]),         # 32
                ]),
                ''.join([
                # 2nd word
                '{0:0>2}'.format(bin(self.ILC)[2:]),                        #  2
                '{0:0>2}'.format(bin(self.CC)[2:]),                         #  4
                '{0:0>4}'.format(bin(self.Program_mask)[2:]),               #  8
                '{0:0>24}'.format(bin(self.Instruct_addr)[2:])              # 32
                ])
                )

    def dump_hex(self):
        (w1, w2) = self.dump_bin()
        h1 = hex(int(w1, 2))
        if h1[-1] == 'L':       # check the 'L' appended by int()
            h1 = h1[2:-1]
        else:
            h1 = h1[2:]
        h2 = hex(int(w2, 2))
        if h2[-1] == 'L':       # check the 'L' appended by int()
            h2 = h2[2:-1]
        else:
            h2 = h2[2:]
        return ( '{0:0>8}'.format(h1.upper()), '{0:0>8}'.format(h2.upper()) )

    def __str__(self):
        (w1, w2) = self.dump_hex()
        return '{0} {1}'.format(w1, w2)

    def set_mode(self, C):
        if C == PSW_MODE['EC']:
            self.__full_init(
                0, 1, 0, None,
                self.E, self.PSW_key, PSW_MODE['EC'], self.M, self.W, self.P,
                1, None, None,
                self.CC, self.Program_mask, self.Instruct_addr
                )
        else:
            self.__full_init(
                None, None, None, 0,
                self.E, self.PSW_key, PSW_MODE['BC'], self.M, self.W, self.P,
                None, 0, 0,
                self.CC, self.Program_mask, self.Instruct_addr
                )
# end of PSW class definition


## Register Pool
GPR_NUM = 16                    # number of general purpose registers

GPR = [                         # general purpose registers
    GPR(0), GPR(0), GPR(0), GPR(0), # R0  ~ R3
    GPR(0), GPR(0), GPR(0), GPR(0), # R4  ~ R7
    GPR(0), GPR(0), GPR(0), GPR(0), # R8  ~ R11
    GPR(0), GPR(0), GPR(0), GPR(0)  # R12 ~ R15
    ]

def parse_GPR(reg_str):
    equ = None
    if isinstance(reg_str, int):
        reg_num = reg_str
    elif reg_str.isdigit():
        reg_num = int(reg_str)
    else:
        # check reg equates
        lbl_8 = '{0:<8}'.format(reg_str)
        sym_map = zPE.pgm.ASMA90.SYMBOL
        if lbl_8 in sym_map  and  sym_map[lbl_8].type == 'U':
            equ = sym_map[lbl_8]
            reg_num = equ.value
        else:
            reg_num = -1        # invalidate reg_str

    if 0 <= reg_num  and  reg_num < zPE.core.reg.GPR_NUM:
        return ( reg_num, equ, )
    else:
        return (   -1,    equ, )


SPR = {                         # special purpose registers
    'PSW' : PSW(PSW_MODE['BC']),
    }
