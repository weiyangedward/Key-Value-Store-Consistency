class VariableStored(object):
	"""
	stores all variables and their values in server replicas
	"""

	def __init__(self):
		self.variables = dict() # var value
		self.lastWrite = dict() # last-write timepoint
		self.r_ack = dict() # number of received r_ack for var
		self.w_ack = dict() # number of received w_ack for var
		# self.messageID2client = dict()
		for var_ascii in range(97,(97+26)):
			var_chr = str(unichr(var_ascii))
			self.variables[var_chr] = 0 # e.g., 'a' = 0
			self.lastWrite[var_chr] = 0
			self.r_ack[var_chr] = 0
			self.w_ack[var_chr] = 0

	"""
		write to var
		write(x, value, timepoint)
	"""


	def put(self, var_chr, value, timepoint):
		if (var_chr in self.variables):
			self.variables[var_chr] = value
			self.lastWrite[var_chr] = timepoint
			"""
				send write(x,val) to other servers
				collect ack()
				log finish write
			"""
		else:
			print("variable %s not found" % (var_chr))

	"""
		return last-write timepoint
	"""
	def lastWriteTime(self, var_chr):
		if (var_chr in self.variables):
			return self.lastWrite[var_chr]
		else:
			print("variable %s not found" % (var_chr))

	def setRAck(self, var_chr, ackNum):
		if (var_chr in self.variables):
			self.r_ack[var_chr] = ackNum
		else:
			print("variable %s not found" % (var_chr))

	def setWAck(self, var_chr, ackNum):
		if (var_chr in self.variables):
			self.w_ack[var_chr] = ackNum
		else:
			print("variable %s not found" % (var_chr))

	def getRAck(self, var_chr):
		if (var_chr in self.variables):
			return self.r_ack[var_chr]
		else:
			print("variable %s not found" % (var_chr))

	def getWAck(self, var_chr):
		if (var_chr in self.variables):
			return self.w_ack[var_chr]
		else:
			print("variable %s not found" % (var_chr))

	"""
		read(x)
	"""
	def get(self, var_chr):
		if (var_chr in self.variables):
			"""
				send read(x) to other servers
				collect ack()
				return oldest
			"""
			return self.variables[var_chr]
		else:
			print("variable %s not found" % (var_chr))

	"""
		print all var info to stdout
	"""
	def dump(self, id):
		print("Dumping server %d variables:" % (id))
		for var_ascii in range(97,(97+26)):
			var_chr = str(unichr(var_ascii))
			print(var_chr, self.variables[var_chr])

