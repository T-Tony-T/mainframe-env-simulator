# this is the zPE IO encapsulation for UI
import os, sys


def is_binary(dsn):
    if is_file(dsn):
        return __IS_BINARY(os.path.join(*dsn))
    else:
        raise ValueError


def is_file(dsn):
    return os.path.isfile(os.path.join(* dsn))

def is_dir(dsn):
    return os.path.isdir(os.path.join(* dsn))


def new_file(dsn):
    if not is_file(dsn):
        open_file(dsn, 'w')

def new_dir(dsn):
    __CREATE_DIR(os.path.join(* dsn))


def open_file(dsn, mode):
    '''Open the target file in regardless of the existance'''
    path = os.path.join(* dsn)
    __CREATE_DIR(os.path.dirname(path))

    return open(path, mode)


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

def __CREATE_DIR(path):
    '''creates (recursively) the target directory if not exists'''
    if not os.path.isdir(path):
        os.makedirs(path)


def __IS_BINARY(filename):
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
