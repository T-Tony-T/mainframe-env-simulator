################################################################
# Program Name:
#     ASMA90
#
# Purpose:
#     assemble the assembler source code into object code
#
# Parameter:
#     not implemented yet
#
# Input:
#     SYSIN     source code to be assembled
#     SYSLIB    macro libraries
#
# SWAP:
#     SYSUT1    required by the ASMA90 as sketch file
#
# Output:
#     SYSLIN    object module generated
#     SYSPRINT  source listing and diagnostic message
#
# Return Code:
#     object module generated:
#      0        clear assemble
#      2        clear assemble, with notificaton messages
#      4        warnings occured during assembly
#
#     no objmod generated:
#      8        errors occured during assembly
#     12        severe errors occured during assembly
#     16        insufficient resources
#
# Return Value:
#     none
################################################################


import zPE

import re
from time import localtime, strftime
from random import randint
from binascii import a2b_hex

from asma90_config import *   # read resource file for ASM config + rc

from asma90_err_code_rc import *        # read recourse file for err msg
from asma90_macro_preprocessor import * # read recourse file for macro support

# read recourse file for objmod specification
from asma90_objmod_spec import REC_FMT as OBJMOD_REC
from asma90_objmod_spec import deck_id as OBJMOD_SEQ


FILE_CHK = [                    # files to be checked
    'SYSIN', 'SYSPRINT', 'SYSLIN', 'SYSUT1',
    ]
FILE_REQ = [                    # files that are required
    'SYSIN', 'SYSPRINT', 'SYSLIN', 'SYSUT1',
    ]
FILE_GEN = {                    # files that will be generated if missing
    }


def init(step):
    # check for file requirement
    if __MISSED_FILE(step) != 0:
        return zPE.RC['CRITICAL']

    # load the user-supplied PARM and config into the default configuration
    # asm_load_parm({
    #         })
    asm_load_config({
            'MEM_POS' : randint(512*128, 4096*128) * 8, # random from 512K to 4M
            'REGION'  : step.region,
            })

    while not zPE.core.SPOOL.retrieve('SYSIN').empty():
        rc = max(pass_1(), pass_2())

        __PARSE_OUT()
        asm_init_res()          # release resources

        if rc >= RC['ERROR']:
            return rc        
    return rc


def pass_1():
    spi = zPE.core.SPOOL.retrieve('SYSIN')  # input SPOOL
    spt = zPE.core.SPOOL.retrieve('SYSUT1') # sketch SPOOL

    if spi.empty():
        raise EOFError('No Assembler Code Offered.')
    asm_init_res()              # initialize resources

