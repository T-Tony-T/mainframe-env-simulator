# this is the "Job Entry Subsystem" (including the "Initiator")
# this is currently only working for simple JCL

from zPE.util import *
from zPE.util.global_config import *

import zPE.util.sysmsg as sysmsg

import zPE.util.spool as spool
import zPE.base.core.SPOOL as core_SPOOL

import zPE.base.conf

import sys
import re
from time import time, localtime, strftime, strptime


def parse(job):
    invalid_lable = []          # record all invalid lables

    if job == '-':
        fp = sys.stdin
    else:
        fp = open(job, 'r')     # this is not under the control of SMS
    sp1 = spool.retrieve('JESMSGLG')    # SPOOL No. 01
    sp2 = spool.retrieve('JESJCL')      # SPOOL No. 02

    ctrl = '1'                  # control character
    sp1.append(ctrl, '{0:>27}  J O B  L O G  -'.format(SYSTEM['JEST']),
               '-  S Y S T E M  {0}  -'.format(SYSTEM['SYST']),
               '-  N O D E  {0}\n'.format(SYSTEM['NODET']))
    sp1.append('0', '\n')
    ctrl = ' '

    # initial read (for JOB card)
    line = fp.readline()
    JCL['read_cnt'] += 1
    JCL['card_cnt'] += 1
    if debug_mode():
        print line,

    if not line.startswith('//'): # invalid JCL JOB card
        abort(9, 'Error: ', line[:-1],
              ':\n       Not a valid JCL JOB card.\n')

    if len(line) > 73:          # 72+ char + '\n'
        abort(9, 'Error: line ', str(JCL['read_cnt']),
              ': Statement cannot exceed colomn 72.\n')

    #   field_0  field_1 field_2
    #   -------- ------- ------------------------------------
    # //label    JOB     <args>
    # //         EXEC    <args>
    # //maxlabel DD      <args>
    field = re.split('\s+', line[2:], 2)

    # check lable
    if bad_label(field[0]):
        invalid_lable.append(JCL['read_cnt'])

    # parse JOB card
    # currently supported parameter: region
    if field[1] != 'JOB':
        abort(9, 'Error: No JOB card found.\n')
    JCL['jobname'] = field[0]
    if len(JCL['jobname']) != 8:
        abort(9, 'Error: JOB name is not 8 charactors long.\n')
    JCL['owner'] = JCL['jobname'][:7]
    JCL['class'] = JCL['jobname'][-1]
    JCL['jobid'] = 'JOB{0:0>5}'.format(Config['job_id'])

    JCL['spool_path'] = '{0}.{1}.{2}'.format(
        JCL['owner'],
        JCL['jobname'],
        JCL['jobid']
        )

    # args_0,args_1,args_2
    # AccInfo,'pgmer'[,parameters]
    args = resplit_sq(',', field[2], 2)
    if len(args) < 2:
        abort(9, 'Error: Invalid JOB card: missing parameter(s).\n')
    # parse AccInfo
    JCL['accinfo'] = args[0]
    if args[1][0] != '\'' or args[1][-1] != '\'':
        abort(9, 'Error: ', args[1],
              ':\n       The programmer\'s name need to be ',
              'surrounded by single quotes.\n')
    # parse pgmer
    JCL['pgmer'] = args[1][1:-1]
    if len(JCL['pgmer']) > 20:
        abort(9, 'Error: ', args[1],
              ':\n       The programmer\'s name cannot be exceed ',
              '20 characters.\n')
    # parse parameters
    JCL['time']   = Config['time_limit']
    JCL['region'] = Config['memory_sz']
    if len(args) == 3:
        for part in resplit_pp(',', args[2]):
            if part[:5] == 'TIME=':
                try:
                    JCL['time'] = parse_time(part[5:])
                except SyntaxError:
                    abort(9, 'Error: ', part,
                          ': Invalid time specification.\n')
            elif part[:7] == 'REGION=':
                try:
                    JCL['region'] = parse_region(part[7:])
                except SyntaxError:
                    abort(9, 'Error: ', part,
                          ': Invalid region size.\n')
                except ValueError:
                    abort(9, 'Error: ', part,
                          ': Region must be divisible by 4K.\n')
        #   elif part[:9] == 'MSGCLASS=':

    sp1.append(ctrl, strftime('%H.%M.%S '), JCL['jobid'],
               '{0:<16}'.format(strftime(' ---- %A,').upper()),
               strftime(' %d %b %Y ----').upper(), '\n')
    sp1.append(ctrl, strftime('%H.%M.%S '), JCL['jobid'],
               '  IRR010I  USERID {0:<8}'.format(JCL['owner']),
               ' IS ASSIGNED TO THIS JOB.\n')

    # ctrl for 1st line will be modified in finish_job()
    sp2.append('c', '{0:>9}'.format(1), # should always be the first JCL card
               ' {0:<72}{1}\n'.format(line[:-1], JCL['jobid']))
    ctrl = ' '

    # main read loop
    nextline = None             # for `__READ_UNTIL()` look-ahead buffer
    last_dd  = None             # for DD concatenation
    card_lbl = None             # the label  the JCL card
    jcl_continue = None         # the action the JCL card continues
    while True:
        if nextline == None:    # no left over line in the look-ahead buffer
            line = fp.readline()
        else:                   # line exist in the look-ahead buffer
            line = nextline
            nextline = None

        # check JCL card length
        if not line:
            break
        if len(line) > 73:      # 72+ char + '\n'
            abort(9, 'Error: line ', str(JCL['read_cnt']),
                  ': Statement cannot exceed colomn 72.\n')

        JCL['read_cnt'] += 1
        # check implicit instream data
        if not line.startswith('//'):
            nextline = line     # store the line in the look-ahead buffer
            line = '//SYSIN     DD *               GENERATED STATEMENT\n'

        # check end of JCL marker
        elif len(line) == 2  or  line[2:].isspace():
            JCL['read_cnt'] -= 1    # END mark does not count
            break

        # check comment
        elif line.startswith('//*')  or  jcl_continue == '*':
            if debug_mode():
                print line,
            sp2.append(ctrl, '{0:>9} {1}'.format('', line))
            if len(line) == 73  and  line[71] != ' ':
                # 72+ char + '\n'   col 72 is non-space
                jcl_continue = '*'
            else:
                jcl_continue = None
            continue

        # starting from here, line will be guaranteed to start with "//"
        # increment line counter only for non-comment lines
        if not jcl_continue:
            JCL['card_cnt'] += 1
        if debug_mode():
            print line,

        field = re.split('\s+', line[2:])

        # check lable
        if jcl_continue and field[0]: # JCL concatenation cannot start at col 3
            abort(9, 'Error: line ', str(JCL['read_cnt']),
                  ': Cannot have labels on continuation lines.\n')
        elif bad_label(field[0]):
            invalid_lable.append(JCL['read_cnt'])

        if jcl_continue:
            if line.index(field[1]) > 15:
                abort(9, 'Error: line ', str(JCL['read_cnt']),
                      ': JCL continuation must start before col 16.\n')
        else:
            card_lbl = field[0]

        # parse EXEC card
        # currently supported parameter: parm, time, region
        # currently assumed parameter: cond=(0,NE)
        # see also: __COND_FAIL(step)
        if field[1] == 'EXEC'  or  jcl_continue == 'EXEC':
            if jcl_continue not in [ None, 'EXEC' ]:
                abort(9, 'Error: line ', str(JCL['read_cnt']),
                      ': Invalid JCL continuation.\n')
            last_dd = None

            if not jcl_continue:
                args = re.split(',', field[2], 1)
                pgm = ''
                proc = ''
                if args[0][:4] == 'PGM=':
                    pgm = args[0][4:]
                elif args[0][:5] == 'PROC=':
                    proc = args[0][5:]
                else:
                    proc = args[0]

                parm   = ''     # parameter list
                time   = JCL['time']
                region = JCL['region']
            else:
                args = [ 'continuation', field[1] ]
            jcl_continue = None

            if len(args) == 2:
                for part in resplit_pp(',', args[1]):
                    if jcl_continue: # jcl_continue can only be set by last part
                        abort(9, 'Error: line ', str(JCL['read_cnt']),
                              ': Invalid JCL card\n')
                    elif part[:5] == 'PARM=':
                        parm = part[5:]
                    elif part[:5] == 'TIME=':
                        try:
                            time = parse_time(part[5:])
                        except SyntaxError:
                            abort(9, 'Error: ', part,
                                  ': Invalid time specification.\n')
                    elif part[:7] == 'REGION=':
                        try:
                            region = parse_region(part[7:])
                        except SyntaxError:
                            abort(9, 'Error: ', part,
                                  ': Invalid region size.\n')
                        except ValueError:
                            abort(9, 'Error: ', part,
                                  ': Region must be divisible ',
                                  'by 4K.\n')
                    elif part[:5] == 'COND=':
                        pass    # assume COND=(0,NE)
                    elif part == '':
                        jcl_continue = 'EXEC'
                    else:
                        abort(9, 'Error: ', part,
                              ': Parameter not supported.\n')

            if not jcl_continue:
                JCL['step'].append(
                    JobStep(
                        name = card_lbl,
                        pgm  = pgm,
                        proc = proc,
                        time = time,
                        region = region,
                        parm = parm
                        ))

        # parse DD card
        # currently supported parameter: dsn, disp, sysout, */data
        elif field[1] == 'DD'  or  jcl_continue == 'DD':
            if jcl_continue not in [ None, 'DD' ]:
                abort(9, 'Error: line ', str(JCL['read_cnt']),
                      ': Invalid JCL continuation.\n')

            if not jcl_continue:
                sysout = ''
                dsn = []
                disp = ''
                sp_in = None    # will hold the tmp SPOOL if instream
                if not card_lbl:        # concatenated DD card
                    pass
                else:                   # new DD card
                    last_dd = card_lbl  # record the dd name
                args = field[2]
            else:
                args = field[1]
            jcl_continue = None

            if args == '*' or args == 'DATA':
                ( nextline, sp_in ) = __READ_UNTIL(fp, last_dd, '/*', nextline)
            elif args[:9] == 'DATA,DLM=\'':
                ( nextline, sp_in ) = __READ_UNTIL(fp, last_dd, args[9:11])
            elif args[:7] == 'SYSOUT=':
                sysout = args[7:]
            else:
                for part in resplit_pp(',', args):
                    if jcl_continue: # jcl_continue can only be set by last part
                        abort(9, 'Error: line ', str(JCL['read_cnt']),
                              ': Invalid JCL card\n')
                    elif part[:4] == 'DSN=':
                        dsn = conv_path(part[4:])
                    elif part[:5] == 'DISP=':
                        disp = part[5:]
                    elif part == '':
                        jcl_continue = 'DD'
                    else:
                        abort(9, 'Error: ', part,
                              ': Parameter not supported.\n')
                if not jcl_continue  and  disp == '':
                    abort(9, 'Error: ', line[:-1],
                          ': Need DISP=[disp].\n')

            if not jcl_continue:
                JCL['step'][-1].dd.append(
                    card_lbl, { # do not use last_dd, since it will be flaged
                                # as duplicated DD names
                        'SYSOUT' : sysout,
                        'DSN'    : dsn,
                        'DISP'   : disp,
                        },
                    sp_in
                    )

        # ignore other types of cards
        else:
            mark4future(field[1])

        sp2.append(ctrl, '{0:>9} {1}'.format(JCL['card_cnt'], line))
    # end of the main read loop

    sp3 = spool.retrieve('JESYSMSG') # SPOOL No. 03
    if len(invalid_lable) != 0:
        # ctrl for 1st line will be modified in finish_job()
        sp3.append('c', ' STMT NO. MESSAGE\n')
        ctrl = ' '
        for indx in invalid_lable:
            sp3.append(ctrl, '{0:>9} IEFC662I INVALID LABEL\n'.format(indx))
        sp3.append(ctrl, '\n')

        return 'label'

    return 'ok'


