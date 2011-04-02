# this is not the complete module for "Job Control Language"
# this is currently only working for simple assist

import zPE

import os, sys
import re
from time import localtime, mktime, strftime, strptime


def parse(job):
    invalid_lable = []          # record all invalid lables

    fp = open(job, 'r')         # this is not under the control of SMS
    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp2 = zPE.core.SPOOL.retrive('JESJCL')   # SPOOL No. 02

    ctrl = '1'                  # control character
    sp1.append(ctrl, '{0:>27}  J O B  L O G  -'.format(zPE.SYSTEM['JEST']),
               '-  S Y S T E M  {0}  -'.format(zPE.SYSTEM['SYST']),
               '-  N O D E  {0}\n'.format(zPE.SYSTEM['NODET']))
    sp1.append('0', '\n')
    ctrl = ' '

    # initial read
    line = fp.readline()
    zPE.JCL['read_cnt'] += 1
    zPE.JCL['card_cnt'] += 1
    if len(line) > 72:
        zPE.abort(72, 'Error: line ' + str(zPE.JCL['read_cnt']) +
                  'Statement cannot exceed colomn 72.\n')

    # field_0    field_1 field_2
    # ---------- ------- ------------------------------------
    # //label    JOB     <args>
    # //         EXEC    <args>
    # //maxlabel DD      <args>
    field = re.split('\s+', line, 2)

    # check lable
    if zPE.bad_label(field[0][2:]):
        invalid_lable.append(zPE.JCL['read_cnt'])

    # parse JOB card
    # currently supported parameter: region
    if field[1] != 'JOB':
        zPE.abort(1, 'Error: No JOB card found.\n')
    zPE.JCL['jobname'] = field[0][2:]
    zPE.JCL['owner'] = zPE.JCL['jobname'][:7]
    zPE.JCL['class'] = zPE.JCL['jobname'][-1]
    zPE.JCL['jobid'] = 'JOB' + str(zPE.Config['job_id'])

    # args_0,args_1,args_2
    # AccInfo,'pgmer'[,parameters]
    args = zPE.resplit_sq(',', field[2], 2)
    if len(args) < 2:
        zPE.abort(1, 'Error: Invalid JOB card.\n')
    # parse AccInfo
    zPE.JCL['accinfo'] = args[0]
    if args[1][0] != '\'' or args[1][-1] != '\'':
        zPE.abort(1, 'Error: ' + args[1] +
                  ':\n       The programmer\'s name need to be ' +
                  'surrounded by single quotes.\n')
    # parse pgmer
    zPE.JCL['pgmer'] = args[1][1:-1]
    if len(zPE.JCL['pgmer']) > 20:
        zPE.abort(1, 'Error: ' + args[1] +
                  ':\n       The programmer\'s name cannot be exceed ' +
                  '20 characters.\n')
    # parse parameters
    zPE.JCL['region'] = zPE.Config['memory_sz']
    if len(args) == 3:
        for part in re.split(',', args[2]):
            if part[:7] == 'REGION=':
                try:
                    zPE.JCL['region'] = zPE.core.mem.parse_region(part[7:])
                except SyntaxError:
                    zPE.abort(52, 'Error: ' + part +
                              ': Invalid region size.\n')
                except ValueError:
                    zPE.abort(4, 'Error: ' + part +
                              ': Region must be divisible by 4K.\n')
        #   elif part[:9] == 'MSGCLASS=':


    zPE.Config['spool_path'] = '{0}.{1}.{2}'.format(
        zPE.JCL['owner'],
        zPE.JCL['jobname'],
        zPE.JCL['jobid']
        )

    sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
               '{0:<16}'.format(strftime(' ---- %A,').upper()),
               strftime(' %d %b %Y ----').upper(), '\n')
    sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
               '  IRR010I  USERID {0:<8}'.format(zPE.JCL['owner']),
               ' IS ASSIGNED TO THIS JOB.\n')

    # ctrl for 1st line will be modified in finish_job()
    sp2.append('c', '{0:>9}'.format(1), # should always be the first JCL card
               ' {0:<72}{1}\n'.format(line[:-1], zPE.JCL['jobid']))
    ctrl = ' '

    # main read loop
    nextline = fp.readline()
    while line != '':
        if nextline == '':
            line = fp.readline()
        else:
            line = nextline
            nextline = ''
        zPE.JCL['read_cnt'] += 1
        zPE.JCL['card_cnt'] += 1

        if len(line) > 72:
            zPE.abort(72, 'Error: line ' + str(zPE.JCL['read_cnt']) +
                      'Statement cannot exceed colomn 72.\n')

        # check comment
        if line[:3] == '//*':
            sp2.append(ctrl, '{0:>9} {1}'.format('', line))
            continue

        field = re.split('\s+', line)

        # check end of JCL
        if field[1] == '':
            zPE.JCL['read_cnt'] -= 1 # "//" does not count
            break

        # check lable
        if zPE.bad_label(field[0][2:]):
            invalid_lable.append(zPE.JCL['read_cnt'])

        # parse EXEC card
        # currently supported parameter: parm, region
        # currently assumed parameter: cond=(0,NE)
        # see also: __COND_FAIL(step)
        if field[1] == 'EXEC':
            args = re.split(',', field[2], 1)
            pgm = ''
            proc = ''
            if args[0][:4] == 'PGM=':
                pgm = args[0][4:]
            elif args[0][:5] == 'PROC=':
                proc = args[0][5:]
            else:
                proc = args[0]

            parm = ''           # parameter list
            region = zPE.JCL['region']
            if len(args) == 2:
                for part in re.split(',', args[1]):
                    if part[:5] == 'PARM=':
                        parm = part[5:]
                    elif part[:7] == 'REGION=':
                        try:
                            region = zPE.core.mem.parse_region(part[7:])
                        except SyntaxError:
                            zPE.abort(52, 'Error: ' + part +
                                      ': Invalid region size.\n')
                        except ValueError:
                            zPE.abort(4, 'Error: ' + part +
                                      ': Region must be divisible ' +
                                      'by 4K.\n')
                #   elif part[:5] == 'COND=':

            zPE.JCL['step'].append(
                zPE.Step(
                    name = field[0][2:],
                    pgm  = pgm,
                    proc = proc,
                    region = region,
                    parm = parm
                    ))
        # parse DD card
        # currently supported parameter: dsn, disp, sysout, */data
        elif field[1] == 'DD':
            sysout = ''
            dsn = []
            disp = ''
            if field[2] == '*' or field[2] == 'DATA':
                nextline = __READ_UNTIL(fp, field[0][2:], [], '/*')
            elif field[2][:9] == 'DATA,DLM=\'':
                nextline = __READ_UNTIL(fp, field[0][2:], [], field[2][9:11])
            elif field[2][:7] == 'SYSOUT=':
                sysout = field[2][7:]
            else:
                for part in re.split(',', field[2]):
                    if part[:4] == 'DSN=':
                        dsn = zPE.conv_path(part[4:])
                    elif part[:5] == 'DISP=':
                        disp = part[5:]
                    else:
                        zPE.abort(44, 'Error: ' + part +
                                  ': Parameter not supported.\n')
                if disp == '':
                    zPE.abort(44, 'Error: ' + field[0][2:] +
                              ': Need DISP=[disp].\n')

            zPE.JCL['step'][-1].dd.append(
                field[0][2:], {
                    'SYSOUT' : sysout,
                    'DSN' : dsn,
                    'DISP' : disp,
                    })
        else:                   # continuation
            zPE.abort(33, 'Error: Continuation not supported.\n')

        sp2.append(ctrl, '{0:>9} {1}'.format(zPE.JCL['card_cnt'], line))
    # end of the main read loop

    sp3 = zPE.core.SPOOL.retrive('JESYSMSG') # SPOOL No. 03
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
    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrive('JESYSMSG') # SPOOL No. 03

    zPE.JCL['jobstart'] = localtime()
    zPE.JCL['jobstat'] = 'STARTED'

    # ctrl for 1st line will be modified in finish_job()
    sp3.append('c', '\n')
    ctrl = ' '

    conf = zPE.load_ICH70001I()
    line = 'ICH70001I {0:<8} LAST ACCESS AT {1}\n'.format(zPE.JCL['owner'],
                                                          conf['atime'])
    sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'], '  ', line)
    sp3.append(ctrl, line)
    conf['atime'] = strftime('%H:%M:%S ON %A, %B %d, %Y').upper()
    zPE.dump_ICH70001I(conf)

    sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
               '  $HASP373 {0:<8} STARTED'.format(zPE.JCL['jobname']),
               ' - INIT {0:<4}'.format(1),                      # mark
               ' - CLASS {0}'.format(zPE.JCL['class']),
               ' - SYS {0}\n'.format(zPE.SYSTEM['SYS']))
    sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
               '  IEF403I {0:<8}'.format(zPE.JCL['jobname']),
               ' - {0}'.format(zPE.JCL['jobstat']),
               strftime(' - TIME=%H.%M.%S\n', zPE.JCL['jobstart']))
    sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
               '  -                                              -',
               '-TIMINGS (MINS.)--            -----PAGING COUNTS----\n')
    sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
               '  -STEPNAME PROCSTEP    RC',
               '   EXCP   CONN    TCB    SRB  CLOCK   SERV',
               '  WORKLOAD  PAGE  SWAP   VIO SWAPS\n')


