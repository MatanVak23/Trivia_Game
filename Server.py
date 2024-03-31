from struct import *
import socket
import random
from time import *
import threading
import select
import time
import select


def broadcast():
    while True:
        # print("Server in broadcast")
        udp_format = 'LBh'
        # tcp_port = 12351
        tcp_port = 13118
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