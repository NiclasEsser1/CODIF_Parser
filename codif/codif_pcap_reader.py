#!/usr/local/bin/python2.7

import inc.codif_base *
import json
import argparse
from argparse import RawTextHelpFormatter

def format_mac_address(mac_string):
    return ':'.join('%02x' % b for b in bytearray(mac_string))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='options', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--fname', '-f', action = "store", default = "", dest = "fname", help = "Input file name with directory of type '.pcap'")
    parser.add_argument('--outputfile', '-o', action = "store", default = "", dest = "oname", help = "Output file name in which to write the parsed .pcap file")

    fname = parser.parse_args().fname
    output = parser.parse_args().oname

    reader = CodifReadPcap(fname)
    writer = open(output, 'w')
    i = 0
    reader.next()
    reader.add()
    # json.dumps(reader.packet_list[0].header["codif"], indent=4)
    # ref_epoch = reader.packet_list[0].header["codif"]["word1"]["epoch_start_sec"]
    while(reader.next()):
        reader.add()
        # i+=1
        # reader.add()
        # writer.write("\n\n-----------\nPacket #" + str(i) + "\n-----------\n")
        # if ref_epoch != reader.packet_list[i].header["codif"]["word0"]["epoch_start_sec"]:
        #     print("Old ref epoch: " + str(ref_epoch) )
        #     ref_epoch = reader.packet_list[i].header["codif"]["word1"]["epoch_start_sec"]
        #     print("New ref epoch detected: " + str(ref_epoch) )
        #     print("Setting to new epoch ref")
        #     print("Last dataframe of old ref epoch: " + str(reader.packet_list[i-1].header["codif"]["word1"]["frame_number"]) )
        json.dump(reader.packet.header["codif"], writer, indent=4)
