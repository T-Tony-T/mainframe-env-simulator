# this is a simplification of the "Job Entry Subsystem"
# it is used to manage the SPOOL files

import zPE

import os, sys
import re

import sqlite3


class JES_DB(object):
    @staticmethod
    def append(src, dest):
        return src + dest

    def __init__(self, job_id, job_name, owner, spool_key):
        self.__job_id = job_id
        self.__job_name = job_name
        self.__owner = owner
        self.__spool_key = spool_key

        self.__buffer = ''      # the buffer for output

        # connect db
        self.__db = sqlite3.connect(zPE.conf.CONFIG_PATH['SPOOL'])
        self.__db.create_function("append", 2, JES_DB.append) # register `append(src, dest)` to SQLite
        self.__db.text_factory = str                          # map TEXT to str instead of unicode
        self.__db_opened = True

        self.__c  = self.__db.cursor()

        # insert JOB information
        self.__c.execute('''SELECT Job_ID FROM JOB WHERE Job_ID = ?''', (self.__job_id,))
        if not self.__c.fetchone():
            self.__c.execute(
                '''INSERT INTO JOB VALUES (?, ?, ?)''',
                ( self.__job_id, self.__job_name, self.__owner, )
                )

        # initiate SPOOL information
        self.__c.execute(
            '''INSERT INTO SPOOL VALUES (NULL, ?, ?, ?)''',
            ( self.__job_id, self.__spool_key, '', )
            )

        self.__db.commit()


    def __del__(self):
        if self.__db_opened:
            self.close()


    def close(self):
        self.flush()

        self.__c.close()
        self.__db.close()
        self.__db_opened = False


    def flush(self):
        if not self.__buffer:
            return              # no need to flush, early return

        self.__c.execute(
            '''UPDATE SPOOL set Content = append(Content, ?) where Job_id = ? AND Spool_key = ?''',
            ( self.__buffer, self.__job_id, self.__spool_key )
            )

        # clear buffer
        self.__buffer = ''
        self.__db.commit()


    def write(self, line, force_flush = False):
        self.__buffer += line
        if force_flush:
            self.flush()


# open the target file in regardless of the existance
def open_file(dsn, mode):
    return JES_DB(zPE.JCL['jobid'], zPE.JCL['jobname'], zPE.JCL['owner'], os.path.join(* dsn))
