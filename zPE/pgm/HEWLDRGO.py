################################################################
# Program Name:
#     HEWLDRGO / LOADER
#
# Purpose:
#     linkage-edit the object module into a load module, execute
#     it, ant through it away
#
# Parameter:
#     not implemented yet
#
# Input:
#     SYSLIN    the object module
#     SYSLIB    load module libraries needed by the loader
#     [ ... ]   user-defined input for the module to be executed
#
# Output:
#     SYSLOUT   loader information and diagnostic message
#     [ ... ]   user-defined output for the module to be executed
#
# Return Code:
#     16        insufficient resources
#     [ ... ]   same as the RC of the execution of the module
#
# Return Value:
#     [ ... ]   same as the RV of the execution of the module
################################################################


import zPE

import os, sys
from time import strftime
from random import randint
from binascii import b2a_hex

from zPE.core.asm import B_, C_, X_ # for conversion
def chs(src):             # chs = CHaractor bit-Stream (char -> hex)
    return X_.tr(C_(src).dump())
def cht(src):             # cht = CHaractor reverTed (char <- hex)
    return C_.tr(X_(src).dump())


FILE = [ 'SYSLIN', 'SYSLOUT' ]  # SYSLIB not required

PARM = {
    'AMODE'     : 31,
    'RMODE'     : 31,
}
def load_parm(parm_dic):
    for key in parm_dic:
        if key in PARM:
            PARM[key] = parm_dic[key]
        else:
            raise KeyError('{0}: Invalid PARM key.'.format(key))

LOCAL_CONF = {
    'MEM_POS'   : None,         # required; first available memory location
    'MEM_LEN'   : None,         # required; length of memory required
    'REGION'    : None,         # required; maximum length allowed
    }
def load_local_conf(conf_dic):
    for key in conf_dic:
        if key in LOCAL_CONF:
            LOCAL_CONF[key] = conf_dic[key]
        else:
            raise KeyError('{0}: Invalid configuration key.'.format(key))


### resource definition

INSTRUCTION = [ ]               # Instruction history
BRANCHING = [ ]                 # Branching history
### end of resource definition

def init_res():
    del INSTRUCTION[:]          # clear Instruction history
    del BRANCHING[:]            # clear Branching history


def run(step):
    '''this should prepare an tmp step and pass it to init()'''
    zPE.mark4future('user-specific pgm')


def init(step):
    # check for file requirement
    if __MISSED_FILE(step) != 0:
        return zPE.RC['CRITICAL']

    # load the user-supplied PARM and config into the default configuration
    # load_parm({
    #         })
    load_local_conf({
            'MEM_POS' : randint(512*128, 4096*128) * 8, # random from 512K to 4M
            'MEM_LEN' : zPE.core.mem.max_sz_of(step.region),
                        # this is WAY to large;
                        # need a way to detect actual mem size
            'REGION'  : step.region,
            })

    # load OBJMOD into memory, and execute it
    rc = go(load())

    __PARSE_OUT()

    init_res() # release resources (by releasing their refs to enable gc)

    return rc


def load():
    if LOCAL_CONF['MEM_LEN'] > zPE.core.mem.max_sz_of(LOCAL_CONF['REGION']):
        zPE.abort(9, 'Error: ', LOCAL_CONF['REGION'],
                  ': RIGEON is not big enough.\n')

    spi = zPE.core.SPOOL.retrive('SYSLIN') # input SPOOL
    mem = zPE.core.mem.Memory(LOCAL_CONF['MEM_POS'], LOCAL_CONF['MEM_LEN'])

    rec_tp = { # need to be all lowercase since b2a_hex() returns all lowercase
        'ESD' : chs('ESD').lower(),
        'TXT' : chs('TXT').lower(),
        'RLD' : chs('RLD').lower(),
        'END' : chs('END').lower(),
        'SYM' : chs('SYM').lower(),
        }

    has_txt = False             # indicates whether encountered TXT record(s)
    for r in spi.spool:
        rec = b2a_hex(r)
        if rec[:2] != '02':     # first byte need to be X'02'
            zPE.abort(13, "Error: X'", rec[:2],
                      "': invalid OBJECT MODULE record indicator.\n",
                      "    Every record should begin with X'02'.\n")

        # parse ESD record
        if rec[2:8] == rec_tp['ESD']:
            # do something here
            pass

        # parse TXT record
        elif rec[2:8] == rec_tp['TXT']:
            has_txt = True
            # do something here

        # parse RLD record
        elif rec[2:8] == rec_tp['RLD']:
            pass                # currently not supported

        # parse END record
        elif rec[2:8] == rec_tp['END']:
            if not has_txt:
                zPE.abort(13, 'Error: no TXT records found in OBJECT MODULE.\n')

            if r != spi[-1]:
                zPE.abort(13, 'Error: OBJECT MODULE not end with END record.\n')

            # do something here

        # parse SYM record
        elif rec[2:8] == rec_tp['SYM']:
            pass                # currently not supported

        else:
            zPE.abort(13, 'Error: ', cht(rec[2:8]),
                      ': invalid OBJECT MODULE record type.\n')

    return mem
# end of load()

def go(mem):
    print mem.dump(mem.min_pos, mem.max_pos - mem.min_pos)

    return zPE.RC['NORMAL']
# end of go()


### Supporting Functions
def __MISSED_FILE(step):
    sp1 = zPE.core.SPOOL.retrive('JESMSGLG') # SPOOL No. 01
    sp3 = zPE.core.SPOOL.retrive('JESYSMSG') # SPOOL No. 03
    ctrl = ' '

    cnt = 0
    for fn in FILE:
        if fn not in zPE.core.SPOOL.list():
            sp1.append(ctrl, strftime('%H.%M.%S '), zPE.JCL['jobid'],
                       '  IEC130I {0:<8}'.format(fn),
                       ' DD STATEMENT MISSING\n')
            sp3.append(ctrl, 'IEC130I {0:<8}'.format(fn),
                       ' DD STATEMENT MISSING\n')
            cnt += 1

    return cnt


def __PARSE_OUT():
    spo = zPE.core.SPOOL.retrive('SYSPRINT') # output SPOOL

