import zPE

import os, sys
from optparse import OptionParser


if __name__ == '__main__':
    main()


def main():
    zPE.read_rc()

    parser = prepare_option(OptionParser())
    (options, args) = parser.parse_args()

    if options.list:
        zPE.LIST_PGM()
        return 0

    if len(args) == 0:
        parser.print_help()
        return 0

    submit(args[0])


def submit(job):
    rv = zPE.core.jcl.parse(job)
    if rv == 'ok':
        zPE.core.jcl.init_job()
        for step in zPE.JCL['step']:
            if step.pgm in zPE.PGM_SUPPORTED:
                rv = zPE.core.jcl.init_step(step)
                if rv == 'ok':
                    step.rc = eval(zPE.PGM_SUPPORTED[step.pgm])(step)
                    if step.rc != 0:
                        rv = 'steprun'
                else:
                    step.rc = 'FLUSH'
                zPE.core.jcl.finish_step(step)
            else:               # not in system path, search in STEPLIB
                found_module = False
                if 'STEPLIB' in step.dd:
                    rv = zPE.core.jcl.init_step(step)
                    if rv == 'ok':
                        step.rc = zPE.core.asm.run(step)
                        if step.rc != 0:
                            rv = 'steprun'
                    else:
                        step.rc = 'FLUSH'
                    zPE.core.jcl.finish_step(step)

    zPE.core.jcl.finish_job(rv)


def prepare_option(parser):
    parser = OptionParser(usage="Usage: %prog [options] SOURCE_FILE(s)")

    parser.add_option("-l", "--list", action="store_true", dest="list",
                      default=False,
                      help="list all supported programs (PGM)")
    return parser
