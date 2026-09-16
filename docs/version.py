"""
mkdocs-macros hook providing the plugin name/version variables that used to be
Sphinx `rst_epilog` substitutions (|app_name|, |short_name|, etc.), sourced from
geocatbridge/metadata.txt via geocatbridge.utils.meta.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geocatbridge.utils import meta  # noqa: E402


def define_env(env):
    app_name = meta.getAppName()
    short_name = meta.getShortAppName()

    env.variables["app_name"] = app_name
    env.variables["short_name"] = short_name
    env.variables["long_name"] = meta.getLongAppName()
    env.variables["plugin_name"] = f"{app_name} for QGIS"
    env.variables["menu_name"] = f"Web/{app_name}"
    env.variables["publisher"] = "GeoCat"
    env.variables["app_url"] = meta.getHomeUrl()
    env.variables["min_qgis_ver"] = meta.getQqisMinimumVersion()
    env.variables["version"] = str(meta.getVersion())
