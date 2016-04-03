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
        self.serverID = serverID - 1 # (0,9)
        self.client_id = client_id

        """
            Read config from file
            process_info[id] = (ip, port)
            addr_dict[(ip, port)] = id
        """
        self.process_info, self.addr_dict = configreader.get_processes_info()
        self.total_server = configreader.get_total_servers()
        self.address = self.process_info[self.serverID+1]
        self.ip, self.port = self.address[0], self.address[1]
        self.batch_cmd = ''
        self.client_id = client_id
        self.reconnect_try = 0

        """
            init TCP connect to server
        """
        self.address = self.process_info[self.serverID+1]
        self.ip, self.port = self.address[0], self.address[1]
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
            Init unicast channel
        """
        print 'client, no ordering'
        # pass Client obj as arg to Channel
        self.channel = Channel(self, self.client_id, self.socket, self.process_info, self.addr_dict)

    def socketTCP(self):
        self.address = self.process_info[self.serverID+1]
        self.ip, self.port = self.address[0], self.address[1]
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
        else:
            print("successfully connected to server %d" % (self.serverID+1))

    def channelSet(self):
        self.channel = Channel(self, self.client_id, self.socket, self.process_info, self.addr_dict)
            # sys.exit(1)

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
        except KeyboardInterrupt:
            print("CTRL C occured")
        except:
            print("Disconnected from server")
            # ====
            # choose another server if the connected server is crashed
            # handle server crash: pick a server with higher id
            # relaunch run()
            # ====
            
        finally:
            print("exit client thread")
            if self.socket != None: self.socket.close()
            if (self.reconnect_try < self.total_server * 10):
                print("Trying to connect to next server...")
                self.reconnect_try += 1
                self.serverID = (self.serverID + 1) % (self.total_server)
                print("Trying to connect to next server %d" % (self.serverID+1))
                self.socketTCP()
                self.channelSet()
                self.run()
            else:
                print("Hit maximum attempts, please enter 'exit'")
            
        # except:

               # ====
               # choose another server if the connected server is crashed
               # handle server crash: pick a server with higher id
               # relaunch run()
               # ====

            # print("Disconnected from server")
        # try:
        #     self.serverID = (self.serverID + 1) % self.total_server
        #     self.run()
        # except:
        #     print("cannot connect to server")
            
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
        print("addBatchCmd...")
        try:
            while True:
                self.batch_cmd += raw_input()
        except:
            print("timeout")

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
        cmd_args = cmd.split()
        # write value to variable
        if cmd_args[0] == "put" and len(cmd_args) == 3:
            var_name, value = cmd_args[1], int(cmd_args[2])
            message = str(self.client_id) + " " + cmd
            self.channel.unicastTCP(self.serverID, message)
        # get variable's value and print to stdout
        elif cmd_args[0] == "get" and len(cmd_args) == 2:
            var_name = cmd_args[1]
            message = str(self.client_id) + " " + cmd
            self.channel.unicastTCP(self.serverID, message)
        # delay input to allow a batch of commands
        elif cmd_args[0] == "delay" and len(cmd_args) == 2:
            sleep_time = float(cmd_args[1])
            # t_batchCmd = Thread(target = self.addBatchCmd, args=())
            # t_batchCmd.start()
            t_batchCmd = multiprocessing.Process(target=self.addBatchCmd, args=())
            t_batchCmd.start()
            # wait until thread timeout
            time.sleep(sleep_time / 1000.0)
            # t_batchCmd.join(sleep_time / 1000.0)
            t_batchCmd.terminate()
            self.executeBatchCmd()
        # requests server to print all variables to stdout
        elif cmd_args[0] == "dump" and len(cmd_args) == 1:
            message = str(self.client_id) + " " + cmd
            self.channel.unicastTCP(self.serverID, message)
        else:
            print("command not understood, enter new command:")


def main():
    parser = argparse.ArgumentParser(description="client")
    parser.add_argument("serverID", help="server id, default=1", type=int, default=1)
    args = parser.parse_args()

    """
        init client thread
    """
    client_id = random.randint(1, 999999) # generate a random id for client
    p = Client(client_id, args.serverID)
    # daemon thread does not prevent main program from exiting
    p.daemon = True 
    p.start()

    # try:
    while True:
        print("waiting for command: ")
        cmd = raw_input()
        if cmd:
            cmd_args = cmd.split()
            if cmd_args[0] == "exit": break
            p.parseCommand(cmd)
    # except KeyboardInterrupt:
    #     print("CTRL C occured")
    # finally:
    print("exit client process")
    p.terminate()

if __name__ == '__main__':
    main()
