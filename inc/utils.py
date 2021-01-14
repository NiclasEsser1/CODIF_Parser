# Imported modules
import os
import glob
import re
import numpy as np
import matplotlib.pyplot as plt
# Custom modules
from inc.constants import *

def format_mac_address(mac_string):
    return ':'.join('%02x' % b for b in bytearray(mac_string))

def get_file_list(dir, fname_expr="*"):
    check_slash(dir)
    key_expr = dir + fname_expr
    return sorted(glob.glob(os.path.join("", key_expr)))

def empty_string(bytes):
    rpay = ""
    for i in range(bytes):
        rpay += " "
    return rpay
def splitter(s):
    return re.split('\_|\.', s)[1]

def check_slash(dir):
    if dir[-1] != "/":
        dir += "/"
    return dir

def check_dir(dir):
    if not os.path.isdir(dir):
        confirm = raw_input("Directory '" + dir + "' not exists, create it? (y/n)")
        if confirm == 'y':
            try:
                os.mkdir(dir)
            except:
                print("Dircetory already created")
        else:
            sys.exit(0)

def plot_acm(acm, freq, timestamp=0, yaxis=2, dir="", element_list=[]):
    nchannel = len(freq)
    if nchannel%2:
        nplotx = int(np.floor((nchannel+1)/yaxis))
    else:
        nplotx = int(np.floor(nchannel/yaxis))

    plt.rcParams['figure.figsize'] = [len(freq)*2, 6]
    fig, sub = plt.subplots(yaxis, nplotx)
    fig.suptitle("ACM - Array Covariance Matrices\n"
        + " Channels: "
        + str(freq[0])
        + " - "
        + str(freq[-1])
        + " MHz")
    for idx, f in enumerate(freq):
        sub[int(idx/nplotx), int(idx%nplotx)].set_title("Channel: "+str(freq[idx]))
        if element_list != []:
            acm_new = np.zeros((len(freq), len(element_list), len(element_list)),dtype='complex')
            for eidx, e in enumerate(element_list):
                acm_new[idx, eidx] = acm[idx, e, element_list]
            sub[int(idx/nplotx), int(idx%nplotx)].imshow(20*np.log10(abs(acm_new[idx])/np.max(abs(acm_new[idx]))))
        else:
            sub[int(idx/nplotx), int(idx%nplotx)].imshow(20*np.log10(abs(acm[idx])/np.max(abs(acm[idx]))))
    if dir != "":
        check_dir(dir)
        plt.savefig(dir + "acm_" + str(freq[0]) + "_" + str(freq[-1]) + "mhz.png")
        print("Saved results: " + dir)
    plt.show()

def select_from_list(data, element_list):
    dim1 = data.shape[0]
    selected_data = np.zeros((dim1, len(element_list), len(element_list)),dtype=type(data))
    for idx in range(dim1):
        for eidx, e in enumerate(element_list):
            selected_data[idx, eidx] = data[idx, e, element_list]
    return selected_data


def fillup_acm(acm, element_list, freq_list, start=1148):
    filled = np.zeros((1+CODIF_CHANNELS_IN_BLOCK,PAF_N_FREQ_GROUP, N_ELEMENTS, N_ELEMENTS), dtype='complex')
    sky_freq = np.zeros((1+CODIF_CHANNELS_IN_BLOCK,PAF_N_FREQ_GROUP))
    for idx in range(1+CODIF_CHANNELS_IN_BLOCK):
        sky_freq[idx] = np.arange(start + idx, start + PAF_BANDWIDTH, 8)
    for freq in freq_list:
        for row in range(N_ELEMENTS):
            if row in element_list:
                for col in range(N_ELEMENTS):
                    if col in element_list:
                        x = np.nonzero(np.asarray(element_list) == row)
                        y = np.nonzero(np.asarray(element_list) == col)
                        z = np.nonzero(freq_list == freq)
                        pos = np.argwhere(sky_freq == float(freq))
                        filled[pos[0,0], pos[0,1], row, col] += acm[z,x,y].reshape(1)[0]
    return filled
