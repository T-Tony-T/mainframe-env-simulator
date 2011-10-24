# this is the definition and the implementation of Memories
# 
# Note: in this file, "page" refers to "memory page" (a 4K frame)

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
    '''mainly for internal usage'''
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


    def dump(self, pos_s = 0, length = 4096): # default dump all
        if pos_s < 0 or pos_s >= 4096:
            raise IndexError('position must be within a Page (0 ~ 4095)!')
        if length < 0:
            raise OverflowError('length should be positive!')
        pos_e = pos_s + length

        # memory alignment
        pos_s = pos_s - pos_s % 32
        pos_e = pos_e + (32 - pos_e % 32)
        if pos_e > 4096:
            pos_e = 4096

        rv = []
        while True:
            char_arr = ''
            line = '{0:0>6}   '.format(hex(pos_s)[2:].upper())

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

            rv.append('{0}  *{1}*\n'.format(
                    line,
                    re.sub(r'[^\x21-\x7e]', '.', char_arr) # show invisible char
                    ))

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
    def __init__(self, pos_str, sz_str):
        self.min_pos = parse_sz_from(pos_str)
        self.max_pos = self.min_pos + parse_sz_from(sz_str)

        self.l_bound =      self.min_pos     / 4096 * 4096 # align to page
        self.h_bound = (self.max_pos + 4095) / 4096 * 4096 # align to page

        if self.l_bound < 0 or self.h_bound >= zPE.conf.Config['addr_max']:
            raise MemoryError   # addressing exception

        self.memory = ( Page * ((self.h_bound - self.l_bound) / 4096) )()


    def __str__(self):
        return "0x{0:0>6} ~ 0x{1:0>6} (0x{2:0>6} ~ 0x{3:0>6}) : {4}".format(
            hex(self.l_bound)[2:].upper(),
            hex(self.h_bound)[2:].upper(),
            hex(self.min_pos)[2:].upper(),
            hex(self.max_pos)[2:].upper(),
            self.memory
            )


    def dump(self, addr_s, length = 32):
        if addr_s < self.l_bound or addr_s >= self.h_bound:
            raise IndexError('address out of boundary!')
        if length < 0:
            raise OverflowError('length should be positive!')
        addr_e = min(addr_s + length, self.h_bound)

        page_indx_s = (addr_s     - self.l_bound) / 4096 # index of start page
        page_indx_e = (addr_e - 1 - self.l_bound) / 4096 # index of end page

        head_pos_s = (addr_s     - self.l_bound) % 4096
        tail_pos_e = (addr_e - 1 - self.l_bound) % 4096 + 1

        if page_indx_e == page_indx_s:  # all dumping in one page
            rv = self.__normalize(
                self.memory[page_indx_s].dump(
                    head_pos_s,
                    tail_pos_e - head_pos_s
                    ),
                self.l_bound + page_indx_s * 4096
                )
        else:                           # at least two pages
            # dump first page
            rv = self.__normalize(
                self.memory[page_indx_s].dump(head_pos_s),
                self.l_bound + page_indx_s * 4096
                )

            # dumping full-page pages { [2,n) }, if any
            for indx in range(page_indx_s + 1, page_indx_e):
                self.__concat(rv, self.__normalize(
                        self.memory[indx].dump(),
                        self.l_bound + indx * 4096
                        ))

            # dump last page
            self.__concat(rv, self.__normalize(
                    self.memory[page_indx_e].dump(
                        0,
                        tail_pos_e
                        ),
                    self.l_bound + page_indx_e * 4096
                    ))
        return '{0}{1:0>6} TO {2:0>6}\n{3}'.format(
            '                             CORE ADDRESSES SPECIFIED-     ',
            hex(addr_s)[2:].upper(),
            hex(addr_e)[2:].upper(),
            ''.join(rv)
            )

    def dump_all(self):
        return self.dump(self.l_bound, self.h_bound - self.l_bound)


    def __normalize(self, dump, addr_offset):
        rv = []
        prev = 'line #'         # initialize to not match
        dump.append('FFFFFF')   # add dummy line to flush dup
        dup = 0                 # degree of duplication
        for line in dump:
            line = '{0:0>6}{1}'.format( # update address
                hex(int(line[:6], 16) + addr_offset)[2:].upper(),
                line[6:]
                )
            if line[6:] != prev[6:]: # if content differs
                if dup > 1: # has more then 1 duplicated lines
                    rv[-1] = '    LINES    {0}-{1}    SAME AS ABOVE\n'.format(
                        rv[-1][:6], prev[:6]
                        )       # replace the 1st duplication with abbr
                dup = 0
            else:
                dup += 1
            prev = line         # update prev

            if dup < 2:         # less than 2 duplicated lines
                rv.append(line)
        rv.pop()                # remove dummy line
        return rv

    def __concat(self, dump1, dump2):
        if dump1[-1][0] == ' ':
            last_start = dump1[-2]
        else:
            last_start = dump1[-1]
        if last_start[6:] == dump2[0][6:]:
            # has cross-page duplication
            if len(dump2) > 1 and dump2[0][6:] == dump2[1][6:]:
                # 1 duplicated line in 2nd page
                dup_end = dump2[1][:6]
                dump2.pop(1) # remove duplicated line
            elif len(dump2) > 1 and dump2[1][0] == ' ':
                # more than 1 duplicated line in 2nd page
                dup_end = dump2[1][20:26] # 2nd (end) addr
                dump2.pop(1) # remove abbr
            else:
                dup_end = dump2[0][:6]
            dump2.pop(0)
            dump1[-1] = ''.join([ dump1[-1][:20], dup_end, dump1[-1][26:] ])

        dump1.extend(dump2)
        return dump1
# end of Memory class definition



## Region Parser
def parse_region(region):
    return __PARSE_REGION(region, check_alignment = True)[1]

def max_sz_of(region):
    return __PARSE_REGION(region, check_alignment = True)[0]

def parse_sz_from(sz_str):
    return __PARSE_REGION(sz_str, check_alignment = False)[0]


### Supporting Function

def __PARSE_REGION(region, check_alignment):
    region = re.split('(\d+)', region)
    if len(region) == 2:
        region = int(region[1])
    elif len(region) == 3:
        unit = region[2].upper().split()
        if len(unit) != 1:
            raise SyntaxError('Invalid region size unit. Use "B", "K" or "M" as unit.')

        unit = unit[0]
        if unit in [ 'B', 'BYTE' ]:
            region = int(region[1])
        elif unit in [ 'K', 'KB' ]:
            region = int(region[1]) * 1024
        elif unit in [ 'M', 'MB' ]:
            region = int(region[1]) * 1024 * 1024
        else:
            raise SyntaxError('Invalid region size unit. Use "B[yte]", "K[B]" or "M[B]" as unit.')
    else:
        raise SyntaxError('Invalid region size format. Should be similar to "512K" or "4096 Byte".')

    if check_alignment and region % 4096 != 0:
        raise ValueError('Region must be divisible by 4K.')

    return (region, '{0}K'.format(region / 1024))
