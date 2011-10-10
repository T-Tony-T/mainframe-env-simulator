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
from time import localtime, mktime, strftime

from assist_err_code_rc import * # read recourse file for err msg


FILE = [
    ('SYSIN', 'AM002 ASSIST COULD NOT OPEN READER SYSIN:ABORT'),
    ('SYSPRINT', 'AM001 ASSIST COULD NOT OPEN PRINTER FT06F001:ABORT'),
    ]

LOCAL_CONFIG = {
    'LN_P_PAGE' : 56,           # line per page for output
    }

def init(step):
    # check for file requirement
    if __MISSED_FILE(step, 0) != 0:
        return zPE.RC['SEVERE']

    __LOAD_PSEUDO()             # load in all the pseudo instructions

    limit = 0 # error tolerance limit; currently hard coded. need info

    # invoke parser from ASMA90 to assemble the source code
    objmod = zPE.core.SPOOL.new('SYSLIN', '+', 'tmp', '', '')
    sketch = zPE.core.SPOOL.new('SYSUT1', '+', 'tmp', '', '')

    rc      = zPE.pgm.ASMA90.pass_1(24, 24)
    err_cnt = zPE.pgm.ASMA90.pass_2(rc, 24, 24)

    __PARSE_OUT(step, limit)

    zPE.core.SPOOL.remove('SYSLIN')
    zPE.core.SPOOL.remove('SYSUT1')

    if err_cnt > limit:
        return zPE.RC['NORMAL'] # skip exec, return with "CC = 0"

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

