# this is not the complete module for "Job Control Language"
# this is currently only working for simple assist

import zPE

import os, sys
import re
from time import localtime, mktime, strftime, strptime


def parse(job):
    invalid_lable = []          # record all invalid lables

    fp = open(job, 'r')         # this is not under the control of SMS

    # initial read
    line = fp.readline()
    zPE.JCL['read_cnt'] += 1
    if len(line) > 72:
        sys.stderr.write('Error: line ' + str(zPE.JCL['read_cnt']) +
                         'Statement cannot exceed colomn 72.\n')
        sys.exit(72)

    field = re.split('\s', line)

    # parse JOB card
    if not zPE.ck_label(field[0][2:]):
        invalid_lable.append(zPE.JCL['read_cnt'])

    if field[1] != 'JOB':
        sys.stderr.write('Error: No JOB card found.\n')
        sys.exit(1)
    zPE.JCL['jobname'] = field[0][2:]
    zPE.JCL['owner'] = zPE.JCL['jobname'][:7]
    zPE.JCL['job'] = 'JOB' + str(zPE.Config['job_id'])

    zPE.Config['spool_path'] = zPE.JCL['jobname'] + '.' + zPE.JCL['job']

    sp = zPE.core.SPOOL.retrive('JESJCL')

    # ctrl for 1st line will be modified in finish_job()
    sp.append('c', '{0:>9} {1:<72}'.format(1, line[:-1]), zPE.JCL['job'], '\n')
    ctrl = ' '                  # control character for output

    zPE.JCL['jobstart'] = localtime()

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
            sys.stderr.write('Error: line ' + str(zPE.JCL['read_cnt']) +
                             'Statement cannot exceed colomn 72.\n')
            sys.exit(72)

        # check comment
        if line[:3] == '//*':
            sp.append(ctrl, '{0:>9} {1}'.format('', line))
            continue

        field = re.split('\s', line)

        # check end of JCL
        if field[1] == '':
            zPE.JCL['read_cnt'] -= 1 # "//" does not count
            break

        # parse EXEC card
        # currently supported parameter: parm
        if not zPE.ck_label(field[0][2:]):
            invalid_lable.append(zPE.JCL['read_cnt'])

        if field[1] == 'EXEC':
            tmp = re.split(',', field[2], 1)
            pgm = ''
            proc = ''
            if tmp[0][:4] == 'PGM=':
                pgm = tmp[0][4:]
            elif tmp[0][:5] == 'PROC=':
                proc = tmp[0][5:]
            else:
                proc = tmp[0]

            parm = ''
            if len(tmp) == 2:
                for part in re.split(',', tmp[1]):
                    if part[:5] == 'PARM=':
                        parm = part[5:]
                #   elif part[:5] == 'COND=':

            zPE.JCL['step'].append(zPE.Step(name = field[0][2:],
                                            pgm  = pgm,
                                            proc = proc,
                                            parm = parm))
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
                        sys.stderr.write('Error: ' + part +
                                         ': Parameter not supported.\n')
                        sys.exit(44)
                if disp == '':
                    sys.stderr.write('Error: ' + field[0][2:] +
                                     ': Need DISP=[disp].\n')
                    sys.exit(44)

            zPE.JCL['step'][-1].dd.append(
                field[0][2:], {
                    'SYSOUT' : sysout,
                    'DSN' : dsn,
                    'DISP' : disp,
                    })

        sp.append(ctrl, '{0:>9} {1}'.format(zPE.JCL['card_cnt'], line))
    # end of the main read loop

    # save MSGLG
    sp = zPE.core.SPOOL.retrive('JESMSGLG')
    ctrl = '1'                  # in skip list
    sp.append(ctrl, '                    J E S 2  J O B  L O G  --  S Y S T E M  S Y S 1  --  N O D E  Z O S K C T R\n')
    ctrl = '0'
    sp.append(ctrl, '\n')
    ctrl = ' '
    sp.append(ctrl, strftime("%H.%M.%S "), zPE.JCL['job'],
              '{0:<16}'.format(strftime(" ---- %A,")),
              strftime(" %d %b %Y ----"), '\n')
    sp.append(ctrl, strftime("%H.%M.%S "), zPE.JCL['job'],
              '  IRR010I  USERID {0:<8}'.format(zPE.JCL['owner']),
              ' IS ASSIGNED TO THIS JOB.\n')

    if len(invalid_lable) != 0:
        sp = zPE.core.SPOOL.retrive('JESYSMSG')
        # ctrl for 1st line will be modified in finish_job()
        sp.append('c', ' STMT NO. MESSAGE\n')
        ctrl = ' '
        for indx in invalid_lable:
            sp.append(ctrl, '{0:>9} IEFC662I INVALID LABEL\n'.format(indx))
        sp.append(ctrl, '\n')

        return 'label'

    return 'ok'


