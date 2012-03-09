# this defines the basic assembler instruction set

import zPE

import re


### Valid ASM Instruction
ASM_INSTRUCTION = set([
        'TITLE', 'EJECT', 'SPACE',
        'CSECT', 'DSECT',
        'USING', 'DROP',
        'END',
        'LTORG', 'ORG',
        'EQU', 'DC', 'DS',
        ])

def valid_ins(instruction):
    return (instruction in ASM_INSTRUCTION)


### Valid Operation Code

## basic instruction format type
class InstructionType(object):
    '''this is an abstract base class'''

    def __init__(self, ins_type, pos):
        self.type  = ins_type
        self.pos   = pos

        # default to no alignment
        # see al() and is_aligned() for more info
        self.align = 1

        # default to no access permission
        # see flag() / ro() / wo() / rw() / br() / ex() for more info
        self.for_read   = False # flag  ; able to retrieve value
        self.for_write  = False # flag M; able to set new value
        self.for_branch = False # flag B; able to jump to value
        self.for_exec   = False # flag X; able to exec at value
        # these flag affects the corresponding flag in the CR table
        # see flag() for more info

    def __len__(self):
        '''return number of half-bytes / hex-digits'''
        raise AssertionError('require overridden')

    def get(self):
        '''return the internal value'''
        raise AssertionError('require overridden')

    def prnt(self):
        '''
        return ( first_str, second_str ) where either one can be ''

        when connecting multiple InstructionTypes, 'first_str's are
        concatenated before 'second_str's
        '''
        raise AssertionError('require overridden')

    def value(self):
        '''return the logical value'''
        raise AssertionError('require overridden')

    def set(self, val):
        '''store the value'''
        raise AssertionError('require overridden')


    def al(self, alignment):
        '''
        invoke this like a modifier. e.g. r = X(2).al(fw)
        argument should be one of the follows:
          bw = byteword (character) alignment (no alignment)
          hw = align on halfword boundary
          fw = align on fullword boundary
          dw = align on doubleword boundary
        '''
        self.align = zPE.fmt_align_map[alignment]
        return self

    def is_aligned(self, loc = None):
        if loc == None:
            loc = self.value()
        return loc % self.align == 0


    def flag(self):
        '''
        available CR table flags are:
          M = modified  contents may be modified by action of instruction
          B = branch    used as operands of branch instructions
          U = USING     [ not handled here ]
          D = DROP      [ not handled here ]
          N = index     [ not handled currently ]
          X = EXecute   targets of execute (EX) instruction
        '''
        if self.for_exec:
            return 'X'
        if self.for_branch:
            return 'B'
        if self.for_write:
            return 'M'
        return ' '

    def ro(self):
        '''invoke this like a modifier. e.g. r = R(3).ro()'''
        self.for_read   = True
        self.for_write  = False
        self.for_branch = False
        self.for_exec   = False
        return self

    def wo(self):
        '''invoke this like a modifier. e.g. r = R(1).wo()'''
        self.for_read   = False
        self.for_write  = True
        self.for_branch = False
        self.for_exec   = False
        return self

    def rw(self):
        '''invoke this like a modifier. e.g. r = R(1).rw()'''
        self.for_read   = True
        self.for_write  = True
        self.for_branch = False
        self.for_exec   = False
        return self

    def br(self):
        '''invoke this like a modifier. e.g. r = R(2).br()'''
        self.for_read   = True
        self.for_write  = False
        self.for_branch = True
        self.for_exec   = False
        return self

    def ex(self):
        '''invoke this like a modifier. e.g. r = X(2).ex()'''
        self.for_read   = True
        self.for_write  = False
        self.for_branch = False
        self.for_exec   = True
        return self

class OpConst(object):
    '''this is for extended mnemonics and other pre-filled InstructionType()'''
    def __init__(self, ins_type, *val_list):
        self.ins_type = ins_type
        self.type = self.ins_type.type # pull over the type info
        self.pos  = self.ins_type.pos  # pull over the position info

        self.ins_type.set(*val_list)     # initialize the constant
        self.valid = self.ins_type.valid # pull over the valid indicator

    def __len__(self):
        return len(self.ins_type)

    def get(self):
        return self.ins_type.get()

    def prnt(self):
        return self.ins_type.prnt()

    def value(self):
        return self.ins_type.value()

    def is_aligned(self, loc = None):
        return self.ins_type.is_aligned(loc)

    def flag(self):
        return self.ins_type.flag()


# int_4 => ( 'r', '' )
class R(InstructionType):
    def __init__(self, arg_pos, val = None):
        super(R, self).__init__('R', arg_pos)

        if val == None:
            self.valid = False
            self.__val = None
        else:
            self.set(val)

    def __len__(self):
        return 1                # number of half-bytes / hex-digits

    def get(self):
        if self.valid:
            return self.__val
        else:
            raise ValueError('value is invalid (non-initialized).')

    def prnt(self):
        if self.valid:
            rv = hex(self.__val)[-1].upper()
        else:
            rv = '-'
        return ( rv, '', )

    def value(self):
        if self.valid:
            rv = self.__val
        else:
            rv = None
        return rv

    def set(self, val):
        if not 0x0 <= val <= 0xF:
            raise ValueError('register number must be between 0 and 15')
        self.__val = val
        self.valid = True

