import socket
import struct
import threading
import time

# ANSI color codes
class Colors:
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Constants
MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4

def listen_for_offers(udp_port):
    """Listens for server UDP offers."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(("", udp_port))

        print(f"{Colors.GREEN}[CLIENT]{Colors.WHITE} Listening for offers on UDP port {udp_port}...")

        while True:
            data, server_address = udp_socket.recvfrom(1024)
            try:
                cookie, msg_type, server_udp_port, server_tcp_port = struct.unpack('!IBHH', data)
                if cookie == MAGIC_COOKIE and msg_type == OFFER_MESSAGE_TYPE:
                    print(f"{Colors.CYAN}[OFFER RECEIVED]{Colors.WHITE} From {server_address}: UDP {server_udp_port}, TCP {server_tcp_port}")
                    return server_address[0], server_tcp_port
            except Exception as e:
                print(f"{Colors.RED}[ERROR]{Colors.WHITE} Invalid offer packet: {e}")


def tcp_transfer(server_ip, server_tcp_port, file_size):
    """Handles TCP file transfer."""
    start_time = time.time()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.connect((server_ip, server_tcp_port))
        tcp_socket.sendall(f"{file_size}\n".encode('utf-8'))

        data_received = 0
        while data_received < file_size:
            data = tcp_socket.recv(4096)
            if not data:
                break
            data_received += len(data)

    total_time = time.time() - start_time
    speed = (data_received * 8) / total_time  # bits per second
    print(f"{Colors.BLUE}[TCP FINISHED]{Colors.WHITE} Time: {total_time:.2f}s, Speed: {speed:.2f} bps")

def udp_transfer(server_ip, server_udp_port, file_size):
    """Handles UDP file transfer."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.settimeout(1)
        request_packet = struct.pack('!IBQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, file_size)
        udp_socket.sendto(request_packet, (server_ip, server_udp_port))

        data_received = 0
        packet_count = 0

        try:
            while True:
                data, _ = udp_socket.recvfrom(2048)
                packet_count += 1
                data_received += len(data) - 20  # Subtract header size
        except socket.timeout:
            pass

        print(f"{Colors.GREEN}[UDP FINISHED]{Colors.WHITE} Packets: {packet_count}, Bytes: {data_received}")

def main():
    """Main client function."""
    udp_port = 13117
    server_ip, server_tcp_port = listen_for_offers(udp_port)

    file_size = int(input("Enter file size (bytes): "))
    protocol = input("Choose protocol (tcp/udp): ").strip().lower()

    if protocol == "tcp":
        tcp_transfer(server_ip, server_tcp_port, file_size)
    elif protocol == "udp":
        udp_transfer(server_ip, udp_port, file_size)
    else:
        print(f"{Colors.YELLOW}[WARNING]{Colors.WHITE} Invalid protocol. Exiting.")

if __name__ == "__main__":
    main()
