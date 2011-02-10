# this is the definition and the implementation of Memories

import zPE

import os, sys
import re


## Region Parser
def parse_region(region):
    return __PARSE_REGION(region)[1]

def max_sz_of(region):
    return __PARSE_REGION(region)[0]



### Supporting Function

def __PARSE_REGION(region):
    region = re.split('(\d+)', region)
    if len(region) == 2:
        region = int(region[1])
    elif (len(region) == 3) and ('K' in re.split('\s', region[2].upper())):
        region = int(region[1]) * 1024
    elif (len(region) == 3) and ('M' in re.split('\s', region[2].upper())):
        region = int(region[1]) * 1024 * 1024
    else:
        raise SyntaxError

    if region % 4096 != 0:
        raise ValueError

    return (region, '{0}K'.format(region / 1024))
