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
#     MACRO     required by Marist ASSIST (MACRO=H);
#               will be ignored here
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
            })

    TIME['asm_start'] = time()
    zPE.pgm.ASMA90.pass_1()
    zPE.pgm.ASMA90.pass_2()
    TIME['asm_end'] = time()

    err_cnt = __PARSE_OUT_ASM(limit)

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
            'PSWKEY'  : 12, # 12 is the key used by ASSIST on "marist"
            })
    zPE.pgm.HEWLDRGO.load_local_conf({
            'MEM_POS' : 0,      # always start at 0x000000 for ASSIST
            'MEM_LEN' : required_mem_sz,
            'TIME'    : min(
                zPE.JCL['jobstart'] + zPE.JCL['time'] - time(), # job limit
                step.start + step.time - time()                 # step limit
                ),
            'REGION'  : step.region,
            })

    # load OBJMOD into memory, and execute it
    TIME['exec_start'] = time()
    rc = zPE.pgm.HEWLDRGO.go(zPE.pgm.HEWLDRGO.load())
    TIME['exec_end'] = time()

    __PARSE_OUT_LDR(rc)

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
from ASMA90 import INFO, INFO_GE, MAP_INFO_GE
from ASMA90 import ESD, ESD_ID, MNEMONIC, MACRO_GEN, USING_MAP
from ASMA90 import SYMBOL, SYMBOL_V, SYMBOL_EQ, NON_REF_SYMBOL, INVALID_SYMBOL

