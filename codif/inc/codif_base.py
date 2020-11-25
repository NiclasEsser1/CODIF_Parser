import struct
import pcapy
import socket
import io
import json
import argparse
import numpy as np

# Constants
ETHII_HEADER_BYTES = 14
IPV4_HEADER_BYTES = 20
UDP_HEADER_BYTES = 8
CODIF_HEADER_BYTES = 64
TOTAL_HEADER_BYTES =  ETHII_HEADER_BYTES + IPV4_HEADER_BYTES + UDP_HEADER_BYTES + CODIF_HEADER_BYTES
CODIF_PAYLOAD_BYTES = 7168
PACKET_SIZE = CODIF_PAYLOAD_BYTES + CODIF_HEADER_BYTES
TOTAL_PACKET_SIZE = TOTAL_HEADER_BYTES + CODIF_PAYLOAD_BYTES
BLOCKS_IN_PACKET = 128
CHANNELS_IN_BLOCK = 7
POLARIZATION = 2


def format_mac_address(mac_string):
    return ':'.join('%02x' % b for b in bytearray(mac_string))

class CodifReadPcap:
    def __init__(self, fname):
        self.fname = fname
        try:
            self.reader = pcapy.open_offline(self.fname)
        except IOError as e:
            raise e
        self.packet_list = []
        self.packet = 0

    def set_bpf_filter(self, filter):
        self.reader.setfilter(filter)
    def next(self):
        frame = self.reader.next()[1]
        if(frame):
            self.packet = CodifPacket(io.BytesIO(frame))
            return True
        else:
            return False

    def add(self):
        self.packet_list.append(self.packet)

class CodifReadDada:
    def __init__(self, fname):
        self.fname = fname
        try:
            self.reader = open(self.fname, "rb")
        except IOError as e:
            raise e
        self.packet_list = []
        self.packet = 0
    def next(self):
        frame = self.reader.read(PACKET_SIZE)
        print(frame)
        if(len(frame) == PACKET_SIZE):
            self.packet = CodifPacket(io.BytesIO(frame))
            return True
        else:
            print("Could not read packet")
            return False

    def add(self):
        self.packet_list.append(self.packet)

    def read_bytes(self, bytes):
        while(bytes > 0):
            if(self.next()):
                print(packet.header["codif"], "\n")
                self.add()
            else:
                print("Could not parse packet")
            bytes = bytes - PACKET_SIZE
            print(bytes)

    def read_all(self):
        print("Not implemented")

    def proof_order(self):
        ref_packet = packet_list.at(0)
        if(len(packet_list) > ref_packet.period):
            print("Proofing order")
        else:
            print("Not full period read")

class CodifPacket:
    def __init__(self, bytestream):
        self.stream = bytestream
        self.header = Header(self.stream).header
        self.payload = Payload(self.stream, self.header)

