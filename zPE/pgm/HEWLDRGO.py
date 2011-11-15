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
    'ENTRY_PT'  : None,         # entry point (specified by END)
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

from ASMA90 import ExternalSymbol
CSECT = {
    # ( OBJMOD_id, ESD_name ) : ExternalSymbol
    }
SCOPE = {
    # ( mem_loc, addr, length ) : ( OBJMOD_id, ESD_name )
    }
def scope_of(loc):
    for key in sorted(SCOPE, key = lambda t: t[0] + t[1] + t[2]):
        loc_s = key[0] + key[1]
        loc_e = loc_s + key[2]
        if loc_s <= loc  and  loc < loc_e:
            return key
    return None
### end of resource definition

def init_res():
    del INSTRUCTION[:]          # clear Instruction history
    del BRANCHING[:]            # clear Branching history

    CSECT.clear()               # clear Control SECTion records
    SCOPE.clear()               # clear scope records


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
    '''load all OBJECT MODULEs (statically) into memory'''
    if LOCAL_CONF['MEM_LEN'] > zPE.core.mem.max_sz_of(LOCAL_CONF['REGION']):
        zPE.abort(9, 'Error: ', LOCAL_CONF['REGION'],
                  ': RIGEON is not big enough.\n')

    spi = zPE.core.SPOOL.retrive('SYSLIN') # input SPOOL
    mem = zPE.core.mem.Memory(LOCAL_CONF['MEM_POS'], LOCAL_CONF['MEM_LEN'])

    rec_tp = { # need to be all lowercase since b2a_hex() returns all lowercase
        'ESD' : zPE.c2x('ESD').lower(),
        'TXT' : zPE.c2x('TXT').lower(),
        'RLD' : zPE.c2x('RLD').lower(),
        'END' : zPE.c2x('END').lower(),
        'SYM' : zPE.c2x('SYM').lower(),
        }

    obj_id = 1           # 1st OBJECT MODULE
    loc = mem.min_pos    # next available memory location

    has_txt = False             # indicates whether encountered TXT record(s)
    esd_id_next = 1             # next available ESD ID
    for r in spi.spool:
        rec = b2a_hex(r)
        if rec[:2] != '02':     # first byte need to be X'02'
            zPE.abort(13, "Error: X'", rec[:2],
                      "': invalid OBJECT MODULE record indicator.\n",
                      "    Every record should begin with X'02'.\n")

        # parse ESD record
        if rec[2:8] == rec_tp['ESD']: # byte 2-4
            byte_cnt = int(rec[20:24], 16) # byte 11-12: byte count
            esd_id = rec[28:32]            # byte 15-16: ESD ID / blank
            if esd_id.startswith(zPE.c2x(' ')):
                # blank => 'LD'
                esd_id = None   # no advancing in ESD ID
            else:
                # non-blank, parse it to int
                esd_id = int(esd_id, 16)
                esd_id_next = esd_id + 1
            for i in [ 32 + j * 32                   # vf indx -> start pos
                       for j in range(byte_cnt / 16) # number of vf
                       ]:
                vf = rec[i : i+32] # each vf is 16 bytes long
                addr = int(vf[18:24]) # vf byte 10-12: address
                length = vf[26:32]    # vf byte 14-16: length / blank
                if length.startswith(zPE.c2x(' ')):
                    length = None
                else:
                    length = int(length, 16)
                esd = ExternalSymbol(
                    None, esd_id, addr, length,
                    None, PARM['AMODE'],PARM['RMODE'], None
                    )
                esd.load_type(vf[16:18])         # vf byte 9: ESD type code
                if esd.type in [ 'SD', 'PC', ]:
                    esd_name = zPE.x2c(vf[0:16]) # vf byte 1-8: ESD Name
                    CSECT[obj_id, esd_name] = esd
                    SCOPE[loc, esd.addr, esd.length] = ( obj_id, esd_name )
                else:
                    pass        # ignore the rest
                # advance ESD ID by 1
                esd_id = esd_id_next
                esd_id_next = esd_id + 1

        # parse TXT record
        elif rec[2:8] == rec_tp['TXT']: # byte 2-4
            has_txt = True
            addr = int(rec[10:16], 16)     # byte 6-8: starting address
            byte_cnt = int(rec[20:24], 16) # byte 11-12: byte count
            scope = int(rec[28:32], 16)    # byte 15-16: scope id

            esd = CSECT[SCOPE[scope_of(addr)]]
            if esd.id != scope:
                zPE.abort(13, 'Error: ', scope,
                          ': Invalid ESD ID in TXT record(s).\n')
            mem[addr] = rec[32 : 32 + byte_cnt * 2]

        # parse RLD record
        elif rec[2:8] == rec_tp['RLD']: # byte 2-4
            pass                # currently not supported

        # parse END record
        elif rec[2:8] == rec_tp['END']: # byte 2-4
            if not has_txt:
                zPE.abort(13, 'Error: no TXT records found in OBJECT MODULE.\n')

            if r != spi[-1]:
                # more OBJECT MODULE to go
                obj_id += 1     # advance OBJECT MODULE counter
                loc = (loc + 7) / 8 * 8 # align to double-word boundary

                has_txt = False # reset TXT record indi
                esd_id_next = 1 # reset next available ESD ID

            ###################################
            # need ways to decide entry point #
            ###################################

        # parse SYM record
        elif rec[2:8] == rec_tp['SYM']: # byte 2-4
            pass                # currently not supported

        else:
            zPE.abort(13, 'Error: ', zPE.x2c(rec[2:8]), # byte 2-4
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
    spo = zPE.core.SPOOL.retrive('SYSLOUT') # output SPOOL

