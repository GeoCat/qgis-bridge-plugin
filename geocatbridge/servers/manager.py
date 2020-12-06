import json
from importlib import import_module
from inspect import isclass
from pathlib import Path
from pkgutil import iter_modules

from qgis.PyQt.QtCore import QSettings

from geocatbridge.servers import bases
from geocatbridge.servers import models
from geocatbridge.utils import meta
from geocatbridge.utils import feedback
from geocatbridge.utils.enum_ import LabeledIntEnum

# QGIS setting that stores all configured Bridge servers
SERVERS_SETTING = f"{meta.PLUGIN_NAMESPACE}/BridgeServers"

# Globals for server model and instance lookup
_types = {}
_instances = {}


class UnknownServerError(NameError):
    """ Raised when a server type is listed in the settings that does not exist (anymore). """
    pass


class ServerInitError(TypeError):
    """ Raised when a server class failed to initialize. """
    pass


def _loadServerTypes(force: bool = False):
    """ Load all supported server class models from the `servers.models` folder.

    :param force:   When True (default is False), all server models will be reloaded.
    """
    global _types

    if force:
        # Reset the available server types
        _types = {}

    if _types:
        # Do nothing if the server types were already loaded
        return

    # Iterate all modules in the models folder
    package_dir = Path(models.__file__).resolve().parent
    for (_, module_name, _) in iter_modules([package_dir]):
        module = import_module(f"{models.__name__}.{module_name}")
        # Iterate all non-imported classes in the module
        for name, cls in ((k, v) for k, v in module.__dict__.items() if isclass(v) and v.__module__ == module.__name__):
            # Server class must inherit from ServerBase
            if not issubclass(cls, bases.ServerBase):
                continue
            # Concrete server classes that do NOT implement the AbstractServer methods
            # will raise a TypeError once the class is being initialized.
            # However, that error message is rather obscure, so we will check beforehand
            # if the methods have been implemented and log warnings.
            add_type = True
            for method in getattr(bases.AbstractServer, '__abstractmethods__'):
                if hasattr(getattr(cls, method, None), '__isabstractmethod__'):
                    feedback.logWarning(f"{name} class does not implement {method}() method")
                    add_type = False
            # Add type to dictionary if tests passed
            if add_type:
                _types[name] = cls


def _initServer(type_name: str, **props):
    """ Look up the given server type name and initialize the corresponding server class.

    :param type_name:   The server type name to initialize.
    :param props:       The keyword arguments required for the __init__ call.
    :return:            An instance of type `type_name`.
    """
    global _types

    _loadServerTypes()
    cls = _types.get(type_name)
    if not cls:
        raise UnknownServerError(f"unsupported '{type_name}' server in {SERVERS_SETTING} configuration: "
                                 f"must be one of [{', '.join(sorted(_types.keys()))}]")
    try:
        return cls(**props)
    except (TypeError, AttributeError) as e:
        call_params = ', '.join(f"{k}={v}" for k, v in props.items())
        raise ServerInitError(f"could not initialize {type_name}({call_params}):\n{e}")


def _getServerAsTuple(server):
    """ Verifies that the given server can be recreated using the values from `getSettings()`.
        If this is the case, a tuple of (type, params) will be returned. Otherwise, None is returned.
    """
    param_func = bases.AbstractServer.getSettings.__name__
    get_kwargs = getattr(server, param_func, None)
    params = get_kwargs() if get_kwargs else {}
    server_type = server.__class__.__name__
    try:
        # Test that the server class can be instantiated again using the output from getSettings()
        _initServer(server_type, **params)
    except ServerInitError as e:
        # Report error that the server cannot be initialized with the given parameters
        feedback.logError(f"{server_type}.{param_func}() returns bad parameters:\n{e}")
        return
    return server_type, params


def getServerTypes():
    """ Returns a generator of available server types (model) to use in a UI menu. """
    global _types

    _loadServerTypes()
    for t in _types.values():
        yield t


def saveConfiguredServers() -> bool:
    """ Calls `getSettings()` on all initialized servers and stores them in the QGIS server settings. """
    global _instances

    server_config = []
    bad_servers = []

    # Test servers
    for s in _instances.values():
        server_tuple = _getServerAsTuple(s)
        if not server_tuple:
            feedback.logError(f"Server configuration for '{s.serverName}' cannot be saved in QGIS settings.'")
            bad_servers.append(s.serverName)
            continue
        server_config.append(server_tuple)

    # Remove bad servers (if any)
    while bad_servers:
        del _instances[bad_servers.pop()]

    # Write QSettings value
    try:
        config_str = json.dumps(server_config)
    except TypeError as e:
        feedback.logError(f"Failed to serialize server configuration as JSON: {e}")
        return False
    else:
        QSettings().setValue(SERVERS_SETTING, config_str)
    return True


