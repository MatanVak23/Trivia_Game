import socket
import threading
from struct import *


def get_input(client_tcp_socket, game_over_flag):
    while not game_over_flag.is_set():
        try:
            answer = input("")
            client_tcp_socket.send(answer.encode('utf-8'))
        except Exception as e:
            print("Error occurred:", e)
            break


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # my_ip = '127.0.0.1'  # Local computer
    my_ip = '192.168.111.1'  # Local computer
    # my_port = 12350
    my_port = 13117


    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client_socket.bind(("", my_port))
    print("Client started, listening for offer requests...")

    while True:
        data, addr = client_socket.recvfrom(4096)
        udp_format = 'LBh'
        message = unpack(udp_format, data)
        print(message)
        print("Received offer from " + addr[0] + ", attempting to connect...")

        try:
            client_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_tcp_socket.connect((addr[0], message[2]))
            client_tcp_socket.send("SYN".encode('utf-8'))
            response = client_tcp_socket.recv(4096)
            print(response.decode('utf-8'))
            group_name = input("Enter your group name: ")
            client_tcp_socket.send(group_name.encode('utf-8'))
            game_directions = client_tcp_socket.recv(4096)
            print(game_directions.decode('utf-8'))

            game_over_flag = threading.Event()

            input_thread = threading.Thread(target=get_input, args=(client_tcp_socket,game_over_flag))
            input_thread.start()

            while True:
                response = client_tcp_socket.recv(4096)
                if not response:
                    break
                print(response.decode('utf-8'))

                if "Game over!" in response.decode('utf-8'):
                    print("Game over! Closing connection.")
                    client_tcp_socket.close()
                    game_over_flag.set()  # Set the flag to stop the input thread
                    input_thread.join()  # Wait for the input thread to terminate
                    client_socket.close()  # Close the UDP socket
                    return  # Exit the main function

            client_tcp_socket.close()
            break
        except Exception as e:
            print("")
            # print("Error occurred:", e)


if __name__ == "__main__":
    main()
