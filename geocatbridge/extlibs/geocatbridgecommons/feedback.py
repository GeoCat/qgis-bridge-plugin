class SilentFeedbackReporter():

    def setProgress(self, progress):
        pass

    def setText(self, text):
    	pass


_feedback = SilentFeedbackReporter()

def setFeedbackIndicator(feed):
	global _feedback
	_feedback = feed

def setProgress(progress):
	_feedback.setProgress(progress)

def setText(text):
	_feedback.setText(text)