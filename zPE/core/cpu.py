# this defines the CPU execution details

import zPE

from reg import GPR, SPR, Register, RegisterPair
from mem import Memory
from asm import len_op, X_, P_


### Interface Function Definition

def fetch(EX_addr = None, EX_reg = None):
    '''
    both EX_addr and EX_reg should not be touched by any regular fetch;
    only an EX instruction should pass those to `fetch()`
    '''
    if EX_reg:
        addr = EX_addr                  # use the address specified by EX
    else:
        addr = SPR['PSW'].Instruct_addr # retrieve address of next instruction

    # check address alignment
    if addr % 2 != 0:
        raise zPE.newSpecificationException()

    # get to the page containing the address
    pg_i = addr / 4096          # index of the page containing the address
    addr = addr % 4096          # relative address within the page

    if pg_i not in Memory._pool_allocated:
        raise zPE.newProtectionException()
    page = Memory._pool_allocated[pg_i] # get the actual page

    # get 1st byte of the op-code
    op_code = page[addr]
    addr += 1
    if EX_reg and op_code == '44':
        # try to EXecute an EX instruction
        raise zPE.newSystemException('0C3', 'EXECUTION EXCEPTION')

    # test if op-code is more than one byte
    op_len = len_op([ op_code ]) / 2 # op_code_byte_cnt = num_of_hex_digit / 2

    if op_len == 2:             # 2-byte op-code
        op_code += page[addr]   # no need to check page, since aligned on hw
        addr += 1

    if not EX_reg:
        # update ILC and Address pointer
        SPR['PSW'].ILC = op_len / 2 # num of halfwords
        SPR['PSW'].Instruct_addr += op_len

    # validate op-code
    if op_code not in ins_op:
        raise zPE.newOperationException()

    # fetch the argument(s)
    byte_cnt = ins_op[op_code][1] # get the byte_cnt of the argument(s)
    if addr + byte_cnt > 4096:
        # retrieve next page, if available
        if pg_i + 1 not in Memory._pool_allocated:
            raise zPE.newProtectionException()
        next_page = Memory._pool_allocated[pg_i + 1]
        arg = page[addr : ] + next_page[ : addr + byte_cnt - 4096]
    else:
        arg = page[addr : addr + byte_cnt]

    if EX_reg:
        if zPE.debug_mode():
            print '[ EX instruction ] receives:', op_code, arg

        # perform OR if needed
        indx = __h2i(EX_reg)
        if indx:                # not R0
            if zPE.debug_mode():
                print '  ORing with R{0} = {1:0>2}******'.format(
                    indx, hex(GPR[indx][1])[2:].upper()
                    )
            if op_len == 1:
                # 1-byte op-code
                arg = '{0:0>2}{1}'.format(
                    hex( GPR[indx][1] | int(arg[0:2],16) )[2:].upper(), arg[2:]
                    ) # perform OR on 2nd byte of instruction (1st arg byte)
            else:
                # 2-byte op-code
                op_code = '{0}{1:0>2}{2}'.format(
                    op_code[:2],
                    hex( GPR[indx][1] | int(op_code[2:],16) )[2:].upper()
                    ) # perform OR on 2nd byte of instruction (2nd op-code byte)
                # validate op-code
                if op_code not in ins_op:
                    raise zPE.newOperationException()
                # validate arg length
                if byte_cnt != ins_op[op_code][1]:
                    raise zPE.newOperationException()
        else:
            if zPE.debug_mode():
                print '  Register is R0, no instruction unchanged'

    else:
        # update ILC and Address pointer
        SPR['PSW'].ILC += len(arg) / 4 # num of halfwords
        SPR['PSW'].Instruct_addr += len(arg) / 2

    return ( op_code, arg )


