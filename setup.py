#!/usr/bin/env python

import os, sys
from setuptools import setup, find_packages
from shutil import copytree     # for including data files under Windows

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name = "mainframe-env-simulator",
    keywords = "simulator mainframe compiler",

    # M.FFF{.dev-rR} / M.FFF-rcP / M.FFF[-B]
    # where as:
    #   M - Major Version Number (int)
    #   F - Functional Update Number (alnum[3])
    #   R - SVN Revision Number (int) [ developing version ]
    #   P - Pre-Release Number (int)  [ release candidate  ]
    #   B - Bug-Fix Number (int)      [ normal release     ]
    version = "0.815",
    # note:
    #   Major version is considered as:
    #     0 - None   Fully Functional - current
    #     1 - ASSIST Fully Functional - coming
    #     2 - HLASM  Fully Functional - planning
    #     3 - COBOL  Fully Functional - planning
    #     4 - ...
    #   {.dev-rR} is appended by ./setup.cfg; remove it before packaging
    #   [-B] is optional; add it only for bug-fixes

    author = "Tony C. Zhang",
    author_email = "niu.tony.c.zhang@gmail.com",
    url = "http://code.google.com/p/mainframe-env-simulator/",

    description = ("This software is a Mainframe Programming Environment Simulator running on PC (Linux, Max OS, Windows, etc.) that will compile / assemble source code written to be compiled / assembled on a Mainframe machine. The final goal is to let the developer work on their own PC when developing / testing their programs without worrying about internet connection or connection to a Mainframe machine. It is also aimed at reduce the teaching cost of IBM Assembler, COBOL, etc."),
    long_description=read('README'),
    license = "BSD 3-Clause",

    packages = find_packages(),
    include_package_data = True, # include every data file under SVN control
    zip_safe = False,            # do NOT install as a zip file; install as dir

    entry_points = {
        'console_scripts': [
            'zsub   = zPE.scripts.zsub:main',
            'zfetch = zPE.scripts.zfetch:main',
            ],
        'gui_scripts': [
            'zPE    = zPE.scripts.zPE_gtk:main',
            ],
        },
    )


# including data files under Windows
if sys.argv[1] == 'build':
    for (base_path, dirs, files) in os.walk('build'):
        if base_path.endswith(os.path.join('zPE', 'UI')):
            if 'image' not in dirs:
                copytree(
                    os.path.join('zPE', 'UI', 'image'), # from src dir
                    os.path.join(base_path, 'image')    # to build dir
                    )
            if 'zMajorMode' not in dirs:
                copytree(
                    os.path.join('zPE', 'UI', 'zMajorMode'), # from src dir
                    os.path.join(base_path, 'zMajorMode')    # to build dir
                    )
