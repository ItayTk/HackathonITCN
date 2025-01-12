import socket
import struct
import threading
import time

# Constants
MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2

# ANSI Colors
RESET = "\033[0m"
GREEN = "\033[32m"
CYAN = "\033[36m"

class SpeedTestServer:
    def __init__(self, udp_port, tcp_port):
        self.udp_port = udp_port
        self.tcp_port = tcp_port
        self.running = True

    def start(self):
        threading.Thread(target=self.broadcast_offers, daemon=True).start()
        self.start_tcp_server()

    def broadcast_offers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            offer_packet = struct.pack('!IBHH', MAGIC_COOKIE, OFFER_MESSAGE_TYPE, self.udp_port, self.tcp_port)

            while self.running:
                udp_socket.sendto(offer_packet, ('<broadcast>', self.udp_port))
                print(f"{GREEN}Broadcasting offer on UDP port {self.udp_port}{RESET}")
                time.sleep(1)

    def start_tcp_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.bind(("", self.tcp_port))
            tcp_socket.listen()
            print(f"{CYAN}Server started, listening on TCP port {self.tcp_port}{RESET}")

            while self.running:
                client_socket, address = tcp_socket.accept()
                print(f"{GREEN}Accepted connection from {address}{RESET}")
                threading.Thread(target=self.handle_tcp_client, args=(client_socket,), daemon=True).start()

    def handle_tcp_client(self, client_socket):
        try:
            with client_socket:
                data = client_socket.recv(1024).decode()
                file_size = int(data.strip())
                print(f"{CYAN}Received file size request: {file_size} bytes{RESET}")
                client_socket.sendall(b"\x00" * file_size)  # Sending requested data
                print(f"{GREEN}Sent {file_size} bytes to client{RESET}")
        except Exception as e:
            print(f"Error handling TCP client: {e}")

if __name__ == "__main__":
    udp_port = int(input("Enter UDP port: "))
    tcp_port = int(input("Enter TCP port: "))
    server = SpeedTestServer(udp_port, tcp_port)
    server.start()
    while True:
        time.sleep(1)