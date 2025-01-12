import socket
import struct
import threading
import time

# Constants
MAGIC_COOKIE = 0xabcddcba  # Unique identifier for packets to ensure validity
OFFER_MESSAGE_TYPE = 0x2  # Message type for server offers
REQUEST_MESSAGE_TYPE = 0x3  # Message type for client requests
PAYLOAD_MESSAGE_TYPE = 0x4  # Message type for data payloads

# ANSI Colors for output formatting
RESET = "\033[0m"
GREEN = "\033[32m"
CYAN = "\033[36m"

class SpeedTestServer:
    def __init__(self, udp_port, tcp_port):
        self.udp_port = udp_port  # Port for broadcasting UDP offers
        self.tcp_port = tcp_port  # Port for handling TCP connections
        self.running = True  # Flag to keep the server running

    def start(self):
        # Get the server's IP address to display on startup
        server_ip = self.get_server_ip()
        print(f"{CYAN}Server started, listening on IP address {server_ip}{RESET}")
        # Start the thread to broadcast UDP offers and the TCP/UDP server
        threading.Thread(target=self.broadcast_offers, daemon=True).start()
        threading.Thread(target=self.start_udp_server, daemon=True).start()
        self.start_tcp_server()

    def get_server_ip(self):
        # Determine the server's IP address dynamically
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
            except Exception:
                return "127.0.0.1"  # Fallback to localhost if unable to determine

    def broadcast_offers(self):
        # Broadcast UDP packets to announce the server's presence
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            offer_packet = struct.pack('!IBHH', MAGIC_COOKIE, OFFER_MESSAGE_TYPE, self.udp_port, self.tcp_port)

            while self.running:
                udp_socket.sendto(offer_packet, ('<broadcast>', self.udp_port))
                print(f"{GREEN}Broadcasting offer on UDP port {self.udp_port}{RESET}")
                time.sleep(1)  # Wait 1 second between broadcasts

    def start_tcp_server(self):
        # Start a TCP server to handle file size requests
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.bind(('', self.tcp_port))
            tcp_socket.listen()
            print(f"{CYAN}Server started, listening on TCP port {self.tcp_port}{RESET}")

            while self.running:
                client_socket, address = tcp_socket.accept()
                print(f"{GREEN}Accepted connection from {address}{RESET}")
                threading.Thread(target=self.handle_tcp_client, args=(client_socket,), daemon=True).start()

    def handle_tcp_client(self, client_socket):
        # Handle a single TCP client request
        try:
            with client_socket:
                data = client_socket.recv(1024).decode()  # Receive file size from client
                file_size = int(data.strip())
                print(f"{CYAN}Received TCP file size request: {file_size} bytes{RESET}")
                client_socket.sendall(b"\x00" * file_size)  # Send requested amount of data
                print(f"{GREEN}Sent {file_size} bytes to client via TCP{RESET}")
        except Exception as e:
            print(f"Error handling TCP client: {e}")

    def start_udp_server(self):
        # Start a UDP server to handle client requests
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.bind(('', self.udp_port))
            print(f"{CYAN}Server started, listening on UDP port {self.udp_port}{RESET}")

            while self.running:
                data, addr = udp_socket.recvfrom(1024)
                magic_cookie, msg_type, file_size = struct.unpack('!IBQ', data)

                if magic_cookie == MAGIC_COOKIE and msg_type == REQUEST_MESSAGE_TYPE:
                    print(f"{CYAN}Received UDP file size request: {file_size} bytes from {addr}{RESET}")
                    threading.Thread(target=self.handle_udp_client, args=(udp_socket, addr, file_size), daemon=True).start()

    def handle_udp_client(self, udp_socket, addr, file_size):
        # Send data in UDP packets to the client
        total_segments = (file_size + 1023) // 1024  # Calculate total number of segments
        for segment in range(total_segments):
            payload = struct.pack('!IBQQ', MAGIC_COOKIE, PAYLOAD_MESSAGE_TYPE, total_segments, segment) + b"\x00" * min(1024, file_size)
            udp_socket.sendto(payload, addr)
            file_size -= 1024
        print(f"{GREEN}Sent {total_segments} segments to {addr} via UDP{RESET}")

if __name__ == "__main__":
    udp_port = int(input("Enter UDP port: "))
    tcp_port = int(input("Enter TCP port: "))
    server = SpeedTestServer(udp_port, tcp_port)
    server.start()
    while True:
        time.sleep(1)  # Keep the main thread alive
