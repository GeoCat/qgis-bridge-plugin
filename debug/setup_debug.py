"""
PyCharm <-> QGIS Bridge Remote Debugger Setup:
Prepares the QGIS Bridge plugin.py for remote debugging in PyCharm (Windows).
It will inject remote debug code before the `GeocatBridge` class definition.

This only needs to be run once when you start debugging for the first time
or when you have modified the plugin.py module.

This script allows you to change the host and port for the remote debugger.
Make sure that these settings reflect the ones in your Debug Configuration.

Once you finished debugging, please make sure to rollback plugin.py before
committing your changes to the Git repository.
"""

from pathlib import Path
import inspect
import argparse
import shutil

# This is the code that will be injected to enable remote debugging
_CODE = """
# Enable PyCharm remote debugger, if debug folder exists
_debug_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '{0}'))
if os.path.isdir(_debug_dir):
    sys.path.append(_debug_dir)
    import pydevd_pycharm
    from warnings import simplefilter
    try:
        # Suppress ResourceWarning when remote debug server is not running
        simplefilter('ignore', category=ResourceWarning)
        pydevd_pycharm.settrace('{1}', True, True, {2})
    except (ConnectionRefusedError, AttributeError):
        # PyCharm remote debug server is not running on {1}:{2}
        # Restore ResourceWarnings
        simplefilter('default', category=ResourceWarning)    
"""

# This is the code line before which to inject the debug code
# It is case-insensitive and trailing whitespace is removed,
# but other than that, it must exactly match the full code line
_SEARCH = 'class GeoCatBridge:'

# Default remote debug server settings
_HOST = 'localhost'
_PORT = 53100

# Default folder name
_REMOTE_DEBUG_DIR = '_debug'


def get_curdir() -> Path:
    """ Gets the current directory of this script file. """
    return Path(inspect.getfile(inspect.currentframe())).absolute().parent


def get_args() -> list:
    """ Parses the CLI arguments. """
    parser = argparse.ArgumentParser(Path(__file__).name, description=__doc__)
    parser.add_argument('plugin_py', type=str, help='Path to the Bridge plugin.py')
    parser.add_argument('pydevd_egg', type=str, help='Path to the pycharm-pydevd.egg')
    parser.add_argument('--debug_dir', type=str, help='Name of the target debug directory', default=_REMOTE_DEBUG_DIR)
    parser.add_argument('--host', type=str, help='Remote debugger host address', default=_HOST)
    parser.add_argument('--port', type=int, help='Remote debugger port', default=_PORT)
    ns = parser.parse_args()
    args = [
        Path(ns.plugin_py).absolute(),
        Path(ns.pydevd_egg).absolute()
    ]
    if any(not x.exists() for x in args):
        raise argparse.ArgumentTypeError('A path was specified that does not exist')
    return args + [ns.debug_dir, ns.host, ns.port]


def extract_egg(source: Path, target: Path, work_dir: Path):
    """ Extracts a Python egg to a given target folder. """
    # First copy the egg to our debug directory and give it a zip extension
    pydevd_zip = work_dir / source.with_suffix('.zip').name
    shutil.copy2(source, pydevd_zip)
    # Now do the actual unzipping
    print(f'Extracting contents of {source} to {target}...')
    shutil.unpack_archive(pydevd_zip, target)
    print(f'Contents extracted successfully')


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


def main(plugin_py: Path, pydevd_egg: Path, debug_dir: str = _REMOTE_DEBUG_DIR, host: str = _HOST, port: int = _PORT):
    """ Main function to start debug setup. """
    cur_dir = get_curdir()
    dest_debug_dir = plugin_py.parent / debug_dir
    local_py = cur_dir / plugin_py.name

    # Backup plugin.py file
    if not local_py.exists():
        print(f'Creating backup of {plugin_py} in {cur_dir}...')
        shutil.copy2(plugin_py, local_py)
    print(f'Using backup {local_py} for code injection')

    # Extract PyCharm pydevd egg to destination debug directory
    if not dest_debug_dir.exists():
        extract_egg(pydevd_egg, dest_debug_dir, cur_dir)

    # Inject debug code
    code = _CODE.format(debug_dir, host, port)
    inject_debug(local_py, plugin_py, code)


if __name__ == '__main__':
    main(*get_args())
