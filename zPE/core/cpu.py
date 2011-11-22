# this defines the CPU execution details

import zPE

from reg import GPR, SPR, RegisterPair
from mem import Memory
from asm import len_op


### Interface Function Definition

def fetch():
    addr = SPR['PSW'].Instruct_addr
    if addr % 2 != 0:
        raise ValueError('specification exception')

    pg_i = addr / 4096          # index of the page containing the address
    addr = addr % 4096          # relative address within the page

    if pg_i not in Memory._pool_allocated:
        raise ValueError('protection exception')
    page = Memory._pool_allocated[pg_i] # get the actual page

    op_code = page[addr]
    addr += 1
    if len_op([ op_code ]) == 4:
        op_code += page[addr]
        addr += 1
    if op_code not in ins_op:
        raise ValueError('operation exception')

    byte_cnt = ins_op[op_code][0] # only fetch the argument(s) themselves
    if addr + byte_cnt > 4096:
        # retrieve next page, if available
        if pg_i + 1 not in Memory._pool_allocated:
            raise ValueError('protection exception')
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
    '05'   : ( 1, lambda s : None ),
    '06'   : ( 1, lambda s : None ),
    '07'   : ( 1, lambda s : None ),
    '12'   : ( 1, lambda s : None ),
    '13'   : ( 1, lambda s : None ),
    '14'   : ( 1, lambda s : None ),
    '15'   : ( 1, lambda s : None ),
    '16'   : ( 1, lambda s : None ),
    '17'   : ( 1, lambda s : None ),
    '18'   : ( 1, lambda s : __reg(s[0]) << __reg(s[1]) ),
    '19'   : ( 1, lambda s : None ),
    '1A'   : ( 1, lambda s : __reg(s[0])  + __reg(s[1]) ),
    '1B'   : ( 1, lambda s : __reg(s[0])  - __reg(s[1]) ),
    '1C'   : ( 1, lambda s : __pair(s[0]) * __reg(s[1]) ),
    '1D'   : ( 1, lambda s : __pair(s[0]) / __reg(s[1]) ),
    '41'   : ( 3, lambda s : __reg(s[0]) << __addr(s[3:6], s[1], s[2]) ),
    '42'   : ( 3, lambda s : None ),
    '43'   : ( 3, lambda s : None ),
    '44'   : ( 3, lambda s : None ),
    '45'   : ( 3, lambda s : None ),
    '46'   : ( 3, lambda s : None ),
    '47'   : ( 3, lambda s : None ),
    '50'   : ( 3, lambda s : __reg(s[0]) >> __page(s[3:6], s[1], s[2]) ),
    '54'   : ( 3, lambda s : None ),
    '55'   : ( 3, lambda s : None ),
    '56'   : ( 3, lambda s : None ),
    '57'   : ( 3, lambda s : None ),
    '58'   : ( 3, lambda s : __reg(s[0]) << __deref(s[3:6], s[1], s[2]) ),
    '59'   : ( 3, lambda s : None ),
    '5A'   : ( 1, lambda s : __reg(s[0])  + __deref(s[3:6], s[1], s[2]) ),
    '5B'   : ( 1, lambda s : __reg(s[0])  - __deref(s[3:6], s[1], s[2]) ),
    '5C'   : ( 1, lambda s : __pair(s[0]) * __deref(s[3:6], s[1], s[2]) ),
    '5D'   : ( 1, lambda s : __pair(s[0]) / __deref(s[3:6], s[1], s[2]) ),
    '90'   : ( 3, lambda s : None ),
    '98'   : ( 3, lambda s : None ),
    }
###

### Internal Functions

def __reg(r):
    return GPR[int(r, 16)]

def __pair(r):
    indx = int(r, 16)
    if indx % 2 != 0:
        raise ValueError('specification exception')
    return RegisterPair(GPR[indx], GPR[indx + 1])

def __addr(d, x, b):
    if x == '0':
        indx = 0
    else:
        indx = __reg(x).long
    if b == '0':
        base = 0
    else:
        base = __reg(b).long
    return indx + base + int(d, 16)

def __page(d, x, b, al = 4):      # default to fullword boundary
    addr = __addr(d, x, b)
    if addr % al != 0:
        raise ValueError('specification exception')
    
    pg_i = addr / 4096          # index of the page containing the address
    addr = addr % 4096          # relative address within the page

    if pg_i not in Memory._pool_allocated:
        raise ValueError('protection exception')
    return ( Memory._pool_allocated[pg_i], int(addr) )

def __deref(d, x, b, al = 4):     # default to fullword boundary
    ( page, addr ) = __page(d, x, b, al)
    return page.retrieve(addr, zPE.align_fmt_map[al])
