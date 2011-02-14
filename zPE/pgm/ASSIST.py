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
    for line in spi:
        cnt += 1                # start at line No. 1
        if pln_cnt >= zPE.DEFAULT['LN_P_PAGE']:
            page_cnt += 1
            spo.append('1', '{0:>111}PAGE {1:>4}\n'.format(' ', page_cnt))
            spo.append(ctrl, '  LOC  OBJECT CODE    ADDR1 ADDR2  STMT   SOURCE STATEMENT\n')
            pln_cnt = 2
        ctrl = ' '


        if line[0] == '*':      # comment
            spo.append(ctrl, '{0:>6} {1:<26} '.format(' ', ' '),
                       '{0:>5} {1}'.format(cnt, line))
        else:
            spo.append(ctrl, '{0:0>6} {1:<26} '.format('0', ' '),
                       '{0:>5} {1}'.format(cnt, line))

    print '\nExternal Symbol Dictionary:'
    for k,v in sorted(zPE.pgm.ASMA90.ESD.iteritems(),
                      key=lambda (k,v): (v,k)):
        print '{0:<8} => {1}'.format(k, v.__dict__)

    print '\nSymbol Cross Reference Table:'
    mydict = zPE.pgm.ASMA90.SYMBOL
    for key in sorted(mydict.iterkeys()):
        print '{0:<8} => {1}'.format(key, mydict[key].__dict__)