# char => ( 'ii', '' )
class I(InstructionType):
    def __init__(self, arg_pos, val = None):
        super(I, self).__init__('I', arg_pos)

        if val == None:
            self.valid = False
            self.__val = None
        else:
            self.set(val)

    def __len__(self):
        return 2                # number of half-bytes / hex-digits

    def get(self):
        if self.valid:
            return self.__val
        else:
            raise ValueError('value is invalid (non-initialized).')

    def prnt(self):
        if self.valid:
            rv = '{0:0>2}'.format(hex(self.__val)[2:].upper())
        else:
            rv = '--'
        return ( rv, '', )

    def value(self):
        if self.valid:
            rv = self.__val
        else:
            rv = None
        return rv

    def set(self, val):
        if not 0x00 <= val <= 0xFF:
            raise ValueError('immediate byte must be 8 bit long')
        self.__val = val
        self.valid = True

# int_12(int_4) => ( '', 'bddd' )
class S(InstructionType):
    def __init__(self, arg_pos, dsplc = None, base = 0):
        super(S, self).__init__('S', arg_pos)

        if dsplc == None:
            self.valid = False
            self.__dsplc = None
            self.__base = None
        else:
            self.set(dsplc, base)

    def __len__(self):
        return 4

    def get(self):
        if self.valid:
            return (
                self.__base,
                self.__dsplc
                )
        else:
            raise ValueError('value is invalid (non-initialized).')

    def prnt(self):
        if self.valid:
            rv = '{0}{1:0>3}'.format(
                hex(self.__base)[-1].upper(),
                hex(self.__dsplc)[2:].upper()
                )
        else:
            rv = '----'
        return ( '', rv, )

    def value(self):
        if self.valid:
            rv = self.__dsplc
        else:
            rv = None
        return rv

    def set(self, dsplc, base = 0):
        if not 0x000 <= dsplc <= 0xFFF:
            raise ValueError('displacement must be between 0 and 4095')
        if not 0x0 <= base <= 0xF:
            raise ValueError('register number must be between 0 and 15')
        self.__base = base
        self.__dsplc = dsplc
        self.valid = True

# int_12(int_4, int_4) => ( 'x', 'bddd' )
class X(S):
    def __init__(self, arg_pos, dsplc = None, indx = 0, base = 0):
        super(X, self).__init__(arg_pos, dsplc, base)
        self.type = 'X'         # override type

        if dsplc == None:
            self.__indx = None
        else:
            self.set(dsplc, indx, base)

    def __len__(self):
        return 5

    def get(self):
        if self.valid:
            return ( self.__indx, ) + super(X, self).get()
        else:
            raise ValueError('value is invalid (non-initialized).')

    def prnt(self):
        if self.valid:
            rv = hex(self.__indx)[-1].upper()
        else:
            rv = '-'
        return ( rv, super(X, self).prnt()[1], )

    def value(self):
        return super(X, self).value()

    def set(self, dsplc, indx = 0, base = 0):
        if not 0x0 <= indx <= 0xF:
            raise ValueError('register number must be between 0 and 15')
        self.__indx = indx
        super(X, self).set(dsplc, base)

# int_12(int_4, int_4) => (  'l', 'bddd' )
# int_12(int_8, int_4) => ( 'll', 'bddd' )
class L(S):
    def __init__(self, arg_pos, lenfmt = 1, dsplc = None, length = 0, base = 0):
        super(L, self).__init__(arg_pos, dsplc, base)
        self.type = 'L'         # override type
        if lenfmt == 1:
            self.lenfmt = 1     # 1 : L + bddd
        else:
            self.lenfmt = 2     # 2 : LL + bddd

        if dsplc == None:
            self.__length = None
        else:
            self.set(length, dsplc, base)

    def __len__(self):
        return 4 + self.lenfmt

    def get(self):
        if self.valid:
            return ( self.__length, ) + super(L, self).get()
        else:
            raise ValueError('value is invalid (non-initialized).')

    def prnt(self):
        if self.valid:
            if self.__length:   # non-zero
                encoded_len = self.__length - 1 # length code = length - 1
            else:               # zero
                encoded_len = self.__length     # length code = 0
            rv = '{0:0>{1}}'.format(hex(encoded_len)[2:].upper(), self.lenfmt)
        else:
            rv = '{0:->{1}}'.format('', self.lenfmt)
        return ( rv, super(L, self).prnt()[1], )

    def value(self):
        return super(L, self).value()

    def set(self, length, dsplc, base = 0):
        if not 0x0 <= length <= self.max_len_length():
            raise ValueError('length must be between 1 and ' + str(max_len))
        self.__length = length
        super(L, self).set(dsplc, base)

    def max_len_length(self):
        return 0x1 << ( 4 * self.lenfmt )


## Op-Code Look-Up Table
# Pseudo-Instruction
pseudo = { }        # should only be filled by other modules (e.g. ASSIST)

