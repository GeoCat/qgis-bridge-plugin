import json
from abc import ABC, abstractmethod
from importlib import import_module
from pathlib import Path
from typing import Union, Iterable, Dict
from urllib.parse import urlparse

import requests
from requests.auth import HTTPBasicAuth
from qgis.PyQt.QtGui import QPixmap, QIcon
from qgis.core import (
    QgsAuthMethodConfig,
    QgsApplication,
    QgsProcessingAlgorithm
)

from geocatbridge.utils import gui
from geocatbridge.utils.feedback import FeedbackMixin
from geocatbridge.utils.layers import BridgeLayer
from geocatbridge.utils.enum_ import LabeledIntEnum
from geocatbridge.utils.network import BridgeSession, UPLOAD_TIMEOUT


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
    def getLabel(cls) -> str:
        """ This abstract class method must be implemented on all server subclasses.
        It should return the server type label (e.g. "GeoServer" for the GeoServerServer class).

        :returns:   A string with the server type label.
        """
        raise NotImplementedError(f"{cls.__name__} must implement getLabel()")

    @classmethod
    def getAlgorithmInstance(cls) -> Union[QgsProcessingAlgorithm, None]:
        """ This abstract class method can be implemented on all server classes, if needed.
        If the server class can also be used by a QGIS processing provider, this method should
        return a new processing algorithm instance that exposes its functionality.

        :returns:   A new algorithm instance that inherits from QgsProcessingAlgorithm.
                    If the server class does not support this, return None.
        """
        return


class ServerBase(AbstractServer, FeedbackMixin, ABC):

    def __init__(self, name, authid="", **options):
        super().__init__()
        self._apply_options(**options)
        self._name = name
        self._authid = authid
        self._username = None
        self._password = None
        self.getCredentials()

    def _apply_options(self, **kwargs):
        """ Processes class initialization options (kwargs) and adds them as first-class attribute values
        if the option names and types match the annotations defined at the top of the subclass.
        Called on `__init__()` of the ServerBase.
        """
        for keyword, value in kwargs.items():
            if keyword not in self.__class__.__annotations__:
                self.logWarning(f"'{keyword}' is an unsupported {self.__class__.__name__} keyword argument")
                continue
            keyword_type = self.__class__.__annotations__[keyword]
            try:
                if issubclass(keyword_type, LabeledIntEnum):
                    # lookup the underlying LabeledInt type using the value as index
                    value_copy = keyword_type[value]
                else:
                    # call the type using the value as parameter (re-init)
                    value_copy = keyword_type(value)
            except (ValueError, TypeError):
                self.logError(f"Keyword argument '{keyword}' of {self.__class__.__name__} has invalid value '{value}'")
                continue
            setattr(self, keyword, value_copy)

    def _collect_options(self) -> dict:
        """ Collects all first-class attribute values where the option names and types match
        the annotations defined at the top of the subclass, and returns it as a dictionary.
        Called by `getSettings()` on the ServerBase. Overrides in subclasses must call `super().getSettings()`.
        """
        options = {}
        for keyword, keyword_type in self.__class__.__annotations__.items():
            try:
                value = getattr(self, keyword)
            except AttributeError:
                continue
            if not (isinstance(value, keyword_type) or
                    (issubclass(keyword_type, LabeledIntEnum) and value in keyword_type)):
                continue
            options[keyword] = value
        return options

    def getSettings(self) -> dict:
        settings = {
            'name': self.serverName,
            'authid': self.authId,
        }
        settings.update(self._collect_options())
        return settings

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
    def testConnection(self, errors: set) -> bool:
        """ This abstract method must be implemented on all server instances.
        It tests if the connection to the server can be established.

        :params errors: A Python set in which all error messages are collected.
                        No messages will be added to the set if the connection was successful.
        :returns:       True if the connection is established, False otherwise.
        """
        pass


