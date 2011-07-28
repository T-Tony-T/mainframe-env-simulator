from zPE.conf import CONFIG_PATH

import os, sys

import argparse
import sqlite3


def main(argv = sys.argv):
    prog_name = os.path.basename(argv[0])
    parser = prepare_option(prog_name)
    args = parser.parse_args(argv[1:])

    # check argument conflicts
    if args.list and args.purge:
        sys.stderr.write('Error: argument -l conflicting with -p!\n')
        return -1
    if args.output:
        if args.list or args.purge:
            sys.stderr.write('Error: argument -o conflicting with -l or -p!\n')
            return -1
        fetch_out = open(args.output[0], 'w')
    else:
        fetch_out = sys.stdout

    # fetch information
    conn = connect_db()
    job_listing = fetch_job_list(conn)

    # parse alias
    if args.job_id == 'first':
        job_id = job_listing[0][0]
        job_pttn = None
    elif args.job_id == 'last':
        job_id = job_listing[-1][0]
        job_pttn = None
    elif args.job_id == 'all':
        job_id = None
        job_pttn = '%'
    elif args.job_id:
        job_pttn = args.job_id.replace('*', '%').replace('?', '_')
        if job_pttn == args.job_id:
            # not a pattern
            job_id = job_pttn
            job_pttn = None
        else:
            # is a pattern
            job_id = None
    else:
        job_id = None
        job_pttn = None

    if args.dd_pttn:
        dd_pttn = args.dd_pttn.replace('*', '%').replace('?', '_')
    else:
        dd_pttn = '%'


    # check exact match if a pattern is offered
    if job_pttn:
        job_listing_pttn = fetch_job_list_by(conn, job_pttn)
        if len(job_listing_pttn) == 1:
            # exact match, switch to JOB ID
            job_id = job_listing_pttn[0][0]
            job_pttn = None


    # start processing
    if job_id:
        # JOB ID offered, try to process it
        if job_id in [ r[0] for r in job_listing ]:
            # JOB ID is valid
            if args.list:
                print_dd_list(sys.stdout, job_id, fetch_dd_list(conn, job_id))
            elif args.purge:
                delete_jobs(conn, job_id)
            else:
                for row in fetch_content(conn, job_id, dd_pttn):
                    fetch_out.write(row[0])
        else:
            # JOB ID is invalid
            sys.stderr.write('Error: ' + args.job_id +
                             ': JOB not found inside the JOB queue\n'
                             )
            return -1
    elif job_pttn:
        # JOB pattern is offered, process it
        if args.list:
            print_job_list(sys.stdout, job_listing_pttn)
        elif args.purge:
            delete_jobs(conn, job_pttn)
        else:
            sys.stderr.write('Error: Require an exact match of a JOB ID\n')
            return -1
    else:
        # no JOB ID nor JOB pattern offered, fetch all
        if args.list:
            print_job_list(sys.stdout, job_listing)
        elif args.purge:
            delete_jobs(conn, '%')
        else:
            sys.stderr.write('Error: No JOB ID offered. Run `' + prog_name +
                             ' -h` for more information.\n'
                             )
            return -1

    sys.stdout.write('\n')
    check_n_jobs(conn)

    conn.commit()
    conn.close()

    return 0


def connect_db():
    conn = sqlite3.connect(CONFIG_PATH['SPOOL'])
    conn.execute('''PRAGMA foreign_keys = ON''')
    conn.text_factory = str     # map TEXT to str instead of unicode
    return conn


def check_n_jobs(conn):
    if len(fetch_job_list(conn)) >= 15:
        # according to the current design of printing, 15 is the threshold
        # of displaying the full listing on a 24-line terminal
        # ( 24 = 3 separaters + 1 header + 15 JOBs + 2 empty lines +
        #        2 warning lines + 1 cmd prompt )
        sys.stderr.write('Warning: Too many JOBs in the JOB queue.\n' +
                         '         Use `-p` to purge the queue.\n\n')


def delete_jobs(conn, job_pttn):
    stmt = '''DELETE
                FROM  JOB
               WHERE  Job_ID LIKE ?
           '''
    conn.execute(stmt, (job_pttn,))


