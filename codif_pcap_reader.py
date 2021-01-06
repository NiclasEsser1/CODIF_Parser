import json
import argparse
from argparse import RawTextHelpFormatter
from inc.codif import *

def format_mac_address(mac_string):
    return ':'.join('%02x' % b for b in bytearray(mac_string))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fname', '-f', action = "store", default = "", dest = "fname", help = "Input file name with directory of type '.pcap'")
    parser.add_argument('--outputfile', '-o', action = "store", default = "", dest = "oname", help = "Output file name in which to write the parsed .pcap file")

    fname = parser.parse_args().fname
    output = parser.parse_args().oname

    reader = CodifFile(fname)
    writer = open(output, 'w')

    while(reader.next()):
        reader.add()
        json.dump(reader.packet.header["codif"], writer, indent=4)
