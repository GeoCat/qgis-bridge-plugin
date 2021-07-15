import configparser
from pathlib import Path
from typing import Tuple
from re import compile

#: GeoCat Bridge plugin namespace
PLUGIN_NAMESPACE = "geocatbridge"

#: Semantic version regex
VERSION_REGEX = compile(r'^(\d+)\.(\d+).*')

_prop_cache = {}
_meta_parser = configparser.ConfigParser()


def _load():
    _meta_parser.read(str(Path(__file__).parent.parent / 'metadata.txt'))


def semanticVersion(version: str) -> Tuple[int, int]:
    """ Converts a version string to a (major, minor) version tuple. """
    m = VERSION_REGEX.match(version)
    if not m or len(m.groups()) != 2:
        return 0, 0
    return tuple(int(v) for v in m.groups())  # noqa


def getProperty(name, section='general'):
    """ Reads the property with the given name from the **local** plugin metadata. """
    key = f'{section}.{name}'
    try:
        value = _prop_cache.get(key, _meta_parser.get(section, name))
    except (configparser.NoOptionError, configparser.NoSectionError):
        value = None
    _prop_cache[key] = value
    return value


def getAppName() -> str:
    """ Returns the name of the QGIS Bridge plugin. """
    return getProperty("name")


def getLongAppName() -> str:
    """ Returns the full name of the QGIS Bridge plugin.
    Depending on the settings, this may return the same as calling getAppName(). """
    long_name = getProperty("longName", "bridge")
    if long_name:
        return long_name
    return getAppName()


def getShortAppName() -> str:
    """ Returns the short name of the QGIS Bridge plugin.
    Depending on the settings, this may return the same as calling getAppName(). """
    short_name = getProperty("shortName", "bridge")
    if short_name:
        return short_name
    return getAppName()


def getTrackerUrl() -> str:
    """ Returns the issue tracker URL for GeoCat Bridge. """
    return getProperty("tracker")


def getVersion() -> str:
    """ Returns the GeoCat Bridge version string. """
    return getProperty("version").strip()


def getDocsUrl() -> str:
    """ Returns the GeoCat Bridge documentation URL. """
    return getProperty("docs", "bridge").rstrip('/')


_load()
