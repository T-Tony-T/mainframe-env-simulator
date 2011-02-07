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



    rc = pass_1(None)           # cStringIO
    return pass_2(rc, None)     # cStringIO


def pass_1(memory):
    spi = zPE.core.SPOOL.retrive('SYSIN')    # input SPOOL

    # main read loop
    for line in spi:
        if line[0] != '*':      # not comment
            field = re.split('\s', line[:-1], 3)

            # check lable
            bad_lbl = zPE.bad_label(field[0])
            if bad_lbl:
                pass            # err msg
            elif bad_lbl != None: # label exists
                pass            # add to table

    # end of main read loop

    return zPE.RC['NORMAL']


def pass_2(rc, memory):
    spi = zPE.core.SPOOL.retrive('SYSIN')    # input SPOOL
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



    # end of main read loop

    return zPE.RC['NORMAL']



### Supporting Functions
def __MISSED_FILE(step, i):
    if i >= len(FILE):
        return 0                # termination condition

    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrive('JESYSMSG') # SPOOL No. 03
    ctrl = ' '

    if FILE[i][0] not in step.dd.dict():
        sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
                   '  IEC130I {0:<8}'.format(FILE[i][0]), 
                   ' DD STATEMENT MISSING\n')
        sp3.append(ctrl, 'IEC130I {0:<8}'.format(FILE[i][0]),
                   ' DD STATEMENT MISSING\n')

    cnt = __MISSED_FILE(step, i+1)

    if FILE[i][0] not in step.dd.dict():
        sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
                   '  +{0}\n'.format(FILE[i][1]))
        sp3.append(ctrl, '{0}\n'.format(FILE[i][1]))
        cnt += 1

    return cnt
