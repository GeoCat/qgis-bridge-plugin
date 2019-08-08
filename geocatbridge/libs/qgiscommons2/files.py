import os
import shutil
import uuid
import time

from qgis.PyQt.QtCore import QDir
from qgis.PyQt.QtWidgets import QFileDialog

from qgiscommons2.utils import _callerName


def removeTempFolder(namespace = None):
    namespace = namespace or _callerName().split(".")[0]
    shutil.rmtree(tempFolder(namespace))


def tempFolder(namespace = None):
    namespace = namespace or _callerName().split(".")[0]
    tempDir = os.path.join(unicode(QDir.tempPath()), "qgiscommons2", namespace)
    if not QDir(tempDir).exists():
        QDir().mkpath(tempDir)
    return unicode(os.path.abspath(tempDir))

def tempFilename(ext = None, namespace = None):
    namespace = namespace or _callerName().split(".")[0]
    ext = "." + ext if ext is not None else ""
    filename = os.path.join(tempFolder(namespace), str(time.time()) + ext)
    return filename

def tempFilenameInTempFolder(basename, namespace = None):
    namespace = namespace or _callerName().split(".")[0]
    path = tempFolder(namespace)
    folder = os.path.join(path, str(uuid.uuid4()).replace("-",""))
    if not QDir(folder).exists():
        QDir().mkpath(folder)
    filename =  os.path.join(folder, basename)
    return filename


def tempFolderInTempFolder(namespace = None):
    namespace = namespace or _callerName().split(".")[0]
    path = tempFolder(namespace)
    folder = os.path.join(path, str(uuid.uuid4()).replace("-",""))
    if not QDir(folder).exists():
        QDir().mkpath(folder)
    return folder
