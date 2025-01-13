import socket
import struct
import threading
import time
from datetime import datetime
from logging import exception

import colorama


# ANSI Color Definitions
class Colors:
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


# Constants for the protocol
MAGIC_COOKIE = 0xabcddcba
MESSAGE_TYPE_OFFER = 0x2
MESSAGE_TYPE_REQUEST = 0x3
MESSAGE_TYPE_PAYLOAD = 0x4
UDP_PORT = 30001  # Listening port for UDP broadcasts
BUFFER_SIZE = 1024

def listen_for_offers():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_socket.bind(('', UDP_PORT))

            while True:
                print(f"{Colors.MAGENTA}[Data Entry]{Colors.RESET}")
                file_size = int(input("Enter file size to download (bytes): "))
                tcp_connections = int(input(f"Enter number of {Colors.YELLOW}TCP{Colors.RESET} connections: "))
                udp_connections = int(input(f"Enter number of {Colors.CYAN}UDP{Colors.RESET} connections: "))
                print(f"{Colors.GREEN}[CLIENT START] {Colors.RESET}Listening for offer requests")

                data, addr = udp_socket.recvfrom(BUFFER_SIZE)
                handle_offer(data, addr, file_size, tcp_connections, udp_connections)
    except Exception as e:
        print(f"{Colors.RED}[ERROR] Error in listening for offers: {e}")
        listen_for_offers()

def handle_offer(data, addr, file_size, tcp_connections, udp_connections):
    try:
        magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!IbHH', data[:9])
        if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_OFFER:
            server_address = addr[0]
            print(f"{Colors.CYAN}[Broadcast OFFER] {Colors.RESET}Received offer from {server_address}")
            run_speed_test(server_address, udp_port, tcp_port, file_size, tcp_connections, udp_connections)
    except Exception as e:
        print(f"{Colors.RED}[ERROR] Error in handling offer: {e}")

def run_speed_test(server_address, udp_port, tcp_port, file_size, tcp_connections, udp_connections):

    threads = []

    for i in range(tcp_connections):
        thread = threading.Thread(target=tcp_download, args=(server_address, tcp_port, file_size, i + 1))
        threads.append(thread)
        thread.start()

    for i in range(udp_connections):
        thread = threading.Thread(target=udp_download, args=(server_address, udp_port, file_size, i + 1))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print(f"{Colors.GREEN}[COMPLETE] {Colors.RESET}All transfers complete, listening to offer requests")

def tcp_download(server_address, tcp_port, file_size, connection_id):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_address, tcp_port))
            tcp_socket.sendall(f"{file_size}\n".encode())

            start_time = datetime.now()
            received_data = 0
            while received_data < file_size:
                received_data += len(tcp_socket.recv(BUFFER_SIZE))
            elapsed_time = (datetime.now() - start_time).total_seconds()

            speed = received_data * 8 / elapsed_time
            print(f"{Colors.YELLOW}[TCP #{connection_id}] {Colors.RESET}Finished, total time: {elapsed_time:.2f} seconds, total speed: {speed:.2f} bits/second")
    except Exception as e:
        print(f"{Colors.RED}[TCP #{connection_id}] Error: {e}")

def udp_download(server_address, udp_port, file_size, connection_id):
    header_size = 21
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            request_packet = struct.pack('!IbQ', MAGIC_COOKIE, MESSAGE_TYPE_REQUEST, file_size)
            udp_socket.sendto(request_packet, (server_address, udp_port))

            start_time = datetime.now()
            received_packets = 0
            total_packets = 0

            while True:
                try:
                    udp_socket.settimeout(1.0)
                    data, _ = udp_socket.recvfrom(BUFFER_SIZE)
                    magic_cookie, message_type, total_segments, current_segment = struct.unpack('!IbQQ', data[:header_size])
                    if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_PAYLOAD:
                        total_packets = total_segments
                        received_packets += 1
                except socket.timeout:
                    break

            elapsed_time = (datetime.now() - start_time).total_seconds()
            percentage_received = (received_packets / total_packets) * 100 if total_packets > 0 else 0
            speed = (received_packets * file_size * 8) / elapsed_time

            print(f"{Colors.CYAN}[UDP #{connection_id}] {Colors.RESET}Finished, total time: {elapsed_time:.2f} seconds, total speed: {speed:.2f} bits/second, percentage received: {percentage_received:.2f}%")
    except Exception as e:
        print(f"{Colors.RED}[UDP #{connection_id}] Error: {e}")


if __name__ == "__main__":

    listen_for_offers()
