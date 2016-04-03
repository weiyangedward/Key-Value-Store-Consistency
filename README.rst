Key-Value Store Consistency
===========================

Processes
----------
::

	1. server.py
	2. client.py

Consistency Models
-------------------
::

	1. eventualConsistency.py
	2. linearizability.py


To Run
------
::

	Server:

	python server.py [serverID] [consistency model (eventual/linearizability)] [W] [R]

	serverID = 1 indicates sequencer

	Client:

	python client.py [serverID]


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

