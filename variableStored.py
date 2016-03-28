class VariableStored(object):
	"""
		stores all variables and their values in server replicas
	"""
	def __init__(self):
		self.variables = {}
		for var_ascii in range(97,(97+26)):
			var_chr = str(unichr(var_ascii))
			self.variables[var_chr] = 0 # e.g., 'a' = 0

	# write(x,val)
	def put(self, var_chr, value):
		if (var_chr in self.variables):
			self.variables[var_chr] = value
			"""
				send write(x,val) to other servers
				collect ack()
				log finish write 
			"""
		else:
			print("variable %s not found" % (var_chr))

	# read(x)
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

	def dump(self, id):
		print("Dumping server %d variables:" % (id))
		for var_ascii in range(97,(97+26)):
			var_chr = str(unichr(var_ascii))
			print(self.variables[var_chr])