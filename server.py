"""

    def main():
        1. parse args
        2. init a lock for both of Replica and Server
        3. init Server obj
        4. launch Server thread to talk to client
        5. listen to manager command


    class ServerThread(derived from multiprocessing.Process):

        def __init__(server, client_id, conn):


    class ReplicaThread(derived from multiprocessing.Process):

        def __init__(server):
            get server Address and Port info from configreader
            set UDP connect

        def run():
            while true:
                receiving message
                self.server.consistency.recv(data, address)

    class Server(derived from multiprocessing.Process):

        def __init__(serverID, arg_consistency, variableStored, lock):
            get server Address and Port info from configreader
            set consistency model (eventual consistency modified from channel, linearizability modified from totalOrderChannel)
            set TCP connect

        def run():
            launch a replicaThread
            while True:
                keep accepting client
                launch a server thread for a client

"""


import multiprocessing
import threading
import socket
import argparse
import configreader
from variableStored import VariableStored
from eventualConsistency import EventualConsistency
from linearizabilityConsistency import LinearizabilityConsistency

class ServerThread(multiprocessing.Process):
    """
        a server thread handles requests from a client
    """
    def __init__(self, server, client_port, conn):
        super(ServerThread, self).__init__()
        self.conn = conn
        self.client_port = client_port
        self.server = server
    """
        handle requests from a client
    """
    def run(self):
        try:
            while 1:
                # data = self.conn.recv(4096) # receive message 
                data, address = self.conn.recvfrom(4096)
                print("receive %s from %d" % (data, client_port))
                self.conn.send(("client " + str(client_port) + " say: " + data.decode()).encode())
                self.server.consistency.recvClient(data, address, self.conn, self.lock)
        except:
            print("Lost a client")
        self.conn.close()


class ReplicaThread(multiprocessing.Process):
    """ 
        a replica thread talks to other server replicas
    """
    def __init__(self, server):
        super(ReplicaThread, self).__init__() # call __init__ from multiprocessing.Process
        
        # Read config from file
        self.process_info, self.addr_dict = server.process_info, server.addr_dict
        self.address = server.address
        self.ip, self.port = server.ip, server.port
        self.server = server

        """
            Init a UDP socket
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.address)

    """
        receive message, override run()
    """
    def run(self):
        try:
            while True:
                data, address = self.socket.recvfrom(4096)
                """
                    call server.consistency.recvReplica(), which will 
                    handle the message received.
                    The recvReplica() function will also invoke multicast/unicast
                    to other server replicas
                """
                self.server.consistency.recvReplica(self, data, address)
        except:
            print("Disconnected from server replicas")


class Server(multiprocessing.Process):
    """
        a server gets request from all clients and sends data back
    """
    def __init__(self, serverID, arg_consistency, variableStored, lock, W, R):
        super(Server, self).__init__()
        # get address and port info
        self.process_info, self.addr_dict = configreader
        .get_processes_info()
        self.address = self.process_info[serverID]
        self.ip, self.port = address[0], address[1]

        self.socket = None
        self.variableStored = variableStored
        self.arg_consistency = arg_consistency
        self.consistency = None
        self.lock = lock
        self.serverID = serverID
        self.W = W
        self.R = R

    """
        init consistency model
    """
    def setConsistency(self):
        if (arg_consistency == "eventual"): # no sequencer for eventual consistency
                self.consistency = EventualConsistency(self, self.serverID, self.process_info, self.addr_dict, self.variableStored, self.lock, W, R)
        elif (arg_consistency == "linearizability"):
            if (self.serverID == 1):
                self.consistency = LinearizabilityConsistency(self, self.serverID, self.socket, self.process_info, self.addr_dict, True)
            else:
                self.consistency = LinearizabilityConsistency(self, self.serverID, self.socket, self.process_info, self.addr_dict)

    """    
        init TCP connect to clients 
    """
    def tcpConn(self):
        for res in socket.getaddrinfo(self.ip, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                print("building a socket")
                self.socket = socket.socket(af, socktype, proto) # build a socket
            except socket.error as msg:
                self.socket = None
                continue
            try:
                print("binding to a socket")
                self.socket.bind(sa) # build to a socket
                print("listening")
                self.socket.listen(1) # listen
            except socket.error as msg:
                self.socket.close()
                self.socket = None
                continue
            break
        if self.socket is None:
            print('could not open socket')
            sys.exit(1)

    """
        init a thread for server replica
        init a new thread for every client
    """
    def run(self):
        try:
            # start process thread
            t_replica = ReplicaThread(self)
            t_replica.daemon = True # daemon thread does not prevent main program from exiting
            t_replica.start()
            # connect to TCP
            tcpConn()
            while(1):
                conn, addr = self.s.accept() # accept
                print('Connected by', addr) # addr = (host, port)
                # init a server thread for a client
                t_serverThread = ServerThread(addr[1], conn)
                t_serverThread.daemon = True
                t_serverThread.start()
        except:
            print("Server crashed")


def main():
    parser = argparse.ArgumentParser(description="replica server")
    parser.add_argument("id", help="process id (1-10), default=1", type=int, default=1)
    parser.add_argument("consistency", help="consistency model (eventual || linearizability), default=eventual", type=str, default='eventual')
    parser.add_argument("W", help="number of w_ack indicates finished, default=1", type=int, default='1')
    parser.add_argument("R", help="number of r_ack indicates finished, default=1", type=int, default='1')
    args = parser.parse_args()
    variableStored = VariableStored() # init variables stored in server
    lock = multiprocessing.Lock()

    # start server thread
    t_server = Server(args.id, args.consistency, variableStored, lock, W, R)
    t_server.daemon = True
    t_server.start()

    # replica talks to other replicas
    try:
        while True:
            cmd = raw_input()
            if cmd:
                cmd_args = cmd.split()
                if cmd_args[0] == "exit": 
                    break;
    except KeyboardInterrupt:
        print("CTRL C occured")

if __name__ == '__main__':
    main()
