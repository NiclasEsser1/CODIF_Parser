import argparse
import glob
import numpy as np
from argparse import RawTextHelpFormatter

from inc.acm_hdf5 import *
from inc.utils import *


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--dir', '-d', action = "store", default = "/media/scratch/nesser/acm_data/", dest = "dir", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--output', '-o', action = "store", default = "/media/scratch/nesser/acm_data/plots", dest = "odir", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--sbid', '-i', action = "store", default=1217, dest="sbid")
    parser.add_argument('--subsbid', '-sub', action = "store", default="-1", dest="subsbid")

    dir = check_slash(parser.parse_args().dir) # Appends a slash to the end of dir, if not passed
    odir = check_slash(parser.parse_args().odir) # Appends a slash to the end of dir, if not passed
    sbid = int(parser.parse_args().sbid)
    subid = parser.parse_args().subsbid

    # Initial variables
    acm_files = []
    files = []



    # if subsbid is not passed we assume to read out every file that matches the main scan id (sbid)
    if subid == "-1":
        fname = "SB0" + str(1217) + "*.pk01.acm.hdf5"
        files = get_file_list(dir, fname)
    else:
        subid = subid.split(",")
        for i in subid:
            fname = "SB0" + str(1217) + "-" + str(i).zfill(3) + "*.pk01.acm.hdf5"
            files.append(get_file_list(dir, fname)[0])

    for f in files:
        acm_files.append(ACMFile(f))
        freq = acm_files[-1].make_freq_ind_dict().keys()
        data = acm_files[-1]["ACMdata"][0].astype(dtype='complex')
        i = 0
        while i < len(freq):
            plot_acm(data[i:i+8], freq[i:i+8], dir=odir)
            i += 8