# Extended Mnemonic
ext_mnem = {
    'B'    : lambda: ('47', OpConst(R(1).ro(), 0xF), X(2).br().al('hw')),
    'BR'   : lambda: ('07', OpConst(R(1).ro(), 0xF), R(2).br()),
    'NOP'  : lambda: ('47', OpConst(R(1).ro(), 0x0), X(2).br().al('hw')),
    'NOPR' : lambda: ('07', OpConst(R(1).ro(), 0x0), R(2).br()),

    'BH'   : lambda: ('47', OpConst(R(1).ro(), 0x2), X(2).br().al('hw')),
    'BHR'  : lambda: ('07', OpConst(R(1).ro(), 0x2), R(2).br()),
    'BL'   : lambda: ('47', OpConst(R(1).ro(), 0x4), X(2).br().al('hw')),
    'BLR'  : lambda: ('07', OpConst(R(1).ro(), 0x4), R(2).br()),
    'BE'   : lambda: ('47', OpConst(R(1).ro(), 0x8), X(2).br().al('hw')),
    'BER'  : lambda: ('07', OpConst(R(1).ro(), 0x8), R(2).br()),
    'BNH'  : lambda: ('47', OpConst(R(1).ro(), 0xD), X(2).br().al('hw')),
    'BNHR' : lambda: ('07', OpConst(R(1).ro(), 0xD), R(2).br()),
    'BNL'  : lambda: ('47', OpConst(R(1).ro(), 0xB), X(2).br().al('hw')),
    'BNLR' : lambda: ('07', OpConst(R(1).ro(), 0xB), R(2).br()),
    'BNE'  : lambda: ('47', OpConst(R(1).ro(), 0x7), X(2).br().al('hw')),
    'BNER' : lambda: ('07', OpConst(R(1).ro(), 0x7), R(2).br()),

    'BP'   : lambda: ('47', OpConst(R(1).ro(), 0x2), X(2).br().al('hw')),
    'BPR'  : lambda: ('07', OpConst(R(1).ro(), 0x2), R(2).br()),
    'BM'   : lambda: ('47', OpConst(R(1).ro(), 0x4), X(2).br().al('hw')),
    'BMR'  : lambda: ('07', OpConst(R(1).ro(), 0x4), R(2).br()),
    'BZ'   : lambda: ('47', OpConst(R(1).ro(), 0x8), X(2).br().al('hw')),
    'BZR'  : lambda: ('07', OpConst(R(1).ro(), 0x8), R(2).br()),
    'BO'   : lambda: ('47', OpConst(R(1).ro(), 0x1), X(2).br().al('hw')),
    'BOR'  : lambda: ('07', OpConst(R(1).ro(), 0x1), R(2).br()),
    'BNP'  : lambda: ('47', OpConst(R(1).ro(), 0xD), X(2).br().al('hw')),
    'BNPR' : lambda: ('07', OpConst(R(1).ro(), 0xD), R(2).br()),
    'BNM'  : lambda: ('47', OpConst(R(1).ro(), 0xB), X(2).br().al('hw')),
    'BNMR' : lambda: ('07', OpConst(R(1).ro(), 0xB), R(2).br()),
    'BNZ'  : lambda: ('47', OpConst(R(1).ro(), 0x7), X(2).br().al('hw')),
    'BNZR' : lambda: ('07', OpConst(R(1).ro(), 0x7), R(2).br()),
    'BNO'  : lambda: ('47', OpConst(R(1).ro(), 0xE), X(2).br().al('hw')),
    'BNOR' : lambda: ('07', OpConst(R(1).ro(), 0xE), R(2).br()),
    }

