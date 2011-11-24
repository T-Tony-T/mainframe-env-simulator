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
#      0        the module ended normally
#      8        the module ended abnormally
#     12        the module is force closed by the LOADER
#     16        insufficient resources
#
# Return Value:
#     None
################################################################


import zPE

import sys
from time import strftime
from random import randint
from binascii import b2a_hex
from threading import Timer

import zPE.core.cpu as CPU


FILE = [ 'SYSLIN', 'SYSLOUT' ]  # SYSLIB not required

PARM = {
    'AMODE'     : 31,
    'RMODE'     : 31,
    'PSWKEY'    : 8,            # 1st user-mode key
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
    'TIME'      : None,         # required; maximum execution time allowed
    'REGION'    : None,         # required; maximum length allowed
    'ENTRY_PT'  : None,         # entry point (specified by END)
    'EXIT_PT'   : None,         # return address
    }
def load_local_conf(conf_dic):
    for key in conf_dic:
        if key in LOCAL_CONF:
            LOCAL_CONF[key] = conf_dic[key]
        else:
            raise KeyError('{0}: Invalid configuration key.'.format(key))


### resource definition

INSTRUCTION = [                 # Instruction history
    # [ PSW, MNEMONIC ]
    ]
BRANCHING = [                   # Branching history
    # [ PSW, MNEMONIC ]
    ]
def record_ins(psw, ins):
    INSTRUCTION.append([ psw, ''.join(ins) ])
    if ins[0][0] in '04' and ins[0][1] in '567':
        BRANCHING.append([ psw, ''.join(ins) ])
    return ins


EXCEPTION = {
    # e.g.      type : 'S',  code : '06C',  text : 'SPECIFICATION EXCEPTION',
    }

MEM_DUMP = [ ]                  # the entire memory dump at ABEND


from ASMA90 import ExternalSymbol
CSECT = {
    # ( OBJMOD_id, ESD_ID ) : ( mem_loc, ExternalSymbol, ESD_name )
    #   mem_loc - the starting memory location where the OBJMOD is loaded into
    }
SCOPE = {
    # ( mem_loc, addr, length ) : ( OBJMOD_id, ESD_ID )
    #   addr    - the starting location of the CSECT relative to the OBJMOD
    #   length  - the length of the CSECT 
    }
### end of resource definition

def init_res():
    del INSTRUCTION[:]          # clear Instruction history
    del BRANCHING[:]            # clear Branching history

    CSECT.clear()               # clear Control SECTion records
    SCOPE.clear()               # clear scope records

    EXCEPTION['type'] = None
    EXCEPTION['code'] = None
    EXCEPTION['text'] = None

    del MEM_DUMP[:]             # clear memory dump



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
            'TIME'    : min(
                zPE.JCL['jobstart'] + zPE.JCL['time'] - time(), # job limit
                step.time                                       # step limit
                ),
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
    LOCAL_CONF['EXIT_PT'] = mem.h_bound

    rec_tp = { # need to be all lowercase since b2a_hex() returns all lowercase
        'ESD' : zPE.c2x('ESD').lower(),
        'TXT' : zPE.c2x('TXT').lower(),
        'RLD' : zPE.c2x('RLD').lower(),
        'END' : zPE.c2x('END').lower(),
        'SYM' : zPE.c2x('SYM').lower(),
        }

    obj_id = 1            # 1st OBJECT MODULE
    mem_loc = mem.min_pos # starting memory location for each OBJMOD

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
            if esd_id == zPE.c2x('  '):    # 2 spaces
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
                if length == zPE.c2x('   '): # 3 spaces
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
                    CSECT[obj_id, esd.id] = ( mem_loc, esd, esd_name )
                    SCOPE[mem_loc, esd.addr, esd.length] = ( obj_id, esd.id )
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

            if ( obj_id, scope ) not in CSECT:
                zPE.abort(13, 'Error: ', scope,
                          ': Invalid ESD ID in TXT record(s).\n')

            # calculate the actual location
            loc = ( CSECT[obj_id, scope][0] +      # start of OBJMOD
                    CSECT[obj_id, scope][1].addr + # start of CSECT
                    addr                           # addr into CSECT
                    )
            mem[loc] = rec[32 : 32 + byte_cnt * 2]

        # parse RLD record
        elif rec[2:8] == rec_tp['RLD']: # byte 2-4
            pass                # currently not supported

        # parse END record
        elif rec[2:8] == rec_tp['END']: # byte 2-4
            if not has_txt:
                zPE.abort(13, 'Error: no TXT records found in OBJECT MODULE.\n')

            # setup ENTRY POINT, if not offered by the user
            if LOCAL_CONF['ENTRY_PT'] == None:
                # no ENTRY POINT offered, nor setup by a previous OBJMOD
                entry = rec[10:16] # byte 6-8: entry point
                if entry == zPE.c2x('   '): # 3 spaces
                    scope = 1   # no ENTRY POINT in END, use 1st CSECT
                    loc = CSECT[obj_id, scope][1].addr
                else:
                    scope = int(rec[28:32], 16) # byte 15-16: ESD ID for EP
                    loc = int(entry, 16)
                loc += CSECT[obj_id, scope][0] # add the offset of the OBJMOD
                LOCAL_CONF['ENTRY_PT'] = loc

            # prepare for next OBJECT MODULE, if any
            max_offset = 0
            for key in CSECT:
                if key[0] == obj_id:
                    offset = CSECT[key][1].addr + CSECT[key][1].length
                    if max_offset < offset:
                        max_offset = offset
            # advance to next available loc, align to double-word boundary
            mem_loc = (mem_loc + max_offset + 7) / 8 * 8
            obj_id += 1     # advance OBJECT MODULE counter

            has_txt = False # reset TXT record indi
            esd_id_next = 1 # reset next available ESD ID

        # parse SYM record
        elif rec[2:8] == rec_tp['SYM']: # byte 2-4
            pass                # currently not supported

        else:
            zPE.abort(13, 'Error: ', zPE.x2c(rec[2:8]), # byte 2-4
                      ': invalid OBJECT MODULE record type.\n')

    return mem