def fetch_content(conn, job_id, dd_pttn = '%'):
    stmt = '''SELECT  Content
                FROM  SPOOL
               WHERE  Job_ID = ?
                 AND  Spool_key LIKE ?
            ORDER BY  row_id
           '''
    return conn.execute(stmt, (job_id, dd_pttn))

def fetch_dd_list(conn, job_id):
    stmt = '''SELECT  Spool_key, Step_Name
                FROM  SPOOL
               WHERE  Job_ID LIKE ?
            ORDER BY  row_id
           '''
    return [ row for row in conn.execute(stmt, (job_id,)) ]

def fetch_job_list(conn):
    return [ row for row in conn.execute('''SELECT * FROM JOB''') ]

def fetch_job_list_by(conn, job_pttn):
    stmt = '''SELECT  *
                FROM  JOB
               WHERE  Job_ID LIKE ?
           '''
    return [ row for row in conn.execute(stmt, (job_pttn,)) ]


def print_dd_list(out, job_id, dd_list):
    out.write('\n  DD Names (and the step they belong to) in ' + job_id + ':\n')
    for r in dd_list:
        out.write('    {0:<8}    {1}\n'.format(r[0], r[1]))

def print_job_list(out, job_listing):
    out.write('\n')

    # no JOB ID offered, fetch all JOBs
    if job_listing:
        # there is at least one JOB in the queue
        out.write('  +----------+--------------+---------+\n')
        out.write('  | JOB Name | ** JOB ID ** |  Owner  |\n')
        out.write('  +----------+--------------+---------+\n')
        for r in job_listing:
            out.write('  | {0} | < {1} > | {2} |\n'.format(r[1], r[0], r[2]))
        out.write('  +----------+--------------+---------+\n')
    else:
        # no JOB in the queue
        out.write('  No JOB matches the search\n')


def prepare_option(prog):
    parser = argparse.ArgumentParser(
        prog = prog, usage = '',
        formatter_class = argparse.RawDescriptionHelpFormatter,
        description =
'''
    %(prog)s  -l | -p [JOB_ID_PATTERN]
    %(prog)s [-o OUTPUT_FILE]  JOB_ID [DD_PATTERN]

Note: JOB_ID_PATTERN can be a JOB ID, a pattern like '*1013?' (matches all
      JOBs from 'JOB10130' to 'JOB10139'), or one of the following:
          'first', 'last' : the first / last JOB in the JOB queue
          'all'           : all JOBs in the JOB queue, same as '*'
'''
        )

    # positional arguments
    parser.add_argument(
        action = 'store',
        nargs = '?',
        default = None,
        help = ( 'the JOB ID (pattern) of the JOB to be fetched or listed. ' +
                 'Any pattern without an exact match can only be used with ' +
                 '`-l` or `-p`'
                 ),
        metavar = 'JOB_ID | JOB_ID_PATTERN',
        dest = 'job_id'
        )

    parser.add_argument(
        action = 'store',
        nargs = '?',
        default = None,
        help = 'the pattern of DD Names in the JOB to be fetched',
        metavar = 'DD_PATTERN',
        dest = 'dd_pttn'
        )


    # optional arguments
    parser.add_argument(
        '-l', '--list',
        action = 'store_true',
        default = False,
        help = ( 'list all DD Names of all outputs in the indicated JOB,' +
                 ' or all matched JOBs if no JOB pattern is offered but ' +
                 'not an exact match'
                 ),
        dest = 'list'
        )
    parser.add_argument(
        '-o', '--output',
        action = 'store',
        nargs = 1,
        default = [],
        help = ( 'write the fetched JOB output into the indicated file, ' +
                 'instead of print it on screen'
                 ),
        metavar = 'OUTPUT_FILE',
        dest = 'output'
        )
    parser.add_argument(
        '-p', '--purge',
        action = 'store_true',
        default = False,
        help = 'perge the indicated JOB(s) from the JOB queue',
        dest = 'purge'
        )

    return parser


if __name__ == '__main__':
    main()
