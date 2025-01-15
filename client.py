import socket
import struct
import threading
from datetime import datetime

# ANSI Color Definitions for better console readability
class Colors:
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# Protocol Constants
MAGIC_COOKIE = 0xabcddcba  # Unique identifier for protocol validation
MESSAGE_TYPE_OFFER = 0x2  # Indicates an offer message
MESSAGE_TYPE_REQUEST = 0x3  # Indicates a request message
MESSAGE_TYPE_PAYLOAD = 0x4  # Indicates a payload message

# Networking Constants
UDP_PORT = 30001  # Port for UDP broadcasts
BUFFER_SIZE = 1024  # Buffer size for receiving data
UDP_HEADER_SIZE = 21  # Header size for UDP payload packets

# Packet Formats
OFFER_MESSAGE_FORMAT = '!IBHH'  # Offer message format: cookie, type, UDP port, TCP port
REQUEST_MESSAGE_FORMAT = '!IbQ'  # Request message format: cookie, type, file size
PAYLOAD_MESSAGE_FORMAT = '!IbQQ'  # Payload message format: cookie, type, total segments, current segment

def listen_for_offers():
    """
    Listens for UDP broadcast offers from the server.
    Establishes connections based on valid offers.
    """
    try:
        # Set up a UDP socket to listen for broadcast messages
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow address reuse
            udp_socket.bind(('', UDP_PORT))  # Bind to the UDP port

            while True:
                # Receive UDP packet
                data, addr = udp_socket.recvfrom(BUFFER_SIZE)
                # Unpack the data according to the offer message format
                cookie, msg_type, udp_port, tcp_port = struct.unpack(OFFER_MESSAGE_FORMAT, data[:9])

                # Validate the received offer packet
                if cookie != MAGIC_COOKIE or msg_type != MESSAGE_TYPE_OFFER:
                    return  # Ignore invalid packets

                server_address = addr[0]  # Extract the server IP
                print(f"{Colors.CYAN}[Broadcast OFFER] {Colors.RESET}Received offer from {server_address}")

                # Run the speed test using the received offer details
                run_speed_test(server_address, udp_port, tcp_port, file_size, tcp_connections, udp_connections)
                return
    except Exception as e:
        print(f"{Colors.RED}[ERROR] Error while listening to offers: {e}")


def run_speed_test(server_address, udp_port, tcp_port, file_size, tcp_connections, udp_connections):
    """
    Orchestrates the speed test by spawning threads for TCP and UDP connections.
    """
    threads = []  # List to hold all connection threads

    # Start TCP connection threads
    for i in range(tcp_connections):
        thread = threading.Thread(target=tcp_download, args=(server_address, tcp_port, file_size, i + 1))
        threads.append(thread)
        thread.start()

    # Start UDP connection threads
    for i in range(udp_connections):
        thread = threading.Thread(target=udp_download, args=(server_address, udp_port, file_size, i + 1))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    print(f"{Colors.GREEN}[COMPLETE] {Colors.RESET}All transfers complete, listening to offer requests")


