class SilentLogger():

	def logInfo(self, text):
		pass

	def logWarning(self, text):
		pass

	def logError(self, text):
		pass

_logger = SilentLogger()

def setLogger(logger):
	global _logger
	_logger = logger

def logInfo(text):
	_logger.logInfo(text)

def logWarning(text):
	_logger.logWarning(text)

def logError(text):
	_logger.logError(text)