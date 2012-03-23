# this is the "Major Editing Mode" selector
# each Major Mode is defined as an resource module in "zMajorMode" resource folder

import os


def list():
    return os.listdir(os.path.join(os.path.dirname(__file__), "zMajorMode"))