# Macro parsing are currently disabled.
#
#    macro_init()                # load and init macro engine
#    macro_parse(spi)            # pre-process macro
#

    addr = 0                    # program counter
    prev_addr = None            # previous program counter
    line_num = 0

    scope = ScopeCounter()

    # memory heap for constant allocation
    const_pool = {}             # same format as SYMBOL
    const_pool_lbl = []         # order of the occurrence
    const_plid = None
    const_left = 0              # number of =constant LTORG/END allocated

    skip_until = None
    eoflag  = False
    autoeof = False

    # main read loop
    while True:
        # check END
        if spi.empty():         # encountered EOF before END
            # manually insert an END instruction
            spi.append('{0:<8} END\n'.format(''))
            autoeof = True

        # retrieve the next line
        ( line, deck_id ) = spi.pop(0)
        line_num += 1                  # start at line No. 1

        field = zPE.resplit_sq(r'\s+', line[:-1], 3)

        # check Macro definition
        if len(field) > 1 and field[1] == 'MACRO':
            skip_until = 'MEND'
        if skip_until:
            # skip all lines until the end flag encountered
            if len(field) > 1 and field[1] == skip_until:
                skip_until = None
            spt.push( ( line, deck_id, ) )
            continue

        # skip comment, EJECT
        if ( line[0] == '*'  or
             (len(field) > 1 and field[1] in [ 'EJECT', ])
             ):
            spt.push( ( line, deck_id, ) )
            continue

        # check SPACE
        elif len(field) > 1 and field[1] == 'SPACE':
            if len(field) > 2  and  not field[2].isdigit():
                zPE.abort(91, 'Error: ', field[2],
                          ': Argument is not a valid number')
            spt.push( ( line, deck_id, ) )
            continue


        # check label
        ins_lbl = zPE.bad_label(field[0])
        if ins_lbl:
            __INFO('E', line_num, ( 143, ins_lbl - 1, len(field[0]), ))

        # check for OP code
        if len(field) < 2:
            __INFO('E', line_num, ( 142, 9, None, ))

            MNEMONIC[line_num] = [ scope.id(), addr, ]          # type 2
            spt.push( ( line, deck_id, ) )
            continue
        # end of checks

        # parse TITLE
        if field[1] == 'TITLE':
            # check label
            if ins_lbl == 0:    # valid label
                if not TITLE[0]:
                    TITLE[0] = field[0] # record the first named TITLE

            if ( len(field[2]) < 2    or # at least "''"
                 field[2][0]  != "'"  or # start with "'"
                 field[2][-1] != "'"  or # end with "'"
                 "'" in field[2][1:-1]   # no "'" in the content
                 ):
                zPE.abort(91, 'Error: ', field[2], ': Invalid TITLE content.\n')
            TITLE.append([ line_num, field[0], field[2][1:-1] ])

            MNEMONIC[line_num] = [  ]                           # type 0
            spt.push( ( line, deck_id, ) )

        # parse CSECT/DSECT
        elif field[1] in [ 'CSECT', 'DSECT', ]:
            # update the current CSECT/DSECT info, if any
            if scope.id(test = True):
                ESD[scope.label()][0].length = addr

            # allocate scope id for new CSECT/DSECT
            if ins_lbl != 0:    # no label detected, or an invalid label
                # treat it as PC symbol
                addr = scope.new(field[1], line_num, None)
            else:               # valid label
                addr = scope.new(field[1], line_num, field[0])
            prev_addr = None

            MNEMONIC[line_num] = [ scope.id(), addr, ]          # type 2
            spt.push( ( line, deck_id, ) )

        # parse USING
        elif field[1] == 'USING':
            # actual parsing in pass 2
            MNEMONIC[line_num] = [ scope.id(), ]                # type 1 **
            spt.push( ( line, deck_id, ) )

        # parse DROP
        elif field[1] == 'DROP':
            # actual parsing in pass 2
            MNEMONIC[line_num] = [ scope.id(), ]                # type 1
            spt.push( ( line, deck_id, ) )

        # parse END
        elif field[1] == 'END':
            if len(field[0]) != 0: # has label
                __INFO('W', line_num, ( 165, 0, None, ))

            if not eoflag:
                # first time encounter END
                eoflag = True
                spt.push( ( line, deck_id, ) )
                # the scope ID of END is always None, and
                # the location counter is always 0
                MNEMONIC[line_num] = [ None, 0, ]               # type 2
            
            if const_plid:      # check left-over constants
                spi.push( ( line, deck_id, ), 0 ) # put back the END card
                spi.insert(0, ' LTORG\a') # hand left-over constants to LTORG
                                          # the generated LTORG will be removed
                continue

            else:               # no left-over constant, end the program
                # update the CSECT info
                ESD[scope.label()][0].length = addr

                addr = 0    # reset program counter
                prev_addr = None

                if autoeof:
                    __INFO('W', line_num, ( 140, 9, None, ))
                break           # end of program

        # parse LTORG
        elif field[1] == 'LTORG':
            # align boundary
            addr = (addr + 7) / 8 * 8

            curr_pool = [
                [],     # pool for constant with double-word alignment
                [],     # pool for constant with full-word alignment
                [],     # pool for constant with half-word alignment
                [],     # pool for constant with byte alignment
                ]
            curr_pool_al = {
                0b000 : 0,      # evenly dividable by 8, [0] into above list
                0b100 : 1,      # evenly dividable by 4, etc.
                0b010 : 2, 0b110 : 2,
                0b001 : 3, 0b011 : 3, 0b101 : 3, 0b111 : 3,
                }

            for lbl in const_pool_lbl:
                alignment = zPE.core.asm.align_at(lbl[1])

                sd_info = zPE.core.asm.parse_sd(lbl[1:])
                sd_len  = sd_info[1] * sd_info[3]
                if (sd_len & 0b111) in curr_pool_al:
                    alignment = max(alignment, sd_len)

                curr_pool[curr_pool_al[alignment & 0b111]].append(lbl)

            line_num_tmp = 0    # start insertion before next line
            for pool in curr_pool:
                for lbl in pool:
                    spi.insert(line_num_tmp, '{0:<15}{1}\n'.format('', lbl))
                    ALLOC_EQ_SYMBOL(lbl, const_pool[lbl])
                    const_left += 1
                    line_num_tmp += 1

            # close the current pool
            const_pool.clear()
            del const_pool_lbl[:]
            const_plid = None

            if line == ' LTORG\a'  and  deck_id == None:
                # inserted LTORG, ignore it
                line_num -= 1   # move back one line (since not LTORG)
            else:
                MNEMONIC[line_num] = [ scope.id(), addr, ]      # type 2
                spt.push( ( line, deck_id, ) )

        # parse EQU
        elif field[1] == 'EQU':
            if field[2].isdigit():
                # simple equates expression
                equ_reloc = 'A' # absolute symbol

                equ_addr = int(field[2]) # exp_1
                equ_len  = 1             # exp_2 [omitted, default length]
            else:
                # complex equates expression(s)
                equ_reloc = 'C' # complexly relocatable symbol

                zPE.mark4future('complex EQUates exp')

            # check label
            lbl_8 = '{0:<8}'.format(field[0])
            if lbl_8 in SYMBOL: # duplicated label definition
                __INFO('E', line_num, ( 43, 0, len(field[0]), ))
            elif ins_lbl == 0:  # valid label
                SYMBOL[lbl_8] = Symbol(
                    equ_len, equ_addr, scope.id(),
                    equ_reloc, 'U', '', '',
                    line_num, []
                    )

            MNEMONIC[line_num] = [ scope.id(),                  # type 4
                                   None, # need info
                                   None, # need info
                                   equ_addr,
                                   ]
            spt.push( ( line, deck_id, ) )

        # parse DC/DS/=constant
        elif field[1] in [ 'DC', 'DS' ] or field[1][0] == '=':
            if field[1][0] == '=':
                tmp = field[1][1:]
            else:
                tmp = field[2]
            try:
                sd_info = zPE.core.asm.parse_sd(tmp)
            except:
                zPE.abort( 91, 'Error: ', tmp,
                           ': Invalid constant at line {0}.\n'.format(line_num)
                           )

            # align boundary if needed
            if not sd_info[5]:
                # do not have length specified, force alignment
                alignment = zPE.core.asm.align_at(sd_info[2])
                addr = (addr + alignment - 1) / alignment * alignment

            # check =constant
            if field[1][0] == '=':
                if not const_left:
                    indx_s = line.index(field[1])
                    __INFO('E', line_num,
                           ( 141, indx_s, indx_s + len(field[1]), )
                           )
                    MNEMONIC[line_num] = [ scope.id(), ]        # type 1
                    spt.push( ( line, deck_id, ) )
                    continue

                if field[1] in SYMBOL_EQ:
                    symbol = __HAS_EQ(field[1], scope.id())
                    if symbol == None:
                        zPE.abort(91, 'Error: ', field[1],
                                  ': Fail to find the allocation.\n')
                    else:       # found successfully
                        if symbol.defn != None:
                            zPE.warn('** Warning: ', field[1],
                                     ': =Const redefined at line ',
                                     str(line_num), '; was at line ',
                                     str(symbol.defn), '\n')
                        const_left -= 1
                        symbol.length = sd_info[3]
                        symbol.value  = addr
                        symbol.type   = sd_info[2]
                        symbol.defn   = line_num
                else:
                    zPE.abort(91, 'Error: ', field[1],
                              ': Fail to allocate the constant.\n')

            # check address const
            if sd_info[0] == 'a' and sd_info[4] != None:
                if sd_info[2] == 'V':
                    # check external reference
                    for lbl in sd_info[4]:
                        bad_lbl = zPE.bad_label(lbl)
                        lbl_8 = '{0:<8}'.format(lbl)

                        if bad_lbl == None:
                            zPE.abort(
                                91, 'wrong value in sd:{0}.\n'.format(sd_info)
                                )
                        elif bad_lbl:
                            indx_s = line.index(lbl) + bad_lbl - 1
                            __INFO( 'E', line_num,
                                    ( 143, indx_s, indx_s + len(lbl), )
                                    )
                        else:
                            # update the Cross-References ER Sub-Table
                            if lbl_8 not in SYMBOL_V:
                                SYMBOL_V[lbl_8] = Symbol(
                                    1, 0, scope.id(),
                                    '', 'T', '', '',
                                    line_num, [ ]
                                    )
                            SYMBOL_V[lbl_8].references.append(
                                '{0:>4}{1}'.format(line_num, '')
                                )

                            # update the External Symbol Dictionary
                            if lbl_8 not in ESD:
                                ESD[lbl_8] = (
                                    ExternalSymbol(
                                        None, None, None, None,
                                        None, ASM_PARM['AMODE'],
                                        ASM_PARM['RMODE'], None,
                                        ),
                                    ExternalSymbol(
                                        None, None, None, None,
                                        None, ASM_PARM['AMODE'],
                                        ASM_PARM['RMODE'], None,
                                        ),
                                    )
                            if ESD[lbl_8][1].id == None:
                                ESD[lbl_8][1].type = 'ER'
                                ESD[lbl_8][1].id = scope.next()

                                ESD_ID[ESD[lbl_8][1].id] = lbl_8

                elif sd_info[2] == 'A':
                    # check internal reference
                    for lbl_i in range(len(sd_info[4])):
                        sd_info[4][lbl_i] = '0' # fool the paser
                    pass        # hand check to pass 2
                else:
                    zPE.abort(91, 'Error: ', sd_info[2],
                              ': Invalid address type.\n')

            # check lable
            lbl_8 = '{0:<8}'.format(field[0])
            if lbl_8 in SYMBOL: # duplicated label definition
                __INFO('E', line_num, ( 43, 0, len(field[0]), ))
            elif ins_lbl == 0:  # valid label
                SYMBOL[lbl_8] = Symbol(
                    sd_info[3], addr, scope.id(),
                    '', sd_info[2], sd_info[2], '',
                    line_num, []
                    )

            if field[1] == 'DC' and not zPE.core.asm.can_get_sd(sd_info):
                zPE.abort(91, 'Error: ', field[2],
                          ': Cannot evaluate the constant.\n')
            MNEMONIC[line_num] = [ scope.id(), addr, sd_info, ] # type 3
            spt.push( ( line, deck_id, ) )

            # update address
            prev_addr = addr
            addr += sd_info[1] * sd_info[3]

        # parse op-code
        elif zPE.core.asm.valid_op(field[1]):
            # align boundary
            addr = addr + addr % 2

            if len(field) < 3  or  field[2] == '':
                # no argument offered
                argv = []
                argc = 0
            else:
                # has argument(s), get the count
                argv = zPE.resplit(',', field[2], ['(',"'"], [')',"'"])
                argc = len(argv)
            if zPE.core.asm.valid_pseudo(field[1]):
                op_code = zPE.core.asm.get_op_from(field[1], argc)
            else:
                op_code = zPE.core.asm.get_op(field[1])
            op_args = zPE.core.asm.op_arg_indx(op_code)

            # check arguments
            if not op_args:                 # no args required
                pass
            elif len(op_args) > len(argv):  # too few args
                indx_s = line.index(argv[-1]) + len(argv[-1])
                __INFO('S', line_num, ( 175, indx_s, indx_s, ))
                arg_list = field[2]
            elif len(op_args) < len(argv):  # too many args
                indx_e = line.index(field[2]) + len(field[2])
                __INFO('S', line_num, (
                        173,
                        indx_e - len(argv[len(op_args)]) - 1, # -1 for ','
                        indx_e,
                        ))
                arg_list = field[2]
            else:                           # correct number of args
                # check arguments
                for arg in argv:
                    res = __PARSE_ARG(arg, bypass_sym = True)
                    if isinstance(res, int):
                        indx_e = line.index(arg) + res
                        __INFO('E', line_num, ( 41, indx_e - 1, indx_e, ))
                        break

                    for indx in range(len(res[0]) - 1):
                        lbl = res[0][indx]
                        if res[1][indx] == 'eq_constant':
                            # parse =constant
                            if not const_plid:
                                # allocate new pool
                                const_plid = scope.id()

                            if lbl in const_pool:
                                const_pool[lbl].references.append(
                                    '{0:>4}{1}'.format(line_num, '')
                                    )
                            elif zPE.core.asm.valid_sd(lbl[1:]):
                                try:
                                    sd_info = zPE.core.asm.parse_sd(lbl[1:])
                                except:
                                    zPE.abort( 91, 'Error: ', lbl[1:],
                                               ': Invalid constant at line',
                                               ' {0}.\n'.format(line_num)
                                               )

                                # validate =constant (not complete)
                                if sd_info[4] == None:
                                    zPE.abort( 91, 'Error: ', lbl[1:],
                                               ': Uninitialized constant at',
                                               ' line {0}.\n'.format(line_num)
                                               )
                                if sd_info[0] == 'a':
                                    for tmp in sd_info[4]:
                                        bad_lbl = zPE.bad_label(tmp)
                                        if bad_lbl == None:
                                            zPE.abort( 91, 'wrong value in sd:',
                                                       '{0}.\n'.format(sd_info)
                                                       )
                                        elif bad_lbl:
                                            indx_s = line.index(tmp)+bad_lbl-1
                                            __INFO( 'E', line_num, (
                                                    143,
                                                    indx_s,
                                                    indx_s + len(tmp),
                                                    ) )

                                # add =constant to the constant pool
                                if not INFO_GE(line_num, 'W'):
                                    const_pool[lbl] = Symbol(
                                        None, None, const_plid,
                                        '', lbl[1], '', '',
                                        None, [
                                            '{0:>4}{1}'.format(line_num, ''),
                                            ]
                                        )
                                    const_pool_lbl.append(lbl)
                            else:
                                indx_s = line.index(lbl) + 1
                                __INFO('E', line_num,
                                       ( 65, indx_s, indx_s - 1 + len(lbl), )
                                       )

                        elif res[1][indx] == 'inline_const':
                            # in-line constant
                            sd_info = zPE.core.asm.parse_sd(lbl)
                            if not sd_info[5]:
                                sd_info = (sd_info[0], sd_info[1], sd_info[2],
                                           0, sd_info[4], sd_info[3]
                                           )
                            if sd_info[2] not in 'BCX':
                                # in-line constant need to be variable length
                                indx_s = line.index(lbl)
                                __INFO('E', line_num,
                                       ( 41, indx_s, indx_s - 1 + len(lbl), )
                                       )
                ## end of checking arguments

                # check lable
                lbl_8 = '{0:<8}'.format(field[0])
                if lbl_8 in SYMBOL: # duplicated label definition
                    __INFO('E', line_num, ( 43, 0, len(field[0]), ))
                elif ins_lbl == 0:  # valid label
                    SYMBOL[lbl_8] = Symbol(
                        zPE.core.asm.len_op(op_code), addr, scope.id(),
                        '', 'I', '', '',
                        line_num, []
                        )
            # end of checking arguments

            # parsing addr1 and addr2
            op_addr = [ 'pos 0', None, None ]
            for i in range(1, len(op_code)):
                if op_code[i].type in 'LSX': # address type
                    op_addr[op_code[i].pos] = op_code[i]

            MNEMONIC[line_num] = [ scope.id(), addr,            # type 5
                                   op_code, op_addr[1], op_addr[2],
                                   ]
            spt.push( ( line, deck_id, ) )

            # update address
            prev_addr = addr
            length = 0
            for code in op_code:
                length += len(code)
            if length % 2 != 0:
                zPE.abort(91, 'Error: {0}'.format(length / 2),
                          '.5: Invalid OP code length\n')
            addr += length / 2

        # parse macro call
        elif field[1] in MACRO_DEF:
            zPE.mark4future('Macro Expansion')

        # unrecognized op-code
        else:
            indx_s = line.index(field[1])
            __INFO('E', line_num, ( 57, indx_s, indx_s + len(field[1]), ))
            MNEMONIC[line_num] = [ scope.id(), ]                # type 1
            spt.push( ( line, deck_id, ) )
    # end of main read loop

    # remove left-over DSECT from the ESD-index table
    if -1 in ESD_ID:
        del ESD_ID[-1]
    # prepare the offset look-up table of the addresses
    offset = RELOCATE_OFFSET
    for key in sorted(ESD_ID.iterkeys()):
        symbol = ESD[ESD_ID[key]][0]
        if symbol != None and symbol.id == key:
            if symbol.id == 1:  # 1st CSECT
                prev_sym = symbol
            else:               # 2nd or later CSECT
                # calculate the actual offset
                # align to double-word boundary
                offset[symbol.id] = (
                    (offset[prev_sym.id] + prev_sym.length + 7) / 8 * 8
                    )

                # update the pointer
                prev_sym = symbol

    # update symbol address
    for key in ESD:
        if ESD[key][0].id > 0:
            ESD[key][0].addr = offset[ESD[key][0].id]
    for key in SYMBOL:
        if not SYMBOL[key].reloc  and  SYMBOL[key].id > 0:
            SYMBOL[key].value += offset[SYMBOL[key].id]

    # update the address in MNEMONIC table and record them in MNEMONIC_LOC table
    line_num = 0
    prev_scope = None
    tmp_buff = []               # [ line_num, ... ]
    keyed_buff = {}             # { scope_id : tmp_buff, ... }
    for line in spt:
        line_num += 1
        if line_num not in MNEMONIC  or  len(MNEMONIC[line_num]) == 0:
            # comments               or      TITLE statement
            continue
        scope_id = MNEMONIC[line_num][0]        # retrieve scope ID

        if prev_scope == None:
            prev_scope = scope_id

        elif prev_scope != scope_id:
            # scope switched, move tmp buff to keyed buff
            keyed_buff[prev_scope] = tmp_buff
            tmp_buff = []
            prev_scope = scope_id

        if not scope_id:
            continue

        tmp_buff.append(line_num)

        if len(MNEMONIC[line_num]) in [ 2, 3, 5 ]: # type 2/3/5
            if scope_id > 0:
                MNEMONIC[line_num][1] += offset[scope_id] # update loc ptr

            # process tmp_buff
            for i in tmp_buff:
                MNEMONIC_LOC[i] = MNEMONIC[line_num][1]
            tmp_buff = []

            if scope_id in keyed_buff:
                # process keyed_buff
                for i in keyed_buff[scope_id]:
                    MNEMONIC_LOC[i] = MNEMONIC[line_num][1]
                del keyed_buff[scope_id]
    # process leftover keyed_buff, since END will force scope switching
    for scope_id in keyed_buff:
        for i in keyed_buff[scope_id]:
            esd = ESD[ESD_ID[scope_id]][0]
            MNEMONIC_LOC[i] = esd.addr + esd.length
    keyed_buff.clear()

    # update memory requirement for generating OBJECT MODULE
    sz_required = max(
        # get maximum of size from:
        [ # the constant set
            MNEMONIC[ln][1] +   # starting loc  +
            sum([ len(const)    # sum of length of each constant
                  for const in zPE.core.asm.get_sd(MNEMONIC[ln][2])
                  ])
            for ln in MNEMONIC
            if ( len(MNEMONIC[ln]) == 3  and # type 3
                 zPE.core.asm.can_get_sd(MNEMONIC[ln][2])
                 )
            ] + # and
        [ # the instruction set
            MNEMONIC[ln][1] + len(zPE.core.asm.prnt_op(MNEMONIC[ln][2])) / 2
            # starting loc  + length of the mathine code
            for ln in MNEMONIC
            if len(MNEMONIC[ln]) == 5 # type 5
            ] +
        [ 0 ]   # just in case no statement at all
        )
    if not sz_required:
        zPE.abort(9, 'Error: no statement found.\n')
    elif sz_required > zPE.core.mem.max_sz_of(ASM_CONFIG['REGION']):
        zPE.abort(9, 'Error: ', ASM_CONFIG['REGION'],
                  ': RIGEON is not big enough.\n')
    else:
        ASM_CONFIG['MEM_LEN'] = sz_required

    # check cross references table integrality
    for (k, v) in SYMBOL.iteritems():
        if v.defn == None:
            # symbol not defined
            INVALID_SYMBOL.append(k)
    if len(INVALID_SYMBOL):
        rc_symbol = zPE.RC['ERROR']
    else:
        rc_symbol = zPE.RC['NORMAL']

    # check error messages
    if len(INFO['S']):
        rc_err = zPE.RC['SEVERE']
    elif len(INFO['E']):
        rc_err = zPE.RC['ERROR']
    elif len(INFO['W']):
        rc_err = zPE.RC['WARNING']
    elif len(INFO['N']):
        rc_err = zPE.RC['NOTIFY']
    else:
        rc_err = zPE.RC['NORMAL']

    if zPE.debug_mode():
        __PRINT_DEBUG_INFO(1)

    return max(rc_symbol, rc_err)
