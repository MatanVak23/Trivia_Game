import time
import select
from Configuration import *


class TriviaGame:
    """
    A class representing the trivia game logic.
    """
    def __init__(self, client_socket, client_name, qa_pairs, game_over_event, server_instance):
        """
        Constructor method for the TriviaGame class.
        Initializes various attributes for the game.
        """
        self.client_socket = client_socket
        self.client_name = client_name
        self.qa_pairs = qa_pairs
        self.game_over_event = game_over_event
        self.server_instance = server_instance
        self.question_index = 0
        self.is_connected_flag = True

    def send_welcome(self):
        """
        send welcome message for the current client
        """
        players = [client[2] for client in self.server_instance.my_clients]
        message = f"Welcome to Soccer Trivia.\nPlayers: {players}\n==\nPlease answer the following " \
                  f"question as fast as you can: \n"
        self.client_socket.send(message.encode('utf-8'))

    def send_question_to_client(self, question, index):
        """
        send the player the current question
        """
        # use lock on the server to print the question only once one on the server screen
        self.server_instance.server_print_lock.acquire()
        if self.server_instance.server_print_counter == index:
            print(COLORS_FOR_PLAYERS[self.client_name] + question + COLORS_FOR_PLAYERS["default"])
            self.server_instance.server_print_counter += 1
            self.server_instance.total_questions_asked += 1
            self.server_instance.server_print_counter = self.server_instance.server_print_counter % 40
        self.server_instance.server_print_lock.release()
        if self.is_connected_flag:
            self.client_socket.send(question.encode('utf-8'))

    def valid_input(self, answer):
        """
        check if the answer is one of the optional valid answers
        """
        valid = ['Y', 'N', 'T', 'F', '0', '1']
        return answer in valid

    def receive_answer(self, correct_answer):
        """
        receive answer from the current client and handle all the optional cases of this answer
        """
        answer_client = False
        start_time = time.time()
        end_time = start_time + WAITING_ANSWER  # Change timeout to 10 seconds

        while time.time() < end_time:
            ready_clients, _, _ = select.select([self.client_socket], [], [], end_time-time.time())
            if ready_clients:  # Check if there's at least one socket ready
                sock = ready_clients[0]  # Get the first (and only) item in the list
                answer = sock.recv(1024).strip().decode('utf-8').strip()
                # Process the answer as needed
                if answer_client:
                    already_answered_message = "You already tried to answer this question!"
                    self.client_socket.send(already_answered_message.encode('utf-8'))

                else:
                    if not self.valid_input(answer):
                        invalid_message = "You Provided invalid input! try again"
                        self.client_socket.send(invalid_message.encode('utf-8'))
                    else:
                        self.server_instance.valid_answers_lock.acquire()
                        self.server_instance.valid_answers[answer] += 1
                        self.server_instance.valid_answers_lock.release()

                        if self.server_instance.is_correct(correct_answer, answer):
                            winner = next(client[2] for client in self.server_instance.my_clients if
                                          client[0] == self.client_socket)
                            self.server_instance.finish_game_winner(winner)
                            return True
                        else:
                            wrong_answer_message = "Wrong answer!"
                            self.client_socket.send(wrong_answer_message.encode('utf-8'))
                            answer_client = True

        timeout_message = "No player provided the correct answer within 10 seconds. Let's try another question."
        if self.is_connected_flag and not self.game_over_event.is_set():
            self.client_socket.send(timeout_message.encode('utf-8'))
        return False

    def start_game(self):
        try:
            self.send_welcome()
            question_index = 0
            # run as long as the game active
            while not self.game_over_event.is_set() and self.is_connected_flag:
                curr_question, correct_answer = self.qa_pairs[question_index]
                self.send_question_to_client(curr_question, question_index)
                question_index += 1
                question_index = question_index % 40
                if self.receive_answer(correct_answer):
                    self.game_over_event.set()
                    break
        except (ConnectionResetError, KeyboardInterrupt):
            print(COLORS_FOR_PLAYERS["error"] + f"{self.client_name} disconnected " +
                  COLORS_FOR_PLAYERS["default"])
            self.server_instance.finish_game_disconnect(self.client_socket)
            self.is_connected_flag = False


