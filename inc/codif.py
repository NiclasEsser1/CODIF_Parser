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
import numpy as np
from threading import Thread
from Queue import Queue
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
        self.payload = np.zeros(
            (CODIF_BLOCKS_IN_PACKET, CODIF_CHANNELS_IN_BLOCK, CODIF_POLARIZATION),
            dtype="complex")
        for block in range(CODIF_BLOCKS_IN_PACKET):
            for channel in range(CODIF_CHANNELS_IN_BLOCK):
                for pol in range(CODIF_POLARIZATION):
                    self.payload[block, channel, pol] = struct.unpack("!H", self.stream.read(2))[0]
                    self.payload[block, channel, pol] += struct.unpack("!H", self.stream.read(2))[0] *1j
    def update(self, stream):
        self.stream = stream
        for block in range(CODIF_BLOCKS_IN_PACKET):
            for channel in range(CODIF_CHANNELS_IN_BLOCK):
                for pol in range(CODIF_POLARIZATION):
                    self.payload[block, channel, pol] = struct.unpack("!H", self.stream.read(2))[0]
                    self.payload[block, channel, pol] += struct.unpack("!H", self.stream.read(2))[0] *1j

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
        parse()
            Parses the bystream to a dictionary.
        parse_eth_hdr()
            Parses ethernet protcol header.
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
        self.header = {
            "eth" : {},
            "ipv4" : {},
            "udp" : {},
            "codif" : {
                "word"+str(i) : {} for i in range(0,8)
            }
        }
        self.stream = stream
        self.nbytes = len(stream.getvalue())#getbuffer().nbytes
        self.parse()

    def update(self,stream):
        self.stream = stream
        self.parse_codif_hdr_light()

    def parse(self):
        # ETHII layer
        if self.nbytes == CODIF_TOTAL_SIZE:
                self.parse_eth_hdr()
                self.parse_ipv4_hdr()
                self.parse_udp_hdr()
                self.parse_codif_hdr()
        # IPV4 layer
        elif self.nbytes == CODIF_TOTAL_SIZE - ETHII_HEADER:
                self.parse_ipv4_hdr()
                self.parse_udp_hdr()
                self.parse_codif_hdr()
        # UDP layer
        elif self.nbytes == CODIF_TOTAL_SIZE - ETHII_HEADER - IPV4_HEADER:
            self.parse_udp_hdr()
            self.parse_codif_hdr()
        # CODFI layer (=4)
        elif self.nbytes >= CODIF_PACKET_SIZE:
                self.parse_codif_hdr()
        else:
            print("Failed to parse CODIF packet from layer "
                + str(layer)
                + ": byte size ("
                + str(self.nbytes)
                + "/"
                + str(CODIF_TOTAL_SIZE)
                +")")

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

    def parse_codif_hdr_light(self):
        """
        Description:
        ------------
            Used for faster parsing of datastream
        Parameters
        ----------
            None
        """
        header = []
        for i in range(0,3):
            header.append(struct.unpack("!Q", self.stream.read(8))[0])
        self.epoch_start_sec = header[0] >> 32
        self.frame_number = header[0] & 0x00000000FFFFFFFF
        self.beam_id = (header[2] & 0x000000000000FFFF)

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
        self.header["codif"]["word2"]["freq_group"] = (header[2] & 0x00000000FFFF0000) >> 16
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
        self.freq_group = self.header["codif"]["word2"]["freq_group"]
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
        zero_pkt_cnt : string
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
        self.zero_pkt_cnt = 0
        self.stream_position = 0
        self.random_payload = ""
        # The passed file is a .dada file
        if self.type == "dada":
            # Try to open the file
            try:
                self.file = open(self.fname, "rb")
            except IOError as e:
                raise e
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
        Returns:
        --------
            True on success and False on failure
        """
        if self.type == "pcap":
            # Pcap library directly supports frame collecting
            frame = self.file.next()[1]
        elif self.type == "dada":
            # DADA frame collection is byte based
            if skip_payload:
                frame = self.file.read(CODIF_HEADER) # Just read the header
                if self.random_payload == "":
                    self.random_payload = gen_payload(CODIF_PAYLOAD)
                frame += self.random_payload
                self.seek(CODIF_PAYLOAD, 1)    # And skip the payload
            else:
                frame = self.file.read(CODIF_PACKET_SIZE)

        if(len(frame) >= CODIF_PACKET_SIZE):
            if add == True or self.packet_cnt == 1:
                self.packet = CodifPacket(io.BytesIO(frame), skip_payload)
                self.add()
            # Reuse object
            else:
                self.packet.update(io.BytesIO(frame), skip_payload)
            self.packet_cnt += 1
            return True
        else:
            return False


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
                        if self.packet.header.beam_id == 0 and self.packet.header.epoch_start_sec==0 and self.packet.header.frame_number == 0:
                            self.zero_pkt_cnt += 1
                        else:
                            self.faulty_list.append([self.packet_cnt, self.packet])
                            self.faulty_cnt += 1
                        if verbose:
                            print(self.not_order_msg(self.packet, ref_beam, ref_frame, ref_epoch))

                    ref_beam = self.packet.header.beam_id
                    ref_frame = self.packet.header.frame_number
                    ref_epoch = self.packet.header.epoch_start_sec
                bytes -= CODIF_PACKET_SIZE
        # Entire file is read
        else:
            while self.next(skip_payload, add):
                if not self.proof_order(self.packet, ref_beam, ref_frame, ref_epoch) and validate:
                    if self.packet.header.beam_id == 0 and self.packet.header.epoch_start_sec==0 and self.packet.header.frame_number == 0:
                        self.zero_pkt_cnt += 1
                    else:
                        self.faulty_list.append([self.packet_cnt, self.packet])
                        self.faulty_cnt += 1
                    if verbose:
                        print(self.not_order_msg(self.packet, ref_beam, ref_frame, ref_epoch))
                old_packet = self.packet
                ref_beam = self.packet.header.beam_id
                ref_frame = self.packet.header.frame_number
                ref_epoch = self.packet.header.epoch_start_sec

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
            Proofs if two packets are in order or not
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
            if packet.header.frame_number == ref_frame and packet.header.epoch_start_sec == ref_epoch:
                return True
            else:
                return False
        # new data frame index
        elif ref_beam == 35 and packet.header.beam_id == 0:
            if packet.header.frame_number-1 == ref_frame and packet.header.epoch_start_sec == ref_epoch:
                return True
            # New period
            elif packet.header.frame_number == 0 and ref_frame == 249999 and packet.header.epoch_start_sec + packet.header.period == ref_epoch:
                return True
            else:
                return False
        else:
            return False
        return True


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
            + str(packet.header.frame_number)
            + " with beam index "
            + str(packet.header.beam_id)
            + " in epoch "
            + str(packet.header.epoch_start_sec)
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
        self.fin_list = fin_list
        self.fout = fout
        self.file_handle = []
        # For each item in list create a CodifFile object
        for file in (fin_list):
            self.file_handle.append( CodifFile(file, type) )

    def validate(self, packets=-1, threads=1, deamon=True):
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
        print("Starting to validate " +str(len(self.file_handle))+ " with " + str(threads))
        # Create Queue and assign work
        jobs = Queue()
        for file in self.file_handle:
            if file.npackets > 1:
                jobs.put( file )
            # If the file is too "small" do not join Queue and delete from lsit
            else:
                self.file_handle.remove(file)

        # Launch Threads
        for t in range(threads):
            thread = Thread(target=self.threaded_read, args=(jobs, packets, True, False, True))
            thread.daemon = deamon
            thread.start()
        # Sleep two seconds to make sure all threads are launched
        time.sleep(2)

        # Create curses window
        stdscr = curses.initscr()
        stdscr.keypad(1)
        curses.noecho()
        curses.cbreak()

        last_time = []
        last_pkt_cnt = []
        for i in range(len(self.file_handle)):
            last_time.append(time.time())
            last_pkt_cnt.append(0)

        # Below the current statistics are calculated
        while True:
            if not KeyboardInterrupt:
                curses.endwin()
                break

            total_pkt_cnt = 0
            total_pkt_num = 0
            total_fal_cnt = 0
            total_zro_cnt = 0
            total_rate = 0

            stdscr.addstr(0,0, "File \t|Progress\t\t\t\t|Faulty\t\t\t|Zeros\t\t\t|Pkt/s\t\t|Filename")
            stdscr.addstr(1,0, "----------------------------------------------------------------------------------------------------------------------------------------------------")
            for i, file in enumerate(self.file_handle):
                cur_time = time.time()
                cur_rate = (file.packet_cnt - last_pkt_cnt[i])/(cur_time - last_time[i])
                stdscr.addstr(i+2, 0, '{:<5}\t| {:<6.2f}%  ({:<9}/ {:<9}) \t| {:<6.2f}% / {:<7} \t| {:<6.2f}% / {:<7} \t| {:<6.1f} \t| {}'.format(i,
                    file.packet_cnt/file.npackets*100,
                    file.packet_cnt,
                    file.npackets,
                    file.faulty_cnt/file.packet_cnt*100,
                    file.faulty_cnt,
                    file.zero_pkt_cnt/file.packet_cnt*100.0,
                    file.zero_pkt_cnt,
                    cur_rate,
                    file.fname))
                last_time[i] = cur_time
                last_pkt_cnt[i] = file.packet_cnt
                total_pkt_num += file.npackets
                total_pkt_cnt += file.packet_cnt
                total_fal_cnt += file.faulty_cnt
                total_zro_cnt += file.zero_pkt_cnt
                total_rate += cur_rate
            stdscr.addstr(i+3,0, "----------------------------------------------------------------------------------------------------------------------------------------------------")
            stdscr.addstr(i+4, 0, 'Total\t| {:.2f} %\t\t\t\t| {:.2f} %\t\t| {:.2f}%\t\t|{:.2f}'.format(
                total_pkt_cnt/total_pkt_num*100,
                total_fal_cnt/total_pkt_cnt*100,
                total_zro_cnt/total_pkt_cnt*100,
                total_rate))
            stdscr.refresh()
            time.sleep(1)


    def merge():
        pass

    def clean():
        pass

    def to_array():
        pass


    def threaded_read(self, q, packets=-1, validate=False, add=False, skip_payload=False):

        while True:
            item = q.get()
            item.read(packets, validate=validate, add=add, skip_payload=skip_payload)
            q.task_done()
