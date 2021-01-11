from __future__ import division
import curses
import pcapy
import sys
import struct
import time
import socket
import io
import json
import copy
import re
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from threading import Thread
from Queue import Queue
from copy import deepcopy

from inc.constants import *
from inc.utils import *


"""
 Description:
 ------------
    CODIF packet tool
    CODIF is a UDP based protcol specified by CSIRO

Institution: Max-Planck Institution for Radioastronomy (MPIfR-Bonn)
    Auf dem Huegel 69, Bonn, Germany

Author: Niclas Eesser <nesser@mpifr-bonn.mpg.de>

"""


class HandlerError(Exception):
    pass

class CodifPacket:
    """
    Description:
    ------------
        CodifPacket
    Attributes
    ----------
        header : CodifHeader
            Object that holds all header data
        payload : CodifPayload
            Object that hold the payload ()
        stream : BytesIO
            Bytestream containing the data of one CODIF packet
    Methods
    -------
        None
    """
    def __init__(self, bytestream, skip=False):
        """
        Description:
        ------------
            Constructor of CodifPacket. Initializes header and payload data from
            bytestream.
        Parameters
        ----------
            bytestream : BytesIO
                bytestream that corresponds to one CODIF packet
            skip : bool
                Optional argument to skip reading of payload. Useful if you just
                want to parse header data
        """
        self.stream = bytestream
        self.header = CodifHeader(self.stream) # Instantiate CODIF header
        # Skip payload (Much faster if just header data are required)
        if skip:
            self.payload = 0
        # Or instantiate a payload object
        else:
            self.payload = CodifPayload(self.stream)
    def __str__(self):
        return self.header.__str__()

    def update(self, bytestream, skip=False):
        self.stream = bytestream
        self.header.update(self.stream) # Instantiate CODIF header
        # Skip payload (Much faster if just header data are required)
        if skip:
            self.payload = 0
        # Or instantiate a payload object
        else:
            self.payload.update(self.stream)


class CodifPayload:
    """
    Description:
    ------------
        CodifPayload
    Attributes
    ----------
        stream : BytesIO
            Bytestream containing the data of one CODIF packet
        payload : numpy array
            Numpy array containing raw data of a CODIF packet
    Methods
    -------
        None
    """
    def __init__(self, stream):
        """
        Description:
        ------------
            Constructor of CodifPayload
        Parameters
        ----------
            bytestream : BytesIO
                bytestream that corresponds to one CODIF packet.
        """
        self.stream = stream
        self.comp = np.zeros(
            (CODIF_BLOCKS_IN_PACKET, CODIF_CHANNELS_IN_BLOCK, CODIF_POLARIZATION),
            dtype="complex")
        self.data = np.frombuffer(stream.getvalue()[CODIF_HEADER:], dtype='int16') \
            .reshape(CODIF_BLOCKS_IN_PACKET, CODIF_CHANNELS_IN_BLOCK, CODIF_POLARIZATION, 2) \
            .astype(dtype='float') \
            .view(dtype='complex') \
            .reshape(CODIF_BLOCKS_IN_PACKET, CODIF_CHANNELS_IN_BLOCK, CODIF_POLARIZATION)

    def update(self, stream):
        self.stream = stream
        self.data = np.frombuffer(stream.getvalue()[CODIF_HEADER:], dtype=np.dtype('short').newbyteorder('>')) \
            .reshape(CODIF_BLOCKS_IN_PACKET, CODIF_CHANNELS_IN_BLOCK, CODIF_POLARIZATION*2) \
            .astype(dtype='float') \
            .view(dtype='complex')
            # .reshape(CODIF_BLOCKS_IN_PACKET, CODIF_CHANNELS_IN_BLOCK, CODIF_POLARIZATION)
