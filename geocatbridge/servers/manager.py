import json
from typing import Union

from qgis.PyQt.QtCore import QSettings

from geocatbridge.servers import bases, getModelLookup
from geocatbridge.utils import feedback
from geocatbridge.utils import meta
from geocatbridge.utils.enum_ import LabeledIntEnum

# QGIS setting that stores all configured Bridge servers
SERVERS_SETTING = f"{meta.PLUGIN_NAMESPACE}/BridgeServers"

# Global for server instance lookup
_instances = {}


class UnknownServerError(NameError):
    """ Raised when a server type is listed in the settings that does not exist (anymore). """
    pass


class ServerInitError(TypeError):
    """ Raised when a server class failed to initialize. """
    pass


def _initServer(type_name: str, **props):
    """ Look up the given server type name and initialize the corresponding server class.

    :param type_name:   The server type name to initialize.
    :param props:       The keyword arguments required for the __init__ call.
    :return:            An instance of type `type_name`.
    """
    cls = getModelLookup().get(type_name)
    if not cls:
        raise UnknownServerError(f"unsupported '{type_name}' server in {SERVERS_SETTING} configuration: "
                                 f"must be one of [{', '.join(sorted(getModelLookup().keys()))}]")
    try:
        return cls(**props)
    except (TypeError, AttributeError) as e:
        call_params = ', '.join(f"{k}={v}" for k, v in props.items())
        raise ServerInitError(f"could not initialize {type_name}({call_params}): {e}")


def _getServerAsTuple(server):
    """ Verifies that the given server instance can be recreated using the values from `getSettings()`.
        If this is the case, a tuple of (type, params) will be returned. Otherwise, None is returned.
    """
    try:
        params = server.getSettings() or {}
    except (AttributeError, NotImplementedError):
        # This should not happen if the server properly implements AbstractServer
        feedback.logError(f"Server does not implement {bases.AbstractServer.__name__}.getSettings")
        return

    server_type = server.__class__.__name__
    try:
        # Test that the server class can be instantiated again using the output from getSettings()
        _initServer(server_type, **params)
    except ServerInitError as e:
        # Report error that the server cannot be initialized with the given parameters
        feedback.logError(f"{server_type}.getSettings() returned bad parameters: {e}")
        return
    return server_type, params


def getServerTypes():
    """ Returns a generator of available server types (model) to use in a UI menu. """
    for t in getModelLookup().values():
        yield t


def serializeServers() -> Union[str, None]:
    """ Calls `getSettings()` on all initialized serializable servers and returns them as a JSON string. """
    global _instances

    server_config = []
    bad_servers = []

    # Test servers
    for s in _instances.values():
        server_tuple = _getServerAsTuple(s)
        if not server_tuple:
            feedback.logError(f"Server configuration for '{s.serverName}' cannot be saved and will be removed.'")
            bad_servers.append(s.serverName)
            continue
        server_config.append(server_tuple)

    # Remove bad servers (if any)
    while bad_servers:
        del _instances[bad_servers.pop()]

    # Serialize JSON and output string
    try:
        config_str = json.dumps(server_config, indent=4)
    except TypeError as e:
        feedback.logError(f"Failed to serialize server configuration as JSON: {e}")
        return
    return config_str


def deserializeServers(config_str: str) -> bool:
    """ Deserializes a JSON server configuration string and creates Bridge server instances.

    :param config_str:  A JSON string. Must be deserializable as a list of (str, dict).
    :returns:           True when successful, False otherwise.
    """
    global _instances

    # Parse JSON object from settings string
    try:
        stored_servers = json.loads(config_str)
    except json.JSONDecodeError as e:
        feedback.logError(f"Failed to parse servers configuration: {e}")
        return False

    # It is expected that `stored_servers` is a list
    if not isinstance(stored_servers, list) or len(stored_servers) == 0:
        feedback.logError("Server configuration must be a non-empty list")
        return False

    # Instantiate servers from models and settings
    num_added = 0
    for (server_type, properties) in stored_servers:
        name = properties.get('name')
        if not name:
            feedback.logWarning(f'Skipped {server_type} entry due to missing name')
            continue
        key = getUniqueName(name)
        if key != name:
            properties['name'] = key
        try:
            s = _initServer(server_type, **properties)
        except (UnknownServerError, ServerInitError) as e:
            feedback.logError(f"Failed to load {server_type} type: {e}")
            continue
        if key != name:
            feedback.logWarning(f"Changed name from '{name}' to '{key}' for "
                                f"non-unique {s.getLabel()} entry")
        _instances[key] = s
        num_added += 1

    # Return True if any of the servers initialized successfully
    return num_added > 0


def saveConfiguredServers() -> bool:
    """ Persists all valid initialized servers in the QGIS server settings. """
    config_str = serializeServers()
    if config_str is None:
        return False
    QSettings().setValue(SERVERS_SETTING, config_str)
    return True


def loadConfiguredServers() -> bool:
    """ Reads all configured servers from the QGIS settings and initializes them. """

    # Read QGIS Bridge server settings string
    server_config = QSettings().value(SERVERS_SETTING)
    if not server_config:
        feedback.logInfo(f"Could not find existing {meta.getAppName()} setting '{SERVERS_SETTING}'")
        return False

    # Deserialize JSON and initialize servers
    return deserializeServers(server_config)