def init_job():
    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrive('JESYSMSG') # SPOOL No. 03

    # ctrl for 1st line will be modified in finish_job()
    sp3.append('c', '\n')
    ctrl = ' '

    conf = zPE.load_ICH70001I()
    line = 'ICH70001I {0:<8} LAST ACCESS AT {1}\n'.format(zPE.JCL['owner'],
                                                          conf['atime'])
    sp1.append(ctrl, strftime("%H.%M.%S "), zPE.JCL['job'], '  ', line)
    sp3.append(ctrl, line)
    conf['atime'] = strftime("%H:%M:%S ON %A, %B %d, %Y").upper()
    zPE.dump_ICH70001I(conf)

    sp1.append(ctrl, strftime("%H.%M.%S "), zPE.JCL['job'],
              '  $HASP373 {0:<8}'.format(zPE.JCL['jobname']),
              ' STARTED - INIT 1    - CLASS A - SYS SYS1\n')
    sp1.append(ctrl, strftime("%H.%M.%S "), zPE.JCL['job'],
              '  IEF403I {0:<8}'.format(zPE.JCL['jobname']),
              ' - STARTED - TIME=', strftime("%H.%M.%S"), '\n')
    sp1.append(ctrl, strftime("%H.%M.%S "), zPE.JCL['job'],
              '  -                                              --TIMINGS (MINS.)--            -----PAGING COUNTS----\n')
    sp1.append(ctrl, strftime("%H.%M.%S "), zPE.JCL['job'],
              '  -STEPNAME PROCSTEP    RC   EXCP   CONN    TCB    SRB  CLOCK   SERV  WORKLOAD  PAGE  SWAP   VIO SWAPS\n')


def init_step(step):
    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrive('JESYSMSG') # SPOOL No. 03

    step.start = localtime()
    ctrl = ' '

    sp3.append(ctrl, 'IEF236I ALLOC. FOR {0:<8} {1}\n'.format(
            zPE.JCL['jobname'], step.name))
    if 'STEPLIB' in step.dd.dict():
        if not zPE.is_dir(step.dd['STEPLIB']['DSN']):
            # STEPLIB cannot be instream, thus DSN= should always exist
            sp3.rmline(-1)
            sp3.append(ctrl, 'IEF212I {0:<8} '.format(zPE.JCL['jobname']),
                       step.name, ' STEPLIB - DATA SET NOT FOUND\n')
            sp3.append(ctrl, 'IEF272I {0:<8} '.format(zPE.JCL['jobname']),
                       step.name, ' - STEP WAS NOT EXECUTED.\n')
            step.dd['STEPLIB']['STAT'] = zPE.DD_STATUS['abnormal']
            return 'steplib'
        sp3.append(ctrl, 'IGD103I {0}'.format(zPE.JES['file']),
                   ' ALLOCATED TO DDNAME STEPLIB\n')
        step.dd['STEPLIB']['STAT'] = zPE.DD_STATUS['normal']

    for ddname in step.dd.list():
        if step.dd[ddname]['STAT'] != zPE.DD_STATUS['init']:
            continue            # skip the allocated ones

        # check for the f_type
        if ddname in zPE.core.SPOOL.list():
            # read in but not allocate, must be instream
            step.dd[ddname]['STAT'] = zPE.DD_STATUS['normal']
        else:
            if step.dd[ddname]['SYSOUT'] != '':
                # outstream
                mode = 'o'
                f_type = 'outstream'
                path = [ '{0:0>2}_{1}'.format(zPE.core.SPOOL.sz(), ddname) ]
            else:
                if step.dd[ddname]['DSN'] != '':
                    # file
                    f_type = 'file'
                    path = [ '{0:0>2}_{1}'.format(zPE.core.SPOOL.sz(), ddname) ]
                else:
                    # tmp
                    f_type = 'tmp'
                    path = [ '{0:0>2}_{1}'.format(zPE.core.SPOOL.sz(), ddname) ]
                mode = step.dd.mode(ddname)
            zPE.core.SPOOL.new(ddname, mode, f_type, path)

        sp3.append(ctrl, 'IEF237I {0}'.format(zPE.JES[f_type]),
                   ' ALLOCATED TO {0}\n'.format(ddname))

    return 'ok'