# end of pass 1


def pass_2():
    spi = zPE.core.SPOOL.retrieve('SYSUT1') # sketch SPOOL (main input)

    # obtain memory for generating Object Module
    mem = zPE.core.mem.Memory(ASM_CONFIG['MEM_POS'], ASM_CONFIG['MEM_LEN'])

    addr = 0                    # program counter
    line_num = 0

    scope_id = 0                # scope id for current line
    prev_scope = None           # scope id for last statement
    pos_start = None            # starting addr for last contiguous machine code
    pos_end   = None            # ending addr for last contiguous machine code

    # append it to ESD records
    __APPEND_ESD([ ESD_ID[1], ESD[ESD_ID[1]][0] ]) # append first ESD entry

    # main read loop
    for line in spi:
        line_num += 1
        if line_num not in MNEMONIC  or  len(MNEMONIC[line_num]) == 0:
            # comment, EJECT, SPACE  or      TITLE statement
            continue
        scope_id = MNEMONIC[line_num][0]        # retrieve scope ID
        if scope_id == None:
            sect_lbl = None
        elif scope_id > 0:
            # CSECT
            sect_lbl = ESD_ID[scope_id]         # retrieve CSECT label
            addr = MNEMONIC_LOC[line_num]       # retrieve address
        elif scope_id < 0:
            # DSECT
            sect_lbl = GET_DSECT_LABEL(line_num)# retrieve DSECT label
            addr = MNEMONIC_LOC[line_num]       # retrieve address
        else:
            pass                # scope = 0, no change to addr

        if scope_id != prev_scope: # swiching scope, append to TXT records
            __APPEND_TXT(mem, prev_scope, pos_start, pos_end)
            # update to new scope (reset "buffer")
            prev_scope = scope_id
            pos_start  = addr
            pos_end    = None

        field = zPE.resplit_sq(r'\s+', line[:-1], 3)

        # skip lines that handled in the first pass
        if len(field) < 2 or len(field[1]) == 0:
            continue            # no op code
        elif field[1] == 'TITLE':
            continue            # TITLE statement

        # parse CSECT
        if field[1] == 'CSECT':
            if ( sect_lbl != '{0:<8}'.format(field[0]) and
                 sect_lbl != '{0:<8}'.format('') # in case of PC
                 ):
                zPE.abort(92, 'Error: Fail to retrieve CSECT label.\n')
            if scope_id != ESD[sect_lbl][0].id:
                zPE.abort(92, 'Error: Fail to retrieve scope ID.\n')

            # append it to ESD records
            __APPEND_ESD([ sect_lbl, ESD[sect_lbl][0] ])

        # parse USING
        elif field[1] == 'USING':
            using_value = None  # for "upgrading" USING to type 2
            if len(field[0]) != 0:
                zPE.mark4future('Labeled USING')
            if len(field) < 3:
                indx_s = line.index(field[1]) + len(field[1]) + 1
                                                                # +1 for ' '
                __INFO('S', line_num, ( 40, indx_s, None, ))
            else:
                args = zPE.resplit(',', field[2], ['(',"'"], [')',"'"])

                # check 1st argument
                sub_args = re.split(',', args[0])
                if len(sub_args) == 1:
                    # regular using
                    range_limit = 4096      # have to be 4096

                    bad_lbl = zPE.bad_label(args[0])
                    if args[0] == '*':
                        # location counter
                        using_value = addr
                        using_scope = scope_id
                    elif bad_lbl == None:
                        # nothing before ','
                        indx_s = line.index(field[2])
                        __INFO('E', line_num,
                               ( 74, indx_s, indx_s + 1 + len(args[1]), )
                               )
                    elif bad_lbl:
                        # not a valid label
                        indx_s = line.index(field[2])
                        __INFO('E', line_num, ( 305, indx_s, None, ))
                    else:
                        # a valid label
                        lbl_8 = '{0:<8}'.format(args[0])
                        if lbl_8 in SYMBOL:
                            SYMBOL[lbl_8].references.append(
                                '{0:>4}{1}'.format(line_num, 'U')
                                )
                            using_value = SYMBOL[lbl_8].value
                            using_scope = SYMBOL[lbl_8].id
                        else:
                            indx_s = line.index(field[2])
                            __INFO('E', line_num,
                                   ( 44, indx_s, indx_s + 1 + len(args[1]), )
                                   )
                else:
                    if len(sub_args) != 2:
                        __INFO('S', line_num, (
                                178,
                                line.index(sub_args[2]),
                                line.index(args[0]) + len(args[0]) - 1,
                                ))
                    # range-limit using
                    zPE.mark4future('Range-Limited USING')

                # check existance of 2nd argument
                if len(args) < 2:
                    indx_s = line.index(field[2]) + len(field[2])
                    __INFO('S', line_num, ( 174, indx_s, indx_s, ))

                # check following arguments
                parsed_args = [ None ] * len(args)
                for indx in range(1, len(args)):
                    reg_info = zPE.core.reg.parse_GPR(args[indx])
                    if reg_info[0] < 0:
                        indx_s = line.index(args[indx])
                        __INFO('E', line_num,
                               ( 29, indx_s, indx_s + len(args[indx]), )
                               )
                        break
                    if reg_info[0] in parsed_args:
                        indx_s = ( line.index(args[indx-1]) +
                                   len(args[indx-1]) + 1 # +1 for ','
                                   )
                        __INFO('E', line_num,
                               ( 308, indx_s, indx_s + len(args[indx]), )
                               )
                        break
                    # register OK, record it
                    parsed_args[indx] = reg_info[0]
                    if reg_info[1]:
                        # a reference to a symbol
                        reg_info[1].references.append(
                            '{0:>4}{1}'.format(line_num, 'U')
                            )

            if not INFO_GE(line_num, 'E'):
                # update using map
                USING_MAP[line_num, parsed_args[1]] = Using(
                    addr, scope_id,
                    'USING',
                    'ORDINARY', using_value, range_limit, using_scope,
                    0, '{0:>5}'.format(''), field[2]
                    )
                ACTIVE_USING[parsed_args[1]] = line_num # start domain of USING

                for indx in range(2, len(args)):
                    USING_MAP[line_num, parsed_args[indx]] = Using(
                        addr, scope_id,
                        'USING',
                        'ORDINARY', using.value + 4096 * (indx - 1),
                        range_limit, using.id,
                        0, '{0:>5}'.format(''), ''
                        )
                    ACTIVE_USING[parsed_args[indx]] = line_num
            # "upgrade" USING
            MNEMONIC_LOC[line_num] = using_value  # record USING location

        # parse DROP
        elif field[1] == 'DROP':
            # update using map
            args = zPE.resplit(',', field[2], ['(',"'"], [')',"'"])
            for indx in range(len(args)):
                reg_info = zPE.core.reg.parse_GPR(args[indx])
                if reg_info[0] < 0:
                    indx_s = line.index(args[indx])
                    __INFO('E', line_num,
                           ( 29, indx_s, indx_s + len(args[indx]), )
                           )
                    continue
                if reg_info[0] in ACTIVE_USING:
                    del ACTIVE_USING[reg_info[0]] # end domain of USING
                    if reg_info[1]:
                        # a reference to a symbol
                        reg_info[1].references.append(
                            '{0:>4}{1}'.format(line_num, 'D')
                            )
                else:
                    indx_s = line.index(args[indx])
                    __INFO('W', line_num,
                           ( 45, indx_s, indx_s + len(args[indx]), )
                           )

        # parse END
        elif field[1] == 'END':
            if len(field) == 3: # has CSECT name
                lbl_8 = '{0:<8}'.format(field[2])
                if lbl_8 in SYMBOL:
                    SYMBOL[lbl_8].references.append(
                        '{0:>4}{1}'.format(line_num, '')
                        )
                else:
                    indx_s = line.index(field[2])
                    __INFO('E', line_num,
                           ( 44, indx_s, indx_s + len(field[2]), )
                           )

                __APPEND_END(lbl_8)
            else:               # has no argument; default to 1st CSECT
                __APPEND_END()

        # parse LTORG
        elif field[1] == 'LTORG':
            if pos_end and pos_start < pos_end: 
                # effective LTORG, append to TXT records
                __APPEND_TXT(mem, prev_scope, pos_start, pos_end)
                prev_scope = None # virtually switch scope to reset "buffer"

        # skip any line that do not need second pass
        elif field[1] in [ 'EQU', ]:
            continue

        # parse DC/DS/=constant
        elif field[1] in [ 'DC', 'DS' ] or field[1][0] == '=':
            if field[1][0] == '=':
                tmp = field[1][1:]
            else:
                tmp = field[2]
            try:
                sd_info = zPE.core.asm.parse_sd(tmp)
            except:
                zPE.abort(91, 'Error: ', tmp, ': Invalid constant.\n')

            # check address const
            if sd_info[0] == 'a' and sd_info[4] != None:
                if sd_info[2] == 'V':
                    # check internal reference
                    for lbl in sd_info[4]:
                        lbl_8 = '{0:<8}'.format(lbl)
                        if lbl_8 in SYMBOL_V: # fully processed in pass 1
                            # append it to ESD records
                            __APPEND_ESD([ lbl_8, ESD[lbl_8][1] ])
                            # add to relocation dictionary
                            RECORD_RL_SYMBOL(
                                scope_id,         # position   ESDID
                                ESD[lbl_8][1].id, # relocation ESDID
                                RelocationEntry(  # relocation entry
                                    addr, 'V', sd_info[3], 'ST'
                                    )
                                )

                elif sd_info[2] == 'A':
                    # check internal reference
                    for lbl_i in range(len(sd_info[4])):
                        # for each 'SYMBOL', try to resolve an address
                        lbl = sd_info[4][lbl_i]
                        sd_info[4][lbl_i] = '0'

                        res = __PARSE_ARG(lbl)

                        if isinstance(res, int):
                            indx_s = line.index(lbl)
                            __INFO('S', line_num,
                                   ( 35, indx_s + res, indx_s + len(lbl), )
                                   )
                            break

                        # check index / base register
                        if res[0][-1] != None:
                            indx_s = line.index(lbl)
                            __INFO('E', line_num,
                                   ( 32, indx_s, indx_s + len(lbl), )
                                   )
                            break

                        reloc_cnt = 0    # number of relocatable symbol
                        reloc_arg = None # backup of the relocatable symbol
                        reloc_neg = [ False ] # if negative of each level of ()
                        reloc_entry = None
                        for indx in range(len(res[0]) - 1):
                            # for each element in the exp, try to envaluate

                            if res[1][indx] == 'parenthesis':
                                if res[0][indx] == '(':
                                    reloc_neg.append(False) # push down 1 level
                                else:
                                    reloc_neg.pop()         # pop  back 1 level
                                continue
                            elif res[1][indx] == 'operator':
                                if res[0][indx] == '-':
                                    reloc_neg[-1] = not reloc_neg[-1]
                                continue

                            if res[1][indx] == 'eq_constant':
                                indx_s = line.index(res[0][indx])
                                __INFO('E', line_num, (
                                        30,
                                        indx_s,
                                        indx_s + len(res[0][indx]),
                                        ))
                                break

                            if ( res[1][indx] == 'location_ptr' or
                                 res[1][indx] == 'valid_symbol'
                                 ):
                                if res[1][indx] == 'location_ptr':
                                    pass # no special process required
                                else:
                                    bad_lbl = zPE.bad_label(res[0][indx])
                                    lbl_8 = '{0:<8}'.format(res[0][indx])

                                    if bad_lbl:
                                        indx_s = line.index(
                                            res[0][indx]
                                            )
                                        __INFO('E', line_num, (
                                                74,
                                                indx_s,
                                                indx_s + len(res[0][indx]),
                                                ))
                                    elif lbl_8 not in SYMBOL:
                                        indx_s = line.index(
                                            res[0][indx]
                                            )
                                        __INFO('E', line_num, (
                                                44,
                                                indx_s,
                                                indx_s + len(res[0][indx]),
                                                ))
                                # check complex addressing
                                if ( ( indx-1 >= 0  and
                                       res[0][indx-1] in '*/()'
                                       ) or
                                     ( indx+1 < len(res[0])-1  and
                                       res[0][indx+1] in '*/()'
                                       ) ):
                                    indx_s = line.index(lbl)
                                    __INFO('E', line_num, (
                                            32,
                                            indx_s,
                                            indx_s + len(lbl),
                                            ))
                                    break
                                reloc_arg = res[0][indx]
                                res[0][indx] = '0'
                                reloc_cnt += 1
                            elif res[1][indx] == 'inline_const':
                                tmp = zPE.core.asm.parse_sd(res[0][indx])
                                if tmp[2] not in 'BCX': # variable length const
                                    indx_s = line.index(
                                        res[0][indx]
                                        )
                                    __INFO('E', line_num, (
                                            41,
                                            indx_s,
                                            indx_s + len(res[0][indx]),
                                            )
                                           )
                                    break
                                elif res[0][indx][0] != tmp[2]: # e.g. 2B'10'
                                    indx_s = line.index(
                                        res[0][indx]
                                        )
                                    __INFO('E', line_num, (
                                            145,
                                            indx_s,
                                            indx_s + len(res[0][indx]),
                                            ))
                                    break
                                elif res[0][indx][1] != "'": # e.g. BL2'1'
                                    indx_s = line.index(
                                        res[0][indx]
                                        )
                                    __INFO('E', line_num, (
                                            150,
                                            indx_s,
                                            indx_s + len(res[0][indx]),
                                            ))
                                    break
                                # parse inline constant, length check required
                                try:
                                    sd = zPE.core.asm.get_sd(tmp)[0]
                                    parsed_addr = zPE.core.asm.X_.tr(sd.dump())
                                    if len(parsed_addr) <= len(
                                        zPE.i2h((2 ** ASM_PARM['AMODE'] - 1))
                                        ):
                                        res[0][indx] = str(int(parsed_addr, 16))
                                    else:
                                        indx_s = line.index(
                                            res[0][indx]
                                            )
                                        __INFO('E', line_num, (
                                                146,
                                                indx_s,
                                                indx_s + len(res[0][indx]),
                                                ))
                                except:
                                    zPE.abort(
                                        92, 'Error: ', res[0][indx],
                                        ': Fail to parse the expression.\n'
                                              )
                            if reloc_cnt > 1: # more than one relocatable symbol
                                indx_s = line.index(lbl)
                                __INFO('E', line_num,
                                       ( 78, indx_s, indx_s + len(lbl), )
                                       )
                                break
                        # end of processing res

                        if INFO_GE(line_num, 'E'):
                            break # if has error, stop processing

                        # calculate constant part
                        if reloc_cnt < 2:
                            try:
                                ex_disp = eval(''.join(res[0][:-1]))
                            except:
                                zPE.abort( 92, 'Error: ', ''.join(res[0][:-1]),
                                           ': Invalid expression.\n'
                                           )
                        # evaluate expression
                        if reloc_cnt == 0:      # no relocatable symbol
                            sd_info[4][lbl_i] = str(ex_disp)
                        elif reloc_cnt == 1:    # one relocatable symbol
                            if reloc_arg == '*':
                                lbl_8 = '*{0}'.format(line_num)
                            else:
                                lbl_8 = '{0:<8}'.format(reloc_arg)

                            sd_info[4][lbl_i] = str(SYMBOL[lbl_8].value)
                            reloc_entry = RelocationEntry(
                                addr, 'A', sd_info[3], '+-'[reloc_neg[-1]]
                                )
                    # end of processing args

                    # update the A-const information
                    if not INFO_GE(line_num, 'E'):
                        MNEMONIC[line_num][2] = (
                            MNEMONIC[line_num][2][:3] + sd_info[3:5] +
                            MNEMONIC[line_num][2][5:]
                            )
                        # add to relocation dictionary
                        if reloc_entry:
                            RECORD_RL_SYMBOL(
                                scope_id,         # position   ESDID
                                SYMBOL[lbl_8].id, # relocation ESDID
                                reloc_entry       # relocation entry
                                )
                # end of parsing A-const

            if INFO_GE(line_num, 'E'):
                # has error(s), skip
                pass
            elif field[1] == 'DC' or field[1][0] == '=':
                # DC/=const, push to memory
                content = ''.join([
                        zPE.core.asm.X_.tr(val.dump())
                        for val in zPE.core.asm.get_sd(MNEMONIC[line_num][2])
                        ])
                mem[mem.min_pos + addr] = content
                pos_end = addr + len(content) / 2
            else:
                if MNEMONIC[line_num][2][1] * MNEMONIC[line_num][2][3]:
                    # effective DS, append to TXT records
                    __APPEND_TXT(mem, prev_scope, pos_start, pos_end)
                    prev_scope = None # virtually switch scope to reset "buffer"

        # parse op-code
        elif zPE.core.asm.valid_op(field[1]):
            op_code = MNEMONIC[line_num][2]
            op_args = zPE.core.asm.op_arg_indx(op_code)

            if op_args:
                args = zPE.resplit(',', field[2], ['(',"'"], [')',"'"])
            else:
                args = ()       # skip argument parsing
            if len(op_args) != len(args):
                continue        # should be processed in pass 1

            # check reference
            for lbl_i in range(len(args)):
                if INFO_GE(line_num, 'E'): # could already be flagged in pass 1
                    break # if has error, stop processing args
                abs_values = False # assume no absolute values

                lbl = args[lbl_i]
                res = __IS_ABS_ADDR(lbl)

                if op_code[op_args[lbl_i]].type in 'LSX' and res != None:
                    # absolute address found
                    abs_values = True

                    equ_info = __PARSE_EQU_VALUE(res[0])
                    if equ_info[0] != None:
                        res[0] = equ_info[0]
                        if equ_info[1]:
                            equ_info[1].references.append(
                                '{0:>4}{1}'.format(line_num, '')
                                )
                    else:
                        res[0] = __REDUCE_EXP(res[0]) # already validated in
                                                      # __IS_ABS_ADDR()
                    # check length
                    if not 0x000 <= res[0] <= 0xFFF:
                        indx_s = line.index(lbl)
                        if '(' in lbl:
                            tmp = lbl.index('(')
                        else:
                            tmp = len(lbl)
                        __INFO('E', line_num,
                               ( 28, indx_s, indx_s + tmp, )
                               )
                        break   # stop processing current res

                    # validate registers
                    if op_code[op_args[lbl_i]].type == 'L':
                        indx_range = [ 1, 2 ] # validate length and base
                        max_len = op_code[op_args[lbl_i]].max_len_length()

                        # ture validation of length
                        equ_info = __PARSE_EQU_VALUE(res[1]) # length @ indx
                        reg_indx = equ_info[0]  # type 'L' will use reg_indx
                                                # instead of res[1]
                        if equ_info[0] != None  and  0 <= reg_indx <= max_len:
                            res[1] =  0 # skip the register check
                            if equ_info[1]:
                                equ_info[1].references.append(
                                    '{0:>4}{1}'.format(line_num, '')
                                    )
                        else:
                            res[1] = -1 # invalidate the register check

                    elif op_code[op_args[lbl_i]].type == 'S':
                        del res[2] # remove the extra item (real base in indx)
                        indx_range = [ 1 ] # only validate indx (real base)

                        if ',' in lbl:
                            indx_s = line.index(lbl)
                            __INFO('S', line_num, (
                                179,
                                indx_s + lbl.index(','),
                                indx_s + len(lbl) + 1,
                                ))
                            break   # stop processing current res
                    else:
                        indx_range = [ 1, 2 ] # validate indx and base

                    if ',' in lbl:
                        indx_os = [ # index offset for error msg generation
                            None,
                            ( lbl.index('('), lbl.index(',') ),
                            ( lbl.index(','), lbl.index(')') ),
                            ]
                    elif '(' in lbl:
                        indx_os = [
                            None,
                            ( lbl.index('('), lbl.index(')') ),
                            None, # no base offered
                            ]
                    else:
                        indx_os = [
                            None,
                            None, # no indx offered
                            None, # no base offered
                            ]
                    for i in indx_range:
                        # validate each register
                        reg_info = zPE.core.reg.parse_GPR(res[i])
                        if reg_info[0] >= 0:
                            res[i] = reg_info[0]
                            if reg_info[1]:
                                reg_info[1].references.append(
                                    '{0:>4}{1}'.format(line_num, '')
                                    )
                        else:
                            indx_s = line.index(lbl) + 1
                            __INFO('E', line_num,
                                   ( 29,
                                     indx_s + indx_os[i][0],
                                     indx_s + indx_os[i][1],
                                     )
                                   )
                            break   # stop processing current res

                elif op_code[op_args[lbl_i]].type == 'R':
                    # register found
                    abs_values = True

                    res = [ lbl ]
                    res[0] = __REDUCE_EXP(lbl)
                    if res[0] == None: # label cannot be reduced
                        res[0] = lbl
                    # validate register
                    reg_info = zPE.core.reg.parse_GPR(res[0])
                    if reg_info[0] >= 0:
                        res[0] = reg_info[0]
                        if reg_info[1]:
                            reg_info[1].references.append(
                                '{0:>4}{1}'.format(
                                    line_num,
                                    op_code[op_args[lbl_i]].flag()
                                    )
                                )
                    else:
                        indx_s = line.index(lbl) + 1
                        __INFO('E', line_num,
                               ( 29, indx_s, indx_s + len(lbl), )
                               )
                        break   # stop processing current res
                else:
                    res = __PARSE_ARG(lbl)
                    if isinstance(res, int):
                        # delimiter error, S035, S173-175, S178-179
                        indx_s = line.index(args[lbl_i])
                        if line[indx_s + res - 1] in ')':
                            if lbl_i < len(op_args) - 1:
                                err_num = 175 # expect comma
                            else:
                                err_num = 173 # expect blank
                        else:
                            err_num = 35 # cannot determine
                        __INFO('S', line_num, (
                                err_num,
                                indx_s + res,
                                indx_s + len(args[lbl_i]),
                                ))
                        break   # stop processing current res

                    reloc_cnt = 0    # number of relocatable symbol
                    reloc_arg = None # backup of the relocatable symbol
                    for indx in range(len(res[0]) - 1):
                        # for each element in the exp, try to envaluate

                        if ( res[1][indx] == 'eq_constant'  or
                             res[1][indx] == 'location_ptr' or
                             res[1][indx] == 'valid_symbol'
                             ):
                            if res[1][indx] == 'eq_constant':
                                if op_code[op_args[lbl_i]].for_write:
                                    indx_s = line.index(res[0][indx])
                                    __INFO('E', line_num, (
                                            30,
                                            indx_s,
                                            indx_s + len(res[0][indx]),
                                            ))
                                    break   # stop processing current res

                                symbol = __HAS_EQ(lbl, scope_id)
                                if symbol == None:
                                    if not INFO_GE(line_num, 'E'):
                                        zPE.abort(91, 'Error: ', lbl,
                                                  ': symbol not in EQ table.\n')
                                elif symbol.defn == None:
                                    zPE.abort(91, 'Error: ', lbl,
                                              ': symbol not allocated.\n')
                            elif res[1][indx] == 'location_ptr':
                                pass # no special process required
                            else: # valid_symbol
                                bad_lbl = zPE.bad_label(res[0][indx])
                                lbl_8 = '{0:<8}'.format(res[0][indx])

                                if ( op_code[op_args[lbl_i]].type == 'S'  and
                                     res[0][-1] != None
                                     ): # S-type arg does not support index reg
                                    indx_s = line.index(lbl)
                                    __INFO('S', line_num, (
                                        173,
                                        indx_s + lbl.index('('),
                                        indx_s + len(lbl) + 1,
                                        ))
                                    break   # stop processing current res
                                elif bad_lbl:
                                    indx_s = (
                                        line.index(res[0][indx])
                                        )
                                    __INFO('E', line_num, (
                                            74,
                                            indx_s,
                                            indx_s + len(res[0][indx]),
                                            ))
                                    break   # stop processing current res
                                elif lbl_8 not in SYMBOL:
                                    indx_s = (
                                        line.index(res[0][indx])
                                        )
                                    __INFO('E', line_num, (
                                            44,
                                            indx_s,
                                            indx_s + len(res[0][indx]),
                                            ))
                                    break   # stop processing current res
                            # check complex addressing
                            if ( ( indx-1 >= 0  and
                                   res[0][indx-1] in '*/()'
                                   ) or
                                 ( indx+1 < len(res[0])-1  and
                                   res[0][indx+1] in '*/()'
                                   ) ):
                                indx_s = line.index(lbl)
                                __INFO('E', line_num, (
                                        32,
                                        indx_s,
                                        indx_s + len(lbl),
                                        ))
                                break   # stop processing current res
                            reloc_arg = res[0][indx]
                            res[0][indx] = '0'
                            reloc_cnt += 1
                        elif res[1][indx] == 'inline_const':
                            sd_info = zPE.core.asm.parse_sd(res[0][indx])
                            if res[0][indx][0] != sd_info[2]: # e.g. 2B'10'
                                indx_s = (
                                    line.index(res[0][indx])
                                    )
                                __INFO('E', line_num, (
                                        145,
                                        indx_s,
                                        indx_s + len(res[0][indx]),
                                        ))
                                break   # stop processing current res
                            elif res[0][indx][1] != "'": # e.g. BL2'1'
                                indx_s = (
                                    line.index(res[0][indx])
                                    )
                                __INFO('E', line_num, (
                                        150,
                                        indx_s,
                                        indx_s + len(res[0][indx]),
                                        ))
                                break   # stop processing current res

                            if not sd_info[5]:
                                sd_info = (sd_info[0], sd_info[1], sd_info[2],
                                           0, sd_info[4], sd_info[3]
                                           )

                        if reloc_cnt > 1: # more than one relocatable symbol
                            indx_s = line.index(lbl)
                            __INFO('E', line_num,
                                   ( 78, indx_s, indx_s + len(lbl), )
                                   )
                            break   # stop processing current res
                # end of processing res
                if INFO_GE(line_num, 'E'):
                    break # if has error, stop processing args

                # calculate constant part for relocatable address
                if not abs_values and reloc_cnt < 2:
                    ex_disp = __REDUCE_EXP(''.join(res[0][:-1]))
                    if ex_disp == None:
                        zPE.abort(92, 'Error: ', ''.join(res[0][:-1]),
                                  ': Invalid expression.\n')

                # evaluate expression
                if abs_values:    # absolute values
                    if op_code[op_args[lbl_i]].type == 'L':
                        op_code[op_args[lbl_i]].set(reg_indx, res[0], res[2])
                    else:
                        op_code[op_args[lbl_i]].set(*res)
                elif reloc_cnt == 0:    # no relocatable symbol
                    try:
                        op_code[op_args[lbl_i]].set(ex_disp)
                    except:
                        indx_s = line.index(lbl)
                        __INFO('E', line_num,
                               ( 29, indx_s, indx_s + len(lbl), )
                               )
                elif reloc_cnt == 1:    # one relocatable symbol
                    if reloc_arg == '*':
                        # current location ptr
                        lbl_8 = '*{0}'.format(line_num)
                        reg_indx = 0
                    elif reloc_arg[0] == '=':
                        # =constant
                        lbl_8 = reloc_arg
                        if op_code[op_args[lbl_i]].type == 'L':
                            reg_indx = __HAS_EQ(lbl_8, scope_id).length
                        else:
                            reg_indx = 0
                    else:
                        # label
                        lbl_8 = '{0:<8}'.format(reloc_arg)
                        reg_indx = res[0][-1]
                        if not reg_indx:
                            if op_code[op_args[lbl_i]].type == 'L':
                                reg_indx = SYMBOL[lbl_8].length
                            else:
                                reg_indx = 0

                    if __IS_ADDRESSABLE(lbl_8, sect_lbl, ex_disp):
                        # update Using Map
                        addr_res = __ADDRESSING(
                            lbl_8, sect_lbl, ex_disp
                            )
                        using = USING_MAP[addr_res[1]]
                        using.max_disp = max(
                            using.max_disp, addr_res[0]
                            )
                        using.last_stmt = '{0:>5}'.format(line_num)
                        # update CR table
                        if reloc_arg == '*':
                            pass # no reference of any symbol
                        else:
                            if reloc_arg[0] == '=':
                                symbol = __HAS_EQ(lbl_8, scope_id)
                            else:
                                symbol = SYMBOL[lbl_8]
                            symbol.references.append(
                                '{0:>4}{1}'.format(
                                    line_num,
                                    op_code[op_args[lbl_i]].flag()
                                    )
                                )
                        if op_code[op_args[lbl_i]].type == 'L':
                            op_code[op_args[lbl_i]].set(
                                reg_indx, addr_res[0], addr_res[2]
                                )
                        elif op_code[op_args[lbl_i]].type == 'S':
                            op_code[op_args[lbl_i]].set(
                                addr_res[0], addr_res[2]
                                )
                        else:
                            op_code[op_args[lbl_i]].set(
                                addr_res[0], reg_indx, addr_res[2]
                                )
                    else:
                        indx_s = line.index(lbl)
                        __INFO('E', line_num,
                               ( 34, indx_s, indx_s + len(lbl), )
                               )

                # check possible alignment error
                if ( not INFO_GE(line_num, 'E')  and
                     not op_code[op_args[lbl_i]].is_aligned(1)
                     ): # no other error, and op code arg require an alignment
                    if not op_code[op_args[lbl_i]].is_aligned():
                        indx_s = line.index(lbl)
                        __INFO('I', line_num,
                               ( 33, indx_s, indx_s + len(lbl), )
                               )
            # end of processing args

            for indx in range(3, 5):
                if MNEMONIC[line_num][indx]:
                    if MNEMONIC[line_num][indx].valid:
                        disp = MNEMONIC[line_num][indx].get()[-1]
                        base = MNEMONIC[line_num][indx].get()[-2]
                        if base in ACTIVE_USING:
                            disp += USING_MAP[ACTIVE_USING[base], base].u_value
                    else:
                        disp = 0
                    MNEMONIC[line_num][indx] = disp

            content = zPE.core.asm.prnt_op(MNEMONIC[line_num][2])
            if not INFO_GE(line_num, 'E'):
                mem[mem.min_pos + addr] = content
            pos_end = addr + len(content) / 2

        # parse macro call
        elif field[1] in MACRO_DEF:
            pass

        # unrecognized op-code
        else:
            pass                # already handled in pass 1
    # end of main read loop

    # append leftover variable fields to ESD records
    __APPEND_ESD()
    # append data fields to RLD records
    for (pos_id, rel_id) in sorted(RLD):
        for entry in RLD[pos_id, rel_id]:
            __APPEND_RLD(pos_id, rel_id, entry)
    __APPEND_RLD()        # append leftover data fields to RLD records


    # check cross references table integrality
    for (k, v) in SYMBOL.iteritems():
        if len(v.references) == 0:
            # symbol not referenced
            NON_REF_SYMBOL.append((v.defn, k, ))


    # check error messages
    if len(INFO['S']):
        rc_err = zPE.RC['SEVERE']
    elif len(INFO['E']):
        rc_err = zPE.RC['ERROR']
    elif len(INFO['W']):
        rc_err = zPE.RC['WARNING']
    elif len(INFO['N']):
        rc_err = zPE.RC['NOTIFY']
    else:
        rc_err = zPE.RC['NORMAL']

    if zPE.debug_mode():
        __PRINT_DEBUG_INFO(2)

    # generate object module if no error occured
    if rc_err <= zPE.RC['WARNING']:
        obj_mod_gen() # write the object module into the corresponding SPOOL

    mem.release()
    return rc_err


