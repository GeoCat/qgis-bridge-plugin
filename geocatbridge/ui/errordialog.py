import webbrowser
from urllib import parse

from qgis.core import QgsMessageLog
from requests.models import PreparedRequest

from geocatbridge.utils.gui import loadUiType, getSvgIcon
from geocatbridge.utils import meta

WIDGET, BASE = loadUiType(__file__)


class ErrorDialog(BASE, WIDGET):

    def __init__(self, md_error: str):
        super(ErrorDialog, self).__init__()
        self.setupUi(self)

        self.setWindowTitle(meta.getLongAppName())
        self.setWindowIcon(getSvgIcon('bridge_icon'))
        self.label.setText(f"The {meta.getAppName()} plugin has caused the following exception:")

        self.txtError.setMarkdown(md_error)

        support_url = meta.getSupportUrl()
        if not support_url:
            self.btnSendReport.setEnabled(False)
        else:
            self.btnSendReport.clicked.connect(lambda: self.sendReport(md_error, support_url))
        self.btnClose.clicked.connect(self.close)

    def sendReport(self, error, support_url):
        """ Copies the given stacktrace in a GeoCat support form. """

        error = f"[please add context here]  \n\n{error}"
        payload = {
            "subject": f"[Crash Report] {meta.getLongAppName()}",
            "message": error
        }
        req = PreparedRequest()
        try:
            req.prepare("GET", support_url, params=parse.urlencode(payload, quote_via=parse.quote))
            webbrowser.open_new_tab(req.url)
        except Exception as e:
            QgsMessageLog().logMessage(f"Failed to send crash report: {e}", meta.getAppName())