def dummy():
    sp1.append(ctrl, strftime("%H.%M.%S "), zPE.JCL['job'],
              '  IEF453I {0:<8}'.format(zPE.JCL['jobname']),
              ' - JOB FAILED - JCL ERROR - TIME=23.04.09\n')
    sp1.append(ctrl, strftime("%H.%M.%S "), zPE.JCL['job'],
              '  -{0:<8}'.format(zPE.JCL['jobname']),
              ' ENDED.  NAME-CHI ZHANG            TOTAL TCB CPU TIME=    .00 TOTAL ELAPSED TIME=    .0\n')
    sp1.append(ctrl, strftime("%H.%M.%S "), zPE.JCL['job'],
              '  $HASP395 {0:<8}'.format(zPE.JCL['jobname']),
              ' ENDED\n')


    sp3.append(ctrl, 'IEF142I {0:<8}'.format(zPE.JCL['jobname']),
              ' STEP1 - STEP WAS EXECUTED - COND CODE 0000\n')
    sp3.append(ctrl, 'IGD104I KC02293.ASSIST.LOADLIB                       RETAINED,  DDNAME=STEPLIB\n')
    sp3.append(ctrl, 'IEF285I   KC03GC4.KC03GC4A.JOB09061.D0000102.?         SYSOUT\n')
    sp3.append(ctrl, 'IEF285I   KC03GC4.KC03GC4A.JOB09061.D0000101.?         SYSIN\n')


def finish_step(step):
    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrive('JESYSMSG') # SPOOL No. 03
    ctrl = ' '

    sp1.append(ctrl, strftime("%H.%M.%S "), zPE.JCL['job'],
               '  -{0:<8} {1:<8} '.format(step.name, step.procname),
               '{0:>5} {1:>6} {2:>6} '.format(step.rc, 0, 0), # mark
               '{0:>6} {1:>6} '.format('.00', '.00'),         # mark
               '{0:>6} {1:>6} '.format('.0', 0),              # mark
               ' {0:<8} '.format('BATCH'),                    # mark
               '{0:>5} {1:>5} '.format(0, 0),                 # mark
               '{0:>5} {1:>5}\n'.format(0, 0))                # mark

    sp3.append(' ', 'IEF373I STEP/{0:<8}/START '.format(step.name),
               strftime("%Y%m%d.%H%M", step.start), '\n')
    sp3.append(' ', 'IEF373I STEP/{0:<8}/STOP  '.format(step.name),
               strftime("%Y%m%d.%H%M"), ' CPU    0MIN 00.00SEC SRB    0MIN',
               ' 00.00SEC VIRT   584K SYS   260K EXT       0K SYS   11352K\n')


