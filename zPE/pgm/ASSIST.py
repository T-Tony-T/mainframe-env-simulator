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
#      0        ASSIST executed
#     16        insufficient resources
#
# Return Value:
#     none
################################################################


import zPE

import os, sys
import re
from time import time, strftime

from assist_err_code_rc import * # read recourse file for err msg


FILE = [
    ('SYSIN', 'AM002 ASSIST COULD NOT OPEN READER SYSIN:ABORT'),
    ('SYSPRINT', 'AM001 ASSIST COULD NOT OPEN PRINTER FT06F001:ABORT'),
    ]

TIME = {
    'asm_start'  : None,
    'asm_end'    : None,
    'exec_start' : None,
    'exec_end'   : None,
    }

def init(step):
    # check for file requirement
    if __MISSED_FILE(step, 0) != 0:
        return zPE.RC['CRITICAL']

    __LOAD_PSEUDO()             # load in all the pseudo instructions

    limit = 0 # error tolerance limit; currently hard coded. need info

    # invoke parser from ASMA90 to assemble the source code
    objmod = zPE.core.SPOOL.new('SYSLIN', '+', 'tmp', '', '')
    sketch = zPE.core.SPOOL.new('SYSUT1', '+', 'tmp', '', '')

    # load the user-supplied PARM and config into the default configuration
    zPE.pgm.ASMA90.load_parm({
            'AMODE'     : 24,
            'RMODE'     : 24,
            })
    zPE.pgm.ASMA90.load_local_conf({
            'MEM_POS'   : 0,    # always start at 0x000000 for ASSIST
            'REGION'    : step.region,
            'LN_P_PAGE' : 59,
            })

    TIME['asm_start'] = time()
    zPE.pgm.ASMA90.pass_1()
    zPE.pgm.ASMA90.pass_2()
    TIME['asm_end'] = time()

    err_cnt = __PARSE_OUT_ASM(limit, False)

    # calculate memory needed to execute the module
    required_mem_sz = 0
    for esd in zPE.pgm.ASMA90.ESD.itervalues():
        if esd[0]:
            sz = esd[0].addr + esd[0].length
            if sz > required_mem_sz:
                required_mem_sz = sz

    zPE.pgm.ASMA90.init_res()   # release resources

    zPE.core.SPOOL.remove('SYSLIN')
    zPE.core.SPOOL.remove('SYSUT1')

    if err_cnt > limit:
        return zPE.RC['NORMAL'] # skip exec, return with "CC = 0"

    # invoke HEWLDRGO to link-edit and execute the object module
    zPE.core.SPOOL.replace('SYSLIN', objmod)
    zPE.core.SPOOL.pretend('SYSLOUT', 'SYSPRINT') # SYSLOUT -> SYSPRINT

    # load the user-supplied PARM and config into the default configuration
    zPE.pgm.HEWLDRGO.load_parm({
            'AMODE'   : 24,
            'RMODE'   : 24,
            })
    zPE.pgm.HEWLDRGO.load_local_conf({
            'MEM_POS' : 0,      # always start at 0x000000 for ASSIST
            'MEM_LEN' : required_mem_sz,
            'REGION'  : step.region,
            })

    # load OBJMOD into memory, and execute it
    TIME['exec_start'] = time()
    rc = zPE.pgm.HEWLDRGO.go(zPE.pgm.HEWLDRGO.load())
    TIME['exec_end'] = time()

    __PARSE_OUT_LDR(rc, False)

    zPE.pgm.HEWLDRGO.init_res()   # release resources

    zPE.core.SPOOL.remove('SYSLIN')
    zPE.core.SPOOL.remove('SYSLOUT') # unlink SYSLOUT

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


