# this is not the complete module for JCL
# this is currently only working for simple assist

import zPE

import os, sys
import re
from time import localtime, mktime, strftime, strptime

def parse(src):
    invalid_lable = []          # record all invalid lables

    fp = open(src, 'r')
    sp = zPE.SPOOL['JESJCL'][0]

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
    for k,v in zPE.SPOOL.items(): # add in path to pre-defined spool
        v[2] = [ zPE.Config['spool_path'],
                 zPE.JCL['jobname'] + '.' + zPE.JCL['job']
                 ] + v[2]

    # ctrl for 1st line will be added in finish_job()
    sp.append('{0:>9}'.format(1) + ' {0:<72}'.format(line[:-1]) +
              zPE.JCL['job'] + '\n')
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
            sp.append(ctrl + '{0:>9}'.format('') + ' ' + line)
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
        # currently supported parameter: dsn, disp(simplified), sysout, */data
        elif field[1] == 'DD':
            sysout = ''
            dsn = []
            disp = 'NEW'
            if field[2] == '*' or field[2] == 'DATA':
                nextline = __READ_UNTIL(fp, field[0][2:], [], '/*')
            elif field[2][:9] == 'DATA,DLM=\'':
                nextline = __READ_UNTIL(fp, field[0][2:], [], field[2][9:11])
            elif field[2][:7] == 'SYSOUT=':
                sysout = field[2][7:]
            elif field[2][:4] == 'DSN=':
                tmp = re.split(',', field[2], 1)
                dsn = zPE.conv_path(tmp[0][4:])
                if len(tmp) == 2:
                    for part in re.split(',', tmp[1]):
                        if part[:5] == 'DISP=':
                            disp = part[5:]
            else:
                sys.stderr.write('Error: ' + re.split(',', field[2], 1)[0] +
                                 ': Parameter not supported.\n')
                sys.exit(44)

            zPE.JCL['step'][-1].append_dd(
                field[0][2:], {
                    'SYSOUT' : sysout,
                    'DSN' : dsn,
                    'DISP' : disp,
                    })

        sp.append(ctrl + '{0:>9}'.format(zPE.JCL['card_cnt']) + ' ' + line)
    # end of the main read loop

    # save MSGLG
    sp = zPE.SPOOL['JESMSGLG'][0]
    ctrl = '1'                  # in skip list
    sp.append(ctrl + '                    J E S 2  J O B  L O G  --  S Y S T E M  S Y S 1  --  N O D E  Z O S K C T R\n')
    ctrl = '0'
    sp.append(ctrl + '\n')
    ctrl = ' '
    sp.append(ctrl + strftime("%H.%M.%S ") + zPE.JCL['job'] +
              '{0:<16}'.format(strftime(" ---- %A,")) +
              strftime(" %d %b %Y ----") + '\n')
    sp.append(ctrl + strftime("%H.%M.%S ") + zPE.JCL['job'] +
              '  IRR010I  USERID {0:<8}'.format(zPE.JCL['owner']) +
              ' IS ASSIGNED TO THIS JOB.\n')

    if len(invalid_lable) != 0:
        sp = zPE.SPOOL['JESYSMSG'][0]
        # ctrl for 1st line will be added in finish_job()
        sp.append(' STMT NO. MESSAGE\n')
        ctrl = ' '
        for indx in invalid_lable:
            sp.append(ctrl + '{0:>9} IEFC662I INVALID LABEL\n'.format(indx))
        sp.append(ctrl + '\n')

        return 'label'

    return 'ok'


