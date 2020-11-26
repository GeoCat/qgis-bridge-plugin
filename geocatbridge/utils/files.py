import os
import shutil
import uuid
from pathlib import Path

from qgis.PyQt.QtCore import QDir

ICONS_DIR = Path(__file__).parent.parent / "icons"


def tempFolder():
    temp_dir = os.path.join(QDir.tempPath(), "geocatbridge")
    if not QDir(temp_dir).exists():
        QDir().mkpath(temp_dir)
    return os.path.abspath(temp_dir)


def tempFolderInTempFolder():
    path = tempFolder()
    folder = os.path.join(path, str(uuid.uuid4()).replace("-", ""))
    if not QDir(folder).exists():
        QDir().mkpath(folder)
    return folder


def tempFilenameInTempFolder(basename):
    folder = tempFolderInTempFolder()    
    filename = os.path.join(folder, basename)
    return filename


def removeTempFolder():    
    shutil.rmtree(tempFolder())


def getIconPath(name, ext=".png"):
    """
    Constructs the full icon path for a given base name.
    If `name` does not have an extension, the given `ext` will be appended.
    :param name:    The icon or image file name.
    :param ext:     The default image extension (if not specified in the name).
    :returns:       An icon file path string.
    """
    base_name = Path(name)
    if not base_name.suffix:
        base_name = base_name.with_suffix(ext)
    return str(ICONS_DIR / base_name)
