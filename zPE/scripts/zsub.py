import zPE
import zfetch

import os, sys
import argparse


def main(argv = sys.argv):
    parser = prepare_option(os.path.basename(argv[0]))
    args = parser.parse_args(argv[1:])

    if args.list:
        zPE.LIST_PGM()
        return 0

    if not args.job_file:
        parser.print_help()
        return 0

    zPE.conf.read_rc()
    rc = submit(args.job_file)

    if args.output:
        zfetch.main(['zfetch', '-o', args.output[0], 'last'])

    return rc


def submit(job):
    rv = zPE.core.jcl.parse(job)
    flush_all = False
    overall_rc = 0

    if rv == 'ok':
        zPE.core.jcl.init_job()
        for step in zPE.JCL['step']:
            if flush_all:
                continue        # flush all the rest step

            if step.pgm in zPE.PGM_SUPPORTED:
                rv = zPE.core.jcl.init_step(step)
                if rv == 'ok':
                    step.rc = eval(zPE.PGM_SUPPORTED[step.pgm])(step)
                    overall_rc = max(overall_rc, step.rc)
                    if step.rc != 0:
                        rv = 'steprun'
                else:
                    step.rc = 'FLUSH'
                    flush_all = True
                zPE.core.jcl.finish_step(step)
            else:               # not in system path, search in STEPLIB
                if 'STEPLIB' in step.dd:
                    rv = zPE.core.jcl.init_step(step)
                    if rv == 'ok':
                        step.rc = zPE.core.asm.run(step)
                        overall_rc = max(overall_rc, step.rc)
                        if step.rc != 0:
                            rv = 'steprun'
                    else:
                        step.rc = 'FLUSH'
                        flush_all = True
                    zPE.core.jcl.finish_step(step)
                else:           # not found at all
                    zPE.abort(-1, 'Error: ', step.pgm,
                               ': Program not supported.\n',
                               'For more information, see \'',
                               sys.argv[0], ' -l\' for help.\n'
                               )
        # end of all steps
    else:
        overall_rc = 9       # JCL error; see zPE.__init__.py for help

    zPE.core.jcl.finish_job(rv)
    return overall_rc


def prepare_option(prog):
    parser = argparse.ArgumentParser(
        prog = prog, usage = '',
        formatter_class = argparse.RawDescriptionHelpFormatter,
        description =
'''
    %(prog)s  -h | -l
    %(prog)s  [-o OUTPUT_FILE]  JOB_FILE
'''
        )

    # positional arguments
    parser.add_argument(
        action = 'store',
        nargs = '?',
        default = '',
        help = 'the JOB file containing the JCL to be submitted',
        metavar = 'JOB_FILE',
        dest = 'job_file'
        )

    # optional arguments
    parser.add_argument(
        '-l', '--list',
        action = 'store_true',
        default = False,
        help = 'list all supported programs (PGM)',
        dest = 'list'
        )
    parser.add_argument(
        '-o', '--fetch-current',
        action = 'store',
        nargs = 1,
        default = [],
        help = "fetch the current job's output to the indicated file after the submission",
        metavar='OUTPUT_FILE',
        dest = 'output'
        )

    return parser


if __name__ == '__main__':
    main()
