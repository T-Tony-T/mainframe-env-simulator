# this defines the basic assembler instruction set

import zPE

import os, sys
import re


### Valid Operation Code

## basic instruction format type
class R(object):
    def __init__(self, val = None):
        if val == None:
            self.__val = None
        else:
            self.set(val)

    def __len__(self):
        return 1                # number of half-bytes / hex-digits

    def get(self):
        return self.__val
    def prnt(self):
        return hex(self.__val)[-1].upper()
    def set(self, val):
        if val < 0 or val > 15:
            raise ValueError
        self.__val = val

class X(object):
    def __init__(self, dsplc = None, indx = None, base = None):
        if dsplc == None:
            self.__dsplc = None
            self.__indx = None
            self.__base = None
        else:
            self.set(dsplc, indx, base)

    def __len__(self):
        return 5

    def get(self):
        return (
            self.__indx,
            self.__base,
            self.__dsplc
            )
    def prnt(self):
        return '{0}{1}{2:0>3}'.format(
            hex(self.__indx)[-1].upper(),
            hex(self.__base)[-1].upper(),
            hex(self.__dsplc)[2:].upper()
            )
    def set(self, dsplc, indx, base):
        if dsplc < 0 or dsplc > 4095:
            raise ValueError
        if indx < 0 or indx > 15:
            raise ValueError
        if base < 0 or base > 15:
            raise ValueError
        self.__indx = indx
        self.__base = base
        self.__dsplc = dsplc


## pseudo-instruction
pseudo = { }    # need to be filled by other modules (e.g. ASSIST)

## extended mnemonic
ext_mnem = {
    'B'    : ('47F', X()),
    'BR'   : ('07F', R()),
    }

## op-code look-up table
TYPE_OP = {     # M=modified, B=branch, U=USING, D=DROP, N=index
    #       AP    DP    ED    EDMK  MP    PACK  SP    SRP   UNPK  ZAP
    'M' : ( 'FA', 'FD', 'DE', 'DF', 'FC', 'F2', 'FB', 'F0', 'F3', 'F8',
          # MVC   MVI   TR    TRT
            'D2', '92', 'DC', 'DD',
          # ST    STC   STCM  STH   STM   
            '50', '42', 'BE', '40', '90' ),

    #       BAL   BALR  BAS   BASR  BC    BCR   BCT   BCTR  BXH   BXLE
    'B' : ( '45', '05', '4D', '0D', '47', '07', '46', '06', '86', '87' ),
    }
op_code = {
    'BC'   : ('47', R(), X()),
    'BCR'  : ('07', R(), R()),
    'L'    : ('58', R(), X()),
    'LA'   : ('41', R(), X()),
    'LR'   : ('18', R(), R()),
    'SR'   : ('1B', R(), R()),
    'ST'   : ('50', R(), X()),
    }


### Valid Constant Type

## constant type
# byte-based types
class C_(object):
    def __init__(self, ch_str, length = 0):
        self.set(ch_str, length)

    def __len__(self):
        return len(self.__vals)

    def get(self):
        return self.tr(self.__vals)
    def value(self):
        return None             # should not be evaluated
    def set(self, ch_str, length = 0):
        ch_len = len(ch_str)
        if not length:
            length = ch_len
        self.__vals = [ord(' '.encode('EBCDIC-CP-US'))] * length
                                # initialize to all spaces
        for indx in range(0, min(ch_len, length), 1):
            self.__vals[indx] = ord(ch_str[indx].encode('EBCDIC-CP-US'))
    def dump(self):
        return self.__vals
    def fill__(self, vals):     # no error checking
        self.__vals = vals
    @staticmethod
    def tr(vals):
        ch_str = ''
        for val in vals:
            ch_str += chr(val).decode('EBCDIC-CP-US')
        return ch_str

