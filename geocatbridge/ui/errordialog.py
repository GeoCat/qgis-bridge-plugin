import webbrowser
from urllib import parse

from qgis.core import QgsApplication
from requests.models import PreparedRequest

from geocatbridge.utils.gui import loadUiType, getSvgIcon
from geocatbridge.utils import meta, feedback

WIDGET, BASE = loadUiType(__file__)


class ErrorDialog(BASE, WIDGET):

    def __init__(self, md_error: str):
        super(ErrorDialog, self).__init__()
        self.setupUi(self)

        self.setWindowTitle(meta.getLongAppName())
        self.setWindowIcon(getSvgIcon('bridge_icon'))
        self.label.setText(f"The {meta.getAppName()} plugin has caused the following exception:")

        self.txtError.setMarkdown(md_error)

        github_url = self.getGitHubIssueUrl()
        if not github_url:
            feedback.logWarning(f"Issue tracker not set to a valid GitHub URL - please check metadata.txt")
            self.btnSendReport.setEnabled(False)
        else:
            self.btnSendReport.clicked.connect(lambda: self.sendReport(md_error, github_url))
        self.btnCopyToClipboard.clicked.connect(lambda: self.copyToClipboard)
        self.btnClose.clicked.connect(self.close)

    @staticmethod
    def getGitHubIssueUrl() -> str:
        """ Retrieves and validates the GitHub issue tracker URL. """
        url = meta.getTrackerUrl()
        parsed_url = parse.urlparse(url)
        if parsed_url.hostname.endswith("github.com") and parsed_url.path.endswith("/issues"):
            return url
        return ""

    @staticmethod
    def sendReport(md_error: str, github_url: str):
        """ Copies the given Markdown error description into a GitHub issue form. """

        # GitHub issues can be created from URLs like:
        # https://github.com/owner/repo/issues/new?title=...&body=...&labels=...,...,...
        github_url += "/new"
        q = {
            "body": md_error,
            "labels": "bug"
            # NOTE: GitHub also allows "title" here, but we leave it out on purpose:
            # As this is a required field, this forces users to provide a (hopefully) meaningful title.
        }
        req = PreparedRequest()
        try:
            req.prepare("GET", github_url, params=parse.urlencode(q, quote_via=parse.quote))
            webbrowser.open_new_tab(req.url)
        except Exception as e:
            feedback.logError(f"Failed to send crash report: {e}")

    def copyToClipboard(self):
        """ Copies the error message to the clipboard. """
        clipboard = QgsApplication.clipboard()
        clipboard.setText(self.txtError.toPlainText())
