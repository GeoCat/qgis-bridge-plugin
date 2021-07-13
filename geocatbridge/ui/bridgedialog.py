from functools import partial

from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtGui import QIcon, QKeyEvent
from qgis.PyQt.QtWidgets import QListWidgetItem

from geocatbridge.ui.geocatwidget import GeoCatWidget
from geocatbridge.ui.publishwidget import PublishWidget
from geocatbridge.ui.serverconnectionswidget import ServerConnectionsWidget
from geocatbridge.utils import files, gui, meta
from geocatbridge.utils.enum_ import LabeledIntEnum

VERSION_SETTING = f"{meta.PLUGIN_NAMESPACE}/currentVersion"

WIDGET, BASE = gui.loadUiType(__file__)


class Panels(LabeledIntEnum):
    PUBLISH = PublishWidget
    SERVERS = ServerConnectionsWidget
    ABOUT = GeoCatWidget


class BridgeDialog(BASE, WIDGET):

    def __init__(self, parent=None, info=None):
        super().__init__(parent)
        self.info = info
        self.setupUi(self)

        self.setWindowTitle(meta.getLongAppName())
        self.setWindowIcon(QIcon(files.getIconPath('geocat')))

        self.panel_widgets, self.keymap = self.addPanels()
        self.panel_widgets[Panels.PUBLISH].restoreConfig()  # noqa

        # Connect event handlers for panel activation
        self.listWidget.itemClicked.connect(partial(self.listItemClicked))
        self.listWidget.keyPressEvent = partial(self.listKeyPressed)

        if self.showAbout():
            # Show About panel first on fresh install or update
            self.listWidget.setCurrentRow(Panels.ABOUT)
        else:
            self.listWidget.setCurrentRow(Panels.PUBLISH)

    def addPanels(self):
        """ Populate stackWidget and listWidget and return a list of available panel widgets and a keymap. """
        keymap = {}
        panels = []
        for i, panel in enumerate(Panels):
            widget = panel.value(self)
            panels.append(widget)
            self.stackedWidget.addWidget(widget)
            name = panel.name.lower().title()
            list_item = QListWidgetItem(QIcon(files.getIconPath(name.lower())), name)
            self.listWidget.insertItem(panel, list_item)
            keymap[name.lower()[0]] = i
        return panels, keymap

    @staticmethod
    def showAbout() -> bool:
        """ Checks if the currentVersion QSetting exists and the Bridge version matches the current one.
        If the versions do NOT match, it means that the About screen should be shown.
        """
        cur_version = meta.getVersion()
        old_version = QSettings().value(VERSION_SETTING)
        if old_version != cur_version:
            QSettings().setValue(VERSION_SETTING, cur_version)
            return True
        return False

    def listSelectNoSignals(self, index: int):
        self.listWidget.blockSignals(True)
        self.listWidget.setCurrentRow(index)
        self.listWidget.blockSignals(False)

    def listKeyPressed(self, event: QKeyEvent):
        """ Activates the panel matching a key press event if the QListWidget has focus.
        The QListWidget items can be selected using the Up and Down arrow keys or by pressing the
        first letter of the item title (e.g. "a" for the "About" item).
        These key events emit an `itemClicked` event in turn, which are being handled by the `listItemClicked` method.
        """
        key = (event.text() or '').lower() or event.key()
        list_index = self.keymap.get(key, -1)
        if list_index < 0:
            # User did not press the first letter of a panel name: check if arrow keys were pressed
            row_index = self.listWidget.currentRow()
            if key == Qt.Key_Up and row_index > 0:
                # User pressed the Up key and there is a list item above the current one
                list_index = row_index - 1
            elif key == Qt.Key_Down and row_index < len(self.panel_widgets) - 1:
                # User pressed the Down key and there is a list item below the current one
                list_index = row_index + 1

        if list_index >= 0:
            # Select the list item that the user requested
            self.listSelectNoSignals(list_index)
            list_item = self.listWidget.item(list_index)
            self.listWidget.itemClicked.emit(list_item)

        # Default action
        event.accept()

    def listItemClicked(self, list_item: QListWidgetItem):
        """ Activates the panel that matches the clicked QListWidgetItem.

        .. note::   The `QListWidget.itemPressed` event handler is the **second-last** triggered event handler
                    whenever the user clicks a QListWidgetItem. Because we reselect the Servers QListWidgetItem
                    if the Servers panel still has edits (which the user wants to save), we cannot handle more
                    logical events like `QListWidget.currentRowChanged` for example, since we cannot stop event
                    propagation (as with a QEvent).
        """
        enum_name = list_item.text().upper()
        panel_widget = self.panel_widgets[getattr(Panels, enum_name)]
        current_panel = self.stackedWidget.currentWidget()

        if panel_widget == current_panel:
            # User clicked the same list item again: do nothing
            return
        if isinstance(current_panel, Panels.SERVERS.value) and not current_panel.canClose():
            # User wants to edit/save Server settings: reselect Servers list item
            self.listSelectNoSignals(Panels.SERVERS)  # noqa
            return

        # Match panel to selected list item and populate/update if needed
        self.stackedWidget.setCurrentWidget(panel_widget)
        if isinstance(panel_widget, Panels.PUBLISH.value):
            panel_widget.updateServers()
        elif isinstance(panel_widget, Panels.SERVERS.value):
            panel_widget.populateServerList()

    def closeEvent(self, evt):
        """ Triggered whenever the user closes the dialog. """
        self.panel_widgets[Panels.PUBLISH].storeMetadata()  # noqa
        self.panel_widgets[Panels.PUBLISH].saveConfig()  # noqa
        current_panel = self.stackedWidget.currentWidget()
        if isinstance(current_panel, Panels.SERVERS.value) and not current_panel.canClose():
            # Abort dialog close if the user decided that a server still needs editing
            evt.ignore()
        else:
            evt.accept()

    def destroy(self):
        """ Releases all resources used by the BridgeDialog. """
        for i in range(len(self.panel_widgets)):
            panel = self.panel_widgets.pop()
            if i in (Panels.PUBLISH, Panels.SERVERS):
                panel.destroy()
            del panel
        self.listWidget.destroy()
        self.stackedWidget.destroy()
        super().destroy()
