from inc.codif_base import cd
import json
import argparse
from argparse import RawTextHelpFormatter
import numpy as np
import os
import glob

def getFileNames(folderName, sb) :
   glob_key        = "{:s}/SB{:05d}-*.pk01.acm.hdf5".format(folderName, sb)
   return sorted(glob.glob(os.path.join("", glob_key) ) )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fin', '-i', action = "store", default = "", dest = "fin", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--dir', '-d', action = "store", default = "", dest = "dir", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--fout', '-o', action = "store", default = "", dest = "fout", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--chunk', '-c', action = "store", default=-1, dest = "chunk", help = "Packets to read from .dada file")

    fin = parser.parse_args().fin
    fout = parser.parse_args().fout
    directory = parser.parse_args().dir
    chunk = int(parser.parse_args().chunk)

    file_list = cd.get_file_list(directory, fin)

    # Iterate through all files with the same ID
    for file in file_list:
        handler = CodifAndDada(file, fout)
        size = os.path.getsize(file)
        while bytes > 0:
            handler.read(chunk, remove=True)
            handler.write(chunk)
            bytes -= chunk*PACKET_SIZE
