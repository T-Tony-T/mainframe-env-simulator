# this is the definition and the implementation of Registers
# currently defines: General Purpose Registers, PSW

import zPE

import re
from ctypes import *            # for Union and C-Style array


## General Purpose Register
class Register(Union):
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
        return '{0:0>8}'.format(hex(self.long)[2:-1].upper())


    def __add__(self, other):
        '''
        AR  R1,R2       =>      R1 + R2
        A   R1,addr     =>      R1 + value@addr
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        self_sign = self.sign()
        self.long += other.long          # perform the addition
        if ( self_sign * other.sign()  and            # both non-zero
             self_sign == other.sign() != self.sign() # same sign => diff sign
             ):
            # overflow occurs
            SPR['PSW'].CC = 3
            if SPR['PSW'].Program_mask & 0b1000 == 0b1000:
                raise OverflowError('fixed-point overflow exception.')
        else:
            SPR['PSW'].CC = self.sign()

    def __sub__(self, other):
        '''
        SR  R1,R2       =>      R1 - R2
        S   R1,addr     =>      R1 - value@addr
        '''
        if isinstance(other, Register):
            self.__add__(Register(- other.long))
        else:
            self.__add__(Register(- other))

    def __lshift__(self, other):
        '''
        LR  R1,R2       =>      R1 << R2
        LA  R1,addr     =>      R1 << addr
        L   R1,addr     =>      R1 << value@addr
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        self.long = other.long

    def __rshift__(self, other):
        '''
        ST  R1,addr     =>      R1 >> ( Page, addr )
        '''
        if ( len(other) != 2  or
             not isinstance(other[0], zPE.core.mem.Page)  or
             not isinstance(other[1], int)  or
             not 0 <= other[1] < 4096
             ):
            raise TypeError('Second operand must be of type `(Page, addr)`.')
        other[0].store(other[1], self.long)


    def sign(self):
        if self.positive():
            return 2
        elif self.negative():
            return 1
        else:
            return 0

    def positive(self):
        # 0x80000000 will mask off all but the sign bit
        if self.long & 0x80000000 == 0:
            return self.long != 0
        else:
            return False
    def negative(self):
        # 0x80000000 will mask off all but the sign bit
        if self.long & 0x80000000 == 0x80000000:
            return self.long != 0
        else:
            return False

class RegisterPair(object):
    def __init__(self, even, odd):
        if not isinstance(even, Register) or not isinstance(odd, Register):
            raise TypeError('Both operands must be of type `Register`.')
        self.even = even
        self.odd  = odd

    def __str__(self):
        return '{0} {1}'.format(self.even, self.odd)

    def __mul__(self, other):
        '''
        MR  R2,R3       =>      R2 * R3
        M   R2,addr     =>      R2 * value@addr
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        res = '{0:0>16}'.format(hex(self.odd.long * other.long)[2:-1].upper())
        self.even.long = int(res[ :8], 16)
        self.odd.long  = int(res[8: ], 16)

    def __div__(self, other):
        self.__truediv__(other)
    def __truediv__(self, other):
        '''
        DR  R2,R3       =>      R2 / R3
        D   R2,addr     =>      R2 / value@addr
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        if other.sign() == 0:       # zero-division
            raise OverflowError('fixed-point divide exception.')

        dividend = (self.even.long << 32) + self.odd.long
        self.even.long = abs(dividend % other.long)
        res = (dividend - self.even.long) / other.long

        if not -0x80000000 <= res < 0x80000000: # quotient too large
            raise OverflowError('fixed-point divide exception.')
        self.odd.long  = res
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

    def __getitem__(self, key):
        return ''.join(self.dump_bin())[key]


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


    def snapshot(self):
        ss = PSW(self.C)
        for (k, v) in self.__dict__.iteritems():
            ss.__dict__[k] = v
        return ss
# end of PSW class definition


## Register Pool
GPR_NUM = 16                    # number of general purpose registers

GPR = [                         # general purpose registers
    Register(0x0), Register(0x1), Register(0x2), Register(0x3), # R0  ~ R3
    Register(0x4), Register(0x5), Register(0x6), Register(0x7), # R4  ~ R7
    Register(0x8), Register(0x9), Register(0xA), Register(0xB), # R8  ~ R11
    Register(0xC), Register(0xD), Register(0xE), Register(0xF)  # R12 ~ R15
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

    if 0 <= reg_num < zPE.core.reg.GPR_NUM:
        return ( reg_num, equ, )
    else:
        return (   -1,    equ, )


SPR = {                         # special purpose registers
    'PSW' : PSW(PSW_MODE['BC']),
    }

SPR['PSW'].Channel_masks = 127  # turn on all internal channels
SPR['PSW'].E = 1                # also turn on external channel
SPR['PSW'].PSW_key = 1          # superuser mode