class CombiServerBase(AbstractServer, FeedbackMixin, ABC):

    def __init__(self, name, **servers):
        super().__init__()
        self._name = name
        self._servers = {}

        # Lazy import getModelLookup to avoid cyclic imports
        from geocatbridge.servers import getModelLookup

        supported_types = self.getCatalogTypes()
        for type_name, params in servers.items():
            try:
                server_type = getModelLookup().get(type_name)
                if not issubclass(server_type, supported_types):
                    self.logError(f'{type_name} type was not found or not supported')
                    continue
                instance = server_type(**params)  # noqa
                self.setServer(instance)  # noqa
            except Exception as err:
                self.logError(f'{type_name} type failed to initialize: {err}')
                continue

    @classmethod
    @abstractmethod
    def getCatalogTypes(cls) -> tuple:
        """ This class method must be implemented on each CombiServerBase implementation.
        It should return a tuple of allowed catalog server sub types (added by setServer(), which means
        that the types should inherit from CatalogServerBase.
        """
        raise NotImplementedError(f"{cls.__name__} must implement getCatalogTypes()")

    @abstractmethod
    def testConnection(self, errors: set) -> bool:
        """ This abstract method must be implemented on all server instances.
        It tests if the connection to the server can be established.

        :params errors: A Python set in which all error messages are collected.
                        No messages will be added to the set if the connection was successful.
        :returns:       True if the connection is established, False otherwise.
        """
        pass

    @property
    def serverName(self):
        return self._name

    def setServer(self, server):
        """ Sets (adds or overwrites) the given server instance. """
        allowed_types = (CatalogServerBase,) + self.getCatalogTypes()
        if not isinstance(server, allowed_types):
            raise TypeError(f'{self.getLabel()} must implement one of '
                            f'({", ".join(t.__name__ for t in allowed_types)})')
        server._name = self._name
        self._servers[type(server)] = server

    def getServer(self, server_type: type):
        """ Returns the first server by the given type (exact match).
        If the server was not found, the first instance type match is returned.
        If that was not found either, None is returned.
        """
        server = self._servers.get(server_type)
        if server:
            return server
        for inst in self._servers.values():
            if isinstance(inst, server_type):
                return inst
        return None

    def serverItems(self):
        return self._servers.items()

    def getSettings(self) -> dict:
        settings = {
            'name': self.serverName
        }
        for server_type, instance in self._servers.items():
            settings[server_type.__name__] = instance.getSettings()
        return settings


class CatalogServerBase(ServerBase, ABC):

    def __init__(self, name, authid="", url="", **options):
        super().__init__(name, authid, **options)
        self._baseurl = urlparse(url).geturl()

    def request(self, url, method="get", data=None, **kwargs):
        """ Wrapper function for HTTP requests. """
        # TODO: Use qgis.core.QgsBlockingNetworkRequest in later QGIS versions.
        #       This should improve proxy and authentication handling.
        #       Currently, only 3.18+ supports the PUT request (3.16 LTR does not).

        headers = kwargs.pop("headers", {})
        files_ = kwargs.pop("files", {})
        session = kwargs.pop("session", {})

        if isinstance(data, dict) and not files_:
            try:
                data = json.dumps(data)
                headers["Content-Type"] = "application/json"
            except:  # noqa
                pass

        auth = None
        self.logInfo(f"{method.upper()} {url}")
        if session and isinstance(session, requests.Session):
            # An existing Session was passed-in: call request method on it (handle auth in session!)
            req_method = getattr(session, method.casefold())
        else:
            # Perform a regular request on temp session with basic auth if credentials were set
            user, pwd = self.getCredentials()
            if user and pwd:
                auth = HTTPBasicAuth(user, pwd)
            with BridgeSession() as session:
                req_method = getattr(session, method.casefold())

        if (method.casefold() in ('put', 'post') and files_) or (isinstance(data, bytes) or hasattr(data, 'read')) or \
                headers.get('Content-Type', '').endswith(('zip', 'octet-stream')):
            # If it looks like we're going to transfer something (potentially) large, increase the timeout
            kwargs['timeout'] = max(kwargs.get('timeout', 0), UPLOAD_TIMEOUT)
        result = req_method(url, headers=headers, files=files_, data=data, auth=auth, **kwargs)
        result.raise_for_status()
        return result

    @property
    def baseUrl(self):
        """ Returns the base part of the server URL. """
        return self._baseurl

    def addOGCServices(self):
        pass

    def validateBeforePublication(self, *args, **kwargs):
        pass

    def getSettings(self) -> dict:
        settings = super().getSettings()
        # Add URL property to base settings
        settings['url'] = self.baseUrl
        return settings