def init_step(step):
    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrive('JESYSMSG') # SPOOL No. 03

    step.start = localtime()
    ctrl = ' '

    # check condition
    if __COND_FAIL(step):
        sp3.append(ctrl, 'IEF202I {0:<8} '.format(zPE.JCL['jobname']),
                   step.name, ' - STEP WAS NOT RUN BECAUSE OF CONDITION CODES\n'
                   )
        return 'cond'

    sp3.append(ctrl, 'IEF236I ALLOC. FOR {0:<8} {1}\n'.format(
            zPE.JCL['jobname'], step.name))
    alloc = False               # whether allocated any file

    if 'STEPLIB' in step.dd.dict():
        if not zPE.is_dir(step.dd['STEPLIB']['DSN']):
            # STEPLIB cannot be instream, thus DSN= should always exist
            sp3.rmline(-1)      # no file allocated
            sp3.append(ctrl, 'IEF212I {0:<8} '.format(zPE.JCL['jobname']),
                       step.name, ' STEPLIB - DATA SET NOT FOUND\n')
            step.dd['STEPLIB']['STAT'] = zPE.DD_STATUS['abnormal']
            zPE.JCL['jobstat'] = 'JOB FAILED - JCL ERROR'

            return 'steplib'

        sp3.append(ctrl, 'IGD103I {0}'.format(zPE.JES['file']),
                   ' ALLOCATED TO DDNAME STEPLIB\n')
        step.dd['STEPLIB']['STAT'] = zPE.DD_STATUS['normal']
        alloc = True

    for ddname in step.dd.list():
        if step.dd[ddname]['STAT'] != zPE.DD_STATUS['init']:
            continue            # skip the allocated ones

        # check for the f_type
        if ddname in zPE.core.SPOOL.list():
            pass          # read in but not allocate, must be instream
        else:
            v_path = []         # virtual path
            r_path = []         # real path
            if step.dd[ddname]['SYSOUT'] != '':
                # outstream
                mode = 'o'
                f_type = 'outstream'
                r_path = [
                    '{0:0>2}_{1}'.format(zPE.core.SPOOL.sz(), ddname)
                    ]
            else:
                if step.dd[ddname]['DSN'] != '':
                    # file
                    f_type = 'file'
                    v_path = [
                        '{0:0>2}_{1}'.format(zPE.core.SPOOL.sz(), ddname)
                        ]
                else:
                    # tmp
                    f_type = 'tmp'
                    r_path = [
                        '{0:0>2}_{1}'.format(zPE.core.SPOOL.sz(), ddname)
                        ]
                mode = step.dd.mode(ddname)
            zPE.core.SPOOL.new(ddname, mode, f_type, v_path, r_path)

        sp3.append(ctrl, 'IEF237I {0}'.format(zPE.JES[f_type]),
                   ' ALLOCATED TO {0}\n'.format(ddname))
        step.dd[ddname]['STAT'] = zPE.DD_STATUS['normal']
        alloc = True

    if not alloc:
        sp3.rmline(-1)      # no file allocated
    return 'ok'