def __PARSE_OUT_ASM(limit):
    spi = zPE.core.SPOOL.retrive('SYSIN')    # input SPOOL
    spt = zPE.core.SPOOL.retrive('SYSUT1')   # sketch SPOOL
    spo = zPE.core.SPOOL.retrive('SYSPRINT') # output SPOOL

    CNT = {
        'pln'  : 1,         # printed line counter of the current page
        'page' : 1,         # page counter
        }

    ### header portion of the report
    ctrl = '1'
    spo.append(ctrl, '*** ASSIST 4.0/A2-05/15/82  470/V7A/0:OS/VS2  INS=SDFP7/X=BGHO, CHECK/TRC/=1180, OPTS=CDKMPR FROM PENN ST*NIU COMPSCI*LT\n')
    CNT['pln'] += zPE.SPOOL_CTRL_MAP[ctrl]

    ctrl = '0'
    spo.append(ctrl, '\n')
    CNT['pln'] += zPE.SPOOL_CTRL_MAP[ctrl]

    ### main read loop, op code portion of the report
    init_line_num = 1           # start at line No. 1
    title = ''                  # default title
    title_indx = 1              # start at first title, if any
    # print first header
    if len(TITLE) > title_indx and TITLE[title_indx][0] == init_line_num:
        # line No. 1 is TITLE
        title = TITLE[title_indx][2]
        title_indx += 1         # advance the index to the next potential TITLE
        if not INFO_GE(init_line_num, 'I'):
            init_line_num = 2   # all green with the TITLE line, skip it
    CNT['pln'] = __PRINT_HEADER(spo, title, CNT['pln'], CNT['page'], ctrl)

    eojob = False # "end of job" indicater; will be turned on by "END" statement
    for line_num in range(init_line_num, len(spi) + 1):
        # loop through line_num (indx + 1)
        line = spi[line_num - 1]
        ctrl = ' '

        if eojob:
            # inline inputs
            continue # ignored

        elif line[0] == '*':
            # comments
            ( CNT['pln'], CNT['page'] ) = __PRINT_LINE(
                spo, title,
                [ ctrl, '{0:>6} {1:<26} '.format(' ', ' '),
                  '{0:>5} {1:<72}'.format(line_num, line[:-1]),
                  '{0:0>4}{1:0>4}'.format(line_num, 0), # need info
                  '\n',
                  ],
                CNT['pln'], CNT['page']
                )
            continue


        # instructions
        if len(MNEMONIC[line_num]) == 0: # type 0, TITLE
            if not INFO_GE(line_num, 'E'):
                title = TITLE[title_indx][2] # update current TITLE
                title_indx += 1 # advance the index to the next potential TITLE

                CNT['page'] += 1 # new page
                CNT['pln']   = __PRINT_HEADER(spo, title, 0, CNT['page'])

                if not INFO_GE(line_num, 'I'):
                    # skip the current iteration if no info need to be printed
                    continue
            loc = ' ' * 6       # do not print location for this type
        elif len(MNEMONIC[line_num]) == 1: # type 1, no info to print
            loc = ''
        elif MNEMONIC[line_num][0] == None: # no scope ==> END (type 2)
            loc = ''
            eojob = True
        elif len(MNEMONIC[line_num]) == 4: # type 4, EQU
            loc = hex(MNEMONIC[line_num][3])[2:].upper()
        else:                       # type 2/3/5, inside CSECT or DSECT
            loc = hex(MNEMONIC[line_num][1])[2:].upper()

        tmp_str = ''

        if ( len(MNEMONIC[line_num]) == 3  and # type 3
             zPE.core.asm.can_get_sd(MNEMONIC[line_num][2]) # DC/=const
             ):
            for val in zPE.core.asm.get_sd(MNEMONIC[line_num][2]):
                tmp_str += zPE.core.asm.X_.tr(val.dump())
            if len(tmp_str) > 16:
                tmp_str = tmp_str[:16]
        elif len(MNEMONIC[line_num]) == 4: # type 4
            tmp_str = '{0:<14} {1:0>5} {0:>5}'.format(
                '', loc
                )
        elif len(MNEMONIC[line_num]) == 5: # type 5
            # breaking up the op-mnemonic field
            code = zPE.core.asm.prnt_op(MNEMONIC[line_num][2])
            if len(code) == 12:
                field_3 = code[8:12]
            else:
                field_3 = ' ' * 4
            if len(code) >= 8:
                field_2 = code[4:8]
            else:
                field_2 = ' ' * 4
            field_1 = code[0:4]

            tmp_str = '{0} {1} {2} '.format(
                field_1, field_2, field_3
                )
            # appending to it the "ADDR1" and "ADDR2" fields, if applied
            if MNEMONIC[line_num][3]:
                if MNEMONIC[line_num][3].valid:
                    addr_1 = hex(MNEMONIC[line_num][3].get()[-1])[2:].upper()
                else:
                    addr_1 = '0'
            else:
                addr_1 = '     '
            if MNEMONIC[line_num][4]:
                if MNEMONIC[line_num][4].valid:
                    addr_2 = hex(MNEMONIC[line_num][4].get()[-1])[2:].upper()
                else:
                    addr_2 = '0'
            else:
                addr_2 = '     '
            tmp_str += '{0:0>5} {1:0>5}'.format(
                addr_1, addr_2
                )

        ( CNT['pln'], CNT['page'] ) = __PRINT_LINE(
            spo, title,
            [ ctrl, '{0:0>6} {1:<26} '.format(loc, tmp_str),
              '{0:>5} {1:<72}'.format(line_num, line[:-1]),
              '{0:0>4}{1:0>4}'.format(line_num, 0), # need info
              '\n',
              ],
            CNT['pln'], CNT['page']
            )

        # process error msg, if any
        def print_err_msg(line_num, err_level):
            for tmp in INFO[err_level][line_num]:
                ( CNT['pln'], CNT['page'] ) = __PRINT_LINE(
                    spo, title,
                    [ ctrl, gen_msg(err_level, tmp, line) ],
                    CNT['pln'], CNT['page']
                    )
        MAP_INFO_GE(line_num, 'I', print_err_msg)
    ### end of main read loop

    ### summary portion of the report
    cnt_warn = len(INFO['I']) + len(INFO['N']) + len(INFO['W'])
    cnt_err  = len(INFO['E']) + len(INFO['S'])
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
    if diff:
        stmt_p_sec = int(len(spi) / diff)
    else:
        stmt_p_sec = 'INF'
    spo.append(ctrl, '*** ASSEMBLY TIME = {0:>8.3f} SECS, '.format(diff),
               '{0:>8} STATEMENT/SEC ***\n'.format(stmt_p_sec))

    if not zPE.debug_mode():
        return cnt_err          # regular process end here
    #
    # debugging information
    #
    from binascii import b2a_hex
    print '\nExternal Symbol Dictionary:'
    for key in sorted(ESD_ID.iterkeys()):
        k = ESD_ID[key]
        if ESD[k][0] and ESD[k][0].id == key:
            v = ESD[k][0]
        else:
            v = ESD[k][1]
        print '{0} => {1}'.format(k, v.__dict__)

    print '\nSymbol Cross Reference Table:'
    for key in sorted(SYMBOL.iterkeys()):
        if SYMBOL[key].value == None:
            addr = 0xFFFFFF
        else:
            addr = SYMBOL[key].value
        print '{0} (0x{1:0>6}) => {2}'.format(
            key, hex(addr)[2:].upper(), SYMBOL[key].__dict__
            )
    print '\nSymbol Cross Reference ER Sub-Table:'
    for key in sorted(SYMBOL_V.iterkeys()):
        if SYMBOL_V[key].value == None:
            addr = 0xFFFFFF
        else:
            addr = SYMBOL_V[key].value
        print '{0} (0x{1:0>6}) => {2}'.format(
            key, hex(addr)[2:].upper(), SYMBOL_V[key].__dict__
            )
    print '\nSymbol Cross Reference =Const Sub-Table:'
    for key in sorted(SYMBOL_EQ.iterkeys()):
        for indx in range(len(SYMBOL_EQ[key])):
            if SYMBOL_EQ[key][indx].value == None:
                addr = 0xFFFFFF
            else:
                addr = SYMBOL_EQ[key][indx].value
            print '{0} (0x{1:0>6}) => {2}'.format(
                key, hex(addr)[2:].upper(), SYMBOL_EQ[key][indx].__dict__
                )
    print '\nUnreferenced Symbol Defined in CSECTs:'
    for (ln, key) in sorted(NON_REF_SYMBOL, key = lambda t: t[1]):
        print '{0:>4} {1}'.format(ln, key)
    print '\nInvalid Symbol Found in CSECTs:'
    for (ln, key) in sorted(INVALID_SYMBOL, key = lambda t: t[1]):
        print '{0:>4} {1}'.format(ln, key)


    print '\nMnemonic:'
    for key in sorted(MNEMONIC.iterkeys()):
        if len(MNEMONIC[key]) == 0: # type 0
            scope = ''
        else:
            try:
                scope = zPE.f2x(MNEMONIC[key][0])
            except:
                scope = ''
        if len(MNEMONIC[key]) == 0: # type 0
            loc = ''
        elif len(MNEMONIC[key]) == 1: # type 1
            loc = ''
        elif len(MNEMONIC[key]) == 4: # type 4
            loc = hex(MNEMONIC[key][3])[2:].upper()
        else:
            loc = hex(MNEMONIC[key][1])[2:]
        tmp_str = ''
        if ( len(MNEMONIC[key]) == 3  and # type 3
             zPE.core.asm.can_get_sd(MNEMONIC[key][2]) # DC/=const
             ):
            for val in zPE.core.asm.get_sd(MNEMONIC[key][2]):
                tmp_str += zPE.core.asm.X_.tr(val.dump())
        elif len(MNEMONIC[key]) == 4: # type 4
            tmp_str += '{0:<14} {1:0>5} {0:>5}'.format(
                '', loc
                )            
        elif len(MNEMONIC[key]) == 5: # type 5
            code = zPE.core.asm.prnt_op(MNEMONIC[key][2])
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
            if MNEMONIC[key][3]:
                if MNEMONIC[key][3].valid:
                    addr_1 = hex(MNEMONIC[key][3].get()[-1])[2:].upper()
                else:
                    addr_1 = '0'
            else:
                addr_1 = '     '
            if MNEMONIC[key][4]:
                if MNEMONIC[key][4].valid:
                    addr_2 = hex(MNEMONIC[key][4].get()[-1])[2:].upper()
                else:
                    addr_2 = '0'
            else:
                addr_2 = '     '
            tmp_str += '{0:0>5} {1:0>5}'.format(
                addr_1, addr_2
                )
        print '{0:>5}: {1} {2:0>6} {3}'.format(
            key,
            scope,
            loc,
            tmp_str
            )

    print '\nInfomation:'
    print INFO['I']
    print '\nNotification:'
    print INFO['N']
    print '\nWarning:'
    print INFO['W']
    print '\nError:'
    print INFO['E']
    print '\nSevere Error:'
    print INFO['S']

    print '\nUsing Map:'
    for (k, v) in USING_MAP.iteritems():
        print k, v.__dict__

    print '\n\nObject Deck:'
    for line in zPE.core.SPOOL.retrive('SYSLIN'):
        line = b2a_hex(line)
        print ' '.join(re.findall(r'(....)', line[0   :  32])), '  ',
        print ' '.join(re.findall(r'(....)', line[32  :  64])), '  ',
        print ' '.join(re.findall(r'(....)', line[64  :  96]))
        print '{0:42}'.format(''),
        print ' '.join(re.findall(r'(....)', line[96  : 128])), '  ',
        print ' '.join(re.findall(r'(....)', line[128 : 160]))
        print
    print
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
    if line_num >= zPE.pgm.ASMA90.PARM['LN_P_PAGE']:
        page_num += 1           # new page
        line_num = __PRINT_HEADER(spool_out, title, 0, page_num)
    spool_out.append(* line_words)

    return ( line_num + zPE.SPOOL_CTRL_MAP[line_words[0][0]], page_num )


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
    spool_out.append(
        ctrl, '{0:<8} {1:<102}PAGE {2:>4}\n'.format(TITLE[0], title, page_num)
        )
    spool_out.append(
        '0',  '  LOC  OBJECT CODE    ADDR1 ADDR2  STMT   SOURCE STATEMENT\n'
        )
    return line_num + zPE.SPOOL_CTRL_MAP[ctrl] + zPE.SPOOL_CTRL_MAP['0']


