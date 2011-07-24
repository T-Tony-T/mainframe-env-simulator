# this is the definition and the implementation of Memories

import zPE

import os, sys
import re
from ctypes import *            # for Union and C-Style array
from struct import *            # for pack and unpack


### Supporting Variables and Classes
_CONV_ = {                      # converter for big endian int
    'hw' : Struct('>H'),        # for half word
    'fw' : Struct('>L'),        # for full word
    'dw' : Struct('>Q'),        # for double word
    }

class _BYTE_(Union):
    _fields_ = [
        ('char', c_char),
        ('int8', c_ubyte)
        ]
### End of Supporting Definition


## Memory Page
# KeyError:    invalid index type
# IndexError:  invalid index value
# ValueError:  invalid value
# SyntaxError: invalid formatter
class Page(Structure):
    _fields_ = [                # each page is 4K in size
        ('bytes', c_ubyte * 4096)
        ]

    def __getitem__(self, key):
        if isinstance(key, int):
            rv = '{0:0>2}'.format(hex(self.bytes[key])[2:])
            return rv.upper()
        else:                   # slice
            (in_s, in_e, step) = key.indices(len(self.bytes))
            rv = ''
            for indx in range(in_s, in_e):
                rv = '{0}{1:0>2}'.format(rv, hex(self.bytes[indx])[2:])
            return rv.upper()

    def __setitem__(self, key, val):
        if not isinstance(key, int):
            raise KeyError
        self.__set_char(key, val)


    def store(self, pos, val, fmt = 'fw'):
        if not isinstance(pos, int):
            raise KeyError

        # if storing a single byte, no need to bit-reverse
        if fmt == 'bw':
            self.__set_char(pos, val)
            return None         # early return

        # otherwise, alignment checking is performed first
        key = self.__range_of(pos, fmt)

        # pack it to big endian, and convert it into a list of int
        val = _CONV_[fmt].pack(val)
        val_list = self.__to_list(val)

        self.__set_slice(key, val_list)


    def retrive(self, pos, fmt = 'fw'):
        if not isinstance(pos, int):
            raise KeyError

        # if retriving a single byte, no need to bit-reverse
        if fmt == 'bw':
            return self.__get_char(pos, val) # early return

        # otherwise, alignment checking is performed first
        key = self.__range_of(pos, fmt)

        # convert the list of int into a packed number, and unpack it
        val = self.__to_pack(self.__get_slice(key))
        return _CONV_[fmt].unpack(val)[0]


    def dump(self, pos_s, pos_e):
        if pos_s >= pos_e:
            raise IndexError

        pos_s = pos_s - pos_s % 32 # memory alignment
        if pos_e > 4096:
            pos_e = 4096
        rv = []
        while True:
            char_arr = ''
            line = '{0:0>6}   '.format(hex(pos_s)[2:])

            for indx in range(0, 4):
                line += self.__getitem__(slice(pos_s, pos_s + 4)) + ' '
                char_arr += self.__to_pack(
                    self.__get_slice(slice(pos_s, pos_s + 4))
                    )
                pos_s += 4
            line += '   '
            for indx in range(0, 4):
                line += self.__getitem__(slice(pos_s, pos_s + 4)) + ' '
                char_arr += self.__to_pack(
                    self.__get_slice(slice(pos_s, pos_s + 4))
                    )
                pos_s += 4

            rv.append('{0}  *{1}*\n'.format(line, char_arr))

            if pos_s >= pos_e:
                return rv

    ## private function

    # pos: starting position
    # fmt: one of ['hw', 'fw', 'dw']
    # rv:  slice of the required range
    def __range_of(self, pos, fmt):
        if fmt == 'hw':
            if pos % 2 != 0:
                raise IndexError
            key = slice(pos, pos+2)
        elif fmt == 'fw':
            if pos % 4 != 0:
                raise IndexError
            key = slice(pos, pos+4)
        elif fmt == 'dw':
            if pos % 8 != 0:
                raise IndexError
            key = slice(pos, pos+8)
        else:
            raise SyntaxError
        return key

    # key:       int
    # rv / val:  int
    def __get_char(self, key):
        return self.bytes[key]
    def __set_char(self, key, val):
        self.bytes[key] = val

    # key:       slice
    # rv / val:  list of int
    def __get_slice(self, key):
        (in_s, in_e, step) = key.indices(len(self.bytes))
        rv = []
        for indx in range(in_s, in_e):
            rv.append(self.bytes[indx])
        return rv
    def __set_slice(self, key, val):
        (in_s, in_e, step) = key.indices(len(self.bytes))

        if len(val) != in_e - in_s:
            raise ValueError

        for indx in range(in_s, in_e):
            self.bytes[indx] = val[indx - in_s]

    # val:       packed int
    # val_list:  list of int
    def __to_pack(self, val_list):
        sz = len(val_list)
        val = ''
        byte = _BYTE_()
        for indx in range(0, sz):
            byte.int8 = val_list[indx]
            val += byte.char
        return val
    def __to_list(self, val):
        sz = len(val)
        val_list = []
        byte = _BYTE_()
        for indx in range(0, sz):
            byte.char = val[indx]
            val_list.append(byte.int8)
        return val_list
# end of Page class definition


## Virtual Memory
# MemoryError:   addressing exception
class Memory(object):
    def __init__(self, pos, sz):
        if pos < 0 or pos + sz >= zPE.conf.Config['addr_max']:
            raise MemoryError   # addressing exception
        self.pos = pos
        self.memory = ( Page * (sz % 4096 + 1) )()


# end of Memory class definition



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
    elif (len(region) == 3) and ('K' in re.split('\s+', region[2].upper())):
        region = int(region[1]) * 1024
    elif (len(region) == 3) and ('M' in re.split('\s+', region[2].upper())):
        region = int(region[1]) * 1024 * 1024
    else:
        raise SyntaxError

    if region % 4096 != 0:
        raise ValueError

    return (region, '{0}K'.format(region / 1024))
