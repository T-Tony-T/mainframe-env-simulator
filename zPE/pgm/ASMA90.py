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
#     
# Return Value:
#     none
################################################################


import zPE

import os, sys
import re
from time import localtime, mktime, strftime, strptime


FILE = [ 'SYSIN', 'SYSLIB', 'SYSPRINT', 'SYSLIN', 'SYSUT1' ]

INFO = {                # { Line_Num : 'message' }
    'WARNING'  : {},            # warning message below where it occurs
    'ERROR'    : {},            # error message below where it occurs
    }

MNEMONIC = {
    # Line_Num : [ scope, ]                                     // type (len) 1
    # Line_Num : [ scope, LOC, ]                                // type (len) 2
    # Line_Num : [ scope, LOC, [CONST_OBJECTs], ]               // type (len) 3
    # Line_Num : [ scope, LOC, (OBJECT_CODE), ADDR1, ADDR2, ]   // type (len) 5
    }

RELOCATE_OFFSET = {
    1 : 0,                      # { scope_id : offset }
    }

class ExternalSymbol(object):
    def __init__(self, tp, scope_id, addr, length,
                 owner, flags, alias
                 ):
        self.type = tp
        self.id = scope_id
        self.addr = addr
        self.length = length
        self.owner = owner
        self.flags = flags
        self.alias = alias

class Symbol(object):
    def __init__(self, length, addr, scope_id,
                 r_type, asm, program,
                 line_cnt, references
                 ):
        self.length = length
        self.value = addr
        self.id = scope_id
        self.r_type = r_type
        self.asm = asm
        self.program = program
        self.defn = line_cnt
        self.references = references

ESD = {                 # External Symbol Dictionary; build during pass 1
    # 'Symbol  ' : ( ExternalSymbol(SD/PC), ExternalSymbol(ER), )
    }
ESD_ID = {              # External Symbol Dictionary ID Table
    # scope_id : 'Symbol  '
    }
SYMBOL = {              # Cross Reference Table; build during pass 1
    # 'Symbol  ' : Symbol()
    }
SYMBOL_V = {            # Cross Reference Sub-Table
    # 'Symbol  ' : Symbol()
    }

def init(step):
    # check for file requirement
    if __MISSED_FILE(step) != 0:
        return zPE.RC['SEVERE']

    rc1 = pass_1()
    if rc1 < zPE.RC['ERROR']:
        rc2 = pass_2()
    else:
        rc2 = rc1

    __PARSE_OUT()

    return max(rc1, rc2)


