# this defines the CPU execution details

import zPE

from reg import GPR, SPR


### 


### Interface Function Definition

def fetch(mem, addr):
    

    return 


def execute(ins):
    

    return


def parse_time(time):
    if time.isdigit():
        return int(time) * 60
    if time[0] != '(' or time[-1] != ')':
        raise SyntaxError('Invalid format. Use TIME=(m,s) or TIME=m instead.')
    time = time[1:-1].split(',')
    if len(time) != 2:
        raise SyntaxError('Invalid format. Use TIME=(m,s) or TIME=m instead.')
    return int('{0:0>1}'.format(time[0])) * 60 + int('{0:0>1}'.format(time[1]))
###


### Internal Functions
