# Constants

# General constants for packet parsing
ETHII_HEADER = 14     # Bytes used for header in ETHII protocol (OSI-Layer 1)
IPV4_HEADER = 20      # Bytes used for header in IPV4 protocol (OSI-Layer 2)
UDP_HEADER = 8        # Bytes used for header in UDP protocol (OSI-Layer 2)

# CODIF constants
CODIF_HEADER = 64
CODIF_PAYLOAD = 7168
CODIF_BLOCKS_IN_PACKET = 128
CODIF_CHANNELS_IN_BLOCK = 7
CODIF_POLARIZATION = 2
CODIF_HEADER_TOTAL = ETHII_HEADER
    + IPV4_HEADER
    + UDP_HEADER
    + CODIF_HEADER
CODIF_PACKET_SIZE = CODIF_PAYLOAD + CODIF_HEADER
TOTAL_PACKET_SIZE = CODIF_HEADER_TOTAL + CODIF_PAYLOAD
