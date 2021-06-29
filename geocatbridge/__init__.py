# coding: utf-8

import site
from pathlib import Path

# Make sure that all available Bridge libs can be imported (e.g. bridgestyle):
# This avoids having to do "from geocatbridge.libs.libdir.libpackage import libmodule"
# and allows us to do "from libpackage import libmodule" instead.
libs_dir = Path(__file__).parent.resolve() / 'libs'
for subdir in libs_dir.glob('./*'):
    # Only add subdir paths if subdir contains a Python package
    if any(subdir.rglob('__init__.py')):
        site.addsitedir(subdir)


def classFactory(iface):
    from .plugin import GeocatBridge
    return GeocatBridge(iface)
