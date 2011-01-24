import os, sys


if __name__ == '__main__':
    main()


def main(argv = []):
    if len(argv) != 0:
        sys.argv = argv
    print 'now running ASSIST with:'
    print sys.argv
