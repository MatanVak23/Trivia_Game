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
from TriviaGame import TriviaGame


class Server:
    """
       Constructor
       :return: None
       """

    def __init__(self):
        self.UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.my_ip = self.get_wifi_ip_windows()
        self.my_port = UDP_PORT
        # broadcast as long as the game didnt started
        self.broadcasting = False
        # flag to handle disconnected client until the game start
        self.game_on = False
        self.number_of_clients = [0]
        self.my_clients = []
        self.lock = threading.Lock()
        # lock to limit the number times server print the question
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
            self.start_game_for_all_players()
            t_handle_client_searching.join()
            self.reset_server_after_finish_game()
            # After the game ends, close TCP socket and restart server to look for new clients
            # self.TCP_socket_server.close()
            self.TCP_socket_server = None

    def update_statistics_before_game(self):
        """Save current statistics to JSON file."""
        filename = "server_statistics.json"
        statistics_data = {}
        if os.path.exists(filename):
            with self.json_lock:  # Acquire the lock before writing to the file
                with open(filename, "r") as file:
                    statistics_data = json.load(file)
        # Update only the number of games and total players
        statistics_data["number_of_games"] = statistics_data.get("number_of_games", 0) + 1
        self.number_of_games = statistics_data["number_of_games"]
        statistics_data["total_players"] = statistics_data.get("total_players", 0) + self.number_of_clients[0]
        self.total_players = statistics_data["total_players"]
        # Save updated statistics to JSON file
        with self.json_lock:
            with open(filename, "w") as file:
                json.dump(statistics_data, file)

    def update_statistics_after_game(self):
        """
        Update statistics after finishing a game session.
        """
        filename = "server_statistics.json"
        statistics_data = {}
        if os.path.exists(filename):
            with self.json_lock:  # Acquire the lock before writing to the file
                with open(filename, "r") as file:
                    statistics_data = json.load(file)
                # Update only the number of games and total players
                if 'valid_answers' not in statistics_data:
                    statistics_data['valid_answers'] = {}
                curr_game_time = time.time() - self.begin_time
                statistics_data["total_game_time"] = statistics_data.get("total_game_time", 0) + self.total_game_time
                self.total_game_time = statistics_data["total_game_time"]
                statistics_data["total_questions_asked"] = statistics_data.get("total_questions_asked",
                                                                               0) + self.total_questions_asked
                self.total_questions_asked = statistics_data["total_questions_asked"]
                if statistics_data.get("fastest_game_time", 0) > 0:
                    statistics_data["fastest_game_time"] = min(curr_game_time,
                                                               statistics_data.get("fastest_game_time", 0))
                else:
                    statistics_data["fastest_game_time"] = curr_game_time
                self.fastest_game_time = statistics_data["fastest_game_time"]
                statistics_data["longest_game_time"] = max(curr_game_time, statistics_data.get("longest_game_time", 0))
                self.longest_game_time = statistics_data["longest_game_time"]
                for answer, count in self.valid_answers.items():
                    statistics_data["valid_answers"][answer] = statistics_data["valid_answers"].get(answer, 0) + count
                    self.valid_answers[answer] = statistics_data["valid_answers"][answer]
                # Save updated statistics to JSON file
                with open(filename, "w") as file:
                    json.dump(statistics_data, file)

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
                packed = pack(udp_format, PACKET_FORMAT, 0x2, self.tcp_port)
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

    def start_game_for_all_players(self):
        """
        create for each client game thread and run them all simultaneity
         :return: None
         """
        # write to the json - add one more game and update the players num
        self.update_statistics_before_game()
        # all the players receive the same shuffle questions in the same order
        random.shuffle(self.qa_pairs)
        game_threads = []
        with self.lock:
            if self.number_of_clients[0] < 2:
                winner = self.my_clients[0][2]
                self.finish_game_winner(winner)
                self.finish_game_routine()
                return

        for client in self.my_clients:
            game_instance = TriviaGame(client[0], client[2], self.qa_pairs, self.game_over_event, self)
            game_thread = threading.Thread(target=game_instance.start_game)
            game_threads.append(game_thread)
            game_thread.start()
        self.game_on = True

        for thread in game_threads:
            thread.join()
        self.finish_game_routine()

    def finish_game_routine(self):
        # Update statistics after all games finished
        self.update_statistics_after_game()
        self.print_statistics()
        for client in self.my_clients:
            client[0].close()

    def print_statistics(self):
        """
        Print server statistics.
        """
        print("====Statistics for Server====")
        print(COLORS_FOR_PLAYERS["Kaka"] + "Total games plays:",
              str(self.number_of_games) + COLORS_FOR_PLAYERS["default"])
        print(COLORS_FOR_PLAYERS["Lionel Messi"] + "Average number of players per game:",
              str(self.total_players / self.number_of_games) + COLORS_FOR_PLAYERS["default"])
        print(COLORS_FOR_PLAYERS["Sergio Ramos"] + "Average question per game:",
              str(self.total_questions_asked / self.number_of_games) + COLORS_FOR_PLAYERS["default"])
        print(COLORS_FOR_PLAYERS["Neymar Jr."] + "Fastest game:",
              str(self.fastest_game_time) + COLORS_FOR_PLAYERS["default"])
        print(COLORS_FOR_PLAYERS["Ronaldinho"] + "Slowest game:",
              str(self.longest_game_time) + COLORS_FOR_PLAYERS["default"])
        print(COLORS_FOR_PLAYERS["Luka Modric"] + "Most common answer:",
              str(max(self.valid_answers, key=self.valid_answers.get)) + COLORS_FOR_PLAYERS["default"])

    def reset_server_after_finish_game(self):
        """reset the server in the end of the game."""
        self.broadcasting = False
        self.game_on = False
        self.my_clients = []
        self.number_of_clients = [0]
        self.game_over_event.clear()
        self.server_print_counter = 0
        self.begin_time = None
        self.reset_server_statistics()

    def reset_server_statistics(self):
        """reset the server statistics in the end of the game."""
        self.number_of_games = 0
        self.total_players = 0
        self.total_game_time = 0
        self.total_questions_asked = 0
        self.fastest_game_time = float('inf')
        self.longest_game_time = 0
        self.valid_answers = {"T": 0, "Y": 0, "1": 0, "F": 0, "N": 0, "0": 0}

    def finish_game_winner(self, winner):
        """Send a 'finish game' message to all players."""
        finish_message = f"{winner} is correct! {winner} wins!"
        finish_message_2 = f"Game Over!\nCongratulations to the winner: {winner}!"
        for client in self.my_clients:
            client[0].send(finish_message.encode('utf-8'))
            client[0].send(finish_message_2.encode('utf-8'))
        print(COLORS_FOR_PLAYERS[winner] + finish_message_2 + COLORS_FOR_PLAYERS["default"])
        self.game_over_event.set()

    def finish_game_disconnect(self, disconnect):
        """handle disconnect player when only one left and announce him as winner."""

        self.my_clients = [(sock, addr, name) for sock, addr, name in self.my_clients if
                           sock != disconnect]
        if len(self.my_clients) == 1:
            remaining_player = self.my_clients[0][2]
            message = f"Game Over!\nCongratulations to the winner: {remaining_player}!"
            print(COLORS_FOR_PLAYERS[remaining_player] + message + COLORS_FOR_PLAYERS["default"])
            self.game_over_event.set()
            for client in self.my_clients:
                client[0].send(message.encode('utf-8'))
            return True
        disconnect.close()
        return False

    def read_questions_answers_file(self):
        """read the questios from the const questions file"""

        qa_pairs = []
        with open("questions_answers.txt", "r") as file:
            for line in file:
                question, answer = line.strip().split(" : ")
                qa_pairs.append((question, answer))
        return qa_pairs

    def is_correct(self, realAns, playerAns):
        """check if the received answer is the correct answer"""

        if realAns == "Yes":
            if playerAns == "T" or playerAns == "Y" or playerAns == "1":
                return True
            return False
        else:
            if playerAns == "F" or playerAns == "N" or playerAns == "0":
                return True
        return False

    def get_wifi_ip_windows(self):
        """return the wifi port of the current wifi connection"""

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
            return ip_address
        except Exception as e:
            print("Error:", e)
            return None


if __name__ == "__main__":
    server = Server()
    server.start_server()