def pass_1():
    spi = zPE.core.SPOOL.retrive('SYSIN')    # input SPOOL
    spt = zPE.core.SPOOL.retrive('SYSUT1')   # sketch SPOOL

    addr = 0                    # program counter
    line_num = 0

    scope_id = 0                # current scope ID; init to None (0)
    scope_new = scope_id + 1    # next available scope ID; starting at 1
    csect_lbl = None            # current csect label

    const_pool = None           # memory heap for constant allocation

    spi.terminate()             # manually append an EOF at the end, which
                                # will be removed before leave 1st pass

    # main read loop
    for line in spi:
        line_num += 1           # start at line No. 1

        # check EOF
        if spi.atEOF(line):
            INFO['WARNING'][line_num] = 'W-END MISSING'
            # replace EOF with an END instruction
            spi.unterminate()   # this indicates the generation of the END
            line = '{0:<8} END\n'.format(' ')
            spi.append(line)    # will be removed when encountered

        # check comment
        if line[0] == '*':
            continue

        field = zPE.resplit_sq('\s+', line[:-1], 3)

        # check for OP code
        if len(field) < 2:
            INFO['ERROR'][line_num] = 'OP-CODE MISSING'

            MNEMONIC[line_num] = [ scope_id, addr, ]            # type 2
            spt.append('{0:0>5}{1:<8}\n'.format(
                    line_num, field[0]
                    ))                

        # parse CSECT
        elif field[1] == 'CSECT':
            # update the CSECT info
            if scope_id:        # if not first CSECT
                ESD[csect_lbl][0].length = addr

            bad_lbl = zPE.bad_label(field[0])
            if bad_lbl == None:
                csect_lbl = '{0:<8}'.format(' ') # PC symbol
            elif bad_lbl:
                INFO['ERROR'][line_num] = 'INVALID SYMBOL'
                csect_lbl = '{0:<8}'.format(' ') # treat as PC symbol
            else:
                csect_lbl = '{0:<8}'.format(field[0])

            # parse the new CSECT
            scope_id = scope_new
            scope_new += 1      # update the next scope_id ptr
            addr = 0            # reset program counter; not fixed yet

            if csect_lbl not in ESD:
                ESD[csect_lbl] = (
                    ExternalSymbol(
                        None, None, None, None,
                        None, None, None,
                        ),
                    ExternalSymbol(
                        None, None, None, None,
                        None, None, None,
                        ),
                    )

            if ESD[csect_lbl][0].id != None:
                # continued CSECT, switch to it
                scope_id = ESD[csect_lbl][0].id
                scope_new -= 1  # roll back the next scope id
                addr = ESD[csect_lbl][0].length
            else:
                # new CSECT, update info
                ESD[csect_lbl][0].id = scope_id
                ESD[csect_lbl][0].addr = addr
                ESD[csect_lbl][0].flags = '00'

                ESD_ID[scope_id] = csect_lbl

                if csect_lbl == '{0:<8}'.format(' '):
                    # unlabelled symbol
                    ESD[csect_lbl][0].type = 'PC'
                else:
                    # labelled symbol
                    ESD[csect_lbl][0].type = 'SD'

                    SYMBOL[csect_lbl] = Symbol(
                        1, addr, scope_id,
                        'J', ' ', ' ',
                        line_num, []
                        )

            MNEMONIC[line_num] = [ scope_id, addr, ]            # type 2
            spt.append('{0:0>5}{1:<8} CSECT\n'.format(
                    line_num, field[0]
                    ))
                
        # parse USING
        elif field[1] == 'USING':
            if len(field[0]) != 0:
                INFO['ERROR'][line_num] = 'LABEL NOT ALLOWED'
            if len(field) < 3:
                INFO['ERROR'][line_num] = 'MISSING OPERAND'
            else:
                args = zPE.resplit_sp(',', field[2])


                # mark
                lbl_8 = '{0:<8}'.format(args[0])
                if len(args) < 2:
                    INFO['ERROR'][line_num] = 'INVALID DELIMITER'
                elif SYMBOL[lbl_8].id > 0 and SYMBOL[lbl_8].id != scope_id:
                    pass        # err msg
                else:
                    SYMBOL[lbl_8].references.append(
                        '{0:>4}{1}'.format(line_num, 'U')
                        )

            MNEMONIC[line_num] = [ scope_id, addr, ]            # type 2
            spt.append('{0:0>5}{1:<8} USING {2}\n'.format(
                    line_num , ' ', field[2]
                    ))

        # parse END
        elif field[1] == 'END':
            if const_pool:      # check left-over constants
                line_num_tmp = line_num - 1
                for lbl in SYMBOL:
                    if lbl[0] == '=' and SYMBOL[lbl].defn == None:
                        spi.insert(line_num_tmp,
                                   '{0:<14} {1}\n'.format(' ', lbl)
                                   )
                        line_num_tmp += 1
                const_pool = None   # close the current pool
                # the following is to "move back" the iterator
                # need to be removed after END
                spi.insert(0, '')
                line_num -= 1
            else:               # no left-over constant, end the program
                if len(field[0]) != 0:
                    pass            # err msg

                # update the CSECT info
                ESD[csect_lbl][0].length = addr

                if len(field) == 3: # has label
                    lbl_8 = '{0:<8}'.format(field[2])
                else:               # has no label; default to 1st CSECT
                    lbl_8 = ESD_ID[1]
                if lbl_8 in SYMBOL:
                    SYMBOL[lbl_8].references.append(
                        '{0:>4}{1}'.format(line_num, ' ')
                        )
                addr = 0    # reset program counter

                # check EOF again
                if spi.atEOF():
                    # no auto-generation of END
                    spi.unterminate()

                    MNEMONIC[line_num] = [ 0, addr, ]           # type 2
                                # the scope ID of END is always set to 0
                    spt.append('{0:0>5}{1:<8} END   {2}\n'.format(
                            line_num, ' ', lbl_8
                            ))
                else:
                    # END auto-generated, remove it
                    spi.rmline(-1)

                # remove the dummy line added in the previous branch
                if spi[0] == '':
                    spi.rmline(0)
                break           # end of program

        # parse LTORG
        elif field[1] == 'LTORG':
            curr_pool = [
                [],     # pool for constant with double-word alignment
                [],     # pool for constant with full-word alignment
                [],     # pool for constant with half-word alignment
                [],     # pool for constant with byte alignment
                ]
            for lbl in SYMBOL:
                if lbl[0] == '=' and SYMBOL[lbl].defn == None:
                    # current pool
                    alignment = zPE.core.asm.align_at(lbl[1])
                    for i in range(0,3):
                        if alignment == 2 ** i:
                            curr_pool[3 - i].append(lbl)
                            break

            line_num_tmp = line_num
            for pool in curr_pool:
                for lbl in pool:
                    spi.insert(line_num_tmp, '{0:<15}{1}\n'.format(' ', lbl))
                    line_num_tmp += 1

            const_pool = None   # close the current pool
            MNEMONIC[line_num] = [ scope_id, addr, ]            # type 2
            spt.append('{0:0>5}{1:<8} LTORG\n'.format(line_num, ' '))

        # parse DC/DS/=constant
        elif field[1] in ['DC', 'DS'] or field[1][0] == '=':
            try:
                if field[1][0] == '=':
                    sd_info = zPE.core.asm.parse_sd(field[1][1:])
                else:
                    sd_info = zPE.core.asm.parse_sd(field[2])
            except:
                print '-----------------'
                continue        # err msg

            # check =constant
            if field[1][0] == '=':
                if field[1] in SYMBOL:
                    symbol = SYMBOL[field[1]]
                    if symbol.defn == None and symbol.id == scope_id:
                        symbol.length = sd_info[3]
                        symbol.value = addr
                        symbol.r_type = sd_info[2]
                        symbol.defn = line_num
                    else:
                        pass    # err msg

            if sd_info[0] == 'a' and sd_info[4] != None:
                # check references
                for lbl in sd_info[4]:
                    if re.match('[A-Z@#$]', lbl[0]): # is a symbol
                        bad_lbl = zPE.bad_label(lbl)
                        lbl_8 = '{0:<8}'.format(lbl)

                        if bad_lbl:
                            pass # err msg
                        elif sd_info[2] == 'A':
                            if lbl_8 in SYMBOL:
                                # check scope
                                symbol = SYMBOL[lbl_8]
                                if symbol.id == scope_id:
                                    symbol.references.append(
                                        '{0:>4}{1}'.format(line_num, ' ')
                                        )
                                else:
                                    pass # duplicated symbol
                            else:
                                SYMBOL[lbl_8] = Symbol(
                                    None, None, scope_id,
                                    None, None, None,
                                    None, [ '{0:>4}{1}'.format(line_num, ' '), ]
                                    )
                        elif sd_info[2] == 'V':
                            # update the Cross-References Sub-Table
                            if lbl_8 not in SYMBOL_V:
                                SYMBOL_V[lbl_8] = Symbol(
                                    1, 0, scope_id,
                                    'T', ' ', ' ',
                                    line_num, [ ]
                                    )
                            SYMBOL_V[lbl_8].references.append(
                                '{0:>4}{1}'.format(line_num, ' ')
                                )

                            # update the External Symbol Dictionary
                            if lbl_8 not in ESD:
                                ESD[lbl_8] = (
                                    ExternalSymbol(
                                        None, None, None, None,
                                        None, None, None,
                                        ),
                                    ExternalSymbol(
                                        None, None, None, None,
                                        None, None, None,
                                        ),
                                    )

                            if ESD[lbl_8][1].id == None:
                                ESD[lbl_8][1].type = 'ER'
                                ESD[lbl_8][1].id = scope_new

                                ESD_ID[scope_new] = lbl_8
                                scope_new += 1 # update the next scope_id ptr
                        else:
                            sys.stderr.write('Error: {0}'.format(sd_info[2]) +
                                             ': Invalid address type.\n')
                            sys.exit(10)
            # check lable
            bad_lbl = zPE.bad_label(field[0])
            lbl_8 = '{0:<8}'.format(field[0])
            if bad_lbl == None:
                pass        # no label detected
            elif bad_lbl:
                pass        # err msg
            elif lbl_8 in SYMBOL:
                symbol = SYMBOL[lbl_8]
                if symbol.defn == None and symbol.id == scope_id:
                    symbol.length = sd_info[3]
                    symbol.value = addr
                    symbol.r_type = sd_info[2]
                    symbol.asm = sd_info[2]
                    symbol.program = ' '
                    symbol.defn = line_num
                else:
                    pass        # duplicated symbol
            else:
                SYMBOL[lbl_8] = Symbol(
                    sd_info[3], addr, scope_id,
                    sd_info[2], sd_info[2], ' ',
                    line_num, []
                    )

            # align boundary
            alignment = zPE.core.asm.align_at(sd_info[2])
            addr = (addr + alignment - 1) / alignment * alignment

            if field[1] == 'DS':
                MNEMONIC[line_num] = [ scope_id, addr, ]        # type 2
            else:
                MNEMONIC[line_num] = [ scope_id, addr,          # type 3
                                       zPE.core.asm.get_sd(sd_info),
                                       ]
            if field[1][0] == '=':
                spt.append('{0:0>5}{1}'.format(line_num, line))
            else:
                spt.append('{0:0>5}{1:<8} {2:<5} {3}\n'.format(
                        line_num, field[0], field[1], field[2]
                        ))

            # update address
            addr += sd_info[1] * sd_info[3]

        # parse op-code
        elif zPE.core.asm.valid_op(field[1]):
            op_code = zPE.core.asm.get_op(field[1])
            args = zPE.resplit_sp(',', field[2])

            if len(op_code) != len(args) + 1:
                INFO['ERROR'][line_num] = 'UNMATCHED ARGUMENTS'
                arg_list = field[2] + ','
            else:
                # check reference
                arg_list = ''
                arg_indx = 0    # index used for op_code
                for lbl in args:
                    arg_indx += 1 # start at 1, since op_code = ('xx', ...)

                    if lbl[0] == '=':
                        # parse =constant, op_code not filled
                        if not const_pool:
                            # allocate new pool
                            const_pool = scope_id

                        if scope_id != const_pool:  # invalid pool

                            pass    # err msg
                        else:                       # valid pool
                            if lbl in SYMBOL:
                                SYMBOL[lbl].references.append(
                                    '{0:>4}{1}'.format(line_num, ' ')
                                    )
                            elif zPE.core.asm.valid_sd(lbl[1:]):
                                SYMBOL[lbl] = Symbol(
                                    None, None, const_pool,
                                    lbl[1], ' ', ' ',
                                    None, [
                                        '{0:>4}{1}'.format(line_num, ' '),
                                        ]
                                    )
                            else:
                                pass # err msg
                        arg_list += lbl + ','
                    elif re.match('[A-Z@#$]', lbl[0]):
                        if zPE.core.asm.valid_sd(lbl):
                            # try parse in-line constant,
                            # op_code filled on success
                            try:
                                sd_info = zPE.core.asm.parse_sd(lbl)
                                arg_val = zPE.core.asm.value_sd(sd_info)
                                op_code[arg_indx].set(arg_val)

                                arg_list += '{0},'.format(arg_val)
                                continue # is in-line constant, skip label
                            except:
                                pass     # is not in-line constant, check label

                        # parse label, op_code not filled
                        bad_lbl = zPE.bad_label(lbl)
                        lbl_8 = '{0:<8}'.format(lbl)
                        if bad_lbl:
                            pass        # err msg
                        elif lbl_8 in SYMBOL:
                            # check scope
                            symbol = SYMBOL[lbl_8]
                            if symbol.id == scope_id:
                                symbol.references.append(
                                    '{0:>4}{1}'.format(
                                        line_num, zPE.core.asm.type_op(op_code)
                                        )
                                    )
                            else:
                                pass        # duplicated symbol
                        else:
                            SYMBOL[lbl_8] = Symbol(
                                None, None, scope_id,
                                None, None, None,
                                None, [
                                    '{0:>4}{1}'.format(
                                        line_num, zPE.core.asm.type_op(op_code)
                                        ),
                                    ]
                                )
                        arg_list += lbl + ','
                    else:
                        # try parse integer string,
                        # op_code filled on success
                        try:
                            int_val = int(lbl)
                            op_code[arg_indx].set(int_val)
                        except:
                            pass
                        arg_list += lbl + ','
                ## end of checking references

                # check lable
                bad_lbl = zPE.bad_label(field[0])
                lbl_8 = '{0:<8}'.format(field[0])
                if bad_lbl == None:
                    pass        # no label detected
                elif bad_lbl:
                    pass        # err msg
                elif lbl_8 in SYMBOL:
                    symbol = SYMBOL[lbl_8]
                    if symbol.defn == None and symbol.id == scope_id:
                        symbol.length = zPE.core.asm.len_op(op_code)
                        symbol.value = addr
                        symbol.r_type = 'I'
                        symbol.asm = ' '
                        symbol.program = ' '
                        symbol.defn = line_num
                    else:
                        pass        # duplicated symbol
                else:
                    SYMBOL[lbl_8] = Symbol(
                        zPE.core.asm.len_op(op_code), addr, scope_id,
                        'I', ' ', ' ',
                        line_num, []
                        )
            # fi

            MNEMONIC[line_num] = [ scope_id, addr,              # type 5
                                   op_code, '', '',
                                   ]
            spt.append('{0:0>5}{1:<8} {2:<5} {3}\n'.format(
                    line_num, field[0], field[1], arg_list[:-1]
                    ))

            # update address
            length = 0
            for code in op_code:
                length += len(code)
            if length % 2 != 0:
                sys.stderr.write('Error: {0}'.format(length / 2) +
                                 '.5: Invalid OP code length\n')
                sys.exit(5)
            addr += length / 2

        # unrecognized op-code
        else:
            INFO['ERROR'][line_num] = 'INVALID OP CODE'
            MNEMONIC[line_num] = [ scope_id, ]                  # type 1
            spt.append('{0:0>5}{1}'.format(line_num, line))
    # end of main read loop

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

    # check cross references table integrality
    invalid_symbol = 0
    for k,v in SYMBOL.items():
        if v.defn == None:
            invalid_symbol += 1
            pass                # symbol not defined
        if len(v.references) == 0:
            pass                # symbol not referenced