# Basic Instruction
op_code = {
    'A'    : lambda: ('5A', R(1).rw(), X(2).ro().al('fw')),
    'AL'   : lambda: ('5E', R(1).rw(), X(2).ro().al('fw')),
    'ALR'  : lambda: ('1E', R(1).rw(), R(2).ro()),
    'AP'   : lambda: ('FA', L(1,1).rw(),L(2,1).ro()),
    'AR'   : lambda: ('1A', R(1).rw(), R(2).ro()),

    'BAL'  : lambda: ('45', R(1).wo(), X(2).br().al('hw')),
    'BALR' : lambda: ('05', R(1).wo(), R(2).br()),
    'BC'   : lambda: ('47', R(1).ro(), X(2).br().al('hw')),
    'BCR'  : lambda: ('07', R(1).ro(), R(2).br()),
    'BCT'  : lambda: ('46', R(1).rw(), X(2).br().al('hw')),
    'BCTR' : lambda: ('06', R(1).rw(), R(2).br()),
    'BXH'  : lambda: ('86', R(1).rw(), R(3).ro(), S(2).br().al('hw')),
    'BXLE' : lambda: ('87', R(1).rw(), R(3).ro(), S(2).br().al('hw')),

    'C'    : lambda: ('59', R(1).ro(), X(2).ro().al('fw')),
    'CL'   : lambda: ('55', R(1).ro(), X(2).ro().al('fw')),
    'CLC'  : lambda: ('D5', L(1,2).ro(), S(2).ro()), # LL + bddd format
    'CLI'  : lambda: ('95', S(1).ro(), I(2).ro()),
    'CLR'  : lambda: ('15', R(1).ro(), R(2).ro()),
    'CP'   : lambda: ('F9', L(1,1).ro(),L(2,1).ro()),
    'CR'   : lambda: ('19', R(1).ro(), R(2).ro()),

    'D'    : lambda: ('5D', R(1).rw().al('hw'), X(2).ro().al('fw')),
    'DP'   : lambda: ('FD', L(1,1).rw(),L(2,1).ro()),
    'DR'   : lambda: ('1D', R(1).rw().al('hw'), R(2).ro()),

    'EX'   : lambda: ('44', R(1).ro(), X(2).ex()),

    'IC'   : lambda: ('43', R(1).rw(), X(2).ro()),
    'ICM'  : lambda: ('BF', R(1).rw(), R(3).ro(), S(2).ro()),

    'L'    : lambda: ('58', R(1).wo(), X(2).ro().al('fw')),
    'LA'   : lambda: ('41', R(1).wo(), X(2).ro()),
    'LCR'  : lambda: ('13', R(1).rw(), R(2).ro()),
    'LM'   : lambda: ('98', R(1).wo(), R(3).wo(), S(2).ro().al('fw')),
    'LNR'  : lambda: ('11', R(1).rw(), R(2).ro()),
    'LPR'  : lambda: ('10', R(1).rw(), R(2).ro()),
    'LR'   : lambda: ('18', R(1).wo(), R(2).ro()),
    'LTR'  : lambda: ('12', R(1).rw(), R(2).ro()),

    'M'    : lambda: ('5C', R(1).rw().al('hw'), X(2).ro().al('fw')),
    'MP'   : lambda: ('FC', L(1,1).rw(),L(2,1).ro()),
    'MR'   : lambda: ('1C', R(1).rw().al('hw'), R(2).ro()),

    'MVC'  : lambda: ('D2', L(1,2).rw(), S(2).ro()), # LL + bddd format
    'MVI'  : lambda: ('92', S(1).rw(), I(2).ro()),

    'N'    : lambda: ('54', R(1).rw(), X(2).ro().al('fw')),
    'NR'   : lambda: ('14', R(1).rw(), R(2).ro()),

    'O'    : lambda: ('56', R(1).rw(), X(2).ro().al('fw')),
    'OR'   : lambda: ('16', R(1).rw(), R(2).ro()),

    'PACK' : lambda: ('F2', L(1,1).rw(),L(2,1).ro()),

    'S'    : lambda: ('5B', R(1).rw(), X(2).ro().al('fw')),
    'SL'   : lambda: ('5F', R(1).rw(), X(2).ro().al('fw')),
    'SLR'  : lambda: ('1F', R(1).rw(), R(2).ro()),
    'SP'   : lambda: ('FB', L(1,1).rw(),L(2,1).ro()),
    'SR'   : lambda: ('1B', R(1).rw(), R(2).ro()),

    'ST'   : lambda: ('50', R(1).ro(), X(2).wo().al('fw')),
    'STC'  : lambda: ('42', R(1).ro(), X(2).rw()),
    'STCM' : lambda: ('BE', R(1).ro(), R(3).ro(), S(2).rw()),
    'STM'  : lambda: ('90', R(1).ro(), R(3).ro(), S(2).wo().al('fw')),

    'UNPK' : lambda: ('F3', L(1,1).rw(),L(2,1).ro()),

    'X'    : lambda: ('57', R(1).rw(), X(2).ro().al('fw')),
    'XR'   : lambda: ('17', R(1).rw(), R(2).ro()),

    'ZAP'  : lambda: ('F8', L(1,1).rw(),L(2,1).ro()),
    }


## Interface Functions

# rv: ( 'op_mnem', fmt_tp_1, ... )
def get_op(instruction):
    if instruction in op_code:
        return op_code[instruction]()
    elif instruction in ext_mnem:
        return ext_mnem[instruction]()
    else:
        return None

def get_op_from(pseudo_ins, argc):
    if pseudo_ins in pseudo:
        try:
            op = pseudo[pseudo_ins](argc) # fetch the indicated format
        except:
            # number of arguments is invalid
            if zPE.debug_mode():
                raise
            op = pseudo[pseudo_ins](0)    # fetch the default format
        return op
    else:
        return None


def len_op(op_code):
    code = int(op_code[0][:2], 16)
    if ( code <= 0x98 or
         0xAC <= code <= 0xB1 or
         0xB6 <= code <= 0xDF or
         0xE8 <= code
         ):
        return 2
    else:
        return 4

def op_arg_indx(op_code):
    rv = []
    indx = 1                    # op_code[0] is the OP code itself
    while indx < len(op_code):
        if isinstance(op_code[indx], InstructionType):
            rv.append(indx)
        indx += 1
    return rv

def prnt_op(op_code):
    # print OP code itself
    code = op_code[0]

    # print arguments - first pass
    for indx in range(1, len(op_code)):
        code += op_code[indx].prnt()[0]

    # print arguments - second pass
    for indx in range(1, len(op_code)):
        code += op_code[indx].prnt()[1]

    return code


def valid_op(instruction):
    if instruction in op_code:
        return True
    elif instruction in ext_mnem:
        return True
    else:
        return valid_pseudo(instruction)

def valid_pseudo(instruction):
    return (instruction in pseudo)

def is_branching(instruction):
    if not valid_op(instruction):
        return None
    if valid_pseudo(instruction):
        op_code = get_op_from(instruction, 0)
    else:
        op_code = get_op(instruction)
    for i in op_arg_indx(op_code):
        if op_code[i].for_branch:
            return True
    return False
### end of Operation Code Definition


### Valid Constant Type

