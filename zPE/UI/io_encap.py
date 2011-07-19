# this is the zPE IO encapsulation for UI

import zPE
import os, sys


def is_binary(dsn):
    if is_file(dsn):
        return __is_binary(os.path.join(*dsn))
    else:
        raise ValueError

def is_file(dsn):
    return zPE.is_file(dsn)

def is_dir(dsn):
    return zPE.is_dir(dsn)

def new_file(dsn):
    if not is_file(dsn):
        open_file(dsn, 'w')

def new_dir(dsn):
    if not is_dir(dsn):
        os.makedirs(os.path.join(* dsn))

def open_file(dsn, mode):
    '''Open the target file in regardless of the existance'''
    return zPE.open_file(dsn, mode, 'file')

def fetch(buff):
    '''Fetch the corresponding file to the indicated MainWindowBuffer'''
    if buff.path == None:
        return False

    if is_binary(buff.path):
        return False

    fp = open_file(buff.path, 'r')
    tb = buff.buffer
    tb.set_text(fp.read())
    return True

def flush(buff):
    '''Flush the indicated MainWindowBuffer to the corresponding file'''
    if buff.path == None:
        return False

    fp = open_file(buff.path, 'w')
    tb = buff.buffer
    fp.write(tb.get_text(tb.get_start_iter(), tb.get_end_iter(), True))
    return True


# supporting function
def __is_binary(filename):
    """Return true if the given filename is binary.
    @raise EnvironmentError: if the file does not exist or cannot be accessed.
    @attention: found @ http://bytes.com/topic/python/answers/21222-determine-file-type-binary-text on 6/08/2010
    @author: Trent Mick <TrentM@ActiveState.com>
    @author: Jorge Orpinel <jorge@orpinel.com>"""
    fin = open(filename, 'rb')
    try:
        CHUNKSIZE = 1024
        while 1:
            chunk = fin.read(CHUNKSIZE)
            if '\0' in chunk: # found null byte
                return True
            if len(chunk) < CHUNKSIZE:
                break # done
    # A-wooo! Mira, python no necesita el "except:". Achis... Que listo es.
    finally:
        fin.close()

    return False
