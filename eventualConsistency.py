import random
import multiprocessing
import threading
import socket
import sys
from message import Message, TotalOrderMessage, SqeuncerMessage, EventualConsistencyMessage, LinearizabilityConsistencyMessage
from channel import Channel
from variableStored import VariableStored


class EventualConsistency(Channel): # inherit from Channel
    """
        evantual consistency model to handle write and read from client
    """

    sequencer_pid = 1
    """
        __init__(Process, int, process_info, addr_dict, bool)
    """
    def __init__(self, process, pid, process_info, addr_dict, W, R, lock, is_sequencer = False):
        super(EventualConsistency, self).__init__(process, pid, socket, process_info, addr_dict)

        self.r_sequencer = multiprocessing.Value('i', 0) # receive sequence number
        self.s_sequencer = multiprocessing.Value('i', 0) # send sequence number
        self.hb_queue = []  # hold back queue
        self.pid = pid
        self.seq_queue = []
        self.lock = lock
        self.W = W
        self.R = R
        self.messageID2timestamp = dict() # map messageID to time
        self.messageID2client = dict() # map messageID to client TCP socket
        self.variables = VariableStored()
        self.is_sequencer = is_sequencer

    """
        send message via TCP
        unicastTCP(int, socket, str)
    """
    def unicastTCP(self, serverID, message, conn):
        print("unicastTCP...")
        delay_time = random.uniform(self.min_delay, self.max_delay)
        # m = Message(self.pid, serverID, message)
        print(message.send_str())
        print('delay unicastTCP with {0:.2f}s '.format(delay_time))
        delayed_t = threading.Timer(delay_time, self.__unicastTCP, (conn, message,))
        delayed_t.start()

    """
        unicastTCP helper
        __unicastTCP(socket, str)
    """
    def __unicastTCP(self, conn, message):
        try:
            conn.send(str(message))
        except:
            print("Cannot send TCP message to client")

    """
        UDP unicast to server replicas with messages:
        w_ack(var), r_ack(var,value,timepoint)
        unicast(EventualConsistencyMessage)
    """
    def unicast(self, message, destination):
        print("unicast...")

        delay_time = random.uniform(self.min_delay, self.max_delay)
        # message = Message(self.pid, destination, message)
        print(str(message))
        print('delay unicast with {0:.2f}s '.format(delay_time))
        delayed_t = threading.Timer(delay_time, self.__unicast, (message, destination,))
        delayed_t.start()

    """
        helper function for UDP unicast to server replicas
    """
    def __unicast(self, message, destination):
        dest_addr = self.process_info[destination]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(str(message), dest_addr)
        finally:
            sock.close()

    """
        total ordering multicast to server replicas with messages:
        w(var, value), r(var)
        multicast(str)

        This will also multicast to sender
    """
    def multicast(self, conn, message, header, client_id):
        print("multicast...")
        """
            Generate a random identifer ranged from 1 - MAX_INT
            as a message ID
        """
        id = random.randint(1, sys.maxint)
        self.lock.acquire()
        self.messageID2client[id] = conn
        self.lock.release()

        for to_pid in self.process_info.keys():
            # m = "header from_id to_id message messageID"
            m = EventualConsistencyMessage(self.pid, to_pid, id, client_id, message, header)
            self.unicast(m, to_pid)

    """
        Multicast order message, only called by if the process is sequencer
        the message carries a unique timepoint decicde by sequencer
    """
    def sequencer_multicast(self, id):
        """
            SqeuncerMessage(randMessageID, s_sequencer.value)
        """
        m = SqeuncerMessage(id, self.s_sequencer.value)

        for to_pid in self.process_info.keys():
            self.unicast(m, to_pid)
        """
            increment sequencer order number
        """
        with self.s_sequencer.get_lock():
            self.s_sequencer.value += 1

    """
        receive message from server replicas,
        parse messages:
        w(var, value)
    """
    def recv_from_replica(self, data):
        print("recvReplica...")
        # print("dump all keys in messageID2client: ")
        # self.lock.acquire()
        # for key in self.messageID2client: print(key)
        # self.lock.release()

        if data:
            print("get replica message ", data)
            data_args = data.split()
            """
                r_ack(var, value, timepoint, messageID)
            """
            if data_args[0] == "r_ack":
                # data = 'r_ack 2 2 x 0 0 8037938055510234267 980486'
                from_id, to_id, var, value, timepoint, id, client_id = int(data_args[1]), int(data_args[2]), data_args[3], int(data_args[4]), int(data_args[5]), int(data_args[6]), int(data_args[7])
                # update var timpoint and value
                if timepoint > self.variables.lastWrite[var]:
                    self.variables.lastWrite[var] = timepoint
                    self.variables.variables[var] = value

                # update received ack
                self.variables.setRAck(var, self.variables.getRAck(var) + 1)

                # send r_ack to client if received ack >= R
                if self.variables.getRAck(var) >= self.R:
                    self.lock.acquire()
                    if id in self.messageID2client:
                        conn = self.messageID2client[id]
                        ack_message = var + " " + str(self.variables.variables[var])
                        m = EventualConsistencyMessage(self.pid, client_id, id, client_id, ack_message, "r_ack")
                        self.unicastTCP(self.pid, m, conn)
                        # clean received ack
                        self.variables.setRAck(var, 0)
                        self.printLog(m, self.variables.lastWriteTime(var))
                    else:
                        print("no corresponded messageID %d" % (id))
                    self.lock.release()

            # w_ack(var, messageID)
            elif data_args[0] == "w_ack":
                # data = 'w_ack 33276 2 put x 1 7440523501060122809 33276'
                from_id, to_id, tok, var, value, id, client_id = int(data_args[1]), int(data_args[2]), data_args[3], data_args[4], int(data_args[5]), int(data_args[6]), int(data_args[7])
                self.variables.setWAck(var, self.variables.getWAck(var)+1)
                if self.variables.w_ack[var] >= self.W:
                    self.lock.acquire()
                    if id in self.messageID2client:
                        conn = self.messageID2client[id]
                        ack_message = var + " " + str(self.variables.variables[var])
                        # m = "w_ack from_id message_id message_id message message_id"
                        m = EventualConsistencyMessage(self.pid, client_id, id,client_id, ack_message, "w_ack")
                        self.unicastTCP(self.pid, m, conn)
                        # clean received ack
                        self.variables.setWAck(var, 0)
                        self.printLog(m, self.variables.lastWriteTime(var))
                    else:
                        print("no corresponded messageID %d" % (id))
                    self.lock.release()
            # write(var,value)
            # total order multicast
            elif data_args[0] == "w":
                # data = 'w 1 1 17701 put x 1 990784337849110725'
                from_id, to_id, tok, var, value, id, client_id = int(data_args[1]), int(data_args[2]), data_args[3], data_args[4], int(data_args[5]), int(data_args[6]), int(data_args[7])
                message = tok + " " + var + " " + str(value)
                m = EventualConsistencyMessage(from_id, to_id, id, client_id, message, "w")
                # push the message in to queue
                self.hb_queue.append(m)

                # If the receiving process is sequencer, 
                # multicast the sequencer message to all the other processes
                if self.is_sequencer:
                    self.sequencer_multicast(id)

                # check our sequence message to queue to see if we already received the corresponding sequence message
                self.check_seq_queue(self.r_sequencer.value)

            # read(var) Message
            # deliver immediately without total order multicast
            elif data_args[0] == "r":
                # data = 'r 2 2 103533 get x 1342189802441044593 54641'
                from_id, to_id, tok, var, id, client_id= int(data_args[1]), int(data_args[2]), data_args[3], data_args[4], int(data_args[5]), int(data_args[6])
                # deliver message
                print("deliver message %s from %d" % (data, from_id))

                timepoint = self.variables.lastWriteTime(var)
                value = self.variables.variables[var]
                ack_message = var + " "  + str(value) + " "  + str(timepoint)

                # only sender print log
                if from_id == self.pid:
                    ack_log = var + " "  + str(value)
                    m_log = EventualConsistencyMessage(from_id, to_id, id, client_id, ack_log, "r")
                    self.printLog(m_log, timepoint)

                # ack_message = "r_ack var value timepoint messageID"
                m = EventualConsistencyMessage(from_id, to_id, id, client_id, ack_message, "r_ack")
                self.unicast(m, from_id)
            
            # Sequencer's order message
            elif data_args[0] == "seq":
                m_id, sequence = int(data_args[1]), int(data_args[2])
                self.messageID2timestamp[m_id] = sequence
                seq_m = SqeuncerMessage(m_id, sequence)

                # only 'w' message has 'seq'
                # message = self.messageID2message[m_id]
                # self.printLog(message, sequence)
                message = self.check_queue(m_id)

                # if the sequence order is expected and we already received the message
                if sequence == self.r_sequencer.value and message:

                    # Deliver the message to process
                    self.deliver(message.from_id, message, sequence)

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
                print("replica message not understood")
                # m = Message(data_args[0], data_args[1], data_args[2])
                # self.process.unicast_receive(m.from_id, m)
        else:
            print("No data received from replica")

    """
        receive messages from clients
        parse message, and then invoke multicast:
        w(var, value), r(var)

        server replica and sequencer handles these two types
        of messages differently:
            1. For w(var, value), total order is needed. 
            2. For r(var), only to read var from a server 
            and unicast back r_ack(var,value,timepoint).

        Order of execution:
        Once a "put" or "get" message is arrived, execute immediately

        here we don't use self.conn since server needs to handle
        different client with different TCP conn
    """
    def recv_from_client(self, data, conn):
        print("call recvClient()...")
        print("get client message ", data)
        if data:
            data_args = data.split()
            client_id = data_args[0]
            """
                client r(var)
            """
            if data_args[1] == "get":
                var = data_args[2]
                # data_args = "get var"
                message = data_args[1] + " " + data_args[2]
                self.multicast(conn, message, "r", client_id)

            # client w(var, value)
            elif data_args[1] == "put":
                var, value = data_args[2], data_args[3]
                # data_args = "put var value"
                message = data_args[1] + " " + data_args[2] + " " + data_args[3]
                self.multicast(conn, message, "w", client_id)
            # client dump
            elif data_args[1] == "dump":
                self.variables.dump(self.pid)
            else:
                print("Client message not understood")
        else:
            print("No message received")
    
    # ouput to log file
    def printLog(self, m, timepoint, value=0):
        print("printLog...")
        request = ''
        status = ''
        if m.header == 'w':
            request = 'put'
            status = 'req'
        elif m.header == 'r':
            request = 'get'
            status = 'req'
        elif m.header == 'w_ack':
            request = 'put'
            status = 'resp'
        elif m.header == 'r_ack':
            request = 'get'
            status = 'resp'
        else:
            print("header not known")

        content = m.content.split()
        print("content: ", m.content)
        var, value = content[0], content[1]
        log_id = self.pid
        log_line = ''
        if (m.header == 'r'):
            log_line = str(log_id) + ',' + str(m.client_id) + ',' + request + ',' + var + ',' + str(timepoint) + ',' + status + ',' + '\n'
        else:
            log_line = str(log_id) + ',' + str(m.client_id) + ',' + request + ',' + var + ',' + str(timepoint) + ',' + status + ',' + str(value) + '\n'

        log_name = "output_log" + str(self.pid) + ".txt"

        with open(log_name, "a") as logf:
            print(log_line)
            logf.write(log_line)
            logf.close()

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
        deliver total order message at this server replica
        there is only one kind of message: "w"
    """
    def deliver(self, from_id, m, timepoint):
        if m.header == "w":
            data_args = m.content.split()
            tok, var, value = data_args[0], data_args[1], data_args[2]
            if var in self.variables.variables:
                self.variables.put(var, value, timepoint)
            print("deliver message %s\n" % (str(m)))
            m = EventualConsistencyMessage(m.from_id, m.to_id, m.id, m.client_id, m.content, "w_ack");
            self.unicast(m, from_id)

            # only sender print log
            if (from_id == self.pid):
                ack_log = var + " "  + str(value)
                m_log = EventualConsistencyMessage(from_id, m.to_id, m.id, m.client_id, ack_log, "w")
                self.printLog(m_log, timepoint)

        # elif m.header == "r":
        #     data_args = m.content.split()
        #     tok, var = data_args[0], data_args[1]
        #     print("deliver message %s\n" % (str(m)))
        #     message = m.content + " " + str(self.variables.variables[var]) + timepoint
        #     m = EventualConsistencyMessage(m.from_id, m.to_id, m.id, message, "r_ack");
        #     self.unicast(m, from_id)

    """
        Check our queue for sequence number,
        if we have an expected sequence number stored in the queue,
        then we check if we have the corresponding message received.
        If both conditions are met, we pop the sequence number the message out of our queues.
        check_seq_queue(int)
    """
    def check_seq_queue(self, seq):
        # if the sequence message queue is not empty
        if self.seq_queue:
            for seq_m in self.seq_queue:
                if seq_m.sequence == seq:
                    queued_message = self.check_queue(seq_m.id)
                    if queued_message:

                        # Deliver the message to process
                        self.deliver(queued_message.from_id, queued_message, seq)
                        self.seq_queue.remove(seq_m)
                        # increment this process order number
                        with self.r_sequencer.get_lock():
                            self.r_sequencer.value += 1

                        # keep checking the queue
                        self.check_seq_queue(self.r_sequencer.value)
