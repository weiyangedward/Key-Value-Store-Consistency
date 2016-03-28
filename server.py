import multiprocessing
import threading
import socket
import argparse
import configreader
from channel import Channel
from totalOrderChannel import TotalOrderChannel
from variableStored import VariableStored
from eventualConsistency import EventualConsistency
from linearizabilityConsistency import LinearizabilityConsistency

class ServerThread(multiprocessing.Process):
    """
        a server thread handles requests from a client
    """
    def __init__(self, client_port, conn, consistency, t_replica, variables, lock):
        super(ServerThread, self).__init__()
        self.conn = conn
        self.client_port = client_port
        self.lock = lock
        self.consistency = consistency
        self.t_replica = t_replica
        self.variables = variables

    # handle requests from a client
    def run(self):
        try:
            while 1:
                # data = self.conn.recv(4096) # receive message 
                data, address = self.conn.recvfrom(4096)
                print("receive %s from %d" % (data, client_port))
                self.conn.send(("client " + str(client_port) + " say: " + data.decode()).encode())
                self.consistency.recv(data, address, self.conn, self.t_replica, self.variables, self.lock)
        except:
            print("Lost a client")
        self.conn.close()



class Server(multiprocessing.Process):
    """
        a server gets request from all clients and sends data back
    """
    def __init__(self, id, t_replica, arg_consistency, variables, lock):
        super(Server, self).__init__()
        self.id = id
        self.process_info, self.addr_dict = configreader.get_processes_info()
        self.address = self.process_info[id]
        self.ip, self.port = address[0], address[1]
        self.s = None
        self.variables = variables
        self.arg_consistency = arg_consistency
        self.consistency = None
        self.lock = lock
        # replica thread, is used to talk to other servers
        self.t_replica = t_replica

    # init consistency model
    def setConsistency(self):
        if (arg_consistency == "eventual"):
            self.consistency = EventualConsistency(self, self.id, self.socket, self.process_info, self.addr_dict)
        elif (arg_consistency == "linearizability"):
            self.consistency = LinearizabilityConsistency(self, self.id, self.socket, self.process_info, self.addr_dict)
        
    #init TCP connect to clients 
    def tcpConn(self):
        for res in socket.getaddrinfo(self.ip, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                print("building a socket")
                self.s = socket.socket(af, socktype, proto) # build a socket
            except socket.error as msg:
                self.s = None
                continue
            try:
                print("binding to a socket")
                self.s.bind(sa) # build to a socket
                print("listening")
                self.s.listen(1) # listen
            except socket.error as msg:
                self.s.close()
                self.s = None
                continue
            break
        if self.s is None:
            print('could not open socket')
            sys.exit(1)

    # init a new thread for every client
    def run(self):
        try:
            tcpConn()
            while(1):
                conn, addr = self.s.accept() # accept
                print('Connected by', addr) # addr = (host, port)
                # init a server thread for a client
                t_serverThread = ServerThread(addr[1], conn, self.consistency, self.t_replica, self.variables, self.lock)
                t_serverThread.daemon = True
                t_serverThread.start()
        except:
            print("Server crashed")


class Replica(multiprocessing.Process):
    """ 
        a replica server talks to other replicas
    """

    def __init__(self, id, variables, lock):
        super(Replica, self).__init__() # call __init__ from multiprocessing.Process
        self.id = id
        self.channel = None

        # Read config from file
        self.process_info, self.addr_dict = configreader.get_processes_info()
        address = self.process_info[id]
        ip, port = address[0], address[1]

        # Init a UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(address)
        self.lock = lock
        self.variables = variables
        self.W = 2
        self.R = 2
        self.w_ack = {}
        self.r_ack = {}
       
    # Init replica channel to be total order
    def setChannel(self): 
        print 'total ordering'
        # Total Order Channel
        if self.id == 1:
            # Select process 1 to be the sequencer
            self.channel = TotalOrderChannel(self, self.id, self.socket, self.process_info, self.addr_dict, self.variables, True)
        else:
            self.channel = TotalOrderChannel(self, self.id, self.socket, self.process_info, self.addr_dict, self.variables)

    # receive message, override run()
    def run(self):
        setChannel()
        try:
            while True:
                data, address = self.socket.recvfrom(4096)
                self.channel.recv(data, address)
        except:
            print("Disconnected from server replicas")

    # unicast_receive(int, Message)
    def unicast_receive(self, source, message, client_port, var, action):
        print (message.receive_str())
        if (action == "w"):
            self.w_ack[(client_port, var)] += 1
            if (self.w_ack[(client_port, var)] >= self.W):


    def unicast(self, destination, message):
        self.channel.unicast(message, destination)

    def multicast(self, message):
        self.channel.multicast(message)


def main():
    parser = argparse.ArgumentParser(description="replica server")
    parser.add_argument("id", help="process id, default=1", type=int, default=1)
    parser.add_argument("consistency", help="consistency model, default=eventual consistency", type=str, default='eventual')
    args = parser.parse_args()
    variables = VariableStored()
    lock = multiprocessing.Lock()

    # start process thread
    t_replica = Replica(args.id, variables, lock)
    t_replica.daemon = True # daemon thread does not prevent main program from exiting
    t_replica.start()

    # start server thread
    t_server = Server(args.id, t_replica, args.consistency, variables, lock)
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
                elif cmd_args[0] == "send":
                    destination, message = int(cmd_args[1]), cmd_args[2]
                    # call unicast()
                    t_replica.unicast(destination, message)
                elif cmd_args[0] == "msend":
                    message = cmd_args[1]
                    # call multicast
                    t_replica.multicast(message)
    except KeyboardInterrupt:
        print("CTRL C occured")

if __name__ == '__main__':
    main()
