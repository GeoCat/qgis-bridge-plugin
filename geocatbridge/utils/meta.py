import configparser
from pathlib import Path
from re import compile

from qgis.PyQt.QtCore import qVersion

#: GeoCat Bridge plugin namespace
PLUGIN_NAMESPACE = "geocatbridge"

#: Plugin metadata file path
PLUGIN_METAPATH = (Path(__file__).parent.parent / "metadata.txt").resolve()

#: Sections in metadata.txt file
SECTION_DEFAULT = "general"
SECTION_BRIDGE = "bridge"

#: Semantic version regex
VERSION_REGEX = compile(r'^(\d+)\.?(\d+)?\.?(\d+)?')

_prop_cache = {}
_meta_parser = configparser.ConfigParser()


class SemanticVersion:
    def __init__(self, version):
        self._major, self._minor, self._patch = self._parse(version)
        self._comp = f"{self._major:0>6}.{self._minor:0>6}.{self._patch:0>6}"
        self._valid = not (self.major == self.minor == self.patch == 0)
        self._actual = str(version).strip()

    @staticmethod
    def _parse(version: str):
        """ Converts a version string to a (major, minor, patch) version tuple. """
        if isinstance(version, SemanticVersion):
            yield from (version._major, version._minor, version._patch)  # noqa
            return
        m = VERSION_REGEX.match(str(version).strip() or '0')  # Interpret empty strings as version 0.0.0
        if m is None or len(m.groups()) != 3:
            raise ValueError(f"'{version}' is not a valid semantic version")
        for g in m.groups():
            yield int(g or 0)

    @property
    def major(self) -> int:
        """ The major version number (first number). """
        return self._major

    @property
    def minor(self) -> int:
        """ The minor version number (second number). """
        return self._minor

    @property
    def patch(self) -> int:
        """ The patch version number (third number). Defaults to 0 if not set. """
        return self._patch

    @property
    def is_official(self) -> bool:
        """ Returns True if the version number only contains valid digits (e.g. not a beta or RC). """
        return self and self._actual and self._actual[-1].isdigit()

    def __bool__(self):
        return self._valid

    def __str__(self):
        """ Returns the actual version number as it was passed in. """
        return self._actual

    def __eq__(self, other):
        """ Numeric equality comparison of 2 semantic versions. """
        return self._comp == SemanticVersion(other)._comp

    def __gt__(self, other):
        return self._comp > SemanticVersion(other)._comp

    def __lt__(self, other):
        return self._comp < SemanticVersion(other)._comp

    def __ge__(self, other):
        return self._comp >= SemanticVersion(other)._comp

    def __le__(self, other):
        return self._comp <= SemanticVersion(other)._comp


def _load():
    _meta_parser.read(str(PLUGIN_METAPATH))


def getProperty(name, section=SECTION_DEFAULT):
    """ Reads the property with the given name from the **local** plugin metadata. """
    key = f'{section}.{name}'
    try:
        value = _prop_cache.get(key, _meta_parser.get(section, name))
    except (configparser.NoOptionError, configparser.NoSectionError):
        value = None
    _prop_cache[key] = value
    return value


def getAuthor() -> str:
    """ Returns the author of the QGIS Bridge plugin. """
    return getProperty("author")


def getAppName() -> str:
    """ Returns the name of the QGIS Bridge plugin. """
    return getProperty("name")


def getLongAppName() -> str:
    """ Returns the full name of the QGIS Bridge plugin.
    Depending on the settings, this may return the same as calling getAppName(). """
    long_name = getProperty("longName", SECTION_BRIDGE)
    if long_name:
        return long_name
    return getAppName()


def getLongAppNameWithMinVersion() -> str:
    """ Returns the full name of the QGIS Bridge plugin with the minimum required QGIS version. """
    return f"{getAppName()} {getVersion()} for QGIS {getQqisMinimumVersion()}+"


def getLongAppNameWithCurrentVersion() -> str:
    """ Returns the full name of the QGIS Bridge plugin with the current QGIS version. """
    return f"{getAppName()} {getVersion()} on QGIS {getCurrentQgisVersion()}"


def getCurrentQgisVersion() -> str:
    """ Returns the current QGIS version string. """
    try:
        # Lazy import to prevent crashes when running outside QGIS environment
        from qgis.core import Qgis
    except (ImportError, ModuleNotFoundError):
        return "QGIS version unknown"

    version = Qgis().version()
    revision = Qgis().QGIS_DEV_VERSION
    if revision:
        version += f" (rev {revision})"
    return version


def getCurrentQtVersion() -> SemanticVersion:
    return SemanticVersion(qVersion())


def getShortAppName() -> str:
    """ Returns the short name of the QGIS Bridge plugin.
    Depending on the settings, this may return the same as calling getAppName(). """
    short_name = getProperty("shortName", SECTION_BRIDGE)
    if short_name:
        return short_name
    return getAppName()


def getTrackerUrl() -> str:
    """ Returns the issue tracker URL for GeoCat Bridge (i.e. GitHub). """
    return getProperty("tracker")


def getRepoUrl() -> str:
    """ Returns the Git repository URL for GeoCat Bridge (i.e. GitHub). """
    return getProperty("repository")


def getHomeUrl() -> str:
    """ Returns the homepage URL for GeoCat Bridge. """
    return getProperty("homepage")


def getVersion() -> SemanticVersion:
    """ Returns the GeoCat Bridge version string. """
    return SemanticVersion(getProperty("version"))


def getQqisMinimumVersion() -> str:
    """ Returns the minimum required QGIS version (string!) for the plugin. """
    return getProperty("qgisMinimumVersion")


def getChatUrl() -> str:
    """ Returns the Gitter chat URL for GeoCat Bridge. """
    return getProperty("chat", SECTION_BRIDGE)


def getDocsUrl() -> str:
    """ Returns the GeoCat Bridge documentation URL for the current (major.minor) release. """
    doc_url = getProperty('docs', SECTION_BRIDGE)
    if not doc_url:
        raise ValueError("Bridge documentation URL has not been set")
    semver = getVersion()
    return f"{doc_url.rstrip('/')}/v{semver.major}.{semver.minor}/"


def isEnterprise() -> bool:
    """ Returns True if this is the GeoCat Bridge Enterprise edition. """
    try:
        from geocatbridge.utils import license  # noqa
    except ImportError:
        return False
    return True


_load()