def init_job():
    sp1 = spool.retrieve('JESMSGLG') # SPOOL No. 01
    sp3 = spool.retrieve('JESYSMSG') # SPOOL No. 03

    JCL['jobstart'] = time()
    JCL['jobstat']  = 'STARTED'

    # ctrl for 1st line will be modified in finish_job()
    sp3.append('c', '\n')
    ctrl = ' '

    conf = zPE.base.conf.load_ICH70001I()
    line = 'ICH70001I {0:<8} LAST ACCESS AT {1}\n'.format(JCL['owner'],
                                                          conf['atime'])
    sp1.append(ctrl, strftime('%H.%M.%S '), JCL['jobid'], '  ', line)
    sp3.append(ctrl, line)
    conf['atime'] = strftime('%H:%M:%S ON %A, %B %d, %Y').upper()
    zPE.base.conf.dump_ICH70001I(conf)

    sp1.append(ctrl, strftime('%H.%M.%S '), JCL['jobid'],
               '  $HASP373 {0:<8} STARTED'.format(JCL['jobname']),
               ' - INIT {0:<4}'.format(1),                      # need info
               ' - CLASS {0}'.format(JCL['class']),
               ' - SYS {0}\n'.format(SYSTEM['SYS']))
    sp1.append(ctrl, strftime('%H.%M.%S '), JCL['jobid'],
               '  IEF403I {0:<8}'.format(JCL['jobname']),
               ' - {0}'.format(JCL['jobstat']),
               strftime(' - TIME=%H.%M.%S\n', localtime(JCL['jobstart'])))
    sp1.append(ctrl, strftime('%H.%M.%S '), JCL['jobid'],
               '  -                                              -',
               '-TIMINGS (MINS.)--            -----PAGING COUNTS----\n')
    sp1.append(ctrl, strftime('%H.%M.%S '), JCL['jobid'],
               '  -STEPNAME PROCSTEP    RC',
               '   EXCP   CONN    TCB    SRB  CLOCK   SERV',
               # TCB: Task Control Block CPU time
               #      total amount of time spent by the CPU in the execution of
               #      the job step, including the vector facility time, if used
               #
               # SRB: System Request Block CPU time
               #      time spent on behalf of the step by the system
               '  WORKLOAD  PAGE  SWAP   VIO SWAPS\n')


