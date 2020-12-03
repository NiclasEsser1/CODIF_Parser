#!/usr/local/bin/python2.7

import json
import argparse
import os
from argparse import RawTextHelpFormatter

from inc.utils import *
from inc.handler import *

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fname', '-f', action = "store", default = "", dest = "fname", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--packets', '-p', action = "store", default=-1, dest = "packets", help = "Packets to read from .dada file")

    fname = parser.parse_args().fname
    packets = int(parser.parse_args().packets)
    files = []
    for root, dirs, files in os.walk(".", topdown=False):
        for directory in dirs:
            files.append(get_file_list(directory, fname))
    print(files)
    # reader = CodifHandler(fname)
    # reader.read(packets, True)
