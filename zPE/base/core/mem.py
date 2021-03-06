# this is the definition and the implementation of Memories
# 
# Note: in this file, "page" refers to "memory page" (a 4K frame)

from zPE.util import *
from zPE.util.conv import *
from zPE.util.global_config import *
from zPE.util.excptn import *

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
    '''
    C-style Structure class
    mainly for internal usage
    '''
    _fields_ = [                # each page is 4K in size
        ('bytes', c_ubyte * 4096) # C-style array
        ]

    def __getitem__(self, key):
        if isinstance(key, int) or isinstance(key, long):
            return '{0:0>2}'.format(i2h(self.bytes[key]))
        else: # slice
            (in_s, in_e, step) = key.indices(len(self.bytes))
            rv = []
            for indx in range(in_s, in_e):
                rv.append('{0:0>2}'.format(i2h(self.bytes[indx])))
            return ''.join(rv)

    def __setitem__(self, key, val):
        if isinstance(key, int) or isinstance(key, long):
            self.__set_char(key, val)
        else:
            raise KeyError('{0}: Invalid key.'.format(key))


    def store(self, pos, val, fmt = 'fw'):
        if not isinstance(pos, int):
            raise KeyError('{0}: Position must be an integer.'.format(pos))
        if pos < 0:             # handle nagetive index
            pos += 4096
        if pos >= 4096:
            raise KeyError('{0}: Position must be less than 4K.'.format(pos))

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


    def retrieve(self, pos, fmt = 'fw'):
        if not isinstance(pos, int):
            raise KeyError('{0}: Position must be an integer.'.format(pos))
        if pos < 0:             # handle nagetive index
            pos += 4096
        if pos >= 4096:
            raise KeyError('{0}: Position must be less than 4K.'.format(pos))

        # if retrieving a single byte, no need to bit-reverse
        if fmt == 'bw':
            return self.__get_char(pos) # early return

        # otherwise, alignment checking is performed first
        key = self.__range_of(pos, fmt)

        # convert the list of int into a packed number, and unpack it
        val = self.__to_pack(self.__get_slice(key))
        return _CONV_[fmt].unpack(val)[0]


    def dump(self, pos_s = 0, length = 4096): # default dump all
        if not 0 <= pos_s < 4096:
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
            line = '{0:0>6}   '.format(i2h(pos_s))

            for indx in range(0, 4):
                line += self.__getitem__(slice(pos_s, pos_s + 4)) + ' '
                char_arr += x2c(self.__getitem__(slice(pos_s, pos_s + 4)))
                pos_s += 4
            line += '   '
            for indx in range(0, 4):
                line += self.__getitem__(slice(pos_s, pos_s + 4)) + ' '
                char_arr += x2c(self.__getitem__(slice(pos_s, pos_s + 4)))
                pos_s += 4

            rv.append('{0}  *{1}*\n'.format(
                    line,
                    re.sub(r'[^ A-Z0-9]', '.', char_arr) # hide binary code
                    ))

            if pos_s >= pos_e:
                return rv

    ## private function

    # pos: starting position
    # fmt: one of ['hw', 'fw', 'dw']
    # rv:  slice of the required range
    def __range_of(self, pos, fmt):
        if fmt not in fmt_align_map:
            raise SyntaxError('{0}: Invalid format.'.format(fmt))

        align = fmt_align_map[fmt]
        if pos % align != 0:
            raise IndexError('{0}: {1}'.format(
                    pos,
                    'Position not aligned on ',
                    fmt_name_map[fmt],
                    ' boundary.'
                    ))
        return slice(pos, pos + align)

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
            raise ValueError('{0}: Length not match with the key.'.format(val))

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