def init_step(step):
    sp1 = spool.retrieve('JESMSGLG') # SPOOL No. 01
    sp3 = spool.retrieve('JESYSMSG') # SPOOL No. 03

    step.start = time()
    ctrl = ' '

    # check condition
    if __COND_FAIL(step):
        sp3.append(ctrl, 'IEF202I {0:<8} '.format(JCL['jobname']),
                   step.name, ' - STEP WAS NOT RUN BECAUSE OF CONDITION CODES\n'
                   )
        return 'cond'

    sp3.append(ctrl, 'IEF236I ALLOC. FOR {0:<8} {1}\n'.format(
            JCL['jobname'], step.name))
    alloc = False               # whether allocated any file

    if 'STEPLIB' in step.dd.dict():
        for ddcard in step.dd['STEPLIB']:
            if not is_pds(ddcard['DSN']):
                # STEPLIB cannot be instream, thus DSN= should always exist
                sp3.pop()       # no file allocated
                sp3.append(ctrl, 'IEF212I {0:<8} '.format(JCL['jobname']),
                           step.name, ' STEPLIB - DATA SET NOT FOUND\n')
                ddcard['STAT'] = DD_STATUS['abnormal']
                JCL['jobstat'] = 'JOB FAILED - JCL ERROR'

                return 'steplib'

            sp3.append(ctrl, sysmsg.IGD103('STEPLIB'), '\n')
            ddcard['STAT'] = DD_STATUS['normal']
        alloc = True

    ddindx_map = {}        # { ddname : index_into_dd_concatenation, }
    for ddname in step.dd.list():
        if ddname not in ddindx_map:
            ddindx_map[ddname] = 0
        else:
            ddindx_map[ddname] += 1
        ddindx = ddindx_map[ddname]

        if step.dd[ddname][ddindx]['STAT'] != DD_STATUS['init']:
            continue            # skip the allocated ones

        # check for the f_type
        if step.dd[ddname][ddindx]['TMP_SP']:
            # instream data
            f_type = 'instream'
            sp_in = step.dd[ddname][ddindx]['TMP_SP']

            if ddindx:          # DD concatenation
                sp_real = spool.retrieve(ddname)
                while not sp_in.empty():
                    sp_real.push(sp_in.pop(0))
            else:               # new DD
                core_SPOOL.replace(ddname, sp_in)
            step.dd[ddname][ddindx]['TMP_SP'] = {
                'mode'         : sp_in.mode,
                'f_type'       : sp_in.f_type,
                'virtual_path' : sp_in.virtual_path,
                'real_path'    : sp_in.real_path,
                }
        else:
            v_path = []         # virtual path
            r_path = []         # real path
            if step.dd[ddname][ddindx]['SYSOUT'] != '':
                # outstream
                mode = 'o'
                f_type = 'outstream'
                r_path = [ ddname ]
            else:
                if step.dd[ddname][ddindx]['DSN'] != '':
                    # file
                    f_type = 'file'
                    v_path = step.dd[ddname][ddindx]['DSN']
                    r_path = step.dd[ddname][ddindx]['DSN']
                else:
                    # tmp
                    f_type = 'tmp'
                    r_path = [ ddname ]
                mode = step.dd.mode(ddname)
            if ddindx:          # DD concatenation
                core_SPOOL.load(ddname, mode, f_type, r_path)
            else:               # new DD
                core_SPOOL.new(ddname, mode, f_type, v_path, r_path)
            step.dd[ddname][ddindx]['TMP_SP'] = {
                'mode'         : mode,
                'f_type'       : f_type,
                'virtual_path' : v_path,
                'real_path'    : r_path,
                }

        if ddindx:              # DD concatenation
            action = 'CONCAT   '
        else:                   # new DD
            action = 'ALLOCATED'
        if f_type in [ 'file', 'tmp' ]:
            sp3.append(ctrl, sysmsg.IGD103(ddname, f_type, action), '\n')
        else:
            sp3.append(ctrl, sysmsg.IEF237(ddname, f_type, action), '\n')
        step.dd[ddname][ddindx]['STAT'] = DD_STATUS['normal']
        alloc = True

    if not alloc:
        sp3.pop()               # no file allocated
    return 'ok'

