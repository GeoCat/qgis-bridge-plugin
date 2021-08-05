from copy import deepcopy
from functools import partial
from typing import Union

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QKeyEvent, QIcon
from qgis.PyQt.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QListWidgetItem,
    QWidget,
    QFileDialog
)

from geocatbridge.servers import manager
from geocatbridge.servers.bases import ServerWidgetBase
from geocatbridge.utils import gui, files
from geocatbridge.utils.feedback import FeedbackMixin

WIDGET, BASE = gui.loadUiType(__file__)


class ServerConnectionsWidget(FeedbackMixin, BASE, WIDGET):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server_widgets = {}
        self.setupUi(self)

        self.addMenuToButtonNew()
        self.buttonRemove.clicked.connect(self.removeButtonClicked)
        self.populateServerList()
        self.showServerWidget()
        self.buttonSave.clicked.connect(self.saveServer)
        self.buttonImport.clicked.connect(self.importServers)
        self.buttonExport.clicked.connect(self.exportServers)
        self.buttonDuplicate.clicked.connect(self.duplicateServer)
        self.buttonClose.clicked.connect(parent.close)
        self.buttonTest.clicked.connect(self.testConnection)
        self.buttonTest.setVisible(False)
        self.buttonTest.setIcon(QIcon(files.getIconPath("connect")))

        # Connect event handlers for server widget activation
        self.listServers.itemClicked.connect(partial(self.listItemClicked))
        self.listServers.keyPressEvent = partial(self.listKeyPressed)
        self.stackedWidget.currentChanged.connect(partial(self.toggleTestButton))

    @property
    def serverManager(self):
        """ Convenience property to get a reference to the server manager module.
        This is mainly used by server widgets that have the server connection dialog as a parent.

        ..note::    Server widget views should **not** import the manager module,
                    as this could lead to cyclical import errors.
        """
        return manager

    def toggleServerList(self):
        has_servers = self.listServers.count() > 0
        self.txtNoServers.setVisible(not has_servers)
        self.listServers.setVisible(has_servers)
        self.buttonExport.setEnabled(has_servers)
        self.buttonDuplicate.setEnabled(has_servers)
        self.buttonRemove.setEnabled(has_servers)
        self.buttonTest.setEnabled(has_servers)
        if not has_servers:
            # If there are no servers (anymore), show empty widget
            self.stackedWidget.setCurrentWidget(self.widgetEmpty)

    def toggleTestButton(self, widget_index: int):
        """ Shows/hides the connection test button if a server widget is visible. """
        self.buttonTest.setVisible(self.stackedWidget.widget(widget_index) not in (None, self.widgetEmpty))

    def exportServers(self):
        filename = QFileDialog.getSaveFileName(self, self.translate("Export servers"),
                                               filter=f'{self.translate("Server configuration")} (*.json)',
                                               options=QFileDialog.DontUseNativeDialog)[0]
        if not filename:
            self.logWarning("No export filename specified")
            return

        config_str = manager.serializeServers()
        if not config_str:
            self.showErrorBar("Error", "Failed to export server configuration. Please check QGIS log.")
            return

        if not filename.endswith("json"):
            filename += ".json"
        try:
            with open(filename, "w+") as f:
                f.write(config_str)
            self.showSuccessBar("Success", "Successfully exported server configuration to JSON file")
        except Exception as err:
            self.logError(err)
            self.showErrorBar("Error", "Failed to write server configuration JSON file. Please check QGIS log.")

    def importServers(self):
        filename = QFileDialog.getOpenFileName(self, self.translate("Import servers"),
                                               filter=f'{self.translate("Server configuration")} (*.json)',
                                               options=QFileDialog.DontUseNativeDialog)[0]
        if not filename:
            self.logWarning("No export filename specified")
            return

        try:
            with open(filename) as f:
                config_str = f.read()
        except Exception as err:
            self.logError(err)
            self.showErrorBar("Error", "Unable to read server configuration JSON file. Please check QGIS log.")

        if not manager.deserializeServers(config_str):
            self.showErrorBar("Error", "Failed to import server configuration from JSON file. "
                                       "Please check QGIS log.")
            return

        self.populateServerList()
        self.showSuccessBar("Success", "Successfully imported server configuration from JSON file")

    def serverIsDirty(self) -> bool:
        widget = self.stackedWidget.currentWidget()
        if widget and hasattr(widget, 'isDirty'):
            return widget.isDirty
        return False

    def serverSetClean(self):
        widget = self.stackedWidget.currentWidget()
        if widget and hasattr(widget, 'setClean'):
            widget.setClean()

    def serverExists(self, item=None) -> bool:
        """ Returns True if the server has been saved before (i.e. is not new). """
        return manager.getServer(self.getListWidgetItemName(item)) is not None

    def askToSave(self, question: str, **kwargs):
        msgbox_kwargs = {
            'buttons': self.BUTTONS.CANCEL | self.BUTTONS.NO | self.BUTTONS.YES,
            'defaultButton': self.BUTTONS.YES
        }
        msgbox_kwargs.update(kwargs)
        return self.showQuestionBox("Servers", question, **msgbox_kwargs)

    def listSelectNoSignals(self, item):
        self.listServers.blockSignals(True)
        self.listServers.setCurrentItem(item)
        self.listServers.blockSignals(False)

    def getListItemFromServerWidget(self, server_widget):
        """ Finds the list item that matches the given server widget. """
        if not hasattr(server_widget, 'getId'):
            # The current widget likely is the empty widget
            return
        for i in range(self.listServers.count()):
            item = self.listServers.item(i)
            widget = self.listServers.itemWidget(item)
            if widget.serverName == server_widget.getId():
                return item
        return

    def listKeyPressed(self, event: QKeyEvent):
        """ Activates the server widget matching a key press event if the QListWidget has focus.
        The QListWidget items can be selected using the Up and Down arrow keys only.
        These key events emit an `itemClicked` event in turn, which are being handled by the `listItemClicked` method.
        """
        list_index = -1
        row_index = self.listServers.currentRow()
        if event.key() == Qt.Key_Up and row_index > 0:
            # User pressed the Up key and there is a list item above the current one
            list_index = row_index - 1
        elif event.key() == Qt.Key_Down and row_index < self.listServers.count() - 1:
            # User pressed the Down key and there is a list item below the current one
            list_index = row_index + 1

        if list_index >= 0:
            # Select the list item that the user requested
            list_item = self.listServers.item(list_index)
            self.listSelectNoSignals(list_item)
            self.listServers.itemClicked.emit(list_item)

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
        new_server = self.getServerFromItem(list_item)
        cur_widget = self.stackedWidget.currentWidget()
        old_item = self.getListItemFromServerWidget(cur_widget)

        if not old_item:
            # No item was selected before: set widget for new server (or empty widget) directly
            return self.showServerWidget(new_server)
        if not new_server and list_item == old_item:
            # User clicked the same list item again, but it was not saved yet: do nothing
            return
        if new_server.serverName == cur_widget.getId():
            # User clicked the same list item again: do nothing
            return

        if cur_widget.isDirty:
            # Current server has edits: ask user if we should save them
            item = self.getListItemFromServerWidget(cur_widget)
            answer = self.askToSave("Do you want to save your changes to the current server?")
            if (answer == self.BUTTONS.YES and not self.persistServer(item)) or answer == self.BUTTONS.CANCEL:
                # User wants to save but saving failed OR user canceled: reset to old server
                # return self.listSelectNoSignals(item)
                return self.listServers.setCurrentItem(item)
            elif answer == self.BUTTONS.NO:
                # Clean up newly created dirty servers that were never saved before
                self.cleanupServerItem(item)

        # Match server widget to selected server list item
        self.showServerWidget(new_server)

    def testConnection(self):
        """ Tests if the server instance can actually connect to it.

        .. note::   Not all servers might support this. Servers that don't support it,
                    should still implement :func:`testConnection`, but in that case,
                    the method should simply always return `True`.
        """
        server_widget = self.stackedWidget.currentWidget()
        if not server_widget or not hasattr(server_widget, 'createServerInstance'):
            # No current server widget set or empty widget
            return

        server = server_widget.createServerInstance()
        if server is None:
            # Server is usually None when createServerInstance() call failed.
            self.showErrorBar("Error", "Wrong value(s) in current server settings. Please check QGIS log.")
        else:
            errors = set()
            # Run the actual connection test method on the server instance.
            if gui.execute(server.testConnection, errors):
                self.showSuccessBar("Success", "Successfully established server connection")
                return
            for e in errors:
                self.showErrorBar("Error", e)

    def persistServer(self, list_item=None) -> bool:
        """ Tells the server manager to store the server in the QGIS settings. """

        server_widget = self.stackedWidget.currentWidget()
        if not server_widget:
            # No current server widget set (should not happen)
            return False

        # See if the server can be instantiated from field values
        try:
            server = server_widget.createServerInstance()
        except NotImplementedError:
            self.showErrorBar("Error", f"Current server does not implement {ServerWidgetBase.__name__}")
            return False
        if not server:
            self.showErrorBar("Error", "Bad or missing values in current server settings. Please check QGIS log.")
            return False

        try:
            result = manager.saveServer(server, server_widget.getId())
        except ValueError as err:
            # Show error bar if user set a bad name
            self.showErrorBar("Error", f"Invalid name: {err}")
            return False

        # Update list view item if selected and server was successfully saved
        list_widget = self.getListWidgetItem(list_item)
        if result and list_widget:
            list_widget.serverName = server.serverName
        return result

    def getListWidgetItem(self, item=None):
        item = item or self.listServers.currentItem()
        if item is None:
            return
        return self.listServers.itemWidget(item)

    def getListWidgetItemName(self, item=None):
        widget = self.getListWidgetItem(item)
        return widget.serverName if widget else None

    def getServerFromItem(self, item):
        if not item:
            return
        list_widget = self.listServers.itemWidget(item)
        return manager.getServer(list_widget.serverName)

    def duplicateServer(self):
        """ Duplicates (copies) the current selected server. """
        if self.serverIsDirty():
            # Ask to save but do not provide a No button: can't duplicate an unsaved server
            res = self.askToSave("Do you want to save your changes to the current server?",
                                 buttons=self.BUTTONS.CANCEL | self.BUTTONS.YES)
            if (res == self.BUTTONS.YES and not self.persistServer()) or res == self.BUTTONS.CANCEL:
                # User wants to save but saving failed OR user canceled: do not add new server
                return

        source_name = self.getListWidgetItemName()
        source_instance = manager.getServer(source_name)
        if not (source_name and source_instance):
            return

        # Copy settings from selected server and make new unique name
        settings = source_instance.getSettings()
        server_type = type(source_instance)
        target_name = manager.getUniqueName(f"Copy of {source_name}")
        settings['name'] = target_name

        # Instantiate new server (but do not store it yet)
        try:
            target_instance = server_type(**settings)
        except Exception as err:
            self.logError(err)
            self.showErrorBar("Error", f"Failed to duplicate server {source_name}. Please check QGIS log.")
            return

        # Populate server widget with duplicated instance values and set dirty
        target_name = self.showServerWidget(target_instance, force_dirty=True)
        if target_name:
            self.addServerListItem(server_type, target_name, True)
            self.toggleServerList()
        else:
            manager.removeServer(target_name, True)
            self.showErrorBar("Error", f"Failed to duplicate server {source_name}. Please check QGIS log.")

    def addMenuToButtonNew(self):
        """ Populate "New Server" menu button with available server types (in alphabetical order). """
        menu = QMenu()
        for label, server_type in sorted((s.getLabel(), deepcopy(s)) for s in manager.getServerTypes()):
            menu.addAction(label, partial(self.addNewServer, server_type))
        self.buttonNew.setMenu(menu)

    def selectItemAbove(self, index: int):
        """ Selects the item above the one with the given index and activates the server widget for it. """
        if self.listServers.count():
            # Set the selected list item to the one above the deleted item (if there are any items left).
            new_item = self.listServers.item(max(0, index - 1))
            self.listServers.setCurrentItem(new_item)
            server = self.getServerFromItem(new_item)
            if not self.showServerWidget(server):
                return None
            return new_item
        # If there are no items left, toggle some buttons and set to empty widget
        self.toggleServerList()
        return None

    def removeButtonClicked(self):
        """ Completely removes the current server when the user clicks the Remove button. """
        index = self.removeServer(purge=True)
        return self.selectItemAbove(index)

    def cleanupServerItem(self, item=None):
        """ Cleans up the current server (or given item) if it was never saved before. """
        if self.serverExists(item):
            # Keep the server list item if the server instance was saved before
            return
        index = self.removeServer(item)
        return self.selectItemAbove(index)

    def removeServer(self, item=None, purge: bool = False) -> int:
        """ Removes the server under the given list item or the current selected server from the list.

        :param item:    If a list widget item is specified, the server instance and widget for that
                        specific item will be removed. If unspecified, the current selected one will
                        be removed (default).
        :param purge:   If True (default is False), the server instance will also be removed (not just the list item).
        :returns:       The index of the removed item.
        """
        name = self.getListWidgetItemName(item)
        index = self.listServers.row(item) if item else self.listServers.currentRow()
        if purge:
            # Remove server instance as well (not just list item)
            manager.removeServer(name, True)
        # Remove list item
        self.listServers.blockSignals(True)
        self.listServers.takeItem(index)
        self.listServers.blockSignals(False)
        return index

    def populateServerList(self):
        """ Populates the list widget with all available server instances (in alphabetical order). """
        self.listServers.clear()
        for name, server_type in sorted((s.serverName, s.__class__) for s in manager.getServers()):
            self.addServerListItem(server_type, name)
        self.toggleServerList()

    def addServerListItem(self, server_class, server_name: str, set_active: bool = False):
        """ Adds a server item to the list widget. """
        widget = ServerItemWidget(server_class, server_name)
        item = QListWidgetItem(self.listServers)
        item.setSizeHint(widget.sizeHint())
        self.listServers.blockSignals(True)
        self.listServers.addItem(item)
        self.listServers.setItemWidget(item, widget)
        if set_active:
            self.listServers.setCurrentItem(item)
        self.listServers.blockSignals(False)

    def addNewServer(self, cls):
        """ Adds a new server of type `cls`. Adds a list widget item and activates a server widget for it. """
        if self.serverIsDirty():
            # Current server has edits: ask user if we should save them
            answer = self.askToSave("Do you want to save your changes to the current server?")
            if (answer == self.BUTTONS.YES and not self.persistServer()) or answer == self.BUTTONS.CANCEL:
                # User wants to save but saving failed OR user canceled: do not add new server
                return
            elif answer == self.BUTTONS.NO:
                # Cleanup server that was never saved before
                self.cleanupServerItem()

        assigned_name = self.showServerWidget(cls)
        if assigned_name:
            self.addServerListItem(cls, assigned_name, True)
            self.toggleServerList()
        else:
            self.showErrorBar("Error", f"Failed to add {cls.getLabel()} server. Please check QGIS log.")

    def showServerWidget(self, server=None, force_dirty: bool = False) -> Union[str, None]:
        """ Sets the current server configuration widget for the given server instance or class.

        :param server:      An existing server instance or a server class.
                            If this argument is omitted, an empty widget will be shown.
                            If `server` is a class, a new server of that class will be added with a generated name.
                            If `server` is an instance, the matching server widget will be populated with the data.
        :param force_dirty: This only applies when `server` is an instance. When True (default is False),
                            the server widget will be set to a dirty state after the fields were populated.
        :returns:           The currently shown server name or None (if unsuccessful).
        """

        if server is None:
            # If there's no current server, show empty widget
            self.stackedWidget.setCurrentWidget(self.widgetEmpty)
            return

        if isinstance(server, (manager.bases.ServerBase, manager.bases.CombiServerBase)):
            # 'server' argument is a model instance (existing servers)
            server_cls = type(server)
        else:
            # 'server' argument is a model class (new servers)
            server_cls = server

        # Retrieve widget class from server
        cls = server.getWidgetClass()
        if not issubclass(cls, ServerWidgetBase):
            # All server widgets must implement the ServerWidgetBase class
            self.logError(f"Server widget {cls.__name__} does not implement {ServerWidgetBase.__name__}")
            return

        # Lookup existing widget instance (there should only be 1 widget instance for each server type)
        widget = self._server_widgets.get(cls.__name__, None)

        # If the widget does not exist yet, instantiate and add it to the stackedWidget
        if not widget:
            widget = cls(self, server_cls)
            self._server_widgets[cls.__name__] = widget
            self.stackedWidget.addWidget(widget)

        # Set as current widget and populate its form fields
        self.stackedWidget.setCurrentWidget(widget)
        if server_cls == server:
            srv_name = manager.getUniqueName(server_cls.getLabel())
            widget.newFromName(srv_name)
            widget.setId(srv_name)
            widget.setDirty()
        else:
            srv_name = server.serverName
            widget.loadFromInstance(server)
            widget.setId(srv_name)
            if force_dirty:
                widget.setDirty()

        return srv_name

    def saveServer(self, silent: bool = False) -> bool:
        """ Makes sure that the current server is stored in the QGIS Bridge settings.
        Sets the server state to "clean" if it was successfully stored.
        Updates the server name in the list view (if changed).

        :param silent:  If True (default = False), a message bar will be shown upon success.
                        Otherwise, there will only be a log message.
        :returns:       True if the server was successfully saved, False otherwise.
        """
        if not self.persistServer():
            return False
        self.serverSetClean()
        if not silent:
            self.showSuccessBar("Success", "Successfully saved server settings")
        else:
            self.logInfo("Successfully saved server settings")
        return True

    def canClose(self) -> bool:
        """ Checks if the server connection widget can be closed (i.e. no unsaved edits). """
        if self.serverIsDirty():
            res = self.askToSave("Do you want to save your changes to the current server?")
            if res == self.BUTTONS.YES:
                return self.saveServer(True)
            if res == self.BUTTONS.NO:
                # Remove server from list view if it has never been saved before (clean up)
                self.cleanupServerItem()
            return res != self.BUTTONS.CANCEL
        return True

    def destroy(self):
        self._server_widgets = None
        for i in range(len(self.listServers) - 1, -1, -1):
            item_widget = self.listServers.item(i)
            self.removeServer(item_widget)


class ServerItemWidget(QWidget):
    def __init__(self, server_class, server_name, parent=None):
        """ Widget used by the list widget control to show all available server instances. """
        super(ServerItemWidget, self).__init__(parent)
        icon = server_class.getWidgetClass().getPngIcon()
        self.layout = QHBoxLayout()
        self.label = QLabel()
        self.serverName = server_name
        self.iconLabel = QLabel()
        self.iconLabel.setPixmap(icon)
        self.iconLabel.setFixedWidth(50)
        self.layout.addWidget(self.iconLabel)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

    @property
    def serverName(self):
        return self.label.text()

    @serverName.setter
    def serverName(self, name):
        self.label.setText(name)
