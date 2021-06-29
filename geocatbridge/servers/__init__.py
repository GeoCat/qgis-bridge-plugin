from importlib import import_module
from inspect import isclass
from pathlib import Path
from pkgutil import iter_modules

import geocatbridge.servers.bases
import geocatbridge.servers.models
from geocatbridge.utils import feedback

# Global for server model lookup (cache)
_types = {}


def getModelLookup(force: bool = False) -> dict:
    """ Load all supported server class models from the `servers.models` folder and returns a lookup dict.
    The dictionary has the model names as keys and the actual types/classes as values.

    :param force:   When True (default is False), all server models will be reloaded.
    """
    global _types

    if force:
        # Reset the available server types
        _types = {}

    if _types:
        # Do nothing if the server types were already loaded
        return _types

    package_dir = Path(models.__file__).resolve().parent
    for (_, module_name, _) in iter_modules([package_dir]):
        module = import_module(f"{models.__name__}.{module_name}")
        # Iterate all non-imported classes in the module
        for name, cls in ((k, v) for k, v in module.__dict__.items() if isclass(v) and v.__module__ == module.__name__):  # noqa
            # Server class must inherit from ServerBase or CombiServerBase
            if not issubclass(cls, (bases.ServerBase, bases.CombiServerBase)):
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

    return _types
