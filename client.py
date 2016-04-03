import random
import sys
import time
import multiprocessing
import socket
import argparse
import configreader
from channel import Channel


class Client(multiprocessing.Process):
    """
        a client sends requests to a server
    """

    def __init__(self, client_id, server_id):
        super(Client, self).__init__() # call __init__ from multiprocessing.Process

        # a shared variable to show serverID
        self.server_id = multiprocessing.Value('i', 0)
        with self.server_id.get_lock():
            self.server_id.value = server_id + 1 # (1,10)

        # a shared variable to show socket status
        self.socket_status = multiprocessing.Value('i', 0)
        with self.socket_status.get_lock():
            self.socket_status.value = 0

        # read process config from file
        self.process_info, self.addr_dict = configreader.get_processes_info()
        self.total_server = configreader.get_total_servers()
        self.batch_cmd = ''
        self.reconnect_try = 0
        self.client_id = client_id

        # init a TCP socket to connect to server
        with self.server_id.get_lock():
            self.address = self.process_info[self.server_id.value]
        self.ip, self.port = self.address[0], self.address[1]

        # robust way to find an available port
        for res in socket.getaddrinfo(self.ip, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.socket = socket.socket(af, socktype, proto)
                with self.socket_status.get_lock():
                    self.socket_status.value = 1
            except socket.error as msg:
                self.socket = None
                with self.socket_status.get_lock():
                    self.socket_status.value = 0
                continue
            try:
                self.socket.connect(sa)
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

        # init a unicast channel with delayed function, reuse code from MP1
        self.channel = Channel(self, self.client_id, self.socket, self.process_info, self.addr_dict)

    def run(self):
        try:
            while True:
                data, address = self.socket.recvfrom(4096)
                # print("receive server message: ", data, address)

                # break if connected server crashed
                if not data:
                    break

                self.channel.recv(data)
        except:
            print("run() Exceptions")
        finally:
            print("connected server crash")
            if self.socket:
                self.socket.close()
                self.socket = None
                with self.socket_status.get_lock():
                    self.socket_status.value = 0  # set socket_status to be not available

    # handle delay, add batch commands keeps adding commands
    def add_batch_cmd(self):
        print("add batch commands")
        try:
            while True:
                self.batch_cmd += input()
        except:
            pass

    # handle 'delay', execute batch commands execute each command line received during delay
    def execute_batch_cmd(self):
        print("execute batch commands")
        if self.batch_cmd:
            for cmd in self.batch_cmd.splitlines():
                self.parse_command(cmd)
        self.batch_cmd = ''

    #  execute user commands from std-input
    def parse_command(self, cmd):
        """
        :param cmd: user input command.
        :return: a signal with value 0 or 1.
                "1" represents the requested operation succeed. "O" means the connected server crash.
        """

        # read socket status
        with self.socket_status.get_lock():
            socket_status = self.socket_status.value

        if socket_status == 1:  # if socket is still connected
            with self.server_id.get_lock():
                server_id = self.server_id.value
            cmd_args = cmd.split()

            # put command
            if cmd_args[0] == "put" and len(cmd_args) == 3:
                message = str(self.client_id) + " " + cmd
                self.channel.unicast_tcp(server_id, message)

            # get command
            elif cmd_args[0] == "get" and len(cmd_args) == 2:
                message = str(self.client_id) + " " + cmd
                self.channel.unicast_tcp(server_id, message)

            # delay command: allow a batch of commands
            elif cmd_args[0] == "delay" and len(cmd_args) == 2:
                sleep_time = float(cmd_args[1])
                t_batch_cmd = multiprocessing.Process(target = self.add_batch_cmd, args=())
                t_batch_cmd.start()

                # wait until thread timeout
                time.sleep(sleep_time / 1000.0)
                t_batch_cmd.terminate()

                print("timeout")
                self.execute_batch_cmd()

            # dump command: requests server to print all variables to std out
            elif cmd_args[0] == "dump" and len(cmd_args) == 1:
                message = str(self.client_id) + " " + cmd
                self.channel.unicast_tcp(server_id, message)
            else:
                print("unable to recognize the command, enter new command:")
            return 1
        else:
            # return server crash signal to main
            return 0


# function to start a client thread, the client obj will be returned
# This function call will crash if not able to create TCP socket between
# client and a server, which will in turn trigger crash handling
def start_client_process(client_id, server_id):
    p = Client(client_id, server_id)
    p.daemon = True
    p.start()
    return p


def main():
    parser = argparse.ArgumentParser(description="client")
    parser.add_argument("serverID", help="server id, default=1", type=int, default=1)
    args = parser.parse_args()

    num_of_servers = configreader.get_total_servers()
    server_id = args.serverID - 1  # (0,9)
    reconnect_try = 0

    client_id = random.randint(1, 999999) # generate a random id for client
    
    # try to connect to server
    while True:
        try:
            p = start_client_process(client_id, server_id)
            if p:
                break
        except:
            print("cannot connect to server %d " % (server_id + 1))
            if reconnect_try <= (num_of_servers+1): # try 10+1 times if there are 10 servers
                reconnect_try += 1
                server_id = (server_id + 1) % num_of_servers
            else:
                break

    # reset try times
    reconnect_try = 0

    # if no server connected, then aborted
    if p:
        try:
            while True:
                print("please enter command ")
                cmd = raw_input()

                if cmd:
                    cmd_args = cmd.split()
                    if cmd_args[0] == "exit":
                        break
                    try:
                        signal = p.parse_command(cmd)
                        # signal = 1 when the connected server is available, 0 otherwise

                        if not signal:
                            # loop until next available server is found, or hit max attempts
                            while True:
                                try:
                                    print("try to connect ", server_id + 1)
                                    p = None
                                    p = start_client_process(client_id, server_id)
                                    if p:
                                        print("successfully connected to server %d, please re-enter your last command" % (server_id+1))
                                        reconnect_try = 0  # reset try times
                                        break
                                except:
                                    print("cannot connect to server %d " % (server_id + 1))
                                    if reconnect_try <= (num_of_servers+1): # try 10+1 times if there are 10 servers
                                        reconnect_try += 1
                                        server_id = (server_id + 1) % num_of_servers
                                    else:
                                        break
                    except:
                        print("server not connected")

        except:
            print("main() Exceptions")
        finally:
            print("exit client process")
            if p:
                p.terminate()
    else:
        print("server not available")        


if __name__ == '__main__':
    main()
