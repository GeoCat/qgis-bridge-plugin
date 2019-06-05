class SilentLogger():

	def logInfo(text):
		pass

	def logWarning(text):
		pass

	def logError(text):
		pass

_logger = SilentLogger()

def setLogger(logger):
	_logger = logger

def logInfo(text):
	_logger.logInfo(text)

def logWarning(text):
	_logger.logWarning(text)

def logError(text):
	_logger.logError(text)