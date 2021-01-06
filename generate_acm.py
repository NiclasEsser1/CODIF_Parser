import argparse
import glob
import numpy as np
from argparse import RawTextHelpFormatter

from inc.codif import *
from inc.utils import *


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fname', '-f', action = "store", default = "*", dest = "fname", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--dir', '-d', action = "store", default = "/beegfsEDD/NESSER/PAF-12-2020/2020-12-09/2020-12-09-15:57:51/numa14/", dest = "dir", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--nelements', '-n', action = "store", default=36, dest="nelements")

    fname = parser.parse_args().fname
    dir = parser.parse_args().dir
    nelements = int(parser.parse_args().nelements)

    files = get_file_list(dir, fname)
    handler = CodifHandler(files)
    acm_x, acm_y = handler.compute_acm(nelements)
    for i in range(7):
        # acm_x = np.loadtxt("results/acm_x_chan"+str(i)+".txt", dtype="complex")
        # acm_y = np.loadtxt("results/acm_x_chan"+str(i)+".txt", dtype="complex")
        np.savetxt("results/acm_x_chan"+str(i)+".txt", acm_x[i])
        np.savetxt("results/acm_y_chan"+str(i)+".txt", acm_y[i])
        handler.plot_acm(abs(acm_x[i]))
        handler.plot_acm(abs(acm_y[i]))