def obj_mod_gen():
    spo = zPE.core.SPOOL.retrieve('SYSLIN') # output SPOOL (object module)
    deck = []
    for rec_type in [ 'ESD', 'TXT', 'RLD', 'END', 'SYM' ]:
        deck.extend(OBJMOD[rec_type])

    for rec in deck:
        spo.append(a2b_hex( # compress object module into binary format
                rec + OBJMOD_SEQ(TITLE[0], len(spo) + 1)
                ))

    if zPE.debug_mode():
        obj_dump = zPE.core.SPOOL.new(
            'OBJMOD', 'o', 'file',
            [ 'KC03I6E', 'TONY', 'OBJMOD' ],
            [ 'objmod' ]
            )
        obj_dump.spool = spo.spool
        zPE.flush(obj_dump)

    
### Supporting Functions
def __ADDRESSING(lbl, sect_lbl, ex_disp = 0):
    rv = [ 4096, None, -1, ]  # init to least priority USING (non-exsit)
    eq_const = __HAS_EQ(lbl, ESD[sect_lbl][0].id)

    for (k, v) in ACTIVE_USING.iteritems():
        if __IS_IN_RANGE(lbl, ex_disp, USING_MAP[v,k], ESD[sect_lbl][0]):
            if lbl[0] == '*':
                disp = MNEMONIC[ int( lbl[1:] ) ][1] - USING_MAP[v,k].u_value
            elif lbl[0] == '=':
                disp = MNEMONIC[ eq_const.defn  ][1] - USING_MAP[v,k].u_value
            else:
                disp = MNEMONIC[SYMBOL[lbl].defn][1] - USING_MAP[v,k].u_value
            disp += ex_disp
            if ( ( disp < rv[0] )  or           # minimal displacement rule
                 ( disp == rv[0] and k > rv[2]) # maximal register rule
                 ):
                rv = [ disp, (v, k), k, ]
    return rv