def tcp_download(server_address, tcp_port, file_size, connection_id):
    """
    Handles a single TCP connection for downloading data.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_address, tcp_port))  # Connect to the server
            tcp_socket.sendall(f"{file_size}\n".encode())  # Send requested file size

            start_time = datetime.now()
            received_data = 0

            # Calculate the number of iterations for the transfer
            iterations = file_size // BUFFER_SIZE if file_size % BUFFER_SIZE == 0 else (file_size // BUFFER_SIZE) + 1
            for _ in range(iterations):
                received_data += len(tcp_socket.recv(BUFFER_SIZE))  # Receive data chunks

            elapsed_time = (datetime.now() - start_time).total_seconds()
            speed = received_data * 8 / elapsed_time  # Calculate transfer speed

            print(f"{Colors.YELLOW}[TCP #{connection_id}] {Colors.RESET}Finished, total time: {elapsed_time:.2f} seconds, total speed: {speed:.2f} bits/second")
    except Exception as e:
        print(f"{Colors.RED}[TCP #{connection_id}] Error: {e}")


def udp_download(server_address, udp_port, file_size, connection_id):
    """
    Handles a single UDP connection for downloading data.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            # Send a request packet to the server
            request_packet = struct.pack(REQUEST_MESSAGE_FORMAT, MAGIC_COOKIE, MESSAGE_TYPE_REQUEST, file_size)
            udp_socket.sendto(request_packet, (server_address, udp_port))

            start_time = datetime.now()
            received_packets = 0
            total_packets = 0

            # Calculate the number of iterations required for the transfer
            iterations = file_size // BUFFER_SIZE if file_size % BUFFER_SIZE == 0 else (file_size // BUFFER_SIZE) + 1
            for _ in range(iterations):
                try:
                    udp_socket.settimeout(1.0)  # Set a timeout for the response
                    data, _ = udp_socket.recvfrom(BUFFER_SIZE)
                    # Unpack the received payload
                    magic_cookie, message_type, total_segments, current_segment = struct.unpack(PAYLOAD_MESSAGE_FORMAT, data[:UDP_HEADER_SIZE])
                    if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_PAYLOAD:
                        total_packets = total_segments
                        received_packets += 1
                except socket.timeout:
                    break

            elapsed_time = (datetime.now() - start_time).total_seconds()
            percentage_received = (received_packets / total_packets) * 100 if total_packets > 0 else 0
            speed = (total_packets * BUFFER_SIZE * 8) / elapsed_time  # Calculate transfer speed

            print(f"{Colors.CYAN}[UDP #{connection_id}] {Colors.RESET}Finished, total time: {elapsed_time:.2f} seconds, total speed: {speed:.2f} bits/second, percentage received: {percentage_received:.2f}%")
    except Exception as e:
        print(f"{Colors.RED}[UDP #{connection_id}] Error: {e}")


if __name__ == "__main__":
    print(f"""\033[93;1m   
___________________________________
|  ⣤⣤⣤⣤⣀⠀⠀⣤⣤⣤⣤⡄⠀⣤⣤⣤⣤⠀⣤⣤⣤⣤⣤      ⠀⠀⠀⠀ 
|  ⣿⡇⠀⠈⢻⣧⠀⣿⡇⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀  ⢠⡾⠃      ⠀⠀⠀ 
|  ⣿⡇⠀⠀⢸⣿⠀⣿⡟⠛⠛⠀⠀⣿⠛⠛⠓⠀⠀⣠⡿⠁⠀⠀⠀⠀⠀
|  ⣿⡇⢀⣀⣾⠏⠀⣿⡇⠀⠀⠀⠀⣿⠀⠀⠀⠀⣴⡟⠁⠀⠀⠀⠀⠀⠀
|  ⠛⠛⠛⠋⠁⠀⠀⠛⠛⠛⠛⠃⠀⠛⠛⠛⠛⠁⠛⠛⠛⠛⠛⠀
|  ⠀⠀⣿⣿⡄⠀⢸⣿⠀⢸⡇⠀⠀⠀⣿⠀⠛⠛⢻⡟⠛⠋⣴⡟⠋⠛⠃
|  ⠀⠀⣿⠘⣿⡄⢸⣿⠀⢸⡇⠀⠀⠀⣿⠀⠀⠀⢸⡇⠀⠀⠙⢿⣦⣄⠀
|  ⠀⠀⣿⠀⠈⢿⣾⣿⠀⢸⣇⠀⠀⠀⣿⠀⠀⠀⢸⡇⠀⠀⠀⠀⠈⢻⣷
|  ⠀⠀⠿⠀⠀⠈⠿⠿⠀⠈⠻⠶⠶⠾⠋⠀⠀⠀⠸⠇⠀⠀⠻⠶⠶⠿⠃
|___________________________________""")

    # Entry point for the client
    while True:
        try:
            print(f"{Colors.MAGENTA}[Data Entry]{Colors.RESET}")
            file_size = int(input("Enter file size to download (bytes): "))
            tcp_connections = int(input(f"Enter number of {Colors.YELLOW}TCP{Colors.RESET} connections: "))
            udp_connections = int(input(f"Enter number of {Colors.CYAN}UDP{Colors.RESET} connections: "))
            print(f"{Colors.GREEN}[CLIENT START] {Colors.RESET}Listening for offer requests")
            listen_for_offers()
        except ValueError:
            print(f"{Colors.RED}[ERROR] Invalid data")