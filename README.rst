Key-Value Store Consistency
===========================

Replication is a key to providing high availability and fault tolerance in distributed
systems. Here we implemented a Key-Value Store with replicated servers to meet these two important properties. Our implementation meets the correctness criteria of linearizability and sequential consistency.

Processes
----------
::

	1. server.py
	2. client.py

Consistency Models
-------------------
::

	1. eventualConsistency.py
	2. linearizabilityConsistency.py


To Run
------
::

	Server:

	usage: server.py [-h] id consistency W R

	positional arguments:

		id           process id (1-10), default=1
		consistency  consistency model (eventual/linearizability), default=eventual
		W            number of w_ack indicates finished, default=1
		R            number of r_ack indicates finished, default=1

	serverID = 1 indicates sequencer

	Client:

	usage: client.py [-h] serverID

	positional arguments:
	  
		serverID    server id, default=1

	Note that log file 'output_log*.txt' will be created in the same directory. 
	New log info will be appended to the previous log file, you can delete 
	log files before start the new run.

	
Quick Start
-----------
::
	
	1. Eventual Consistency:

	Start servers at different terminals:
	>> python server.py 1 eventual 2 2
	>> python server.py 2 eventual 2 2

	Start clients at different terminals:
	>> python client.py 2
	>> python client.py 2

	2. Linearizability Consistency:

	Start servers at different terminals:
	>> python server.py 1 linearizability 2 2
	>> python server.py 2 linearizability 2 2

	Start clients at different terminals:
	>> python client.py 2
	>> python client.py 2

	3. Test server crash:

	Start servers at different terminals:
	>> python server.py 1 eventual 2 2
	>> python server.py 2 eventual 2 2

	Start clients at different terminals:
	>> python client.py 2

	Then kill server2, after which client should be able to connect to 
	server1 automatically.

	4. Test 'delay [ms]' to allow multipule command lines:
		Start servers at different terminals:
	>> python server.py 1 eventual 2 2
	>> python server.py 2 eventual 2 2

	Start clients at different terminals:
	>> python client.py 2
	>> delay 10000
	>> get x
	>> put x 1
	>> get x

	5. Test 'dump' to show all variables status on server side:
	>> python server.py 1 eventual 2 2
	>> python server.py 2 eventual 2 2

	Start clients at different terminals:
	>> python client.py 2
	>> dump