def getServer(name: str):
    """ Retrieves a server instance by its name. Returns None if not found. """
    global _instances
    return _instances.get(name)


def _refineByType(server, type_: type):
    """ Retrieves a nested server instance by `type_` if the given `server` implements CombiServerBase.
    If the given `server` does not implement CombiServerBase, it is returned as-is if it implements `type_`.
    In all other cases, `None` is returned.
    """
    if isinstance(server, type_):
        return server
    elif isinstance(server, bases.CombiServerBase):
        return server.getServer(type_)
    return None


def getGeodataServer(name: str):
    """ Returns the geodata server instance with the given name (or `None` when not found). """
    server = getServer(name)
    return _refineByType(server, bases.DataCatalogServerBase)


def getMetadataServer(name: str):
    """ Returns the metadata server instance with the given name (or `None` when not found). """
    server = getServer(name)
    return _refineByType(server, bases.MetaCatalogServerBase)


def getServers():
    """ Retrieves all available server instances. """
    global _instances
    return _instances.values()


def getMetadataServers():
    """ Retrieves all available metadata server instances. """
    return [s for s in (_refineByType(s, bases.MetaCatalogServerBase) for s in getServers()) if s]


def getGeodataServers():
    """ Retrieves all available (geo)data server instances. """
    return [s for s in (_refineByType(s, bases.DataCatalogServerBase) for s in getServers()) if s]


def getDbServers():
    """ Retrieves all available database server instances. """
    return [s for s in getServers() if isinstance(s, bases.DbServerBase)]


def getGeodataServerNames():
    """ Retrieves all available (geo)data server names. """
    return [s.serverName for s in getGeodataServers()]


def getMetadataServerNames():
    """ Retrieves all available metadata server names. """
    return [s.serverName for s in getMetadataServers()]


def getDbServerNames():
    """ Retrieves all available database server names. """
    return [s.serverName for s in getDbServers()]


def getServerNames() -> frozenset:
    """ Retrieves all configured server names. """
    global _instances
    return frozenset(s.serverName for s in getServers())


def getMetadataProfile(server_name: str) -> LabeledIntEnum:
    """ Returns the metadata profile for the given server name.

    :param server_name: The name of the server for which to retrieve the profile.

    :returns:   The metadata profile (integer-like `LabeledIntEnum`).
    :raises:    Exception if server was not found or not a metadata catalog server.
    """
    server = getMetadataServer(server_name)
    if server and hasattr(server, 'profile'):
        return server.profile
    raise Exception('Server is not a metadata catalog server')


def getUniqueName(preferred_name: str) -> str:
    """ Generates an available server name for the given server name. """
    servers = getServerNames()
    new_name = preferred_name
    i = 0
    while True:
        if new_name not in servers:
            return new_name
        i += 1
        new_name = f"{preferred_name}{i}"


def saveServer(server, replace_key: str) -> bool:
    """ Adds the given server (instance) to the Bridge server settings.
    Returns True if the instance was successfully saved.

    :param server:      The new server instance to store.
    :param replace_key: The key (server name) under which to save the server instance.
                        If the key matches the `server.serverName`, the server is updated
                        under that key. If it doesn't match, the server instance under the
                        given key is deleted and a new instance is saved under a new key
                        equal to the `server.serverName`.

    :returns:   True if save was successful.
    :raises:    ValueError if `replace_key` does not match the `server.serverName` and the new
                `server.serverName` already exists in the `_instances` dictionary (duplicate key),
                or if `server.serverName` is empty.
    """
    global _instances

    if not isinstance(server, (bases.ServerBase, bases.CombiServerBase)):
        # This should not happen if the server properly implements (Combi)ServerBase
        feedback.logError(f"Cannot store server of type '{server.__class__.__name__}': "
                          f"must implement {bases.ServerBase.__name__} or {bases.CombiServerBase.__name__}")
        return False

    if not server.serverName:
        # Make sure that the server has a non-empty name
        raise ValueError('server name cannot be empty')

    if replace_key != server.serverName:
        # User has renamed the server: check if new name does not exist yet
        if server.serverName in getServerNames():
            raise ValueError(f"server named '{server.serverName}' already exists")
        try:
            # Remove instance under old name
            del _instances[replace_key]
        except KeyError:
            feedback.logWarning(f"server named '{replace_key}' does not exist")

    # Save instance using (new) server name as key
    _instances[server.serverName] = server
    if isinstance(server, bases.CatalogServerBase):
        server.addOGCServices()
    if not saveConfiguredServers():
        # Remove server again if the instance could not be saved in QGIS settings
        del _instances[server.serverName]
        return False
    return True


def removeServer(name, silent: bool = False):
    """ Removes the server with the given name from the Bridge server settings.

    :param name:    The server name as defined by the user.
    :param silent:  If True (default is False), a warning is logged when
                    the server name does not exist.
    """
    global _instances

    try:
        del _instances[name]
    except KeyError:
        if not silent:
            feedback.logWarning(f"Server named '{name}' does not exist or has already been removed")
    else:
        saveConfiguredServers()
