import os
from qgis.PyQt.QtCore import QTranslator, QCoreApplication, QSettings

__version__ = "2.0.12"

libFolder = os.path.dirname(__file__)
localePath = ""
locale = QSettings().value("locale/userLocale")[0:2]

if os.path.exists(libFolder):
    localePath = os.path.join(libFolder, "i18n", "qgiscommons_" + locale + ".qm")

translator = QTranslator()
if os.path.exists(localePath):
    translator.load(localePath)
    QCoreApplication.installTranslator(translator)