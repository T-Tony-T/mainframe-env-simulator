import os
from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "mainframe-env-simulator",
    version = "0.0.1",
    author = "Tony C. Zhang",
    author_email = "niu.tony.c.zhang@gmail.com",
    description = ("This software is a Mainframe Programming Environment Simulator running on PC (Linux, Max OS, Windows, etc.) that will compile / assemble source code written to be compiled / assembled on a Mainframe machine. The final goal is to let the developer work on their own PC when developing / testing their programs without worrying about internet connection or connection to a Mainframe machine. It is also aimed at reduce the teaching cost of IBM Assembler, COBOL, etc."),
    license = "New BSD",
    keywords = "Simulator mainframe compiler",
    url = "http://code.google.com/p/mainframe-env-simulator/",
    packages=find_packages(),
    entry_points = {
        'console_scripts': [
            'zsub = zPE.scripts.zsub:main',
            'zfetch = zPE.scripts.zfetch:main',
        ],
        'gui_scripts': [
            'zPE = zPE.zPE_gtk:main',
        ],
    },
    package_data = {
        'UI': [ '*.svg', '*.png', '*.gif' ]
    },
    long_description=read('README'),
)
