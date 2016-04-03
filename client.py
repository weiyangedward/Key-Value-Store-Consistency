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
import random
import sys
import time
import multiprocessing
from threading import *
import socket
import argparse
import configreader
from channel import Channel
from variableStored import VariableStored


class Client(multiprocessing.Process):
    """
        a client sends requests to a server
    """

    def __init__(self, client_id, serverID):
        super(Client, self).__init__() # call __init__ from multiprocessing.Process

        # a shared variable to show serverID
        self.server_id = multiprocessing.Value('i', 0)
        with self.server_id.get_lock():
            self.server_id.value = serverID + 1 # (1,10)

        # a shared variable to show socket status
        self.socket_status = multiprocessing.Value('i', 0)
        with self.socket_status.get_lock():
            self.socket_status.value = 0

        """
            Read config from file
            process_info[id] = (ip, port)
            addr_dict[(ip, port)] = id
        """
        self.process_info, self.addr_dict = configreader.get_processes_info()
        self.total_server = configreader.get_total_servers()
        self.batch_cmd = ''
        self.reconnect_try = 0
        self.client_id = client_id
        # self.exit = sys.exit()

        """
            init TCP connect to server
        """
        with self.server_id.get_lock():
            self.address = self.process_info[self.server_id.value]
        self.ip, self.port = self.address[0], self.address[1]
        # print(self.ip, self.port)
        for res in socket.getaddrinfo(self.ip, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.socket = socket.socket(af, socktype, proto) # build a socket
                with self.socket_status.get_lock():
                    self.socket_status.value = 1
            except socket.error as msg:
                self.socket = None
                with self.socket_status.get_lock():
                    self.socket_status.value = 0
                continue
            try:
                self.socket.connect(sa) # connect to socket 
            except socket.error as msg:
                self.socket.close()
                self.socket = None
                with self.socket_status.get_lock():
                    self.socket_status.value = 0
                continue
            break
        if self.socket is None:
            print('could not open socket')
            sys.exit(1)

        """
            Init unicast channel
        """
        print("client, no ordering")
        # pass Client obj as arg to Channel
        self.channel = Channel(self, self.client_id, self.socket, self.process_info, self.addr_dict)


    """
        override run(), receiving message from server
    """
    def run(self):
        try:

            while True:
                data, address = self.socket.recvfrom(4096)
                print("get server message: ", data, address)
                # break if connected server crashed
                if not data: break
                self.channel.recv(data)
        except:
            print("run() Exceptions")
        finally:
            print("exit client thread")
            if self.socket != None: 
                self.socket.close()
                self.socket = None
                with self.socket_status.get_lock():
                    self.socket_status.value = 0 # set socket_status to be not available


    """
        handle 'delay'
        addBatchCmd keeps adding commands
    """
    def addBatchCmd(self):
        print("addBatchCmd...")
        try:
            while True:
                self.batch_cmd += input()
        except:
            pass

    """
        handle 'delay'
        executeBatchCmd execute each command line received during delay
    """
    def executeBatchCmd(self):
        print("executeBatchCmd...")
        if (self.batch_cmd):
            for cmd in self.batch_cmd.splitlines():
                self.parseCommand(cmd)
        self.batch_cmd = ''

    """
        execute user commands from std-input
    """
    def parseCommand(self, cmd):
        print("parseCommand...")
        socket_status = 0
        with self.socket_status.get_lock():
            socket_status = self.socket_status.value
        if socket_status == 1: # if socket is still connected
            serverID = 0
            with self.server_id.get_lock():
                serverID = self.server_id.value
            print("serverID ", str(serverID))
            cmd_args = cmd.split()
            # write value to variable
            if cmd_args[0] == "put" and len(cmd_args) == 3:
                var_name, value = cmd_args[1], int(cmd_args[2])
                message = str(self.client_id) + " " + cmd
                self.channel.unicastTCP(serverID, message)
            # get variable's value and print to stdout
            elif cmd_args[0] == "get" and len(cmd_args) == 2:
                var_name = cmd_args[1]
                message = str(self.client_id) + " " + cmd
                self.channel.unicastTCP(serverID, message)
            # delay input to allow a batch of commands
            elif cmd_args[0] == "delay" and len(cmd_args) == 2:
                sleep_time = float(cmd_args[1])
                t_batchCmd = multiprocessing.Process(target = self.addBatchCmd, args=())
                t_batchCmd.start()
                # wait until thread timeout
                time.sleep(sleep_time / 1000.0)
                t_batchCmd.terminate()
                print("timeout")
                self.executeBatchCmd()
            # requests server to print all variables to stdout
            elif cmd_args[0] == "dump" and len(cmd_args) == 1:
                message = str(self.client_id) + " " + cmd
                self.channel.unicastTCP(serverID, message)
            else:
                print("command not understood, enter new command:")
            return 1 # return server available signal to main
        else:
            return 0 # return server crash signal to main

# function to start a client thread, the client obj will be returned
# This function call will crash if not able to create TCP socket between
# client and a server, which will in turn triggle crash handling
def startClientMain(client_id, serverID, total_server, reconnect_try):
    p = Client(client_id, serverID)
    p.daemon = True
    p.start()
    return p


def main():
    parser = argparse.ArgumentParser(description="client")
    parser.add_argument("serverID", help="server id, default=1", type=int, default=1)
    args = parser.parse_args()
    total_server = configreader.get_total_servers()
    serverID = args.serverID - 1 # (0,9)
    reconnect_try = 0
    p = None
    """
        init client thread
    """
    client_id = random.randint(1, 999999) # generate a random id for client
    
    # try to connect to server
    while True:
        try:
            p = startClientMain(client_id, serverID, total_server, reconnect_try)
            if p != None: break
        except:
            print("cannot connect to server %d " % (serverID+1))
            if reconnect_try <= (total_server+1): # try 10+1 times if there are 10 servers
                reconnect_try += 1
                serverID = (serverID + 1) % total_server
            else:
                break

    # reset try times
    reconnect_try = 0

    # if no server connected, then aborted
    if (p != None):
        try:
            while True:
                print("waiting for command: ")
                cmd = raw_input()
                if cmd:
                    cmd_args = cmd.split()
                    if cmd_args[0] == "exit": break
                    try:
                        signal = p.parseCommand(cmd)
                        print("signal ", signal)
                        # signal = 1 if server available, 0 otherwise
                        if not signal:
                            # loop until next available server is found, or hit max attempts
                            while True:
                                try:
                                    print("try to connect ", serverID+1)
                                    p = None
                                    p = startClientMain(client_id, serverID, total_server, reconnect_try)
                                    if p != None: 
                                        print("successfully connected to server %d, please re-enter your last command" % (serverID+1))
                                        reconnect_try = 0 # reset try times
                                        break
                                except:
                                    print("cannot connect to server %d " % (serverID+1))
                                    if reconnect_try <= (total_server+1): # try 10+1 times if there are 10 servers
                                        reconnect_try += 1
                                        serverID = (serverID + 1) % total_server
                                    else: break
                    except:
                        print("server not connected")
        except:
            print("main() Exceptions")
        finally:
            print("exit client process")
            if p != None: p.terminate()
    else:
        print("server not available")        


if __name__ == '__main__':
    main()
