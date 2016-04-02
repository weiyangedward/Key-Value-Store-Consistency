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
	
Quick Start
-----------
::
	
	Start servers:
	>> python server.py 1 eventual 2 2
	>> python server.py 2 eventual 2 2

	Start clients:
	>> python client.py 2
	>> python client.py 2