def finish_job(msg):
    zPE.JCL['jobend'] = localtime()

    sp = zPE.core.SPOOL.retrive('JESYSMSG')
    sp.append(' ', 'IEF375I  JOB/{0:<8}/START '.format(zPE.JCL['jobname']),
              strftime("%Y%m%d.%H%M", zPE.JCL['jobstart']), '\n')
    sp.append(' ', 'IEF376I  JOB/{0:<8}/STOP  '.format(zPE.JCL['jobname']),
              strftime("%Y%m%d.%H%M", zPE.JCL['jobend']), ' CPU    0MIN'
              ' 00.00SEC SRB    0MIN 00.00SEC\n')

    for key in zPE.core.SPOOL.list():
        sp = zPE.core.SPOOL.retrive(key)
        if sp.mode  == 'i':
            continue            # input spool
        if sp.empty():
            continue            # empty spool
        if key in ['JESMSGLG']:
            continue            # in skip list

        if msg == 'ok':
            sp[0,0] = '1'
        else:
            if key == 'JESYSMSG':
                sp.rmline(0)
            else:
                sp[0,0] = ' '

    __JES2_STAT(msg)
    __WRITE_OUT()


### Supporting functions

def __JES2_STAT(msg):
    # vvv JCL not executed vvv
    if msg == 'label':
        ctrl = '0'
    elif msg == 'steplib':
        ctrl = '-'
    # ^^^ JCL not executed ^^^
    # vvv JCL executed vvv
    elif msg == 'ok':
        ctrl = '-'
    # ^^^ JCL executed ^^^

    sp = zPE.core.SPOOL.retrive('JESMSGLG')
    sp.append('0', '------ JES2 JOB STATISTICS ------\n')
    if msg not in ['label']:    # if JCL executed
        sp.append(ctrl, '{0:>13}'.format(strftime(" %d %b %Y")),
                  ' JOB EXECUTION DATE\n')

    sp.append(ctrl, '{0:>13}'.format(zPE.JCL['read_cnt']), ' CARDS READ\n')

    cnt = 0
    for k,v in zPE.core.SPOOL.dict():
        if v.mode == 'o':
            cnt += len(v.spool)
    cnt += 4                    # 4 more lines include this line
    sp.append(ctrl, '{0:>13}'.format(cnt), ' SYSOUT PRINT RECORDS\n')

    cnt = 0                     # "punch" is currently not supported
    sp.append(ctrl, '{0:>13}'.format(cnt), ' SYSOUT PUNCH RECORDS\n')

    cnt = 0
    for k,v in zPE.core.SPOOL.dict():
        if v.mode == 'o':
            for line in v.spool:
                cnt = cnt + len(line)
    cnt = (cnt + 72) / 1024 + 1 # 72 more characters include this line
    sp.append(ctrl, '{0:>13}'.format(cnt), ' SYSOUT SPOOL KBYTES\n')

    diff = mktime(zPE.JCL['jobend']) - mktime(zPE.JCL['jobstart'])
    h_mm = '{0}.{1:0>2}'.format(str(int(diff / 3600)), str(int(diff / 60)))
    sp.append(ctrl, '{0:>13}'.format(h_mm), ' MINUTES EXECUTION TIME\n')

def __READ_UNTIL(fp, fn, dsn, dlm):
    # prepare spool
    zPE.core.SPOOL.new(fn, 'i', 'instream', dsn)
    sp = zPE.core.SPOOL.retrive(fn)

    # read until encountering dlm
    while True:
        line = fp.readline()

        # check end of stream
        if line == dlm:
            return ''           # the return value of readline() on EOF

        # check in-stream data
        if len(dsn) == 0:
            if (line[:2] == '//'):
                return line     # next JCL card, put it back
            zPE.JCL['read_cnt'] += 1

        sp.append(line)

def __WRITE_OUT():
    for fn in zPE.core.SPOOL.list():
        sp = zPE.core.SPOOL.retrive(fn)
        if sp.mode == 'i':
            continue            # input spool
        if sp.empty():
            continue            # empty spool

        zPE.flush(sp)