############ test only
    for line in spt.spool:
        print line[:-1]
############ test only

    if invalid_symbol:
        return zPE.RC['ERROR']
    else:
        return zPE.RC['NORMAL']
# end of pass 1


def pass_2():
    spt = zPE.core.SPOOL.retrive('SYSUT1')   # sketch SPOOL
############ test only
    for line in spt.spool:
        print line[:-1]
    return 0
############ test only

    # main read loop
    line_num = 0                     # line number
    for line in spt:
        line_num += 1                # start at line No. 1

        if line[0] == '*':      # is comment
            continue

        field = re.split('\s+', line[:-1])

        # parse CSECT
        if field[1] == 'CSECT':
            scope_id = ESD[field[0]][0].id

        # parse USING
        elif field[1] == 'USING':
            args = re.split(',', field[2])
            # set addressibility

        # parse END
        elif field[1] == 'END':
            break               # end of program

        # parse op-code
        elif zPE.core.asm.valid_op(field[1]):
            op_code = zPE.core.asm.get_op(field[1])
            num = len(op_code) - 1      # number of arguments to be parsed
            args = zPE.resplit_sp(',', field[2])
            if len(args) != num:
                pass            # err msg
            else:
                for i in range(num):
                    arg = args[i] # parsing needed
                    op_code[i+1].set(arg)

        # parse DC/DS/=constant
        elif field[1] in ['DC', 'DS'] or field[1][0] == '=':
            pass



    # end of main read loop

    return zPE.RC['NORMAL']


