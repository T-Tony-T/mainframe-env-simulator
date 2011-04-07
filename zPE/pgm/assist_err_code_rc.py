def __format(msg, pos):
    if len(msg) < 27:
        offset = 0
    else:
        offset = len(msg) - 27
    return '{0:<27}{1:->{2}}${1:->{3}} <-ERROR'.format(msg, '-', pos - offset, 71 - pos)

__I_MSG = {                     # ASMAxxxI
    }

__W_MSG = {                     # ASMAxxxW
    45  : lambda info, line: __format('W-REGISTER NOT USED', info[1]),
    140 : lambda info, line: __format('W-END CARD MISSING-SUPPLIED', info[1]),
    165 : lambda info, line: __format('W-LABEL NOT ALLOWED', info[1]),
    300 : lambda info, line: __format('W-USING OVERRIDDEN', info[1]),
    301 : lambda info, line: __format('W-USING OVERRIDDEN', info[1]),
    302 : lambda info, line: __format('W-USING R0 WITH NON-ZERO ADDRESS', info[1]),
    303 : lambda info, line: __format('W-MULTIPLE ADDRESS RESOLUTION', info[1]),
    }

__E_MSG = {                     # ASMAxxxE
    29  : lambda info, line: __format('INVALID REGISTER', info[1]),
    44  : lambda info, line: __format('UNDEFINED SYMBOL', info[1]),
    57  : lambda info, line: __format('INVALID OP-CODE', info[1]),
    65  : lambda info, line: __format('ILLEGAL CONSTANT TYPE', info[1]),
    74  : lambda info, line: __format('UNEXPECTED END OF EXPRESSION', info[1]),
    141 : lambda info, line: __format('INVALID OP-CODE', info[1]),
    142 : lambda info, line: __format('INVALID OP-CODE', info[1]),
    143 : lambda info, line: __format('INVALID SYMBOL', info[1]),
    305 : lambda info, line: __format('RELOCATABLE EXPRESSION REQUIRED', info[1]),
    307 : lambda info, line: __format('ADDRESSIBILITY ERROR', info[1]),
    308 : lambda info, line: __format('REPEATED REGISTER', info[1]),
    }

__S_MSG = {                     # ASMAxxxS
    40  : lambda info, line: __format('MISSING OPERAND', info[1]),
    173 : lambda info, line: __format('INVALID DELIMITER', info[1]),
    174 : lambda info, line: __format('INVALID DELIMITER', info[1]),
    175 : lambda info, line: __format('INVALID DELIMITER', info[1]),
    178 : lambda info, line: __format('UNEXPECTED END OF EXPRESSION', info[1]),
    }


__MSG = {
    'S' : __S_MSG,
    'E' : __E_MSG,
    'W' : __W_MSG,
    'I' : __I_MSG,
    }

def gen_msg(msg_type, info, line):
    return '----->AS{0:0>3}{1} {2}\n'.format(info[0], msg_type, __MSG[msg_type][info[0]](info, line))