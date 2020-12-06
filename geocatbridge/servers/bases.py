from urllib.parse import urlparse
from abc import ABC, abstractmethod
from pathlib import Path
from importlib import import_module

import requests
import json

from qgis.PyQt.QtGui import QPixmap
from qgis.core import (
    QgsAuthMethodConfig,
    QgsApplication
)

from geocatbridge.utils.feedback import FeedbackMixin
from geocatbridge.utils import files


class AbstractServer(ABC):
    _DATACAT = False
    _METACAT = False

    @abstractmethod
    def getSettings(self) -> dict:
        """ This abstract method must be implemented on all server instances.
        It should return a dictionary with parameters required to initialize the server class (keyword args).

        :returns:   A keyword arguments dictionary.
        """
        pass

    @classmethod
    @abstractmethod
    def getWidgetClass(cls) -> type:
        """ This abstract class method must be implemented on all server subclasses.
        It should return the widget (Qt UI) controller class for this server type.

        :returns:   A server class type.
        """
        raise NotImplementedError("cannot call abstract class method")

    @classmethod
    @abstractmethod
    def getServerTypeLabel(cls) -> str:
        """ This abstract class method must be implemented on all server subclasses.
        It should return the server type label (e.g. "GeoServer" for the GeoServerServer class).

        :returns:   A string with the server type label.
        """
        raise NotImplementedError("cannot call abstract class method")


class ServerBase(AbstractServer, FeedbackMixin, ABC):

    def __init__(self, name, authid=""):
        super().__init__()
        self._name = name
        self._authid = authid
        self._username = None
        self._password = None
        self.getCredentials()

    def setBasicAuthCredentials(self, username, password):
        self._username = username
        self._password = password

    def getCredentials(self):
        if self._username is None or self._password is None:
            auth_config = QgsAuthMethodConfig()
            QgsApplication.authManager().loadAuthenticationConfig(self.authId, auth_config, True)
            self._username = auth_config.config('username')
            self._password = auth_config.config('password')
        return self._username, self._password

    @property
    def serverName(self):
        return self._name

    @property
    def authId(self):
        return self._authid

    @property
    def isDataCatalog(self):
        return self._DATACAT

    @property
    def isMetaCatalog(self):
        return self._METACAT

    @abstractmethod
    def testConnection(self) -> bool:
        """ This abstract method must be implemented on all server instances.
        It tests if the connection to the server can be established.

        :returns:   True if the connection is established, False otherwise.
        """
        pass


class CatalogServerBase(ServerBase, ABC):

    def __init__(self, name, authid="", url=""):
        super().__init__(name, authid)
        self._baseurl = urlparse(url).geturl()

    def request(self, url, method="get", data=None, **kwargs):
        headers = kwargs.get("headers") or {}
        files_ = kwargs.get("files") or {}
        session = kwargs.get("session")
        # TODO: Use qgis.core.QgsBlockingNetworkRequest in later QGIS versions.
        #       This should improve proxy and authentication handling.
        #       Currently, only 3.18+ supports the PUT request (3.16 LTR does not).
        if session and isinstance(session, requests.Session):
            auth = None
            if hasattr(session, 'setTokenHeader'):
                session.setTokenHeader(*self.getCredentials())
            req_method = getattr(session, method.casefold())
        else:
            auth = self.getCredentials()
            req_method = getattr(requests, method.casefold())
        if isinstance(data, dict):
            data = json.dumps(data)
            headers["Content-Type"] = "application/json"
        self.logInfo("Making %s request to '%s'" % (method, url))
        r = req_method(url, headers=headers, files=files_, data=data, auth=auth)
        r.raise_for_status()
        return r

    @property
    def baseUrl(self):
        return self._baseurl

    def addOGCServices(self):
        pass

    def validateBeforePublication(self, errors, *args, **kwargs):
        pass


class MetaCatalogServerBase(CatalogServerBase, ABC):
    _METACAT = True

    def __init__(self, name, authid="", url=""):
        super().__init__(name, authid, url)

    def openMetadata(self, uuid):
        pass


class DataCatalogServerBase(CatalogServerBase, ABC):
    _DATACAT = True

    def __init__(self, name, authid="", url=""):
        super().__init__(name, authid, url)

    def openPreview(self, names, bbox, srs):
        pass


class DbServerBase(ServerBase, ABC):

    def __init__(self, name, authid=""):
        super().__init__(name, authid)


class ServerWidgetBase:
    """ Each server widget view controller class needs to implement this base class. """

    def __init__(self, parent, server_type):
        super().__init__(parent)
        self._parent = parent
        self._server_type = server_type
        self._dirty = False

    @property
    def parent(self):
        """ Returns the parent object (usually a ServerConnectionsWidget instance). """
        return self._parent

    @property
    def serverType(self):
        """ Returns the class (model) for the current server type. """
        return self._server_type

    @property
    def isDirty(self):
        """ Returns True if the form field values have changed. """
        return self._dirty

    def setDirty(self):
        """ Sets the form to a 'dirty' state if the field values have changed. """
        self._dirty = True

    def setClean(self):
        """ Sets the form to a 'clean' state if the field values did not change. """
        self._dirty = False

    def createServerInstance(self):
        """ This method must be implemented on all server widget controllers.
        It should collect all data from the server configuration widget form fields and
        return a new server instance using that data as input parameters.

        :returns:           A server instance of type `self.serverType`.
        """
        raise NotImplementedError

    def newFromName(self, name: str):
        """ This method must be implemented on all server widget controllers.
        It should set the server name form field to the given name and keep
        all other fields blank or in an initial state.

        .. note::   Once the name has been set, typically `setDirty()` should be called.

        :param name:    The new server name.
        """
        raise NotImplementedError

    def loadFromInstance(self, server):
        """ This method must be implemented on all server widget controllers.
        It should call `getSettings()` on the given server instance and
        use the values to populate the server configuration widget form fields.

        .. note::   Once the form has populated, typically `setClean()` should be called.

        :param server:  A server instance.
        """
        raise NotImplementedError

    @classmethod
    def getPngIcon(cls) -> QPixmap:
        """ Returns the Qt icon for the server list widget.
        Icons should be PNG files with the same path and name as the server widget controller.
        If a matching icon is not found, a default icon is returned.

        :return:    A QPixmap object.
        """
        module_name = getattr(cls, '__module__', None)
        if module_name:
            # Retrieve the icon path from the module path
            module = import_module(module_name)
            icon = Path(module.__file__).with_suffix('.png')
            if icon.exists():
                return QPixmap(str(icon))
        # Return the default unknown.png if no matching icon was found
        return QPixmap(files.getIconPath('unknown'))
