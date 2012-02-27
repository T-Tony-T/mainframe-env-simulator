import zPE

### High-Level Assembler config definition

ASM_PARM = {
    'AMODE'     : 31,
    'RMODE'     : 31,
    'ENTRY'     : '',           # need info
    'LN_P_PAGE' : 60,           # line per page for output
}
def asm_load_parm(parm_dic):
    for key in parm_dic:
        if key in ASM_PARM:
            ASM_PARM[key] = parm_dic[key]
        else:
            raise KeyError('{0}: Invalid PARM key.'.format(key))

ASM_CONFIG = {
    'MEM_POS'   : None,         # required; first available memory location
    'MEM_LEN'   : None,         # required; length of memory required
    'REGION'    : None,         # required; maximum length allowed
    }
def asm_load_config(conf_dic):
    for key in conf_dic:
        if key in ASM_CONFIG:
            ASM_CONFIG[key] = conf_dic[key]
        else:
            raise KeyError('{0}: Invalid configuration key.'.format(key))


### High-Level Assembler resource definition

INFO = { # see asm_init_res() for possible message levels
    # 'level' : { Line_Num : [ ( Err_No, Pos_Start, Pos_End, ), ... ] }
    }
def INFO_GE(line_num, err_level):
    if line_num in INFO['S']:
        return True
    if err_level == 'S':        # >= S, ignore E,W,N,I
        return False
    if line_num in INFO['E']:
        return True
    if err_level == 'E':        # >= E, ignore W,N,I
        return False
    if line_num in INFO['W']:
        return True
    if err_level == 'W':        # >= W, ignore N,I
        return False
    if line_num in INFO['N']:
        return True
    if err_level == 'N':        # >= N, ignore I
        return False
    if line_num in INFO['I']:
        return True
    return False                # >= I

def MAP_INFO_GE(line_num, err_level, func):
    '''
    call `func(line_num, err_level)` for each err_level greater than
    the specified one, if the line has errors in that err_level.
    '''
    if line_num in INFO['S']:
        func(line_num, 'S')
    if err_level == 'S':        # >= S, ignore E,W,N,I
        return
    if line_num in INFO['E']:
        func(line_num, 'E')
    if err_level == 'E':        # >= E, ignore W,N,I
        return
    if line_num in INFO['W']:
        func(line_num, 'W')
    if err_level == 'W':        # >= W, ignore N,I
        return
    if line_num in INFO['N']:
        func(line_num, 'N')
    if err_level == 'N':        # >= N, ignore I
        return
    if line_num in INFO['I']:
        func(line_num, 'I')
    return                      # >= I


TITLE = [                       # TITLE (Deck ID) list
    '',                         # will be replaced by the first named TITLE
    # [ line_num, title_name, title_string ]
    ]

MNEMONIC = {
    # Line_Num : [  ]                                           // type (len) 0
    # Line_Num : [ scope, ]                                     // type (len) 1
    # Line_Num : [ scope, LOC, ]                                // type (len) 2
    # Line_Num : [ scope, LOC, sd_info, ]                       // type (len) 3
    # Line_Num : [ scope,  ,  , equates, ]                      // type (len) 4
    # Line_Num : [ scope, LOC, (OBJECT_CODE), ADDR1, ADDR2, ]   // type (len) 5
    }

RELOCATE_OFFSET = {
    # scope_id : offset
    }

OBJMOD = { # see asm_init_res() for possible record types
    # 'record type' : [ lines ]
    }

class ExternalSymbol(object):
    def __init__(self, tp, scope_id, addr, length,
                 owner, amode, rmode, alias
                 ):
        self.type = tp
        self.id = scope_id
        self.addr = addr
        self.length = length
        self.owner = owner
        self.amode = amode
        self.rmode = rmode
        self.alias = alias

    def type_code(self):
        return {
            'SD'   : '00',
            'LD'   : '01',
            'ER'   : '02',
            'PC'   : '04',
            'CM'   : '05',
            'XD'   : '06',
            'PR'   : '06', # (another name for 'XD'?)
            'WX'   : '0A',
            'qaSD' : '0D', # Quad-aligned SD
            'qaPC' : '0E', # Quad-aligned PC
            'qaCM' : '0F', # Quad-aligned CM
            }[self.type]

    def load_type(self, type_code):
        self.type = {
            '00'   : 'SD',
            '01'   : 'LD',
            '02'   : 'ER',
            '04'   : 'PC',
            '05'   : 'CM',
            '06'   : 'XD',
            '0A'   : 'WX',
            '0D'   : 'qaSD', # Quad-aligned SD
            '0E'   : 'qaPC', # Quad-aligned PC
            '0F'   : 'qaCM', # Quad-aligned CM
            }[type_code]

    def flags(self):
        if self.type in [ 'XD', 'PR' ]:
            return 'al'        # mark; should be alignment (need info)
        if self.type in [ 'LD', 'ER', 'WX' ]:
            return zPE.c2x(' ')
        # otherwise
        if self.rmode == 64:
            bit_2 = '1'
            bit_5 = '1' # any
        else:
            bit_2 = '0'
            if self.rmode == 24:
                bit_5 = '0'
            else:
                bit_5 = '1'
        if self.amode == 64:
            bit_3   = '1'
            bit_6_7 = '11' # any
        else:
            bit_3 = '0'
            if self.amode == 24:
                bit_6_7 = '00'
            elif self.amode == 31:
                bit_6_7 = '10'
            else:
                bit_6_7 = '11'
        bit_4 = '0' # '1' if RSECT; need info

        return zPE.b2x('00{0}{1}{2}{3}{4}'.format(
                bit_2, bit_3, bit_4, bit_5, bit_6_7
                ))

