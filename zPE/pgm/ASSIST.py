import zPE

import os, sys


if __name__ == '__main__':
    main()


def main(argv = []):
    if len(argv) != 0:
        sys.argv = argv

    print 'now running ASSIST with:'
    print sys.argv

#    dump()

import pprint
def dump():
    print
    print

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(zPE.JCL)
    pp = pprint.PrettyPrinter(indent=4)
    for step in zPE.JCL['step']:
        pp.pprint(step.__dict__)

    print
    print

    pp = pprint.PrettyPrinter(indent=4, depth=2)
    pp.pprint(zPE.SPOOL)
    pp = pprint.PrettyPrinter(indent=4)
    for k,v in zPE.SPOOL.items():
        pp.pprint(v[2])
        print os.path.join(* v[2])

