import os
import glob
import re

def format_mac_address(mac_string):
    return ':'.join('%02x' % b for b in bytearray(mac_string))

def get_file_list(directory, fname_expr):
    if directory[-1] != "/":
        directory += "/"
    key_expr = directory + fname_expr
    return sorted(glob.glob(os.path.join("", key_expr)))

def gen_payload(bytes):
    rpay = ""
    for i in range(bytes):
        rpay += " "
    return rpay
def splitter(s):
    print(re.split('\_|\.', s)[1])
    return re.split('\_|\.', s)[1]