# Exception:
#   ValueError:  if the string contains invalid hex digit
class X_(object):
    def __init__(self, hex_str, length = 0):
        self.set(hex_str, length)

    def __len__(self):
        return len(self.__vals)

    def get(self):
        return self.tr(self.__vals)
    def value(self):
        return int(self.get(), 16)
    def set(self, hex_str, length = 0):
        hex_len = len(hex_str)
        # align to byte
        hex_len += hex_len % 2
        hex_str = '{0:0>{1}}'.format(hex_str, hex_len)
        if not length:
            length = hex_len
        else:
            length *= 2
        self.__vals = [0] * (length / 2)
                                # initialize to all zeros
        for indx in range(0, min(hex_len, length), 2):
            end = hex_len - indx
            self.__vals[- indx / 2 - 1] = int(hex_str[end - 2 : end], 16)
    def dump(self):
        return self.__vals
    def fill__(self, vals):     # no error checking
        self.__vals = vals
    @staticmethod
    def tr(vals):
        hex_str = ''
        for val in vals:
            hex_str += '{0:0>2}'.format(hex(val)[2:].upper())
        return hex_str

# Exception:
#   ValueError:  if the string contains anything other than '0' and '1'
class B_(object):
    def __init__(self, bin_str, length = 0):
        self.set(bin_str, length)

    def __len__(self):
        return len(self.__vals)

    def get(self):
        return self.tr(self.__vals)
    def value(self):
        return int(self.get(), 2)
    def set(self, bin_str, length = 0):
        bin_len = len(bin_str)
        # align to byte
        bin_len += 8 - bin_len % 8
        bin_str = '{0:0>{1}}'.format(bin_str, bin_len)
        if not length:
            length = bin_len
        else:
            length *= 8
        self.__vals = [0] * (length / 8)
                                # initialize to all zeros
        for indx in range(0, min(bin_len, length), 8):
            end = bin_len - indx
            self.__vals[- indx / 8 - 1] = int(bin_str[end - 8 : end], 2)
    def dump(self):
        return self.__vals
    def fill__(self, vals):     # no error checking
        self.__vals = vals
    @staticmethod
    def tr(vals):
        bin_str = ''
        for val in vals:
            bin_str += '{0:0>8}'.format(bin(val)[2:].upper())
        return bin_str

# Exception:
#   SyntaxError: if sign is not invalid
#   TypeError:   if the value is not packed
#   ValueError:  if the range exceeds the length;
#                if the string contains invalid digit (except pack())
class P_(object):
    def __init__(self, ch_str, length = 0):
        self.set(ch_str, length)

    def __len__(self):
        return len(self.__vals)

    def get(self, sign = '-'):
        return self.tr(self.__vals, sign)
    def value(self):
        ch_str = self.tr(self.__vals, '+')
        return int(ch_str[-1] + ch_str[:-1])
    def set(self, ch_str, length = 0):
        # check sign
        sign_digit = 'C'        # assume positive
        if ch_str[0] == '-':
            ch_str = ch_str[1:]
            sign_digit = 'D'    # change to negative
        elif ch_str[0] == '+':
            ch_str = ch_str[1:]
        int(ch_str)             # check format
        if length and length * 2 - 1 < len(ch_str):
            raise ValueError    # check length
        self.fill__(X_(ch_str + sign_digit).dump())
    def pack(self, ch_str, length = 0):
        if length and length * 2 - 1 < len(ch_str):
            raise ValueError    # check length
        hex_str = ''
        for ch in ch_str:
            hex_str += hex(
                ord(ch.encode('EBCDIC-CP-US'))
                )[-1].upper()   # for each char, get the low digit
        hex_str += '{0:0>2}'.format(
            hex(ord(ch_str[-1].encode('EBCDIC-CP-US')))[2:]
            )[0].upper()        # for the last char, add the high digit
        self.fill__(X_(hex_str).dump())
    def dump(self):
        return self.__vals
    def fill__(self, vals):     # no error checking
        self.__vals = vals
    @staticmethod
    def tr(vals, sign = '-'):
        ch_str = ''
        for val in vals[:-1]:
            hex_val = '{0:0>2}'.format(hex(val)[2:].upper())
            ch_str += chr(int('F' + hex_val[0], 16)).decode('EBCDIC-CP-US')
            ch_str += chr(int('F' + hex_val[1], 16)).decode('EBCDIC-CP-US')
        hex_val = '{0:0>2}'.format(hex(vals[-1])[2:].upper())
        ch_str += chr(int('F' + hex_val[0], 16)).decode('EBCDIC-CP-US')
        int(ch_str)             # check format
        if hex_val[1] in 'FACE':
            if sign == '+':
                ch_str += '+'
            elif sign == '-':
                ch_str += ' '
            elif sign in [ 'DB', 'CR' ]:
                ch_str += '  '
            else:
                raise SyntaxError
        elif hex_val[1] in 'BD':
            if sign in [ '+', '-' ]:
                ch_str += '-'
            elif sign in [ 'DB', 'CR' ]:
                ch_str += sign
            else:
                raise SyntaxError
        else:
            raise ValueError
        return ch_str


