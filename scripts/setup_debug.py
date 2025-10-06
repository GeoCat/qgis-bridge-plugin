"""
PyCharm <-> QGIS Bridge Remote Debugger Setup:
Prepares the QGIS Bridge plugin.py for remote debugging in PyCharm (Windows).
It will inject remote debug code before the `GeocatBridge` class definition.

This only needs to be run once when you start debugging for the first time
or when you have modified the plugin.py module.

NOTE: please make sure that you have installed the `pydevd-pycharm` package
in your virtual environment, as it cannot run without it.

This script allows you to change the host and port for the remote debugger.
Make sure that these settings reflect the ones in your Debug Configuration.

Once you finished debugging, please make sure to rollback plugin.py before
committing your changes to the Git repository.
"""

import argparse
import os
import stat
import shutil
from pathlib import Path

from shared import get_workdir

# This is the code that will be injected to enable remote debugging
_CODE = """
# Enables PyCharm remote debugger - DO NOT COMMIT!
import pydevd_pycharm
from warnings import simplefilter
try:
    # Suppress ResourceWarning when remote debug server is not running
    simplefilter('ignore', category=ResourceWarning)
    pydevd_pycharm.settrace('{0}', True, True, {1})
except (ConnectionRefusedError, AttributeError):
    # PyCharm remote debug server is not running on {0}:{1}
    # Restore ResourceWarnings
    simplefilter('default', category=ResourceWarning)    
"""

# This is the code line before which to inject the debug code
# It is case-insensitive and trailing whitespace is removed,
# but other than that, it must exactly match the full code line
_SEARCH = 'class GeoCatBridge:'

# Default remote debug server settings
_HOST = 'localhost'
_PORT = 6666

# Default folder name
_REMOTE_DEBUG_DIR = '_debug'


def get_args() -> list:
    """ Parses the CLI arguments. """
    parser = argparse.ArgumentParser(Path(__file__).name, description=__doc__)
    parser.add_argument('plugin_py', type=str, help='Path to the Bridge plugin.py')
    parser.add_argument('--host', type=str, help='Remote debugger host address', default=_HOST)
    parser.add_argument('--port', type=int, help='Remote debugger port', default=_PORT)
    ns = parser.parse_args()
    args = [
        Path(ns.plugin_py).absolute()
    ]
    if any(not x.exists() for x in args):
        raise argparse.ArgumentTypeError('A path was specified that does not exist')
    return args + [ns.host, ns.port]


def extract_egg(source: Path, target: Path, work_dir: Path):
    """ Extracts a Python egg to a given target folder. """

    def remove_readonly(func, path, _):
        """ Clear the readonly bit and reattempt the removal. """
        os.chmod(path, stat.S_IWRITE)
        func(path)

    # First copy the egg to our debug directory and give it a zip extension
    pydevd_zip = work_dir / source.with_suffix('.zip').name
    shutil.copy2(source, pydevd_zip)
    # Remove output directory
    if target.is_dir():
        print(f'Removing existing debugger directory {target}...')
        try:
            shutil.rmtree(target, onerror=remove_readonly)
        except PermissionError as e:
            print(e)
            print('Existing debugger directory was NOT updated')
            return
    # Now do the actual unzipping
    print(f'Extracting contents of {source} to {target}...')
    shutil.unpack_archive(pydevd_zip, target)
    print(f'Contents extracted successfully')
    os.remove(pydevd_zip)


def inject_debug(source: Path, target: Path, code: str):
    """
    Reads the backup of the original file and copies it line by line to a new destination,
    injecting the debug code at the right insertion point.
    """
    print(f'Injecting debug code into {target}...')
    with open(source, 'r') as in_file, open(target, 'w+') as out_file:
        line_found = False
        for line in in_file.readlines():
            if line.strip().casefold() == _SEARCH.strip().casefold():
                out_file.write(f'{code}\r\n')
                line_found = True
            out_file.write(f'{line}')
    if line_found:
        print('Done! Don\'t forget to rollback changes before committing!')
    else:
        raise Exception(f'Code line {_SEARCH} was not found: no debug code can be injected')


def main(plugin_py: Path, host: str = _HOST, port: int = _PORT):
    """ Main function to start debug setup. """
    try:
        import pydevd_pycharm
    except (ImportError, ModuleNotFoundError):
        raise Exception('PyCharm remote debugger package not found: '
                        'run `pip install pydevd-pycharm` in active environment')

    cur_dir = get_workdir()
    local_py = cur_dir / plugin_py.with_suffix('.py.bkp')

    # Check if plugin.py already contains the injected debug code
    with open(plugin_py) as f:
        if next(line for line in _CODE.splitlines() if line) in f.read():
            print(f'{plugin_py} already contains debug code!')
            return

    # Backup plugin.py file (always overwrite)
    print(f'Creating backup of {plugin_py} in {cur_dir}...')
    shutil.copy2(plugin_py, local_py)
    print(f'Using backup {local_py} for code injection')

    # Inject debug code
    code = _CODE.format(host, port)
    inject_debug(local_py, plugin_py, code)


if __name__ == '__main__':
    main(*get_args())