class CodifHeader:
    """
    Description:
    ------------
        CodifHeader
        This class provides access to the header data of a CodifPacket. An CodifHeader
        object is able to parse the first 4 protocol layers (needed for pcap files).
    Attributes
    ----------
        stream : BytesIO
            Bytestream containing the data of one CODIF packet.
            NOTE: The size of the bystream is used to decide which protocol
            layers are present.
                layer 1-4   bytes == 7274
                layer 2-4   bytes == 7260
                layer 3-4   bytes == 7240
                layer 4     bytes == 7232

        header : Dictionary
            header contains all header data provided by the bytestream.
        nbytes : int
            Size of bytestream used for parsing the header

        Note: Every CODIF attribute is also stored as a class attribute and
        therefore accessable without the use of the generated header dictionary
    Methods
    -------
        update(stream)
            Updates header data by passed bytestreams.

            update_codif_hdr()
                Parses changing values of CODIF header without reading static once.
                Thus this function is much faster than parse_codif_hdr()

        parse()
            Parses the bystream to a dictionary.
            Consists of different inner function (NO ACCESS functions) to parse different protocol layers

            parse_eth_hdr()
                Innerfunction  Parses ethernet protcol header.
            parse_ipv4_hdr()
                Parses ipv4 protocol header.
            parse_udp_hdr()
                Parses udp protocol header.
            parse_codif_hdr()
                Parses codif protocol header.
    """
    def __init__(self, stream):
        """
        Description:
        ------------
            Constructor of CodifHeader
        Parameters
        ----------
            bytestream : BytesIO
                bytestream that corresponds to one CODIF packet.
        """
        self.stream = stream
        self.nbytes = len(stream.getvalue())#getbuffer().nbytes
        self.parse()

    def __str__(self):
        s = "epoch: " + str(self.epoch) + "\n"
        s += "frame_id: " + str(self.frame_id) + "\n"
        s += "ref_epoch_period: " + str(self.ref_epoch_period) + "\n"
        s += "channels_per_thread: " + str(self.channels_per_thread) + "\n"
        s += "freq_group: " + str(self.freq_group) + "\n"
        s += "beam_id: " + str(self.beam_id)
        return s

    def update(self, stream):
        """
        Description:
        ------------
            Updates header data by passed bytestreams. Is essential to update a single packet
            instead of creating new objects when reading large files.
        Parameters
        ----------
            None
        """
        def update_codif_hdr(self):
            """
            Description:
            ------------
                Used for faster parsing of datastream
            Parameters
            ----------
                None
            """
            header = []
            for i in range(0,8):
                header.append(struct.unpack("!Q", self.stream.read(8))[0])
            self.epoch = header[0] >> 32
            self.frame_id = header[0] & 0x00000000FFFFFFFF
            self.beam_id = (header[2] & 0x000000000000FFFF)
            self.freq_group = (header[2] & 0x00000000FFFF0000) >> 16
        self.stream = stream
        self.update_codif_hdr()

    def parse(self):
        """
        Description:
        ------------
            Parses header data from the passed bytestream with the capabilty to parse layers from 1 - 4.
            Depending on the size of the bytestream the different layers are in- or excluded.
            Consists of different inner function to parse different protocol layers.
        Parameters
        ----------
            None
        """
        def parse_eth_hdr(self):
            """
            Description:
            ------------
                Parses ETHERNET header data from the passed bytestream (layer 1)
            Parameters
            ----------
                None
            """

            self.dest_mac_addr = format_mac_address(self.stream.read(6))
            self.src_mac_addr = format_mac_address(self.stream.read(6))
            self.frame_length = struct.unpack("!H",self.stream.read(2))[0]

        def parse_ipv4_hdr(self):
            """
            Description:
            ------------
                Parses IPV4 header data from the passed bytestream (layer 2)
            Parameters
            ----------
                None
            """

            byte = struct.unpack("!b", self.stream.read(1))[0]
            self.ver = hex(byte >> 4)
            self.ihl = hex(byte & 0x0F)
            self.tos = struct.unpack("!b", self.stream.read(1))[0]
            self.total_length = struct.unpack("!H",self.stream.read(2))[0]
            self.identification = struct.unpack("!H",self.stream.read(2))[0]

            byte = struct.unpack("!H",self.stream.read(2))[0]
            self.flags = hex(byte >> 13)
            self.fragment_offset = hex(byte << 3)
            self.ttl = struct.unpack("!b", self.stream.read(1))[0]
            self.protocol = struct.unpack("!b", self.stream.read(1))[0]
            self.check_sum = struct.unpack("!H", self.stream.read(2))[0]
            self.src_addr = socket.inet_ntoa(self.stream.read(4))
            self.dest_addr = socket.inet_ntoa(self.stream.read(4))

        def parse_udp_hdr(self):
            """
            Description:
            ------------
                Parses UDP header data from the passed bytestream (layer 3)
            Parameters
            ----------
                None
            """

            self.src_port = struct.unpack("!H",self.stream.read(2))[0]
            self.dest_port = struct.unpack("!H",self.stream.read(2))[0]
            self.length = struct.unpack("!H",self.stream.read(2))[0]
            self.check_sum = struct.unpack("!H", self.stream.read(2))[0]

        def parse_codif_hdr(self):
            """
            Description:
            ------------
                Parses CODIF header data from the passed bytestream (layer 4)
            Parameters
            ----------
                None
            """
            header = []
            # Read in the entire header (8x8 Bytes or 8 words)
            for i in range(0,8):
                header.append(struct.unpack("!Q", self.stream.read(8))[0])
            self.invalid = header[0] >> 63
            self.complex = header[0] >> 62
            self.epoch = header[0] >> 32
            self.frame_id = header[0] & 0x00000000FFFFFFFF
            self.version = header[1] >> 61
            self.bits_per_sample = (header[1] & 0x1F00000000000000) >> 56
            self.array_length = (header[1] & 0x00FFFFFF00000000) >> 32
            self.ref_epoch_period = (header[1] & 0x00000000FC000000) >> 26
            self.sample_representation = (header[1] & 0x0000000003C00000) >> 22
            self.unassigned = (header[1] & 0x00000000003F0000) >> 16
            self.station_id = header[1] & 0x000000000000FFFF
            self.block_length = header[2] >> 48
            self.channels_per_thread = (header[2] & 0x0000FFFF00000000) >> 32
            self.freq_group = (header[2] & 0x00000000FFFF0000) >> 16
            self.beam_id = (header[2] & 0x000000000000FFFF)
            self.reserved16 = header[3] >> 48
            self.period = (header[3] & 0x0000FFFF00000000) >> 32
            self.reserved32 = (header[3] & 0x00000000FFFFFFFF)
            self.intervals_per_period = (header[4] & 0xFFFFFFFFFFFFFFFF)
            self.sync_seq = hex(header[5] >> 32)
            self.reserved32 = (header[5] & 0x00000000FFFFFFFF)
            self.ext_data_version = (header[6] >> 56)
            self.ext_user_data = (header[6] & 0x0FFFFFFFFFFFFFFF)
            self.ext_user_data = (header[7] & 0xFFFFFFFFFFFFFFFF)

            return 0
        # CODFI layer (=4)
        if self.nbytes == CODIF_PACKET_SIZE:
            self.parse_codif_hdr()
        # UDP layer
        elif self.nbytes == CODIF_TOTAL_SIZE - ETHII_HEADER - IPV4_HEADER:
            self.parse_udp_hdr()
            self.parse_codif_hdr()
        # IPV4 layer
        elif self.nbytes == CODIF_TOTAL_SIZE - ETHII_HEADER:
            self.parse_ipv4_hdr()
            self.parse_udp_hdr()
            self.parse_codif_hdr()
        # ETHII layer
        elif self.nbytes == CODIF_TOTAL_SIZE:
            self.parse_eth_hdr()
            self.parse_ipv4_hdr()
            self.parse_udp_hdr()
            self.parse_codif_hdr()
        else:
            print("Failed to parse CODIF packet with byte size ("
                + str(self.nbytes)
                + "/"
                + str(CODIF_TOTAL_SIZE)
                +")")

    def as_dict(self):

        """
        Description:
        ------------
            Creates a dictionary based on parsed header information
        Parameters:
        ----------
            None
        Return:
        -------
            Returns a dctionary containing header information
        """
        d = {
            "eth" : {},
            "ipv4" : {},
            "udp" : {},
            "codif" : {
                "word"+str(i) : {} for i in range(0,8)
            }
        }

        # ETHII layer
        if self.nbytes == CODIF_TOTAL_SIZE:
            d["eth"]["dest_mac_addr"] = self.dest_mac_addr
            d["eth"]["src_mac_addr"] = self.src_mac_addr
            d["eth"]["frame_length"] = self.frame_length

        # IPV4 layer
        if self.nbytes >= CODIF_TOTAL_SIZE - ETHII_HEADER:
            d["ipv4"]["ver"] = self.ver
            d["ipv4"]["ihl"] = self.ihl
            d["ipv4"]["tos"] = self.tos
            d["ipv4"]["total_length"] = self.total_length
            d["ipv4"]["identification"] = self.identification
            d["ipv4"]["flags"] = self.flags
            d["ipv4"]["fragment_offset"] = self.fragment_offset
            d["ipv4"]["ttl"] = self.ttl
            d["ipv4"]["protocol"] = self.protocol
            d["ipv4"]["check_sum"] = self.check_sum
            d["ipv4"]["src_addr"] = self.src_addr
            d["ipv4"]["dest_addr"] = self.dest_addr

        # UDP layer
        if self.nbytes >= CODIF_TOTAL_SIZE - ETHII_HEADER - IPV4_HEADER:
            d["udp"]["src_port"] = self.src_port
            d["udp"]["dest_port"] = self.dest_port
            d["udp"]["length"] = self.length
            d["udp"]["check_sum"] = self.check_sum

        # CODIF layer
        if self.nbytes >= CODIF_PACKET_SIZE:
            d["codif"]["word0"]["invalid"] = self.invalid
            d["codif"]["word0"]["complex"] = self.complex
            d["codif"]["word0"]["epoch"] = self.epoch
            d["codif"]["word0"]["frame_id"] = self.frame_id
            d["codif"]["word1"]["version"] = self.version
            d["codif"]["word1"]["bits_per_sample"] = self.bits_per_sample
            d["codif"]["word1"]["array_length"] = self.array_length
            d["codif"]["word1"]["ref_epoch_period"] = self.ref_epoch_period
            d["codif"]["word1"]["sample_representation"] = self.sample_representation
            d["codif"]["word1"]["unassigned"] = self.unassigned
            d["codif"]["word1"]["station_id"] = self.station_id
            d["codif"]["word2"]["block_length"] = self.block_length
            d["codif"]["word2"]["channels_per_thread"] = self.channels_per_thread
            d["codif"]["word2"]["freq_group"] = self.freq_group
            d["codif"]["word2"]["beam_id"] = self.beam_id
            d["codif"]["word3"]["reserved16"] = self.reserved16
            d["codif"]["word3"]["period"] = self.period
            d["codif"]["word3"]["reserved32"] = self.reserved32
            d["codif"]["word4"]["intervals_per_period"] = self.intervals_per_period
            d["codif"]["word5"]["sync_seq"] = self.sync_seq
            d["codif"]["word5"]["reserved32"] = self.reserved32
            d["codif"]["word6"]["ext_data_version"] = self.ext_data_version
            d["codif"]["word6"]["ext_user_data"] = self.ext_user_data
            d["codif"]["word7"]["ext_user_data"] = self.ext_user_data

        return d