ESD = {                 # External Symbol Dictionary; build during pass 1
    # 'Symbol  ' : ( ExternalSymbol(SD/PC), ExternalSymbol(ER), )
    }
ESD_ID = {              # External Symbol Dictionary ID Table
    # scope_id : 'Symbol  '
    }

class Symbol(object):
    def __init__(self, length, addr, scope_id,
                 reloc, sym_type, asm, program,
                 line_cnt, references
                 ):
        self.length     = length
        self.value      = addr
        self.id         = scope_id

        self.reloc      = reloc
        self.type       = sym_type
        self.asm        = asm
        self.program    = program

        self.defn       = line_cnt
        self.references = references
SYMBOL = {              # Cross Reference Table; build during pass 1
    # 'Symbol  ' : Symbol()
    }
SYMBOL_V = {            # Cross Reference ER Sub-Table
    # 'Symbol  ' : Symbol()
    }
SYMBOL_EQ = {           # Cross Reference =Const Sub-Table
    # 'Symbol  ' : [ Symbol(), ... ]
    }
def ALLOC_EQ_SYMBOL(lbl, symbol):
    zPE.dic_append_list(SYMBOL_EQ, lbl, symbol) # mark =const as allocable
INVALID_SYMBOL = []     # non-defined symbol
NON_REF_SYMBOL = []     # non-referenced symbol

class RelocationEntry(object):
    def __init__(self, addr, const_type, const_len, action
                 ):
        self.addr       = addr   # address of the symbol, or 0x0 if external
        self.type       = const_type # A or V
        self.len        = const_len  # 1, 2, 3, or 4
        self.action     = action     # +, -, or ST
RLD = {
    # (pos_id, rel_id) : [ RelocationEntry, ... ]
    }
def RECORD_RL_SYMBOL(pos_id, rel_id, rl_entry):
    zPE.dic_append_list(RLD, (pos_id, rel_id), rl_entry)


class Using(object):
    def __init__(self, curr_addr, curr_id,
                 action,
                 using_type, lbl_addr, range_limit, lbl_id,
                 max_disp, last_stmt, lbl_text
                 ):
        self.loc_count = curr_addr
        self.loc_id = curr_id
        self.action = action
        self.u_type = using_type
        self.u_value = lbl_addr
        self.u_range = range_limit
        self.u_id = lbl_id
        self.max_disp = max_disp
        self.last_stmt = last_stmt
        self.lbl_text = lbl_text
USING_MAP = {           # Using Map
    # ( Stmt, reg, ) : Using()
    }
ACTIVE_USING = {
    # reg : Stmt
    }


def asm_init_res():
    INFO['I'] = { }             # informational messages
    INFO['N'] = { }             # notification messages
    INFO['W'] = { }             # warning messages
    INFO['E'] = { }             # error messages
    INFO['S'] = { }             # severe error messages

    del TITLE[:]                # clear the TITLE list
    TITLE.append('')            # add back the DECK NAME

    MNEMONIC.clear()            # clear the MNEMONIC dictionary

    RELOCATE_OFFSET[1] = 0      # the main scope always start at 0x000000

    OBJMOD['ESD'] = [ ]         # External symbol dictionary records
    OBJMOD['TXT'] = [ ]         # Text records
    OBJMOD['RLD'] = [ ]         # Relocation dictionary records
    OBJMOD['END'] = [ ]         # End records
    OBJMOD['SYM'] = [ ]         # Symbol table records

    ESD.clear()
    ESD_ID.clear()

    SYMBOL.clear()
    SYMBOL_V.clear()
    SYMBOL_EQ.clear()
    del INVALID_SYMBOL[:]
    del NON_REF_SYMBOL[:]

    RLD.clear()

    USING_MAP.clear()
    ACTIVE_USING.clear()
