import socket
import threading
import struct
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

def udp_offer_broadcast(server_udp_port, server_tcp_port):
    """Broadcasts UDP offers to clients."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        offer_message = struct.pack('!IBHH', MAGIC_COOKIE, OFFER_MESSAGE_TYPE, server_udp_port, server_tcp_port)

        while True:
            udp_socket.sendto(offer_message, ('<broadcast>', server_udp_port))
            print(f"{Colors.CYAN}[UDP OFFER]{Colors.WHITE} Broadcast sent on UDP port {Colors.RED}{server_udp_port}")
            time.sleep(1)

def handle_client_tcp(connection, address):
    """Handles a TCP connection with a client."""
    try:
        print(f"{Colors.GREEN}[TCP CONNECTION]{Colors.WHITE} Connected to {address}")
        file_size = int(connection.recv(1024).strip().decode('utf-8'))
        print(f"{Colors.CYAN}[TCP REQUEST]{Colors.WHITE} Client requested {file_size} bytes")

        # Sending the requested file size worth of data
        connection.sendall(b'X' * file_size)
        print(f"{Colors.BLUE}[TCP TRANSFER]{Colors.WHITE} Sent {file_size} bytes to {address}")

    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.WHITE} {e}")

    finally:
        connection.close()

def handle_client_udp(server_socket):
    """Handles a UDP connection with a client."""
    while True:
        try:
            data, client_address = server_socket.recvfrom(1024)

            # Reject and ignore short packets silently
            if len(data) < 13:
                continue

            # Unpack and validate the packet
            cookie, msg_type, file_size = struct.unpack('!IBQ', data)
            if cookie != MAGIC_COOKIE or msg_type != REQUEST_MESSAGE_TYPE:
                continue

            print(f"{Colors.BLUE}[UDP PROCESSING]{Colors.WHITE} Sending {file_size} bytes to {client_address}")

            # Sending data in segments
            total_segments = file_size // 1024
            for i in range(total_segments):
                payload = struct.pack('!IBQQ', MAGIC_COOKIE, PAYLOAD_MESSAGE_TYPE, total_segments, i) + b'X' * 1024
                server_socket.sendto(payload, client_address)

            print(f"{Colors.GREEN}[UDP TRANSFER]{Colors.WHITE} Completed transfer to {client_address}")
        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.WHITE} {e}")

def get_server_ip():
    """Get the primary IP address of the server."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))  # Use an external address to determine the outbound interface
        return s.getsockname()[0]

def start_server():
    """Starts the server application."""
    server_ip = get_server_ip()
    server_udp_port = 13117
    server_tcp_port = 12345

    print(f"{Colors.MAGENTA}[SERVER START]{Colors.WHITE} Server started")
    print(f"{Colors.MAGENTA}[TCP]{Colors.WHITE} listening on {Colors.GREEN}{server_ip}:{Colors.RED}{server_tcp_port}{Colors.WHITE}")
    print(f"{Colors.MAGENTA}[UDP]{Colors.WHITE} listening on {Colors.GREEN}{server_ip}:{Colors.RED}{server_udp_port}{Colors.WHITE}")

    # Start UDP offer broadcast thread
    threading.Thread(target=udp_offer_broadcast, args=(server_udp_port, server_tcp_port), daemon=True).start()

    # TCP server setup
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.bind((server_ip, server_tcp_port))  # Bind to the specific IP and port
        tcp_socket.listen()

        # UDP server setup
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.bind((server_ip, server_udp_port))  # Bind to the specific IP and port

            threading.Thread(target=handle_client_udp, args=(udp_socket,), daemon=True).start()

            # Accept TCP connections
            while True:
                conn, addr = tcp_socket.accept()
                threading.Thread(target=handle_client_tcp, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