def finish_step(step):
    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrive('JESYSMSG') # SPOOL No. 03
    ctrl = ' '

    sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
               '  -{0:<8} {1:<8}'.format(step.name, step.procname),
               ' {0:>5}  {1:>5}  {2:>5}'.format(step.rc, 0, 0), # mark
               '  {0:>5}  {1:>5}'.format('.00', '.00'),         # mark
               '  {0:>5}  {1:>5}'.format('.0', 0),              # mark
               '  {0:<8}'.format('BATCH'),                      # mark
               '  {0:>4}  {1:>4}'.format(0, 0),                 # mark
               '  {0:>4}  {1:>4}\n'.format(0, 0))               # mark

    if step.rc == 'FLUSH':
        sp3.append(ctrl, 'IEF272I {0:<8} '.format(zPE.JCL['jobname']),
                   step.name, ' - STEP WAS NOT EXECUTED.\n')
    else:
        sp3.append(ctrl, 'IEF142I {0:<8}'.format(zPE.JCL['jobname']),
                   ' {0} - STEP WAS EXECUTED -'.format(step.name),
                   ' COND CODE {0:0>4}\n'.format(step.rc))

        if 'STEPLIB' in step.dd.dict():
            path = step.dd['STEPLIB']['DSN']
            action = zPE.DISP_ACTION[step.dd.get_act('STEPLIB', step.rc)]
            sp3.append(ctrl, 'IGD104I {0:<44} '.format(zPE.conv_back(path)), 
                       '{0:<10} DDNAME=STEPLIB\n'.format(action + ','))

        for ddname in step.dd.list():
            if ddname in zPE.core.SPOOL.DEFAULT:        # skip default spools
                continue
            if ddname == 'STEPLIB':                     # already processed
                continue
            if step.dd[ddname]['STAT'] != zPE.DD_STATUS['normal']:
                sys.error.write('Warning: ' + ddname + ': File status is not' +
                                'normal. (' + step.dd[ddname]['STAT'] + ')\n' +
                                '        Ignored.\n')
                continue

            path = zPE.core.SPOOL.path_of(ddname)
            action = zPE.core.SPOOL.MODE[zPE.core.SPOOL.mode_of(ddname)]
            for i in range(len(path)):
                if len(path[0]) == 0:
                    del path[0]
            sp3.append(ctrl, 'IEF285I   {0:<44}'.format(zPE.conv_back(path)),
                       ' {0}\n'.format(action))

            f_type = zPE.core.SPOOL.type_of(ddname)
            if f_type == 'outstream':                   # write outstream
                __WRITE_OUT([ddname])
            elif f_type == 'instream':                  # remove instream
                pass
            elif f_type == 'tmp':                       # remove tmp
                pass
            else:                                       # sync file if needed
                if step.dd.nmend(ddname) in [ 'KEEP', 'PASS', 'CATLG' ]:
                    __WRITE_OUT([ddname])

            zPE.core.SPOOL.remove(ddname) # remove SPOOLs of the step

    sp3.append(' ', 'IEF373I STEP/{0:<8}/START '.format(step.name),
               strftime('%Y%j.%H%M\n', step.start))
    sp3.append(' ', 'IEF373I STEP/{0:<8}/STOP  '.format(step.name),
               strftime('%Y%j.%H%M'),
               ' CPU {0:>4}MIN {1}SEC'.format(0, '00.00'),      # mark
               ' SRB {0:>4}MIN {1}SEC'.format(0, '00.00'),      # mark
               ' VIRT {0:>5}K SYS {1:>5}K'.format(0, 0),        # mark
               ' EXT {0:>7}K SYS {1:>7}K\n'.format(0, 0))       # mark


