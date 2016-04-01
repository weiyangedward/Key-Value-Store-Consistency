import random
import multiprocessing
import threading
import socket
import sys
from message import Message, TotalOrderMessage, SqeuncerMessage
from channel import Channel


class TotalOrderChannel(Channel): # inherit from Channel
    """
        This is a channel supports delayed function, unicast and total order multicast.
    """

    sequencer_pid = 1
    # __init__(Process, int, socket, process_info, addr_dict, bool)
    def __init__(self, process, pid, socket, process_info, addr_dict, variables, is_sequencer=False):
        super(TotalOrderChannel, self).__init__(process, pid, socket, process_info, addr_dict)

        self.r_sequencer = multiprocessing.Value('i', 0)
        self.s_sequencer = multiprocessing.Value('i', 0)
        self.hb_queue = []  # hold back queue
        # sequence hold_back queue (better to use map!!)
        # seq_queue[ SqeuncerMessage ]
        self.seq_queue = []  
        self.is_sequencer = is_sequencer
        self.consistency = None
        self.variables = variables

    # unicast(Message, int)
    def unicast(self, message, destination):
        delay_time = random.uniform(self.min_delay, self.max_delay)
        print('delay unicast with {0:.2f}s '.format(delay_time))

        print(message.send_str())
        delayed_t = threading.Timer(delay_time, self.__unicast, (message, destination,))
        delayed_t.start()

    # helper function for unicast thread
    def __unicast(self, message, destination):
        dest_addr = self.process_info[destination]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            sock.sendto(str(message), dest_addr)
            # data, server = sock.recvfrom(4096)
        finally:
            sock.close()

    # multicast(str)
    def multicast(self, message, consistency):
        self.consistency = consistency
        """
            Generate a random identifer ranged from 1 - MAX_INT
            as a message ID
        """
        id = random.randint(1, sys.maxint)

        for to_pid in self.process_info.keys():
            m = TotalOrderMessage(self.pid, to_pid, id, message)
            self.unicast(m, to_pid)

    # B-Multicast order message, only called by if the process is sequencer
    def sequencer_multicast(self, id):
        """
            SqeuncerMessage(randMessageID, s_sequencer.value)
        """
        m = SqeuncerMessage(id, self.s_sequencer.value)

        for to_pid in self.process_info.keys():
            self.unicast(m, to_pid)
        # increment sequencer order number
        with self.s_sequencer.get_lock():
            self.s_sequencer.value += 1

    # move unicast_receive from process to here
    def unicast_receive(self, source, message, client_port, var, action):
        print (message.receive_str())
        if (action == "w"):
            self.w_ack[(client_port, var)] += 1
            if (self.w_ack[(client_port, var)] >= self.W):
                self.consistency.unicast(message + var + str(self.variables[var]))

    """
        channel receive message
        recv(str, address)
    """
    def recv(self, data, from_addr):
        if data:
            data_args = data.split()

            """
                Multicast Message
            """
            if len(data_args) == 4:
                from_id, to_id, id, message = int(data_args[0]), int(data_args[1]), int(data_args[3]), data_args[2]
                # ack get message
                print("get message %s from %d" % (message, from_id))

                m = TotalOrderMessage(from_id, to_id, id, message)

                # push the message in to queue
                self.hb_queue.append(m)

                # If the receiving process is sequencer, multicast the sequencer message to all the other processes
                if self.is_sequencer:
                    self.sequencer_multicast(id)

                # check our sequence message to queue to see if we already received the corresponding sequence message
                self.check_seq_queue(self.r_sequencer.value)
            """
                Sequencer's order message
            """
            elif len(data_args) == 2:
                m_id, sequence = int(data_args[0]), int(data_args[1])
                seq_m = SqeuncerMessage(m_id, sequence)
                message = self.check_queue(m_id)

                # if the sequence order is expected and we already received the message
                if sequence == self.r_sequencer.value and message:

                    # Deliver the message to process
                    unicast_receive(message.from_id, message)

                    # update the value of sequence number
                    with self.r_sequencer.get_lock():
                        self.r_sequencer.value += 1

                    # check our sequence message queue to see
                    # if we already received a sequence message with higher sequence number
                    self.check_seq_queue(self.r_sequencer.value)

                # if the sequence number is not what we expected or we haven't received the corresponding message
                # then we save them into the queue for later use.
                else:
                    self.seq_queue.append(seq_m)
                    if message:
                        self.hb_queue.append(message)

            # Unicast Receive
            else:
                m = Message(data_args[0], data_args[1], data_args[2])
                self.process.unicast_receive(m.from_id, m)

    """
        Check if the process received a message with given id.
    """
    def check_queue(self, id):
        if self.hb_queue:
            for queued_message in self.hb_queue:
                if queued_message.id == id:
                    self.hb_queue.remove(queued_message)
                    return queued_message
            return None
        else:
            return None

    """
        Check our queue for sequence number,
        if we have an expected sequence number stored in the queue,
        then we check if we have the corresponding message received.
        If both conditions are met, we pop the sequence number the message out of our queues.
        check_seq_queue(int sequence_number)
    """
    def check_seq_queue(self, seq):
        # if the sequence message queue is not empty
        if self.seq_queue:
            for seq_m in self.seq_queue:
                if seq_m.sequence == seq:
                    queued_message = self.check_queue(seq_m.id)
                    if queued_message:

                        # Deliver the message to process
                        self.process.unicast_receive(queued_message.from_id, queued_message)
                        self.seq_queue.remove(seq_m)
                        # increment this process order number
                        with self.r_sequencer.get_lock():
                            self.r_sequencer.value += 1

                        # keep checking the queue
                        self.check_seq_queue(self.r_sequencer.value)
