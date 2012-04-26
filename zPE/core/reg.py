# this is the definition and the implementation of Registers
# currently defines: General Purpose Registers, PSW

import zPE

import re
from ctypes import *            # for Union and C-Style array


## General Purpose Register
class Register(Union):
    _fields_ = [
        ('long', c_ulong),
        ('int',  c_long),
        ('bytes', c_ubyte * 4),
        ]

    def addr(self, amode = 24):
        if amode == 24:
            return ( self.long & 0x00FFFFFF )
        elif amode == 31:
            return ( self.long & 0x7FFFFFFF )
        else:
            raise KeyError('Invalid Address Mode!')

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
        return '{0:0>8}'.format(zPE.i2h(self.long))


    def __add__(self, other):
        '''
        AR   R1,R2      =>      R1 + R2
        A    R1,addr    =>      R1 + value@addr
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        self_sign = self.sign()
        self.long += other.long          # perform the addition
        if ( self_sign * other.sign()  and            # both non-zero
             self_sign == other.sign() != self.sign() # same sign => diff sign
             ):                 # overflow occurs
            return self.__overflow()
        else:                   # no overflow, test sign
            return self.test()
    def add_lgc(self, other):
        '''
        ALR  R1,R2      =>      R1.add_lgc(R2)
        AL   R1,addr    =>      R1.add_lgc(value@addr)
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        carry = self.long + other.long # perform the addition
        self.long = carry              # fill the register
        carry >>= 32                   # get the carry
        # 00 - carry 0, res 0
        # 01 - carry 0, res non-zero
        # 10 - carry 1, res 0
        # 11 - carry 1, res non-zero
        SPR['PSW'].CC = (bool(carry) << 1) + bool(self.int)
        return SPR['PSW'].CC

    def __sub__(self, other):
        '''
        SR   R1,R2      =>      R1 - R2
        S    R1,addr    =>      R1 - value@addr
        '''
        if isinstance(other, Register):
            return self.__add__(Register(- other.int))
        else:
            return self.__add__(Register(- other))
    def sub_lgc(self, other):
        '''
        SLR  R1,R2      =>      R1.sub_lgc(R2)
        SL   R1,addr    =>      R1.sub_lgc(value@addr)
        '''
        # get the 2's complement
        if not isinstance(other, Register):
            other = Register(- other)
        else:
            other.long = (- other.int)
        carry = self.long + other.long # perform the addition
        self.long = carry              # fill the register
        carry >>= 32                   # get the carry
        # 00 - never
        # 01 - carry 0, res non-zero
        # 10 - res 0
        # 11 - carry 1, res non-zero
        if not self.int:
            SPR['PSW'].CC = 2
        else:
            if carry:
                SPR['PSW'].CC = 3
            else:
                SPR['PSW'].CC = 1
        return SPR['PSW'].CC

    def __mul__(self, other):
        '''
        MH   R1,addr    =>      R1 * value@addr
        '''
        self.int *= Register(zPE.i2i_sign(other,4,8)).int
        return self


    def __lshift__(self, other):
        '''
        SLL   R1,addr   =>      R1 << addr
        '''
        self.long <<= (other & 0b111111)
        return self

    def __rshift__(self, other):
        '''
        SRL   R1,addr   =>      R1 >> addr
        '''
        self.long >>= (other & 0b111111)
        return self

    def lshft(self, other):
        '''
        SLA   R1,addr   =>      R1.lshft(addr)
        '''
        res  = self.long << (other & 0b111111)
        self.long &= 0x80000000 # only preserve sign bit
        self.long += (res & 0x7FFFFFFF) # add the rest 31 bits

        res_test  = res >> 32                       # bits shifted out
        test_mask = (0b1 << (other & 0b111111)) - 1 # num-of-bit-shifted 1s
        if 0 < res_test < test_mask: # overflow occured
            SPR['PSW'].CC = 3
        else:
            self.test()
        return self

    def rshft(self, other):
        '''
        SRA   R1,addr   =>      R1.rshft(addr)
        '''
        self.int >>= (other & 0b111111)
        return self.test()      # overflow will never occur


    def __nonzero__(self):
        '''used by bool(self), should not set CC here'''
        return bool(self.long)

    def __and__(self, other):
        '''
        NR   R1,R2      =>      R1 & R2
        N    R1,addr    =>      R1 & value@addr
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        self.long &= other.long
        SPR['PSW'].CC = bool(self)
        return self

    def __or__(self, other):
        '''
        OR   R1,R2      =>      R1 | R2
        O    R1,addr    =>      R1 | value@addr
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        self.long |= other.long
        SPR['PSW'].CC = bool(self)
        return self

    def __xor__(self, other):
        '''
        XR   R1,R2      =>      R1 ^ R2
        X    R1,addr    =>      R1 ^ value@addr
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        self.long ^= other.long
        SPR['PSW'].CC = bool(self)
        return self


    def cmp(self, other):
        '''
        CR   R1,R2      =>      R1.cmp(R2)
        C    R1,addr    =>      R1.cmp(value@addr)
        CH   R1,addr    =>      R1.cmp(value@addr)
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        SPR['PSW'].CC = self.__compare(self.int, other.int)
        return SPR['PSW'].CC

    def cmp_lgc(self, other):
        '''
        CLR  R1,R2      =>      R1.cmp_lgc(R2)
        CL   R1,addr    =>      R1.cmp_lgc(value@addr)
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        SPR['PSW'].CC = self.__compare(self.long, other.long)
        return SPR['PSW'].CC


    def load(self, other, hw = False):
        '''
        LR   R1,R2      =>      R1.load(R2)
        LA   R1,addr    =>      R1.load(addr)
        L    R1,addr    =>      R1.load(value@addr)
        LH   R1,addr    =>      R1.load(value@addr, hw = True)
        LM   R1,R2,addr =>    [ GPR[(R1+offset)%16].load(value@addr+offset*4)
                                for offset in range( [
                                    R1 + i for i in range(16)
                                    ][R2 - R1 + 1] - R1 )
                                ]
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        self.long = zPE.i2i_sign(other.long, 8 - hw * 4, 8)
        return self

    def inc(self, value, pos_mask = None):
        '''
        IC   R1,addr    =>      R1.inc(value@addr)
        ICM  R1,addr    =>    ( lambda mask = listify_mask(mask_string) :
                                    R1.inc(value@addr:addr+len(mask), mask)
                                )()
        '''
        if pos_mask == None:
            self[4] = value
        else:
            if not pos_mask or zPE.h2i(value) == 0:
                SPR['PSW'].CC = 0
            elif zPE.h2i(value[:1]) >= 0x8:
                SPR['PSW'].CC = 1
            else:
                SPR['PSW'].CC = 2
            # insert the bytes
            for pos in pos_mask:
                self[pos + 1] = zPE.h2i(value[:2])
                value = value[2:]
        return self

    def store(self, page, addr, hw = False):
        '''
        ST   R1,addr    =>      R1.stort(Page, addr_into_page)
        STH  R1,addr    =>      R1.stort(Page, addr_into_page, hw = True)
        STM  R1,R2,addr =>    [ GPR[(R1+offset)%16].store(Page, addr_into_page)
                                for offset in range( [
                                    R1 + i for i in range(16)
                                    ][R2 - R1 + 1] - R1 )
                                ]
        '''
        if ( not isinstance(page, zPE.core.mem.Page)  or
             not isinstance(addr, int)  or
             not 0 <= addr < 4096
             ):
            raise TypeError('Operands must be of type `Page` and `int`.')
        page.store(addr, zPE.i2i_sign(self.long, 8, 8 - hw * 4))
        return self

    def stc(self, page, addr, pos = 3):
        '''
        STC  R1,addr    =>      R1.stc(Page, addr_into_page)
        STCM R1,addr    =>    ( lambda mask = listify_mask(mask_string) : [
                                    R1.stc(Page, addr_into_page, mask[offset])
                                    for offset in range(len(mask))
                                    ]
                                )()
        '''
        page[addr] = self[pos + 1]
        return self


    def set_abs(self):
        '''
        LPR  R1,R2      =>      R1.load(R2).set_abs()
        '''
        if self.long == 0x80000000: # overflow occurs, -0x80000000 == 0x80000000
            return self.__overflow() # no need to change the value
        else:
            self.long = abs(self.int)
            return self.test()

    def neg_abs(self):
        '''
        LNR  R1,R2      =>      R1.load(R2).neg_abs()
        '''
        self.long = -abs(self.int)
        return self.test()

    def neg_val(self):
        '''
        LCR  R1,R2      =>      R1.load(R2).neg_val()
        '''
        if self.positive():
            return self.neg_abs()
        else:
            return self.set_abs()

    def test(self):
        '''
        LTR  R1,R2      =>      R1.load(R2).test()
        '''
        SPR['PSW'].CC = self.sign()
        return self

    def decrement(self):
        '''
        BCT  R1,addr    =>      R1.decrement() and <branching_to_addr>
        BCTR R1,R2      =>      R1.decrement() and <branching_if_R2>
        '''
        self.long -= 1
        return self

    def sign(self):
        if self.positive():
            return 2
        elif self.negative():
            return 1
        else:
            return 0

    def positive(self):
        return self.int > 0

    def negative(self):
        return self.int < 0


    ### supporting functions
    def __compare(self, left, right):
        if left == right:
            return 0
        elif left < right:
            return 1
        else:
            return 2

    def __overflow(self):
        SPR['PSW'].CC = 3
        if SPR['PSW'].Program_mask & 0b1000 == 0b1000:
            raise zPE.newFixedPointOverflowException()
        return self
