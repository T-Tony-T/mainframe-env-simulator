import zPE
from zPE import pgm
from zPE import core

import os, sys
from optparse import OptionParser


if __name__ == '__main__':
    main()


def main():
    if os.path.isfile(zPE.CONFIG_FILE):
        zPE.Read_Config()
    else:
        zPE.Touch_Config()

    parser = prepare_option(OptionParser())
    (options, args) = parser.parse_args()

    if options.list:
        zPE.LIST_LANG()
        return 0

    core.jcl.parse(args[0])
    for step in zPE.JCL['step']:
        if step.pgm in zPE.PGM_SUPPORTED:
            eval(zPE.PGM_SUPPORTED[step.pgm])(args)
        else:
            print sys.argv[0] + ': ' + step.pgm + ': Program not supported.'
            print ('For more information, see \'' + sys.argv[0] +
                   ' -l\' for help.')
            return 1

    core.jcl.write_out()


def prepare_option(parser):
    parser = OptionParser(usage="Usage: %prog [options] SOURCE_FILE(s)")

    parser.add_option("-l", "--list", action="store_true", dest="list",
                      default=False,
                      help="list all supported programs (PGM)")
    return parser
