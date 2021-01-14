'''
Institution: Max-Planck Institution for Radioastronomy (MPIfR-Bonn)
    Auf dem Huegel 69, Bonn, Germany

Author: Niclas Eesser <nesser@mpifr-bonn.mpg.de>

Description
-----------
    This script reads and plots Array Covariance Matrices (ACMs).
    The input file(s) must be in HDF5 and must match the structure specified/declared
    by CSIRO to successfully read out ACM data. (More detailed information of the structure
    can be seen in the module 'inc/acm_hdf5.py' or by using common HDF5 tools)
Program flow
------------
    0. Parse user arguments
    1. Iterate and read every file in file list
    2. Extract acm data and frequency information from each file
    3. Plot each ACM
'''
# Included modules
import argparse
import numpy as np
from argparse import RawTextHelpFormatter

# Custom modules
from inc.acm_hdf5 import *
from inc.utils import *

if __name__ == '__main__':
    ##############################
    # Start of arguments parsing #
    ##############################
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fname', '-f', action = "store", default = "", dest = "fname", help = "Filename of ACM file. If this argument is not passed the script searches all files that matches the SBID argument.")
    parser.add_argument('--dir', '-d', action="store", default="/media/scratch/nesser/acm_data/", dest = "dir", help = "Directory of ACM file.")
    parser.add_argument('--output', '-o', action="store", default="", dest="odir", help="If passed plots are stored in the passed location.")
    parser.add_argument('--sbid', '-i', action="store", dest="sbid", help="Scan ID")
    parser.add_argument('--subsbid', '-sub', action="store", default="-1", dest="subid", help="Subscan ID")
    parser.add_argument('--band', '-b', action = "store", dest="band", help="The frequency range to plot from low to highest (e.g. 1307-1350). If not passed the whole recorded band ist plotted")
    parser.add_argument('--low_freq', '-l', action = "store", dest="low_freq", default=1148, help="The frequency range to plot from low to highest (e.g. 1307-1350). If not passed the whole recorded band ist plotted")
    parser.add_argument('--element_list', '-e', action="store", dest="element_list", default=1, help="Allows to plot only certain antenna elements (e.g. 15,16,17,18,25,26). By default only the elements used in PAF snapshots wil be plotted. To plot all elements value has to be set to 0")
    # Assign arguments to variables for readability
    fname = parser.parse_args().fname
    dir = check_slash(parser.parse_args().dir) # Appends a slash to the end of dir, if not passed
    odir = check_slash(parser.parse_args().odir) # Appends a slash to the end of dir, if not passed
    sbid = parser.parse_args().sbid
    subid = parser.parse_args().subid
    low_freq = parser.parse_args().low_freq
    band = parser.parse_args().band
    element_list = parser.parse_args().element_list
    # Parse the desired band
    if band:
        freq = np.arange(float(band.split("-")[0]), float(band.split("-")[1]))
    else:
        freq = np.arange(low_freq, low_freq + PAF_BANDWIDTH)
    # If file name was passed, get all files that matches
    if fname != "":
        files = get_file_list(dir, fname)
    # Just collect files with the correct subscan id
    elif subid != '-1':
        subid = subid.split(",")
        for i in subid:
            fname = "SB0" + str(sbid) + "-" + str(i).zfill(3) + "*.pk01.acm.hdf5"
            files.append(get_file_list(dir, fname)[0])
    # if subsbid is not passed we assume to read out every file that matches the main scan id (sbid)
    else:
        fname = "SB0" + str(sbid) + "*.hdf5"
        files = get_file_list(dir, fname)
    if files == []:
        print("No files found, aborting ...")
        sys.exit()
    ##############################
    #  End of arguments parsing  #
    ##############################

    # 1. Iterate and read all files
    for f in files:
        data = np.zeros((len(freq), N_ELEMENTS, N_ELEMENTS), dtype=np.complex64)
        print("Reading "+f+" ... ")
        acm_file = ACMFile(f, count_scale=False)
        freq_dict = acm_file.make_freq_ind_dict()
        acm_data = np.asarray(acm_file["ACMdata"], dtype=np.complex64)
        # 2. Extract data
        for (key, value) in (freq_dict.items()):
            data[np.argwhere(freq==key)] = acm_data[value[0], value[1]]
        # 3. Plot data (maximum of 8 ACMs within a diagramm)
        i = 0
        while i < len(freq):
            if element_list == 1:
                plot_acm(data[i:i+8], freq[i:i+8], dir=odir, element_list=ELEMENT_LIST)
            elif isinstance(element_list, str):
                plot_acm(data[i:i+8], freq[i:i+8], dir=odir, element_list=element_list.split(','))
            else:
                plot_acm(data[i:i+8], freq[i:i+8], dir=odir)
            i += 8
