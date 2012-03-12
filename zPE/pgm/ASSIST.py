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
#     FT05F001  data file for XREAD; default to instream data
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

from asma90_config import *   # read resource file for ASM config + rc
from hewldrgo_config import * # read resource file for LDR config + rc

from assist_err_code_rc import *        # read recourse file for err msg
from assist_pseudo_ins import PSEUDO_INS, PSEUDO_OP # load pseudo-instructions


FILE_CHK = [                    # files to be checked
    'SYSIN', 'FT05F001', 'SYSPRINT',
    ]
FILE_REQ = {                    # files that are required
    'SYSIN'    : 'AM002 ASSIST COULD NOT OPEN READER SYSIN:ABORT',
    'SYSPRINT' : 'AM001 ASSIST COULD NOT OPEN PRINTER FT06F001:ABORT',
    }
FILE_GEN = {                    # files that will be generated if missing
    'FT05F001' : lambda : zPE.core.SPOOL.new('FT05F001', '+', 'tmp', '', ''),
    }
FILE_MISSING = [ ]              # files that are missing


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

    # load in all the pseudo instructions
    zPE.core.asm.pseudo.update(PSEUDO_INS)
    zPE.core.cpu.ins_op.update(PSEUDO_OP)

    limit = 0 # error tolerance limit; currently hard coded. need info

    # invoke parser from ASMA90 to assemble the source code
    zPE.core.SPOOL.new('SYSLIN', '+', 'tmp', '', '') # new,pass,delete
    zPE.core.SPOOL.new('SYSUT1', '+', 'tmp', '', '') # new,delete,delete


    # load the user-supplied PARM and config into the default configuration
    asm_load_parm({
            'AMODE'     : 24,
            'RMODE'     : 24,
            })
    asm_load_config({
            'MEM_POS'   : 0,    # always start at 0x000000 for ASSIST
            'REGION'    : step.region,
            })

    TIME['asm_start'] = time()
    zPE.pgm.ASMA90.pass_1()
    zPE.pgm.ASMA90.pass_2()
    TIME['asm_end'] = time()

    err_cnt = __PARSE_OUT_ASM(limit)

    # get instream data, if not specified in DD card
    spo = zPE.core.SPOOL.retrieve('FT05F001')
    if 'FT05F001' in FILE_MISSING:
        spi = zPE.core.SPOOL.retrieve('SYSIN')
        while not spi.empty():
            spo.append('{0:<72}{1:0>4}{2:0>4}\n'.format(
                    spi[0][:-1], spi.deck_id(0), '----' # need info
                    ))
            spi.pop(0)
    else:
        for indx in range(len(spo)):
            spo[indx] = '{0:<80}\n'.format(spo[indx][:-1])
    spi = None                  # unlink spi
    spo = None                  # unlink spo

    # calculate memory needed to execute the module
    required_mem_sz = 0
    for esd in ESD.itervalues():
        if esd[0]:
            sz = esd[0].addr + esd[0].length
            if sz > required_mem_sz:
                required_mem_sz = sz

    asm_init_res()              # release resources
    zPE.core.SPOOL.remove('SYSUT1')

    if err_cnt > limit:
        if 'FT05F001' in FILE_MISSING:
            zPE.core.SPOOL.remove('FT05F001')
        zPE.core.SPOOL.remove('SYSLIN')
        return zPE.RC['NORMAL'] # skip exec, return with "CC = 0"

    # invoke HEWLDRGO to link-edit and execute the object module
    zPE.core.SPOOL.new('SYSLOUT', 'o', 'outstream', '', '') # new,delete,delete
    zPE.core.SPOOL.pretend('XREAD',    'FT05F001') # XREAD    -> FT05F001
    zPE.core.SPOOL.pretend('XPRNT',    'SYSLOUT')  # XPRNT    -> SYSLOUT
    zPE.core.SPOOL.pretend('XSNAPOUT', 'SYSLOUT')  # XSNAPOUT -> SYSLOUT

    # load the user-supplied PARM and config into the default configuration
    ldr_load_parm({
            'AMODE'   : 24,
            'RMODE'   : 24,
            'PSWKEY'  : 12, # 12 is the key used by ASSIST on "marist"
            })
    ldr_load_config({
            'MEM_POS' : 0,      # always start at 0x000000 for ASSIST
            'MEM_LEN' : required_mem_sz,
            'TIME'    : min(
                zPE.JCL['jobstart'] + zPE.JCL['time'] - time(), # job limit
                step.start + step.time - time()                 # step limit
                ),
            'REGION'  : step.region,
            })

    # initialize all register to "F4F4F4F4"
    for reg in zPE.core.reg.GPR:
        reg.long = 0xF4F4F4F4

    # load OBJMOD into memory, and execute it
    TIME['exec_start'] = time()
    rc = zPE.pgm.HEWLDRGO.go(zPE.pgm.HEWLDRGO.load())
    TIME['exec_end'] = time()

    if 'FT05F001' in FILE_MISSING:
        zPE.core.SPOOL.remove('FT05F001')
    zPE.core.SPOOL.remove('XREAD')    # unlink XREAD

    __PARSE_OUT_LDR(rc)

    ldr_init_res()              # release resources

    zPE.core.SPOOL.remove('SYSLIN')
    zPE.core.SPOOL.remove('SYSLOUT')
    zPE.core.SPOOL.remove('XPRNT')    # unlink XPRNT
    zPE.core.SPOOL.remove('XSNAPOUT') # unlink XSNAPOUT

    return zPE.RC['NORMAL']