def __HAS_EQ(lbl, scope_id):
    if lbl not in SYMBOL_EQ:
        return None
    for symbol in SYMBOL_EQ[lbl]:
        if symbol.id == scope_id:
            return symbol
    return None                 # nor found

def __IS_ADDRESSABLE(lbl, sect_lbl, ex_disp = 0):
    if (lbl[0] != '*') and (lbl not in SYMBOL) and (lbl not in SYMBOL_EQ):
        return False            # not an *, a symbol, nor a =constant
    if len(ACTIVE_USING) == 0:
        return False            # not in domain of any USING
    for (k, v) in ACTIVE_USING.iteritems():
        if __IS_IN_RANGE(lbl, ex_disp, USING_MAP[v,k], ESD[sect_lbl][0]):
            return True
    return False                # not in the range of any USING

# rv:
#   [ disp_str, indx_str, base_str ]
#   None    if error happened during parsing
#
# Note: no length check nor register validating involved
def __IS_ABS_ADDR(addr_arg):
    reminder = addr_arg

    # parse displacement
    res = re.search(r'\(', reminder)
    if res != None:     # search succeed
        disp     = reminder[:res.start()]
        reminder = reminder[res.end():]
    else:
        disp     = reminder
        reminder = ''
    if not disp:                # (disp exp)(...)
        ( disp, reminder ) = zPE.resplit_pp(r'\)', reminder, 1)
        if not disp:
            return None
    if __REDUCE_EXP(disp) == None: # disp cannot be reduced
        return None

    # parse index
    res = re.search(r'[,)]', reminder)
    if res != None:     # search succeed
        matched_ch = reminder[res.start():res.end()]

        indx = reminder[:res.start()]
        reminder = reminder[res.end():]
        if not indx:
            if matched_ch == ',': # omitted indx
                indx = '0'
            else:                 # nothing in parenthesis
                return None
    else:
        indx = '0'

    # parse base
    res = re.search(r'\)', reminder)
    if res != None:     # search succeed
        base     = reminder[:res.start()]
        reminder = reminder[res.end():]
        if not base:
            base = '0'
    else:
        base = '0'

    # check reminder
    if reminder != '':
        return None
    return [ disp, indx, base ]