def execute(ins):
    if zPE.debug_mode():
        print 'Exec: {0}: {1}'.format(
            ins_op[ins[0]][0],
            ' '.join(zPE.fixed_width_split(4, ''.join(ins)))
            )
    ins_op[ins[0]][2](ins[1]) # execute the instruction against the arguments

    if zPE.debug_mode() and ins[0] != '44': # skip EX
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
    '05'   : ( 'BALR', 1,
               lambda s : [ __reg(s[0]).load(SPR['PSW'].Instruct_addr),
                            __cnt(Register(0), __addr_reg(s[1]))
                            ] ),
    '06'   : ( 'BCTR', 1, lambda s : __cnt(__reg(s[0]), __addr_reg(s[1])) ),
    '07'   : ( 'BCR',  1, lambda s : __br(__mask(s[0]), __reg(s[1]).addr()) ),
    '10'   : ( 'LPR',  1, lambda s : __reg(s[0]).load(__reg(s[1])).set_abs() ),
    '11'   : ( 'LNR',  1, lambda s : __reg(s[0]).load(__reg(s[1])).neg_abs() ),
    '12'   : ( 'LTR',  1, lambda s : __reg(s[0]).load(__reg(s[1])).test() ),
    '13'   : ( 'LCR',  1, lambda s : __reg(s[0]).load(__reg(s[1])).neg_val() ),
    '14'   : ( 'NR',   1, lambda s : __reg(s[0]) & __reg(s[1]) ),
    '15'   : ( 'CLR',  1, lambda s : __reg(s[0]).cmp_lgc(__reg(s[1])) ),
    '16'   : ( 'OR',   1, lambda s : __reg(s[0]) | __reg(s[1]) ),
    '17'   : ( 'XR',   1, lambda s : __reg(s[0]) ^ __reg(s[1]) ),
    '18'   : ( 'LR',   1, lambda s : __reg(s[0]).load(__reg(s[1])) ),
    '19'   : ( 'CR',   1, lambda s : __reg(s[0]).cmp(__reg(s[1])) ),
    '1A'   : ( 'AR',   1, lambda s : __reg(s[0])  + __reg(s[1]) ),
    '1B'   : ( 'SR',   1, lambda s : __reg(s[0])  - __reg(s[1]) ),
    '1C'   : ( 'MR',   1, lambda s : __pair(s[0]) * __reg(s[1]) ),
    '1D'   : ( 'DR',   1, lambda s : __pair(s[0]) / __reg(s[1]) ),
    '41'   : ( 'LA',   3,
               lambda s : __reg(s[0]).load( __addr(s[3:6],s[1],s[2])   )
               ),
    '42'   : ( 'STC',  3,
               lambda s : __reg(s[0]).stc(* __page(s[3:6],s[1],s[2],1) )
               ),
    '43'   : ( 'IC',   3,
               lambda s : __reg(s[0]).inc( __deref(s[3:6],s[1],s[2],1) )
               ),
    '44'   : ( 'EX',   3,
               lambda s : execute(fetch(__addr(s[3:6],s[1],s[2]), s[0]))
               ),
    '45'   : ( 'BAL',  3,
               lambda s : [ __reg(s[0]).load(SPR['PSW'].Instruct_addr),
                            __cnt(Register(0), __addr(s[3:6],s[1],s[2]))
                            ] ),
    '46'   : ( 'BCT',  3, lambda s : __cnt(__reg(s[0]),
                                           __addr(s[3:6], s[1], s[2])
                                           ) ),
    '47'   : ( 'BC',   3, lambda s : __br(__mask(s[0]),
                                          __addr(s[3:6], s[1], s[2])
                                          ) ),
    '50'   : ( 'ST',   3,
               lambda s : __reg(s[0]).store(* __page(s[3:6],s[1],s[2]))
               ),
    '54'   : ( 'N',    3, lambda s : __reg(s[0]) & __deref(s[3:6],s[1],s[2]) ),
    '55'   : ( 'CL',   3,
               lambda s : __reg(s[0]).cmp_lgc(__deref(s[3:6],s[1],s[2]))
               ),
    '56'   : ( 'O',    3, lambda s : __reg(s[0]) | __deref(s[3:6],s[1],s[2]) ),
    '57'   : ( 'X',    3, lambda s : __reg(s[0]) ^ __deref(s[3:6],s[1],s[2]) ),
    '58'   : ( 'L',    3, lambda s : __reg(s[0]).load(__deref(s[3:6],s[1],s[2]))
               ),
    '59'   : ( 'C',    3, lambda s : __reg(s[0]).cmp(__deref(s[3:6],s[1],s[2]))
               ),
    '5A'   : ( 'A',    3, lambda s : __reg(s[0])  + __deref(s[3:6],s[1],s[2]) ),
    '5B'   : ( 'S',    3, lambda s : __reg(s[0])  - __deref(s[3:6],s[1],s[2]) ),
    '5C'   : ( 'M',    3, lambda s : __pair(s[0]) * __deref(s[3:6],s[1],s[2]) ),
    '5D'   : ( 'D',    3, lambda s : __pair(s[0]) / __deref(s[3:6],s[1],s[2]) ),
    '86'   : ( 'BXH',  3, lambda s : (
            lambda R1 = __reg(s[0]), R2_num = __h2i(s[1]) : [
                R1 + GPR[R2_num],                           # add increment
                R1.cmp(GPR[R2_num + (R2_num + 1) % 2]),     # cmp limit
                __br([ 2 ], __addr(s[3:6],'0',s[2])),       # BH  addr
                ]
            )() ),
    '87'   : ( 'BXLE', 3, lambda s : (
            lambda R1 = __reg(s[0]), R2_num = __h2i(s[1]) : [
                R1 + GPR[R2_num],                           # add increment
                R1.cmp(GPR[R2_num + (R2_num + 1) % 2]),     # cmp limit
                __br([ 0, 1 ], __addr(s[3:6],'0',s[2])),    # BNH addr
                ]
            )() ),
    '90'   : ( 'STM',  3, lambda s : [
            __reg(s[0], offset).store(* __page(s[3:6],'0',s[2],4,offset))
            for offset in (
                lambda R1 = __h2i(s[0]), R2 = __h2i(s[1]) :
                    range([ R1 + i for i in range(16) ][R2 - R1] - R1 + 1)
                )() # this handles the case when R1 > R2 using negative index
            ] ),
    '92'   : ( 'MVI',  3, lambda s : __ref(s[3:6],'0',s[2],s[0:2]) ),
    '95'   : ( 'CLI',  3, lambda s : __cmp_lgc(__deref(s[3:6], '0', s[2], 1),
                                               __h2i(s[0:2])
                                               ) ),
    '98'   : ( 'LM',   3, lambda s : [
            __reg(s[0], offset).load(  __deref(s[3:6],'0',s[2],4,offset))
            for offset in (
                lambda R1 = __h2i(s[0]), R2 = __h2i(s[1]) :
                    range([ R1 + i for i in range(16) ][R2 - R1] - R1 + 1)
                )() # this handles the case when R1 > R2 using negative index
            ] ),
    'BE'   : ( 'STCM', 3, lambda s : (
            lambda mask = __mask(s[1]) : [
                __reg(s[0]).stc(* __page(s[3:6], '0', s[2], 1, offset),
                                  pos = mask[offset] # keyword (named) arg
                                  ) # list extension must be last unmaned arg
                for offset in range(len(mask))
                ]
            )() ),
    'BF'   : ( 'ICM',  3, lambda s : (
            lambda mask = __mask(s[1]) :
                __reg(s[0]).inc(__dump(s[3:6],s[2],len(mask)), mask)
            )() ),
    'D2'   : ( 'MVC',  5, lambda s : [
            __ref( s[3:6], '0', s[2],                      # d, i, b
                   __deref(s[7:10], '0', s[6], 1, offset), # value
                   offset                                  # offset
                   )
            for offset in range(__dclen(s[0:2]))
            ] ),
    'D5'   : ( 'CLC',  5, lambda s : [
            __cmp_lgc(__deref(s[3:6],  '0', s[2], 1, offset),
                      __deref(s[7:10], '0', s[6], 1, offset),
                      offset and SPR['PSW'].CC
                      )     # skip comparison if CC is set to non-zero
            for offset in range(__dclen(s[0:2]))
            ] ),
    'F2'   : ( 'PACK', 5, lambda s : (
            lambda pack_lst = P_.pack(__dump(s[7:10], s[6], __dclen(s[1])),
                                      __dclen(s[0])) :
                [ __ref(s[3:6], '0', s[2], pack_lst[offset], offset)
                  for offset in range(len(pack_lst))
                  ]
            )() ),
    'F3'   : ( 'UNPK', 5, lambda s : (
            lambda pack_lst = P_.unpk(__dump(s[7:10], s[6], __dclen(s[1])),
                                      __dclen(s[0])) :
                [ __ref(s[3:6], '0', s[2], pack_lst[offset], offset)
                  for offset in range(len(pack_lst))
                  ]
            )() ),
    'F8'   : ( 'ZAP',  5, lambda s : __ref_dec(
            s[3:6], __dclen(s[0]), s[2],
            zPE.p2i(__dump(s[7:10],s[6],__dclen(s[1])))
            ) ),
    'FA'   : ( 'AP',   5, lambda s : __ref_dec(
            s[3:6], __dclen(s[0]), s[2],
            ( zPE.p2i( __dump(s[3:6], s[2],__dclen(s[0])) ) +
              zPE.p2i( __dump(s[7:10],s[6],__dclen(s[1])) )
              )
            ) ),
    'FB'   : ( 'SP',   5, lambda s : __ref_dec(
            s[3:6], __dclen(s[0]), s[2],
            ( zPE.p2i( __dump(s[3:6], s[2],__dclen(s[0])) ) -
              zPE.p2i( __dump(s[7:10],s[6],__dclen(s[1])) )
              )
            ) ),
    }

