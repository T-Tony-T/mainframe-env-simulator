SYS_VAR_SYMBLE = {
    '&SYSNDX'  : 0,    # a 4 digit auto-increment number, starting at 1
    '&SYSLIST' : [],   # refer to any positional parameter in a macro definition
    '&SYSDATE' : None, # date on which source module was assembled MM/DD/YY
    '&SYSTIME' : None, # time at which source module was assembled hh.mm
    '&SYSECT'  : None, # name of the current control section
    '&SYSPARM' : None, # need info
    }

IBM_MACRO = {
    'IF'     : lambda args: [
        ],
    'ELSEIF' : lambda args: [
        ],
    'ELSE'   : lambda: [
        ],
    'ENDIF'  : lambda: [
        ],

    'SELECT' : lambda args: [
        ],
    'WHEN'   : lambda args: [
        ],
    'ENDSEL' : lambda: [
        ],

    'DO'     : lambda args: [
        ],
    'ENDDO'  : lambda: [
        ],
    }
