# this defines the CPU execution details

import zPE

from reg import GPR, SPR, Register, RegisterPair
from mem import Memory
from asm import len_op, X_, P_, F_


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
        SPR['PSW'].ILC = (op_len + 1) / 2       # num of halfwords
                                                # (including half-filled one)
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
        indx = zPE.h2i(EX_reg)
        if indx:                # not R0
            if zPE.debug_mode():
                print '  ORing with R{0} = ******{1:0>2}'.format(
                    indx, zPE.i2h(GPR[indx][4])
                    )
            if op_len == 1:
                # 1-byte op-code
                arg = '{0:0>2}{1}'.format(
                    zPE.i2h( GPR[indx][4] | int(arg[0:2],16) ), arg[2:]
                    ) # perform OR on 2nd byte of instruction (1st arg byte)
            else:
                # 2-byte op-code
                op_code = '{0}{1:0>2}{2}'.format(
                    op_code[:2],
                    zPE.i2h( GPR[indx][4] | int(op_code[2:],16) )
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
        SPR['PSW'].ILC += len(arg) / 4  # num of additional halfword(s)
                                        # (not including half-filled one)
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
        print '  '.join([ str(r) for r in GPR[8:] ]), '\t\tCC =', SPR['PSW'].CC
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
               lambda s : [ __reg(s[0]).load(zPE.h2i(SPR['PSW'].dump_hex(2))),
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
    '1E'   : ( 'ALR',  1, lambda s : __reg(s[0]).add_lgc(__reg(s[1])) ),
    '1F'   : ( 'SLR',  1, lambda s : __reg(s[0]).sub_lgc(__reg(s[1])) ),
    '40'   : ( 'STH',  3,
               lambda s : __reg(s[0]).store( hw = True,
                                             * __page(s[3:6],s[1],s[2],2)
                                             ) ),
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
               lambda s : [ __reg(s[0]).load(zPE.h2i(SPR['PSW'].dump_hex(2))),
                            __cnt(Register(0), __addr(s[3:6],s[1],s[2]))
                            ] ),
    '46'   : ( 'BCT',  3, lambda s : __cnt(__reg(s[0]),
                                           __addr(s[3:6], s[1], s[2])
                                           ) ),
    '47'   : ( 'BC',   3, lambda s : __br(__mask(s[0]),
                                          __addr(s[3:6], s[1], s[2])
                                          ) ),
    '48'   : ( 'LH',   3,
               lambda s : __reg(s[0]).load( __deref(s[3:6],s[1],s[2],2),
                                            hw = True
                                            ) ),
    '49'   : ( 'CH',   3,
               lambda s : __reg(s[0]).cmp(__deref(s[3:6],s[1],s[2],2))
               ),
    '4A'   : ( 'AH',   3, lambda s : __reg(s[0]) + __deref(s[3:6],s[1],s[2],2)
               ),
    '4B'   : ( 'SH',   3, lambda s : __reg(s[0]) - __deref(s[3:6],s[1],s[2],2)
               ),
    '4C'   : ( 'MH',   3, lambda s : __reg(s[0]) * __deref(s[3:6],s[1],s[2],2)
               ),
    '4E'   : ( 'CVD',  3, lambda s : (
            lambda val_str = '{0:0>16}'.format(zPE.i2p(__reg(s[0]).int)),
            ( page, addr ) = __page(s[3:6],s[1],s[2],8) :
                page.store(addr,
                           ( (Register(zPE.h2i(val_str[:8])).long << 32) +
                             (Register(zPE.h2i(val_str[8:])).long)
                             ),
                           'dw'
                           )
            )() ),
    '4F'   : ( 'CVB',  3, lambda s : __reg(s[0]).load(
            __chk_dec(__deref(s[3:6],s[1],s[2],8), 8)
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
    '5E'   : ( 'AL',   3,
               lambda s : __reg(s[0]).add_lgc(__deref(s[3:6],s[1],s[2]))
               ),
    '5F'   : ( 'SL',   3,
               lambda s : __reg(s[0]).sub_lgc(__deref(s[3:6],s[1],s[2]))
               ),
    '86'   : ( 'BXH',  3, lambda s : (
            lambda R1 = __reg(s[0]), R2_num = zPE.h2i(s[1]) : [
                R1 + GPR[R2_num],                           # add increment
                R1.cmp(GPR[R2_num + (R2_num + 1) % 2]),     # cmp limit
                __br([ 2 ], __addr(s[3:6],'0',s[2])),       # BH  addr
                ]
            )() ),
    '87'   : ( 'BXLE', 3, lambda s : (
            lambda R1 = __reg(s[0]), R2_num = zPE.h2i(s[1]) : [
                R1 + GPR[R2_num],                           # add increment
                R1.cmp(GPR[R2_num + (R2_num + 1) % 2]),     # cmp limit
                __br([ 0, 1 ], __addr(s[3:6],'0',s[2])),    # BNH addr
                ]
            )() ),
    '88'   : ( 'SRL',  3, lambda s : __reg(s[0])  >> __addr(s[3:6],'0',s[2]) ),
    '89'   : ( 'SLL',  3, lambda s : __reg(s[0])  << __addr(s[3:6],'0',s[2]) ),
    '8A'   : ( 'SRA',  3,
               lambda s : __reg(s[0]).rshft(__addr(s[3:6],'0',s[2]))
               ),
    '8B'   : ( 'SLA',  3,
               lambda s : __reg(s[0]).lshft(__addr(s[3:6],'0',s[2]))
               ),
    '8C'   : ( 'SRDL', 3, lambda s : __pair(s[0]) >> __addr(s[3:6],'0',s[2]) ),
    '8D'   : ( 'SLDL', 3, lambda s : __pair(s[0]) << __addr(s[3:6],'0',s[2]) ),
    '8E'   : ( 'SRDA', 3,
               lambda s : __pair(s[0]).rshft(__addr(s[3:6],'0',s[2]))
               ),
    '8F'   : ( 'SLDA', 3,
               lambda s : __pair(s[0]).lshft(__addr(s[3:6],'0',s[2]))
               ),
    '90'   : ( 'STM',  3, lambda s : [
            __reg(s[0], offset).store(* __page(s[3:6],'0',s[2],4,offset))
            for offset in (
                lambda R1 = zPE.h2i(s[0]), R2 = zPE.h2i(s[1]) :
                    range([ R1 + i for i in range(16) ][R2 - R1] - R1 + 1)
                )() # this handles the case when R1 > R2 using negative index
            ] ),
    '91'   : ( 'TM',   3, lambda s : __tst_bit(__deref(s[3:6], '0', s[2], 1),
                                               zPE.h2i(s[0:2])
                                               ) ),
    '92'   : ( 'MVI',  3, lambda s : __ref(s[3:6],'0',s[2],s[0:2]) ),
    '94'   : ( 'NI',   3, lambda s : __refmod(s[3:6],'0',s[2],'N',s[0:2]) ),
    '95'   : ( 'CLI',  3, lambda s : __cmp_lgc(__deref(s[3:6], '0', s[2], 1),
                                               zPE.h2i(s[0:2])
                                               ) ),
    '96'   : ( 'OI',   3, lambda s : __refmod(s[3:6],'0',s[2],'O',s[0:2]) ),
    '97'   : ( 'XI',   3, lambda s : __refmod(s[3:6],'0',s[2],'X',s[0:2]) ),
    '98'   : ( 'LM',   3, lambda s : [
            __reg(s[0], offset).load(  __deref(s[3:6],'0',s[2],4,offset))
            for offset in (
                lambda R1 = zPE.h2i(s[0]), R2 = zPE.h2i(s[1]) :
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
    'D4'   : ( 'NC',   5, lambda s : [
            __refmod( s[3:6], '0', s[2], 'N',                 # d, i, b, AND
                      __deref(s[7:10], '0', s[6], 1, offset), # value
                      offset,                                 # offset
                      offset and SPR['PSW'].CC
                      )         # skip zero-check if CC is already 1
            for offset in range(__dclen(s[0:2]))
            ] ),
    'D5'   : ( 'CLC',  5, lambda s : [
            __cmp_lgc(__deref(s[3:6],  '0', s[2], 1, offset),
                      __deref(s[7:10], '0', s[6], 1, offset),
                      offset and SPR['PSW'].CC
                      )     # skip comparison if CC is set to non-zero
            for offset in range(__dclen(s[0:2]))
            ] ),
    'D6'   : ( 'OC',   5, lambda s : [
            __refmod( s[3:6], '0', s[2], 'O',                 # d, i, b, OR
                      __deref(s[7:10], '0', s[6], 1, offset), # value
                      offset,                                 # offset
                      offset and SPR['PSW'].CC
                      )         # skip zero-check if CC is already 1
            for offset in range(__dclen(s[0:2]))
            ] ),
    'D7'   : ( 'XC',   5, lambda s : [
            __refmod( s[3:6], '0', s[2], 'X',                 # d, i, b, XOR
                      __deref(s[7:10], '0', s[6], 1, offset), # value
                      offset,                                 # offset
                      offset and SPR['PSW'].CC
                      )         # skip zero-check if CC is already 1
            for offset in range(__dclen(s[0:2]))
            ] ),
    'DC'   : ( 'TR',   5, lambda s : (
            lambda tr_val_gen_func = ( # encapsulate a tr mapping generator
                lambda tr_index : __deref(s[7:10], '0', s[6], 1, tr_index)
                ) :
                [ __refmod( s[3:6], '0', s[2], 'R', # d, i, b, TR
                            tr_val_gen_func,        # value generator (function)
                            offset                  # offset
                            )
                  for offset in range(__dclen(s[0:2]))
                  ]
            )() ),
    'DD'   : ( 'TRT',  5, lambda s : (
            lambda tr_val_gen_func = ( # encapsulate a tr mapping generator
                lambda tr_index : __deref(s[7:10], '0', s[6], 1, tr_index)
                ) :
                [ __refmod( s[3:6], '0', s[2], 'T', # d, i, b, TRT
                            tr_val_gen_func,        # value generator (function)
                            offset,                 # offset
                            offset and SPR['PSW'].CC
                            )   # skip translation if CC is non-zero
                  for offset in range(__dclen(s[0:2]))
                  ]
            )() ),
    'DE'   : ( 'ED',   5,
               lambda s : __ed(s[3:6], s[2], __dclen(s[0:2]), s[7:10], s[6])
               ),
    'DF'   : ( 'EDMK', 5,
               lambda s : __ed(s[3:6], s[2], __dclen(s[0:2]), s[7:10], s[6], 1)
               ),
    'F0'   : ( 'SRP',  5, lambda s : __shft_dec(
            s[3:6], s[2], __dclen(s[0]),
            __addr(s[7:10],'0',s[6]), # encoded shift code
            zPE.h2i(s[1])             # rounding factor
            ) ),
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
            zPE.p2i(__dump(s[7:10],s[6],__dclen(s[1]))),
            cc = True, ex = None # set CC, no exception checking
            ) ),
    'F9'   : ( 'CP',   5, lambda s : __cmp_dec(
            zPE.p2i( __dump(s[3:6], s[2],__dclen(s[0])) ),
            zPE.p2i( __dump(s[7:10],s[6],__dclen(s[1])) )
            ) ),
    'FA'   : ( 'AP',   5, lambda s : __ref_dec(
            s[3:6], __dclen(s[0]), s[2],
            ( zPE.p2i( __dump(s[3:6], s[2],__dclen(s[0])) ) +
              zPE.p2i( __dump(s[7:10],s[6],__dclen(s[1])) )
              ),
            cc = True, ex = None # set CC, no exception checking
            ) ),
    'FB'   : ( 'SP',   5, lambda s : __ref_dec(
            s[3:6], __dclen(s[0]), s[2],
            ( zPE.p2i( __dump(s[3:6], s[2],__dclen(s[0])) ) -
              zPE.p2i( __dump(s[7:10],s[6],__dclen(s[1])) )
              ),
            cc = True, ex = None # set CC, no exception checking
            ) ),
    'FC'   : ( 'MP',   5, lambda s : __ref_dec(
            s[3:6], __dclen(s[0]), s[2],
            ( zPE.p2i( __dump(s[3:6], s[2],__dclen(s[0])) ) *
              zPE.p2i( __dump(s[7:10],s[6],__dclen(s[1])) )
              ),
            cc = False, ex = __dclen(s[1])
            ) ),
    'FD'   : ( 'DP',   5, lambda s : __ref_dec(
            s[3:6], __dclen(s[0]), s[2],
            divmod( zPE.p2i( __dump(s[3:6], s[2],__dclen(s[0])) ),
                    zPE.p2i( __dump(s[7:10],s[6],__dclen(s[1])) )
                    ),
            cc = False, ex = __dclen(s[1])
            ) ),
    }

def decode_op(mnem):
    return ins_op[mnem][0]
###

### Internal Functions

def __dclen(lc):                # decode length-code to length
    return zPE.h2i(lc) + 1

def __reg(r, offset = 0):       # register retriever
    return GPR[ zPE.h2i(r) + offset - 16 ]

def __addr_reg(r):              # addressing register retriever
    reg_num = zPE.h2i(r)
    if reg_num:
        return GPR[reg_num].addr()
    else:
        return None

def __pair(r):                  # even-odd pair registers retriever
    indx = zPE.h2i(r)
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
    return indx + base + zPE.h2i(d)

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
    return __refmod(d, x, b, '=', byte, offset, skip_CC = True)

def __refmod(d, x, b, action, byte, offset = 0, skip_CC = False):
    if isinstance(byte, str):
        byte = zPE.h2i(byte)
    ( page, addr ) = __page(d, x, b, 1, offset) # have to be byteword boundary

    if action == 'N':
        byte &= page.retrieve(addr, 'bw')
    elif action == 'O':
        byte |= page.retrieve(addr, 'bw')
    elif action == 'X':
        byte ^= page.retrieve(addr, 'bw')
    elif action == 'R':
        byte = byte(page.retrieve(addr, 'bw')) # get the actual byte
        skip_CC = True          # always skip CC
    elif action == 'T':
        if skip_CC:             # in TRT, skip_CC is used to skip translation
            SPR['PSW'].CC = 1   # stop early, change CC to 1
            return None
        byte = byte(page.retrieve(addr, 'bw')) # get the actual byte
        if byte:                # non-zero, scan succeed
            addr = __addr(d, x, b) + offset
            for i in [ 4, 3, 2 ]: # load offset into right-most 3 bytes of R1
                GPR[1][i] = addr & 0xFF
                addr  >>= 8
            GPR[2][4] = byte    # insert tr value into right-most byte of R2
            SPR['PSW'].CC = 2   # assume the end of the scan field
        else:
            SPR['PSW'].CC = 0
        return None

    page[addr] = byte

    if not skip_CC:
        SPR['PSW'].CC = bool(byte)
    return byte    

def __deref(d, x, b, al = 4, offset = 0): # default to fullword boundary
    ( page, addr ) = __page(d, x, b, al, offset)
    return page.retrieve(addr, zPE.align_fmt_map[al])

def __dump(d, b, size):
    base = __addr_reg(b)
    if not base:
        base = 0
    addr_start = zPE.h2i(d) + base
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
    if cnt_reg.decrement() and addr != None:
        SPR['PSW'].Instruct_addr = addr
        return True
    return False

def __cmp(val_l, val_r, skip = False):
    if skip:
        return None
    return Register(val_l).cmp(val_r)     # CC is set in Register.cmp()

def __cmp_lgc(val_l, val_r, skip = False):
    if skip:
        return None
    return Register(val_l).cmp_lgc(val_r) # CC is set in Register.cmp_lgc()


def __tst_bit(val_l, val_r):
    val_and = val_l & val_r
    if not val_and:             # bits tested are all 0s
        SPR['PSW'].CC = 0
    elif val_and == val_r:      # bits tested are all 1s
        SPR['PSW'].CC = 3
    else:
        SPR['PSW'].CC = 1       # bits tested are mixed 0(s) and 1(s)
    return SPR['PSW'].CC


## packed decimal operation

def __cmp_dec(val_l, val_r):
    if val_l == val_r:
        SPR['PSW'].CC = 0
    elif val_l < val_r:
        SPR['PSW'].CC = 1
    else:
        SPR['PSW'].CC = 2
    return SPR['PSW'].CC

def __ref_dec(d, l, b, value, cc = True, ex = None):
    '''
    value: result / (quotient, reminder)
    cc:    True / False
    ex:    None / L2 - required if value = (quotient, reminder)
    '''
    ex_action = 'M'             # will be ignored if ex == None
    if isinstance(value, int) or isinstance(value, long):
        val_str = '{0:0>{1}}'.format(zPE.i2p(value), l * 2)
    elif not ex:
        zPE.abort(-1, 'Error: zPE.core.cpu.__ref_dec(): invalid call.\n')
    else:
        val_str = '{0:0>{1}}{2:0>{3}}'.format(
            zPE.i2p(value[0]), (l - ex) * 2, # store quotient in D1(L1-L2,B1)
            zPE.i2p(value[1]), ex * 2        # store reminder in D1+L1-L2(L2,B2)
            )
        ex_action = 'D'
    indx_s = len(val_str) / 2 - l
    if cc:                      # condition code is to be set
        if indx_s:
            SPR['PSW'].CC = 3
        elif value > 0:
            SPR['PSW'].CC = 2
        elif value < 0:
            SPR['PSW'].CC = 1
        else:
            SPR['PSW'].CC = 0
    if ex:                      # exception is to be checked
        if l <= ex:
            raise zPE.newSpecificationException()
        if ex_action == 'M':
            if zPE.h2i(__dump(d,b,ex)):
                raise zPE.newDataException()
        if ex_action == 'D':
            if ex > 8:
                raise zPE.newSpecificationException()
            if indx_s:
                raise zPE.newDecimalDivideException()
            
    # store back the new value
    value = X_(val_str).dump()[0]
    [ __ref(d, '0', b, value[offset], offset - indx_s)
      for offset in range(indx_s, l)
      ]
    return SPR['PSW'].CC

def __shft_dec(d, b, l, shft_code, rounding):
    val_str = __dump(d, b, l)
    if val_str[-1] in 'FACE':
        val_sign = 1
    else:
        val_sign = -1
    val_len = len(val_str) - 1  # length of the digit string

    # (0 < l < 16)  =>  (0 < byte_cnt < 32)  =>  (0 < digit_cnt < 31)
    buff = '{0:0>32}{1:0>32}'.format(val_str[:-1], '') # val_32|zero_32
    buff = buff[shft_code:] + buff[:shft_code]         # spin the circular array

    overflow = False
    if shft_code > 32:
        # right shift, add rounding factor
        val_str = '{0:0>{1}}'.format(int(buff[:33]) + rounding, val_len)[:-1]
    else:
        # left shift, check overflow
        val_str = buff[32 - val_len : 32]
        if int(buff[32:]):      # zero_32 != all_zero, overflow occured
            overflow = True

    # determine and append sign digit
    val = int(val_str) * val_sign
    if val < 0:
        val_str += 'D'
    else:
        val_str += 'C'

    # set CC
    if overflow:
        SPR['PSW'].CC = 3
    elif val > 0:
        SPR['PSW'].CC = 2
    elif val < 0:
        SPR['PSW'].CC = 1
    else:
        SPR['PSW'].CC = 0

    # store back the new value
    value = X_(val_str).dump()[0]
    [ __ref(d, '0', b, value[offset], offset)
      for offset in range(l)
      ]
    return SPR['PSW'].CC

def __ed(pttn_disp, pttn_base, ed_len, src_disp, src_base, mark_reg = None):
    significance_indicator = False
    num_sign = 0                # for CC calculation

    fill = __deref(pttn_disp, '0', pttn_base, 1, 0)
    if fill not in [ 0x20, 0x21 ]:
        indx_s = 1
    else:
        indx_s = 0

    src_field_swap = {
        'buff'   : '',          # buffer for src field
        'offset' : 0,           # offset for src field
        'digit'  : False,       # whether encountered any digit
        }
    def get_next_src_digit(look_ahead = False):
        if not src_field_swap['buff']:
            # no buffered src digits, read next byte
            src_field_swap['buff'] = '{0:0>2}'.format(zPE.i2h(__deref(
                        src_disp, '0', src_base, 1, src_field_swap['offset']
                        )))
            src_field_swap['offset'] += 1
        rv = src_field_swap['buff'][0]
        if not look_ahead:
            src_field_swap['buff'] = src_field_swap['buff'][1:] # pop the digit
            src_field_swap['digit'] = bool(src_field_swap['digit']  or  rv.isdigit())
        return rv

    for indx in range(indx_s, ed_len):
        pttn = __deref(pttn_disp, '0', pttn_base, 1, indx)

        if pttn in [ 0x20, 0x21 ]:
            # digit selector / significance indicator

            # get the next src digit
            src_digit = get_next_src_digit()
            if not src_digit.isdigit()  and  src_field_swap['digit']:
                # end of current field
                src_field_swap['digit'] = False
                src_digit = get_next_src_digit()
            if not src_digit.isdigit(): # still not digit -> invalid format
                raise zPE.newDataException()
            src_digit = int(src_digit)
            if src_digit:
                num_sign = 1    # mark as non-zero

            if significance_indicator  or  src_digit:
                __ref(pttn_disp, '0', pttn_base, 0xF0 + src_digit, indx)
                if mark_reg  and  not significance_indicator:
                    # from off to on, mark it if required
                    GPR[mark_reg].load(__addr(pttn_disp,'0',pttn_base) + indx)
                significance_indicator = True
            else:
                __ref(pttn_disp, '0', pttn_base, fill, indx)
                if pttn == 0x21:
                    significance_indicator = True

            # check sign
            if src_field_swap['buff'] and src_field_swap['buff'][0] in 'FACE':
                significance_indicator = False

        elif pttn == 0x22:
            # field separator
            __ref(pttn_disp, '0', pttn_base, fill, indx)
            significance_indicator = False
            num_sign = 0        # reset sign field

        else:
            # message character
            if not significance_indicator:
                __ref(pttn_disp, '0', pttn_base, fill, indx)

    # get the next src digit
    if significance_indicator:
        num_sign = (- num_sign) # mark negative

    if num_sign == 0:
        SPR['PSW'].CC = 0
    elif num_sign < 0:
        SPR['PSW'].CC = 1
    else:
        SPR['PSW'].CC = 2
    return SPR['PSW'].CC

def __chk_dec(val, al):
    val = zPE.p2i(zPE.i2h(val)) # raise data exception if cannot convert to int
    try:
        F_(val)                 # validate value range
    except:
        raise zPE.newFixedPointDivideException()
    return val
