import webbrowser
from functools import partial

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtWebKitWidgets import QWebPage

from geocatbridge.utils import gui, meta
from geocatbridge.utils.files import getAboutUrl

WIDGET, BASE = gui.loadUiType(__file__)


class GeoCatWidget(WIDGET, BASE):

    def __init__(self, parent=None):
        super(GeoCatWidget, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)

        self.txtAbout.load(getAboutUrl())
        self.txtAbout.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.txtAbout.linkClicked.connect(partial(self.open_link))

        # Add version info
        name = meta.getLongAppName()
        version = meta.getVersion()
        if version and name:
            info_txt = f'{name} v{version}'
            aux_info = getattr(self.parent, 'info', None)
            if aux_info:
                info_txt += f'  \u2192  {aux_info}'
            self.txtInfo.setText(info_txt)

        self.btnClose.clicked.connect(parent.close)

    @staticmethod
    def open_link(url: QUrl) -> bool:
        return webbrowser.open_new_tab(url.toString())