## constant type
# byte-based types
class C_(object):
    def __init__(self, ch_str, length = 0):
        self.set(ch_str, length)

    def __len__(self):
        return len(self.__vals)

    def get(self):
        return self.tr(self.dump())

    def value(self):
        return int(X_.tr(self.dump()), 16)

    def set(self, ch_str, length = 0):
        ch_len = len(ch_str)
        if not length:
            length = ch_len
        # calculate natual length; in unit of bin_digit
        self.natual_len = length * 8 # for char, natual length = 8 * len(str)
        # convert encoding
        self.__vals = [ord(' '.encode('EBCDIC-CP-US'))] * length
                                # initialize to all spaces
        for indx in range(0, min(ch_len, length), 1): # filling left to right
            self.__vals[indx] = ord(ch_str[indx].encode('EBCDIC-CP-US'))

    def dump(self):
        return (self.__vals, self.natual_len)

    def fill__(self, dump):     # no error checking
        self.__vals = dump[0]
        self.natual_len = dump[1]

    @staticmethod
    def tr(dump):
        ch_list = []
        for val in dump[0]:
            ch_list.append(chr(val).decode('EBCDIC-CP-US'))
        return ''.join(ch_list)

# Exception:
#   ValueError:  if the string contains invalid hex digit
class X_(object):
    def __init__(self, hex_str, length = 0):
        self.set(hex_str, length)

    def __len__(self):
        return len(self.__vals)

    def get(self):
        return self.tr(self.dump())

    def value(self):
        return int(self.get(), 16)

    def set(self, hex_str, length = 0):
        hex_len = len(hex_str)
        # calculate natual length; in unit of bin_digit
        self.natual_len = length * 8
        if not self.natual_len: # for hex, natual length = 4 * len(str)
            self.natual_len = hex_len * 4
        # align to byte
        hex_len += hex_len % 2
        hex_str = '{0:0>{1}}'.format(hex_str, hex_len)
        if not length:
            length = hex_len
        else:
            length *= 2
        self.__vals = [0] * (length / 2)
                                # initialize to all zeros
        for indx in range(0, min(hex_len, length), 2): # filling right to left
            end = hex_len - indx
            self.__vals[- indx / 2 - 1] = int(hex_str[end - 2 : end], 16)

    def dump(self):
        return (self.__vals, self.natual_len)

    def fill__(self, dump):     # no error checking
        self.__vals = dump[0]
        self.natual_len = dump[1]

    @staticmethod
    def tr(dump):
        hex_list = []
        for val in dump[0]:
            hex_list.append('{0:0>2}'.format(hex(val)[2:].upper()))
        return ''.join(hex_list)

# Exception:
#   ValueError:  if the string contains anything other than '0' and '1'
class B_(object):
    def __init__(self, bin_str, length = 0):
        self.set(bin_str, length)

    def __len__(self):
        return len(self.__vals)

    def get(self):
        return self.tr(self.dump())

    def value(self):
        return int(self.get(), 2)

    def set(self, bin_str, length = 0):
        bin_len = len(bin_str)
        # calculate natual length; in unit of bin_digit
        self.natual_len = length * 8
        if not self.natual_len: # for bin, natual length = len(str)
            self.natual_len = bin_len
        # align to byte
        bin_len += (8 - bin_len % 8) % 8
        bin_str = '{0:0>{1}}'.format(bin_str, bin_len)
        if not length:
            length = bin_len
        else:
            length *= 8
        self.__vals = [0] * (length / 8)
                                # initialize to all zeros
        for indx in range(0, min(bin_len, length), 8): # filling right to left
            end = bin_len - indx
            self.__vals[- indx / 8 - 1] = int(bin_str[end - 8 : end], 2)

    def dump(self):
        return (self.__vals, self.natual_len)

    def fill__(self, dump):     # no error checking
        self.__vals = dump[0]
        self.natual_len = dump[1]

    @staticmethod
    def tr(dump):
        bin_list = []
        for val in dump[0]:
            bin_list.append('{0:0>8}'.format(bin(val)[2:].upper()))
        return ''.join(bin_list)