from ASMA90 import TITLE
def __PARSE_OUT_ASM(limit, debug = True):
    spi = zPE.core.SPOOL.retrive('SYSIN')    # input SPOOL
    spt = zPE.core.SPOOL.retrive('SYSUT1')   # sketch SPOOL
    spo = zPE.core.SPOOL.retrive('SYSPRINT') # output SPOOL

    asm_info    = zPE.pgm.ASMA90.INFO['I']
    asm_msg     = zPE.pgm.ASMA90.INFO['N']
    asm_warn    = zPE.pgm.ASMA90.INFO['W']
    asm_err     = zPE.pgm.ASMA90.INFO['E']
    asm_sev     = zPE.pgm.ASMA90.INFO['S']

    info_ge     = zPE.pgm.ASMA90.INFO_GE

    asm_mnem    = zPE.pgm.ASMA90.MNEMONIC

    asm_esd     = zPE.pgm.ASMA90.ESD
    asm_esd_id  = zPE.pgm.ASMA90.ESD_ID
    asm_symb    = zPE.pgm.ASMA90.SYMBOL
    asm_symb_v  = zPE.pgm.ASMA90.SYMBOL_V
    asm_symb_eq = zPE.pgm.ASMA90.SYMBOL_EQ
    asm_symb_nr = zPE.pgm.ASMA90.NON_REF_SYMBOL
    asm_symb_iv = zPE.pgm.ASMA90.INVALID_SYMBOL

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

    ### main read loop, op code portion of the report
    init_cnt = 1                # start at line No. 1
    title = ''                  # default title
    title_indx = 1              # start at first title, if any
    # print first header
    if len(TITLE) > title_indx and TITLE[title_indx][0] == init_cnt:
        # line No. 1 is TITLE
        title = TITLE[title_indx][2]
        title_indx += 1         # advance the index to the next potential TITLE
        if not info_ge(init_cnt, 'I'):
            init_cnt = 2        # all green with the TITLE line, skip it
    pln_cnt = __PRINT_HEADER(spo, title, pln_cnt, page_cnt, ctrl)

    eojob = False # "end of job" indicater; will be turned on by "END" statement
    for cnt in range(init_cnt, len(spi) + 1): # loop through line_num (indx + 1)
        line = spi[cnt - 1]     # indx = line_num - 1
        ctrl = ' '

        if eojob:
            # inline inputs
            continue # ignored

        elif line[0] == '*':
            # comments
            pln = [ ctrl, '{0:>6} {1:<26} '.format(' ', ' '),
                    '{0:>5} {1}'.format(cnt, line) ]
            ( pln_cnt, page_cnt ) = __PRINT_LINE(
                spo, title, pln, pln_cnt, page_cnt
                )
            continue

        # instructions
        if len(asm_mnem[cnt]) == 0: # type 0, TITLE; new page if no error
            if not info_ge(cnt, 'I'):
                title = TITLE[title_indx][2] # update current TITLE
                title_indx += 1 # advance the index to the next potential TITLE

                page_cnt += 1   # new page
                pln_cnt = __PRINT_HEADER(spo, title, 0, page_cnt)

                if not info_ge(cnt, 'I'):
                    continue    # skip the current iteration
            loc = ''
        elif len(asm_mnem[cnt]) == 1: # type 1, no info to print
            loc = ''
        elif asm_mnem[cnt][0] == 0: # no scope ==> END (type 2)
            loc = ''
            eojob = True
        elif len(asm_mnem[cnt]) == 4: # type 4, EQU
            loc = hex(asm_mnem[cnt][3])[2:].upper()
        else:                       # type 2/3/5, inside CSECT or DSECT
            loc = hex(asm_mnem[cnt][1])[2:].upper()

        tmp_str = ''

        if ( len(asm_mnem[cnt]) == 3  and # type 3
             zPE.core.asm.can_get_sd(asm_mnem[cnt][2]) # DC/=const
             ):
            for val in zPE.core.asm.get_sd(asm_mnem[cnt][2]):
                tmp_str += zPE.core.asm.X_.tr(val.dump())
            if len(tmp_str) > 16:
                tmp_str = tmp_str[:16]
        elif len(asm_mnem[cnt]) == 4: # type 4
            tmp_str = '{0:<14} {1:0>5} {0:>5}'.format(
                '', loc
                )
        elif len(asm_mnem[cnt]) == 5: # type 5
            # breaking up the op-mnemonic field
            code = zPE.core.asm.prnt_op(asm_mnem[cnt][2])
            if len(code) == 12:
                field_3 = code[8:12]
            else:
                field_3 = '    ' # 4 spaces
            if len(code) >= 8:
                field_2 = code[4:8]
            else:
                field_2 = '    ' # 4 spaces
            field_1 = code[0:4]
            tmp_str = '{0} {1} {2} '.format(
                field_1, field_2, field_3
                )
            # appending to it the "ADDR1" and "ADDR2" fields, if applied
            if asm_mnem[cnt][3]:
                if asm_mnem[cnt][3].valid:
                    addr_1 = hex(asm_mnem[cnt][3].get()[-1])[2:].upper()
                else:
                    addr_1 = '0'
            else:
                addr_1 = '     '
            if asm_mnem[cnt][4]:
                if asm_mnem[cnt][4].valid:
                    addr_2 = hex(asm_mnem[cnt][4].get()[-1])[2:].upper()
                else:
                    addr_2 = '0'
            else:
                addr_2 = '     '
            tmp_str += '{0:0>5} {1:0>5}'.format(
                addr_1, addr_2
                )

        pln = [ ctrl, '{0:0>6} {1:<26} '.format(loc, tmp_str),
                '{0:>5} {1}'.format(cnt, line) ]
        ( pln_cnt, page_cnt ) = __PRINT_LINE(spo, title, pln, pln_cnt, page_cnt)

        # process error msg, if any
        if cnt in asm_sev:
            for tmp in asm_sev[cnt]:
                ( pln_cnt, page_cnt ) = __PRINT_LINE(
                    spo, title,
                    [ ctrl, gen_msg('S', tmp, line) ],
                    pln_cnt, page_cnt
                    )
        if cnt in asm_err:
            for tmp in asm_err[cnt]:
                ( pln_cnt, page_cnt ) = __PRINT_LINE(
                    spo, title,
                    [ ctrl, gen_msg('E', tmp, line) ],
                    pln_cnt, page_cnt
                    )
        if cnt in asm_warn:
            for tmp in asm_warn[cnt]:
                ( pln_cnt, page_cnt ) = __PRINT_LINE(
                    spo, title,
                    [ ctrl, gen_msg('W', tmp, line) ],
                    pln_cnt, page_cnt
                    )
        if cnt in asm_msg:
            for tmp in asm_msg[cnt]:
                ( pln_cnt, page_cnt ) = __PRINT_LINE(
                    spo, title,
                    [ ctrl, gen_msg('N', tmp, line) ],
                    pln_cnt, page_cnt
                    )
        if cnt in asm_info:
            for tmp in asm_info[cnt]:
                ( pln_cnt, page_cnt ) = __PRINT_LINE(
                    spo, title,
                    [ ctrl, gen_msg('I', tmp, line) ],
                    pln_cnt, page_cnt
                    )
    ### end of main read loop

    ### summary portion of the report
    cnt_warn = len(asm_info) + len(asm_msg) + len(asm_warn)
    cnt_err  = len(asm_err) + len(asm_sev)
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
               ' AVERAGE: {0:>8} BYTES/STMT ***\n'.format('##'))
               # (LOW + HIGH) / len(spi)
    diff = TIME['asm_end'] - TIME['asm_start']
    spo.append(ctrl, '*** ASSEMBLY TIME = {0:>8.3f} SECS, '.format(diff),
               '{0:>8} STATEMENT/SEC ***\n'.format(int(len(spi) / diff)))

    if not debug:
        return cnt_err          # regular process end here
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
    print '\nUnreferenced Symbol Defined in CSECTs:'
    for (ln, key) in sorted(asm_symb_nr, key = lambda t: t[1]):
        print '{0:>4} {1}'.format(ln, key)


    print '\nMnemonic:'
    for key in sorted(asm_mnem.iterkeys()):
        if len(asm_mnem[cnt]) == 0: # type 0
            loc = ''
        elif len(asm_mnem[key]) == 1: # type 1
            loc = ''
        elif len(asm_mnem[key]) == 4: # type 4
            loc = hex(asm_mnem[key][3])[2:].upper()
        else:
            loc = hex(asm_mnem[key][1])[2:]
        tmp_str = ''
        if ( len(asm_mnem[cnt]) == 3  and # type 3
             zPE.core.asm.can_get_sd(asm_mnem[cnt][2]) # DC/=const
             ):
            for val in zPE.core.asm.get_sd(asm_mnem[cnt][2]):
                tmp_str += zPE.core.asm.X_.tr(val.dump())
        elif len(asm_mnem[key]) == 4: # type 4
            tmp_str += '{0:<14} {1:0>5} {0:>5}'.format(
                '', loc
                )            
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
                if asm_mnem[key][3].valid:
                    addr_1 = hex(asm_mnem[key][3].get()[-1])[2:].upper()
                else:
                    addr_1 = '0'
            else:
                addr_1 = '     '
            if asm_mnem[key][4]:
                if asm_mnem[key][4].valid:
                    addr_2 = hex(asm_mnem[key][4].get()[-1])[2:].upper()
                else:
                    addr_2 = '0'
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

    print '\nInfomation:'
    print asm_info
    print '\nNotification:'
    print asm_msg
    print '\nWarning:'
    print asm_warn
    print '\nError:'
    print asm_err
    print '\nSevere Error:'
    print asm_sev

    print '\nUsing Map:'
    for (k, v) in asm_using.iteritems():
        print k, v.__dict__

    print '\n\nObject Deck:'
    for line in zPE.core.SPOOL.retrive('SYSLIN'):
        print line
    # end of debugging
    return cnt_err