def __PARSE_OUT(step, limit):
    spi = zPE.core.SPOOL.retrive('SYSIN')    # input SPOOL
    spt = zPE.core.SPOOL.retrive('SYSUT1')   # sketch SPOOL
    spo = zPE.core.SPOOL.retrive('SYSPRINT') # output SPOOL

    asm_info    = zPE.pgm.ASMA90.INFO['I']
    asm_warn    = zPE.pgm.ASMA90.INFO['W']
    asm_err     = zPE.pgm.ASMA90.INFO['E']
    asm_ser     = zPE.pgm.ASMA90.INFO['S']

    asm_mnem    = zPE.pgm.ASMA90.MNEMONIC

    asm_esd     = zPE.pgm.ASMA90.ESD
    asm_esd_id  = zPE.pgm.ASMA90.ESD_ID
    asm_symb    = zPE.pgm.ASMA90.SYMBOL
    asm_symb_v  = zPE.pgm.ASMA90.SYMBOL_V
    asm_symb_eq = zPE.pgm.ASMA90.SYMBOL_EQ

    asm_using   = zPE.pgm.ASMA90.USING_MAP

    # aliases used to convert signed integer to unsigned hex string
    TP_F = zPE.core.asm.F_
    TP_X = zPE.core.asm.X_

    pln_cnt = 0                 # printed line counter of the current page
    page_cnt = 1                # page counter

    ### header portion of the report
    ctrl = '1'
    spo.append(ctrl, '*** ASSIST 4.0/A2-05/15/82  470/V7A/0:OS/VS2  INS=SDFP7/X=BGHO, CHECK/TRC/=1180, OPTS=CDKMPR FROM PENN ST*NIU COMPSCI*LT\n')
    pln_cnt += 1
    ctrl = '0'

    spo.append(ctrl, '\n')
    pln_cnt += 1

    spo.append(ctrl, '{0:>111}PAGE {1:>4}\n'.format(' ', page_cnt))
    spo.append(ctrl, '  LOC  OBJECT CODE    ADDR1 ADDR2  STMT   SOURCE STATEMENT\n')
    pln_cnt += 2


    ### main read loop, op code portion of the report
    cnt = 0                     # line number
    eojob = False               # end of job indicater
    for line in spi:
        cnt += 1                # start at line No. 1
        if pln_cnt >= LOCAL_CONFIG['LN_P_PAGE']:
            page_cnt += 1
            spo.append('1', '{0:>111}PAGE {1:>4}\n'.format(' ', page_cnt))
            spo.append('0', '  LOC  OBJECT CODE    ADDR1 ADDR2  STMT   SOURCE STATEMENT\n')
            pln_cnt = 2
        ctrl = ' '


        if eojob:
            # inline inputs
            continue # ignored

        elif line[0] == '*':
            # comments
            spo.append(ctrl, '{0:>6} {1:<26} '.format(' ', ' '),
                       '{0:>5} {1}'.format(cnt, line))
            pln_cnt += 1
            continue

        # instructions
        if len(asm_mnem[cnt]) == 1: # type 1
            loc = '      '
        elif asm_mnem[cnt][0] != 0: # CSECT or DSECT
            loc = hex(asm_mnem[cnt][1])[2:].upper()
        else:                       # END
            loc = hex(asm_mnem[cnt][1])[2:].upper()
            eojob = True

        tmp_str = ''

        if len(asm_mnem[cnt]) == 3: # type 3
            for val in asm_mnem[cnt][2]:
                tmp_str += zPE.core.asm.X_.tr(val.dump())
            if len(tmp_str) > 16:
                tmp_str = tmp_str[:16]
        elif len(asm_mnem[cnt]) == 5: # type 5
            op = asm_mnem[cnt][2]
            code = zPE.core.asm.prnt_op(op)
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
            # mark; add addr here

        spo.append(ctrl, '{0:0>6} {1:<26} '.format(loc, tmp_str),
                   '{0:>5} {1}'.format(cnt, line))
        pln_cnt += 1

        # process error msg, if any
        if cnt in asm_ser:
            for tmp in asm_ser[cnt]:
                spo.append(ctrl, gen_msg('S', tmp, line))
                pln_cnt += 1
        if cnt in asm_err:
            for tmp in asm_err[cnt]:
                spo.append(ctrl, gen_msg('E', tmp, line))
                pln_cnt += 1
        if cnt in asm_warn:
            for tmp in asm_warn[cnt]:
                spo.append(ctrl, gen_msg('W', tmp, line))
                pln_cnt += 1
        if cnt in asm_info:
            for tmp in asm_info[cnt]:
                spo.append(ctrl, gen_msg('I', tmp, line))
                pln_cnt += 1
    ### end of main read loop


    ### summary portion of the report
    cnt_warn = len(asm_warn)
    cnt_err  = len(asm_err) + len(asm_ser)
    cnt_all  = cnt_warn + cnt_err
    def format_cnt(cnt):
        if cnt:
            return '{0:>5}'.format(cnt)
        else:
            return ' NO  '

    ctrl = '0'
    spo.append(ctrl, '*** ', format_cnt(cnt_all), ' STATEMENTS FLAGGED - ',
               format_cnt(cnt_warn), ' WARNINGS, ',
               format_cnt(cnt_err), ' ERRORS\n')
    if cnt_err > limit:
        spo.append(ctrl, '***** NUMBER OF ERRORS EXCEEDS LIMIT OF ',
                   format_cnt(limit),
                   ' ERRORS - PROGRAM EXECUTION DELETED *****\n')
    spo.append(ctrl, '*** DYNAMIC CORE AREA USED: ',
               ' LOW: {0:>7} HIGH: {1:>7}'.format('###', '###'), # need info
               ' LEAVING: {0:>7} FREE BYTES.'.format('#######'), # need info
               ' AVERAGE: {0:>8} BYTES/STMT ***\n'.format('##')) # need info
    diff = mktime(localtime()) - mktime(step.start)
    spo.append(ctrl, '*** ASSEMBLY TIME = {0:>8.3f} SECS,'.format(diff),
               ' {0:>8} STATEMENT/SEC ***\n'.format('#####')) # need info

    #
    # debugging information
    #

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
    print '\nSymbol Cross Reference ER Sub-Table:'
    for key in sorted(asm_symb_v.iterkeys()):
        if asm_symb_v[key].value == None:
            addr = int('ffffff', 16)
        else:
            addr = asm_symb_v[key].value
        print '{0} (0x{1:0>6}) => {2}'.format(
            key, hex(addr)[2:].upper(), asm_symb_v[key].__dict__
            )
    print '\nSymbol Cross Reference =Const Sub-Table:'
    for key in sorted(asm_symb_eq.iterkeys()):
        for indx in range(len(asm_symb_eq[key])):
            if asm_symb_eq[key][indx].value == None:
                addr = int('ffffff', 16)
            else:
                addr = asm_symb_eq[key][indx].value
            print '{0} (0x{1:0>6}) => {2}'.format(
                key, hex(addr)[2:].upper(), asm_symb_eq[key][indx].__dict__
                )

    print '\nMnemonic:'
    for key in sorted(asm_mnem.iterkeys()):
        if len(asm_mnem[key]) == 1: # type 1
            loc = '      '
        else:
            loc = hex(asm_mnem[key][1])[2:]
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
            loc,
            tmp_str
            )

    print '\nInfo:'
    print asm_info
    print '\nWarning:'
    print asm_warn
    print '\nError:'
    print asm_err
    print '\nSerious:'
    print asm_ser

    print '\nUsing Map:'
    for k,v in asm_using.iteritems():
        print k, v.__dict__
