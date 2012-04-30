# general purpose utility functions

import os
import re


### JCL argument parser

## Label Parser
def bad_label(label):
    '''
    Return:
      - the position (start at 1) of the first invalid char
      - 0 if all good
      - None if no label
    '''
    if len(label) == 0:
        return None             # no lable
    if len(label) > 8:
        return 9                # label too long
    if not re.match('[A-Z@#$]', label[0]):
        return 1                # first character not legal
    for indx in range(1, len(label)):
        if not re.match('[A-Z@#$0-9]', label[indx]):
            return indx         # (indx+1)th character not legal
    return 0                    # all good

## Time Parser
def parse_time(time):
    if time.isdigit():
        return int(time) * 60
    if time[0] != '(' or time[-1] != ')':
        raise SyntaxError('Invalid format. Use TIME=(m,s) or TIME=m instead.')
    time = time[1:-1].split(',')
    if len(time) != 2:
        raise SyntaxError('Invalid format. Use TIME=(m,s) or TIME=m instead.')
    return int('{0:0>1}'.format(time[0])) * 60 + int('{0:0>1}'.format(time[1]))


## Region Parser
def parse_region(region):
    return __PARSE_REGION(region, check_alignment = True)[1]

def region_max_sz(region):
    return __PARSE_REGION(region, check_alignment = True)[0]

def parse_sz_from(sz_str):
    return __PARSE_REGION(sz_str, check_alignment = False)[0]


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


## Path Parser

def conv_path(fn):
    '''Converts "ABCD.EFG" to ["ABCD", "EFG"]'''
    return re.split('\.', fn)

def conv_back(fn_list):
    '''Converts ["ABCD", "EFG"] to "ABCD.EFG"'''
    while not fn_list[0]:       # remove leading empty nodes
        del fn_list[0]
    return '.'.join(fn_list)

def is_file(dsn):
    return os.path.isfile(os.path.join(* dsn))

def is_dir(dsn):
    return os.path.isdir(os.path.join(* dsn))

def is_pds(dsn):                # PDS is currently mapped to flat directory
    return is_dir(dsn)




### Dictionary Manipulation

def dic_append_list(dic, key, value):
    if key not in dic:
        dic[key] = []
    dic[key].append(value)

def dic_find_key(dic, val):
    '''Return the (first) key of the dic that has the given val'''
    return [k for (k, v) in dic.iteritems() if v == val][0]


### Mask Manipulation

def listify_mask(mask_hex):
    '''Convert an (hex) mask to an index list containing positions of 1-bit'''
    mask = '{0:0>4}'.format(bin(int(mask_hex, 16))[2:])
    return [ i for i in range(4) if mask[i] == '1' ]


### String Manipulation

## Digit-String Convertion
def h2i(src):
    return int(src, 16)

def h2i_sign(src):
    res = h2i(src)
    if h2i(src[0]) & 0b1000:    # sign bit on, negative
        res -= ( 0b1 << (len(src) * 4) )
    return res

def i2h(src):
    return re.split(r'[xL]', hex(src))[1].upper()

def i2h_sign(src, precision):
    '''precision is measured in number of hex digits'''
    if src < 0:
        cmp2 = ( 0b1 << (precision * 4) ) + src # 2's complement
        res = i2h(cmp2)
    else:
        res = i2h(src)
    return '{0:0>{1}}'.format(res[-precision:], precision)

def i2i_sign(src, precision_in, precision_out):
    '''precision is measured in number of hex digits'''
    if precision_in == precision_out: # no need to convert
        return src

    cmp2_in   = 0b1 << (precision_in  * 4)
    cmp2_out  = 0b1 << (precision_out * 4)

    mask_in   = cmp2_in  - 1    # all 1s
    mask_out  = cmp2_out - 1    # all 1s

    if precision_in > precision_out: # reduce precision, mask off extra bits
        return src & mask_out

    sign_in = cmp2_in >> 1      # sign bit of src

    if src & sign_in:           # src negative
        src = cmp2_out - ((cmp2_in - src) & mask_in) # 2's complement
    return src & mask_out


## Regular Expression Split
def fixed_width_split(width, src_str, flags = 0):
    return re.findall(''.join([ r'.{', str(width), r'}|.+' ]), src_str, flags)

