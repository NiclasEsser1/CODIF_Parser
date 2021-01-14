#!/usr/local/bin/python2.7

import json
import argparse
import os
from argparse import RawTextHelpFormatter

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fname', '-f', action = "store", default = "log", dest = "fname", help = "Input file name with directory (filetype '.dada')")
    parser.add_argument('--time', '-t', action = "store", default = "15:58,16:03,16:10,16:15,", dest = "time", help = "Input file name with directory (filetype '.dada')")

    fname = parser.parse_args().fname
    time = parser.parse_args().time.split(',')


    with open(fname) as input:
        lines = input.readlines()

    for t in time:
        with open(fname.split('.')[0]+'_'+t+".log", 'w') as output:
            for line in lines:
                if t in line:
                    output.writelines(line)