def __IS_IN_RANGE(lbl, ex_disp, using, csect):
    u_range = min(
        using.u_value + using.u_range, # ending addr of the USING
        csect.addr + csect.length      # ending addr of the CSECT
        )
    eq_const = __HAS_EQ(lbl, csect.id)

    if lbl[0] == '*':
        # is loc_ptr, encoded disp
        disp = int(lbl[1:])
    elif lbl[0] == '=':
        # is =constant, retrieve definition location
        disp = MNEMONIC[eq_const.defn][1]
    elif SYMBOL[lbl].type != 'U':
        # is symbol, retrieve definition location
        disp = MNEMONIC[SYMBOL[lbl].defn][1]
    else:
        return False

    if using.u_value <= disp + ex_disp < u_range:
        return True
    else:
        return False

def __INFO(err_level, line, item):
    if line not in INFO[err_level]:
        INFO[err_level][line] = []
    INFO[err_level][line].append(item)


def __MISSED_FILE(step):
    sp1 = zPE.core.SPOOL.retrieve('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrieve('JESYSMSG') # SPOOL No. 03
    ctrl = ' '

    cnt = 0
    for fn in FILE_CHK:
        if fn not in zPE.core.SPOOL.list():
            sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
                       '  IEC130I {0:<8}'.format(fn),
                       ' DD STATEMENT MISSING\n')
            sp3.append(ctrl, 'IEC130I {0:<8}'.format(fn),
                       ' DD STATEMENT MISSING\n')

            if fn in FILE_REQ:
                cnt += 1
            else:
                FILE_GEN[fn]()

    return cnt


