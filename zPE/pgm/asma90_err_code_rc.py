__I_MSG = {                     # ASMAxxxI
    }

__W_MSG = {                     # ASMAxxxW
    45  : lambda info, line: 'Register or label not previously used - {0}'.format(line[info[1]:info[2]]),
    140 : lambda info, line: 'END record missing',
    165 : lambda info, line: 'Unexpected name field',
    300 : lambda info, line: 'USING overridden by a prior active USING on statement number {0}'.format(info[1]),
    301 : lambda info, line: 'Prior active USING on statement number {0} overridden by this USING'.format(info[1]),
    302 : lambda info, line: 'USING specifies register 0 with a nonzero absolute or relocatable base address',
    303 : lambda info, line: 'Multiple address resolutions may result from this USING and the USING on statement number {0}'.format(info[1]),
    }

__E_MSG = {                     # ASMAxxxE
    29  : lambda info, line: 'Incorrect register specification - {0}'.format(line[info[1]:info[2]]),
    44  : lambda info, line: 'Undefined symbol - {0}'.format(line[info[1]:info[2]]),
    57  : lambda info, line: 'Undefined operation code - {0}'.format(line[info[1]:info[2]]),
    65  : lambda info, line: 'Unknown type - {0}'.format(line[info[1]:info[2]]),
    74  : lambda info, line: 'Illegal syntax in expansion - {0}'.format(line[info[1]:info[2]]),
    141 : lambda info, line: 'Bad character in operation code - {0}'.format(line[info[1]:info[2]]),
    142 : lambda info, line: 'Operation code not complete on first record',
    143 : lambda info, line: 'Bad character in name field - {0}'.format(line[info[1]:info[2]]),
    305 : lambda info, line: 'Operand 1 does not refer to location within reference control section',
    307 : lambda info, line: 'No active USING for operand {0}'.format(line[info[1]:info[2]]),
    308 : lambda info, line: 'Repeated register {0}'.format(line[info[1]:info[2]]),
    }

__S_MSG = {                     # ASMAxxxS
    40  : lambda info, line: 'Missing operand',
    173 : lambda info, line: 'Delimiter error, expected blank - {0}'.format(line[info[1]:info[2]]),
    174 : lambda info, line: 'Delimiter error, expected blank or comma - {0}'.format(line[info[1]:info[2]]),
    175 : lambda info, line: 'Delimiter error, expected comma - {0}'.format(line[info[1]:info[2]]),
    178 : lambda info, line: 'Delimiter error, expected comma or right parenthesis - {0}'.format(line[info[1]:info[2]]),
    }


__MSG = {
    'S' : __S_MSG,
    'E' : __E_MSG,
    'W' : __W_MSG,
    'I' : __I_MSG,
    }

def gen_msg(msg_type, info, line):
    return '** ASMA{0:0>3}{1} {2}\n'.format(info[0], msg_type, __MSG[msg_type][info[0]](info, line))