# Exception:
#   SyntaxError: if sign is not invalid
#   TypeError:   if the value is not packed
#   DataException: if the string contains invalid digit (except pack() & unpk())
class P_(object):
    def __init__(self, ch_str, length = 0):
        self.set(ch_str, length)

    def __len__(self):
        return len(self.__vals)

    def get(self, sign = '-'):
        return self.tr(self.dump(), sign)

    def value(self):
        return self.tr_val(self.dump())

    def set(self, ch_str, length = 0):
        # check sign
        sign_digit = 'C'        # assume positive
        if ch_str[0] == '-':
            ch_str = ch_str[1:]
            sign_digit = 'D'    # change to negative
        elif ch_str[0] == '+':
            ch_str = ch_str[1:]
        int(ch_str)             # check format
        self.fill__(X_(ch_str + sign_digit, length).dump())

    @staticmethod
    def pack(hex_str, length):
        hex_list = []
        # align to byte
        hex_len = len(hex_str)
        hex_len += hex_len % 2
        hex_str = '{0:0>{1}}'.format(hex_str, hex_len)
        for indx in range(0, hex_len, 2):
            hex_list.append(hex_str[indx+1]) # for each byte, get the low digit
        hex_list.append(hex_str[-2])         # for last byte, add the high digit
        return X_(''.join(hex_list), length).dump()[0]

    @staticmethod
    def unpk(hex_str, length):
        hex_list = []
        hex_str = '{0:0>{1}}'.format(hex_str, length + 1) # add leading 0s
        for indx in range(0, len(hex_str) - 2):
            # for each hex digit (except last byte), add 'F' in-front
            hex_list.append('F')
            hex_list.append(hex_str[indx])
        # for last byte, reverse hex digits
        hex_list.append(hex_str[-1])
        hex_list.append(hex_str[-2])
        return X_(''.join(hex_list), length).dump()[0]

    def dump(self):
        return (self.__vals, self.natual_len)

    def fill__(self, dump):     # no error checking
        self.__vals = dump[0]
        self.natual_len = dump[1]

    @staticmethod
    def tr(dump, sign = '-'):
        vals = dump[0]
        ch_list = []
        for val in vals[:-1]:
            hex_val = '{0:0>2}'.format(hex(val)[2:].upper())
            ch_list.append(chr(int('F'+ hex_val[0], 16)).decode('EBCDIC-CP-US'))
            ch_list.append(chr(int('F'+ hex_val[1], 16)).decode('EBCDIC-CP-US'))
        hex_val = '{0:0>2}'.format(hex(vals[-1])[2:].upper())
        ch_list.append(chr(int('F'+ hex_val[0], 16)).decode('EBCDIC-CP-US'))

        # check format
        ch_list = [ ''.join(ch_list) ]
        if not ch_list[0].isdigit():
            raise zPE.newDataException()

        # check sign
        if hex_val[1] in 'FACE':
            if sign == '+':
                ch_list.append('+')
            elif sign == '-':
                ch_list.append(' ')
            elif sign in [ 'DB', 'CR' ]:
                ch_list.append('  ')
            else:
                raise SyntaxError("sign must be '+', '-', 'DB', or 'CR'.")
        elif hex_val[1] in 'BD':
            if sign in [ '+', '-' ]:
                ch_list.append('-')
            elif sign in [ 'DB', 'CR' ]:
                ch_list.append(sign)
            else:
                raise SyntaxError("sign must be '+', '-', 'DB', or 'CR'.")
        else:
            raise zPE.newDataException()
        return ''.join(ch_list)

    @staticmethod
    def tr_val(dump):
        ch_str = P_.tr(dump, '+')
        return int(ch_str[-1] + ch_str[:-1])


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
        return self.tr(self.dump(), sign)

    def value(self):
        ch_str = self.tr(self.dump(), '+')
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
        # calculate natual length; in unit of bin_digit
        self.natual_len = length * 4 # for zone, natual length = 4 * len(str)
        # convert encoding
        self.__vals = [ord('0'.encode('EBCDIC-CP-US'))] * length
                                # initialize to all zeros
        for indx in range(0, min(ch_len, length), 1): # filling right to left
            self.__vals[length - indx - 1] = ord(
                ch_str[ch_len - indx - 1].encode('EBCDIC-CP-US')
                )
        # set sign for the last digit
        self.__vals[-1] = int(sign_digit + hex(self.__vals[-1])[-1], 16)

    def dump(self):
        return (self.__vals, self.natual_len)

    def fill__(self, dump):     # no error checking
        self.__vals = dump[0]
        self.natual_len = dump[1]

    @staticmethod
    def tr(dump, sign = '-'):
        vals = dump[0]
        ch_list = []
        for val in vals[:-1]:
            ch_list.append(chr(val).decode('EBCDIC-CP-US'))
        hex_val = hex(vals[-1])[2:].upper()
        ch_list.append(hex_val[1])

        int(''.join(ch_list))   # check format
        if hex_val[1] in 'FACE':
            if sign == '+':
                ch_list.append('+')
            elif sign == '-':
                ch_list.append(' ')
            elif sign in [ 'DB', 'CR' ]:
                ch_list.append('  ')
            else:
                raise SyntaxError("sign must be '+', '-', 'DB', or 'CR'.")
        elif hex_val[1] in 'BD':
            if sign in [ '+', '-' ]:
                ch_list.append('-')
            elif sign in [ 'DB', 'CR' ]:
                ch_list.append(sign)
            else:
                raise SyntaxError("sign must be '+', '-', 'DB', or 'CR'.")
        else:
            raise ValueError('invalid hex value.')
        return ''.join(ch_list)



# non-byte-based (numerical) types