class MetaCatalogServerBase(CatalogServerBase, ABC):

    def __init__(self, name, authid="", url="", **options):
        super().__init__(name, authid, url, **options)

    def openMetadata(self, uuid):
        pass

    def metadataUrl(self, uuid: str) -> str:
        """ This method must be implemented if the server has a REST API URL for the given record ID. """
        raise NotImplementedError

    def metadataExists(self, uuid: str) -> bool:
        """ This method must be implemented if the server offers a way to check if a metadata record was published. """
        raise NotImplementedError

    def publishLayerMetadata(self, layer: BridgeLayer,
                             wms_url: str = None, wfs_url: str = None, linked_name: str = None):
        """ This method must be implemented if the server offers a way to publish a metadata record for a layer. """
        raise NotImplementedError


class DataCatalogServerBase(CatalogServerBase, ABC):

    def __init__(self, name, authid="", url="", **options):
        super().__init__(name, authid, url, **options)

    def prepareForPublishing(self, only_symbology: bool):
        """ This method is called right before any publication takes place.

        :param only_symbology:  If True, a destination folder/workspace does not need to be cleared.
        """
        pass

    def clearWorkspace(self, recreate: bool = True) -> bool:
        """ This method is called by the publish widget (among others) to clear a destination
        workspace or folder. All data, layers and styling within the target workspace/folder is removed.

        :param recreate:    If True, the target workspace/folder should be recreated (i.e. empty, but existing).
        :returns:           Returns True if clearing was successful.
        """
        pass

    @abstractmethod
    def vectorLayersAsShp(self) -> bool:
        """ Returns True if vector layers must be exported as a Shapefile.
        If False is returned, GeoPackage is preferred.

        This method is called when a user starts a publish task.
        """
        raise NotImplementedError

    @abstractmethod
    def publishLayer(self, layer: BridgeLayer, fields: Iterable[str] = None):
        """ Publishes the given QGIS layer (and specified fields) to the server."""
        raise NotImplementedError

    @abstractmethod
    def publishStyle(self, layer: BridgeLayer):
        """ Publishes a style (symbology) for the given QGIS layer to the server."""
        raise NotImplementedError

    def closePublishing(self, layer_ids: Iterable[str]):
        """ This method is called after a publish task has finished.
        It may be implemented to do some clean up or perform other tasks.
        """
        pass

    def getPreviewUrl(self, layer_names: list, bbox: str, crs_authid: str) -> str:
        """ This method may be implemented for servers that support previewing published layers.
        It should return a URL to get a preview map for the given layers.

        :param layer_names: A list of layer names for which to get a preview map.
        :param bbox:        A concatenated BBOX string (XMIN, YMIN, XMAX, YMAX) for the preview map extent.
        :param crs_authid:  The coordinate system ID (e.g. EPSG code) for the preview map.
        """
        pass

    def layerNames(self) -> Dict[str, str]:
        """ Returns a lookup of all QGIS layer names matched to remote layer names in the current workspace. """
        raise NotImplementedError

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

    def createGroups(self, layer_ids: Iterable[str]):
        """ This method may be implemented to create layer groups on the server.

        :param layer_ids:  QGIS layer IDs to include in the group(s).
        """
        pass


class DbServerBase(ServerBase, ABC):

    def __init__(self, name, authid="", **options):
        super().__init__(name, authid, **options)


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
        """ Returns the parent object (usually a ConnectionsWidget instance). """
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
    def getIcon(cls) -> QIcon:
        """ Returns the Qt icon for the server list widget.
        Icons should be SVG files with the same path and name as the server widget controller.
        If a matching icon is not found, a default icon is returned.

        :return:    A QIcon object.
        """
        module_name = getattr(cls, '__module__', None)
        if module_name:
            # Retrieve the icon path from the module path
            module = import_module(module_name)
            icon = Path(module.__file__).with_suffix('.svg')
            if icon.exists():
                return gui.getCustomIcon(icon)
        # Return the default unknown.svg if no matching icon was found
        return gui.getSvgIconByName('unknown')
