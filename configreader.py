# This is a helper function which read process parameters from files.
def read_config(para):
    with open('config', 'r') as f:
        min_delay, max_delay = 0, 0
        processes = {}
        addr_dict = {}
        total_servers = 0 # total number of server replicas
        for i, line in enumerate(f):
            try:
                args = line.split()
                if i == 0:
                    min_delay, max_delay = int(args[0]), int(args[1])
                else:
                    total_servers += 1
                    id, ip, port = int(args[0]), args[1], int(args[2])
                    processes[id] = (ip, port)
                    addr_dict[(ip, port)] = id
            except:
                print("empty line")

        if para == 'processes':
            return processes, addr_dict
        elif para == 'delay':
            return min_delay, max_delay
        elif para == 'totalServers':
            return total_servers


def get_processes_info():
    return read_config('processes')

def get_delay_info():
    return read_config('delay')

def get_total_servers():
    return read_config('totalServers')