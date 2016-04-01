"""
    
    def main():
        1. parse args
        2. init a Client obj
        3. launch a thread for Client obj
        4. main() thread keeps getting command from user
        and pass command to Client thread 


    class Client(derived from multiprocessing.Process):

        def __init__(serverID):
            get server Address, Port info from configreader

        def setChannel():
            set client channel to be unicast

        def tcpConn():
            use TCP socket to connect to server

        def run():
            1. this function will be invoked at init of Client obj
            2. call function setChannel() and tcpConn()
            3. while (receiving message from server):
                if server not crashed:
                    use channel.recv() to handle message
                else:
                    break
            4. choose another server
            5. relaunch run()

        def parseCommand(cmd):
            This function parse user command and sends message to server,
            server will need to parse the message once it arrives

            if "put":
                use channel.unicastTCP(serverID, self.socket, cmd)
            elif "get":
                use channel.unicastTCP(serverID, self.socket, cmd)
            elif "delay":
                init a batch thread to accept multi-line commands from user
                set timeout for thread to join(), during which the Client
                thread will have to wait
                after join(), call parseCommand to parse batch commands line-by-line
            elif "dump":
                use channel.unicastTCP(serverID, self.socket, cmd)




"""

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

    def __init__(self, client_id, serverID):
        super(Client, self).__init__() # call __init__ from multiprocessing.Process
        self.serverID = serverID
        self.client_id = client_id

        """
            Read config from file
            process_info[id] = (ip, port)
            addr_dict[(ip, port)] = id
        """
        self.process_info, self.addr_dict = configreader.get_processes_info()
        self.total_server = configreader.get_total_servers()
        self.address = self.process_info[self.serverID]
        self.ip, self.port = address[0], address[1]
        self.socket = None # TCP socket
        self.channel = None
        self.batch_cmd = None
        self.client_id = client_id

    """
        Init unicast channel
    """
    def setChannel(self):
            # client only has Regular channel
            print 'client, no ordering'
            # pass Client obj as arg to Channel
            self.channel = Channel(self, self.client_id, self.socket, self.process_info, self.addr_dict)
    
    """
        init TCP connect to server
    """
    def tcpConn(self):
        self.address = self.process_info[self.serverID]
        self.ip, self.port = address[0], address[1]
        for res in socket.getaddrinfo(self.ip, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.socket = socket.socket(af, socktype, proto) # build a socket
            except socket.error as msg:
                self.socket = None
                continue
            try:
                self.socket.connect(sa) # connect to socket 
            except socket.error as msg:
                self.socket.close()
                self.socket = None
                continue
            break
        if self.socket is None:
            print('could not open socket')
            sys.exit(1)

    """
        override run(), receiving message from server
    """
    def run(self):
        try:
            tcpConn(self)
            setChannel(self)
            while True:
                data, address = self.socket.recvfrom(4096)
                # break if connected server crashed
                if not data:
                    break
                self.channel.recv(data, address)
        except:
            # choose another server if the connected server is crashed
            # handle server crash: pick a server with higher id
            # relaunch run()
            print("Disconnected from server")
            self.serverID = (serverID + 1) % total_server
            run()
            
    """
        unicast_receive(int, Message)
    """
    # def unicast_receive(self, source, message):
    #     print (message.receive_str())

    """
        unicast(int, Message)
    """
    def unicast(self, destination, message):
        self.channel.unicast(message, destination)

    """
        handle 'delay'
        addBatchCmd keeps adding commands
    """
    def addBatchCmd(self):
        while True:
            self.batch_cmd += raw_input()

    """
        handle 'delay'
        executeBatchCmd execute each command line received during delay
    """
    def executeBatchCmd(self):
        if (self.batch_cmd):
            for cmd in self.batch_cmd.splitlines():
                parseCommand(cmd)
        self.batch_cmd = None

    """
        execute user commands from std-input
    """
    def parseCommand(self, cmd):
        cmd_args = cmd.split()
        # write value to variable
        if cmd_args[0] == "put":
            var_name, value = cmd_args[1], int(cmd_args[2])
            self.channel.unicastTCP(self.serverID, self.socket, str(self.client_id) + " " + cmd)
        # get variable's value and print to stdout
        elif cmd_args[0] == "get":
            var_name = cmd_args[1]
            self.channel.unicastTCP(self.serverID, self.socket, str(self.client_id) + " " + cmd)
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
            self.channel.unicastTCP(self.serverID, self.socket, str(self.client_id) + " " + cmd)


def main():
    parser = argparse.ArgumentParser(description="client")
    parser.add_argument("serverID", help="server id, default=1", type=int, default=1)
    args = parser.parse_args()

    """
        init client thread
    """
    client_id = random.uniform(1, sys.maxint) # generate a random id for client
    p = Client(client_id, args.serverID)
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
