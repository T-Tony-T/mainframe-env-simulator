# this is the zPE IO encapsulation for UI

import zPE
import os, sys


def is_file(dsn):
    return zPE.is_file(dsn)

def is_dir(dsn):
    return zPE.is_dir(dsn)

def open_file(dsn, mode):
    '''Open the target file in regardless of the existance'''
    return zPE.open_file(dsn, mode, 'file')

def fetch(buff):
    '''Fetch the corresponding file to the indicated MainWindowBuffer'''
    if buff.path == None:
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
