from zPE.__init__ import c2x    # for conversion


# general
def deck_id(title, sequence):# 73-80 : Deck ID + sequence number
    '''
    title
        Deck ID (the name of the first named TITLE)
    sequence
        Deck sequence number
    '''
    if len(title) == 8:
        return c2x(title)
    else:                        # has room for sequence number
        # get the last `seq_len` digit of the sequence number
        seq_len = 8 - len(title)
        seq = '{0:0>{1}}'.format(sequence, seq_len)[-seq_len : ]

        return c2x('{0}{1}'.format(title, seq))


# for ESD record
def esd_id(sym):
    if sym.type == 'LD':
        return c2x('  ')        # blank
    return '{0:0>4}'.format(hex(sym.id)[2:])

def esd_vf(vf, indx):
    if indx >= len(vf):
        return c2x('{0:16}'.format('')) # 16 spaces

    sym = vf[indx][1]

    # byte 14-16
    if sym.type == 'LD':
        last = sym.id
    else:
        last = sym.length

    return ''.join([
            c2x(vf[indx][0]),      # 01-08 : External symbol name
            sym.type_code(),       # 09    : ESD type code
            '{0:0>6}'.format(      # 10-12 : Address
                hex(sym.addr)[2:]
                ),
            sym.flags(),           # 13    : Flag
            '{0:0>6}'.format(      # 14-16 : Length, LDID, or space
                hex(last)[2:]
                ),
            ])

# for TXT record
def txt_ds(ds):
    rv = ds
    rv_len = len(ds) / 2
    if rv_len < 56:       # fill with tailing spaces
        rv += c2x('{0:{1}}'.format('', 56 - rv_len))
    return rv

# for RLD record
def rld_df(df):
    return c2x('{0:56}'.format('Need Information')) # need info

# for END record
def end_fill(src, length):
    if isinstance(src, int):
        return '{0:0>{1}}'.format(hex(src)[2:].upper(), length * 2)
    else:
        return c2x('{0:<{1}}'.format(src, length))

def end_cnt_idr(idr):
    if len(idr):
        return c2x('{0}'.format(len(idr))) # EBCDIC 1 or 2
    else:
        return c2x(' ')         # blank if not present

def end_idr(idr, indx):
    if indx >= len(idr):
        return c2x('{0:19}'.format('')) # 19 spaces

    return ''.join([
            c2x(idr[indx]['translator id']), # 01-09 : Translator identification
            c2x(' '),                        # 10    : Space
            c2x(idr[indx]['ver + release']), # 11-14 : Version and release level
            c2x(idr[indx]['assembly date']), # 15-19 : date of assembly (yyddd)
            ])

# for SYM record
def sym_vf(vf):
    return c2x('{0:56}'.format('Need Information')) # need info


REC_FMT = {                 # record formatter
    # External symbol dictionary records describe external symbols
    # used in the program
    'ESD' : lambda vf : ''.join([
            # vf  : variable field (1~3 [ Symbol, ExternalSymbol ] pair(s))
            # am  : AMODE (24, 31, or 64)
            # rm  : RMODE (24, 31, or 64)
            '02',                       # 01    : X'02'
            c2x('ESD'),                 # 02-04 : ESD
            c2x('{0:6}'.format('')),    # 05-10 : Space
            '{0:0>4}'.format(           # 11-12 : Variable field count
                hex(len(vf) * 16)[2:]   #         (number of bytes of vf)
                ),
            c2x('{0:2}'.format('')),    # 13-14 : Space
            esd_id(vf[0][1]),           # 15-16 : ESDID of first SD, XD,
                                        #         CM, PC, ER, or WX in vf;
                                        #         blank for LD items
            esd_vf(vf, 0),              # 17-32 : Variable field item 1
            esd_vf(vf, 1),              # 33-48 : Variable field item 2
            esd_vf(vf, 2),              # 49-64 : Variable field item 3
            c2x('{0:8}'.format('')),    # 65-72 : Space
            ]),
    # Text records describe object code generated
    'TXT' : lambda scp, loc, ds : ''.join([
            # scp : ESDID (scope id)
            # loc : location of the first instruction
            # ds  : Data stream
            '02',                       # 01    : X'02'
            c2x('TXT'),                 # 02-04 : TXT
            c2x(' '),                   # 05    : Space
            '{0:0>6}'.format(           # 06-08 : Relative address of instrction
                hex(loc)[2:]
                ),
            c2x('{0:2}'.format('')),    # 09-10 : Space
            '{0:0>4}'.format(           # 11-12 : Byte count
                hex(len(ds) / 2)[2:]
                ),
            c2x('{0:2}'.format('')),    # 13-14 : Space
            '{0:0>4}'.format(           # 15-16 : ESDID (scope id)
                hex(scp)[2:]
                ),
            txt_ds(ds),                 # 17-72 : Data Stream
            ]),
    # Relocation dictionary provide information required to relocate
    # address constants within the object module
    'RLD' : lambda df : ''.join([
            # df  : data field (1~7 [ Symbol, <need info> ])
            '02',                       # 01    : X'02'
            c2x('RLD'),                 # 02-04 : RLD
            c2x('{0:6}'.format('')),    # 05-10 : Space
            '{0:0>4}'.format(           # 11-12 : Data field count
                hex(len(df) * 8)[2:]    #         (number of bytes of df)
                ),
            c2x('{0:4}'.format('')),    # 13-16 : Space
            rld_df(df),                 # 17-72 : Data fields
            ]),
    # End records terminate the object module and optionally provide
    # the entry point
    'END' : lambda enty, scp, sym, csl, idr : ''.join([
            # enty: Entry address from operand of END record in source deck
            # scp : ESDID of entry point (blank if no END operand)
            # sym : Symbolic entry point if specified and no END operand
            # csl : Control section length for a CSECT whose length was not
            #       specified on its SD ESD item.
            # idr : 0~2 IDR items contains translator identification,
            #       version and release level (e.g. 0101), and date of
            #       the assembly (yyddd)
            '02',                       # 01    : X'02'
            c2x('END'),                 # 02-04 : END
            c2x(' '),                   # 05    : Space
            end_fill(enty, 3),          # 06-08 : Entry address from END
            c2x('{0:6}'.format('')),    # 09-14 : Space
            end_fill(scp, 2),           # 15-16 : Type 1: ESDID of entry point
                                        #         Type 2: Blank
            end_fill(sym, 8),           # 17-24 : Type 1: Blank
                                        #         Type 2: Symbolic name or blank
            c2x('{0:4}'.format('')),    # 25-28 : Blank
            end_fill(csl, 4),           # 29-32 : Control section length
            end_cnt_idr(idr),           # 33    : Number of IDR items
            end_idr(idr, 0),            # 34-52 : IDR item 1
            end_idr(idr, 1),            # 53-71 : IDR item 2
            c2x(' '),                   # 72    : Space 
            ]),
    # Symbol table records provide symbol information for TSO TEST
    'SYM' : lambda vf : ''.join([
            # vf  : variable field - need info
            '02',                       # 01    : X'02'
            c2x('SYM'),                 # 02-04 : SYM
            c2x('{0:6}'.format('')),    # 05-10 : Space
            '{0:0>4}'.format(           # 11-12 : Variable field byte count
                hex(len(vf) * 8)[2:]    #         (number of bytes of text)
                ),
            c2x('{0:4}'.format('')),    # 13-16 : Space
            sym_vf(vf),                 # 17-72 : Variable fields
            ]),
    }
