from zPE import lang
from zPE import core

import sys
import os
from optparse import OptionParser


if __name__ == '__main__':
    main()


def main():
    parser = prepare_option(OptionParser())
    (options, args) = parser.parse_args()

    if options.list:
        core.list_lang()
        return 0

    if options.lang in core.LANG_SUPPORTED:
        eval(core.LANG_SUPPORTED[options.lang])(args)
    else:
        print sys.argv[0] + ': ' + options.lang + ': Language not supported.'
        print 'For more information, see \'' + sys.argv[0] + ' -l\' for help.'
        return 1


def prepare_option(parser):
    parser = OptionParser(usage="Usage: %prog [options] SOURCE_FILE(s)")

    parser.add_option("-l", "--list", action="store_true", dest="list",
                      default=False,
                      help="list all supported languages")
    parser.add_option("-L", "--lang", dest="lang",
                      default='assist',
                      help="language of the source file", metavar="LANGUAGE")

    return parser


def slv_assist(src):
    print 'process assist'