def finish_job(msg):
    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrive('JESYSMSG') # SPOOL No. 03

    if msg in ['ok', 'steprun']: # step was executed
        zPE.JCL['jobstat'] = 'ENDED'
    zPE.JCL['jobend'] = localtime()

    ctrl = ' '

    sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
               '  IEF404I {0:<8}'.format(zPE.JCL['jobname']),
               ' - {0}'.format(zPE.JCL['jobstat']),
               strftime(' - TIME=%H.%M.%S\n', zPE.JCL['jobend']))
    sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
               '  -{0:<8} ENDED.'.format(zPE.JCL['jobname']),
               '  NAME-{0:<20}'.format(zPE.JCL['pgmer']),
               ' TOTAL TCB CPU TIME=    .00 TOTAL ELAPSED TIME=    .0\n')
    sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
               '  $HASP395 {0:<8} ENDED\n'.format(zPE.JCL['jobname']))

    sp3.append(ctrl, 'IEF375I  JOB/{0:<8}/START '.format(zPE.JCL['jobname']),
               strftime('%Y%j.%H%M', zPE.JCL['jobstart']), '\n')
    sp3.append(ctrl, 'IEF376I  JOB/{0:<8}/STOP  '.format(zPE.JCL['jobname']),
               strftime('%Y%j.%H%M', zPE.JCL['jobend']),
               ' CPU {0:>4}MIN {1}SEC'.format(0, '00.00'),      # mark
               ' SRB {0:>4}MIN {1}SEC\n'.format(0, '00.00'))    # mark

    if msg == 'ok':
        ctrl_new = '1'          # the control character to update
    else:
        ctrl_new = ' '

    for key in zPE.core.SPOOL.DEFAULT:
        sp = zPE.core.SPOOL.retrive(key)
        if sp.empty():
            continue            # empty spool
        if key in ['JESMSGLG']:
            continue            # in skip list

        sp[0,0] = ctrl_new

        if key == 'JESYSMSG' and msg != 'ok':
            sp.rmline(0)

    __JES2_STAT(msg)
    __WRITE_OUT(zPE.core.SPOOL.DEFAULT)


