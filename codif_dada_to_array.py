import argparse
import os
from argparse import RawTextHelpFormatter

from inc import utils
from inc import protocols as proto


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fin', '-i', action = "store", default = "", dest = "fin", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--dir', '-d', action = "store", default = "", dest = "dir", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--fout', '-o', action = "store", default = "", dest = "fout", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--chunk', '-c', action = "store", default=-1, dest = "chunk", help = "Packets to read from .dada file")

    fin = parser.parse_args().fin
    fout = parser.parse_args().fout
    directory = parser.parse_args().dir

    file_list = utils.get_file_list(directory, fin)

    # Iterate through all files with the same identifier
    for file in file_list:
        handler = proto.CodifFile(file, fout)
        size = os.path.getsize(file)
        while bytes > 0:
            handler.read(chunk, True, True)
            handler.write()
            bytes -= chunk*PACKET_SIZE
