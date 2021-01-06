#!/usr/local/bin/python2.7

import json
import curses
import argparse
import os
from argparse import RawTextHelpFormatter

from inc.codif import *
from inc.constants import *

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fname', '-f', action = "store", default = "2020-12-07-14:58:18_0000063984107520.000000.dada", dest = "fname", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--dir', '-d', action = "store", default = "/beegfsEDD/NESSER/PAF12_2020/2020-12-07/2020-12-07-14:58:18/numa8/", dest = "dir", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--packets', '-p', action = "store", default=-1, dest = "packets", help = "Packets to read from .dada file")
    parser.add_argument('--verbose', '-v', action = "store", default=0, dest = "verbose", help = "Packets to read from .dada file")
    parser.add_argument('--start', '-s', action = "store", default=0, dest = "start", help = "Packets to read from .dada file")

    fname = parser.parse_args().fname
    dir = parser.parse_args().dir
    packets = int(parser.parse_args().packets)
    verbose = bool(parser.parse_args().verbose)
    start = int(parser.parse_args().start)

    file = CodifFile(dir + fname)
    file.seek_packet(start, offset=DADA_HEADER_SIZE)
    file.read(packets, validate=True, verbose=verbose, skip_payload=False)
    # file.faulty_packets2json("test")
