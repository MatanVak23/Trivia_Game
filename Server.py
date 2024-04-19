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

    def start_server(self):
        """
        Start the main server loop.
        :return: None
        """
        while True:
            self.initialize_server()
            # Start threads for broadcasting, searching clients, and handling client connections
            t_broadcast = threading.Thread(target=self.broadcast)
            t_searching_client = threading.Thread(target=self.searching_client)
            t_handle_client_searching = threading.Thread(target=self.handle_client_while_searching)
            t_broadcast.start()
            t_searching_client.start()
            t_handle_client_searching.start()  # Start the thread to handle clients while searching
            self.searching_client_flag.set()
            t_searching_client.join()
            t_broadcast.join()
            # Once the searching for clients thread finishes, start the game
            self.broadcasting = True
            self.begin_time = time.time()
            ####TODO - finish the function

    def broadcast(self):
        """
        Broadcast UDP packets to discover clients.
        :return: None
        """
        while True:
            if not self.broadcasting:
                sleep(1)
                print(COLORS_FOR_PLAYERS["Xavi Hernández"] + "Server in broadcast" + COLORS_FOR_PLAYERS["default"])
                udp_format = 'LBH'
                packed = pack(udp_format, 0xabcddcba, 0x2, self.tcp_port)
                try:
                    self.UDP_socket.sendto(packed, ('<broadcast>', self.my_port))
                except OSError as e:
                    continue
            else:
                break

    def searching_client(self):
        """
         Search for clients attempting to connect to the server.
         :return: None
         """
        while self.number_of_clients[0] < 2:
            self.TCP_socket_server.listen()
            print("[*] Listening on %s:%d" % (self.my_ip, self.tcp_port))
            client_tcp, address_tcp = self.TCP_socket_server.accept()
            print("[*] Accepted connection from: %s:%d" % (address_tcp[0], address_tcp[1]))
            request = client_tcp.recv(1024)
            print("[*] Received: %s" % request)
            client_tcp.send('ACK!'.encode('utf-8'))
            try:
                with self.lock:
                    client_name = self.nick_names[0]
                    del self.nick_names[0]  # Remove the first name from the list
                    name_message = client_name
                    client_tcp.send(name_message.encode('utf-8'))
                    self.number_of_clients[0] += 1
                    self.my_clients.append((client_tcp, address_tcp, client_name))
            except ConnectionResetError:
                print(
                    COLORS_FOR_PLAYERS["error"] + "ConnectionResetError: Client disconnected before getting nickname." +
                    COLORS_FOR_PLAYERS["default"])
                continue

        print("GOT TWO CONNECTIONS. WAITING FOR MORE PLAYERS...")

        while True and not self.broadcasting:
            self.TCP_socket_server.listen()
            readable, _, _ = select.select([self.TCP_socket_server], [], [], WAITING_CONNECT)
            if readable:
                client_tcp, address_tcp = self.TCP_socket_server.accept()
                print("[*] Accepted connection from: %s:%d" % (address_tcp[0], address_tcp[1]))
                request = client_tcp.recv(1024)
                print("[*] Received: %s" % request)
                client_tcp.send('ACK!'.encode('utf-8'))
                try:
                    with self.lock:
                        client_name = self.nick_names[0]
                        del self.nick_names[0]  # Remove the first name from the list
                        name_message = client_name
                        client_tcp.send(name_message.encode('utf-8'))
                        self.number_of_clients[0] += 1
                        self.my_clients.append((client_tcp, address_tcp, client_name))
                except ConnectionResetError:
                    print(COLORS_FOR_PLAYERS[
                              "error"] + "ConnectionResetError: Client disconnected before getting nickname." +
                          COLORS_FOR_PLAYERS["default"])
                    continue
                if self.number_of_clients[0] == 2:
                    print("GOT TWO CONNECTIONS. WAITING FOR MORE PLAYERS...")
            else:
                self.lock.acquire()
                if self.number_of_clients[0] >= 2:
                    self.broadcasting = True
                    sleep(1)
                    print("No new players joined within 10 seconds. Starting the game.")
                    self.broadcasting = True
                    self.lock.release()
                    break
                self.lock.release()

    def handle_client_while_searching(self):
        """
         handle cases where client disconnect during the server search for client before the beginning of the game
         :return: None
         """
        while not self.broadcasting and not self.game_on:
            if not self.my_clients:
                sleep(1)
                continue
            client_sockets = [client[0] for client in self.my_clients]
            readable, _, exceptional = select.select(client_sockets, [], client_sockets, 1)
            for sock in exceptional:
                client = next((c for c in self.my_clients if c[0] == sock), None)
                if client:
                    print(
                        COLORS_FOR_PLAYERS["error"] + f"Client {client[2]} disconnected abruptly." + COLORS_FOR_PLAYERS[
                            "default"])
                    with self.lock:
                        self.my_clients.remove(client)
                        self.number_of_clients[0] -= 1
            for sock in readable:
                try:
                    data = sock.recv(1024, socket.MSG_PEEK)
                    if not data:
                        client = next((c for c in self.my_clients if c[0] == sock), None)
                        if client:
                            print(COLORS_FOR_PLAYERS["error"] + f"Client {client[2]} disconnected abruptly." +
                                  COLORS_FOR_PLAYERS["default"])
                            with self.lock:
                                self.my_clients.remove(client)
                                self.number_of_clients[0] -= 1
                except ConnectionResetError:
                    client = next((c for c in self.my_clients if c[0] == sock), None)
                    if client:
                        print(COLORS_FOR_PLAYERS[
                                  "error"] + f"ConnectionResetError: Client {client[2]} disconnected abruptly." +
                              COLORS_FOR_PLAYERS["default"])
                        with self.lock:
                            self.my_clients.remove(client)
                            self.number_of_clients[0] -= 1


if __name__ == "__main__":
    server = Server()
    server.start_server()