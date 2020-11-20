import os
import shutil
import uuid

from qgis.PyQt.QtCore import QDir

def tempFolder():
    tempDir = os.path.join(QDir.tempPath(), "geocatbridge")
    if not QDir(tempDir).exists():
        QDir().mkpath(tempDir)
    return os.path.abspath(tempDir)

def tempFolderInTempFolder():
    path = tempFolder()
    folder = os.path.join(path, str(uuid.uuid4()).replace("-",""))
    if not QDir(folder).exists():
        QDir().mkpath(folder)
    return folder

def tempFilenameInTempFolder(basename):
    folder = tempFolderInTempFolder()    
    filename = os.path.join(folder, basename)
    return filename

def removeTempFolder():    
    shutil.rmtree(tempFolder())