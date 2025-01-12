import socket
import struct
import threading
import time

# Constants
MAGIC_COOKIE = 0xabcddcba  # Unique identifier for packets to ensure validity
OFFER_MESSAGE_TYPE = 0x2  # Message type for server offers

# ANSI Colors for output formatting
RESET = "\033[0m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RED = "\033[31m"

class SpeedTestClient:
    def __init__(self, udp_port):
        self.udp_port = udp_port  # Port to listen for UDP offers
        self.user_ready = threading.Event()  # Synchronization flag to ensure user input completion

    def start(self):
        # Start the thread to listen for server offers and prompt user input
        threading.Thread(target=self.listen_for_offers, daemon=True).start()
        self.user_input()

    def listen_for_offers(self):
        # Listen for server offers via UDP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_socket.bind(("", self.udp_port))

            while True:
                data, addr = udp_socket.recvfrom(1024)  # Receive UDP packet
                magic_cookie, msg_type, server_udp_port, server_tcp_port = struct.unpack('!IBHH', data[:9])

                # Validate packet and display offer if user is ready
                if magic_cookie == MAGIC_COOKIE and msg_type == OFFER_MESSAGE_TYPE:
                    if self.user_ready.is_set():
                        print(f"{YELLOW}Received offer from {addr[0]}: UDP port {server_udp_port}, TCP port {server_tcp_port}{RESET}")

    def user_input(self):
        # Prompt the user for test parameters
        file_size = int(input("Enter file size (bytes): "))
        tcp_connections = int(input("Enter number of TCP connections: "))
        udp_connections = int(input("Enter number of UDP connections: "))

        print(f"{BLUE}File size: {file_size}, TCP connections: {tcp_connections}, UDP connections: {udp_connections}{RESET}")
        self.user_ready.set()  # Allow processing of server offers

if __name__ == "__main__":
    udp_port = int(input("Enter UDP port to listen on: "))
    client = SpeedTestClient(udp_port)
    client.start()
    while True:
        time.sleep(1)  # Keep the main thread alive
