import socket
import argparse
import sys
from struct import pack, unpack

DEFAULT_PORT = 69
BLOCK_SIZE = 512
DEFAULT_TRANSFER_MODE = 'netascii'

OPCODE = {'RRQ': 1, 'WRQ': 2, 'DATA': 3, 'ACK': 4, 'ERROR': 5}
MODE = {'netascii': 0}

ERROR_CODE = {
    0: "Not defined, see error message (if any).",
    1: "File not found.",
    2: "Access violation.",
    3: "Disk full or allocation exceeded.",
    4: "Illegal TFTP operation.",
    5: "Unknown transfer ID.",
    6: "File already exists.",
    7: "No such user."
}


def send_rrq(filename, mode):
    format_str = f'>h{len(filename)}sb{len(mode)}sb'
    rrq_message = pack(format_str, OPCODE['RRQ'], filename.encode(), 0, mode.encode(), 0)
    sock.sendto(rrq_message, server_address)


def send_wrq(filename, mode):
    format_str = f'>h{len(filename)}sb{len(mode)}sb'
    wrq_message = pack(format_str, OPCODE['WRQ'], filename.encode(), 0, mode.encode(), 0)
    sock.sendto(wrq_message, server_address)


def send_ack(seq_num):
    ack_message = pack('>hh', OPCODE['ACK'], seq_num)
    sock.sendto(ack_message, server_address)


def receive_file(filename):
    file = open(filename, "wb")
    seq_number = 1

    while True:
        try:
            data, server = sock.recvfrom(516)
            opcode = unpack('>h', data[:2])[0]

            if opcode == OPCODE['DATA']:
                current_seq_number = unpack('>h', data[2:4])[0]

                if current_seq_number == seq_number:
                    file_block = data[4:]
                    file.write(file_block)

                    if len(file_block) < BLOCK_SIZE:
                        file.close()
                        break

                    send_ack(seq_number)
                    seq_number += 1
                elif current_seq_number < seq_number:
                    send_ack(current_seq_number)

        except socket.timeout:
            print("Timeout occurred while receiving data.")
            file.close()
            sys.exit(1)


def send_file(filename):
    try:
        file = open(filename, "rb")
        seq_number = 1
        data = file.read(BLOCK_SIZE)

        while data:
            format_str = f'>hh{len(data)}s'
            data_message = pack(format_str, OPCODE['DATA'], seq_number, data)

            sock.sendto(data_message, server_address)

            while True:
                try:
                    ack, server = sock.recvfrom(4)
                    opcode = unpack('>h', ack[:2])[0]
                    ack_seq_number = unpack('>h', ack[2:4])[0]

                    if opcode == OPCODE['ACK'] and ack_seq_number == seq_number:
                        break

                except socket.timeout:
                    sock.sendto(data_message, server_address)

            seq_number += 1
            data = file.read(BLOCK_SIZE)

        file.close()
    except FileNotFoundError:
        print("File not found.")
        sys.exit(1)


def handle_error(error_code):
    if error_code in ERROR_CODE:
        print(f"TFTP Error: {ERROR_CODE[error_code]}")
    else:
        print("Unknown TFTP Error.")


# Parse command line arguments
parser = argparse.ArgumentParser(description='TFTP client program')
parser.add_argument('host', help='Server IP address', type=str)
parser.add_argument('action', help='get or put a file', type=str, choices=['get', 'put'])
parser.add_argument('filename', help='name of file to transfer', type=str)
parser.add_argument('-p', '--port', dest='port', action='store', type=int, default=DEFAULT_PORT,
                    help='server port number (default: 69)')
args = parser.parse_args()

# Set server IP address and port
server_ip = args.host
server_port = args.port
server_address = (server_ip, server_port)

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(5)  # Set socket timeout to handle possible errors

# Set transfer mode
mode = DEFAULT_TRANSFER_MODE

# Send RRQ or WRQ based on the action
if args.action == 'get':
    send_rrq(args.filename, mode)
    receive_file(args.filename)
elif args.action == 'put':
    send_wrq(args.filename, mode)
    send_file(args.filename)

# Close the socket
sock.close()