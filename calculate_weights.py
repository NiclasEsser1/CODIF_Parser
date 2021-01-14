'''
Institution: Max-Planck Institution for Radioastronomy (MPIfR-Bonn)
    Auf dem Huegel 69, Bonn, Germany

Author: Niclas Eesser <nesser@mpifr-bonn.mpg.de>

Description
-----------
Program flow
------------
'''
# Included modules
import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from argparse import RawTextHelpFormatter

# Custom modules
from inc.acm_hdf5 import *
from inc.utils import *

sources = {
    'CASA'    : {'A' :  3.3584, 'B' : -0.7518, 'C' : -0.0347, 'D' : -0.0705},
    'CYGA'    : {'A' :  3.3498, 'B' : -1.0022, 'C' : -0.2246, 'D' :  0.0227, 'E' :  0.0425},
    'TAUA'    : {'A' :  2.9516, 'B' : -0.2173, 'C' : -0.0473, 'D' : -0.0674},
    'HYDRAA'  : {'A' :  1.7795, 'B' : -0.9176, 'C' : -0.0843, 'D' : -0.0139, 'E' :  0.0295},
    'VIRGOA'  : {'A' :  2.4466, 'B' : -0.8116, 'C' : -0.0483},
    '3C147'   : {'A' :  1.4516, 'B' : -0.6961, 'C' : -0.2007, 'D' :  0.0640, 'E' : -0.0464, 'F' :  0.0289},
    '3C196'   : {'A' :  1.2872, 'B' : -0.8530, 'C' : -0.1534, 'D' : -0.0200, 'E' :  0.0201},
    '3C286'   : {'A' :  1.2481, 'B' : -0.4507, 'C' : -0.1798, 'D' :  0.0357},
    '3C295'   : {'A' :  1.4701, 'B' : -0.7658, 'C' : -0.2780, 'D' : -0.0347, 'E' :  0.0399},
}

def flux_model(freq, source="3C295") :
    """
    check if source is in the internal 'cataog' or use a default source
    set nominal source flux and source name

    Flux data taken from
        An Accurate Flux Density Scale from 50MHz to 50GHz; R.A. Perley and B.J. Butler; DOI:10.384771538-4365/AA6DF9 / table 6 / page 5
    """
    model = sources[source.upper()]
    flux = []
    for f in freq:
        f /= 1000.
        flux.append(10.**( model.get('A', 0.)
            + model.get('B', 0.) *  np.log10(f)
            + model.get('C', 0.) * (np.log10(f)**2)
            + model.get('D', 0.) * (np.log10(f)**3)
            + model.get('E', 0.) * (np.log10(f)**4)
            + model.get('F', 0.) * (np.log10(f)**5) ) * 1E-26
        )
    return flux

def calc_y_factor(weights, acm_on, acm_off=[]):
    channels = acm_on.shape[0]
    elements = acm_on.shape[1]
    y_fac = np.zeros(channels)
    for fidx in range(channels):
        w = weights[fidx]
        if acm_off != []:   # true y-factors (Signal to Noise ratio + 1)
            y_fac[fidx] = np.abs( np.dot(np.dot(w.conj(), acm_on[fidx]), w) / np.dot(np.dot(w.conj(), acm_off[fidx]), w) )
        else:    # or just the signal response
            y_fac[fidx] = np.abs( np.dot(np.dot(w.conj(), acm_on[fidx]), w))
    return y_fac

def calc_t_sys(y_factor, flux):
    A = np.pi*50.**2
    k_boltz = 1.38064852E-23  # J/K
    channels = y_factor.shape[0]
    t_sys = np.zeros(channels)
    for fidx in range(channels):
        t_sys[fidx] = 0.5 * A * flux[fidx] / (k_boltz * y_factor[fidx])
    return t_sys

def max_snr(acm_off, acm_on):
    channels = acm_off.shape[0]
    elements = acm_off.shape[1]
    print(elements)
    acm_sn = np.zeros((channels, elements, elements), dtype='complex')
    weights = np.zeros((channels, elements), dtype='complex')
    for fidx in range(channels):
        acm_sn[fidx] = np.dot(np.linalg.inv(acm_off[fidx]), acm_on[fidx])
        eig_val, eig_vec = np.linalg.eig(acm_sn[fidx])
        w1 = np.zeros((elements, len(eig_val)), dtype='complex')
        w1[np.ix_(range(0, elements), range(0, len(eig_val)))] = eig_vec[:,range(0, len(eig_val))]
        idx_sorted = np.argsort(np.abs(eig_val))[::-1]
        idx1 = idx_sorted[0]
        if len(idx_sorted) > 1:
            idx2 = idx_sorted[1]
        else:
            idx2 = 0
        if np.argmax(w1[:,idx1].flatten()) in ELEMENT_LIST:
            help = idx2
            idx2 = idx1
            idx1 = help
        weights[fidx] = w1[:, idx1].flatten()
    return weights

