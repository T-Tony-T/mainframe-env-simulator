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

INFO = {                # { Line_No : 'message' }
    'TRAN'    : {},             # the machine code translation ahead of src
    'WARNING' : {},             # warning message below where it occurs
    'ERROR'   : {},             # error message below where it occurs
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
    # 'Symbol' : ExternalSymbol()
    }
SYMBOL = {              # Cross Reference table; build during pass 1
    # 'Symbol' : Symbol()
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

    # main read loop
    cnt = 0                     # line number
    addr = 0                    # address
    scope_id = 0
    for line in spi:
        cnt += 1                # start at line No. 1
        if line[0] == '*':      # is comment
            continue

        field = re.split('\s+', line[:-1], 3)

        # parse CSECT
        if field[1] == 'CSECT':
            scope_id += 1
            # check lable
            bad_lbl = zPE.bad_label(field[0])
            if bad_lbl == None:
                pass            # err msg
            elif bad_lbl:
                pass            # err msg
            elif field[0] in SYMBOL:
                pass            # duplicated label
            else:
                ESD[field[0]] = ExternalSymbol(
                    'SD', scope_id, addr, 0,
                    ' ', '00', ' '
                    )
                SYMBOL[field[0]] = Symbol(
                    1, addr, scope_id,
                    'J', ' ', ' ',
                    cnt, []
                    )
            spt.append('{0:0>5}{1:<8} CSECT\n'.format(cnt, field[0]))

        # parse USING
        elif field[1] == 'USING':
            if len(field[0]) != 0:
                pass            # err msg
            if len(field) < 3:
                pass            # err msg
            else:
                args = re.split(',', field[2])
                if len(args) != 2:
                    pass        # err msg
                elif SYMBOL[args[0]].id not in [int('FFFFFFFF', 16), scope_id]:
                    pass        # err msg
                else:
                    SYMBOL[args[0]].references.append(
                        '{0:>4}{1}'.format(cnt, 'U')
                        )
            spt.append('{0:0>5}{1:<8} USING {2}\n'.format(cnt ,' ', field[2]))

        # parse END
        elif field[1] == 'END':
            if len(field[0]) != 0:
                pass            # err msg
            if len(field) < 3:
                pass            # err msg
            else:
                if ESD[field[2]] != 1:
                    pass        # err msg
                else:
                    SYMBOL[args[0]].references.append(
                        '{0:>4}{1}'.format(cnt, ' ')
                        )
            spt.append('{0:0>5}{1:<8} END   {2}\n'.format(cnt, ' ', field[2]))
            break               # end of program

        # parse op-code
        elif zPE.core.asm.valid_op(field[1]):
            op_code = zPE.core.asm.get_op(field[1])
            args = __PARSE_ARGS(field[2])
            # check reference
            arg_list = ''
            for lbl in args:
                if re.match('[A-Z@#$][A-Z@#$0-9]', lbl[:2]):
                    # is a label
                    bad_lbl = zPE.bad_label(lbl)
                    if bad_lbl:
                        pass        # err msg
                    elif lbl in SYMBOL:
                        # check scope
                        symbol = SYMBOL[lbl]
                        if symbol.id == scope_id:
                            symbol.references.append(
                                '{0:>4}{1}'.format(
                                    cnt, zPE.core.asm.type_op(op_code[0])
                                    )
                                )
                        else:
                            pass        # duplicated symbol
                    else:
                        SYMBOL[lbl] = Symbol(
                            None, None, scope_id,
                            None, None, None,
                            None, [
                                '{0:>4}{1}'.format(
                                    cnt, zPE.core.asm.type_op(op_code[0])
                                    ),
                                ]
                            )
                    arg_list += lbl + ','
                elif lbl[0] == '=':
                    # constant
                    arg_list += lbl + ','
                    pass        # mark for allocation
                elif zPE.core.asm.valid_st(lbl):
                    # check for constant
                    try:
                        st_info = zPE.core.asm.parse_st(lbl)
                        arg_list += '{0},'.format(
                            zPE.core.asm.value_st(st_info)
                            )
                    except:
                        arg_list += lbl + ','
                else:
                    arg_list += lbl + ','
            # check lable
            bad_lbl = zPE.bad_label(field[0])
            if bad_lbl == None:
                pass        # no label detected
            elif bad_lbl:
                pass        # err msg
            elif field[0] in SYMBOL:
                symbol = SYMBOL[field[0]]
                if symbol.value == None and symbol.id == scope_id:
                    symbol.length = zPE.core.asm.len_op(op_code[0])
                    symbol.value = addr
                    symbol.r_type = 'I'
                    symbol.asm = ' '
                    symbol.program = ' '
                    symbol.defn = cnt
                else:
                    pass        # duplicated symbol
            else:
                SYMBOL[field[0]] = Symbol(
                    zPE.core.asm.len_op(op_code[0]), addr, scope_id,
                    'I', ' ', ' ',
                    cnt, []
                    )
            # update address
            for code in op_code:
                addr += len(code)
            spt.append('{0:0>5}{1:<8} {2:<5} {3}\n'.format(
                    cnt, field[0], field[1], arg_list[:-1]
                    ))

        # parse DC/DS
        elif field[1] in ['DC', 'DS']:
            st_info = zPE.core.asm.parse_st(field[2])
            if st_info[0] == 'a' and st_info[4] != None:
                # check references
                for lbl in st_info[4]:
                    if re.match('[A-Z@#$]', lbl[0]): # is a symbol
                        bad_lbl = zPE.bad_label(lbl)
                        if bad_lbl:
                            pass # err msg
                        elif lbl in SYMBOL:
                            # check scope
                            symbol = SYMBOL[lbl]
                            if symbol.id == scope_id:
                                symbol.references.append(
                                    '{0:>4}{1}'.format(cnt, ' ')
                                    )
                            else:
                                pass # duplicated symbol
                        else:
                            SYMBOL[lbl] = Symbol(
                                None, None, scope_id,
                                None, None, None,
                                None, [ '{0:>4}{1}'.format(cnt, ' '), ]
                                )
            # check lable
            bad_lbl = zPE.bad_label(field[0])
            if bad_lbl == None:
                pass        # no label detected
            elif bad_lbl:
                pass        # err msg
            elif field[0] in SYMBOL:
                symbol = SYMBOL[field[0]]
                if symbol.value == None and symbol.id == scope_id:
                    symbol.length = st_info[3]
                    symbol.value = addr
                    symbol.r_type = st_info[2]
                    symbol.asm = st_info[2]
                    symbol.program = ' '
                    symbol.defn = cnt
                else:
                    pass        # duplicated symbol
            else:
                SYMBOL[field[0]] = Symbol(
                    st_info[3], addr, scope_id,
                    st_info[2], st_info[2], ' ',
                    cnt, []
                    )
            spt.append('{0:0>5}{1:<8} {2:<5} {3}\n'.format(
                    cnt, field[0], field[1], field[2]
                    ))

        # not recognized op-code
        else:
            spt.append('{0:0>5}{1}'.format(cnt, line))
            pass        # err msg
    # end of main read loop

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
    cnt = 0                     # line number
    for line in spt:
        cnt += 1                # start at line No. 1

        if line[0] == '*':      # is comment
            continue

        field = re.split('\s+', line[:-1])

        # parse CSECT
        if field[1] == 'CSECT':
            scope_id = ESD(field[0]).id

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
            args = __PARSE_ARGS(field[2])
            if len(args) != num:
                pass            # err msg
            else:
                for i in range(num):
                    arg = args[i] # parsing needed
                    op_code[i+1].set(arg)

        # parse DC/DS
        elif field[1] in ['DC', 'DS']:
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

def __PARSE_ARGS(arg_line):
    l = re.split(',', arg_line) # gross argument list
    L = []                      # net argument list
    tmp = ''                    # incomplete argument
    for item in l:
        if len(tmp) > 0:
            # incomplete argument exist
            if re.match('[^)]*\)', item):
                # last piece
                L.append(tmp + item)
                tmp = ''
            else:
                # not last piece
                tmp += item + ','
        elif re.match('[^(]*\([^)]*$', item):
            # incomplete argument
            tmp += item + ','
        else:
            # complete argument
            L.append(item)
    return L

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