def loadConfiguredServers():
    """ Reads all configured servers from the QGIS settings and initializes them. """
    global _instances

    # Read QGIS Bridge server settings string
    server_config = QSettings().value(SERVERS_SETTING)
    if not server_config:
        feedback.logWarning(f"Could not find existing QGIS setting '{SERVERS_SETTING}'")
        return

    # Parse JSON object from settings string
    try:
        stored_servers = json.loads(server_config)
    except json.JSONDecodeError as e:
        feedback.logWarning(f"Failed to parse {SERVERS_SETTING} configuration:\n{e}")
        return

    # It is expected that `stored_servers` is a list
    assert isinstance(stored_servers, list)

    # Instantiate servers from models and settings
    for (server_type, properties) in stored_servers:
        try:
            s = _initServer(server_type, **properties)
        except (UnknownServerError, ServerInitError) as e:
            feedback.logError(f"Failed to load server:\n{e}")
            continue
        _instances[s.serverName] = s


def getServer(name: str):
    """ Retrieves a server instance by its name. Returns None if not found. """
    global _instances
    return _instances.get(name)


def getGeodataServer(name: str):
    """ Returns the geodata server instance with the given name (or `None` when not found). """
    server = getServer(name)
    if isinstance(server, bases.DataCatalogServerBase):
        return server
    return None


def getMetadataServer(name: str):
    """ Returns the metadata server instance with the given name (or `None` when not found). """
    server = getServer(name)
    if isinstance(server, bases.MetaCatalogServerBase):
        return server
    return None


def getServers():
    """ Retrieves all available server instances. """
    global _instances
    return _instances.values()


def getMetadataServers():
    """ Retrieves all available metadata server instances. """
    return [s for s in getServers() if isinstance(s, bases.MetaCatalogServerBase)]


def getGeodataServers():
    """ Retrieves all available (geo)data server instances. """
    return [s for s in getServers() if isinstance(s, bases.DataCatalogServerBase)]


def getDbServers():
    """ Retrieves all available database server instances. """
    return [s for s in getServers() if isinstance(s, bases.DbServerBase)]


def getServerNames() -> frozenset:
    """ Retrieves all configured server names. """
    global _instances
    return frozenset(_instances.keys())


def getMetadataProfile(server_name: str) -> LabeledIntEnum:
    """ Returns the metadata profile for the given server name.

    :param server_name: The name of the server for which to retrieve the profile.

    :returns:   The metadata profile (integer-like `LabeledIntEnum`).
    :raises:    Exception if server was not found or not a metadata catalog server.
    """
    server = getServer(server_name)
    if server and hasattr(server, 'profile'):
        return server.profile
    raise Exception('Server is not a metadata catalog server')


def generateName(server_class) -> str:
    """ Generates an available server name for the given server class. """
    label = server_class.getServerTypeLabel()
    servers = getServerNames()
    i = 1
    while True:
        new_name = f"{label}{i}"
        if new_name not in servers:
            return new_name
        else:
            i += 1


def addServer(server) -> bool:
    """ Adds the given server (instance) to the Bridge server settings.

    :param server:  The new server instance to store.
    """
    global _instances

    server_name = getattr(server, bases.ServerBase.serverName.__name__, None)
    if not server_name:
        # This should not happen if the server properly implements ServerBase
        feedback.logError(f"Cannot store server of type '{server.__class__.__name__}': missing name")
        return False
    if server_name in _instances:
        # This should not happen if the name passed through generateName() first
        feedback.logError(f"A '{server.__class__.__name__}' instance named '{server_name}' already exists")
        return False
    _instances[server_name] = server
    # TODO: call addOGCServers()?
    if not saveConfiguredServers():
        del _instances[server_name]
        return False
    return True


def removeServer(name):
    """ Removes the server with the given name from the Bridge server settings.

    :param name:    The server name as defined by the user.
    """
    global _instances

    try:
        del _instances[name]
    except KeyError:
        feedback.logWarning(f"Server named '{name}' does not exist or has already been removed")
    else:
        saveConfiguredServers()