# Exception:
#   SyntaxError: if sign is not invalid
#   TypeError:   if the value is not zoned
#   ValueError:  if the string contains invalid digit
class Z_(object):
    def __init__(self, ch_str, length = 0):
        self.set(ch_str, length)

    def __len__(self):
        return len(self.__vals)

    def get(self, sign = '-'):
        return self.tr(self.__vals, sign)
    def value(self):
        ch_str = self.tr(self.__vals, '+')
        return int(ch_str[-1] + ch_str[:-1])
    def set(self, ch_str, length = 0):
        # check sign
        sign_digit = 'C'        # assume positive
        if ch_str[0] == '-':
            ch_str = ch_str[1:]
            sign_digit = 'D'    # change to negative
        elif ch_str[0] == '+':
            ch_str = ch_str[1:]
        int(ch_str)             # check format
        # check length
        ch_len = len(ch_str)
        if not length:
            length = ch_len
        self.__vals = [ord('0'.encode('EBCDIC-CP-US'))] * length
                                # initialize to all zeros
        for indx in range(0, min(ch_len, length), 1):
            self.__vals[length - indx - 1] = ord(
                ch_str[ch_len - indx - 1].encode('EBCDIC-CP-US')
                )
        # set sign for the last digit
        self.__vals[-1] = int(sign_digit + hex(self.__vals[-1])[-1], 16)
    def dump(self):
        return self.__vals
    def fill__(self, vals):     # no error checking
        self.__vals = vals
    @staticmethod
    def tr(vals, sign = '-'):
        ch_str = ''
        for val in vals[:-1]:
            ch_str += chr(val).decode('EBCDIC-CP-US')
        hex_val = hex(vals[-1])[2:].upper()
        ch_str += hex_val[1]
        int(ch_str)             # check format
        if hex_val[0] in 'FACE':
            if sign == '+':
                ch_str += '+'
            elif sign == '-':
                ch_str += ' '
            elif sign in [ 'DB', 'CR' ]:
                ch_str += '  '
            else:
                raise SyntaxError
        elif hex_val[0] in 'BD':
            if sign in [ '+', '-' ]:
                ch_str += '-'
            elif sign in [ 'DB', 'CR' ]:
                ch_str += sign
            else:
                raise SyntaxError
        else:
            raise ValueError
        return ch_str



# non-byte-based types

# Exception:
#   ValueError: if length (required or actual) greater than 4
class F_(object):
    def __init__(self, int_str, length = 0):
        self.set(int_str, length)

    def __len__(self):
        return 4                # must be 4

    def get(self):
        return self.tr(self.dump())
    def value(self):
        return self.__val
    def set(self, int_str, length = 0):
        if length > 4:
            raise ValueError
        int_val = int(int_str, 10)
        if int_val < int('-80000000', 16) or int_val > int('7FFFFFFF', 16):
            raise ValueError
        self.__val = int_val
    def dump(self):
        if self.__val >= 0:
            hex_str = '{0:0>8}'.format(hex(self.__val)[2:])
        else:
            hex_str = '{0:0>8}'.format(hex(
                    int('100000000', 16) + self.__val # 2's complement
                    )[2:])
        return (
            int(hex_str[0:2], 16),
            int(hex_str[2:4], 16),
            int(hex_str[4:6], 16),
            int(hex_str[6:8], 16),
            )
    def fill__(self, vals):      # no error checking
        self.__val = int(self.tr(vals))
    @staticmethod
    def tr(vals):
        int_val = vals[0]
        for indx in range(1, len(vals)):
            int_val *= 256
            int_val += vals[indx]
        int_val %= int('FFFFFFFF', 16)
        if int_val > int('7FFFFFFF', 16):
            int_str = '-{0}'.format(
                int('100000000', 16) - int_val # 2's complement
                )
        else:
            int_str = str(int_val)
        return int_str