def __PRINT_LINE(spool_out, title, line_words, line_num, page_num):
    '''
    spool_out
        the spool that the header is written to
    title
        the current title (in case of page increment)
    line_words
        the tuple/list that consist a line
    line_num
        the current line number
    page_num
        the current page number

    return value
        a two-tuple containing the new line number
        and the new page number after the line is
        inserted
    '''
    if line_num >= zPE.pgm.ASMA90.LOCAL_CONF['LN_P_PAGE']:
        page_num += 1           # new page
        line_num = __PRINT_HEADER(spool_out, title, 0, page_num)
    spool_out.append(* line_words)

    return ( line_num + 1, page_num )


def __PRINT_HEADER(spool_out, title, line_num, page_num, ctrl = '1'):
    '''
    spool_out
        the spool that the header is written to
    title
        the title to be printed
    line_num
        the current line number
    page_num
        the current page number
    ctrl = '1'
        the control char for the header

    return value
        the new line number after header is inserted
    '''
    spool_out.append(ctrl, '{0:<8} {1:<102}PAGE {2:>4}\n'.format(
            TITLE[0], title, page_num
            ))
    spool_out.append('0',  '  LOC  OBJECT CODE    ADDR1 ADDR2  STMT   SOURCE STATEMENT\n')
    return line_num + 2