def decode_op(mnem):
    return ins_op[mnem][0]
###

### Internal Functions

def __h2i(r):                   # hex to integer convertor
    return int(r, 16)

def __dclen(lc):                # decode length-code to length
    return __h2i(lc) + 1

def __reg(r, offset = 0):       # register retriever
    return GPR[ __h2i(r) + offset - 16 ]

def __addr_reg(r):              # addressing register retriever
    reg_num = __h2i(r)
    if reg_num:
        return GPR[reg_num].addr()
    else:
        return None

def __pair(r):                  # even-odd pair registers retriever
    indx = __h2i(r)
    if indx % 2 != 0:
        raise zPE.newSpecificationException()
    return RegisterPair(GPR[indx], GPR[indx + 1])

def __addr(d, x, b):            # address retriever
    indx = __addr_reg(x)
    if not indx:
        indx = 0
    base = __addr_reg(b)
    if not base:
        base = 0
    return indx + base + __h2i(d)

def __page(d, x, b, al = 4, offset = 0): # default to fullword boundary
    addr = __addr(d, x, b) + offset * al
    if addr % al != 0:
        raise zPE.newSpecificationException()

    pg_i = addr / 4096          # index of the page containing the address
    addr = addr % 4096          # relative address within the page

    if pg_i not in Memory._pool_allocated:
        raise zPE.newProtectionException()
    return ( Memory._pool_allocated[pg_i], int(addr) )