# Exception:
#   ValueError: if length (required or actual) greater than 2
class H_(object):
    def __init__(self, int_str, length = 0):
        self.set(int_str, length)

    def __len__(self):
        return 2                # must be 2

    def get(self):
        return self.tr(self.dump())
    def value(self):
        return self.__val
    def set(self, int_str, length = 0):
        if length > 2:
            raise ValueError
        int_val = int(int_str, 10)
        if int_val < int('-8000', 16) or int_val > int('7FFF', 16):
            raise ValueError
        self.__val = int_val
    def dump(self):
        if self.__val >= 0:
            hex_str = '{0:0>4}'.format(hex(self.__val)[2:])
        else:
            hex_str = '{0:0>4}'.format(hex(
                    int('10000', 16) + self.__val # 2's complement
                    )[2:])
        return (
            int(hex_str[0:2], 16),
            int(hex_str[2:4], 16),
            )
    def fill__(self, vals):      # no error checking
        self.__val = int(self.tr(vals))
    @staticmethod
    def tr(vals):
        int_val = vals[0]
        for indx in range(1, len(vals)):
            int_val *= 256
            int_val += vals[indx]
        int_val %= int('FFFF', 16)
        if int_val > int('7FFF', 16):
            int_str = '-{0}'.format(
                int('10000', 16) - int_val # 2's complement
                )
        else:
            int_str = str(int_val)
        return int_str

# Exception:
#   ValueError: if length (required or actual) greater than 4
class A_(object):
    def __init__(self, int_str, length = 0):
        self.set(int_str, length)

    def __len__(self):
        return 4                # must be 4

    def get(self):
        return self.tr(self.dump())
    def value(self):
        return self.__val
    def set(self, int_str, length = 0):
        if length > 4:
            raise ValueError
        int_val = int(int_str, 10)
        if int_val < 0 or int_val > int('FFFFFFFF', 16):
            raise ValueError
        self.__val = int_val
    def dump(self):
        hex_str = '{0:0>8}'.format(hex(self.__val)[2:])
        return (
            int(hex_str[0:2], 16),
            int(hex_str[2:4], 16),
            int(hex_str[4:6], 16),
            int(hex_str[6:8], 16),
            )
    def fill__(self, vals):      # no error checking
        self.__val = int(self.tr(vals)[2:], 16)
    @staticmethod
    def tr(vals):
        int_val = vals[0]
        for indx in range(1, len(vals)):
            int_val *= 256
            int_val += vals[indx]
        return '0x{0:0>8}'.format(
            hex(int_val % int('FFFFFFFF', 16))[2:-1].upper()
            )


## simple type
BOUNDARY = [
    [ 'C', 'X', 'B', 'P', 'Z', ], # no boundary
    [ 'H', ],                     # half-word boundary
    [ 'F', 'A', 'V', ],           # full-word boundary
    [  ],                         # double-word boundary
    ]

const_s = {
    'C' : C_('0'),
    'X' : X_('0'),
    'B' : B_('0'),
    'F' : F_('0'),
    'H' : H_('0'),
    'P' : P_('0'),
    'Z' : Z_('0'),
    }

## address type
const_a = {
    'A' : A_('0'),
    'V' : A_('0'),
    }


### Interface Functions

def align_at(st_ch):
    for indx in range(len(BOUNDARY)):
        if st_ch in BOUNDARY[indx]:
            return 2 ** indx
    return 0

