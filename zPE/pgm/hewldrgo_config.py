import zPE

### Linkage-Editor config definition

LDR_PARM = {
    'AMODE'     : 31,
    'RMODE'     : 31,
    'PSWKEY'    : 8,            # 1st user-mode key
}
def ldr_load_parm(parm_dic):
    for key in parm_dic:
        if key in LDR_PARM:
            LDR_PARM[key] = parm_dic[key]
        else:
            raise KeyError('{0}: Invalid PARM key.'.format(key))

LDR_CONFIG = {
    'MEM_POS'   : None,         # required; first available memory location
    'MEM_LEN'   : None,         # required; length of memory required
    'TIME'      : None,         # required; maximum execution time allowed
    'REGION'    : None,         # required; maximum length allowed
    'ENTRY_PT'  : None,         # entry point (specified by END)
    'EXIT_PT'   : None,         # return address
    }
def ldr_load_config(conf_dic):
    for key in conf_dic:
        if key in LDR_CONFIG:
            LDR_CONFIG[key] = conf_dic[key]
        else:
            raise KeyError('{0}: Invalid configuration key.'.format(key))


### resource definition

INSTRUCTION = [                 # Instruction history
    # [ PSW, MNEMONIC ]
    ]
BRANCHING = [                   # Branching history
    # [ PSW, MNEMONIC ]
    ]
from zPE.core.cpu import decode_op
from zPE.core.asm import is_branching
def RECORD_INS(psw, ins):
    INSTRUCTION.append([ psw, ''.join(ins) ])
    if is_branching( decode_op(ins[0]) ):
        RECORD_BR(psw, ins)
    return ins
def RECORD_BR(psw, ins):
    BRANCHING.append([ psw, ''.join(ins) ])
    return ins

MEM_DUMP = [ ]                  # the entire memory dump at ABEND


from asma90_config import ExternalSymbol
CSECT = {
    # ( OBJMOD_id, ESD_ID ) : ( mem_loc,  ExternalSymbol, ESD_name )
    #   mem_loc - the starting memory location where the OBJMOD is loaded into
    }
SCOPE = {
    # ( mem_loc, addr, length ) : ( OBJMOD_id, ESD_ID )
    #   addr    - the starting location of the CSECT relative to the OBJMOD
    #   length  - the length of the CSECT 
    }
EXREF = {
    # ( OBJMOD_id, ESD_ID ) : ( 0x000000, ExternalSymbol, ESD_name )
    }


def ldr_init_res():
    del INSTRUCTION[:]          # clear Instruction history
    del BRANCHING[:]            # clear Branching history

    CSECT.clear()               # clear Control SECTion records
    SCOPE.clear()               # clear scope records
    EXREF.clear()               # clear EXternal REFerence records

    del MEM_DUMP[:]             # clear memory dump
