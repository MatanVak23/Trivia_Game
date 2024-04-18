import json
import os
from struct import *
import socket
import random
from time import *
import threading
import time
import select
from Configuration import *
# from TriviaGame import TriviaGame


class Server:
    """
       Constructor
       :return: None
       """

    def __init__(self):
        self.UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.my_ip = self.get_wifi_ip_windows()
        self.my_port = 13117
        self.broadcasting = False
        self.game_on = False
        self.number_of_clients = [0]
        self.my_clients = []
        self.lock = threading.Lock()
        self.server_print_lock = threading.Lock()
        self.server_print_counter = 0
        self.tcp_port = None
        self.TCP_socket_server = None
        self.qa_pairs = self.read_questions_answers_file()
        self.searching_client_flag = threading.Event()
        self.game_over_event = threading.Event()
        self.nick_names = None
        self.begin_time = None
        # Initialize statistics variables for the current session
        self.number_of_games = 0
        self.total_players = 0
        self.total_game_time = 0
        self.total_questions_asked = 0
        self.fastest_game_time = float('inf')
        self.longest_game_time = 0
        self.valid_answers = {"T": 0, "Y": 0, "1": 0, "F": 0, "N": 0, "0": 0}
        self.valid_answers_lock = threading.Lock()
        self.json_lock = threading.Lock()

    def initialize_server(self):
        """
           Initialize server sockets and start TCP server.
           :return: None
           """
        # Set socket options for UDP broadcasting
        if self.my_ip is None:
            print("Error: Unable to retrieve valid IP address.")
            return
        self.UDP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.UDP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            self.UDP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            print("")
        # Shuffle the list of nicknames for client assignment
        self.nick_names = NICK_NAMES
        random.shuffle(self.nick_names)
        self.UDP_socket.settimeout(0.2)
        try:
            if not self.is_socket_bound(self.UDP_socket):
                print(COLORS_FOR_PLAYERS[
                          "Zinedine Zidane"] + "Football King server started, listening on IP address " + self.my_ip +
                      COLORS_FOR_PLAYERS["default"])
                self.UDP_socket.bind((self.my_ip, self.my_port))
            # Bind TCP socket for client connections
            if not self.TCP_socket_server or not self.is_socket_bound(self.TCP_socket_server):
                if self.TCP_socket_server:
                    self.TCP_socket_server.close()
                self.TCP_socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.TCP_socket_server.bind((self.my_ip, 0))  # 0 indicate any available port
                self.tcp_port = self.TCP_socket_server.getsockname()[1]  # get the dynamic port signed by the os
                print("TCP server socket initialized.")
        except OSError as e:
            print(f"Error binding socket: {e}")
            return

    def is_socket_bound(self, sock):
        """
           Check if a socket is bound.
           :param sock: Socket object
           :return: Boolean indicating whether the socket is bound
           """
        try:
            sock.getsockname()
            return True
        except OSError:
            return False

def broadcast():
    while True:
        # print("Server in broadcast")
        udp_format = 'LBh'
        # tcp_port = 12351
        tcp_port = 13119
        packed = pack(udp_format, 0xabcddcba, 0x2, tcp_port)
        try:
            UDP_socket.sendto(packed, ('<broadcast>', my_port))
        except OSError as e:
            continue
        sleep(1)

def searching_client():
    global now  # Declare 'now' as a global variable
    global number_of_clients
    global my_clients
    global last_connection_time

    while number_of_clients[0] < 2:
        TCP_socket_server.listen(2)
        print("[*] Listening on %s:%d" % (my_ip, tcp_port))
        client_tcp, address_tcp = TCP_socket_server.accept()
        print("[*] Accepted connection from: %s:%d" % (address_tcp[0], address_tcp[1]))
        request = client_tcp.recv(1024)
        print("[*] Received: %s" % request)
        client_tcp.send('ACK!'.encode('utf-8'))
        client_name = client_tcp.recv(1024)
        lock.acquire()
        number_of_clients[0] += 1
        my_clients.append((client_tcp, address_tcp, client_name.decode('utf-8')))
        lock.release()
        last_connection_time = time.time()

    print("GOT TWO CONNECTIONS. WAITING FOR MORE PLAYERS...")

    while True:
        TCP_socket_server.listen(5)
        readable, _, _ = select.select([TCP_socket_server], [], [], 4)  # Wait for new connections for 10 seconds//TODO
        if readable:
            client_tcp, address_tcp = TCP_socket_server.accept()
            print("[*] Accepted connection from: %s:%d" % (address_tcp[0], address_tcp[1]))
            request = client_tcp.recv(1024)
            print("[*] Received: %s" % request)
            client_tcp.send('ACK!'.encode('utf-8'))
            client_name = client_tcp.recv(1024)
            lock.acquire()
            my_clients.append((client_tcp, address_tcp, client_name.decode('utf-8')))
            lock.release()
            last_connection_time = time.time()
        else:
            print("No new players joined within 10 seconds. Starting the game.")
            break

    now = time.time()






if __name__ == "__main__":
    UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    my_ip = '192.168.111.1'
    # my_port = 12350
    my_port = 13117
    UDP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    UDP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    UDP_socket.settimeout(0.2)
    print("Server started, listening on IP address " + my_ip)
    UDP_socket.bind((my_ip, my_port))

    number_of_clients = [0]
    my_clients = []
    lock = threading.Lock()
    tcp_port = 13118
    # tcp_port = 12351
    TCP_socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    TCP_socket_server.bind((my_ip, tcp_port))

    t_broadcast = threading.Thread(target=broadcast)
    t_searching_client = threading.Thread(target=searching_client, args=())
    t_broadcast.start()
    # qa_pairs = read_questions_answers_file()
    t_searching_client.start()

    t_searching_client.join()

    # last_connection_time = time()
    last_connection_time = time.time()