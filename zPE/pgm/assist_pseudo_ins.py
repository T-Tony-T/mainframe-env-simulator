# defines Pseudo-Instructions offered by ASSIST
import zPE

### add types supporting Pseudo-Instructions
from zPE.core.asm import InstructionType, OpConst, R, I, S, X, L

# int_16 => ( '', 'dddd' )
class D(InstructionType):
    def __init__(self, arg_pos, val = None):
        super(D, self).__init__('D', arg_pos)

        if val == None:
            self.valid = False
            self.__val = None
        else:
            self.set(val)

    def __len__(self):
        return 4                # number of half-bytes / hex-digits

    def get(self):
        if self.valid:
            return self.__val
        else:
            raise ValueError('value is invalid (non-initialized).')

    def prnt(self):
        if self.valid:
            rv = '{0:0>4}'.format(hex(self.__val)[2:].upper())
        else:
            rv = '----'
        return ( '', rv, )

    def value(self):
        if self.valid:
            rv = self.__val
        else:
            rv = None
        return rv

    def set(self, val):
        if not 0x0000 <= val <= 0xFFFF:
            raise ValueError('length offset must be between 0 and 65535')
        self.__val = val
        self.valid = True


### Pseudo-Instruction Mapping

PSEUDO_INS = {
    'XDECI' : lambda argc: ('53', R(1).wo(), X(2).ro() ), # argc not used
    'XDECO' : lambda argc: ('52', R(1).ro(), X(2).wo() ), # argc not used

    'XDUMP' : lambda argc: (
        ('E160', OpConst(S(1).ro(), 0), OpConst(D(2).ro(), 0), ),
        ('E060', S(1).ro(), OpConst(D(2).ro(), 4), ),
        ('E060', S(1).ro(), D(2).ro(), ),
        )[argc],

    'XPRNT' : lambda argc: (
        ('E020', S(1).ro(), OpConst(D(2).ro(), 133), ), # require at least 1 arg
        ('E020', S(1).ro(), OpConst(D(2).ro(), 133), ),
        ('E020', S(1).ro(), D(2).ro(), ),
        )[argc],
    'XREAD' : lambda argc: (
        ('E000', S(1).ro(), OpConst(D(2).ro(), 80), ), # require at least 1 arg
        ('E000', S(1).ro(), OpConst(D(2).ro(), 80), ),
        ('E000', S(1).ro(), D(2).ro(), ),
        )[argc],
    }


### Pseudo-Instruction OP-Code Mapping

PSEUDO_OP = {
    '52'   : ( 'XDECO', 3, lambda s : __xdeco(s[0], s[1], s[2], s[3:6]) ),
    '53'   : ( 'XDECI', 3, lambda s : __xdeci(s[0], s[1], s[2], s[3:6]) ),
    'E000' : ( 'XREAD', 4, lambda s : __xread(s[0], s[1:4], s[4:]) ),
    'E020' : ( 'XPRNT', 4, lambda s : __xprnt(s[0], s[1:4], s[4:]) ),
    'E160' : ( 'XDUMP', 4, lambda s : __xdump_reg() ),
    'E060' : ( 'XDUMP', 4, lambda s : __xdump(s[0], s[1:4], s[4:]) ),
    }

# internal functions supporting Pseudo-Instructions
from zPE.core.reg import GPR, SPR, Register
from zPE.core.mem import Memory
from zPE.core.cpu import __addr, __ref, __dump
# Note: zPE.core.cpu.__dump is not a memory dump report, but the content dump

X_MACRO_VAR = {
    'snape_cnt' : 0,            # number of times XSNAP get called
    }

def __xdump_reg():
    reg_list = [ '    {0}'.format(r) for r in GPR ]
    __xsnap_header('REGISTERS')
    __xout('XSNAPOUT', '0', ' REGS 0-7  ', *(reg_list[:8] + [ '\n' ]))
    __xout('XSNAPOUT', ' ', ' REGS 8-15 ', *(reg_list[8:] + [ '\n' ]))
    __xout('XSNAPOUT', '0', '\n')
    return

def __xdump(base, disp, size):
    addr_start = int(__addr(disp, '0', base))
    addr_end   = int(addr_start + int(size, 16))
    __xsnap_header('STORAGE')
    ctrl = '0'
    for line in Memory.dump_storage(addr_start, addr_end):
        __xout('XSNAPOUT', ctrl, line)
        ctrl = ' '
    __xout('XSNAPOUT', '0', '\n')
    return

def __xsnap_header(xdump_type):
    X_MACRO_VAR['snape_cnt'] += 1
    __xout('XSNAPOUT',
           '0', 'BEGIN XSNAP - CALL {0:>5} AT {1} USER {2}\n'.format(
            X_MACRO_VAR['snape_cnt'], SPR['PSW'].dump_hex()[1], xdump_type
            ))
    return


def __xread(base, disp, size):
    try:
        line = __xin('XREAD')[:-1]
        for offset in range(int(size, 16)):
            __ref(disp, '0', base, zPE.c2x(line[offset]), offset)
        SPR['PSW'].CC = 0       # read success

        if zPE.debug_mode():
            print 'Line Read:', line
    except:
        SPR['PSW'].CC = 1       # read error or EoF

        if zPE.debug_mode():
            print 'Xread Error or EoF'
    return

def __xprnt(base, disp, size):
    ctrl = ' '
    line = zPE.x2c(__dump(disp, base, int(size, 16)))
    if line[0] in ' 01-':
        ctrl = line[0]
    __xout('XPRNT', ctrl, line[1:], '\n')
    return


def __xdeci(reg, base, indx, disp):
    reg  = GPR[int(reg, 16)]
    addr = __addr(disp, indx, base)

    pg_i = addr / 4096          # index of the page containing the address
    addr = addr % 4096          # relative address within the page
    if pg_i not in Memory._pool_allocated:
        raise zPE.newProtectionException()

    received = []
    while True:
        byte = zPE.x2c(Memory._pool_allocated[pg_i][addr]) # get next byte
        if not received  and  byte != ' ':
            # first non-blank byte
            if byte not in '1234567890-+':
                # no number found, overflow
                GPR[1].load(pg_i * 4096 + addr)
                SPR['PSW'].CC = 3
                break           # stop processing
            if byte not in '-+':
                # digit, positive
                received.append('+')
            received.append(byte)
        elif len(received)  and  byte not in '1234567890':
            # end of the digit string
            GPR[1].load(pg_i * 4096 + addr)
            if 2 <= len(received) <= 10: # sign + up to 9 digits
                reg.load(int(''.join(received))).test()
            else:                        # sign along / more than 9 digits
                SPR['PSW'].CC = 3
            break               # stop processing
        elif len(received):
            # parsing the number
            received.append(byte)

        # update addr
        addr += 1
        if addr >= 4096:
            pg_i += 1
            addr = 0
            if pg_i not in Memory._pool_allocated:
                raise zPE.newProtectionException()
    return

def __xdeco(reg, base, indx, disp):
    num = '{0: >12}'.format(GPR[int(reg, 16)].int)
    for i in range(len(num)):
        __ref(disp, indx, base, zPE.c2x(num[i]), i)
    return


def __xin(spool):
    return zPE.core.SPOOL.retrieve(spool).pop(0)[0] # on EoF, raise exception

def __xout(spool, *words):
    zPE.core.SPOOL.retrieve(spool).append(*words)
    return
