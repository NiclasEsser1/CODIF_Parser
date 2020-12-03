import pcapy
import struct
from inc import protocols

class HandlerError(Exception):
    pass

class CodifHandler:
    def __init__(self, fin_list, type="dada", fout=""):
        self.fin_list = fin_list
        self.fout = fout
        self.handles = []
        if type(fout) is list:
            if len(fout) == len(fin_list):
                for idx, file in enumerate(fin_list):
                    self.file_handle.append( CodifFile(file, type, fout[idx]) )
            else:
                raise HandlerError("failed init: list size not identical")
        elif type(fout) is str:
            for file in (fin_list):
                self.file_handle.append( CodifFile(file, type, fout) )


    def clean(self, chunks=2048):
        if fout == "":
            raise HandlerError("failed clean(): Outputfile must provided in order to clean")
        for file in self.file_handle:
            file.read(chunks, True, True)
            file.write()

    def merge(self):
        pass
    def validate(self, packets):
        for file in self.file_handle:
            print("Validating file "+file.fname)
            file.read(packets, True)

    def to_array(self):
        pass

class CodifFile:
    def __init__(self, fname, type="dada", outfile=""):
        self.fname = fname
        self.type = type
        if self.type == "dada":
            try:
                self.input_file = open(self.fname, "rb")
            except IOError as e:
                raise e
            self.dada_header = self.input_file.read(4096)
        elif self.type == "pcap":
            try:
                self.input_file = pcapy.open_offline(self.fname)
            except IOError as e:
                raise e
        else:
            raise HandlerError("Failed: CodifFile does not know format " + self.type)

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
        if self.type == "pcap":
            frame = self.input_file.next()[1]
        elif self.type == "dada":
            frame = self.input_file.read(CODIF_PACKET_SIZE)
        else:
            raise HandlerError("failed next(): input type " + self.type + " is not supported")
        if(len(frame) >= CODIF_PACKET_SIZE):
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

    def remove(self, packet=None, id=None):
        if packet:
            self.packet_list.remove(packet)
        elif id:
            self.packet_list.pop(id)
        else:
            self.packet_list.pop(0)


    def read(self, packets=-1, validate=False, add=False):
        old_packet = 0
        if packets != -1:
            bytes = packets*CODIF_PACKET_SIZE
            while(bytes > 0):
                if self.next():
                    if validate:
                        if not self.proof_order(self.packet, old_packet):
                            faulty_cnt += 1
                            old_packet = old_packet
                        elif add == True:
                            self.add()
                    else:
                        self.add()
                else:
                    print("Could not parse packet")
                bytes -= CODIF_PACKET_SIZE
                if self.packet_cnt % 1000 == 0:
                    print("\rProgress ("+self.packet_cnt+"/"+packets+")")
                elif self.packet_cnt == packets:
                    print("done. Summary: "+str(faulty_cnt)+" of "+str(packets)+" were faulty")
        else:
            while self.next():
                if validate:
                    if not self.proof_order(self.packet, old_packet):
                        print(self.not_order_msg(self.packet, old_packet))
                        # break
                    old_packet = self.packet
                else:
                    self.add()

    def write(self, start=0, end=None, keep=False):
        if self.output_file:
            if end == None:
                end = len(self.packet_list)
            if start > end:
                raise HandlerError("failed write(): start index is greater than end index")
            if len(self.packet_list) >= end:
                for packet_idx in range(start,end):
                    self.output_file.write(self.packet_list[packet_idx].stream)
                if keep:
                    return
                self.packet_list.clear()
            else:
                raise HandlerError("failed write(): list out of range")

        else:
            raise HandlerError("failed write(): File not opened, can not write")


    # Horrible dirty function
    #@class_method
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


    #@class_method
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
