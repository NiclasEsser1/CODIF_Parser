#!/usr/local/bin/python2.7

from inc.codif_base import *
import json
import argparse
from argparse import RawTextHelpFormatter


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fname', '-f', action = "store", default = "", dest = "fname", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--packets', '-p', action = "store", default=-1, dest = "packets", help = "Packets to read from .dada file")
    parser.add_argument('--validate', '-v', action = "store", default=False, dest = "validate", help = "Validate if all packets in .dada file are in list")

    fname = parser.parse_args().fname
    packets = int(parser.parse_args().packets)
    validate = bool(parser.parse_args().validate)

    reader = CodifAndDada(fname)
    reader.read(packets, validate)
