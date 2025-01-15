import socket
import threading
import struct
import time

from tqdm import tqdm
import netifaces


# ANSI color codes
class Colors:
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# Constants
MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4
BUFFER = 1024


def get_server_ip():
    """Get the primary IP address of the server."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))  # Use an external address to determine the outbound interface
            return s.getsockname()[0] # PC IP that was used in the connection
        except:
            return "127.0.0.1" # Local host address in case we couldn't connect or don't have an IP


def get_server_broadcast_ip(server_ip):
    """Get the netmask that belongs to the server ip."""
    if str(server_ip) == "127.0.0.1": # In case server IP retrieval failed
        return "127.255.255.255"
    for interface in netifaces.interfaces(): # Go through the network interfaces of the device and check which one has our IP
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addrs: # Check if the interface has an IPv4 address assigned
            ipv4_info = addrs[netifaces.AF_INET][0]
            if str(ipv4_info['addr']) == str(server_ip): # Check if the interface IP matches our own in case of multiple active interfaces
                return str(ipv4_info['broadcast'])


def udp_offer_broadcast(server_udp_port, server_tcp_port, server_broadcast_ip):
    """Broadcasts UDP offers to clients."""

    #Set up an udp packet acts as a broadcast
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        offer_message = struct.pack('!IBHH', MAGIC_COOKIE, OFFER_MESSAGE_TYPE, server_udp_port, server_tcp_port) # !(Big endian) I(4) B(1) H(2) H(2) is the format and sizes in bytes of the components of the packet

        while True: # Repeated sending of the broadcast to the network
            udp_socket.sendto(offer_message, (server_broadcast_ip, server_udp_port))
            print(f"{Colors.CYAN}[UDP OFFER]{Colors.RESET} Broadcast sent on {Colors.GREEN}UDP{Colors.RESET} port {Colors.RED}{server_udp_port}")
            time.sleep(1)


def listen_to_udp(server_ip, server_udp_port):
    """Handles a UDP connection start with a client."""

    # Set up udp socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind((server_ip, server_udp_port))  # Bind to the specific IP and port

        while True:
            try:
                data, client_address = udp_socket.recvfrom(BUFFER) # Wait for arrival with a maximum size of 1024 bytes

                # Silently reject and ignore packets that are too short
                if len(data) < 13:
                    continue

                # Unpack and validate the packet
                cookie, msg_type, file_size = struct.unpack('!IBQ', data)# !(Big Endian) I(4) B(1) Q(8) is the format and sizes in bytes of the components of the packet
                if cookie != MAGIC_COOKIE or msg_type != REQUEST_MESSAGE_TYPE: #Check that the message fields match ours
                    continue
                threading.Thread(target=handle_udp, args=(client_address, file_size), daemon=True).start()
            except Exception as e:
                print(f"{Colors.RED}[UDP ERROR] {e} {Colors.RESET}")


def handle_udp(client_address, file_size):
    """Handles a UDP message transmission with a client."""

    data_buffer = BUFFER - 21
    print(f"{Colors.BLUE}[UDP PROCESSING]{Colors.RESET} Sending {file_size} bytes to {client_address}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            # Sending data in segments
            total_segments = file_size // data_buffer if file_size % data_buffer == 0 else (file_size // data_buffer) + 1
            for i in tqdm(range(total_segments)):
                bytes_to_send = min(file_size,data_buffer)
                payload = struct.pack("!IBQQ", MAGIC_COOKIE, PAYLOAD_MESSAGE_TYPE, total_segments, i) + b'X' *bytes_to_send  # !(Big Endian) I(4) B(1) Q(8) Q(8) is the format and sizes in bytes of the component of the packet
                file_size -= data_buffer
                udp_socket.sendto(payload, client_address)

            print(f"{Colors.GREEN}[UDP TRANSFER]{Colors.RESET} Completed transfer to {client_address}")
    except Exception as e:
        print(f"{Colors.RED}[UDP ERROR] {e} {Colors.RESET}")


def listen_to_tcp(server_ip, server_tcp_port):
    """Handles a TCP connection establishment with a client."""
    #Set up a tcp packet
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.bind((server_ip, server_tcp_port))  # Bind to the specific IP and port
        tcp_socket.listen() # Put the socket into listening mode
        while True:
            # Wait for incoming tcp connections
            connection, client_address = tcp_socket.accept()
            try:
                print(f"{Colors.GREEN}[TCP CONNECTION]{Colors.RESET} Connected to {client_address}")
                file_size = int(connection.recv(BUFFER).decode().strip()) # Wait for arrival with a maximum size of 1024 bytes as well as decoding the data
                print(f"{Colors.CYAN}[TCP REQUEST]{Colors.RESET} Client requested {file_size} bytes")

                threading.Thread(target=handle_tcp, args=(connection, client_address, file_size), daemon=True).start()

            except Exception as e:
                print(f"{Colors.RED}[TCP ERROR] {e} {Colors.RESET}")


def handle_tcp(connection, client_address, file_size):
    """Handles a TCP message transfer with a client."""

    try:
        # Sending the requested file size worth of data
        connection.sendall(b'X' * file_size)  # Using sendall to transfer the data to ensure all the data will be sent
        print(f"{Colors.BLUE}[TCP TRANSFER]{Colors.RESET} Sent {file_size} bytes to {client_address}")
    except Exception as e:
        print(f"{Colors.RED}[TCP ERROR] {e} {Colors.RESET}")

    finally:
        connection.close()


def start_server():
    """Starts the server application."""

    #Set up server parameters
    server_ip = get_server_ip()
    server_broadcast_ip = get_server_broadcast_ip(server_ip)
    server_udp_port = 30001
    server_tcp_port = 12345

    #Announce setup
    print(f"{Colors.MAGENTA}[SERVER START]{Colors.RESET} Server started")
    print(f"{Colors.MAGENTA}[TCP]{Colors.RESET} listening on \033[92;1m{server_ip}{Colors.RESET}:{Colors.RED}{server_tcp_port}")
    print(f"{Colors.MAGENTA}[UDP]{Colors.RESET} listening on \033[92;1m{server_ip}{Colors.RESET}:{Colors.RED}{server_udp_port}")

    # Start UDP offer broadcast thread
    broadcast_thread = threading.Thread(target=udp_offer_broadcast, args=(server_udp_port, server_tcp_port,server_broadcast_ip), daemon=True)

    # UDP server setup
    udp_listen_thread = threading.Thread(target=listen_to_udp, args=(server_ip, server_udp_port), daemon=True)

    # TCP server setup
    tcp_listen_thread = threading.Thread(target=listen_to_tcp, args=(server_ip, server_tcp_port), daemon=True)

    #Start running the threads
    broadcast_thread.start()
    udp_listen_thread.start()
    tcp_listen_thread.start()

    #Make it so that the program wait for all of them to terminate
    broadcast_thread.join()
    udp_listen_thread.join()
    tcp_listen_thread.join()


if __name__ == "__main__":
    start_server()