# end of Register class

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
        MR   R2,R3      =>      RegisterPair(R2,R2+1) * R3
        M    R2,addr    =>      RegisterPair(R2,R2+1) * value@addr
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        res = zPE.i2h_sign(self.odd.int * other.int, 16)
        self.even.long = zPE.h2i(res[ :8])
        self.odd.long  = zPE.h2i(res[8: ])
        return self

    def __div__(self, other):
        return self.__truediv__(other)
    def __truediv__(self, other):
        '''
        DR   R2,R3      =>      RegisterPair(R2,R2+1) / R3
        D    R2,addr    =>      RegisterPair(R2,R2+1) / value@addr
        '''
        if not isinstance(other, Register):
            other = Register(other) # try converting the argument to a register
        if other.sign() == 0:       # zero-division
            raise zPE.newFixedPointDivideException()

        dividend = zPE.h2i_sign(str(self.even)+str(self.odd))
        # res[0] : quotient, res[1] : reminder
        res = list(divmod(abs(dividend), abs(other.int)))
        if self.even.sign() == 1:
            # dividend is negative
            res[1] = (- res[1])
        if (self.even.int < 0) != (other.int < 0):
            # sign of operands differ
            res[0] = (- res[0])

        if not -0x80000000 <= res[0] < 0x80000000: # quotient too large
            raise zPE.newFixedPointDivideException()
        self.even.int = res[1]
        self.odd.int  = res[0]
        return self


    def __lshift__(self, other):
        '''
        SLDL  R2,addr   =>      RegisterPair(R2,R2+1) << addr
        '''
        res = ((self.even.long << 32) + self.odd.long) << (other & 0b111111)
        self.even.long = res >> 32
        self.odd.long  = res
        return self

    def __rshift__(self, other):
        '''
        SRDL  R2,addr   =>      RegisterPair(R2,R2+1) >> addr
        '''
        res = ((self.even.long << 32) + self.odd.long) >> (other & 0b111111)
        self.even.long = res >> 32
        self.odd.long  = res
        return self

    def lshft(self, other):
        '''
        SLDA  R2,addr   =>      RegisterPair(R2,R2+1).lshft(addr)
        '''
        res = ((self.even.long << 32) + self.odd.long) << (other & 0b111111)
        self.even.long &= 0x80000000 # only preserve sign bit
        self.even.long += ((res >> 32) & 0x7FFFFFFF) # add the rest 31 bits
        self.odd.long  =  res

        res_test  = res >> 64                       # bits shifted out
        test_mask = (0b1 << (other & 0b111111)) - 1 # num-of-bit-shifted 1s
        if 0 < res_test < test_mask: # overflow occured
            SPR['PSW'].CC = 3
        else:
            self.even.test()    # sign bit is in even register
        return self

    def rshft(self, other):
        '''
        SRDA  R2,addr   =>      RegisterPair(R2,R2+1).rshft(addr)
        '''
        res = zPE.h2i_sign(str(self.even)+str(self.odd)) >> (other & 0b111111)
        self.even.long = res >> 32
        self.odd.long  = res
        self.even.test()        # sign bit is in even register
        return self
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
        self.PSW_key = PSW_key  # Storage (virtual memory) Reference access key
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

    def dump_hex(self, word = 0):
        bin_dump = self.dump_bin()
        if word:
            return zPE.b2x(bin_dump[word - 1])
        else:
            return [ zPE.b2x(bin_str) for bin_str in bin_dump ]

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

SPR = {                         # special purpose registers
    'PSW' : PSW(PSW_MODE['BC']),
    }

SPR['PSW'].Channel_masks = 127  # turn on all internal channels
SPR['PSW'].E = 1                # also turn on external channel
SPR['PSW'].P = 1                # problem (user) state
SPR['PSW'].PSW_key = 1          # 1st kernel-mode key
