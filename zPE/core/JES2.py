# this is a simplification of the "Job Entry Subsystem"
# it is used to manage the SPOOL files

import zPE

import os, sys
import re


# open the target file in regardless of the existance
def open_file(dsn, mode):
    path = os.path.join(zPE.conf.Config['spool_dir'], zPE.conf.Config['spool_path'])
    if not os.path.isdir(path):
        os.makedirs(path)

    return open(os.path.join(path, dsn[-1]), mode)
