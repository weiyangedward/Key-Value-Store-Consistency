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
        self.socket = socket
        self.process_info = process_info
        self.addr_dict = addr_dict
        self.min_delay, self.max_delay = configreader.get_delay_info()

    def unicast(self, message, destination):
        delay_time = random.uniform(self.min_delay, self.max_delay)
        message = Message(self.pid, destination, message)
        print(message.send_str())
        print('delay unicast with {0:.2f}s '.format(delay_time))
        delayed_t = threading.Timer(delay_time, self.__unicast, (message, destination,))
        delayed_t.start()

    def __unicast(self, message, destination):
        dest_addr = self.process_info[destination]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(str(message), dest_addr)
        finally:
            sock.close()
    # receive message
    def recv(self, data, from_addr):
        if data:
            data_args = data.split()
            m = Message(data_args[0], data_args[1], data_args[2])
            self.process.unicast_receive(m.from_id, m)