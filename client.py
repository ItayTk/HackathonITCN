import socket
import struct
import threading
import time

# Constants
MAGIC_COOKIE = 0xabcddcba  # Unique identifier for packets to ensure validity
OFFER_MESSAGE_TYPE = 0x2  # Message type for server offers
REQUEST_MESSAGE_TYPE = 0x3  # Message type for client requests

# ANSI Colors for output formatting
RESET = "\033[0m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RED = "\033[31m"

class SpeedTestClient:
    def __init__(self, udp_port):
        self.udp_port = udp_port  # Port to listen for UDP offers
        self.server_info = None  # Store server details
        self.user_ready = threading.Event()  # Synchronization flag to ensure user input completion

    def start(self):
        # Start the thread to listen for server offers and prompt user input
        threading.Thread(target=self.listen_for_offers, daemon=True).start()
        self.user_input()
        if self.server_info:
            self.perform_speed_test()

    def listen_for_offers(self):
        # Listen for server offers via UDP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_socket.bind(('', self.udp_port))

            while True:
                data, addr = udp_socket.recvfrom(1024)  # Receive UDP packet
                magic_cookie, msg_type, server_udp_port, server_tcp_port = struct.unpack('!IBHH', data[:9])

                # Validate packet and display offer if user is ready
                if magic_cookie == MAGIC_COOKIE and msg_type == OFFER_MESSAGE_TYPE:
                    if self.user_ready.is_set():
                        print(f"{YELLOW}Received offer from {addr[0]}: UDP port {server_udp_port}, TCP port {server_tcp_port}{RESET}")
                        self.server_info = (addr[0], server_udp_port, server_tcp_port)

    def user_input(self):
        # Prompt the user for test parameters
        file_size = int(input("Enter file size (bytes): "))
        tcp_connections = int(input("Enter number of TCP connections: "))
        udp_connections = int(input("Enter number of UDP connections: "))

        print(f"{BLUE}File size: {file_size}, TCP connections: {tcp_connections}, UDP connections: {udp_connections}{RESET}")
        self.file_size = file_size
        self.tcp_connections = tcp_connections
        self.udp_connections = udp_connections
        self.user_ready.set()  # Allow processing of server offers

    def perform_speed_test(self):
        # Perform speed tests using TCP and UDP
        server_ip, server_udp_port, server_tcp_port = self.server_info

        # TCP Speed Test
        for i in range(self.tcp_connections):
            threading.Thread(target=self.tcp_speed_test, args=(server_ip, server_tcp_port, i), daemon=True).start()

        # UDP Speed Test
        for i in range(self.udp_connections):
            threading.Thread(target=self.udp_speed_test, args=(server_ip, server_udp_port, i), daemon=True).start()

    def tcp_speed_test(self, server_ip, server_tcp_port, connection_id):
        # Perform a TCP file transfer
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
                tcp_socket.connect((server_ip, server_tcp_port))
                tcp_socket.sendall(f"{self.file_size}\n".encode())
                start_time = time.time()
                received_data = tcp_socket.recv(self.file_size)
                end_time = time.time()

            transfer_time = end_time - start_time
            print(f"{GREEN}TCP transfer #{connection_id} completed in {transfer_time:.2f} seconds{RESET}")
        except Exception as e:
            print(f"{RED}TCP error on connection #{connection_id}: {e}{RESET}")

    def udp_speed_test(self, server_ip, server_udp_port, connection_id):
        # Perform a UDP file transfer
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
                request_packet = struct.pack('!IBQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, self.file_size)
                udp_socket.sendto(request_packet, (server_ip, server_udp_port))
                start_time = time.time()

                received_segments = 0
                while True:
                    data, _ = udp_socket.recvfrom(1024)
                    magic_cookie, msg_type, total_segments, current_segment = struct.unpack('!IBQQ', data[:21])
                    if magic_cookie == MAGIC_COOKIE and msg_type == PAYLOAD_MESSAGE_TYPE:
                        received_segments += 1
                    if received_segments >= total_segments:
                        break

                end_time = time.time()

            transfer_time = end_time - start_time
            print(f"{GREEN}UDP transfer #{connection_id} completed in {transfer_time:.2f} seconds{RESET}")
        except Exception as e:
            print(f"{RED}UDP error on connection #{connection_id}: {e}{RESET}")

if __name__ == "__main__":
    udp_port = int(input("Enter UDP port to listen on: "))
    client = SpeedTestClient(udp_port)
    client.start()
    while True:
        time.sleep(1)  # Keep the main thread alive
