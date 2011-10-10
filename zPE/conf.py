# this is the System Level Configuration

from core.mem import parse_region

import os, sys, pickle
import re

import sqlite3


### Architectural Definition
JOB_ID_MIN = 10000              # the smallest job ID
JOB_ID_MAX = 65535              # the largest job ID
TMP_FILE_ID = 101               # the smallest tmp file identifier

## Return Code
RC = {
    'NORMAL'    : 0,
    'WARNING'   : 4,
    'ERROR'     : 8,
    'SERIOUS'   : 12,
    'SEVERE'    : 16,
    }


### Configurable Definition
POSSIBLE_ADDR_MODE = [ 16, 31, 64, ]

DEFAULT = {
    'ADDR_MODE' : 31,           # hardware addressing mode: 31 bit

    'MEMORY_SZ' : '1024K',      # memory size: 1024 KB

    'ICH70001I' : {             # config list for ICH70001I
        'atime' : '00:00:00 ON THURSDAY, JANUARY 18, 2011',
                                # the start time of this project
        },
    }

Config = { }       # 'job_id' and 'tmp_id' should not be modified manually

def init_rc():
    Config['job_id']     = JOB_ID_MIN
    Config['tmp_id']     = TMP_FILE_ID  # next available tmp file identifier

    Config['addr_mode']  = DEFAULT['ADDR_MODE']
    Config['addr_max']   = 0            # calculate on loading

    Config['memory_sz']  = DEFAULT['MEMORY_SZ']
                                # can be altered by "// JOB ,*,REGION=*"
                                # can be overridden by "// EXEC *,REGION=*"


CONFIG_PATH = {
    'dir'       : os.path.join(os.environ['HOME'], '.zPE'),
    'rc'        : os.path.join(os.environ['HOME'], '.zPE', 'config'),
    'data'      : os.path.join(os.environ['HOME'], '.zPE', 'data'),
    'ICH70001I' : os.path.join(os.environ['HOME'], '.zPE', 'data', 'ICH70001I'),
    'SPOOL'     : os.path.join(os.environ['HOME'], '.zPE', 'data', 'SPOOL.sqlite')
    }

def dump_ICH70001I(conf):
    __CK_CONFIG()
    __TOUCH_ICH70001I(conf)

def load_ICH70001I():
    __CK_CONFIG()
    return pickle.load(open(CONFIG_PATH['ICH70001I'], 'rb'))


def fetch_job_id():
    for line in open(CONFIG_PATH['rc'], 'r'):
        (k, v) = re.split('[ \t]*=[ \t]*', line, maxsplit=1)

        if k != 'job_id':
            continue

        try:
            job_id = int(v)

            if JOB_ID_MIN < job_id and job_id < JOB_ID_MAX:
                return job_id   # found
        except:
            pass
        return None             # not found


def read_rc(dry_run = False):
    init_rc()
    __CK_CONFIG()

    for line in open(CONFIG_PATH['rc'], 'r'):
        (k, v) = re.split('[ \t]*=[ \t]*', line, maxsplit=1)
        ok = False

        if k == 'job_id':
            try:
                Config[k] = int(v)
                if not dry_run:
                    Config[k] += 1 # increment the ID number

                if JOB_ID_MIN <= Config[k] and Config[k] < JOB_ID_MAX:
                    ok = True
            except ValueError:
                pass

            if not ok:
                Config[k] = JOB_ID_MIN
                sys.stderr.write(''.join([
                            'CONFIG WARNING: ', v[:-1],
                            ': Invalid job ID.\n'
                            ]))
        elif k == 'addr_mode':
            try:
                Config[k] = int(v)
                if Config[k] in POSSIBLE_ADDR_MODE:
                    ok = True
            except ValueError:
                pass

            if not ok:
                Config[k] = DEFAULT['ADDR_MODE']
                sys.stderr.write(''.join([
                            'CONFIG WARNING: ', v[:-1],
                            ': Invalid address mode.\n'
                            ]))
        elif k == 'memory_sz':
            try:
                Config[k] = parse_region(v)
                ok = True
            except SyntaxError as e_msg:
                sys.stderr.write('CONFIG WARNING: {0}: \n  {1}\n'.format(v[:-1], e_msg))
            except ValueError as e_msg:
                sys.stderr.write('CONFIG WARNING: {0}: \n  {1}\n'.format(v[:-1], e_msg))

            if not ok:
                Config[k] = DEFAULT['MEMORY_SZ']

    Config['addr_max'] = 2 ** Config['addr_mode']

    if JOB_ID_MAX - Config['job_id'] <= 3 and not dry_run:
        sys.stderr.write('\n  JOB queue will be cleared in {0} submit(s)!\n\n'.format(
                JOB_ID_MAX - Config['job_id']
                ))
    elif Config['job_id'] == JOB_ID_MIN and not dry_run:
        open(CONFIG_PATH['SPOOL'], 'w').close()
        __TOUCH_SPOOL()
        sys.stderr.write('\n  JOB queue cleared!\n\n')
    write_rc()

def write_rc():
    __TOUCH_RC()


### Supporting Function

def __CK_CONFIG():
    if not os.path.isdir(CONFIG_PATH['data']):
        os.makedirs(CONFIG_PATH['data'])
    if ( not os.path.isfile(CONFIG_PATH['rc']) or
         not os.path.isfile(CONFIG_PATH['SPOOL'])
         ):
        open(CONFIG_PATH['SPOOL'], 'w').close()
    __TOUCH_SPOOL()

    if not os.path.isfile(CONFIG_PATH['rc']):
        __TOUCH_RC()
    if not os.path.isfile(CONFIG_PATH['ICH70001I']):
        __TOUCH_ICH70001I()


def __TOUCH_ICH70001I(conf = DEFAULT['ICH70001I']):
    pickle.dump(conf, open(CONFIG_PATH['ICH70001I'], 'wb'))

def __TOUCH_SPOOL():
    conn = sqlite3.connect(CONFIG_PATH['SPOOL'])
    conn.executescript(
'''
CREATE TABLE IF NOT EXISTS JOB (
        Job_ID          TEXT    PRIMARY KEY,
        Job_Name        TEXT    NOT NULL,
        Job_OWNER       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS SPOOL (
        row_id          INTEGER PRIMARY KEY,
        Job_ID          TEXT    NOT NULL,
        Spool_Key       TEXT    NOT NULL,
        Step_Name       TEXT    NOT NULL,
        Content         TEXT    NOT NULL,

        FOREIGN KEY (Job_ID)    REFERENCES JOB (Job_ID)
        ON DELETE CASCADE
);
''')
    conn.commit()
    conn.close()


def __TOUCH_RC():
    fp = open(CONFIG_PATH['rc'], 'w')
    fp.write(''.join(['job_id = ', str(Config['job_id']), '\n']))
    fp.write(''.join(['addr_mode = ', str(Config['addr_mode']), '\n']))
    fp.write(''.join(['memory_sz = ', Config['memory_sz'], '\n']))
    fp.close()
