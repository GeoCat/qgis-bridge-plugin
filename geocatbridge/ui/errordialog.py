import webbrowser
from urllib import parse

from qgis.PyQt.QtGui import QPixmap, QIcon
from qgis.core import QgsMessageLog
from requests.models import PreparedRequest

from geocatbridge.utils.gui import loadUiType
from geocatbridge.utils.meta import getTrackerUrl, getAppName
from geocatbridge.utils.files import getIconPath

WIDGET, BASE = loadUiType(__file__)


class ErrorDialog(BASE, WIDGET):

    def __init__(self, html_error, md_error):
        super(ErrorDialog, self).__init__()
        self.setupUi(self)

        self.setWindowTitle(f"{getAppName()} Publish Report")
        self.setWindowIcon(QIcon(getIconPath('geocat')))
        pixmap = QPixmap(getIconPath("bridge_logo"))
        self.labelIcon.setPixmap(pixmap)
        self.label.setText(f"The {getAppName()} plugin has caused the following exception:")

        self.txtError.setHtml(html_error)

        tracker_url = getTrackerUrl()
        if not tracker_url:
            self.btnSendReport.setEnabled(False)
        else:
            self.btnSendReport.clicked.connect(lambda: self.sendReport(md_error, tracker_url))
        self.btnClose.clicked.connect(self.close)

    def sendReport(self, error, tracker_url):
        """ Copies the given stacktrace in a GeoCat support form. """
        payload = {
            "subject": "[Crash Report] GeoCat Bridge for QGIS",
            "message": error
        }
        req = PreparedRequest()
        try:
            req.prepare("GET", tracker_url, params=parse.urlencode(payload, quote_via=parse.quote))
            webbrowser.open_new_tab(req.url)
        except Exception as e:
            QgsMessageLog().logMessage(f"Failed to send crash report: {e}", 'GeoCat Bridge')
