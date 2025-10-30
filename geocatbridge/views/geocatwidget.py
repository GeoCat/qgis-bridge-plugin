import webbrowser
from datetime import datetime
from functools import partial

from geocatbridge.utils import gui, meta

WIDGET, BASE = gui.loadUiType(__file__)


class GeoCatWidget(WIDGET, BASE):

    def __init__(self, parent=None):
        super(GeoCatWidget, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)

        self.btnGeoCat.clicked.connect(partial(self.open_link, meta.getHomeUrl()))
        self.btnGeoCat.setIcon(gui.getSvgIconByName('geocat_logo'))

        self.btnDocs.clicked.connect(partial(self.open_link, meta.getDocsUrl()))
        self.btnDocs.setIcon(gui.getSvgIconByName('manual'))

        self.btnGitHub.clicked.connect(partial(self.open_link, meta.getRepoUrl()))
        self.btnGitHub.setIcon(gui.getSvgIconByName('github_logo'))

        self.btnGitter.clicked.connect(partial(self.open_link, meta.getChatUrl()))
        self.btnGitter.setIcon(gui.getSvgIconByName('gitter_logo'))

        # Add version info
        info_txt = meta.getLongAppNameWithMinVersion()
        if info_txt:
            aux_info = getattr(self.parent, 'info', None)
            if aux_info:
                info_txt += f'  \u2192  {aux_info}'
            author = meta.getAuthor()
            if author:
                info_txt += f'<br/>Copyright \u00A92019-{datetime.now().year} {author} and contributors'
            self.txtInfo.setText(f'<p style="line-height: 1.5">{info_txt}</p>')

        self.btnClose.clicked.connect(parent.close)

    @staticmethod
    def open_link(url: str) -> bool:
        return webbrowser.open_new_tab(url)