### Supporting functions

def __COND_FAIL(step):
    # assume cond=(0,NE), modify if desired
    for indx in range(zPE.JCL['step'].index(step)):
        if zPE.JCL['step'][indx].rc != 0:
            return True
    return False


def __JES2_STAT(msg):
    # vvv JCL not executed vvv
    if msg in [ 'label' ]:
        ctrl = '0'
    # ^^^ JCL not executed ^^^
    # vvv JCL executed vvv
    elif msg in [ 'steplib', 'steprun', 'cond', 'ok' ]:
        ctrl = '-'
    # ^^^ JCL executed ^^^

    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp1.append('0', '------ JES2 JOB STATISTICS ------\n')
    if msg not in ['label']:    # if JCL executed
        sp1.append(ctrl, '{0:>13}'.format(strftime(' %d %b %Y').upper()),
                   ' JOB EXECUTION DATE\n')

    sp1.append(ctrl, '{0:>13}'.format(zPE.JCL['read_cnt']), ' CARDS READ\n')

    cnt = 0
    for k,v in zPE.core.SPOOL.dict():
        if v.mode == 'o':
            cnt += len(v.spool)
    cnt += 4                    # 4 more lines include this line
    sp1.append(ctrl, '{0:>13}'.format(cnt), ' SYSOUT PRINT RECORDS\n')

    cnt = 0                     # "punch" is currently not supported
    sp1.append(ctrl, '{0:>13}'.format(cnt), ' SYSOUT PUNCH RECORDS\n')

    cnt = 0
    for k,v in zPE.core.SPOOL.dict():
        if v.mode == 'o':
            for line in v.spool:
                cnt = cnt + len(line)
    cnt = (cnt + 72) / 1024 + 1 # 72 more characters include this line
    sp1.append(ctrl, '{0:>13}'.format(cnt), ' SYSOUT SPOOL KBYTES\n')

    diff = mktime(zPE.JCL['jobend']) - mktime(zPE.JCL['jobstart'])
    h_mm = '{0}.{1:0>2}'.format(str(int(diff / 3600)), str(int(diff / 60)))
    sp1.append(ctrl, '{0:>13}'.format(h_mm), ' MINUTES EXECUTION TIME\n')

def __READ_UNTIL(fp, fn, dsn, dlm):
    # prepare spool
    sp = zPE.core.SPOOL.new(fn, 'i', 'instream', dsn)

    # read until encountering dlm
    while True:
        line = fp.readline()

        # check end of stream
        if line[:2] == dlm:
            return ''           # the return value of readline() on EOF

        # check in-stream data
        if len(dsn) == 0:
            if (line[:2] == '//'):
                return line     # next JCL card, put it back
            zPE.JCL['read_cnt'] += 1

        sp.append(line)

def __WRITE_OUT(dd_list):
    for fn in dd_list:
        sp = zPE.core.SPOOL.retrive(fn)
        if sp.mode == 'i':
            continue            # input spool
        if sp.empty():
            continue            # empty spool

        zPE.flush(sp)