def __PARSE_OUT_LDR(rc):
    spo = zPE.core.SPOOL.retrive('SYSPRINT') # (actual) output SPOOL

    ldr_ins    = zPE.pgm.HEWLDRGO.INSTRUCTION
    ldr_br     = zPE.pgm.HEWLDRGO.BRANCHING

    ldr_except = zPE.e_pop()    # get the last exception, is exists
    mem_dump   = zPE.pgm.HEWLDRGO.MEM_DUMP


    ctrl = '0'
    spo.append(ctrl, '*** PROGRAM EXECUTION BEGINNING - ANY OUTPUT BEFORE EXECUTION TIME MESSAGE IS PRODUCED BY USER PROGRAM ***\n')

    # output for the execution of the module
    # end of output for the execution of the module

    diff = TIME['exec_end'] - TIME['exec_start']
    if diff:
        ins_p_sec = int(len(ldr_ins) / diff)
    else:
        ins_p_sec = 'INF'
    spo.append(ctrl, '*** EXECUTION TIME = {0:>8.3f} SECS. '.format(diff),
               '{0:>9} INSTRUCTIONS EXECUTED - '.format(len(ldr_ins)),
               '{0:>8} INSTRUCTIONS/SEC ***\n'.format(ins_p_sec))
    spo.append(ctrl, '*** FIRST CARD NOT READ: NO CARDS READ:FILE UNOPENED\n')
    if rc >= zPE.RC['WARNING']:
        msg = 'ABNORMAL'
        # generate err msgs here
        spo.append('1', 'ASSIST COMPLETION DUMP\n')
        spo.append( ctrl, 'PSW AT ABEND ', str(zPE.core.reg.SPR['PSW']),
                    '       COMPLETION CODE {0}\n'.format(str(ldr_except)[:76])
                    ) # only capable of at most 76 characters of exception msg

        # instructions tracing
        spo.append(ctrl, '** TRACE OF INSTRUCTIONS JUST BEFORE TERMINATION: PSW BITS SHOWN ARE THOSE BEFORE CORRESPONDING INSTRUCTION DECODED ***\n')
        spo.append(ctrl, '  IM LOCATION    INSTRUCTION :  IM = PSW BITS 32-39(ILC,CC,MASK) BEFORE INSTRUCTION EXECUTED AT PROGRAM LOCATION SHOWN\n')

        code = [ ' ' * 4 ] * 3
        for ins in ldr_ins[-10 : ]: # only show last 10 instructions
            if len(ins[1]) == 12:
                code[2] = ins[1][8:12]
            else:
                code[2] = ' ' * 4
            if len(ins[1]) >= 8:
                code[1] = ins[1][4:8]
            else:
                code[1] = ' ' * 4
            code[0] = ins[1][0:4]
            spo.append(
                ctrl, '  ', zPE.b2x(ins[0][32:39]),
                '  {0:0>6}     {1} {2} {3}\n'.format(
                    hex(ins[0].Instruct_addr)[2:].upper(), * code
                    )
                )
        # append the following words to the end of the last instruction
        spo[-1, -1] = '  <-- LAST INSTRUCTION DONE - PROBABLE CAUSE OF TERMINATION\n'
        spo.append(ctrl, '\n')

        # branch tracing
        spo.append('-', '** TRACE OF LAST 10 BRANCH INSTRUCTIONS EXECUTED: PSW BITS SHOWN ARE THOSE BEFORE CORRESPONDING INSTRUCTION DECODED ***\n')
        spo.append(ctrl, '  IM LOCATION    INSTRUCTION :  IM = PSW BITS 32-39(ILC,CC,MASK) BEFORE INSTRUCTION EXECUTED AT PROGRAM LOCATION SHOWN\n')

        for ins in ldr_br[-10 : ]: # only show last 10 branches
            if len(ins[1]) == 8:
                code = ' '.join([ ins[1][:4], ins[1][4:] ])
            else:
                code = ins[1]
            spo.append(
                ctrl, '  ', zPE.b2x(ins[0][32:39]),
                '  {0:0>6}     {1}\n'.format(
                    hex(ins[0].Instruct_addr)[2:].upper(), code))

        # register dump
        spo.append(ctrl, ' REGS 0-7      ',
                   '    '.join([ str(r) for r in zPE.core.reg.GPR[ :8] ]),
                   '\n')
        spo.append(' ',  ' REGS 8-15     ',
                   '    '.join([ str(r) for r in zPE.core.reg.GPR[8: ] ]),
                   '\n')
        spo.append(ctrl, ' FLTR 0-6      ', # floating-point registers
                   '        '.join([ 'not..implemented' ] * 4),
                   '\n')

        # storage dump
        spo.append('1', 'USER STORAGE\n')
        spo.append(ctrl, mem_dump[0])
        for indx in range(1, len(mem_dump)):
            spo.append(' ', mem_dump[indx])
        spo.append(ctrl, '\n')
    else:
        msg = 'NORMAL'
    spo.append(ctrl, '*** AM004 - ', msg, ' USER TERMINATION BY RETURN ***\n')