class CodifFile:
    """
    Description:
    ------------
        CodifFile represents a file containing CODIF packets. The file can be of
        type '.dada' or '.pcap'

    Attributes
    ----------
        fname : string
            Complete path to file including directory and filename
        type : string
            Optional argument to set the file type either 'dada' or 'pcap'
        size : integer
            Size of the file
        packet_list : list of CodifPacket
            Stores packets if desired (Caution must be taken when reading huge files)
        packet : CodifPacket
            The latest packet that was parsed
        packet_cnt : integer
            Counts the number of packets
        faulty_cnt : string
            Counts the number of faulty packets
        faulty_list : list of [int, CodifPacket]
            Stores faulty packets and the id of occurence
        zeroed_cnt : string
            Counts the number of packets which are zeroed. Usually occur in 'dada' files
        stream_position : integer
            Position of the file stream
        dada_header : BytesIO
            Contains DADA header information
    Methods
    -------
        seek_packet(self, packet, offset, whence, size)

        seek(self, offset, whence)

        set_bpf_filter(self, filter)

        next(self, skip_payload)

        add(self, packet)

        remove(self, packet, id)

        read(self, packets, validate, add, verbose, skip_payload)

        write(self, start, end, keep)

        proof_order(self, packet, prev_reference)

        not_order_msg(self, packet, prev_reference)
    """
    def __init__(self, fname, type="dada"):
        """
        Description:
        ------------
            Constructor of CodifFile.

        Parameters
        ----------
            fname : string
                Entire path to file
            type : string
                Filetype
        """
        self.fname = fname
        self.type = type
        self.size = os.path.getsize(fname)
        self.packet_list = []
        self.packet = 0
        self.packet_cnt = 1
        self.faulty_cnt = 0
        self.faulty_list = []
        self.zeroed_cnt = 0
        self.stream_position = 0
        self.random_payload = ""
        self.frame_cnt = 0
        self.node_name = self.get_node_name()
        self.empty_payload = empty_string(CODIF_PAYLOAD) # Used if payload needs to be padded
        # The passed file is a .dada file
        if self.type == "dada":
            # Try to open the file
            try:
                self.file = open(self.fname, "rb")
            except IOError as e:
                raise e
            self.seek(0,2)
            self.endlocation = self.file.tell()
            self.seek(0)
            # Read dada header (Note: Every DADA file has an extra header)
            self.dada_header = self.file.read(DADA_HEADER_SIZE)
            # Calculate the number of packet
            self.npackets = (self.size - DADA_HEADER_SIZE) / CODIF_PACKET_SIZE
        # The passed file is a .pcap file
        elif self.type == "pcap":
            # Try to open the file
            try:
                # Here we use the PCAP lib functions to do offline parsing instead of file open()
                self.file = pcapy.open_offline(self.fname)
            except IOError as e:
                raise e
            # Calculate the number of packet
            self.npackets = (self.size) / CODIF_TOTAL_SIZE
        # The passed file type is not known
        else:
            raise HandlerError("Failed: CodifFile does not know format " + self.type)

    def empty(self):
        """
        Description:
        ------------
            Checks if filestream pointer reached the end of file
        Parameters
        ----------
            None
        Returns:
        --------
            Returns True if end is reached otherwise false
        """
        if self.file.tell() >= self.endlocation:
            return True
        else:
            return False

    def get_node_name(self):
        """
        Description:
        ------------
            Get name of numa node.
            ! Not very stable method, since the numa node name has to be in the file dirctory which is passed to __init__() !
        Parameters
        ----------
            None
        Returns:
        --------
            String containing numa node name
        """
        fl = self.fname.split('/')
        for f in fl:
            if "numa" in f:
                return f

    def seek_packet(self, packet, offset=0, whence=0, size=CODIF_PACKET_SIZE):
        """
        Description:
        ------------
            Changes the stream position to the given packet number and offset.
        Parameters
        ----------
            packet : int
                The n-th packet in the file where the stream position should point to
            offset : int
                Addtional offset in bytes (optional)
            whence : int
                Interpretation of seek (optional)
            size : int
                size of one packet (optional)
        Returns:
        --------
            New absolute position
        """
        self.stream_position = packet*CODIF_PACKET_SIZE + offset
        return self.file.seek(self.stream_position, whence)

    def seek(self, offset, whence=0):
        """
        Description:
        ------------
            Changes the stream position to the given packet number and offset.
        Parameters
        ----------
            offset : int
                Offset in bytes
            whence : int
                Interpretation of seek (optional)
        Returns:
        --------
            New absolute position
        """
        return self.file.seek(offset, whence)

    def set_bpf_filter(self, filter):
        """
        Description:
        ------------
            Sets filter for pcap parsing
        Parameters
        ----------
            filter : int
        Returns:
        --------
            -
        """
        if self.type == "pcap":
            self.file.setfilter(filter)
        else:
            raise HandlerError("failed set_bpf_filter(): just 'pcap' type supports this function")

    def next(self, skip_payload=False, add=False):
        """
        Description:
        ------------
            Collects the next CodifPacket
        Parameters
        ----------
            skip_payload : bool
                If set to True the payload is not read from the file
            add : bool
                If set to True, each packet is stored to list (CAUTION when reading huge files)
        Returns:
        --------
            True on success and False on failure
        """
        # Read packet from pcap file
        if self.type == "pcap":
            # Pcap library directly supports frame collecting
            packet = self.file.next()[1]
        # Read packet from dada file
        elif self.type == "dada":
            # DADA frame collection is byte based
            if skip_payload:
                packet = self.file.read(CODIF_HEADER) # Just read the header
                packet += self.empty_payload
                self.seek(CODIF_PAYLOAD, 1)    # And skip the payload
            else:
                packet = self.file.read(CODIF_PACKET_SIZE)

        # Check if we have enough bytes to create a packet
        if len(packet) >= CODIF_PACKET_SIZE:
            # If desired we can add packets to list
            if add == True or self.packet_cnt == 1:
                self.packet = CodifPacket(io.BytesIO(packet), skip_payload)
                self.add()
            # Reuse object by just updateing payload and header data
            else:
                self.packet.update(io.BytesIO(packet), skip_payload)
            self.packet_cnt += 1
            return True
        else:
            return False

    def next_frame(self, nelements=36, skip_payload=False):
        """
        Description:
        ------------
            Collects a dataframe.
            In terms of CODIF a dataframe refers to all received packet at same epoch and frame_id, but with a different beam_id (0 - 35).
        Parameters
        ----------
            nelements : int
                Number of elements (beam_id).
            skip_payload : bool
                If set to True the payload is not read from the file
            add : bool
                If set to True, each packet is stored to list (CAUTION when reading huge files)
        Returns:
        --------
            True on success and False on failure
        """
        epoch = -1
        frame_id = -1
        frame = []
        zero_cnt = 0
        while self.next(skip_payload):
            if self.packet.header.epoch != 0 and epoch == -1:
                epoch = self.packet.header.epoch
                frame_id = self.packet.header.frame_id
            if epoch == self.packet.header.epoch and frame_id == self.packet.header.frame_id:
                frame.insert(self.packet.header.beam_id, deepcopy(self.packet))
            if self.packet.header.beam_id == nelements-1:
                if len(frame) == None:
                    frame = []
                return frame

    def add(self, packet=None):
        """
        Description:
        ------------
            Adds a packet to list
        Parameters
        ----------
            packet : CodifPacket
                If packet is not set (None) add will use the latest parsed packet
                and add it to the list (optional)
        Returns:
        --------
            -
        """
        if packet == None:
            self.packet_list.append(self.packet)
        else:
            self.packet_list.append(packet)

    def remove(self, packet=None, id=None):
        """
        Description:
        ------------
            Removes a packet from list
        Parameters
        ----------
            packet : CodifPacket
                If passed it removes the packet from list (optional)
            id : int
                If passed it removes a packet identified by id from list (optional)
        Returns:
        --------
            -
        """
        if packet:
            self.packet_list.remove(packet)
        elif id:
            self.packet_list.pop(id)
        else:
            self.packet_list.pop(0)



    def read(self, packets=-1, validate=False, add=False, verbose=False, skip_payload=False):
        """
        Description:
        ------------
            Reads an amount of packets and offers some furhter opportunities.
        Parameters
        ----------
            packet : int
                The number of packets to read. If not set the whole file is read (optional)
            validate : bool
                = True, proofs the order of packets (optional)
                    If a packet is not in order it is counted as faulty packet.
                        Faulty packets are always stored in a list
                    If a packet contains only zeros it is counted as zero packet.
            add : bool
                = True, adds all packets to list. CAUTION when reading a huge file
            verbose: bool
                = True, verbose messages. Has only effect in combination with validate
            skip_payload : bool
                = True, skips the payload
        Returns:
        --------
            -
        """
        ref_beam = 0
        ref_frame = 0
        ref_epoch = 0
        # If not the entire file should be read
        if packets != -1:
            bytes = packets*CODIF_PACKET_SIZE
            while bytes > 0:
                if self.next(skip_payload, add):
                    if not self.proof_order(self.packet, ref_beam, ref_frame, ref_epoch) and validate:
                        # if self.packet.header.beam_id == 0 and self.packet.header.epoch==0 and self.packet.header.frame_id == 0:
                        #     self.zeroed_cnt += 1
                        # else:
                        #     self.faulty_list.append([self.packet_cnt, self.packet])
                        #     self.faulty_cnt += 1
                        if verbose:
                            print(self.not_order_msg(self.packet, ref_beam, ref_frame, ref_epoch))

                    ref_beam = self.packet.header.beam_id
                    ref_frame = self.packet.header.frame_id
                    ref_epoch = self.packet.header.epoch
                    bytes -= CODIF_PACKET_SIZE
        # Entire file is read
        else:
            while self.next(skip_payload, add):
                if not self.proof_order(self.packet, ref_beam, ref_frame, ref_epoch) and validate:
                    # if self.packet.header.beam_id == 0 and self.packet.header.epoch==0 and self.packet.header.frame_id == 0:
                    #     self.zeroed_cnt += 1
                    # else:
                    #     self.faulty_list.append([self.packet_cnt, self.packet])
                    #     self.faulty_cnt += 1
                    if verbose:
                        print(self.not_order_msg(self.packet, ref_beam, ref_frame, ref_epoch))
                ref_beam = self.packet.header.beam_id
                ref_frame = self.packet.header.frame_id
                ref_epoch = self.packet.header.epoch

    def faulty_packets2json(self, fname):
        """
        Description:
        ------------
            Dumps all faulty packets to a json file
        Parameters
        ----------
            fname : string
                directory + filename
        Returns:
        --------
            -
        """
        with open(fname+".json", "w") as f:
            json.dump(self.faulty_packets, f, indent=4)

    def write(self, start=0, end=None, keep=False):
        """
        Description:
        ------------
            Not implemented
        Parameters
        ----------
            -
        Returns:
        --------
            -
        """
        # if self.output_file:
        #     if end == None:
        #         end = len(self.packet_list)
        #     if start > end:
        #         raise HandlerError("failed write(): start index is greater than end index")
        #     if len(self.packet_list) >= end:
        #         for packet_idx in range(start,end):
        #             self.output_file.write(self.packet_list[packet_idx].stream)
        #         if keep:
        #             return
        #         self.packet_list.clear()
        #     else:
        #         raise HandlerError("failed write(): list out of range")
        #
        # else:
        #     raise HandlerError("failed write(): File not opened, can not write")


    # Horrible dirty function
    def proof_order(self, packet, ref_beam, ref_frame, ref_epoch):
        """
        Description:
        ------------
            Proofs if two packets are in order or not.
        Parameters
        ----------
            packet : CodifPacket
                packet to proof
            ref_beam : int
            ref_frame : int
            ref_epoch : int
        Returns:
        --------
            Return true if in order, and false if not in order
        """
        # initial packet
        # Same data frame
        if packet.header.beam_id-1 == ref_beam:
            if packet.header.frame_id == ref_frame and packet.header.epoch == ref_epoch:
                return True
            else:
                self.is_faulty_or_zeroed(packet)
                return False
        # new data frame index
        elif ref_beam == 35 and packet.header.beam_id == 0:
            if packet.header.frame_id-1 == ref_frame and packet.header.epoch == ref_epoch:
                return True
            # New period
            elif packet.header.frame_id == 0 and ref_frame == 249999 and packet.header.epoch + packet.header.period == ref_epoch:
                return True
            else:
                self.is_faulty_or_zeroed(packet)
                return False
        else:
            self.is_faulty_or_zeroed(packet)
            return False
        return True

    def is_faulty_or_zeroed(self, packet):
        if packet.header.beam_id == 0 and packet.header.epoch==0 and packet.header.frame_id == 0:
            self.zeroed_cnt += 1
        else:
            #self.faulty_list.append([self.packet_cnt, deepcopy(packet)])
            self.faulty_cnt += 1

    def not_order_msg(self, packet, ref_beam, ref_frame, ref_epoch):
        """
        Description:
        ------------
            Prints a readable message if packets are not in order
        Parameters
        ----------
            packet : CodifPacket
                packet to proof
            ref_beam : int
            ref_frame : int
            ref_epoch : int
        Returns:
        --------
            readable message
        """
        string = ("Packet not in order! Read "+str(self.packet_cnt)+"\nPacket "
            + str(packet.header.frame_id)
            + " with beam index "
            + str(packet.header.beam_id)
            + " in epoch "
            + str(packet.header.epoch)
            + " not trusted/in order \nPrevious packet "
            + str(ref_frame)
            + " with beam index "
            + str(ref_beam)
            + " in epoch "
            + str(ref_epoch)
            + " not trusted/in order")
        return string


