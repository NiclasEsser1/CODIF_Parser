'''
Institution: Max-Planck Institution for Radioastronomy (MPIfR-Bonn)
    Auf dem Huegel 69, Bonn, Germany

Author: Niclas Eesser <nesser@mpifr-bonn.mpg.de>

Description
-----------
    This script validates data of a whole snapshots by reading CODIF meta data.
    It basically proofs the correct order of received packets. Due to a UDP based
    communication packet loss may occur. Packets that are missing are recorded as
    faulty packets. Also so-called zero packets occur, which has no data in it, but
    were still recorded and written to disk.

Preliminaries
-------------
    The script expects a predefined folder structure in which the raw data are stored:
    root_dir/
    |_______numa0/
    |        |______raw_file1.dada
    |        |______raw_file2.dada
    :        :
    |        |______raw_fileN.dada
    |_______numa1/
    |        |______raw_file1.dada
    |        |______raw_file2.dada
    :        :
    |        |______raw_fileN.dada
    :
    |_______numaN/
             |______raw_file1.dada
             |______raw_file2.dada
             :
             |______raw_fileN.dada
    All files within the folder structure are automatically searched, but it is important
    that sub-folders have the name 'numa' + ID
Program flow
------------
    0. Parse user arguments
    1. Create a CodifHandle object with all detected files
    2. Validates all deteced files and monitors the progress. (Validating recorded data of snapshots with 1TB size takes a while)
    3. Save result to a csv file
'''
import argparse
import os
import re
from argparse import RawTextHelpFormatter

from inc.codif import *


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fname', '-f', action = "store", default = "2020-12-03-22:48:30", dest = "fname", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--dir', '-d', action = "store", default = "/beegfsEDD/NESSER/", dest = "dir", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--packets', '-p', action = "store", default=-1, dest = "packets", help = "Packets to read from .dada file")
    parser.add_argument('--threads', '-t', action = "store", default=2, dest = "threads", help = "Packets to read from .dada file")
    parser.add_argument('--output', '-o', action = "store", default= "2020-12-03-22:48:30.csv", dest = "output", help = "Packets to read from .dada file")

    fname = parser.parse_args().fname
    dir = parser.parse_args().dir
    packets = int(parser.parse_args().packets)
    threads = int(parser.parse_args().threads)
    output = parser.parse_args().output

    file_list = []
    fname_list = []

    for root, dirs, files in os.walk(dir):
        for file in files:
            if fname in file:
                file_list.append(os.path.join(root, file))

    file_list.sort(key=splitter)
    handler = CodifHandler(file_list)
    handler.validate(packets, threads=threads, display="node")
    handler.to_csv("results/", output)