# rv: ( 'op_code', fmt_tp_1, ... )
def get_op(instruction):
    if instruction in pseudo:
        return pseudo[instruction]
    elif instruction in ext_mnem:
        return ext_mnem[instruction]
    elif instruction in op_code:
        return op_code[instruction]
    else:
        return None


def len_op(op):
    code = int(op[:2], 16)
    if ( code <= int('98', 16) or
         ( code >= int('AC', 16) and code <= int('B1', 16) ) or
         ( code >= int('B6', 16) and code <= int('DF', 16) ) or
         code >= int('E8', 16)
         ):
        return 2
    else:
        return 4


def len_st(st_ch):
    if st_ch in const_s:
        return len(const_s[st_ch])
    elif st_ch in const_a:
        return len(const_a[st_ch])
    else:
        return None


# rv: ( const_type, multiplier, ch, length, init_val )
# exception:
#   SyntaxError: any syntax error in parsing the arguments
def parse_st(st_arg):
    # split into ( [mul]ch[Llen], val )
    L = re.split('\(', st_arg)  # split according to '\('
    sz = len(L)
    if sz == 2 and L[1][-1] == ')':
        # A(label) ==> [ 'A', 'label)' ]
        st_ch = L[0]
        st_val = re.split(',', L[1][:-1])
        val_tp = 'a'            # address type constant
    elif sz == 1:
        # AL3 ==> [ 'AL3' ]  or  8F'1' ==> [ "8F'1'" ]
        L = re.split("'", st_arg) # re-split according to '\''
        sz = len(L)
        if sz == 3 and L[2] == '':
            # 8F'1' ==> [ '8F', '1', '' ]
            st_ch = L[0]
            st_val = L[1]
            val_tp = 's'        # simple constant
        elif sz == 1:           # DS
            # 8F ==> [ '8F' ]
            st_ch = L[0]
            st_val = None
        else:
            raise SyntaxError
    else:
        raise SyntaxError

    # split l[0] into [ multiplier, type, length ]
    L = re.split('([A-Z])L?', st_ch) # split according to '?L'
    match = len(re.findall('([A-Z])L', st_ch)) # match the postfix 'L'

    # parse multiplier
    if len(L) != 3:
        raise SyntaxError
    if L[0] == '':
        st_mul = 1
    else:
        st_mul = int(L[0])

    # check type
    const_tp = valid_st(L[1])
    if not const_tp:
        raise SyntaxError
    st_ch = L[1]
    if st_val != None and const_tp != val_tp:
        raise SyntaxError

    # parse length
    if match == 0:              # no '?L' found
        if L[2] == '':
            if st_val != None:
                tmp = eval('{0}_(\'{1}\')'.format(st_ch, st_val))
                st_len = len(tmp)
            else:
                st_len = len_st(st_ch)
        else:
            raise SyntaxError
    elif match == 1:            # one '?L' found
        if L[2] == '':
            raise SyntaxError
        else:
            st_len = int(L[2])
    else:                       # more than one '?L' found
        raise SyntaxError

    return (const_tp, st_mul, st_ch, st_len, st_val)


def type_op(op_code):
    if op_code[:2] in TYPE_OP['B']:
        return 'B'
    elif op_code[:2] in TYPE_OP['M']:
        return 'M'
    else:
        return ' '


def valid_op(instruction):
    if instruction in pseudo:
        return True
    elif instruction in ext_mnem:
        return True
    elif instruction in op_code:
        return True
    else:
        return False


def valid_st(st_arg_line):
    if st_arg_line[0] in const_a:
        return 'a'
    elif st_arg_line[0] in const_s:
        return 's'
    else:
        return None


# st_info: ( 's', 1, ch, length, init_val )
#   see parse_st(st_arg) for more details
# exception:
#   ValueError: if the storage type cannot be evaluated
#   others:     along the way of parsing storage
def value_st(st_info):
    st = eval('{0}_( \'{1}\', {2} )'.format(
            st_info[2], st_info[4], st_info[3]
            ))
    if st.value() == None:
        raise ValueError
    return st.value()
