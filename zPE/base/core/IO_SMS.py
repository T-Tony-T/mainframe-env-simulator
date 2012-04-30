# this is a simplification of the "Storage Management Subsystem - IO Component"
# it is used to manage the actual (non-SPOOL) files on the storage

import os
import re


# open the target file in regardless of the existance
def open_file(dsn, mode):
    path = os.path.join(* dsn)
    __CREATE_DIR(os.path.dirname(path))

    return open(path, mode)


def rm_file(dsn):
    path = os.path.join(* dsn)
    if os.path.isfile(path):
        os.remove(path)
        path = os.path.dirname(path)
    if os.path.isdir(path):
        try:
            os.removedirs(path)
        except:
            pass
    return None


### Supporting Functions

# creates (recursively) the target directory if not exists
def __CREATE_DIR(path):
    if not path or os.path.isdir(path):
        return None
    else:
        os.makedirs(path)
