# this defines the CPU execution details

import zPE

from reg import GPR, SPR, Register, RegisterPair
from mem import Memory
from asm import len_op


### Interface Function Definition

def fetch():
    addr = SPR['PSW'].Instruct_addr
    if addr % 2 != 0:
        raise ValueError('S', '0C6', 'SPECIFICATION EXCEPTION')

    pg_i = addr / 4096          # index of the page containing the address
    addr = addr % 4096          # relative address within the page

    if pg_i not in Memory._pool_allocated:
        raise ValueError('S', '0C4', 'PROTECTION EXCEPTION')
    page = Memory._pool_allocated[pg_i] # get the actual page

    op_code = page[addr]
    addr += 1
    if len_op([ op_code ]) == 4:
        op_code += page[addr]
        addr += 1
    if op_code not in ins_op:
        raise ValueError('S', '0C1', 'OPERATION EXCEPTION')

    byte_cnt = ins_op[op_code][0] # only fetch the argument(s) themselves
    if addr + byte_cnt > 4096:
        # retrieve next page, if available
        if pg_i + 1 not in Memory._pool_allocated:
            raise ValueError('S', '0C4', 'PROTECTION EXCEPTION')
        next_page = Memory._pool_allocated[pg_i + 1]
        arg = page[addr : ] + next_page[ : addr + byte_cnt - 4096]
    else:
        arg = page[addr : addr + byte_cnt]

    return ( op_code, arg )


def execute(ins):
    SPR['PSW'].ILC =  (len(ins[0]) + len(ins[1]) ) / 2 # num of bytes
    SPR['PSW'].Instruct_addr += SPR['PSW'].ILC
    SPR['PSW'].ILC /= 2         # further reduce to num of halfwords

    ins_op[ins[0]][1](ins[1]) # execute the instruction against the arguments

    if zPE.debug_mode():
        print 'Exec:', ins
        print '  '.join([ str(r) for r in GPR[:8] ]), '\t\t', SPR['PSW']
        print '  '.join([ str(r) for r in GPR[8:] ])
        print ''.join(Memory.allocation.values()[0].dump_all()),
        print ''.join(Memory.allocation.values()[1].dump_all())
        print
    return


def parse_time(time):
    if time.isdigit():
        return int(time) * 60
    if time[0] != '(' or time[-1] != ')':
        raise SyntaxError('Invalid format. Use TIME=(m,s) or TIME=m instead.')
    time = time[1:-1].split(',')
    if len(time) != 2:
        raise SyntaxError('Invalid format. Use TIME=(m,s) or TIME=m instead.')
    return int('{0:0>1}'.format(time[0])) * 60 + int('{0:0>1}'.format(time[1]))
###


