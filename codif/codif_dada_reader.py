#!/usr/local/bin/python2.7

from inc.codif_base import *
import json
import argparse
from argparse import RawTextHelpFormatter


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fname', '-f', action = "store", default = "", dest = "fname", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--packets', '-p', action = "store", default = "", dest = "packets", help = "Packets to read from .dada file")

    fname = parser.parse_args().fname
    packets = parser.parse_args().packets

    reader = CodifReadDada(fname)
    reader.read_bytes(int(packets * PACKET_SIZE))
