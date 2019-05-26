import os
import json

from qgiscommons2.utils import _callerName, _callerPath
from qgis.PyQt.QtCore import Qt

try:
    from qgis.core import QgsSettings
    settings = QgsSettings()
except:
    from qgis.PyQt.QtCore import QSettings
    settings = QSettings()

try:
    from qgis.PyQt.QtCore import QPyNullVariant
except:
    pass


#Types to use in the settings.json file

BOOL = "bool"
STRING = "string"
TEXT = "text" # a multiline string
NUMBER = "number"
FILE = "file"
FILES = "files"
FOLDER = "folder"
CHOICE  ="choice"
CRS = "crs"
AUTHCFG = "authcfg"

_pythonTypes = {NUMBER: float, BOOL: bool}

def setPluginSetting(name, value, namespace = None):
    '''
    Sets the value of a plugin setting.

    :param name: the name of the setting. It is not the full path, but just the last name of it
    :param value: the value to set for the plugin setting
    :param namespace: The namespace. If not passed or None, the namespace will be inferred from
    the caller method. Normally, this should not be passed, since it suffices to let this function
    find out the plugin from where it is being called, and it will automatically use the
    corresponding plugin namespace
    '''
    namespace = namespace or _callerName().split(".")[0]
    settings.setValue(namespace + "/" + name, value)


def pluginSetting(name, namespace=None, typ=None):
    '''
    Returns the value of a plugin setting.

    :param name: the name of the setting. It is not the full path, but just the last name of it
    :param namespace: The namespace. If not passed or None, the namespace will be inferred from
    the caller method. Normally, this should not be passed, since it suffices to let this function
    find out the plugin from where it is being called, and it will automatically use the
    corresponding plugin namespace
    '''
    def _find_in_cache(name, key):
        for setting in _settings[namespace]:
            if setting["name"] == name:
                return setting[key]
        return None

    def _type_map(t):
        """Return setting python type"""
        if t == BOOL:
            return bool
        elif t == NUMBER:
            return float
        else:
            return unicode

    namespace = namespace or _callerName().split(".")[0]
    full_name = namespace + "/" + name
    if settings.contains(full_name):
        if typ is None:
            typ = _type_map(_find_in_cache(name, 'type'))
        v = settings.value(full_name, None, type=typ)
        try:
            if isinstance(v, QPyNullVariant):
                v = None
        except:
            pass
        return v
    else:
        return _find_in_cache(name, 'default')

def pluginSettings(namespace=None):
    namespace = namespace or _callerName().split(".")[0]
    return _settings.get(namespace, {})

_settings = {}
def readSettings(settings_path=None):
    global _settings
    '''
    Reads the settings corresponding to the plugin from where the method is called.
    This function has to be called in the __init__ method of the plugin class.
    Settings are stored in a settings.json file in the plugin folder.
    Here is an eample of such a file:

    [
    {"name":"mysetting",
     "label": "My setting",
     "description": "A setting to customize my plugin",
     "type": "string",
     "default": "dummy string",
     "group": "Group 1"
     "onEdit": "def f():\\n\\tprint "Value edited in settings dialog"
     "onChange": "def f():\\n\\tprint "New settings value has been saved"
    },
    {"name":"anothersetting",
      "label": "Another setting",
     "description": "Another setting to customize my plugin",
     "type": "number",
     "default": 0,
     "group": "Group 2"
    },
    {"name":"achoicesetting",
     "label": "A choice setting",
     "description": "A setting to select from a set of possible options",
     "type": "choice",
     "default": "option 1",
     "options":["option 1", "option 2", "option 3"],
     "group": "Group 2"
    }
    ]

    Available types for settings are: string, bool, number, choice, crs and text (a multiline string)

    The onEdit property contains a function that will be executed when the user edits the value
    in the settings dialog. It shouldl return false if, after it has been executed, the setting
    should not be modified and should recover its original value.

    The onEdit property contains a function that will be executed when the setting is changed after
    closing the settings dialog, or programatically by callin the setPluginSetting method

    Both onEdit and onChange are optional properties

    '''

    namespace = _callerName().split(".")[0]
    settings_path = settings_path or os.path.join(os.path.dirname(_callerPath()), "settings.json")
    with open(settings_path) as f:
        _settings[namespace] = json.load(f)