### Instruction Look-up Tabel
ins_op = {
    '05'   : ( 1, lambda s : [ __reg(s[0]).load(SPR['PSW'].Instruct_addr),
                               __cnt(Register(0), __addr_reg(s[1]))
                               ] ),
    '06'   : ( 1, lambda s : __cnt(__reg(s[0]), __addr_reg(s[1])) ),
    '07'   : ( 1, lambda s : __br(__mask(s[0]), __reg(s[1]).addr()) ),
    '10'   : ( 1, lambda s : __reg(s[0]).load(__reg(s[1])).set_abs() ),
    '11'   : ( 1, lambda s : __reg(s[0]).load(__reg(s[1])).neg_abs() ),
    '12'   : ( 1, lambda s : __reg(s[0]).load(__reg(s[1])).test() ),
    '13'   : ( 1, lambda s : __reg(s[0]).load(__reg(s[1])).neg_val() ),
    '14'   : ( 1, lambda s : __reg(s[0]) & __reg(s[1]) ),
    '15'   : ( 1, lambda s : __reg(s[0]).cmp_lgc(__reg(s[1])) ),
    '16'   : ( 1, lambda s : __reg(s[0]) | __reg(s[1]) ),
    '17'   : ( 1, lambda s : __reg(s[0]) ^ __reg(s[1]) ),
    '18'   : ( 1, lambda s : __reg(s[0]).load(__reg(s[1])) ),
    '19'   : ( 1, lambda s : __reg(s[0]).cmp(__reg(s[1])) ),
    '1A'   : ( 1, lambda s : __reg(s[0])  + __reg(s[1]) ),
    '1B'   : ( 1, lambda s : __reg(s[0])  - __reg(s[1]) ),
    '1C'   : ( 1, lambda s : __pair(s[0]) * __reg(s[1]) ),
    '1D'   : ( 1, lambda s : __pair(s[0]) / __reg(s[1]) ),
    '41'   : ( 3, lambda s : __reg(s[0]).load( __addr(s[3:6], s[1], s[2])) ),
    '42'   : ( 3, lambda s : __reg(s[0]).stc(* __page(s[3:6], s[1], s[2], 1)) ),
    '43'   : ( 3, lambda s : __reg(s[0]).inc(  __addr(s[3:6], s[1], s[2], 1)) ),
    '44'   : ( 3, lambda s : None ), # EX, not implemented for now
    '45'   : ( 3, lambda s : [ __reg(s[0]).load(SPR['PSW'].Instruct_addr),
                               __cnt(Register(0), __addr(s[3:6], s[1], s[2]))
                               ] ),
    '46'   : ( 3, lambda s : __cnt(__reg(s[0]), __addr(s[3:6], s[1], s[2])) ),
    '47'   : ( 3, lambda s : __br(__mask(s[0]), __addr(s[3:6], s[1], s[2])) ),
    '50'   : ( 3, lambda s : __reg(s[0]).store(* __page(s[3:6], s[1], s[2])) ),
    '54'   : ( 3, lambda s : __reg(s[0]) & __deref(s[3:6], s[1], s[2]) ),
    '55'   : ( 3, lambda s : __reg(s[0]).cmp_lgc(__deref(s[3:6], s[1], s[2])) ),
    '56'   : ( 3, lambda s : __reg(s[0]) | __deref(s[3:6], s[1], s[2]) ),
    '57'   : ( 3, lambda s : __reg(s[0]) ^ __deref(s[3:6], s[1], s[2]) ),
    '58'   : ( 3, lambda s : __reg(s[0]).load(__deref(s[3:6], s[1], s[2])) ),
    '59'   : ( 3, lambda s : __reg(s[0]).cmp(__deref(s[3:6], s[1], s[2])) ),
    '5A'   : ( 3, lambda s : __reg(s[0])  + __deref(s[3:6], s[1], s[2]) ),
    '5B'   : ( 3, lambda s : __reg(s[0])  - __deref(s[3:6], s[1], s[2]) ),
    '5C'   : ( 3, lambda s : __pair(s[0]) * __deref(s[3:6], s[1], s[2]) ),
    '5D'   : ( 3, lambda s : __pair(s[0]) / __deref(s[3:6], s[1], s[2]) ),
    '90'   : ( 3, lambda s : [
            __reg(s[0], offset).store(* __page(s[3:6], '0', s[2], 4, offset))
            for offset in (
                lambda R1 = __indx(s[0]), R2 = __indx(s[1]) :
                    range([ R1 + i for i in range(16) ][R2 - R1 + 1] - R1)
                )() # this handles the case when R1 > R2 using negative index
            ] ),
    '92'   : ( 3, lambda s : __ref(s[3:6], '0', s[2], s[0:2]) ),
    '98'   : ( 3, lambda s : [
            __reg(s[0], offset).load(  __deref(s[3:6], '0', s[2], 4, offset))
            for offset in (
                lambda R1 = __indx(s[0]), R2 = __indx(s[1]) :
                    range([ R1 + i for i in range(16) ][R2 - R1 + 1] - R1)
                )() # this handles the case when R1 > R2 using negative index
            ] ),
    'BE'   : ( 3, lambda s : (
            lambda mask = __mask(s[1]) : [
                __reg(s[0]).stc(* __page(s[3:6], '0', s[2], 1, offset),
                                  pos = mask[offset] # keyword (named) arg
                                  ) # list extension must be last unmaned arg
                for offset in range(len(mask))
                ]
            )() ),
    'BF'   : ( 3, lambda s : (
            lambda mask = __mask(s[1]) : [
                __reg(s[0]).inc( __deref(s[3:6], '0', s[2], 1, offset),
                                 mask[offset]
                                 )
                for offset in range(len(mask))
                ]
            )() ),
    'D2'   : ( 5, lambda s : [
            __ref( s[3:6], '0', s[2],                      # d, i, b
                   __deref(s[7:10], '0', s[6], 1, offset), # value
                   offset                                  # offset
                   )
            for offset in range(int(s[0:2], 16) + 1) # length = length code + 1
            ] ),
    }
###

### Internal Functions

def __indx(r):
    return int(r, 16)

def __reg(r, offset = 0):
    return GPR[ __indx(r) + offset - 16 ]

def __addr_reg(r):
    reg_num = __indx(r)
    if reg_num:
        return GPR[reg_num].addr()
    else:
        return None

def __pair(r):
    indx = __indx(r)
    if indx % 2 != 0:
        raise ValueError('S', '0C6', 'SPECIFICATION EXCEPTION')
    return RegisterPair(GPR[indx], GPR[indx + 1])

def __addr(d, x, b):
    indx = __addr_reg(x)
    if not indx:
        indx = 0
    base = __addr_reg(b)
    if not base:
        base = 0
    return indx + base + int(d, 16)

def __page(d, x, b, al = 4, offset = 0): # default to fullword boundary
    addr = __addr(d, x, b) + offset * al
    if addr % al != 0:
        raise ValueError('S', '0C6', 'SPECIFICATION EXCEPTION')
    
    pg_i = addr / 4096          # index of the page containing the address
    addr = addr % 4096          # relative address within the page

    if pg_i not in Memory._pool_allocated:
        raise ValueError('S', '0C4', 'PROTECTION EXCEPTION')
    return ( Memory._pool_allocated[pg_i], int(addr) )

def __ref(d, x, b, byte, offset = 0):
    if isinstance(byte, str):
        byte = int(byte, 16)
    ( page, addr ) = __page(d, x, b, 1, offset) # have to be byteword boundary
    page[addr] = byte
    return byte

def __deref(d, x, b, al = 4, offset = 0): # default to fullword boundary
    ( page, addr ) = __page(d, x, b, al, offset)
    return page.retrieve(addr, zPE.align_fmt_map[al])

def __mask(m):
    mask = '{0:0>4}'.format(bin(int(m, 16))[2:])
    return [ i for i in range(4) if mask[i] == '1' ]

def __br(mask, addr):
    if SPR['PSW'].CC in mask:
        SPR['PSW'].Instruct_addr = addr
        return True
    return False

def __cnt(cnt_reg, addr):
    cnt_reg.decrement()
    if addr != None:
        SPR['PSW'].Instruct_addr = addr
        return True
    return False