# rv: ( [ symbol_1, ... ], [ desc_1, ... ], )
# or  err_indx  if error occurs
def __PARSE_ARG(arg_str, bypass_sym = False):
    parts = []                  # components of the expression
    descs = []                  # descriptions of the components

    res = re.match(r".*=[AV]\([^()]+\)", arg_str)
    if res:
        exp_rmndr = arg_str[:res.end()]
        arg_str   = arg_str[res.end():]
    else:
        exp_rmndr = ''

    if re.match(r"(.*(=[AV]\([^()]+\)))*.*\([\w']*,?[\w']*\)", arg_str):
        exp_rmndr += arg_str[:arg_str.rindex('(')]
        idx_rmndr = arg_str[arg_str.rindex('('):]
    else:
        exp_rmndr += arg_str
        idx_rmndr = None
    exp_len = len(exp_rmndr)

    # parse expression part
    res = __PARSE_ARG_RECURSIVE(exp_rmndr)
    if isinstance(res, int):
        return res
    else:
        parts.extend(res[0])
        descs.extend(res[1])

    # parse register part
    if bypass_sym:
        idx_val = 'bypass'
    elif idx_rmndr:
        tmp = zPE.resplit_sq(',', idx_rmndr) # search for ','
        if len(tmp) > 1: # has ','
            return exp_len + len(tmp[0])
        idx_rmndr = idx_rmndr[1:-1] # remove ()
        if not idx_rmndr:           # no value
            return exp_len + 1

        # try parse as a register
        if zPE.core.reg.parse_GPR(idx_rmndr)[0] >= 0:
            idx_val = int(idx_rmndr)
        else:
            # try to reduce the value
            idx_val = __REDUCE_EXP(idx_rmndr)
            if idx_val == None:
                try:
                    idx_val = eval(idx_rmndr)
                except:
                    return exp_len + 1
    else:
        idx_val = None
    parts.append(idx_val)
    descs.append('index_reg')

    return ( parts, descs, )

# used by __PARSE_ARG
def __PARSE_ARG_RECURSIVE(arg_str):
    parts = []                  # components of the expression
    descs = []                  # descriptions of the components

    for part in zPE.resplit('([*/+-])', arg_str, ['(',"'"], [')',"'"]):
        if part.startswith('('):
            if part.endswith(')'):
                res = __PARSE_ARG_RECURSIVE(part[1:-1])
                if isinstance(res, int):
                    return len(''.join(parts)) + res
                else:
                    parts.extend(['('          ] + res[0] + [          ')'])
                    descs.extend(['parenthesis'] + res[1] + ['parenthesis'])
            else:
                return len(''.join(parts)) + len(part) - 1

        elif part in '*/+-':
            parts.append(part)
            descs.append('operator')

        elif part.isdigit():
            parts.append(part)
            descs.append('regular_num')

        elif part.startswith('='):
            parts.append(part)
            descs.append('eq_constant')            

        elif zPE.core.asm.valid_sd(part):
            try:
                sd_info = zPE.core.asm.parse_sd(part)
            except:         # not a constant
                sd_info = None
            if sd_info:
                try:
                    if sd_info[0] == 'a':
                        raise TypeError
                    zPE.core.asm.get_sd(sd_info)
                    parts.append(part)
                    descs.append('inline_const')
                except:     # invalid constant; return err pos
                    return len(''.join(parts))
            else:
                if not zPE.bad_label(part):
                    parts.append(part)
                    descs.append('valid_symbol')
                else:
                    return len(''.join(parts))
        else:
            if not zPE.bad_label(part):
                parts.append(part)
                descs.append('valid_symbol')
            else:
                return len(''.join(parts))
    # check location ptr and form rv
    rv = ([], [])
    rv_skip = False
    for indx in range(len(parts)):
        if rv_skip:
            rv_skip = False
            continue
        if parts[indx] == '*':
            if ( ( indx > 0          and  parts[indx-1] == '' )  and
                 ( indx < len(parts) and  parts[indx+1] == '' )
                 ):
                rv[0].pop()
                rv[1].pop()
                rv[0].append(parts[indx])
                rv[1].append('location_ptr')
                rv_skip = True
            else:
                rv[0].append(parts[indx])
                rv[1].append(descs[indx])
        else:
            rv[0].append(parts[indx])
            rv[1].append(descs[indx])
    return rv


def __PARSE_EQU_VALUE(equ):
    if isinstance(equ, int):
        return ( equ, None, )
    if equ.isdigit():
        return ( int(equ), None, )
    # search for equates
    lbl_8 = '{0:<8}'.format(equ)
    if lbl_8 in SYMBOL  and  SYMBOL[lbl_8].type == 'U':
        return ( SYMBOL[lbl_8].value, SYMBOL[lbl_8], )
    else:
        return ( None, None, )


def __PARSE_OUT():
    spi = zPE.core.SPOOL.retrieve('SYSUT1')   # input SPOOL
    spo = zPE.core.SPOOL.retrieve('SYSPRINT') # output SPOOL

    pln_cnt = 0                 # printed line counter of the current page
    page_cnt = 1                # page counter

    ### header portion of the report
    ctrl = '1'
    spo.append(ctrl, '{0:40} High Level Assembler Option Summary {0:17} (PTF UK28644)   Page {1:>4}\n'.format('', 1))
    ctrl = '-'
    spo.append(ctrl, '{0:>90}  HLASM R5.0  {1}\n'.format(
            ' ', strftime('%Y/%m/%d %H.%M')
            ))
    pln_cnt += 2
    ctrl = '0'


    ### main read loop, op code portion of the report
    ### end of main read loop


    ### summary portion of the report