def finish_step(step):
    sp1 = spool.retrieve('JESMSGLG') # SPOOL No. 01
    sp3 = spool.retrieve('JESYSMSG') # SPOOL No. 03

    step.end = time()
    diff = step.end - step.start
    diff_min = diff / 60
    diff_sec = diff % 60

    ctrl = ' '
    sp1.append(ctrl, strftime('%H.%M.%S '), JCL['jobid'],
               '  -{0:<8} {1:<8}'.format(step.name, step.procname),
               ' {0:>5}  {1:>5}  {2:>5}'.format(step.rc, 0, 0), # need info
               '  {0:>5.2f}  {1:>5.2f}'.format(diff_min, diff_min),
               '  {0:>5.1f}  {1:>5}'.format(diff_min, 0),       # need info
               '  {0:<8}'.format('BATCH'),                      # need info
               '  {0:>4}  {1:>4}'.format(0, 0),                 # need info
               '  {0:>4}  {1:>4}\n'.format(0, 0))               # need info

    if step.rc == 'FLUSH':
        sp3.append(ctrl, 'IEF272I {0:<8} '.format(JCL['jobname']),
                   step.name, ' - STEP WAS NOT EXECUTED.\n')
    else:
        sp3.append(ctrl, 'IEF142I {0:<8}'.format(JCL['jobname']),
                   ' {0} - STEP WAS EXECUTED -'.format(step.name),
                   ' COND CODE {0:0>4}\n'.format(step.rc))

        if 'STEPLIB' in step.dd.dict():
            for ddcard in step.dd['STEPLIB']:
                path = ddcard['DSN']
                action = DISP_ACTION[step.dd.get_act('STEPLIB', step.rc)]
                sp3.append(ctrl,
                           sysmsg.IGD104('STEPLIB', conv_back(path), action),
                           '\n')

        ddindx_map = {}    # { ddname : index_into_dd_concatenation, }
        for ddname in step.dd.list():
            if ddname in SP_DEFAULT:    # skip default spools
                continue
            if ddname == 'STEPLIB':     # already processed
                continue

            if ddname not in ddindx_map:
                ddindx_map[ddname] = 0
            else:
                ddindx_map[ddname] += 1
            ddindx = ddindx_map[ddname]

            if step.dd[ddname][ddindx]['STAT'] != DD_STATUS['normal']:
                sys.error.write(''.join([
                            'Warning: ', ddname, ': File status is not',
                            'normal. (', step.dd[ddname][ddindx]['STAT'], ')\n',
                            '        Ignored.\n'
                            ]))
                continue

            if step.dd.is_concat(ddname):
                if not ddindx:  # first DD concatenated
                    path = spool.path_of(ddname)
                else:
                    path = step.dd[ddname][ddindx]['TMP_SP']['virtual_path']
                action = SP_MODE['i'] # must be input data
            else:
                path = spool.path_of(ddname)
                action = SP_MODE[spool.mode_of(ddname)]
            if step.dd[ddname][ddindx]['TMP_SP']['f_type'] in [ 'file', 'tmp' ]:
                action = DISP_ACTION[step.dd.get_act('STEPLIB', step.rc)]
                sp3.append(ctrl,
                           sysmsg.IGD104(ddname, conv_back(path), action),
                           '\n')
            else:
                sp3.append(ctrl,
                           sysmsg.IEF285(ddname, conv_back(path), action),
                           '\n')

            if ( step.dd.is_concat(ddname)  and # concatenated DDs
                 ddname not in spool.list()     # already removed
                 ):
                continue
            f_type = spool.type_of(ddname)
            if f_type == 'outstream':    # register outstream for writting out
                core_SPOOL.register_write(ddname, step.name)
            else:
                if f_type == 'instream': # remove instream if not PASS
                    pass
                elif f_type == 'tmp':    # remove tmp if not PASS
                    pass
                else:                    # sync file if needed
                    if step.dd.get_act(ddname) in [ 'KEEP', 'PASS', 'CATLG' ]:
                        __WRITE_OUT([ddname])
                    elif step.dd.get_act(ddname) == 'DELETE':
                        __RM_FILE([ddname])

                if step.dd.get_act(ddname) != 'PASS':
                    core_SPOOL.remove(ddname) # remove SPOOLs of the step

    sp3.append(' ', 'IEF373I STEP/{0:<8}/START '.format(step.name),
               strftime('%Y%j.%H%M\n', localtime(step.start)))
    sp3.append(' ', 'IEF374I STEP/{0:<8}/STOP  '.format(step.name),
               strftime('%Y%j.%H%M'),
               ' CPU {0:>4}MIN {1:05.2f}SEC'.format(int(diff_min), diff_sec),   
               ' SRB {0:>4}MIN {1:05.2f}SEC'.format(int(diff_min), diff_sec),
               ' VIRT {0:>5}K SYS {1:>5}K'.format('#', '#'), # need info
               ' EXT {0:>7}K SYS {1:>7}K\n'.format(0, '#'))  # need info


