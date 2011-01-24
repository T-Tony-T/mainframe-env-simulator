# this is not the complete module for JCL
# this is currently only working for simple assist

import zPE

import os, sys
import re
from time import gmtime, strftime

def parse(src):
    invalid_lable = []          # record all invalid lables

    fp = open(src, 'r')
    sp = zPE.SPOOL['JESJCL'][0]

    # initial read
    line = fp.readline()
    zPE.JCL['card_cnt'] += 1
    if len(line) > 72:
        sys.stderr.write('Error: line ' + str(zPE.JCL['card_cnt']) +
                         'Statement cannot exceed colomn 72.\n')
        sys.exit(72)

    field = re.split('\s', line)

    # parse JOB card
    if not zPE.ck_label(field[0][2:]):
        invalid_lable.append(zPE.JCL['card_cnt'])

    if field[1] != 'JOB':
        sys.stderr.write('Error: No JOB card found.\n')
        sys.exit(1)
    zPE.JCL['jobname'] = field[0][2:]
    zPE.JCL['owner'] = zPE.JCL['jobname'][:7]
    zPE.JCL['job'] = 'JOB' + str(zPE.Config['job_id'])

    ctrl = '1'
    sp.append(ctrl + '{0:>9}'.format(1) + ' {0:<72}'.format(line[:-1]) +
              zPE.JCL['job'] + '\n')
    ctrl = ' '

    # main read loop
    line = fp.readline()
    nextline = ''
    while line != '':
        zPE.JCL['card_cnt'] += 1
        if len(line) > 72:
            sys.stderr.write('Error: line ' + str(zPE.JCL['card_cnt']) +
                             'Statement cannot exceed colomn 72.\n')
            sys.exit(72)

        field = re.split('\s', line)

        # parse EXEC card
        # currently supported parameter: parm
        if not zPE.ck_label(field[0][2:]):
            invalid_lable.append(zPE.JCL['card_cnt'])

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
                if disp != 'SHR':
                    sys.stderr.write('Error: DISP=' + disp + 
                                     ': Currently not supported.\n')
                    sys.exit(44)
                elif field[0][2:] == 'STEPLIB':
                    pass        # "steplib" is currently ignored
                else:
                    __READ_UNTIL(zPE.open_file(dsn, 'r'), field[0][2:], dsn, '')
            else:
                sys.stderr.write('Error: ' + re.split(',', field[2], 1)[0] +
                                 ': Parameter not supported.\n')
                sys.exit(44)

            zPE.JCL['step'][-1].append_dd({
                    'name' : field[0][2:],
                    'sysout' : sysout,
                    'dsn' : dsn,
                    'disp' : disp,
                    })
        # check end of JCL
        elif field[1] == '':
            zPE.JCL['card_cnt'] -= 1 # "//" does not count
            break

        sp.append(ctrl + '{0:>9}'.format(zPE.JCL['card_cnt']) + ' ' + line)
        if nextline == '':
            line = fp.readline()
        else:
            line = nextline
            nextline = ''

    # save MSGLG
    sp = zPE.SPOOL['JESMSGLG'][0]
    ctrl = '1'                  # control character for output
    sp.append(ctrl + '                    J E S 2  J O B  L O G  --  S Y S T E M  S Y S 1  --  N O D E  Z O S K C T R\n')
    ctrl = '0'
    sp.append(ctrl + '\n')
    ctrl = ' '
    sp.append(ctrl + strftime("%H.%M.%S ", gmtime()) + zPE.JCL['job'] +
              '{0:<16}'.format(strftime(" ---- %A,", gmtime())) +
              strftime(" %d %b %Y ----", gmtime()) + '\n')
    sp.append(ctrl + strftime("%H.%M.%S ", gmtime()) + zPE.JCL['job'] +
              '  IRR010I  USERID {0:<8}'.format(zPE.JCL['owner']) +
              ' IS ASSIGNED TO THIS JOB.\n')

    if len(invalid_lable) != 0:
        sp = zPE.SPOOL['JESYSMSG'][0]
        ctrl = ' '
        sp.append(ctrl + ' STMT NO. MESSAGE\n')
        for indx in invalid_lable:
            sp.append(ctrl + '{0:>9} IEFC662I INVALID LABEL\n'.format(indx))
        sp.append(ctrl + '\n')

        __JES2_STAT('0', False)


def write_out():
    for fn in zPE.SPOOL.keys():
        sp = zPE.SPOOL[fn][0]
        if len(sp) == 0:
            continue            # empty spool
        if zPE.SPOOL[fn][1] in ['i', 't']:
            continue            # input / tmp spool
        fp = open(os.path.join(* zPE.SPOOL[fn][2]), 'w')
        for line in sp:
            fp.write(line)


### Supporting functions

def __JES2_STAT(ctrl, executed):
    sp = zPE.SPOOL['JESMSGLG'][0]
    sp.append(ctrl + '------ JES2 JOB STATISTICS ------\n')
    if executed:
        sp.append(ctrl + '{0:>13}'.format(strftime(" %d %b %Y", gmtime())) +
                  ' JOB EXECUTION DATE\n')

    sp.append(ctrl + '{0:>13}'.format(zPE.JCL['card_cnt']) + ' CARDS READ\n')

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
    sp.append(ctrl + '{0:>13}'.format('0.00') + ' MINUTES EXECUTION TIME\n')

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
            zPE.JCL['card_cnt'] += 1

        sp.append(line)
