################################################################
# Program Name:
#     ASSIST
#
# Purpose:
#     assemble, link-edit, and execute the assembler source code
#     with additional features supported (pretty output,
#     pseudo-instructions, etc.)
#
# Parameter:
#     MACRO     not implemented yet
#
# Input:
#     STEPLIB   required by the ASSIST on Mainframe;
#               an empty folder will work here
#     SYSIN     source code to be assembled, link-edited, and executed
#
# Output:
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


FILE = [
    ('SYSIN', 'AM002 ASSIST COULD NOT OPEN READER SYSIN:ABORT'),
    ('SYSPRINT', 'AM001 ASSIST COULD NOT OPEN PRINTER FT06F001:ABORT'),
    ]

def init(step):
    # check for file requirement
    if __MISSED_FILE(step, 0) != 0:
        return zPE.RC['SEVERE']

    __LOAD_PSEUDO()             # load in all the pseudo instructions

    # invoke parser from ASMA90 to assemble the source code
    objmod = zPE.core.SPOOL.new('SYSLIN', '+', 'tmp', '', '')
    sketch = zPE.core.SPOOL.new('SYSUT1', '+', 'tmp', '', '')

    rc1 = zPE.pgm.ASMA90.pass_1()
    if rc1 < zPE.RC['ERROR']:
        rc2 = zPE.pgm.ASMA90.pass_2()
    else:
        rc2 = rc1

    __PARSE_OUT()

    zPE.core.SPOOL.remove('SYSLIN')
    zPE.core.SPOOL.remove('SYSUT1')

    max_rc = max(rc1, rc2)
    if max_rc > zPE.RC['WARNING']:
        return max_rc

    # invoke HEWLDRGO to link-edit and execute the object module
    zPE.core.SPOOL.replace('SYSLIN', objmod)

    spo = zPE.core.SPOOL.new('SYSLOUT', 'o', 'outstream', '', '')

    rc = zPE.pgm.HEWLDRGO.init(step)

    zPE.core.SPOOL.remove('SYSLIN')
    zPE.core.SPOOL.remove('SYSLOUT')

    return zPE.RC['NORMAL']



### Supporting Functions
def __LOAD_PSEUDO():
    pass

def __MISSED_FILE(step, i):
    if i >= len(FILE):
        return 0                # termination condition

    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrive('JESYSMSG') # SPOOL No. 03
    ctrl = ' '

    if FILE[i][0] not in zPE.core.SPOOL.list():
        sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
                   '  IEC130I {0:<8}'.format(FILE[i][0]), 
                   ' DD STATEMENT MISSING\n')
        sp3.append(ctrl, 'IEC130I {0:<8}'.format(FILE[i][0]),
                   ' DD STATEMENT MISSING\n')

    cnt = __MISSED_FILE(step, i+1)

    if FILE[i][0] not in zPE.core.SPOOL.list():
        sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
                   '  +{0}\n'.format(FILE[i][1]))
        sp3.append(ctrl, '{0}\n'.format(FILE[i][1]))
        cnt += 1

    return cnt