### Supporting Functions
def __MISSED_FILE(step, i):
    if i >= len(FILE_CHK):
        return 0                # termination condition

    sp1 = zPE.core.SPOOL.retrieve('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrieve('JESYSMSG') # SPOOL No. 03
    ctrl = ' '

    if FILE_CHK[i] not in zPE.core.SPOOL.list(): # not offered
        sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
                   '  IEC130I {0:<8}'.format(FILE_CHK[i]),
                   ' DD STATEMENT MISSING\n')
        sp3.append(ctrl, 'IEC130I {0:<8}'.format(FILE_CHK[i]),
                   ' DD STATEMENT MISSING\n')
        FILE_MISSING.append(FILE_CHK[i])

    cnt = __MISSED_FILE(step, i+1)

    if FILE_CHK[i] not in zPE.core.SPOOL.list():
        if FILE_CHK[i] in FILE_REQ:
            sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
                       '  +{0}\n'.format(FILE_REQ[FILE_CHK[i]]))
            sp3.append(ctrl, '{0}\n'.format(FILE_REQ[FILE_CHK[i]]))
            cnt += 1
        else:
            FILE_GEN[FILE_CHK[i]]()

    return cnt


def __PARSE_OUT_ASM(limit):
    spi = zPE.core.SPOOL.retrieve('SYSUT1')   # input SPOOL
    spo = zPE.core.SPOOL.retrieve('SYSPRINT') # output SPOOL

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

    for line_num in range(init_line_num, len(spi) + 1):
        # loop through line_num (indx + 1)
        line = spi[line_num - 1]
        line_did = spi.deck_id(line_num - 1)
        ctrl = ' '

        if line_num not in MNEMONIC:
            # comment, EJECT, SPACE, MACRO definition, etc.
            field = zPE.resplit_sq(r'\s+', line[:-1], 3)

            if len(field) > 1 and field[1] == 'EJECT':
                ( CNT['pln'], CNT['page'] ) = __PRINT_LINE(
                    spo, title, [ ], CNT['pln'], CNT['page'],
                    new_page = True, print_none = True
                    )
                continue

            elif len(field) > 1 and field[1] == 'SPACE':
                p_line = [ ]
                if len(field) > 2:
                    space_n = int(field[2])
                else:
                    space_n = 1
                line_left = ASM_PARM['LN_P_PAGE'] - CNT['pln']
                for i in range(min(space_n, line_left)):
                    ( CNT['pln'], CNT['page'] ) = __PRINT_LINE(
                        spo, title, [ ' \n' ], CNT['pln'], CNT['page']
                        )
                continue

            if line_did == None:
                p_line = [      # regular input line
                    ctrl, '{0:>6} {1:<26} '.format(' ', ' '),
                    '{0:>5} {1:<72}'.format(line_num, line[:-1]),
                    '{0:8}'.format(''), # 8 spaces
                    '\n',
                    ]

            elif isinstance(line_did, int) or line_did.isdigit():
                p_line = [      # regular input line
                    ctrl, '{0:>6} {1:<26} '.format(' ', ' '),
                    '{0:>5} {1:<72}'.format(line_num, line[:-1]),
                    '{0:0>4}{1:0>4}'.format(line_did, '----'), # need info
                    '\n',
                    ]

            else:
                p_line = [      # expanded line
                    ctrl, '{0:>6} {1:<26} '.format(' ', ' '),
                    '{0:>5}+{1:<72}'.format(line_num, line[:-1]),
                    line_did,   # deck ID
                    '\n',
                    ]

            ( CNT['pln'], CNT['page'] ) = __PRINT_LINE(
                spo, title, p_line, CNT['pln'], CNT['page']
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
        elif len(MNEMONIC[line_num]) == 1: # type 1
            if MNEMONIC[line_num][0]:
                loc = zPE.i2h(MNEMONIC_LOC[line_num])
            else:               # no scope, no info to print
                loc = ''
        elif MNEMONIC[line_num][0] == None: # no scope ==> END (type 2)
            loc = ''
        elif len(MNEMONIC[line_num]) == 4: # type 4, EQU
            loc = zPE.i2h(MNEMONIC[line_num][3])
        else:                       # type 2/3/5, inside CSECT or DSECT
            loc = zPE.i2h(MNEMONIC_LOC[line_num])

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
                addr_1 = zPE.i2h(MNEMONIC[line_num][3])
            else:
                addr_1 = '     '
            if MNEMONIC[line_num][4]:
                addr_2 = zPE.i2h(MNEMONIC[line_num][4])
            else:
                addr_2 = '     '
            tmp_str += '{0:0>5} {1:0>5}'.format(
                addr_1, addr_2
                )

        if line_did == None:
            p_line = [      # regular input line
                ctrl, '{0:0>6} {1:<26} '.format(loc, tmp_str),
                '{0:>5} {1:<72}'.format(line_num, line[:-1]),
                '{0:8}'.format(''), # 8 spaces
                '\n',
                ]
        elif isinstance(line_did, int) or line_did.isdigit():
            p_line = [      # regular input line
                ctrl, '{0:0>6} {1:<26} '.format(loc, tmp_str),
                '{0:>5} {1:<72}'.format(line_num, line[:-1]),
                '{0:0>4}{1:0>4}'.format(line_did, '----'), # need info
                '\n',
                ]
        else:
            p_line = [      # expanded line
                ctrl, '{0:0>6} {1:<26} '.format(loc, tmp_str),
                '{0:>5}+{1:<72}'.format(line_num, line[:-1]),
                line_did,   # deck ID
                '\n',
                ]
        ( CNT['pln'], CNT['page'] ) = __PRINT_LINE(
            spo, title, p_line, CNT['pln'], CNT['page']
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
    print '\nMnemonic:'
    for key in sorted(MNEMONIC.iterkeys()):
        if len(MNEMONIC[key]) == 0: # type 0
            scope = ' ' * 8
        else:
            try:
                scope = zPE.f2x(MNEMONIC[key][0])
            except:
                scope = ' ' * 8
        if len(MNEMONIC[key]) == 0: # type 0
            loc = ''
        elif len(MNEMONIC[key]) == 1: # type 1
            loc = ''
        elif len(MNEMONIC[key]) == 4: # type 4
            loc = zPE.i2h(MNEMONIC[key][3])
        else:
            loc = zPE.i2h(MNEMONIC[key][1])
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
                addr_1 = zPE.i2h(MNEMONIC[key][3])
            else:
                addr_1 = '     '
            if MNEMONIC[key][4]:
                addr_2 = zPE.i2h(MNEMONIC[key][4])
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
    print '\nMnemonic Location Remapping:'
    for line_num in MNEMONIC_LOC:
        if ( len(MNEMONIC[line_num]) < 2  or
             MNEMONIC[line_num][1] != MNEMONIC_LOC[line_num]
             ):
            if len(MNEMONIC[line_num]) < 2:
                org_loc = ''
            elif MNEMONIC[line_num][1] == None:
                org_loc = '[None]'
            else:
                org_loc = MNEMONIC[line_num][1]
            print 'line {0:>4}: {1:0>6} => {2:0>6}'.format(
                line_num, org_loc,
                zPE.i2h(MNEMONIC_LOC[line_num])
                )

    from binascii import b2a_hex
    print '\n\nObject Deck:'
    for line in zPE.core.SPOOL.retrieve('SYSLIN'):
        line = b2a_hex(line).upper()
        print ' '.join(zPE.fixed_width_split(8, line[0   :  32])), '  ',
        print ' '.join(zPE.fixed_width_split(8, line[32  :  64])), '  ',
        print ' '.join(zPE.fixed_width_split(8, line[64  :  96]))
        print '{0:38}'.format(''),
        print ' '.join(zPE.fixed_width_split(8, line[96  : 128])), '  ',
        print ' '.join(zPE.fixed_width_split(8, line[128 : 160]))
        print
    print
    # end of debugging
    return cnt_err


def __PRINT_LINE(spool_out, title, line_words, line_num, page_num,
                 new_page = False, print_none = False):
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

    new_page
        force the line to be printed on a new page
    print_none
        ignore the line to be printed. used with `new_page` to force page switch

    return value
        a two-tuple containing the new line number
        and the new page number after the line is
        inserted
    '''
    if new_page or line_num >= ASM_PARM['LN_P_PAGE']:
        page_num += 1           # new page
        line_num = __PRINT_HEADER(spool_out, title, 0, page_num)
    if print_none:
        ctrl = None
    else:
        spool_out.append(* line_words)
        ctrl = line_words[0][0]

    return ( line_num + zPE.SPOOL_CTRL_MAP[ctrl], page_num )


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
    spi = zPE.core.SPOOL.retrieve('SYSLOUT')  # LOADER output SPOOL
    spo = zPE.core.SPOOL.retrieve('SYSPRINT') # ASSIST output SPOOL

    ldr_except = zPE.e_pop()    # get the last exception, is exists

    ctrl = '0'
    spo.append(ctrl, '*** PROGRAM EXECUTION BEGINNING - ANY OUTPUT BEFORE EXECUTION TIME MESSAGE IS PRODUCED BY USER PROGRAM ***\n')

    # output for the execution of the module
    if len(spi):
        spi[0] = '1' + spi[0][1:]   # start an new page on the report
    for line in spi:
        spo.append(line)
    # end of output for the execution of the module

    diff = TIME['exec_end'] - TIME['exec_start']
    if diff:
        ins_p_sec = int(len(INSTRUCTION) / diff)
    else:
        ins_p_sec = 'INF'
    spo.append(ctrl, '*** EXECUTION TIME = {0:>8.3f} SECS. '.format(diff),
               '{0:>9} INSTRUCTIONS EXECUTED - '.format(len(INSTRUCTION)),
               '{0:>8} INSTRUCTIONS/SEC ***\n'.format(ins_p_sec))
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
        for ins in INSTRUCTION[-10 : ]: # only show last 10 instructions
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
                    zPE.i2h(ins[0].Instruct_addr), * code
                    )
                )
        # append the following words to the end of the last instruction
        spo[-1, -1] = '  <-- LAST INSTRUCTION DONE - PROBABLE CAUSE OF TERMINATION\n'
        spo.append(ctrl, '\n')

        # branch tracing
        spo.append('-', '** TRACE OF LAST 10 BRANCH INSTRUCTIONS EXECUTED: PSW BITS SHOWN ARE THOSE BEFORE CORRESPONDING INSTRUCTION DECODED ***\n')
        spo.append(ctrl, '  IM LOCATION    INSTRUCTION :  IM = PSW BITS 32-39(ILC,CC,MASK) BEFORE INSTRUCTION EXECUTED AT PROGRAM LOCATION SHOWN\n')

        for ins in BRANCHING[-10 : ]: # only show last 10 branches
            if len(ins[1]) == 8:
                code = ' '.join([ ins[1][:4], ins[1][4:] ])
            else:
                code = ins[1]
            spo.append(
                ctrl, '  ', zPE.b2x(ins[0][32:39]),
                '  {0:0>6}     {1}\n'.format(
                    zPE.i2h(ins[0].Instruct_addr), code))

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
        if len(MEM_DUMP):
            spo.append(ctrl, MEM_DUMP[0])
        for indx in range(1, len(MEM_DUMP)):
            spo.append(' ', MEM_DUMP[indx])
        spo.append(ctrl, '\n')
    else:
        msg = 'NORMAL'
    spo.append(ctrl, '*** AM004 - ', msg, ' USER TERMINATION BY RETURN ***\n')
