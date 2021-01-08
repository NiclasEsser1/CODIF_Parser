import argparse
import glob
import numpy as np
from argparse import RawTextHelpFormatter

from inc.codif import *
from inc.utils import *


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fname', '-f', action = "store", default = "*", dest = "fname", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--dir', '-d', action = "store", default = "/beegfsEDD/NESSER/PAF-12-2020/2020-12-09/2020-12-09-15:57:51/", dest = "dir", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--nelements', '-n', action = "store", default=36, dest="nelements")
    parser.add_argument('--output_dir', '-o', action = "store", default="", dest="odir")
    parser.add_argument('--numa_id', '-i', action = "store", dest="oname")

    fname = parser.parse_args().fname
    dir = parser.parse_args().dir
    id = parser.parse_args().oname
    nelements = int(parser.parse_args().nelements)
    odir = parser.parse_args().odir

    dir = check_slash(dir)
    if "numa" not in dir:
        dir += "numa" + str(id) + "/"
        
    files = get_file_list(dir, fname + "*")

    if files == []:
        print("No files found, gets aborted")
        sys.exit(0)

    handler = CodifHandler(files)
    acm, freq = handler.compute_acm(nelements)

    if odir != "":
        odir = check_slash(odir)
        create_dir(odir)
        create_dir(odir + "numa" + str(id))
        for fidx, f in enumerate(freq):
            np.savetxt(odir + "numa" + str(id) + "/acm_" + str(f) + " _mhz.txt", acm[fidx])
    plot_acm(acm, freq, dir=odir)
