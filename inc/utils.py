import os
import glob
import re

import numpy as np
import matplotlib.pyplot as plt

def format_mac_address(mac_string):
    return ':'.join('%02x' % b for b in bytearray(mac_string))

def get_file_list(dir, fname_expr="*"):
    check_slash(dir)
    key_expr = dir + fname_expr
    return sorted(glob.glob(os.path.join("", key_expr)))

def gen_payload(bytes):
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

def create_dir(dir):
    if not os.path.isdir(dir):
        confirm = raw_input("Directory '" + dir + "' not exists, create it? (y/n)")
        if confirm == 'y':
            try:
                os.mkdir(dir)
            except:
                print("Dircetory already created")
        else:
            sys.exit(0)

def plot_acm(acm, freq, timestamp=0, yaxis=2, dir=""):
    nchannel = len(freq)
    if nchannel%2:
        nplotx = int(np.floor((nchannel+1)/yaxis))
    else:
        nplotx = int(np.floor(nchannel/yaxis))

    plt.rcParams['figure.figsize'] = [len(freq)*2, 6]
    fig, sub = plt.subplots(yaxis, nplotx)
    fig.suptitle("ACM - Array Covariance Matrices\nSnapshot from "
        + str(timestamp)
        + " Channels: "
        + str(freq[0])
        + " - "
        + str(freq[-1])
        + " MHz")
    for idx, f in enumerate(freq):
        sub[int(idx/nplotx), int(idx%nplotx)].set_title("Channel: "+str(freq[idx]))
        sub[int(idx/nplotx), int(idx%nplotx)].imshow(20*np.log10(abs(acm[idx])/np.max(abs(acm[idx]))))
    if dir != "":
        plt.savefig(dir + "acm_" + str(freq[0]) + "_" + str(freq[-1]) + "mhz.png")
        print("Saved results: " + dir)
    plt.show()