class Memory(object):
    allocation = {
        # ( loc_s, loc_e ) : Memory
        }

    # the following 3 should be manipulated by Memory.[de]ref_page() only
    _pool_available = [ ]
    _pool_allocated = {
        # Page index : Page
        }
    _page_ref_cnt = {
        # Page index : reference counter
        }

    @staticmethod
    def ref_page(indx):
        if indx in Memory._page_ref_cnt:
            Memory._page_ref_cnt[indx] += 1
            page = Memory._pool_allocated[indx] # retrieve the allocated page
        else:
            Memory._page_ref_cnt[indx] = 1
            if Memory._pool_available:
                page = Memory._pool_available.pop() # get a released page
            else:
                page = Page() # allocate a new page
            Memory._pool_allocated[indx] = page
        return page

    @staticmethod
    def deref_page(indx):
        Memory._page_ref_cnt[indx] -= 1
        if not Memory._page_ref_cnt[indx]:
            Memory._pool_available.append(Memory._pool_allocated[indx])
            del Memory._pool_allocated[indx]
            del Memory._page_ref_cnt[indx]

    @staticmethod
    def is_available(loc_start, loc_end):
        for key in sorted(Memory.allocation, key = lambda t: t[0]):
            window_s = key[0]
            window_e = key[1]
            # ----  |    |          loc_start < loc_end   < window_s  < window_e
            #    ---+    |          loc_start < loc_end   = window_s  < window_e
            #     --|--  |          loc_start < window_s  < loc_end   < window_e
            #       | -- |          window_s  < loc_start < loc_end   < window_e
            #      -|----|-         loc_start < window_s  < window_e  < loc_end
            #       |  --|--        window_s  < loc_start < window_e  < loc_end
            #       |    +---       window_s  < window_e  = loc_start < loc_end
            #       |    |  ----    window_s  < window_e  < loc_start < loc_end
            if loc_start < window_e  and  window_s < loc_end:
                return False
        return True

    def __new__(cls, pos_str, sz_str):
        self = object.__new__(cls)

        if isinstance(pos_str, int) or isinstance(pos_str, long):
            self.min_pos = pos_str
        else:
            self.min_pos = parse_sz_from(pos_str)
        if isinstance(sz_str, int) or isinstance(sz_str, long):
            self.max_pos = self.min_pos + sz_str
        else:
            self.max_pos = self.min_pos + parse_sz_from(sz_str)

        # calculate the page boundaries
        self.page_s =      self.min_pos     / 4096
        self.page_e = (self.max_pos + 4095) / 4096
        self.l_bound = self.page_s * 4096
        self.h_bound = self.page_e * 4096

        if self.l_bound < 0 or self.h_bound >= Config['addr_max']:
            raise MemoryError('{0} 0x{1:0>6} ~ 0x{2:0>6}'.format(
                    'Addressing Exception: Valid address range is:',
                    0, i2h(Config['addr_max'])
                    ))

        # allocate the memory
        if Memory.is_available(self.min_pos, self.max_pos):
            self.memory = [ ]
            for i in range(self.page_s, self.page_e):
                page = Memory.ref_page(i) # increment ref counter of page i
                self.memory.append(page)  # append the page to the allocation
            Memory.allocation[self.min_pos, self.max_pos] = self
            return self
        else:
            raise MemoryError('Access denied: specific memory not available.')

    def release(self):
        for i in range(self.page_s, self.page_e):
            Memory.deref_page(i) # decrement ref counter of page i
        self.memory = [ ]        # empty the allocation
        del Memory.allocation[self.min_pos, self.max_pos] # release it

    def __str__(self):
        return "0x{0:0>6} ~ 0x{1:0>6} (0x{2:0>6} ~ 0x{3:0>6}) : {4}".format(
            i2h(self.l_bound), i2h(self.h_bound),
            i2h(self.min_pos), i2h(self.max_pos),
            self.memory
            )

    def __getitem__(self, key):
        if isinstance(key, int) or isinstance(key, long):
            addr_s = key
            if addr_s < 0:      # handle negative index
                addr_s += self.h_bound
            if not self.l_bound <= addr_s < self.h_bound:
                raise IndexError('address out of boundary!')
            addr_e = addr_s + 1
        else: # slice
            addr_s = key.start
            addr_e = key.stop
            if addr_s == None:  # handle missing index
                addr_s = self.l_bound
            elif addr_s < 0:    # handle negative index
                addr_s += self.h_bound
            if addr_e == None:  # handle missing index
                addr_e = self.h_bound
            elif addr_e < 0:    # handle negative index
                addr_e += self.h_bound
            if not self.l_bound <= addr_s < self.h_bound:
                raise IndexError('starting address out of boundary!')
            if not self.l_bound <= addr_e < self.h_bound:
                raise IndexError('ending address out of boundary!')

        rv_list = self.__access(
            addr_s,
            addr_e,
            with_func = lambda page_indx, pos, length, data:
                self.memory[page_indx][pos : pos + length],
            against_data = None
            )
        return ''.join(rv_list)

    def __setitem__(self, key, hex_str):
        if not isinstance(key, int) and not isinstance(key, long):
            raise KeyError('{0}: Invalid key.'.format(key))
        if len(hex_str) % 2 != 0:
            raise ValueError('Invalid hex string length.')
        addr_s = key
        if addr_s < 0:      # handle negative index
            addr_s += self.h_bound
        if not self.l_bound <= addr_s < self.h_bound:
            raise IndexError('address out of boundary!')
        addr_e = addr_s + len(hex_str) / 2

        def setter(page_indx, pos, length, data):
            for i in range(pos, pos + length):
                self.memory[page_indx][i] = int(data.pop(0), 16)
        self.__access(
            addr_s,
            addr_e,
            with_func = setter,
            against_data = [ hex_str[i:i+2] for i in range(0, len(hex_str), 2) ]
            )


    def dump(self, addr_s, length = 32):
        if not self.l_bound <= addr_s < self.h_bound:
            raise IndexError('address out of boundary!')
        if length < 0:
            raise OverflowError('length should be positive!')
        addr_e = min(addr_s + length - 1, self.h_bound)

        rv_list = self.__access(
            addr_s,
            addr_e,
            lambda page_indx, pos, length, data:
                self.__normalize(
                    self.memory[page_indx].dump(pos, length),
                    self.l_bound + page_indx * 4096
                    ),
            against_data = None
            )
        rv = rv_list.pop()
        while len(rv_list):
            self.__concat(rv, rv_list.pop())

        rv.insert(0, '{0}{1:0>6} TO {2:0>6}\n'.format(
                '                             CORE ADDRESSES SPECIFIED-     ',
                i2h(addr_s), i2h(addr_e)
                ))              # prepend the header
        return rv

    def dump_all(self):
        return self.dump(self.min_pos, self.max_pos - self.min_pos)

    @staticmethod
    def dump_storage(loc_s, loc_e):
        for key in sorted(Memory.allocation, key = lambda t: t[0]):
            l_bound = (key[0] / 4096    ) * 4096 # get page start
            h_bound = (key[1] / 4096 + 1) * 4096 # get page end
            if l_bound <= loc_s < loc_e <= h_bound:
                return Memory.allocation[key].dump(loc_s, loc_e - loc_s)
        raise MemoryError('Access denied: specific memory not available.')

    @staticmethod
    def deref_storage(loc_s, loc_e):
        for key in sorted(Memory.allocation, key = lambda t: t[0]):
            if key[0] <= loc_s < loc_e <= key[1]:
                return Memory.allocation[key][loc_s : loc_e]
        raise MemoryError('Access denied: specific memory not available.')


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

    def __access(self, addr_s, addr_e, with_func, against_data):
        '''
        access the memory ranged from addr_s to (but not include) addr_e
        using `with_func` against "against_data"

        with_func(page_indx, pos, length, data):
            page_indx : index of the page to be accessed, relative to the
                        first page within the memory allocation
            pos       : starting position of the current page
            length    : length to be processed within the current page
            data      : the against_data (possibly None) described below

        against_data: the data the the with_func is running against

        return a list of what the with_func returns
        '''
        page_indx_s = (addr_s     - self.l_bound) / 4096 # index of start page
        page_indx_e = (addr_e - 1 - self.l_bound) / 4096 # index of end page

        head_pos_s = (addr_s     - self.l_bound) % 4096
        tail_pos_e = (addr_e - 1 - self.l_bound) % 4096 + 1

        rv = []
        if page_indx_s > page_indx_e:    # nothing need to be retrieved
            pass
        elif page_indx_s == page_indx_e: # all retrieving done in one page
            rv.append(with_func(
                    page_indx_s,
                    head_pos_s,
                    tail_pos_e - head_pos_s,
                    against_data
                    ))
        else:                            # at least two pages
            # retrieve first page
            rv.append(with_func(
                    page_indx_s,
                    head_pos_s,
                    4096 - head_pos_s,
                    against_data
                    ))

            # retrieving full-page pages { [2,n) }, if any
            for indx in range(page_indx_s + 1, page_indx_e):
                rv.append(with_func(indx, 0, 4096, against_data))

            # retrieve last page
            rv.append(with_func(page_indx_e, 0, tail_pos_e, against_data))
        return rv


    def __normalize(self, dump, addr_offset):
        rv = []
        prev = 'line #'         # initialize to not match
        dump.append('FFFFFF')   # add dummy line to flush dup
        dup = 0                 # degree of duplication
        for line in dump:
            line = '{0:0>6}{1}'.format( # update address
                i2h(int(line[:6], 16) + addr_offset),
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
# end of Memory class definition