class CodifHandler:
    """
    Description:
    ------------
        CodifHandler handles a bunch of files concurrently in different threads.
        Thus it is possible to read several files in parallel

    Attributes
    ----------
        fin_list : list of strings
            List containing all files that should be handled (dirctory + filename)
        type : string
            All files must have the same type (either 'dada' or 'pcap')
        file_handle : list of CodifFile
            List containg all CodifFile objects
    Methods
    -------
        validate(self, packets, threads, deamon)
            Validates all passed files and visualize the progress within a curses window
        compute_acm(self, nelements, nsamples=128, nchannel=7, pol=2)
            Computes ACMs from a given file set. It should be noted that only files of the same channel group can be passed.
        plot_acm(self, acm, freq, dir="")
            Plots a passed ACM
        merge()
            not implemented
        clean()
            not implemented
        to_array()
            not implemented
        threaded_read(self, q, packets, validate, add, skip_payload)
            Wraps CodifFile.read() into a Queue of Thread objects
    """
    def __init__(self, fin_list, type="dada", fout=""):
        print("Found " + str(len(fin_list)) + " files that matches expression")
        self.fin_list = fin_list
        self.fout = fout
        self.file_handle = []
        self.numa_list = []
        self.timestamp = 0
        self.total_packets = 0
        # For each item in list create a CodifFile object
        for fname in (fin_list):
            self.file_handle.append( CodifFile(fname, type) )
            file = self.file_handle[-1]
            if not file.node_name in self.numa_list:
                self.numa_list.append(self.file_handle[-1].node_name)
            self.total_packets += self.file_handle[-1].npackets


    def compute_acm(self, nelements, nsamples=CODIF_BLOCKS_IN_PACKET, nchannel=CODIF_CHANNELS_IN_BLOCK, pol=CODIF_POLARIZATION):
        """
        Description:
        ------------
            Computes an ACM from all files that are passed to the the CodifHandler.
        Parameters
        ----------
            nelements : int
                Number of elements which has to be equal to the recorded 'beams'.
            nsamples : int
                Number of samples in a datablock (optional). Should not be set for now
            nchannel : int
                Number of channels within a channel group (optional). Should not be set for now
            pol : int
                Number of polarizations (optional). Should not be set for now
        Returns:
        --------
            Returns calculated ACM as 3D ndarray of size [channels, elements*pol, elements*pol] and frequencies of channels
        """
        # Construct necessary numpy array
        acm = np.zeros((nchannel, nelements*pol, nelements*pol), dtype="complex")
        data = np.zeros((nelements*pol, nsamples, nchannel), dtype="complex")

        # Set counters for displaying current progress
        frame_cnt = 0
        uncomplete_cnt = 0

        # Iterate over all passed CodifFiles
        for fidx, file in enumerate(self.file_handle):
            print("\nWorking on file " + str(fidx+1) + "/" + str(len(self.file_handle)))
            # Further variables (displaying purposes)
            start = time.time()
            file_frame_cnt = 0

            # As long as not all data read from current file
            while not file.empty():
                # Read the next frame (A frame contains nelements == beams (e.g. 36) CodifPackets )
                frame = file.next_frame(nelements)
                # Check if we should ignore frame (zeroed packets)
                if frame != None:
                    # Check if we should ignore frame (packet loss)
                    if len(frame) == nelements:
                        # Store the first epoch and frame index to calculate duration of snapshot
                        if frame_cnt == 0:
                            first_epoch = frame[0].header.epoch
                            first_frame_id = frame[0].header.frame_id

                        frame_cnt += 1
                        file_frame_cnt += 1

                        # Iterate over each element (remember a frame contains all elements)
                        for element in frame:
                            idx = element.header.beam_id # Get beam index which is equal to element index
                            data[idx] = element.payload.data[:,:,0] # Assign x-pol to numpy array
                            data[idx + nelements] = element.payload.data[:,:,1] # Assign y-pol to numpy array
                        # Calculate ACM by dot product over each channel within a channel group
                        for chan in range(nchannel):
                            acm[chan] += data[:,:,chan].dot(data[:,:,chan].conj().T)
                    # Register lost packet
                    else:
                        uncomplete_cnt += 1
                # Register lost packet
                else:
                    uncomplete_cnt += 1

                # Display progress
                sys.stdout.write('\r Total frames: {:d}/{:d}, file frames: {:d}/{:d}, uncomplete: {:d}; duration: {:.2f} s' \
                    .format(frame_cnt + uncomplete_cnt,
                        int(self.total_packets/nelements),
                        file_frame_cnt + uncomplete_cnt,
                        int(file.npackets/nelements),
                        uncomplete_cnt,
                        time.time()-start))

        # Calculate frequencies of channels
        freq = np.arange(frame[0].header.freq_group, frame[0].header.freq_group+7)
        # Get last epoch and frame index
        last_epoch = frame[0].header.epoch
        last_frame_id = frame[0].header.frame_id
        # Calculate snapshot duration
        duration = (last_epoch - first_epoch) \
            + (last_frame_id - first_frame_id) \
            * CODIF_BLOCKS_IN_PACKET / PAF_SAMPLE_PERIOD
        print("\nDuration of record: " +str(duration) + " s")

        return acm, freq



    def validate(self, packets=-1, threads=1, deamon=True, display="file"):
        """
        Description:
        ------------
            Validates all files in file_handle list
        Parameters
        ----------
            packets : int
                Number of packets to proof
            thread : int
                Number of parallel threads
            daemon: bool
                Run threads as daemon. Do not set to False!
        Returns:
        --------
            -
        """
        print("Starting to validate " +str(len(self.file_handle))+ " with " + str(threads) + " threads")

        # Create Queue and assign work
        uniques = sorted(set([re.split('\_|\.', f)[1] for f in self.fin_list]))

        sub_handle = [[] for i in range(len(uniques))]
        total_pkt_num = 0
        total_pkt_cnt = 0
        total_fal_cnt = 0
        total_zro_cnt = 0
        pkt_cnt = []
        fal_cnt = []
        zro_cnt = []
        last_time = []

        total_pkt_numa_num = [0 for i in range(len(self.numa_list))]

        occurence = [0]*len(uniques)
        for k, file in enumerate(self.file_handle):
            if file.npackets < 1:
                continue
            for i, f_expr in enumerate(uniques):
                if f_expr in file.fname:
                    occurence[i] += 1
                    sub_handle[i].append(file)
            idx = self.numa_list.index(file.node_name)
            total_pkt_numa_num[idx] += file.npackets
            total_pkt_num += int(file.npackets)

        for node in self.numa_list:
            last_time.append(time.time())
            pkt_cnt.append(0)
            fal_cnt.append(0)
            zro_cnt.append(0)

        file_cnt = [0 for i in range(max(occurence))]
        for sub_idx, sub in enumerate(sub_handle):

            sub_pkt_num = 0
            rows = len(sub_handle[0]) + 5
            cols = 10
            display_list = []

            total_rate = 0
            cur_rate = 0


            if display == "node":
                last_pkt_cnt = [0 for i in range(len(self.numa_list))]
                last_zro_cnt = [0 for i in range(len(self.numa_list))]
                last_fal_cnt = [0 for i in range(len(self.numa_list))]

            elif display == "file":
                pkt_cnt = [0 for i in range(len(sub))]
                fal_cnt = [0 for i in range(len(sub))]
                zro_cnt = [0 for i in range(len(sub))]
                last_pkt_cnt = [0 for i in range(len(sub))]
                last_zro_cnt = [0 for i in range(len(sub))]
                last_fal_cnt = [0 for i in range(len(sub))]

            self.jobs = Queue()
            for file_idx, file in enumerate(sub):
                if file.npackets > 0:
                    self.jobs.put( file )
                    sub_pkt_num += file.npackets
                    if sub_idx != 0:
                        file_cnt[file_idx] += len(sub_handle[sub_idx-1])
                    else:
                        file_cnt[file_idx] += file_idx
                # If the file is too "small" do not join Queue and delete from list
                else:
                    sub.remove(file)


            # Launch Threads
            for t in range(threads):
                thread = Thread(target=self.threaded_read, args=(self.jobs, packets, True, False, True))
                thread.daemon = deamon
                thread.start()


            file_header_row = ["File", "Progress", "Read pkt", "Total pkt", "Faulty [%]", "Faulty pkt", "Zeroed [%]", "Zeroed pkt", "Rate [pkt/s]", "Filename"]
            seperater_row = ["------------", "------------", "------------", "------------", "------------", "------------", "------------", "------------", "------------", "------------"]

            monitor = Monitor(rows, cols)
            while not self.jobs.empty():
                if not KeyboardInterrupt:
                    monitor.close()
                    break

                for r in range(rows):
                    display_list.append([])
                    if r == 0:
                        display_list[r] = file_header_row
                        continue

                    elif r == 1 or r == rows-1 or r == rows - 4:
                        display_list[r] = seperater_row
                        continue
                    elif r == rows-2:
                        if display == "file":
                            display_list[r] = ['Subset',
                                '{:.2f}%'.format(sum(pkt_cnt)/sub_pkt_num*100),
                                ' ',' ',
                                '{:.2f}%'.format(sum(fal_cnt)/sub_pkt_num*100),
                                ' ',
                                '{:.2f}%'.format(sum(zro_cnt)/sub_pkt_num*100),
                                ' ',
                                '{:.2f}'.format(total_rate),
                                sub[0].fname.rsplit('/',1)[1]]
                        elif display == "node":
                            display_list[r] = seperater_row
                    elif r == rows-3:
                        display_list[r] = ['Total',
                            '{:.2f}%'.format(total_pkt_cnt/total_pkt_num*100),
                            ' ',' ',
                            '{:.2f}%'.format(total_fal_cnt/total_pkt_num*100),
                            ' ',
                            '{:.2f}%'.format(total_zro_cnt/total_pkt_num*100),
                            ' ',
                            '{:.2f}'.format(total_rate),
                            sub[0].fname.rsplit('/',1)[1]]
                        total_rate = 0
                    else:
                        if display == "file":
                            i = r-2
                            if i < len(sub):
                                file = sub[i]
                                cur_dif = file.packet_cnt-last_pkt_cnt[i]
                                cur_time = time.time()
                                cur_rate = cur_dif/(cur_time-last_time[i])
                                pkt_cnt[i] += cur_dif
                                fal_cnt[i] += file.faulty_cnt - last_fal_cnt[i]
                                zro_cnt[i] += file.zeroed_cnt - last_zro_cnt[i]
                                total_pkt_cnt += cur_dif
                                total_fal_cnt += file.faulty_cnt - last_fal_cnt[i]
                                total_zro_cnt += file.zeroed_cnt - last_zro_cnt[i]
                                total_rate += cur_rate
                                display_list[r] = ['{:<5}'.format(file_cnt[i]),
                                    '{:<6.2f}%'.format(file.packet_cnt/file.npackets*100),
                                    '{:<9}'.format(file.packet_cnt),
                                    '{:<9}'.format(file.npackets),
                                    '{:<6.2f}%'.format(file.faulty_cnt/file.packet_cnt*100),
                                    '{:<7}'.format(file.faulty_cnt),
                                    '{:<6.2f}%'.format(file.zeroed_cnt/file.packet_cnt*100.0),
                                    '{:<7}'.format(file.zeroed_cnt),
                                    '{:<6.1f}'.format(cur_rate),
                                    '{}'.format(file.fname)]

                                last_time[i] = cur_time
                                last_pkt_cnt[i] = file.packet_cnt
                                last_zro_cnt[i] = file.zeroed_cnt
                                last_fal_cnt[i] = file.faulty_cnt

                        elif display == "node":
                            i = r-2
                            if i < len(sub):
                                file = sub[i]
                                idx = self.numa_list.index(file.node_name)
                                cur_dif = file.packet_cnt-last_pkt_cnt[idx]
                                cur_time = time.time()
                                cur_rate = cur_dif/(cur_time-last_time[idx])
                                pkt_cnt[idx] += cur_dif
                                fal_cnt[idx] += file.faulty_cnt - last_fal_cnt[idx]
                                zro_cnt[idx] += file.zeroed_cnt - last_zro_cnt[idx]
                                total_pkt_cnt += cur_dif
                                total_fal_cnt += file.faulty_cnt - last_fal_cnt[i]
                                total_zro_cnt += file.zeroed_cnt - last_zro_cnt[i]
                                total_rate += cur_rate
                                display_list[r] = [self.numa_list[idx],
                                    '{:<6.2f}%'.format(pkt_cnt[idx]/total_pkt_numa_num[idx]*100),
                                    '{:<9}'.format(pkt_cnt[idx]),
                                    '{:<9}'.format(total_pkt_numa_num[idx]),
                                    '{:<6.2f}%'.format(fal_cnt[idx]/total_pkt_numa_num[idx]*100),
                                    '{:<7}'.format(fal_cnt[idx]),
                                    '{:<6.2f}%'.format(zro_cnt[idx]/total_pkt_numa_num[idx]*100.0),
                                    '{:<7}'.format(zro_cnt[idx]),
                                    '{:<6.1f}'.format(cur_rate),
                                    '{}'.format(file.fname)]

                                last_time[idx] = cur_time
                                last_pkt_cnt[idx] = file.packet_cnt
                                last_zro_cnt[idx] = file.zeroed_cnt
                                last_fal_cnt[idx] = file.faulty_cnt

                monitor.update(display_list)
                time.sleep(0.2)

	monitor.wait_for_input()
	monitor.close()

    def merge(self):
        pass

    def clean(self):
        pass

    def to_array(self):
        pass
        
    def to_csv(self, dir, fname):
        # Store results in pandas dataframe
        print("Exporting results to " + dir + fname)
        results = pd.DataFrame(columns=['Processed packets', 'Total packets', 'Faulty %', 'Faulty total', 'Zeored %', 'Zeroed total', 'Filename'])
        for file in self.file_handle:
            data = {'Processed packets':file.packet_cnt,
                'Total packets':file.npackets,
                'Faulty %': file.faulty_cnt/file.packet_cnt*100,
                'Faulty total': file.faulty_cnt,
                'Zeored %':file.zeroed_cnt/file.packet_cnt*100.0,
                'Zeroed total':file.zeroed_cnt,
                'Filename': file.fname}
            results = results.append(data, ignore_index=True)
        results.to_csv(dir + fname)

    def threaded_read(self, q, packets=-1, validate=False, add=False, skip_payload=False):
        while True:
            item = q.get()
            item.read(packets, validate=validate, add=add, skip_payload=skip_payload)
            q.task_done()


class Monitor:
    def __init__(self, rows, cols, col_width=12):
        self.stdout = sys.stdout
        self.rows = rows
        self.cols = cols
        self.col_width = col_width

        # Create curses window
        self.display = curses.initscr()
        curses.noecho()
        curses.cbreak()

    def update(self, dlist):
        # Below the current statistics are calculated
        for r in range(self.rows):
            for c in range(self.cols):
                self.display.addstr(r,c*self.col_width, dlist[r][c])
        self.display.refresh()

    def wait_for_input(self):
        while True:
            c = self.display.getch()
            if c:
                break

    def close(self):
        curses.endwin()
        sys.stdout = self.stdout