class SDNumericalType(object):
    '''this is an abstract base class'''

    def __init__(self, int_str, length, n_byte):
        self.natual_len = n_byte * 8
        self._byte_len_ = n_byte
        self.set(int_str, length)

    def __len__(self):
        return self._byte_len_

    def get(self):
        return self.tr(self.dump())

    def value(self):
        return self.__val

    def set(self, int_str, length = 0):
        self.__val  = 0      # reset value
        self.__indx = 1      # reset insert index
        self.append(int_str, length)

    def append(self, int_str, length = 0):
        if not length:
            length = self._byte_len_
        if not 0 < length <= self.room_left(): # length not in (0, room left]
            raise ValueError('invalid length / no room to append')
        if isinstance(int_str, int) or isinstance(int_str, long):
            int_val = int_str
        elif isinstance(int_str, str):
            int_val = int(int_str, 10)
        else:
            raise ValueError('value is not a valid number')
        # get the max value allowed by the length
        max_val = 0x1 << ( 8 * length - 1 )
        if not - max_val <= int_val < max_val:
            raise ValueError('overflow: value too large')
        # update the value
        self.apply_append(int_val, length)

    def apply_append(self, val, length):
        self.__val  += val << ( 8 * (self._byte_len_ - length) )
        self.__indx += length

    def room_used(self):
        return self.__indx - 1

    def room_left(self):
        return self._byte_len_ - self.room_used()


    def dump(self):
        if self.__val >= 0:
            hex_str = '{0:0>{1}}'.format(
                hex(self.__val)[2:],
                self._byte_len_ * 2
                )
        else:
            hex_str = '{0:0>{1}}'.format( # display 2's complement
                hex((0x1 << self.natual_len) + self.__val)[2:],
                self._byte_len_ * 2
                )
        hex_str = hex_str[ : self.room_used() * 2] # get the actually used bytes
        return ( [ int(hex_str[ i : i+2 ], 16)
                   for i in [ i * 2 for i in range(len(hex_str)/2) ]
                   ],
                 self.room_used() * 8 # real length in bit
                 )

    def fill__(self, dump):
        '''load the universal dump into the internal structure'''
        raise AssertionError('require overridden')

    def load_value(self, val, length): # no error checking
        self.__val      = val
        self.natual_len = length

    @staticmethod
    def tr(dump):
        '''translate the universal dump to the repr string of this class'''
        raise AssertionError('require overridden')

class D_(SDNumericalType):
    def __init__(self, int_str, length = 0):
        super(D_, self).__init__(int_str, length, 8) # 8-byte natual length

    def fill__(self, dump):      # no error checking
        self.load_value(int(self.tr(dump)), dump[1])

    @staticmethod
    def tr(dump):
        vals = dump[0]
        int_val = vals[0]
        for indx in range(1, len(vals)):
            int_val *= 256
            int_val += vals[indx]
        int_val  %=  0xFFFFFFFFFFFFFFFF
        if int_val > 0x7FFFFFFFFFFFFFFF:
            int_str = '-{0}'.format(0x10000000000000000 - int_val)
                                    # 2's complement
        else:
            int_str = str(int_val)
        return int_str

class F_(SDNumericalType):
    def __init__(self, int_str, length = 0):
        super(F_, self).__init__(int_str, length, 4) # 4-byte natual length

    def fill__(self, dump):      # no error checking
        self.load_value(int(self.tr(dump)), dump[1])

    @staticmethod
    def tr(dump):
        vals = dump[0]
        int_val = vals[0]
        for indx in range(1, len(vals)):
            int_val *= 256
            int_val += vals[indx]
        int_val  %=  0xFFFFFFFF
        if int_val > 0x7FFFFFFF:
            int_str = '-{0}'.format(0x100000000 - int_val) # 2's complement
        else:
            int_str = str(int_val)
        return int_str

class H_(SDNumericalType):
    def __init__(self, int_str, length = 0):
        super(H_, self).__init__(int_str, length, 2) # 2-byte natual length

    def fill__(self, dump):      # no error checking
        self.load_value(int(self.tr(dump)), dump[1])

    @staticmethod
    def tr(dump):
        vals = dump[0]
        int_val = vals[0]
        for indx in range(1, len(vals)):
            int_val *= 256
            int_val += vals[indx]
        int_val  %=  0xFFFF
        if int_val > 0x7FFF:
            int_str = '-{0}'.format(0x10000 - int_val) # 2's complement
        else:
            int_str = str(int_val)
        return int_str


class A_(SDNumericalType):
    def __init__(self, int_str, length = 0):
        super(A_, self).__init__(int_str, length, 4) # 4-byte natual length

    def append(self, int_str, length = 0):
        if not length:
            length = self._byte_len_
        if not 0 < length <= self.room_left(): # length not in (0, room left]
            raise ValueError('invalid length / no room to append')
        if isinstance(int_str, int) or isinstance(int_str, long):
            int_val = int_str
        elif isinstance(int_str, str):
            int_val = int(int_str, 10)
        else:
            raise ValueError('value is not a valid number')
        # get the max value allowed by the length
        max_val = 0x1 << ( 8 * length )
        if not 0 <= int_val < max_val:
            raise ValueError('overflow: value too large.')
        # update the value
        self.apply_append(int_val, length)

    def dump(self):
        hex_str = '{0:0>8}'.format(hex(self.value())[2:])
        hex_str = hex_str[ : self.room_used() * 2] # get the actually used bytes
        return ( [ int(hex_str[ i : i+2 ], 16)
                   for i in [ i * 2 for i in range(len(hex_str)/2) ]
                   ],
                 self.room_used() * 8 # real length in bit
                 )

    def fill__(self, dump):      # no error checking
        self.load_value(int(self.tr(dump)[2:], 16), dump[1])

    @staticmethod
    def tr(dump):
        vals = dump[0]
        int_val = vals[0]
        for indx in range(1, len(vals)):
            int_val *= 256
            int_val += vals[indx]
        return '0x{0}'.format(
            '{0:0>8}'.format(
                hex(int_val % 0xFFFFFFFF)[2:-1].upper()
                )[ 8 - dump[1] / 4 : ] # only show the real length
            )


## simple type
BOUNDARY = [
    [ 'C', 'X', 'B', 'P', 'Z', ], # no boundary
    [ 'H', ],                     # half-word boundary
    [ 'F', 'A', 'V', ],           # full-word boundary
    [ 'D', ],                     # double-word boundary
    ]