class Header:
    def __init__(self, stream):
        self.header = {"eth" : {}, "ipv4" : {}, "udp" : {}, "codif" : { "word"+str(i) : {} for i in range(0,8)  }}
        self.stream = stream
        # Decide whether or not to parse protocol layer 1-3
        # if stream.getbuffer().nbytes == TOTAL_HEADER_BYTES:
        #     self.parse_eth_hdr()
        #     self.parse_ipv4_hdr()
        #     self.parse_udp_hdr()
        self.parse_codif_hdr()
        # print(json.dumps(self.header, indent=4))

    def parse_eth_hdr(self):
        self.header["eth"]["dest_mac_addr"] = format_mac_address(self.stream.read(6))
        self.header["eth"]["src_mac_addr"] = format_mac_address(self.stream.read(6))
        self.header["eth"]["frame_length"] = struct.unpack("!H",self.stream.read(2))[0]
        self.dest_mac_addr = self.header["eth"]["dest_mac_addr"]
        self.src_mac_addr = self.header["eth"]["src_mac_addr"]
        self.frame_length = self.header["eth"]["frame_length"]

    def parse_ipv4_hdr(self):
        byte = struct.unpack("!b", self.stream.read(1))[0]
        self.header["ipv4"]["ver"] = hex(byte >> 4)
        self.header["ipv4"]["ihl"] = hex(byte & 0x0F)
        self.header["ipv4"]["tos"] = struct.unpack("!b", self.stream.read(1))[0]
        self.header["ipv4"]["total_length"] = struct.unpack("!H",self.stream.read(2))[0]
        self.header["ipv4"]["identification"] = struct.unpack("!H",self.stream.read(2))[0]
        byte = struct.unpack("!H",self.stream.read(2))[0]
        self.header["ipv4"]["flags"] = hex(byte >> 13)
        self.header["ipv4"]["fragment_offset"] = hex(byte << 3)
        self.header["ipv4"]["ttl"] = struct.unpack("!b", self.stream.read(1))[0]
        self.header["ipv4"]["protocol"] = struct.unpack("!b", self.stream.read(1))[0]
        self.header["ipv4"]["check_sum"] = struct.unpack("!H", self.stream.read(2))[0]
        self.header["ipv4"]["src_addr"] = socket.inet_ntoa(self.stream.read(4))
        self.header["ipv4"]["dest_addr"] = socket.inet_ntoa(self.stream.read(4))
        self.ver = self.header["ipv4"]["ver"]
        self.ihl = self.header["ipv4"]["ihl"]
        self.tos = self.header["ipv4"]["tos"]
        self.total_length = self.header["ipv4"]["total_length"]
        self.identification = self.header["ipv4"]["identification"]
        self.flags = self.header["ipv4"]["flags"]
        self.fragment_offset = self.header["ipv4"]["fragment_offset"]
        self.ttl = self.header["ipv4"]["ttl"]
        self.protocol = self.header["ipv4"]["protocol"]
        self.check_sum = self.header["ipv4"]["check_sum"]
        self.src_addr = self.header["ipv4"]["src_addr"]
        self.dest_addr = self.header["ipv4"]["dest_addr"]

    def parse_udp_hdr(self):
        self.header["udp"]["src_port"] = struct.unpack("!H",self.stream.read(2))[0]
        self.header["udp"]["dest_port"] = struct.unpack("!H",self.stream.read(2))[0]
        self.header["udp"]["length"] = struct.unpack("!H",self.stream.read(2))[0]
        self.header["udp"]["check_sum"] = struct.unpack("!H", self.stream.read(2))[0]
        self.src_port = self.header["udp"]["src_port"]
        self.dest_port = self.header["udp"]["dest_port"]
        self.length = self.header["udp"]["length"]
        self.check_sum = self.header["udp"]["check_sum"]

    def parse_codif_hdr(self):
        header = []
        # Read in the entire header (8x8 Bytes or 8 words)
        for i in range(0,8):
            header.append(struct.unpack("!Q", self.stream.read(8))[0])
        self.header["codif"]["word0"]["invalid"] = header[0] >> 63
        self.header["codif"]["word0"]["complex"] = header[0] >> 62
        self.header["codif"]["word0"]["epoch_start_sec"] = header[0] >> 32
        self.header["codif"]["word0"]["frame_number"] = header[0] & 0x00000000FFFFFFFF
        self.header["codif"]["word1"]["version"] = header[1] >> 61
        self.header["codif"]["word1"]["bits_per_sample"] = (header[1] & 0x1F00000000000000) >> 56
        self.header["codif"]["word1"]["array_length"] = (header[1] & 0x00FFFFFF00000000) >> 32
        self.header["codif"]["word1"]["ref_epoch_period"] = (header[1] & 0x00000000FC000000) >> 26
        self.header["codif"]["word1"]["sample_representation"] = (header[1] & 0x0000000003C00000) >> 22
        self.header["codif"]["word1"]["unassigned"] = (header[1] & 0x00000000003F0000) >> 16
        self.header["codif"]["word1"]["station_id"] = header[1] & 0x000000000000FFFF
        self.header["codif"]["word2"]["block_length"] = header[2] >> 48
        self.header["codif"]["word2"]["channels_per_thread"] = (header[2] & 0x0000FFFF00000000) >> 32
        self.header["codif"]["word2"]["thread_id"] = (header[2] & 0x00000000FFFF0000) >> 16
        self.header["codif"]["word2"]["beam_id"] = (header[2] & 0x000000000000FFFF)
        self.header["codif"]["word3"]["reserved16"] = header[3] >> 48
        self.header["codif"]["word3"]["period"] = (header[3] & 0x0000FFFF00000000) >> 32
        self.header["codif"]["word3"]["reserved32"] = (header[3] & 0x00000000FFFFFFFF)
        self.header["codif"]["word4"]["intervals_per_period"] = (header[4] & 0xFFFFFFFFFFFFFFFF)
        self.header["codif"]["word5"]["sync_seq"] = hex(header[5] >> 32)
        self.header["codif"]["word5"]["reserved32"] = (header[5] & 0x00000000FFFFFFFF)
        self.header["codif"]["word6"]["ext_data_version"] = (header[6] >> 56)
        self.header["codif"]["word6"]["ext_user_data"] = (header[6] & 0x0FFFFFFFFFFFFFFF)
        self.header["codif"]["word7"]["ext_user_data"] = (header[7] & 0xFFFFFFFFFFFFFFFF)


        self.invalid = self.header["codif"]["word0"]["invalid"]
        self.complex = self.header["codif"]["word0"]["complex"]
        self.epoch_start_sec = self.header["codif"]["word0"]["epoch_start_sec"]
        self.frame_number = self.header["codif"]["word0"]["frame_number"]
        self.version = self.header["codif"]["word1"]["version"]
        self.bits_per_sample = self.header["codif"]["word1"]["bits_per_sample"]
        self.array_length = self.header["codif"]["word1"]["array_length"]
        self.ref_epoch_period = self.header["codif"]["word1"]["ref_epoch_period"]
        self.sample_representation = self.header["codif"]["word1"]["sample_representation"]
        self.unassigned = self.header["codif"]["word1"]["unassigned"]
        self.station_id = self.header["codif"]["word1"]["station_id"]
        self.block_length = self.header["codif"]["word2"]["block_length"]
        self.channels_per_thread = self.header["codif"]["word2"]["channels_per_thread"]
        self.thread_id = self.header["codif"]["word2"]["thread_id"]
        self.beam_id = self.header["codif"]["word2"]["beam_id"]
        self.reserved16 = self.header["codif"]["word3"]["reserved16"]
        self.period = self.header["codif"]["word3"]["period"]
        self.reserved32 = self.header["codif"]["word3"]["reserved32"]
        self.intervals_per_period = self.header["codif"]["word4"]["intervals_per_period"]
        self.sync_seq = self.header["codif"]["word5"]["sync_seq"]
        self.reserved32 = self.header["codif"]["word5"]["reserved32"]
        self.ext_data_version = self.header["codif"]["word6"]["ext_data_version"]
        self.ext_user_data = self.header["codif"]["word6"]["ext_user_data"]
        self.ext_user_data = self.header["codif"]["word7"]["ext_user_data"]

        return 0





class Payload:
    def __init__(self, stream, header):
        self.stream = stream
        self.header = header
        self.payload = np.zeros((BLOCKS_IN_PACKET, CHANNELS_IN_BLOCK, POLARIZATION), dtype="complex")
        self.read_payload()
        self.beam_id = 0
        self.channels = 0


    def read_payload(self):
        # self.beam_id = struct.unpack("!B", self.stream.read(1))[0]
        # self.channels = struct.unpack("!B", self.stream.read(1))[0]
        # print(self.beam_id, self.channels)
        for block in range(BLOCKS_IN_PACKET):
            for channel in range(CHANNELS_IN_BLOCK):
                for pol in range(POLARIZATION):
                    self.payload[block, channel, pol] = struct.unpack("!H", self.stream.read(2))[0]
                    self.payload[block, channel, pol] += struct.unpack("!H", self.stream.read(2))[0] *1j
