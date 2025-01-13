import socket
import struct
import threading
import time
from datetime import datetime

# ANSI Color Definitions
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


# Constants for the protocol
MAGIC_COOKIE = 0xabcddcba
MESSAGE_TYPE_OFFER = 0x2
MESSAGE_TYPE_REQUEST = 0x3
MESSAGE_TYPE_PAYLOAD = 0x4
UDP_PORT = 30001  # Listening port for UDP broadcasts

def listen_for_offers(running):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_socket.bind(('', UDP_PORT))

            while running:
                data, addr = udp_socket.recvfrom(1024)
                handle_offer(data, addr, running)
    except Exception as e:
        print(f"{Colors.RED}[ERROR] Error in listening for offers: {e}")

def handle_offer(data, addr, running):
    try:
        magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!IbHH', data[:9])
        if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_OFFER:
            server_address = addr[0]
            print(f"{Colors.CYAN}[UDP OFFER] {Colors.WHITE}Received offer from {server_address}")
            run_speed_test(server_address, udp_port, tcp_port, running)
    except Exception as e:
        print(f"{Colors.RED}[ERROR] Error in handling offer: {e}")

def run_speed_test(server_address, udp_port, tcp_port, running):
    file_size = int(input("Enter file size to download (bytes): "))
    tcp_connections = int(input("Enter number of TCP connections: "))
    udp_connections = int(input("Enter number of UDP connections: "))

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

    print(f"{Colors.GREEN}[COMPLETE] {Colors.WHITE}All transfers complete, listening to offer requests")

def tcp_download(server_address, tcp_port, file_size, connection_id):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_address, tcp_port))
            tcp_socket.sendall(f"{file_size}\n".encode('utf-8'))

            start_time = datetime.now()
            received_data = tcp_socket.recv(file_size)
            elapsed_time = (datetime.now() - start_time).total_seconds()

            speed = len(received_data) * 8 / elapsed_time
            print(f"{Colors.YELLOW}[TCP #{connection_id}] {Colors.WHITE}Finished, total time: {elapsed_time:.2f} seconds, total speed: {speed:.2f} bits/second")
    except Exception as e:
        print(f"{Colors.RED}[TCP #{connection_id}] Error: {e}")

def udp_download(server_address, udp_port, file_size, connection_id):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            request_packet = struct.pack('!IbQ', MAGIC_COOKIE, MESSAGE_TYPE_REQUEST, file_size)
            udp_socket.sendto(request_packet, (server_address, udp_port))

            start_time = datetime.now()
            received_packets = 0
            total_packets = 0

            while True:
                udp_socket.settimeout(1.0)
                try:
                    data, _ = udp_socket.recvfrom(1024)
                    magic_cookie, message_type, total_segments, current_segment = struct.unpack('!IbQQ', data[:21])
                    if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_PAYLOAD:
                        total_packets = total_segments
                        received_packets += 1
                except socket.timeout:
                    break

            elapsed_time = (datetime.now() - start_time).total_seconds()
            percentage_received = (received_packets / total_packets) * 100 if total_packets > 0 else 0
            speed = (received_packets * 1024 * 8) / elapsed_time

            print(f"{Colors.CYAN}[UDP #{connection_id}] {Colors.WHITE}Finished, total time: {elapsed_time:.2f} seconds, total speed: {speed:.2f} bits/second, percentage received: {percentage_received:.2f}%")
    except Exception as e:
        print(f"{Colors.RED}[UDP #{connection_id}] Error: {e}")


if __name__ == "__main__":
    running = True
    print(f"{Colors.GREEN}[CLIENT START] {Colors.WHITE}Listening for offer requests")
    listen_thread = threading.Thread(target=listen_for_offers, args=(running,))
    listen_thread.start()
    listen_thread.join()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"{Colors.RED}[SHUTDOWN] {Colors.WHITE}Shutting down client...")
        running = False
        listen_thread.join()