def finish_job(msg):
    sp1 = spool.retrieve('JESMSGLG') # SPOOL No. 01
    sp3 = spool.retrieve('JESYSMSG') # SPOOL No. 03

    if msg in ['ok', 'steprun']: # step was executed
        JCL['jobstat'] = 'ENDED'
    JCL['jobend'] = time()
    diff = JCL['jobend'] - JCL['jobstart']
    diff_min = diff / 60
    diff_sec = diff % 60

    ctrl = ' '

    sp1.append(ctrl, strftime('%H.%M.%S '), JCL['jobid'],
               '  IEF404I {0:<8}'.format(JCL['jobname']),
               ' - {0}'.format(JCL['jobstat']),
               strftime(' - TIME=%H.%M.%S\n', localtime(JCL['jobend'])))
    sp1.append(ctrl, strftime('%H.%M.%S '), JCL['jobid'],
               '  -{0:<8} ENDED.'.format(JCL['jobname']),
               '  NAME-{0:<20}'.format(JCL['pgmer']),
               ' TOTAL TCB CPU TIME=  {0:5.2f}'.format(diff_min),
               ' TOTAL ELAPSED TIME=  {0:4.1f}\n'.format(diff_min))
    sp1.append(ctrl, strftime('%H.%M.%S '), JCL['jobid'],
               '  $HASP395 {0:<8} ENDED\n'.format(JCL['jobname']))

    sp3.append(ctrl, 'IEF375I  JOB/{0:<8}/START '.format(JCL['jobname']),
               strftime('%Y%j.%H%M', localtime(JCL['jobstart'])), '\n')
    sp3.append(ctrl, 'IEF376I  JOB/{0:<8}/STOP  '.format(JCL['jobname']),
               strftime('%Y%j.%H%M', localtime(JCL['jobend'])),
               ' CPU {0:>4}MIN {1:05.2f}SEC'.format(int(diff_min), diff_sec),
               ' SRB {0:>4}MIN {1:05.2f}SEC\n'.format(int(diff_min), diff_sec))

    if msg == 'ok':
        ctrl_new = '1'          # the control character to update
    else:
        ctrl_new = ' '

    for key in SP_DEFAULT:
        sp = spool.retrieve(key)
        if sp.empty():
            continue            # empty spool
        if key in ['JESMSGLG']:
            continue            # in skip list

        sp[0,0] = ctrl_new

        if key == 'JESYSMSG' and msg != 'ok':
            sp.pop(0)

    __JES2_STAT(msg, diff)
    __WRITE_OUT(SP_DEFAULT_OUT) # write out all registered SPOOLs


