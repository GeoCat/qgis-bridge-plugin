import webbrowser
from urllib import parse

from qgis.core import QgsMessageLog
from requests.models import PreparedRequest

from geocatbridge.utils.gui import loadUiType, getSvgIcon
from geocatbridge.utils.meta import getSupportUrl, getAppName

WIDGET, BASE = loadUiType(__file__)


class ErrorDialog(BASE, WIDGET):

    def __init__(self, html_error, md_error):
        super(ErrorDialog, self).__init__()
        self.setupUi(self)

        self.setWindowTitle(f"{getAppName()} Error Report")
        self.setWindowIcon(getSvgIcon('geocat_icon'))
        self.btnGeoCat.setIcon(getSvgIcon('geocat_logo'))
        self.label.setText(f"The {getAppName()} plugin has caused the following exception:")

        self.txtError.setHtml(html_error)

        support_url = getSupportUrl()
        if not support_url:
            self.btnSendReport.setEnabled(False)
        else:
            self.btnSendReport.clicked.connect(lambda: self.sendReport(md_error, support_url))
        self.btnClose.clicked.connect(self.close)

    def sendReport(self, error, support_url):
        """ Copies the given stacktrace in a GeoCat support form. """
        payload = {
            "subject": f"[Crash Report] {getAppName()} for QGIS",
            "message": error
        }
        req = PreparedRequest()
        try:
            req.prepare("GET", support_url, params=parse.urlencode(payload, quote_via=parse.quote))
            webbrowser.open_new_tab(req.url)
        except Exception as e:
            QgsMessageLog().logMessage(f"Failed to send crash report: {e}", getAppName())