def init_step(step):
    sp0 = zPE.SPOOL['JESMSGLG'][0] # spool No. 0
    sp2 = zPE.SPOOL['JESYSMSG'][0] # spool No. 2

    # ctrl for 1st line will be added in finish_job()
    sp2.append('\n')
    ctrl = ' '

    step.start = (
        ctrl + 'IEF373I STEP/{0:<8}/START '.format(step.name) +
        strftime("%Y%m%d.%H%M") + '\n'
        )

    conf = zPE.load_ICH70001I()
    line = 'ICH70001I {0:<8} LAST ACCESS AT {1}\n'.format(zPE.JCL['owner'], conf['atime'])
    sp2.append(ctrl + line)
    sp0.append(ctrl + strftime("%H.%M.%S ") + zPE.JCL['job'] + '  ' + line)
    conf['atime'] = strftime("%H:%M:%S ON %A, %B %d, %Y").upper()
    zPE.dump_ICH70001I(conf)
    
    #dummy()

    sp2.append(ctrl + 'IEF236I ALLOC. FOR {0:<8} {1}\n'.format(
            zPE.JCL['jobname'], step.name))
    if 'STEPLIB' in step.dd:
        if not zPE.is_dir(step.dd['STEPLIB'][1]['DSN']):
            del sp2[-1]
            sp2.append(ctrl + 'IEF212I KC03GC4A ' + step.name +
                       ' STEPLIB - DATA SET NOT FOUND\n')
            sp2.append(ctrl + 'IEF272I KC03GC4A ' + step.name +
                       ' - STEP WAS NOT EXECUTED.\n')
            return 'steplib'
        sp2.append(ctrl + 'IGD103I SMS ALLOCATED TO DDNAME STEPLIB\n')

    #dummy()

    return 'ok'


def dummy():
    sp.append(ctrl + '23.04.09 JOB05799  $HASP373 KC03GC4A STARTED - INIT 1    - CLASS A - SYS SYS1\n')
    sp.append(ctrl + '23.04.09 JOB05799  IEF403I KC03GC4A - STARTED - TIME=23.04.09\n')
    sp.append(ctrl + '23.04.09 JOB05799  -                                              --TIMINGS (MINS.)--            -----PAGING COUNTS----\n')
    sp.append(ctrl + '23.04.09 JOB05799  -STEPNAME PROCSTEP    RC   EXCP   CONN    TCB    SRB  CLOCK   SERV  WORKLOAD  PAGE  SWAP   VIO SWAPS\n')
    sp.append(ctrl + '23.04.09 JOB05799  -STEP1             FLUSH      0      0    .00    .00     .0      0  BATCH        0     0     0     0\n')
    sp.append(ctrl + '23.04.09 JOB05799  IEF453I KC03GC4A - JOB FAILED - JCL ERROR - TIME=23.04.09\n')
    sp.append(ctrl + '23.04.09 JOB05799  -KC03GC4A ENDED.  NAME-CHI ZHANG            TOTAL TCB CPU TIME=    .00 TOTAL ELAPSED TIME=    .0\n')
    sp.append(ctrl + '23.04.09 JOB05799  $HASP395 KC03GC4A ENDED\n')


    sp2.append(ctrl + 'IEF237I JES2 ALLOCATED TO SYSPRINT\n')
    sp2.append(ctrl + 'IEF237I JES2 ALLOCATED TO SYSIN\n')
    sp2.append(ctrl + 'IEF142I KC03GC4A STEP1 - STEP WAS EXECUTED - COND CODE 0000\n')
    sp2.append(ctrl + 'IGD104I KC02293.ASSIST.LOADLIB                       RETAINED,  DDNAME=STEPLIB\n')
    sp2.append(ctrl + 'IEF285I   KC03GC4.KC03GC4A.JOB09061.D0000102.?         SYSOUT\n')
    sp2.append(ctrl + 'IEF285I   KC03GC4.KC03GC4A.JOB09061.D0000101.?         SYSIN\n')


def finish_step(step):
    sp = zPE.SPOOL['JESYSMSG'][0]
    sp.append(step.start)
    sp.append(' ' + 'IEF373I STEP/{0:<8}/STOP  '.format(step.name) +
              strftime("%Y%m%d.%H%M") + ' CPU    0MIN 00.00SEC SRB    0MIN' +
              ' 00.00SEC VIRT   584K SYS   260K EXT       0K SYS   11352K\n')


