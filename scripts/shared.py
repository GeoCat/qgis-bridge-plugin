import inspect
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple


def update_winenv_path():
    """ Updates the PATH environment variable on Windows by adding the system PATH.
    In newer Python environments, the user PATH variable is used instead of the system PATH,
    which causes some commands to not be found.
    """

    if os.name != 'nt':
        # Not Windows: nothing to do
        return

    cmd = 'reg query "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v Path'
    proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, _ = proc.communicate()
    # Extract the PATH value
    path_line = [line for line in stdout.split('    ')][-1]
    if path_line and ';' in path_line:
        paths = f"{os.environ.get('PATH', '')};{path_line.strip()}"
        os.environ['PATH'] = paths


def execute_subprocess(cmd: str) -> Tuple[int, str]:
    """ Execute a command in a subprocess. Returns a tuple of (exit code, stdout). """
    args = shlex.split(cmd)
    exe = args[0]
    if not Path(exe).exists():
        # Try to find the executable in the PATH
        exe = shutil.which(args[0])
        if not exe:
            print(f"Executable '{args[0]}' not found - retrying...")
            update_winenv_path()
        # Retry with updated PATH (on Windows only)
        exe = shutil.which(args[0])
        if not exe:
            print(f"Executable '{args[0]}' not found - giving up", file=sys.stderr, flush=True)
            return 1, "Failed to execute command 'cmd'"
        print(f"Found executable '{exe}'")
        args[0] = exe
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    stdout, _ = proc.communicate()
    return proc.returncode, stdout.decode("utf-8")


def get_workdir() -> Path:
    """ Gets the current working directory (i.e. from where the script is being called). """
    return Path(inspect.getfile(inspect.currentframe())).absolute().parent