# end of load()

def go(mem):
    psw = zPE.core.reg.SPR['PSW']
    ldr_mem = zPE.core.mem.Memory((mem.max_pos + 7) / 8 * 8, 18 * 4) # 18F RSV
    ldr_mem[ldr_mem.min_pos] = zPE.c2x('RSV ') * 18

    prsv = zPE.core.reg.GPR[13] # register 13: parent register saving area
    rtrn = zPE.core.reg.GPR[14] # register 14: return address
    enty = zPE.core.reg.GPR[15] # register 15: entry address

    # initial program load
    prsv[0] = ldr_mem.min_pos        # load LOADER's RSV into register 13
    rtrn[0] = LOCAL_CONF['EXIT_PT']  # load exit point into register 14
    enty[0] = LOCAL_CONF['ENTRY_PT'] # load entry point into register 15
    psw.Instruct_addr = LOCAL_CONF['ENTRY_PT'] # set PSW accordingly

    old_key = psw.PSW_key       # backup previous PSW key
    psw.PSW_key = PARM['PSWKEY']
    psw.M = 1                   # turn on "Machine check"
    psw.W = 0                   # content switch to the program

    # main execution loop
    timeouted = [ ]
    def timeout():
        timeouted.append(True)
    t = Timer(LOCAL_CONF['TIME'], timeout)
    try:
        t.start()               # start the timer
        while not timeouted  and  psw.Instruct_addr != LOCAL_CONF['EXIT_PT']:
            CPU.execute(record_ins(psw.snapshot(), CPU.fetch()))
        t.cancel()              # stop the timer
        rc = zPE.RC['NORMAL']
    except Exception as e:
        # ABEND CODE; need info
        t.cancel()              # stop the timer
        if isinstance(e, ValueError):
            EXCEPTION['type'] = e.args[0]
            EXCEPTION['code'] = e.args[1]
            EXCEPTION['text'] = e.args[2]
        else:
            EXCEPTION['type'] = 'S'
            EXCEPTION['code'] = '0C0'
            EXCEPTION['text'] = 'UNKNOWN EXCEPTION'
            sys.stderr.write(   # print out the actual error
                'Exception: {0}\n'.format(
                    ''.join([ str(arg) for arg in e.args ])
                    )
                )
        MEM_DUMP.extend(mem.dump_all())
        rc = zPE.RC['ERROR']
    if timeouted:
        EXCEPTION['code'] = '322'
        EXCEPTION['type'] = 'S'
        EXCEPTION['text'] = 'TIME EXCEEDED THE SPECIFIED LIMIT'
        MEM_DUMP.extend(mem.dump_all())
        rc = zPE.RC['SEVERE']

    psw.W = 1                   # content switch back to the loader
    psw.PSW_key = old_key       # restore PSW key

    mem.release()
    ldr_mem.release()
    return rc
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

