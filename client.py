import multiprocessing
from threading import Thread
import socket
import argparse
import configreader
from channel import Channel
from totalOrderChannel import TotalOrderChannel
from variableStored import VariableStored


class Client(multiprocessing.Process):
    """
        a client sends requests to a server
    """

    def __init__(self, id):
        super(Client, self).__init__() # call __init__ from multiprocessing.Process
        self.id = id

        # Read config from file
        # process_info[id] = (ip, port), addr_dict[(ip, port)] = id
        self.process_info, self.addr_dict = configreader.get_processes_info()
        self.total_server = configreader.get_total_servers()
        self.address = self.process_info[self.id]
        self.ip, self.port = address[0], address[1]
        self.s = None
        self.channel = None
        self.batch_cmd = None

        
    # Init channel   
    def setChannel(self):
            # client only has Regular channel
            print 'client, no ordering'
            # pass Process obj as arg to Channel
            self.channel = Channel(self, self.id, self.socket, self.process_info, self.addr_dict)

    # init TCP connect to server
    def tcpConn(self):
        self.address = self.process_info[self.id]
        self.ip, self.port = address[0], address[1]
        for res in socket.getaddrinfo(self.ip, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.s = socket.socket(af, socktype, proto) # build a socket
            except socket.error as msg:
                self.s = None
                continue
            try:
                self.s.connect(sa) # connect to socket 
            except socket.error as msg:
                self.s.close()
                self.s = None
                continue
            break
        if self.s is None:
            print('could not open socket')
            sys.exit(1)

    # receive message, override run()
    def run(self):
        try:
            tcpConn(self)
            setChannel(self)
            while True:
                data, address = self.s.recvfrom(4096)
                if not data:
                    break
                self.channel.recv(data, address)
        except:
            print("Disconnected from server")
            # handle server crash: pick a server with higher id
            # redo run()
            self.id = (id + 1) % total_server
            run()
            
    # unicast_receive(int, Message)
    def unicast_receive(self, source, message):
        print (message.receive_str())

    def unicast(self, destination, message):
        self.channel.unicast(message, destination)

    # addBatchCmd keeps adding commands
    def addBatchCmd(self):
        while True:
            self.batch_cmd += raw_input()

    # executeBatchCmd execute each command line received during delay
    def executeBatchCmd(self):
        if (self.batch_cmd):
            for cmd in self.batch_cmd.splitlines():
                parseCommand(cmd)
        self.batch_cmd = None

    # execute a command
    def parseCommand(self, cmd):
        cmd_args = cmd.split()
        # write value to variable
        if cmd_args[0] == "put":
            var_name, value = cmd_args[1], int(cmd_args[2])
            unicast(self.id, cmd)
        # get variable's value and print to stdout
        elif cmd_args[0] == "get":
            var_name = cmd_args[1]
            unicast(self.id, cmd)
        # delay input to allow a batch of commands
        elif cmd_args[0] == "delay":
            sleep_time = cmd_args[1]
            t_batchCmd = Thread(target = addBatchCmd, args=())
            t_batchCmd.start()
            # wait until thread timeout
            t_batchCmd.join(sleep_time / 1000)
            executeBatchCmd()
        # requests server to print all variables to stdout
        elif cmd_args[0] == "dump":
            unicast(self.id, cmd)


def main():
    parser = argparse.ArgumentParser(description="client")
    parser.add_argument("id", help="server id, default=1", type=int, default=1)
    args = parser.parse_args()

    # init client thread
    p = Client(args.id)
    # daemon thread does not prevent main program from exiting
    p.daemon = True 
    p.start()

    try:
        while True:
            cmd = raw_input()
            if cmd:
                cmd_args = cmd.split()
                if cmd_args[0] == "exit": 
                    break;
                p.parseCommand(cmd)
    except KeyboardInterrupt:
        print("CTRL C occured")

if __name__ == '__main__':
    main()
