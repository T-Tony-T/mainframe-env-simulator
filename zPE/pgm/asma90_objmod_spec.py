from zPE.core.asm import B_, C_, X_ # for conversion

def chs(s):
    return X_.tr(C_(s).dump())

# general
def rec_id(tt, cnt):
    if len(tt) > 8:             # normalize the length of Deck ID
        tt = tt[:8]
    cnt_len = 8 - len(tt)       # room for sequence number
    return chs('{0}{1:0>{2}}'.format(tt, cnt, cnt_len))


# for ESD record
def esd_id(sym):
    if sym.type == 'LD':
        return chs('  ')        # blank
    return '{0:0>4}'.format(hex(sym.id)[2:])

def esd_flag(sym, amode, rmode):
    if sym.type in [ 'XD', 'PR' ]:
        return 'al'             # mark; should be alignment (need info)
    if sym.type in [ 'LD', 'ER', 'WX' ]:
        return chs(' ')
    # otherwise
    if rmode == 64:
        bit_2 = '1'
        bit_5 = '1' # any
    else:
        bit_2 = '0'
        if rmode == 24:
            bit_5 = '0'
        else:
            bit_5 = '1'
    if amode == 64:
        bit_3   = '1'
        bit_6_7 = '11' # any
    else:
        bit_3 = '0'
        if amode == 24:
            bit_6_7 = '00'
        elif amode == 31:
            bit_6_7 = '10'
        else:
            bit_6_7 = '11'
    bit_4 = '0' # '1' if RSECT; need info
    
    return X_.tr(B_('00{0}{1}{2}{3}{4}'.format(
                bit_2, bit_3, bit_4, bit_5, bit_6_7
                )).dump())

    return 

def esd_vf(vf, am, rm, indx):
    if indx >= len(vf):
        return chs('{0:16}'.format('')) # 16 spaces

    sym = vf[indx][1]

    # byte 14-16
    if sym.type == 'LD':
        last = sym.id
    else:
        last = sym.length

    return ''.join([
            chs(vf[indx][0]),      # 01-08 : External symbol name
            sym.type_code(),       # 09    : ESD type code
            '{0:0>6}'.format(      # 10-12 : Address
                hex(sym.addr)[2:]
                ),
            esd_flag(sym, am, rm), # 13    : Flag
            '{0:0>6}'.format(      # 14-16 : Length, LDID, or space
                hex(last)[2:]
                ),
            ])


REC_FMT = {                 # record formatter
    # External symbol dictionary records describe external symbols
    # used in the program
    'ESD' : lambda vf, am, rm, tt, cnt : ''.join([
            # vf  : variable field (1~3 [ Symbol, ExternalSymbol object ] pair(s))
            # am  : AMODE (24, 31, or 64)
            # rm  : RMODE (24, 31, or 64)
            # tt  : Deck ID (first TITLE)
            # cnt : sequence number
            '02',                       # 01    : X'02'
            chs('ESD'),                 # 02-04 : ESD
            chs('{0:6}'.format('')),    # 05-10 : Space
            '{0:0>4}'.format(           # 11-12 : Variable field count
                hex(len(vf) * 16)[2:]   #         (number of bytes of vf)
                ),
            chs('{0:2}'.format('')),    # 13-14 : Space
            esd_id(vf[0][1]),           # 15-16 : ESDID of first SD, XD,
                                        #         CM, PC, ER, or WX in vf;
                                        #         blank for LD items
            esd_vf(vf, am, rm, 0),      # 17-32 : Variable field item 1
            esd_vf(vf, am, rm, 1),      # 33-48 : Variable field item 2
            esd_vf(vf, am, rm, 2),      # 49-64 : Variable field item 3
            chs('{0:8}'.format('')),    # 65-72 : Space
            rec_id(tt, cnt),            # 73-80 : Deck ID, sequence number, or both
            ]),
    # Text records describe object code generated
    'TXT' : lambda : ''.join([
            '02',                       # 01    : X'02'
            chs('TXT'),                 # 02-04 : TXT
            chs(' '),                   # 05    : Space
            ]),
    # Relocation dictionary provide information required to relocate
    # address constants within the object module
    'RLD' : lambda : ''.join([
            '02',                       # 01    : X'02'
            chs('RLD'),                 # 02-04 : RLD
            chs('{0:6}'.format('')),    # 05-10 : Space
            ]),
    # End records terminate the object module and optionally provide
    # the entry point
    'END' : lambda : ''.join([
            '02',                       # 01    : X'02'
            chs('END'),                 # 02-04 : END
            chs(' '),                   # 05    : Space
            ]),
    # Symbol table records provide symbol information for TSO TEST
    'SYM' : lambda : ''.join([
            '02',                       # 01    : X'02'
            chs('SYM'),                 # 02-04 : SYM
            chs('{0:6}'.format('')),    # 05-10 : Space
            ]),
    }
