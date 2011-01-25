import zPE
from zPE import pgm
from zPE import core

import os, sys
from optparse import OptionParser


if __name__ == '__main__':
    main()


def main():
    zPE.read_rc()

    parser = prepare_option(OptionParser())
    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.print_help()
        return 0

    if options.list:
        zPE.LIST_LANG()
        return 0

    rv = core.jcl.parse(args[0])
    if rv == 'ok':
        for step in zPE.JCL['step']:
            if step.pgm in zPE.PGM_SUPPORTED:
                rv = zPE.core.jcl.init_step(step)
                if rv == 'ok':
                    eval(zPE.PGM_SUPPORTED[step.pgm])(args)
                zPE.core.jcl.finish_step(step)
            else:               # not in system path, search in STEPLIB
                found_module = False
                if 'STEPLIB' in step.dd:
                    rv = zPE.core.jcl.init_step(step)
                    if rv == 'ok':
                        zPE.core.asm.run(step)
                    zPE.core.jcl.finish_step(step)

    core.jcl.finish_job(rv)


def prepare_option(parser):
    parser = OptionParser(usage="Usage: %prog [options] SOURCE_FILE(s)")

    parser.add_option("-l", "--list", action="store_true", dest="list",
                      default=False,
                      help="list all supported programs (PGM)")
    return parser