def __PARSE_OUT_LDR(rc, debug = True):
    spo = zPE.core.SPOOL.retrive('SYSPRINT') # (actual) output SPOOL

    ldr_ins    = zPE.pgm.HEWLDRGO.INSTRUCTION
    ldr_br     = zPE.pgm.HEWLDRGO.BRANCHING


    ctrl = '0'
    spo.append(ctrl, '*** PROGRAM EXECUTION BEGINNING - ANY OUTPUT BEFORE EXECUTION TIME MESSAGE IS PRODUCED BY USER PROGRAM ***\n')

    # output for the execution of the module
    # end of output for the execution of the module

    diff = TIME['exec_end'] - TIME['exec_start']
    spo.append(ctrl, '*** EXECUTION TIME = {0:>8.3f} SECS. '.format(diff),
               '{0:>9} INSTRUCTIONS EXECUTED - '.format(len(ldr_ins)),
               '{0:>8} INSTRUCTIONS/SEC ***\n'.format(int(len(ldr_ins) / diff)))
    spo.append(ctrl, '*** FIRST CARD NOT READ: NO CARDS READ:FILE UNOPENED\n')
    if rc < zPE.RC['WARNING']:
        msg = 'NORMAL'
    else:
        msg = 'ABNORMAL'
    spo.append(ctrl, '*** AM004 - ', msg, 'USER TERMINATION BY RETURN ***\n')