def resplit(pattern, string, skip_l, skip_r, maxsplit = 0):
    '''
    Split the string using the given pattern like re.split(),
    except when the patten is in between skip_l and skip_r.

    There are three pre-defined skip-pattern:
      resplit_sq ==> single quotes
      resplit_dq ==> double quotes
      resplit_pp ==> pair(s) of parentheses


    Note:
      - Only include the chars as they are in skip_l/r.
        do not escape special chars.
        (no '\' unless that is one of the boundary char)
    '''
    if len(skip_l) != len(skip_r):
        raise ValueError
    return __SKIP_SPLIT(pattern, string, skip_l, skip_r, maxsplit)

def resplit_index(split_src, split_fields, field_index):
    indx_s = 0
    for i in range(field_index):
        indx_s = ( split_src.index(split_fields[i], indx_s) + # start pos
                   len(split_fields[i])                       # length
                   )
    return split_src.index(split_fields[field_index], indx_s)

def resplit_sq(pattern, string, maxsplit = 0):
    '''See resplit() for detials'''
    return resplit(pattern, string, "'", "'", maxsplit)

def resplit_dq(pattern, string, maxsplit = 0):
    '''See resplit() for detials'''
    return resplit(pattern, string, '"', '"', maxsplit)

def resplit_pp(pattern, string, maxsplit = 0):
    '''See resplit() for detials'''
    return resplit(pattern, string, '(', ')', maxsplit)


def __SKIP_SPLIT(pattern, string, skip_l, skip_r, maxsplit = 0):
    '''skip_l/r must be iterable items with corresponding pairs of dlms'''
    rv = []
    reminder = re.findall('.', string)
    current  = []               # current parsing part
    current_splitable = []      # ground level of current parsing part
    current_splitless = []      # upper levels of current parsing part
    expected = []               # expected dlm stack

    while reminder:
        if maxsplit:
            split_quota = maxsplit - len(rv)
        else:
            split_quota = 0
        next_char = reminder.pop(0)

        if split_quota >= 0:
            # more to go
            if expected:
                # waiting for ending dlm, no checking for pattern
                if next_char == expected[-1]:
                    # ending dlm encountered, return previous level
                    expected.pop()
                elif next_char in skip_l:
                    # starting dlm encountered, goto next level
                    expected.append(skip_r[skip_l.index(next_char)])
                current_splitless.append(next_char)

            elif next_char in skip_l:
                # starting dlm first encountered, check current
                if current:
                    res = re.split(
                        pattern,
                        ''.join(current_splitable),
                        split_quota
                        )
                    if len(res) > 1:
                        res[0] = ''.join(current_splitless + res[:1])
                        rv.extend(res[:-1])

                        current = res[-1:]
                        current_splitable = []
                        current_splitless = res[-1:]
                    else:
                        current_splitless.extend(current_splitable)
                        current_splitable = []
                # go to next level
                current_splitless.append(next_char)
                expected.append(skip_r[skip_l.index(next_char)])

            else:
                # ground level
                current_splitable.append(next_char)

            current.append(next_char)
        else:
            # reach length limit
            break

    if maxsplit:
        split_quota = maxsplit - len(rv)
    else:
        split_quota = 0
    if split_quota >= 0  and  current:
        res = re.split(pattern, ''.join(current_splitable), split_quota)
        if len(res) > 1:
            res[0] = ''.join(current_splitless + res[:1])
            rv.extend(res[:-1])
            reminder = res[-1:] + reminder
        else:
            reminder = current + reminder
    else:
        reminder = current + reminder
    rv.append(''.join(reminder))
    return rv


# spool encoding / decoding

SPOOL_ENCODE_MAP = {
    '\0' : '^@',
    '^'  : '^^',
    }
def spool_encode(src):
    rv = []
    while True:
        res = re.search(r'[\0^]', src)
        if res != None:         # search succeed
            rv.append(src[:res.start()])
            rv.append(SPOOL_ENCODE_MAP[src[res.start():res.end()]])
            src = src[res.end():]
        else:                   # search failed
            rv.append(src)
            break
    return ''.join(rv)

SPOOL_DECODE_MAP = {
    '^@' : '\0',
    '^^' : '^',
    }
def spool_decode(src):
    rv = []
    while True:
        res = re.search(r'\^[@^]', src)
        if res != None:         # search succeed
            rv.append(src[:res.start()])
            rv.append(SPOOL_DECODE_MAP[src[res.start():res.end()]])
            src = src[res.end():]
        else:                   # search failed
            rv.append(src)
            break
    return ''.join(rv)
def spool_decode_printable(src):
    return re.sub(r'[^\x20-\x7e\n]', u'\u220e', spool_decode(src))