### Supporting functions

def __COND_FAIL(step):
    # assume cond=(0,NE), modify if desired
    for indx in range(JCL['step'].index(step)):
        if JCL['step'][indx].rc != 0:
            return True
    return False


def __JES2_STAT(msg, job_time):
    # vvv JCL not executed vvv
    if msg in [ 'label' ]:
        ctrl = '0'
    # ^^^ JCL not executed ^^^
    # vvv JCL executed vvv
    elif msg in [ 'steplib', 'steprun', 'cond', 'ok' ]:
        ctrl = '-'
    # ^^^ JCL executed ^^^

    sp1 = spool.retrieve('JESMSGLG') # SPOOL No. 01
    sp1.append('0', '------ JES2 JOB STATISTICS ------\n')
    if msg not in ['label']:    # if JCL executed
        sp1.append(ctrl, '{0:>13}'.format(strftime(' %d %b %Y').upper()),
                   ' JOB EXECUTION DATE\n')

    sp1.append(ctrl, '{0:>13}'.format(JCL['read_cnt']), ' CARDS READ\n')

    cnt = 0
    for (k, v) in spool.dict():
        if v.mode == 'o':
            cnt += len(v.spool)
    cnt += 4                    # 4 more lines include this line
    sp1.append(ctrl, '{0:>13}'.format(cnt), ' SYSOUT PRINT RECORDS\n')

    cnt = 0                     # "punch" is currently not supported
    sp1.append(ctrl, '{0:>13}'.format(cnt), ' SYSOUT PUNCH RECORDS\n')

    cnt = 0
    for (k, v) in spool.dict():
        if v.mode == 'o':
            for line in v.spool:
                cnt = cnt + len(line)
    cnt = (cnt + 72) / 1024 + 1 # 72 more characters include this line
    sp1.append(ctrl, '{0:>13}'.format(cnt), ' SYSOUT SPOOL KBYTES\n')

    h_mm = '{0}.{1:0>2}'.format(int(job_time / 3600), int(job_time / 60) % 60)
    sp1.append(ctrl, '{0:>13}'.format(h_mm), ' MINUTES EXECUTION TIME\n')

def __READ_UNTIL(fp, fn, dlm, nextline = None):
    # prepare spool
    spt = core_SPOOL.pop_new(fn, 'i', 'instream', [], [ fn ])

    # read until encountering dlm
    if nextline == None:        # initial read not occured already
        line = fp.readline()    # perform initial read
    else:
        line = nextline         # retrieve initial read
    while True:
        JCL['read_cnt'] += 1

        # check end of stream
        if line[:2] == dlm:
            return ( None, spt )

        if (line[:2] == '//'  or  not line):
            # next JCL card, put it back to the buffer
            JCL['read_cnt'] -= 1
            return ( line, spt, )

        spt.append(line, deck_id = JCL['read_cnt'])
        line = fp.readline()    # updating read


def __WRITE_OUT(dd_list):
    for fn in dd_list:
        sp = spool.retrieve(fn)
        if sp.mode == 'i':
            continue            # input spool
        if sp.empty():
            continue            # empty spool

        core_SPOOL.flush(sp)

def __RM_FILE(dd_list):
    for fn in dd_list:
        sp = spool.retrieve(fn)
        core_SPOOL.rm_file(sp.real_path, sp.f_type)