def __ref(d, x, b, byte, offset = 0):
    if isinstance(byte, str):
        byte = __h2i(byte)
    ( page, addr ) = __page(d, x, b, 1, offset) # have to be byteword boundary
    page[addr] = byte
    return byte

def __ref_dec(d, l, b, value):
    if value > 0:
        SPR['PSW'].CC = 2
    elif value < 0:
        SPR['PSW'].CC = 1
    else:
        SPR['PSW'].CC = 0
    value = '{0:0>{1}}'.format(zPE.i2p(value), l * 2)
    indx_s = len(value) / 2 - l
    if indx_s:
        SPR['PSW'].CC = 3

    value = X_(value).dump()[0]
    [ __ref(d, '0', b, value[offset], offset - indx_s)
      for offset in range(indx_s, l)
      ]

def __deref(d, x, b, al = 4, offset = 0): # default to fullword boundary
    ( page, addr ) = __page(d, x, b, al, offset)
    return page.retrieve(addr, zPE.align_fmt_map[al])

def __dump(d, b, size):
    addr_start = __h2i(d) + __addr_reg(b)
    addr_end   = addr_start + size
    try:
        val = Memory.deref_storage(addr_start, addr_end)
    except:
        raise zPE.newProtectionException()
    return val

def __mask(m):
    return zPE.listify_mask(m)


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

def __cmp(val_l, val_r, skip = False):
    if skip:
        return None
    return Register(val_l).cmp(val_r)

def __cmp_lgc(val_l, val_r, skip = False):
    if skip:
        return None
    return Register(val_l).cmp_lgc(val_r)