def finish_job(msg):
    zPE.JCL['jobend'] = localtime()

    sp = zPE.SPOOL['JESYSMSG'][0]
    sp.append(' ' + 'IEF375I  JOB/{0:<8}/START '.format(zPE.JCL['jobname']) +
              strftime("%Y%m%d.%H%M", zPE.JCL['jobstart']) + '\n')
    sp.append(' ' + 'IEF376I  JOB/{0:<8}/STOP  '.format(zPE.JCL['jobname']) +
              strftime("%Y%m%d.%H%M", zPE.JCL['jobend']) + ' CPU    0MIN'
              ' 00.00SEC SRB    0MIN 00.00SEC\n')

    for fn in zPE.SPOOL.keys():
        sp = zPE.SPOOL[fn][0]
        if zPE.SPOOL[fn][1] in ['i', 't']:
            continue            # input / tmp spool
        if len(sp) == 0:
            continue            # empty spool
        if fn in ['JESMSGLG']:
            continue            # in skip list

        if msg == 'ok':
            sp[0] = '1' + sp[0]
        else:
            if fn == 'JESYSMSG':
                del sp[0]
            else:
                sp[0] = ' ' + sp[0]

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

    sp = zPE.SPOOL['JESMSGLG'][0]
    sp.append('0' + '------ JES2 JOB STATISTICS ------\n')
    if msg not in ['label']:    # if JCL executed
        sp.append(ctrl + '{0:>13}'.format(strftime(" %d %b %Y")) +
                  ' JOB EXECUTION DATE\n')

    sp.append(ctrl + '{0:>13}'.format(zPE.JCL['read_cnt']) + ' CARDS READ\n')

    cnt = 0
    for k,v in zPE.SPOOL.items():
        if v[1] == 'o':
            cnt += len(v[0])
    cnt += 4                    # 4 more lines include this line
    sp.append(ctrl + '{0:>13}'.format(cnt) + ' SYSOUT PRINT RECORDS\n')

    cnt = 0                     # "punch" is currently not supported
    sp.append(ctrl + '{0:>13}'.format(cnt) + ' SYSOUT PUNCH RECORDS\n')

    cnt = 0
    for k,v in zPE.SPOOL.items():
        if v[1] == 'o':
            for line in v[0]:
                cnt = cnt + len(line)
    cnt = (cnt + 72) / 1024 + 1 # 72 more characters include this line
    sp.append(ctrl + '{0:>13}'.format(cnt) + ' SYSOUT SPOOL KBYTES\n')

    diff = mktime(zPE.JCL['jobend']) - mktime(zPE.JCL['jobstart'])
    h_mm = '{0}.{1:0>2}'.format(str(int(diff / 3600)), str(int(diff / 60)))
    sp.append(ctrl + '{0:>13}'.format(h_mm) + ' MINUTES EXECUTION TIME\n')

def __READ_UNTIL(fp, fn, dsn, dlm):
    # prepare spool
    zPE.new_spool(fn, 'i', dsn)
    sp = zPE.SPOOL[fn][0]

    # read until encountering dlm
    while True:
        line = fp.readline()

        # check end of stream
        if line == dlm:
            return ''

        # check in-stream data
        if len(dsn) == 0:
            if (line[:2] == '//'):
                return line     # next JCL card, put it back
            zPE.JCL['read_cnt'] += 1

        sp.append(line)

def __WRITE_OUT():
    for fn in zPE.SPOOL.keys():
        sp = zPE.SPOOL[fn][0]
        if zPE.SPOOL[fn][1] in ['i', 't']:
            continue            # input / tmp spool
        if len(sp) == 0:
            continue            # empty spool

        path = os.path.join(* zPE.SPOOL[fn][2])
        zPE.create_dir(os.path.dirname(path))
        fp = open(path, 'w')
        for line in sp:
            fp.write(line)

