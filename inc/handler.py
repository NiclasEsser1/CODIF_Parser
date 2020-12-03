import pcapy
import struct

class HandlerError(Exception):
    pass

class CodifHandler:
    def __init__(self, fname, type="dada", outfile=""):
        self.fname = fname
        self.type = type
        if type = "dada":
            try:
                self.input_file = open(self.fname, "rb")
            except IOError as e:
                raise e
            self.dada_header = self.input_file.read(4096)
        elif type == "pcap":
            try:
                self.input_file = pcapy.open_offline(self.fname)
            except IOError as e:
                raise e
        else:
            raise HandlerError("Failed: CodifHandler does not know format " + self.type)

        if outfile != "":
            try:
                self.output_file = open(self.fname, "wb+")
            except IOError as e:
                raise e

        self.packet_list = []
        self.packet = 0
        self.packet_cnt = 0


    def set_bpf_filter(self, filter):
        if self.type == "pcap":
            self.input_file.setfilter(filter)
        else:
            raise HandlerError("failed set_bpf_filter(): just 'pcap' type supports this function")

    def next(self):
        frame = self.input_file.read(CODIF_PACKET_SIZE)
        if(len(frame) == CODIF_PACKET_SIZE):
            self.packet = CodifPacket(io.BytesIO(frame))
            self.packet_cnt += 1
            return True
        else:
            print("Could not read packet")
            return False


    def add(self, packet=None):
        if packet == None:
            self.packet_list.append(self.packet)
        else:
            self.packet_list.append(packet)


    def read(self, packets=-1, validate=False, remove=False):
        old_packet = 0
        if packets != -1:
            bytes = packets*CODIF_PACKET_SIZE
            while(bytes > 0):
                if self.next():
                    if validate:
                        if not self.proof_order(self.packet, old_packet):
                            print(self.not_order_msg(self.packet, old_packet))
                            old_packet = old_packet
                    if remove:
                        if not self.proof_order(self.packet, old_packet):
                            old_packet = old_packet
                        else:
                            self.add()
                    else:
                        self.add()
                else:
                    print("Could not parse packet")
                bytes = bytes - CODIF_PACKET_SIZE
        else:
            while self.next():
                if validate:
                    if not self.proof_order(self.packet, old_packet):
                        print(self.not_order_msg(self.packet, old_packet))
                        # break
                    old_packet = self.packet
                else:
                    self.add()

    def write(self, end, start=0):
        if self.output_file:
            if len(self.packet_list) >= end - start:
                for packet_idx in range(start,end):
                    self.output_file.write(packet_list[packet_idx].steam)
        else:
            raise  HandlerError("failed write(): File not opened, can not write")


    # Horrible dirty function
    @class_method
    def proof_order(self, packet, old_packet):
        # initial packet
        if old_packet == 0:
            return True
        # Same data frame
        if packet.header.beam_id-1 == old_packet.header.beam_id:
            if packet.header.frame_number == old_packet.header.frame_number and packet.header.epoch_start_sec == old_packet.header.epoch_start_sec:
                return True
            else:
                return False
        # new data frame index
        elif old_packet.header.beam_id == 35 and packet.header.beam_id == 0:
            if packet.header.frame_number-1 == old_packet.header.frame_number and packet.header.epoch_start_sec == old_packet.header.epoch_start_sec:
                return True
            # New period
            elif packet.header.frame_number == 0 and old_packet.header.frame_number == 249999 and packet.header.epoch_start_sec + packet.header.period == old_packet.header.epoch_start_sec:
                return True
            else:
                return False
        else:
            return False
        return True


    @class_method
    def not_order_msg(self, packet, old_packet):
        string = ("Packet not in order! Read "+str(self.packet_cnt)+"\nPacket "
            + str(packet.header.frame_number)
            + " with beam index "
            + str(packet.header.beam_id)
            + " in epoch "
            + str(packet.header.epoch_start_sec)
            + " not trusted/in order \nPrevious packet "
            + str(old_packet.header.frame_number)
            + " with beam index "
            + str(old_packet.header.beam_id)
            + " in epoch "
            + str(old_packet.header.epoch_start_sec)
            + " not trusted/in order")
        return string
