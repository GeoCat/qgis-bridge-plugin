import json
from abc import ABC, abstractmethod
from importlib import import_module
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

import requests
from qgis.PyQt.QtGui import QPixmap
from qgis.core import (
    QgsAuthMethodConfig,
    QgsApplication,
    QgsProcessingAlgorithm
)

from geocatbridge.utils import files
from geocatbridge.utils.feedback import FeedbackMixin


class AbstractServer(ABC):

    @abstractmethod
    def getSettings(self) -> dict:
        """ This abstract method must be implemented on all server instances.
        It should return a dictionary with parameters required to initialize the server class (keyword args).

        :returns:   A keyword arguments dictionary.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement getSettings()")

    @classmethod
    @abstractmethod
    def getWidgetClass(cls) -> type:
        """ This abstract class method must be implemented on all server subclasses.
        It should return the widget (Qt UI) controller class for this server type.

        :returns:   A server class type.
        """
        raise NotImplementedError(f"{cls.__name__} must implement getWidgetClass()")

    @classmethod
    @abstractmethod
    def getServerTypeLabel(cls) -> str:
        """ This abstract class method must be implemented on all server subclasses.
        It should return the server type label (e.g. "GeoServer" for the GeoServerServer class).

        :returns:   A string with the server type label.
        """
        raise NotImplementedError(f"{cls.__name__} must implement getServerTypeLabel()")


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
            QgsApplication.authManager().loadAuthenticationConfig(self.authId, auth_config, True)  # noqa
            self._username = auth_config.config('username')
            self._password = auth_config.config('password')
        return self._username, self._password

    @property
    def serverName(self):
        return self._name

    @property
    def authId(self):
        return self._authid

    @abstractmethod
    def testConnection(self) -> bool:
        """ This abstract method must be implemented on all server instances.
        It tests if the connection to the server can be established.

        :returns:   True if the connection is established, False otherwise.
        """
        pass

    @classmethod
    def getAlgorithmInstance(cls) -> Union[QgsProcessingAlgorithm, None]:
        """ This abstract class method can be implemented on all server classes, if needed.
        If the server class can also be used by a QGIS processing provider, this method should
        return a new processing algorithm instance that exposes its functionality.

        :returns:   A new algorithm instance that inherits from QgsProcessingAlgorithm.
                    If the server class does not support this, return None.
        """
        return


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
        self.logInfo(f"{method.upper()} {url}")
        r = req_method(url, headers=headers, files=files_, data=data, auth=auth)
        r.raise_for_status()
        return r

    @property
    def baseUrl(self):
        """ Returns the base part of the server URL. """
        return self._baseurl

    def addOGCServices(self):
        pass

    def validateBeforePublication(self, *args, **kwargs):
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

    def prepareForPublishing(self, only_symbology: bool):
        """ This method is called right before any publication takes place.

        :param only_symbology:  If True, a destination folder/workspace does not need to be cleared.
        """
        pass

    def clearTarget(self, recreate: bool = True) -> bool:
        """ This method is called by the publish widget (among others) to clear a destination
        workspace or folder. All data, layers and styling within the target workspace/folder is removed.

        :param recreate:    If True, the target workspace/folder should be recreated (i.e. empty, but existing).
        :returns:           Returns True if clearing was successful.
        """
        pass

    @abstractmethod
    def publishLayer(self, layer, fields=None):
        """ Publishes the given QGIS layer (and specified fields) to the server. """
        raise NotImplementedError

    @abstractmethod
    def publishStyle(self, layer):
        """ Publishes a style (symbology) for the given QGIS layer to the server. """
        raise NotImplementedError

    def getPreviewUrl(self, layer_names: list, bbox: str, crs_authid: str) -> str:
        """ This method may be implemented for servers that support previewing published layers.
        It should return a URL to get a preview map for the given layers.

        :param layer_names: A list of layer names for which to get a preview map.
        :param bbox:        A concatenated BBOX string (XMIN, YMIN, XMAX, YMAX) for the preview map extent.
        :param crs_authid:  The coordinate system ID (e.g. EPSG code) for the preview map.
        """
        pass

    def layerExists(self, name: str) -> bool:
        """ This method must be implemented if the server offers a way to check if a layer was published. """
        raise NotImplementedError

    def styleExists(self, name: str) -> bool:
        """ This method must be implemented if the server offers a way to check if a style was published. """
        raise NotImplementedError

    def deleteStyle(self, name) -> bool:
        """ This method must be implemented if the server offers a way to delete a style.
        Should return True if deletion was successful.

        :param name:    The name of the style as it is stored on the server.
        """
        raise NotImplementedError

    def deleteLayer(self, name) -> bool:
        """ This method must be implemented if the server offers a way to delete a layer.
        Should return True if deletion was successful.

        :param name:    The name of the layer as it is stored on the server.
        """
        raise NotImplementedError

    def fullLayerName(self, layer_name) -> str:
        """ This method should return the full layer name on the server (e.g. including a workspace path). """
        return layer_name

    def getWmsUrl(self) -> str:
        """ This method should return the Web Map Service (WMS) URL for the server. """
        raise NotImplementedError

    def getWfsUrl(self) -> str:
        """ This method should return the Web Feature Service (WFS) URL for the server. """
        raise NotImplementedError

    def setLayerMetadataLink(self, name, url):
        """ This method must be implemented if the server supports setting a metadata link URL on a layer. """
        raise NotImplementedError

    def createGroups(self, groups, layers):
        """ This method may be implemented to create layer groups on the server.

        :param groups:  One or more groups to assign the given layers to.
        :param layers:  QGIS layer names to put in the given group(s).
        """
        pass


class DbServerBase(ServerBase, ABC):

    def __init__(self, name, authid=""):
        super().__init__(name, authid)


class ServerWidgetBase:
    """ Each server widget view controller class needs to implement this base class. """

    def __init__(self, parent, server_type):
        super().__init__(parent)
        self._id = None
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

    def getId(self):
        """ This method returns the original name of the server (regardless of unsaved user changes).

        :returns:   A server name string.
        """
        return self._id

    def setId(self, name: str):
        """ This method sets the original name of the server (before any user changes).
        It is typically called by the server connections widget, directly after a server widget was populated.
        """
        self._id = name

    def createServerInstance(self):
        """ This method must be implemented on all server widget controllers.
        It should collect all data from the server configuration widget form fields and
        return a new server instance using that data as input parameters.

        :returns:   A server instance of type `self.serverType`.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement createServerInstance()")

    def newFromName(self, name: str):
        """ This method must be implemented on all server widget controllers.
        It should set the server name form field to the given name and keep
        all other fields blank or in an initial state.

        .. note::   Once the name has been set and initial fields have been populated,
                    `setDirty()` is called by the server connections dialog.

        :param name:    The new server name.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement newFromName()")

    def loadFromInstance(self, server):
        """ This method must be implemented on all server widget controllers.
        It should call `getSettings()` on the given server instance and
        use the values to populate the server configuration widget form fields.

        .. note::   Once the form has populated, typically `setClean()` should be called.

        :param server:  A server instance.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement loadFromInstance()")

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