### Supporting Functions
def __MISSED_FILE(step):
    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrive('JESYSMSG') # SPOOL No. 03
    ctrl = ' '

    cnt = 0
    for fn in FILE:
        if fn not in zPE.core.SPOOL.list():
            sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
                       '  IEC130I {0:<8}'.format(fn), 
                       ' DD STATEMENT MISSING\n')
            sp3.append(ctrl, 'IEC130I {0:<8}'.format(fn),
                       ' DD STATEMENT MISSING\n')
            cnt += 1

    return cnt


def __PARSE_OUT():
    spi = zPE.core.SPOOL.retrive('SYSIN')    # input SPOOL
    spt = zPE.core.SPOOL.retrive('SYSUT1')   # sketch SPOOL
    spo = zPE.core.SPOOL.retrive('SYSPRINT') # output SPOOL

    pln_cnt = 0                 # printed line counter of the current page
    page_cnt = 1                # page counter

    ctrl = '1'
    spo.append(ctrl, '{0:>40} High Level Assembler Option Summary                   (PTF UK28644)   Page {1:>4}\n'.format(' ', 1))
    ctrl = '-'
    spo.append(ctrl, '{0:>90}  HLASM R5.0  {1}\n'.format(
            ' ', strftime('%Y/%m/%d %H.%M')
            ))
    pln_cnt += 2
    ctrl = '0'
