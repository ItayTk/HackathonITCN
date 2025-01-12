import socket
import threading
import struct
import time
from tqdm import tqdm

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

def udp_offer_broadcast(server_udp_port, server_tcp_port):
    """Broadcasts UDP offers to clients."""

    #Set up an udp packet acts as a broadcast
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        offer_message = struct.pack('!IBHH', MAGIC_COOKIE, OFFER_MESSAGE_TYPE, server_udp_port, server_tcp_port) # !(Big endian) I(4) B(1) H(2) H(2) is the format and sizes in bytes of the components of the packet

        while True: # Repeated sending of the broadcast to the network
            udp_socket.sendto(offer_message, ('<broadcast>', server_udp_port))
            print(f"{Colors.CYAN}[UDP OFFER]{Colors.WHITE} Broadcast sent on UDP port {Colors.RED}{server_udp_port}")
            time.sleep(1)

def handle_tcp(server_ip, server_tcp_port):
    """Handles a TCP connection with a client."""
    #Set up a tcp packet
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.bind((server_ip, server_tcp_port))  # Bind to the specific IP and port
        tcp_socket.listen() # Put the socket into listening mode

        # Wait for incoming tcp connections
        connection, address = tcp_socket.accept()
        try:
            print(f"{Colors.GREEN}[TCP CONNECTION]{Colors.WHITE} Connected to {address}")
            file_size = int(connection.recv(1024).strip().decode('utf-8')) # Wait for arrival with a maximum size of 1024 bytes as well as decoding the data
            print(f"{Colors.CYAN}[TCP REQUEST]{Colors.WHITE} Client requested {file_size} bytes")

            # Sending the requested file size worth of data
            connection.sendall(b'X' * file_size) # Using sendall to transfer the data to ensure all the data will be sent
            print(f"{Colors.BLUE}[TCP TRANSFER]{Colors.WHITE} Sent {file_size} bytes to {address}")

        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.WHITE} {e}")

        finally:
            connection.close()

def handle_udp(server_ip, server_udp_port):
    """Handles a UDP connection with a client."""

    # Set up udp socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind((server_ip, server_udp_port))  # Bind to the specific IP and port

        while True:
            try:
                data, client_address = udp_socket.recvfrom(1024) # Wait for arrival with a maximum size of 1024 bytes

                # Silently reject and ignore packets that are too short
                if len(data) < 13:
                    continue

                # Unpack and validate the packet
                cookie, msg_type, file_size = struct.unpack('!IBQ', data)# !(Big Endian) I(4) B(1) Q(8) is the format and sizes in bytes of the components of the packet
                if cookie != MAGIC_COOKIE or msg_type != REQUEST_MESSAGE_TYPE: #Check that the message fields match ours
                    continue

                print(f"{Colors.BLUE}[UDP PROCESSING]{Colors.WHITE} Sending {file_size} bytes to {client_address}")

                # Sending data in segments
                total_segments = file_size // 1024 if file_size % 1024 != 0 else file_size // 1024 + 1
                bytes_to_send = file_size
                for i in tqdm(range(total_segments)):
                    payload = struct.pack('!IBQQ', MAGIC_COOKIE, PAYLOAD_MESSAGE_TYPE, total_segments, i) + b'X' * min(1024, bytes_to_send)# !(Big Endian) I(4) B(1) Q(8) Q(8) is the format and sizes in bytes of the component of the packet
                    bytes_to_send -= 1024
                    udp_socket.sendto(payload, client_address)

                print(f"{Colors.GREEN}[UDP TRANSFER]{Colors.WHITE} Completed transfer to {client_address}")
            except Exception as e:
                print(f"{Colors.RED}[ERROR]{Colors.WHITE} {e}")

def get_server_ip():
    """Get the primary IP address of the server."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))  # Use an external address to determine the outbound interface
            return s.getsockname()[0] # PC IP that was used in the connection
        except:
            return "127.0.0.1" # Local host address in case we couldn't connect or don't have an IP

def start_server():
    """Starts the server application."""

    #Set up server parameters
    server_ip = get_server_ip()
    server_udp_port = 30001
    server_tcp_port = 12345

    #Announce setup
    print(f"{Colors.MAGENTA}[SERVER START]{Colors.WHITE} Server started")
    print(f"{Colors.MAGENTA}[TCP]{Colors.WHITE} listening on {Colors.GREEN}{server_ip}{Colors.WHITE}:{Colors.RED}{server_tcp_port}")
    print(f"{Colors.MAGENTA}[UDP]{Colors.WHITE} listening on {Colors.GREEN}{server_ip}{Colors.WHITE}:{Colors.RED}{server_udp_port}")

    # Start UDP offer broadcast thread
    broadcast_thread = threading.Thread(target=udp_offer_broadcast, args=(server_udp_port, server_tcp_port), daemon=True)

    # UDP server setup
    udp_thread = threading.Thread(target=handle_udp, args=(server_ip, server_udp_port), daemon=True)

    # TCP server setup
    tcp_thread = threading.Thread(target=handle_tcp, args=(server_ip, server_tcp_port), daemon=True)

    #Start running the threads
    broadcast_thread.start()
    udp_thread.start()
    tcp_thread.start()

    #Make it so that the program wait for all of them to terminate
    broadcast_thread.join()
    udp_thread.join()
    tcp_thread.join()

if __name__ == "__main__":
    start_server()
