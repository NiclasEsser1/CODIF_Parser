import argparse
import glob
import numpy as np
from argparse import RawTextHelpFormatter

from inc.codif import *
from inc.utils import *


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--dir', '-d', action = "store", default = "/beegfsEDD/NESSER/PAF-12-2020/2020-12-09/2020-12-09-15:57:51/", dest = "dir", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--output_dir', '-o', action = "store", default="", dest="odir")
    parser.add_argument('--numa_id', '-i', action = "store", dest="id")
    parser.add_argument('--freq', '-f', action = "store", default=1284, dest="sfreq")

    dir = parser.parse_args().dir
    odir = parser.parse_args().odir
    id = int(parser.parse_args().id)
    sfreq = int(parser.parse_args().sfreq)

    dir = check_slash(dir)
    if "numa" not in dir:
        dir += "numa" + str(id) + "/"
    files = get_file_list(dir)

    if odir != "":
        odir = check_slash(odir)
        create_dir(odir)

    acm = np.zeros((7,72,72),dtype="complex")
    freq = np.arange(sfreq, sfreq+7)

    print(freq)
    for fidx, f in enumerate(files):
        acm[fidx] = np.loadtxt(f,dtype="complex")
    plot_acm(acm, freq, dir=odir)
