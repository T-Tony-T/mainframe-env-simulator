import zPE

import os, sys


def init(step):
    print 'now running ASSIST with:'
    print step.dd['SYSIN']

#    dump()
    return -1


import pprint
def dump():
    print
    print

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(zPE.JCL)
    for step in zPE.JCL['step']:
        pp.pprint(step.__dict__)
        for indx in range(len(step.dd)):
            print '{0:<8}: {1}'.format(step.dd.key(indx), step.dd[indx])

    print
    print

    for k,v in zPE.core.SPOOL.dict():
        print k, v