if __name__ == '__main__':
    ##############################
    # Start of arguments parsing #
    ##############################
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fname', '-f', action = "store", default = "", dest = "fname", help = "Filename of ACM file. If this argument is not passed the script searches all files that matches the SBID argument.")
    parser.add_argument('--dir', '-d', action="store", default="/media/scratch/nesser/acm_data/", dest = "dir", help = "Directory of ACM file.")
    parser.add_argument('--output', '-o', action="store", default="/media/scratch/nesser/acm_data/", dest="odir", help="If passed plots are stored in the passed location.")
    parser.add_argument('--sbid', '-i', action="store", dest="sbid", help="Scan ID")
    parser.add_argument('--subsbid', '-sub', action="store", default="-1", dest="subid", help="Subscan ID")
    parser.add_argument('--band', '-b', action = "store", dest="band", help="The frequency range to plot from low to highest (e.g. 1307-1350). If not passed the whole recorded band ist plotted")
    parser.add_argument('--element_list', '-e', action="store", dest="element_list", default=1, help="Allows to plot only certain antenna elements (e.g. 15,16,17,18,25,26). By default only the elements used in PAF snapshots wil be plotted. To plot all elements value has to be set to 0")
    # Assign arguments to variables for readability
    fname = parser.parse_args().fname
    dir = check_slash(parser.parse_args().dir) # Appends a slash to the end of dir, if not passed
    odir = check_slash(parser.parse_args().odir) # Appends a slash to the end of dir, if not passed
    sbid = parser.parse_args().sbid
    subid = parser.parse_args().subid
    band = parser.parse_args().band
    element_list = parser.parse_args().element_list
    # Parse the desired band
    if band:
        freq = np.arange(float(band.split("-")[0]), float(band.split("-")[1]))
    else:
        freq = [0 for __ in range(PAF_BANDWIDTH)]
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
        print("Reading "+f+" ... ")

        acm_file = ACMFile(f, count_scale=False)
        if '-000.' in f:
            acm_noise = acm_file.reshape_to_3d()
        else:
            acm_source = acm_file.reshape_to_3d()
    channels = acm_noise.shape[0]
    ele_pol = len(ELEMENT_LIST)/2

    # Calcuation
    weights_x = max_snr(acm_noise[:, 0:ele_pol, 0:ele_pol], acm_source[:, 0:ele_pol, 0:ele_pol])
    weights_y = max_snr(acm_noise[:, ele_pol:2*ele_pol, ele_pol:2*ele_pol], acm_source[:, ele_pol:2*ele_pol, ele_pol:2*ele_pol])
    weights_xy = max_snr(acm_noise, acm_source)


    flux = flux_model(freq, "3C295")

    y_factor_x = calc_y_factor(weights_x, acm_source[:, 0:ele_pol, 0:ele_pol])#, acm_noise[:, 0:ele_pol, 0:ele_pol],)
    t_sys_x = calc_t_sys(y_factor_x, flux)

    y_factor_y = calc_y_factor(weights_y, acm_source[:, ele_pol:2*ele_pol, ele_pol:2*ele_pol])#, acm_noise[:, ele_pol:2*ele_pol, ele_pol:2*ele_pol])
    t_sys_y = calc_t_sys(y_factor_y, flux)

    y_factor_xy = calc_y_factor(weights_xy, acm_source)#, acm_noise)
    t_sys_xy = calc_t_sys(y_factor_xy, flux)

    #############
    # Plots     #
    #############
    fig, sub = plt.subplots(2, 3, figsize=(14,6))

    sub[0, 0].set_title("X-pol weights")
    sub[0, 0].set_xlabel("Elements")
    sub[0, 0].set_ylabel("Frequency [MHz]")
    sub[0, 0].set_yticks([0,45, 90])
    sub[0, 0].set_yticklabels((freq[0], freq[45], freq[-1]))

    sub[1, 0].set_title("Y-Factor X-pol")
    sub[1, 0].set_ylabel("T sys")
    sub[1, 0].set_xlabel("Channels")

    sub[0, 1].set_title("Y-pol weights")
    sub[0, 1].set_yticks([0,45, 90])
    sub[0, 1].set_xlabel("Elements")
    sub[0, 1].set_ylabel("Frequency [MHz]")
    sub[0, 1].set_yticklabels((freq[0], freq[45], freq[-1]))

    sub[1, 1].set_title("Y-Factor Y-pol")
    sub[1, 1].set_ylabel("T sys")
    sub[1, 1].set_xlabel("Channels")

    sub[0, 2].set_title("XY-pol weights")
    sub[0, 2].set_yticks([0,45, 90])
    sub[0, 2].set_xlabel("Elements")
    sub[0, 2].set_ylabel("Frequency [MHz]")
    sub[0, 2].set_yticklabels((freq[0], freq[45], freq[-1]))

    sub[1, 2].set_title("Y-Factor XY-pol")
    sub[1, 2].set_ylabel("T sys")
    sub[1, 2].set_xlabel("Channels")

    sub[0, 0].imshow(np.abs(weights_x))
    sub[0, 1].imshow(np.abs(weights_y))
    sub[0, 2].imshow(np.abs(weights_xy))
    sub[1, 0].plot(t_sys_x)
    sub[1, 1].plot(t_sys_y)
    sub[1, 2].plot(t_sys_xy)
    plt.tight_layout()
    plt.show()


    # print(y)
        # acm_data = np.asarray(acm_file["ACMdata"], dtype='complex')
