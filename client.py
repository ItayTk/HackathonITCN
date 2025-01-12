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

def log(message, color=Colors.WHITE):
    print(f"{color}{message}{Colors.WHITE}")

# Constants for the protocol
MAGIC_COOKIE = 0xabcddcba
MESSAGE_TYPE_OFFER = 0x2
MESSAGE_TYPE_REQUEST = 0x3
MESSAGE_TYPE_PAYLOAD = 0x4
UDP_PORT = 13117  # Listening port for UDP broadcasts

def listen_for_offers(running):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_socket.bind(('', UDP_PORT))

            while running:
                data, addr = udp_socket.recvfrom(1024)
                handle_offer(data, addr, running)
    except Exception as e:
        log(f"Error in listening for offers: {e}", Colors.RED)

def handle_offer(data, addr, running):
    try:
        magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!IbHH', data[:9])
        if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_OFFER:
            server_address = addr[0]
            log(f"Received offer from {server_address}", Colors.CYAN)
            run_speed_test(server_address, udp_port, tcp_port, running)
    except Exception as e:
        log(f"Error in handling offer: {e}", Colors.RED)

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

    log("All transfers complete, listening to offer requests", Colors.GREEN)

def tcp_download(server_address, tcp_port, file_size, connection_id):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_address, tcp_port))
            tcp_socket.sendall(f"{file_size}\n".encode('utf-8'))

            start_time = datetime.now()
            received_data = tcp_socket.recv(file_size)
            elapsed_time = (datetime.now() - start_time).total_seconds()

            speed = len(received_data) * 8 / elapsed_time
            log(f"TCP transfer #{connection_id} finished, total time: {elapsed_time:.2f} seconds, total speed: {speed:.2f} bits/second", Colors.YELLOW)
    except Exception as e:
        log(f"TCP transfer #{connection_id} error: {e}", Colors.RED)

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

            log(f"UDP transfer #{connection_id} finished, total time: {elapsed_time:.2f} seconds, total speed: {speed:.2f} bits/second, percentage of packets received successfully: {percentage_received:.2f}%", Colors.CYAN)
    except Exception as e:
        log(f"UDP transfer #{connection_id} error: {e}", Colors.RED)

def main():
    running = True
    log("Client started, listening for offer requests...", Colors.GREEN)
    listen_thread = threading.Thread(target=listen_for_offers, args=(running,))
    listen_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Shutting down client...", Colors.RED)
        running = False
        listen_thread.join()

if __name__ == "__main__":
    main()