def __REDUCE_EXP(exp):
    if exp == '':
        return 0

    res = __PARSE_ARG_RECURSIVE(exp)
    if isinstance(res, int):
        return None

    for indx in range(len(res[0])):
        if res[1][indx] == 'inline_const':
            try:
                sd_info = zPE.core.asm.parse_sd(res[0][indx])
                if sd_info[4] == None:  # no (initial) value
                    return None
                if not sd_info[5]:      # no limit on length
                    sd_info = (sd_info[0], sd_info[1], sd_info[2],
                               0, sd_info[4], sd_info[3]
                               )
                (val, dummy) = zPE.core.asm.value_sd(sd_info) # get the value
                res[0][indx] = str(val)
            except:
                return None
        elif res[1][indx] in [ 'eq_constant', 'valid_symbol', 'location_ptr' ]:
            # relocatable value
            return None
    if len(res[0]) == 1:
        val = int(res[0][0])
    else:
        val = eval(''.join(res[0]))
    return val


vf_list = []
csect_encountered = { # this guard the function from appending duplicates
    'ER' : [],
    'SD' : [],
    'PC' : [],
}
def __APPEND_ESD(variable_field = None):
    if variable_field:
        csect_lbl  = variable_field[0]
        csect_type = variable_field[1].type
        if csect_lbl in csect_encountered[csect_type]:
            return
        csect_encountered[csect_type].append(csect_lbl)
        vf_list.append(variable_field)  # append to variable field list

        force_flush = False             # natual append
    else:
        force_flush = len(vf_list)      # force flush if there is any pending vf

    if force_flush  or  len(vf_list) == 3:
        # force flush the list, or the list is full (len = 3)
        if zPE.debug_mode():
            print '** building ESD record with', [ ( k, v.__dict__, )
                                                   for (k,v) in vf_list
                                                   ]
        OBJMOD['ESD'].append( OBJMOD_REC['ESD'](vf_list) )
        del vf_list[:]                  # clear variable field list


def __APPEND_TXT(mem, scope, pos_start, pos_end):
    if ( scope < 0         or   # None is also considered '< 0'
         pos_start == None or
         pos_end == None   or
         pos_start >= pos_end
         ):
        return                  # no need to append, early return

    p_s = pos_start
    p_e = min(pos_end, p_s + 56) # 56 Byte per TXT
    while p_s < p_e:
        content = mem[mem.min_pos + p_s : mem.min_pos + p_e]
        if zPE.debug_mode():
            print '** building TXT record (scope', scope, ') with', content
        OBJMOD['TXT'].append( OBJMOD_REC['TXT'](scope, p_s, content) )
        p_s = p_e
        p_e = min(pos_end, p_s + 56 * 2)


df_list = []
df_list_memory = {
    'byte_cnt' : 0,
    'pos_id'   : None,
    'rel_id'   : None,
    }
def __APPEND_RLD(pos_id = None, rel_id = None, data_field = None):
    if data_field:
        # append to data field list
        if ( df_list and        # there is pending df in the list
             pos_id == df_list_memory['pos_id'] and
             rel_id == df_list_memory['rel_id']
             ):
            # same as previous one, use pack format
            df_list.append([ 4, data_field ])
        else:
            # scope changed, use full format and record the change
            df_list.append([ 8, data_field, pos_id, rel_id ])
            df_list_memory['pos_id'] = pos_id
            df_list_memory['rel_id'] = rel_id
        df_list_memory['byte_cnt'] += df_list[-1][0] # update byte counter
        force_flush = False             # natual append
    else:
        force_flush = len(df_list)      # force flush if there is any pending df

    if force_flush  or  df_list_memory['byte_cnt'] == 56:
        # force flush the list, or the list is full (len = 56)
        if zPE.debug_mode():
            print '** building RLD record with', df_list
        OBJMOD['RLD'].append( OBJMOD_REC['RLD'](df_list) )
        del df_list[:]                 # clear data field list
        df_list_memory['byte_cnt'] = 0 # reset byte counter

    elif df_list_memory['byte_cnt'] > 56:
        # the list is overflowed
        if zPE.debug_mode():
            print '** building RLD record with', df_list[:-1]
        OBJMOD['RLD'].append( OBJMOD_REC['RLD'](df_list[:-1]) )
        del df_list[:]                 # clear data field list
        df_list.append([ 8, data_field, pos_id, rel_id ]) # push back last one
        df_list_memory['byte_cnt'] = 8


def __APPEND_END(entry_csect = None):
    if entry_csect:             # type 1 END
        entry = ESD[entry_csect][0]
        entry_pt = entry.addr
        entry_id = entry.id
        entry_sb = ''
    else:                       # type 2 END
        entry_pt = ''
        entry_id = ''
        entry_sb = ASM_PARM['ENTRY']

    asm_time = localtime()
    if zPE.debug_mode():
        print '** building END record with ENTRY =', entry_pt
    OBJMOD['END'].append(OBJMOD_REC['END'](
            entry_pt, entry_id, entry_sb,
            '',                 # need info
            [ {                 # need info
                    'translator id' : '569623400', # need info
                    'ver + release' : '0105',      # need info
                    'assembly date' : '{0}{1}'.format(
                        asm_time.tm_year, asm_time.tm_yday
                        )[-5:]  # yy[yyddd]
                    },
              ]
            ))


def __PRINT_DEBUG_INFO(phase):
    print
    print '*** HL-ASM Pass {0} Finished ***'.format(phase)

    __PRINT_ASM_ESD()
    if phase == 2:
        __PRINT_ASM_RLD()
        __PRINT_ASM_SCRT()
        __PRINT_ASM_UM()
    __PRINT_ASM_DCR()
    __PRINT_ASM_MSG()


def __PRINT_ASM_ESD():
    print '\nExternal Symbol Dictionary:'
    for key in sorted(ESD_ID.iterkeys()):
        k = ESD_ID[key]
        if ESD[k][0] and ESD[k][0].id == key:
            v = ESD[k][0]
        else:
            v = ESD[k][1]
        print '{0} => {1}'.format(k, v.__dict__)

def __PRINT_ASM_RLD():
    print '\nRelocation Dictionary:'
    print' Pos.Id   Rel.Id   Address  Type  Action'
    for (pos_id, rel_id) in sorted(RLD):
        for entry in RLD[pos_id, rel_id]:
            print '{0:0>8} {1:0>8} {2:0>8}   {3} {4}  {5:>4}'.format(
                zPE.i2h(pos_id), zPE.i2h(rel_id), zPE.i2h(entry.addr),
                entry.type,      entry.len,       entry.action
                )

def __PRINT_ASM_SCRT():
    print '\nSymbol Cross Reference Table:'
    for key in sorted(SYMBOL.iterkeys()):
        if SYMBOL[key].value == None:
            addr = 0xFFFFFF
        else:
            addr = SYMBOL[key].value
        print '{0} (0x{1:0>6}) => {2}'.format(
            key, zPE.i2h(addr), SYMBOL[key].__dict__
            )
    print '\nSymbol Cross Reference ER Sub-Table:'
    for key in sorted(SYMBOL_V.iterkeys()):
        if SYMBOL_V[key].value == None:
            addr = 0xFFFFFF
        else:
            addr = SYMBOL_V[key].value
        print '{0} (0x{1:0>6}) => {2}'.format(
            key, zPE.i2h(addr), SYMBOL_V[key].__dict__
            )
    print '\nSymbol Cross Reference =Const Sub-Table:'
    for key in sorted(SYMBOL_EQ.iterkeys()):
        for indx in range(len(SYMBOL_EQ[key])):
            if SYMBOL_EQ[key][indx].value == None:
                addr = 0xFFFFFF
            else:
                addr = SYMBOL_EQ[key][indx].value
            print '{0} (0x{1:0>6}) => {2}'.format(
                key, zPE.i2h(addr), SYMBOL_EQ[key][indx].__dict__
                )
    print '\nUnreferenced Symbol Defined in CSECTs:'
    for (ln, key) in sorted(NON_REF_SYMBOL, key = lambda t: t[1]):
        print '{0:>4} {1}'.format(ln, key)
    print '\nInvalid Symbol Found in CSECTs:'
    for (ln, key) in sorted(INVALID_SYMBOL, key = lambda t: t[1]):
        print '{0:>4} {1}'.format(ln, key)

def __PRINT_ASM_UM():
    print '\nUsing Map:'
    for (k, v) in USING_MAP.iteritems():
        print k, v.__dict__

def __PRINT_ASM_DCR():
    print '\nDSECT Cross Reference:'
    for (k, ls, le) in DSECT_CR:
        print '{0} (ln: {1:>4} ~ {2:<4}) => {3}'.format(
            k, ls, le, ESD[k][0].__dict__
            )

def __PRINT_ASM_MSG():
    __PRINT_ASM_MSG_FOR('Infomation')
    __PRINT_ASM_MSG_FOR('Notification')
    __PRINT_ASM_MSG_FOR('Warning')
    __PRINT_ASM_MSG_FOR('Error')
    __PRINT_ASM_MSG_FOR('Severe Error')

def __PRINT_ASM_MSG_FOR(level):
    print '\n{0}:'.format(level),
    level = level[0]            # first char is index into INFO dict
    if len(INFO[level]):
        print
        for line_num in INFO[level]:
            print 'line {0} => {1}'.format(line_num, INFO[level][line_num])
    else:
        print 'N/A'