const_s = {
    'C' : lambda val = '0', sz = 0: C_(val, sz),
    'D' : lambda val = '0', sz = 0: D_(val, sz),
    'X' : lambda val = '0', sz = 0: X_(val, sz),
    'B' : lambda val = '0', sz = 0: B_(val, sz),
    'F' : lambda val = '0', sz = 0: F_(val, sz),
    'H' : lambda val = '0', sz = 0: H_(val, sz),
    'P' : lambda val = '0', sz = 0: P_(val, sz),
    'Z' : lambda val = '0', sz = 0: Z_(val, sz),
    }

## address type
const_a = {
    'A' : lambda val = '0', sz = 0: A_(val, sz),
    'V' : lambda val = '0', sz = 0: A_('0', sz),
    }


## Interface Functions

def align_at(sd_ch):
    for indx in range(len(BOUNDARY)):
        if sd_ch in BOUNDARY[indx]:
            return 2 ** indx
    return 0


def can_get_sd(sd_info):
    try:
        get_sd(sd_info)
    except:
        return False
    return True

def get_sd(sd_info):
    if sd_info[0] == 's':
        rv = [None] * sd_info[1]
        for indx in range(sd_info[1]):
            rv[indx] = const_s[sd_info[2]](sd_info[4], sd_info[3])
        return rv
    elif sd_info[0] == 'a':
        rv = []
        for val in sd_info[4]:
            rv.append( const_a[sd_info[2]](val, sd_info[3]) )
        return rv
    else:
        return None

def update_sd(sd_list, sd_info):
    for indx in range(len(sd_list)):
        if sd_info[0] == 's':
            sd_list[indx].set(sd_info[4], sd_info[3])
        elif sd_info[0] == 'a':
            sd_list[indx].set(sd_info[4][indx], sd_info[3])


# rv: ( const_type, multiplier, ch, length, init_val, has_L )
#   const_type: 'a' | 's'
#   init_val:   str(num) | [ symbol ] | None
# exception:
#   SyntaxError: any syntax error in parsing the arguments
def parse_sd(sd_arg):
    # split into ( [mul]ch[Llen], val )
    L = zPE.resplit_sq('\(', sd_arg)  # split according to '\('
    sz = len(L)
    if sz == 2 and L[1][-1] == ')':
        # A(label) ==> [ 'A', 'label)' ]
        sd_ch = L[0]
        sd_val = zPE.resplit(',', L[1][:-1], ['(',"'"], [')',"'"])
        if not sd_val:
            sd_val = None
        val_tp = 'a'            # address type constant
    elif sz == 1:
        # AL3 ==> [ 'AL3' ]  or  8F'1' ==> [ "8F'1'" ]
        L = re.split("'", sd_arg) # re-split according to '\''
        sz = len(L)
        if sz == 3 and L[2] == '':
            # 8F'1' ==> [ '8F', '1', '' ]
            sd_ch = L[0]
            sd_val = L[1]
            val_tp = 's'        # simple constant
        elif sz == 1:           # DS
            # 8F ==> [ '8F' ]
            sd_ch = L[0]
            sd_val = None
            val_tp = 's'
        else:
            raise SyntaxError
    else:
        raise SyntaxError

    # split l[0] into [ multiplier, type, length ]
    L = re.split('([A-Z])L?', sd_ch) # split according to '?L'
    match = len(re.findall('([A-Z])L', sd_ch)) # match the postfix 'L'

    # parse multiplier
    if len(L) != 3:
        raise SyntaxError
    if L[0] == '':
        sd_mul = 1
    else:
        sd_mul = int(L[0])
    if val_tp == 'a' and sd_val and len(sd_val) > 0:
        sd_mul = max(sd_mul, len(sd_val))

    # check type
    const_tp = valid_sd(L[1])
    if not const_tp:
        raise SyntaxError
    sd_ch = L[1]
    if sd_val != None and const_tp != val_tp:
        raise SyntaxError

    # parse length
    if match == 0:              # no '?L' found
        has_L = False
        if L[2] == '':
            if const_tp == 's' and sd_val != None:
                sd_len = len(const_s[sd_ch](sd_val))
            else:
                if const_tp == 's':
                    sd_len = len(const_s[sd_ch]())
                else:
                    sd_len = len(const_a[sd_ch]())
        else:
            raise SyntaxError
    elif match == 1:            # one '?L' found
        has_L = True
        if L[2] == '':
            raise SyntaxError
        else:
            sd_len = int(L[2])
    else:                       # more than one '?L' found
        raise SyntaxError

    return (const_tp, sd_mul, sd_ch, sd_len, sd_val, has_L)


# it takes a string like F'12' or A(CARD)
def valid_sd(sd_arg_line):
    if sd_arg_line[0] in const_a:
        return 'a'
    elif sd_arg_line[0] in const_s:
        return 's'
    else:
        return None


# sd_info: ( 's', 1, ch, length, init_val )
#   see parse_sd(sd_arg) for more details
# exception:
#   ValueError: if the storage type cannot be evaluated
#   others:     along the way of parsing storage
def value_sd(sd_info):
    sd = get_sd(sd_info)[0]
    if sd.value() == None:
        raise ValueError('cannot evaluate the given storage type.')
    return ( sd.value(), sd.natual_len, )

### end of Constant Type Definition
