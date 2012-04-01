# this is the zPE IO encapsulation for UI
import os, sys

# this module implements the following APIs:
#
#   is_binary(fn_list):         test if the fn_list corresponding to a binary file
#
#   is_file(fn_list):           test if the fn_list corresponding to a file
#   is_dir(fn_list):            test if the fn_list corresponding to a directory
#
#   norm_path_list(fn_list):    return the normalized absolute path
#   norm_path(full_path):       same as above; take a string as argument
#
#   new_file(fn_list):          create the file unless the fn_list corresponding to a file
#   new_dir(fn_list):           create the dir unless the fn_list corresponding to a directory
#
#   open_file(fn_list, mode):   open the file with the indicated mode
#   list_dir(dir_name):         list the file(s) in the indicated directory, create an empty one if not exsits
#
#   fetch(buff):                read content from the corresponding file to the zEditBuffer
#   flush(buff):                write content from the zEditBuffer to the corresponding file
#

def is_binary(fn_list):
    if is_file(fn_list):
        return __IS_BINARY(os.path.join(* fn_list))
    else:
        raise ValueError


def is_file(fn_list):
    return os.path.isfile(os.path.join(* fn_list))

def is_dir(fn_list):
    return os.path.isdir(os.path.join(* fn_list))


def norm_path_list(fn_list):
    return norm_path(os.path.join(* fn_list))

def norm_path(full_path):
    if not full_path:
        return ''            # indicates no path is given

    return os.path.normcase(        # on Windows, convert all letters to lowercase
        os.path.abspath(            # normalize the path to standard form
            os.path.realpath(       # trace and eliminates any symbolic links (need to be done before normpath/abspath)
                os.path.expanduser( # expand ~ or ~user (need to be done first)
                    full_path
                    ))))


def new_file(fn_list):
    if is_file(fn_list):
        raise IOError('File already exists.')
    elif is_dir(fn_list):
        raise IOError('File name conflict with a folder.')

    open_file(fn_list, 'w')


def new_dir(fn_list):
    if is_file(fn_list):
        raise IOError('Folder name conflict with a file.')
    elif is_dir(fn_list):
        raise IOError('Folder already exists.')

    __CREATE_DIR(os.path.join(* fn_list))


def open_file(fn_list, mode):
    '''Open the target file in regardless of the existance'''
    if isinstance(fn_list, str):
        path = fn_list
    else:
        path = os.path.join(* fn_list)

    __CREATE_DIR(os.path.dirname(path))
    return open(path, mode)


def list_dir(dir_path):
    __CREATE_DIR(dir_path)
    return os.listdir(dir_path)


def fetch(buff):
    '''Fetch the corresponding file to the indicated MainWindowBuffer'''
    if buff.path == None:
        return False

    if is_binary(buff.path):
        raise TypeError('Cannot fetch content out of a binary file.')

    fp = open_file(buff.path, 'r')
    tb = buff.buffer
    try:
        tb.set_text(fp.read().decode('utf8'))
    except:
        raise UnicodeError('File is not in UTF-8 encoding! Convert it to UTF-8 first.')
    return True

def flush(buff):
    '''Flush the indicated MainWindowBuffer to the corresponding file'''
    if buff.path == None:
        return False

    try:
        fp = open_file(buff.path, 'w')
    except:
        return False
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