def __PARSE_OUT():
    spi = zPE.core.SPOOL.retrive('SYSIN')    # input SPOOL
    spt = zPE.core.SPOOL.retrive('SYSUT1')   # sketch SPOOL
    spo = zPE.core.SPOOL.retrive('SYSPRINT') # output SPOOL

    asm_warn    = zPE.pgm.ASMA90.INFO['WARNING']
    asm_err     = zPE.pgm.ASMA90.INFO['ERROR']
    asm_mnem    = zPE.pgm.ASMA90.MNEMONIC
    asm_esd     = zPE.pgm.ASMA90.ESD
    asm_esd_id  = zPE.pgm.ASMA90.ESD_ID
    asm_symb    = zPE.pgm.ASMA90.SYMBOL
    asm_symb_v  = zPE.pgm.ASMA90.SYMBOL_V

    # prepare the offset look-up table of the addresses
    offset = { 1 : 0, }         # { scope_id : offset }
    for key in sorted(asm_esd_id.iterkeys()):
        symbol = asm_esd[asm_esd_id[key]][0]
        if symbol != None:
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

    # aliases used to convert signed integer to unsigned hex string
    TP_F = zPE.core.asm.F_
    TP_X = zPE.core.asm.X_

    pln_cnt = 0                 # printed line counter of the current page
    page_cnt = 1                # page counter
    ctrl = '1'

    spo.append(ctrl, '*** ASSIST 4.0/A2-05/15/82  470/V7A/0:OS/VS2  INS=SDFP7/X=BGHO, CHECK/TRC/=1180, OPTS=CDKMPR FROM PENN ST*NIU COMPSCI*LT\n')
    pln_cnt += 1
    ctrl = '0'

    spo.append(ctrl, '\n')
    pln_cnt += 1

    spo.append(ctrl, '{0:>111}PAGE {1:>4}\n'.format(' ', page_cnt))
    spo.append(ctrl, '  LOC  OBJECT CODE    ADDR1 ADDR2  STMT   SOURCE STATEMENT\n')
    pln_cnt += 2

    # main read loop
    cnt = 0                     # line number
    eojob = False               # end of job indicater
    for line in spi:
        cnt += 1                # start at line No. 1
        if pln_cnt >= zPE.DEFAULT['LN_P_PAGE']:
            page_cnt += 1
            spo.append('1', '{0:>111}PAGE {1:>4}\n'.format(' ', page_cnt))
            spo.append(ctrl, '  LOC  OBJECT CODE    ADDR1 ADDR2  STMT   SOURCE STATEMENT\n')
            pln_cnt = 2
        ctrl = ' '


        if eojob:               # inline inputs
            pass # ignored

        elif line[0] == '*':    # comments
            spo.append(ctrl, '{0:>6} {1:<26} '.format(' ', ' '),
                       '{0:>5} {1}'.format(cnt, line))

        else:                   # instructions
            if asm_mnem[cnt][0] > 0:    # CSECT
                loc = hex(
                    offset[ asm_mnem[cnt][0] ] + asm_mnem[cnt][1]
                    )[2:].upper()
            else:                       # DSECT or END
                loc = hex(asm_mnem[cnt][1])[2:].upper()
                if asm_mnem[cnt][0] == 0:
                    eojob = True

            tmp_str = ''
            if len(asm_mnem[cnt]) == 3: # type 3
                for val in asm_mnem[cnt][2]:
                    tmp_str += zPE.core.asm.X_.tr(val.dump())
                if len(tmp_str) > 16:
                    tmp_str = tmp_str[:16]
            elif len(asm_mnem[cnt]) == 5: # type 5
                code = zPE.core.asm.prnt_op(asm_mnem[cnt][2])
                if len(code) == 12:
                    field_3 = code[8:12]
                else:
                    field_3 = '    '
                if len(code) >= 8:
                    field_2 = code[4:8]
                else:
                    field_2 = '    '
                field_1 = code[0:4]
                tmp_str = '{0} {1} {2} '.format(
                    field_1, field_2, field_3
                    )
                if asm_mnem[cnt][3]:
                    addr_1 = asm_mnem[cnt][3]
                else:
                    addr_1 = '     '
                if asm_mnem[cnt][4]:
                    addr_2 = asm_mnem[cnt][4]
                else:
                    addr_2 = '     '
                tmp_str += '{0:0>5} {1:0>5}'.format(
                    addr_1, addr_2
                    )

            spo.append(ctrl, '{0:0>6} {1:<26} '.format(loc, tmp_str),
                       '{0:>5} {1}'.format(cnt, line))

    print '\nExternal Symbol Dictionary:'
    for key in sorted(asm_esd_id.iterkeys()):
        k = asm_esd_id[key]
        if asm_esd[k][0] and asm_esd[k][0].id == key:
            v = asm_esd[k][0]
        else:
            v = asm_esd[k][1]
        print '{0} => {1}'.format(k, v.__dict__)

    print '\nSymbol Cross Reference Table:'
    for key in sorted(asm_symb.iterkeys()):
        if asm_symb[key].value == None:
            addr = int('ffffff', 16)
        else:
            addr = asm_symb[key].value
        print '{0} (0x{1:0>6}) => {2}'.format(
            key, hex(addr)[2:].upper(), asm_symb[key].__dict__
            )
    print '\nSymbol Cross Reference Sub-Table:'
    for key in sorted(asm_symb_v.iterkeys()):
        if asm_symb_v[key].value == None:
            addr = int('ffffff', 16)
        else:
            addr = asm_symb_v[key].value
        print '{0} (0x{1:0>6}) => {2}'.format(
            key, hex(addr)[2:].upper(), asm_symb_v[key].__dict__
            )

    print '\nMnemonic:'
    for key in sorted(asm_mnem.iterkeys()):
        tmp_str = ''
        if len(asm_mnem[key]) == 3: # type 3
            for val in asm_mnem[key][2]:
                tmp_str += zPE.core.asm.X_.tr(val.dump())
        elif len(asm_mnem[key]) == 5: # type 5
            code = zPE.core.asm.prnt_op(asm_mnem[key][2])
            if len(code) == 12:
                field_3 = code[8:12]
            else:
                field_3 = '    '
            if len(code) >= 8:
                field_2 = code[4:8]
            else:
                field_2 = '    '
            field_1 = code[0:4]
            tmp_str = '{0} {1} {2} '.format(
                field_1, field_2, field_3
                )
            if asm_mnem[key][3]:
                addr_1 = asm_mnem[key][3]
            else:
                addr_1 = '     '
            if asm_mnem[key][4]:
                addr_2 = asm_mnem[key][4]
            else:
                addr_2 = '     '
            tmp_str += '{0:0>5} {1:0>5}'.format(
                addr_1, addr_2
                )
        print '{0:>5}: {1} {2:0>6} {3}'.format(
            key,
            TP_X.tr(TP_F(asm_mnem[key][0]).dump()),
            hex(asm_mnem[key][1])[2:],
            tmp_str
            )
