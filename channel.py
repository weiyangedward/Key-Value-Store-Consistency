import random
import threading
import configreader
import socket
from message import Message


class Channel(object):
    """
        This is a basic channel supports delayed function and unicast.
    """
    def __init__(self, process, pid, socket, process_info, addr_dict):
        self.process = process
        self.pid = pid
        self.socket = socket # TCP socket, is used to send message
        self.process_info = process_info
        self.addr_dict = addr_dict
        self.min_delay, self.max_delay = configreader.get_delay_info()

    """
        send message via TCP
        unicastTCP(int, socket, str)
    """
    def unicastTCP(self, serverID, message):
        delay_time = random.uniform(self.min_delay, self.max_delay)
        m = Message(self.pid, serverID, message)
        print(m.send_str())
        print('delay unicast with {0:.2f}s '.format(delay_time))
        delayed_t = threading.Timer(delay_time, self.__unicastTCP, (message,))
        delayed_t.start()

    """
        unicastTCP helper
        __unicastTCP(socket, str)
    """
    def __unicastTCP(self, message):
        try:
            self.socket.sendall(message.encode())
        except:
            print("Cannot send message to server")

    """
        unicast(str, int)
    """
    def unicast(self, message, destination):
        delay_time = random.uniform(self.min_delay, self.max_delay)
        message = Message(self.pid, destination, message)
        print(message.send_str())
        print('delay unicast with {0:.2f}s '.format(delay_time))
        delayed_t = threading.Timer(delay_time, self.__unicast, (message, destination,))
        delayed_t.start()

    """
        unicast helper, init UDP socket
        __unicast(str, int)
    """
    def __unicast(self, message, destination):
        dest_addr = self.process_info[destination]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(str(message), dest_addr)
        finally:
            sock.close()

    """
        receive message
        recv(str)
    """
    def recv(self, data):
        # print("receive message from cliemt ", data)
        if data:
            data_args = data.split()
            tok, from_id, message_id, var, value, message_id = data_args[0], data_args[1], data_args[2], data_args[3], data_args[4], data_args[5]
            print("received message from server: ", data)
            # print("delivered message: ", data)
            print(var, str(value))


