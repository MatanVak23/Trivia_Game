import time
import socket
import threading
from struct import *
from Configuration import *


class Client:
    """
        A class representing a client connecting to the server.
        """

    def __init__(self):
        """
        Constructor
        Initializes various attributes for the client.
        :param
        :return: None
        """
        self.server_port = 13117
        self.client_udp_socket = None
        self.client_tcp_socket = None
        self.client_name = None
        self.game_over_flag = threading.Event()

    def get_input(self):
        """
        receive input from the server and send answers for questions
        """
        while not self.game_over_flag.is_set():
            try:
                answer = input("")
                self.client_tcp_socket.send(answer.encode('utf-8'))
            except Exception as e:
                print(COLORS_FOR_PLAYERS["error"] + "Error occurred:", e + COLORS_FOR_PLAYERS["default"])
                break

    def activate_client(self):
        """
        Listening for offers from servers through broadcast.
        Once an offer arrives, connect to it.
        :return:
        """
        while True:
            time.sleep(1)
            self.client_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.client_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.client_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.client_udp_socket.bind(('', self.server_port))
            print("Client started, listening for offer requests...")
            data, addr = self.client_udp_socket.recvfrom(4096)
            udp_format = 'LBH'
            message = unpack(udp_format, data)
            print("Received offer from " + addr[0] + ", attempting to connect...")

            try:
                self.client_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_tcp_socket.connect((addr[0], message[2]))
                self.client_tcp_socket.send("SYN".encode('utf-8'))
                response = self.client_tcp_socket.recv(4096)
                print(response.decode('utf-8'))
                player_nick_name = self.client_tcp_socket.recv(4096)
                self.client_name = player_nick_name.decode('utf-8')
                print(COLORS_FOR_PLAYERS[self.client_name] + f"Your Nickname is {self.client_name}" +
                      COLORS_FOR_PLAYERS["default"])
                self.game_over_flag = threading.Event()
                # begin the input thread - send answers and receive qustions
                input_thread = threading.Thread(target=self.get_input)
                input_thread.start()

                while True:
                    try:
                        response = self.client_tcp_socket.recv(4096)
                        if not response:
                            break
                    except KeyboardInterrupt:
                        break
                    curr_response = response.decode('utf-8')
                    # if the client provided wrong answer - announce it to him in red color
                    if curr_response == WRONG1 or curr_response == WRONG2 or curr_response == WRONG3:
                        print(COLORS_FOR_PLAYERS["error"] + response.decode('utf-8') + COLORS_FOR_PLAYERS["default"])
                    else:
                        print(COLORS_FOR_PLAYERS[self.client_name] + response.decode('utf-8') +
                              COLORS_FOR_PLAYERS["default"])

                    if "Game over!" in response.decode('utf-8'):
                        self.game_over(input_thread)
                        break

            except Exception as e:
                print(COLORS_FOR_PLAYERS["error"] + "Error occurred:", str(e) + COLORS_FOR_PLAYERS["default"])

    def game_over(self, input_thread):
        """
        when the game over - print it to client screen and close the get input thread
        :return:
         """
        print(COLORS_FOR_PLAYERS[self.client_name] + "Game over! Closing connection." + COLORS_FOR_PLAYERS["default"])
        self.client_tcp_socket.close()
        self.game_over_flag.set()  # Set the flag to stop the input thread
        input_thread.join()  # Wait for the input thread to terminate
        self.restart_client()

    def restart_client(self):
        """
        close the client connections
        """
        print("Restarting client...")
        self.client_tcp_socket.close()
        self.client_udp_socket.close()


def main():
    """
    Main function, Initialize client consistently
    :return: None
    """
    while True:
        client = Client()
        client.activate_client()
        time.sleep(1)


if __name__ == "__main__":
    main()
