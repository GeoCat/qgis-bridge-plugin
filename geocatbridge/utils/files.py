import os
import shutil
import uuid
from pathlib import Path

from qgis.PyQt.QtCore import QDir

from geocatbridge.utils import meta

#: GeoCat Bridge Python root directory
BRIDGE_ROOT_DIR = Path(__file__).parent.parent

_DIR_NAME_WIDGETS = "ui"
_DIR_NAME_TRANSLATIONS = "i18n"
_DIR_NAME_ICONS = "icons"
_DIR_NAME_RESOURCES = "resources"
_DIR_NAME_DOCS = "docs"


def _fix_ext(name, ext):
    """ Appends a given extension to a file name if it doesn't have one. """
    base_name = Path(name)
    if not base_name.suffix:
        base_name = base_name.with_suffix(ext)
    return base_name


def tempFolder():
    temp_dir = os.path.join(QDir.tempPath(), meta.PLUGIN_NAMESPACE)
    if not QDir(temp_dir).exists():
        QDir().mkpath(temp_dir)
    return os.path.abspath(temp_dir)


def tempFolderInTempFolder():
    path = tempFolder()
    folder = os.path.join(path, uuid.uuid4().hex)
    if not QDir(folder).exists():
        QDir().mkpath(folder)
    return folder


def tempFilenameInTempFolder(basename):
    folder = tempFolderInTempFolder()    
    filename = os.path.join(folder, basename)
    return filename


def removeTempFolder():    
    shutil.rmtree(tempFolder())


def getResourcePath(name, ext=".xsl"):
    """
    Constructs the full resource path for a given base name.
    If `name` does not have an extension, the given `ext` will be appended.
    :param name:    The resource file name or relative `Path`.
    :param ext:     The default resource extension (if not specified in the name).
    :returns:       A resource file path string.
    """
    return str(BRIDGE_ROOT_DIR / _DIR_NAME_RESOURCES / _fix_ext(name, ext))


def getIconPath(name, ext=".png"):
    """
    Constructs the full icon path for a given base name.
    If `name` does not have an extension, the given `ext` will be appended.
    :param name:    The icon or image file name or relative `Path`.
    :param ext:     The default image extension (if not specified in the name).
    :returns:       An icon file path string.
    """
    return str(BRIDGE_ROOT_DIR / _DIR_NAME_ICONS / _fix_ext(name, ext))


def getViewPath(controller, ext=".ui"):
    """
    Constructs the full Qt UI file path for a given view controller (*.py).
    UI files should always be stored in the same folder as the controller
    and bear the same name.

    :param controller:  The Python view controller file path.
    :param ext:         The default UI extension (if not specified in the name).
    :returns:           An Qt UI file path string.
    """
    return Path(controller).with_suffix(ext)


def getLocalePath(name, ext=".qm"):
    """
    Constructs the full Qt Locale (translation) file path for a given base name.
    If `name` does not have an extension, the given `ext` will be appended.
    :param name:    The locale/translation file name or relative `Path`.
    :param ext:     The default locale extension (if not specified in the name).
    :returns:       An Qt locale/translation file path string.
    """
    return str(BRIDGE_ROOT_DIR / _DIR_NAME_TRANSLATIONS / _fix_ext(name, ext))


def getHtmlDocsPath(name, ext=".html"):
    """
    Constructs the full HTML documentation file path for a given base name.
    If `name` does not have an extension, the given `ext` will be appended.
    :param name:    The documentation file name or relative `Path`.
    :param ext:     The default docs extension (if not specified in the name).
    :returns:       A browser-ready documentation file path string.
    """
    return f"file://{BRIDGE_ROOT_DIR / _DIR_NAME_DOCS / _fix_ext(name, ext)}"


def getDirectory(path):
    """ Returns the parent directory path to the given file or directory path. """
    return str(Path(path).resolve().parent)
