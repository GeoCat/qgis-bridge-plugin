import os
import shutil
import uuid
from pathlib import Path

from qgis.PyQt.QtCore import QDir, QUrl
from jinja2 import Environment, FileSystemLoader

from geocatbridge.utils import meta

_DIR_NAME_WIDGETS = "ui"
_DIR_NAME_TRANSLATIONS = "i18n"
_DIR_NAME_ICONS = "icons"
_DIR_NAME_RESOURCES = "resources"
_DIR_NAME_DOCS = "docs"

_ABOUT_SRCDIR = "geocat"
_ABOUT_TEMPLATE = "template.html"
_ABOUT_HTMLPAGE = "index.html"

#: GeoCat Bridge Python root directory
BRIDGE_ROOT_DIR = Path(__file__).parent.parent
BRIDGE_ABOUT_DIR = BRIDGE_ROOT_DIR / _DIR_NAME_RESOURCES / _ABOUT_SRCDIR


def _fix_ext(name, ext):
    """ Appends a given extension to a file name if it doesn't have one. """
    base_name = Path(name)
    if not base_name.suffix:
        base_name = base_name.with_suffix(ext)
    return base_name


def tempFolder():
    """ Creates a directory for Bridge within the QGIS temp folder and returns the path. """
    temp_dir = os.path.join(QDir.tempPath(), meta.PLUGIN_NAMESPACE)
    if not QDir(temp_dir).exists():
        QDir().mkpath(temp_dir)
    return os.path.abspath(temp_dir)


def tempSubFolder():
    """ Creates a temporary directory within the QGIS Bridge temp folder and returns the path. """
    path = tempFolder()
    folder = os.path.join(path, uuid.uuid4().hex)
    if not QDir(folder).exists():
        QDir().mkpath(folder)
    return folder


def tempFileInSubFolder(basename):
    """ Returns a temporary file path in a temporary subfolder of the QGIS Bridge temp folder. """
    folder = tempSubFolder()
    filename = os.path.join(folder, basename)
    return filename


def removeTempFolder():
    """ Recursively deletes the QGIS Bridge temp folder. """
    shutil.rmtree(tempFolder())


def getResourcePath(name, ext=".xsl") -> str:
    """
    Constructs the full resource path for a given base name.
    If `name` does not have an extension, the given `ext` will be appended.
    :param name:    The resource file name or relative `Path`.
    :param ext:     The default resource extension (if not specified in the name).
    :returns:       A resource file path string.
    """
    return str(BRIDGE_ROOT_DIR / _DIR_NAME_RESOURCES / _fix_ext(name, ext))


def getIconPath(name, ext=".png") -> str:
    """
    Constructs the full icon path for a given base name.
    If `name` does not have an extension, the given `ext` will be appended.
    :param name:    The icon or image file name or relative `Path`.
    :param ext:     The default image extension (if not specified in the name).
    :returns:       An icon file path string.
    """
    return str(BRIDGE_ROOT_DIR / _DIR_NAME_ICONS / _fix_ext(name, ext))


def getViewPath(controller, ext=".ui") -> str:
    """
    Constructs the full Qt UI file path for a given view controller (*.py).
    UI files should always be stored in the same folder as the controller
    and bear the same name.

    :param controller:  The Python view controller file path.
    :param ext:         The default UI extension (if not specified in the name).
    :returns:           An Qt UI file path string.
    """
    return str(Path(controller).with_suffix(ext))


def getLocalePath(name, ext=".qm") -> str:
    """
    Constructs the full Qt Locale (translation) file path for a given base name.
    If `name` does not have an extension, the given `ext` will be appended.
    :param name:    The locale/translation file name or relative `Path`.
    :param ext:     The default locale extension (if not specified in the name).
    :returns:       An Qt locale/translation file path string.
    """
    return str(BRIDGE_ROOT_DIR / _DIR_NAME_TRANSLATIONS / _fix_ext(name, ext))


def getDirectory(path) -> str:
    """ Returns the parent directory path to the given file or directory path. """
    fix_path = Path(str(path).split('|')[0])  # Fix for GeoPackage layer paths
    return str(fix_path.resolve().parent)


def getAboutUrl(refresh: bool = False) -> QUrl:
    """
    Returns the QUrl for the Bridge About page (HTML).
    If 'refresh' is True or the HTML page does not exist, it is rendered from the template in the same folder.
    If the template does not exist,
    """
    target_path = (BRIDGE_ABOUT_DIR / _ABOUT_HTMLPAGE).resolve()

    # Render the index.html if it does not exist yet or if it should be updated (i.e. when version changed)
    if refresh or not target_path.is_file():
        template_path = target_path.with_name(_ABOUT_TEMPLATE)
        if not template_path.is_file():
            raise FileNotFoundError(f"HTML template at {template_path} does not exist")
        env = Environment(loader=FileSystemLoader(str(template_path.parent)))
        template = env.get_template(_ABOUT_TEMPLATE)
        html = template.render(
            app_name=meta.getAppName(),
            short_name=meta.getShortAppName(),
            doc_url=meta.getDocsUrl(),
            repo_url=meta.getRepoUrl(),
            support_url=meta.getSupportUrl(),
            homepage=meta.getHomeUrl(),
            is_enterprise=meta.isEnterprise()
        )
        with open(target_path, mode="w+", encoding="utf-8") as fp:
            fp.write(html)

    return QUrl.fromLocalFile(str(target_path))
