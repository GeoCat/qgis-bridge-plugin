""" Build index HTML page from directory listing

docs_index.py </path/to/directory>
"""
import os
import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Tuple

from mako.template import Template

VERSION_PREFIX = 'v'
VERSION_LATEST = 'latest'
HTML_TEMPLATE = 'index_template.html'
HTML_OUTPUT = 'index.html'


def is_version(value: str):
    """ Returns True if the given value is version-like (i.e. 'v{major}.{minor}'). """
    return value.startswith(VERSION_PREFIX) and value.count('.') == 1


def sortable_version(value: str):
    """ Formats the given directory name as sortable version string.
    If it does not have a version-like name, the string is returned as-is.
    """
    if not is_version(value):
        return value
    try:
        major, minor = value[1:].split('.')
        return f'{VERSION_PREFIX}{major:0>4}.{minor:0>2}'
    except (ValueError, IndexError):
        return value


def is_docsdir(d: Path) -> bool:
    """ Returns True if the given directory path is a valid documentation directory. """
    return d.is_dir() and (is_version(d.name) or d.name == VERSION_LATEST)


def sh(cmd: str) -> Tuple[int, str]:
    """ Execute a shell command. """
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    stdout, _ = proc.communicate()
    return proc.returncode, stdout.decode("utf-8")


def is_dirty(git_dir: Path) -> bool:
    """ Returns True if the current branch is dirty (i.e. has uncommitted edits). """
    curdir = Path.cwd().resolve()
    os.chdir(git_dir)
    print(f"Checking if '{git_dir.name}' has updates...")
    exit_code, result = sh("git diff --stat")
    os.chdir(curdir)
    if exit_code:
        print('Failed to check if working branch is clean', file=sys.stderr, flush=True)
        sys.exit(126)
    if not result.strip():
        # Empty response: no differences
        print('Working branch is clean')
        return False
    print(result)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", help="Directory path for which to index its folders "
                                          "(and where index.html must be generated)")
    args = parser.parse_args()

    dir_path = Path(args.directory).resolve()
    if not dir_path.exists():
        print(f"Directory path '{dir_path}' does not exist", file=sys.stderr, flush=True)
        sys.exit(2)

    # If gh-pages branch is clean, there's no need to update the index
    if not is_dirty(dir_path):
        print(f"The {dir_path.name} directory is clean: no docs have been updated", file=sys.stderr, flush=True)
        sys.exit(126)

    # Find local version folders and sort in appropriate order
    print("Listing available docs folders...")
    versions = {sortable_version(d.name): d.name for d in dir_path.iterdir() if is_docsdir(d)}
    if VERSION_LATEST not in versions:
        print(f"No '{VERSION_LATEST}' docs version folder found: cannot continue", file=sys.stderr, flush=True)
        sys.exit(1)
    vkeys = sorted(versions.keys(), reverse=True)
    vkeys.insert(0, vkeys.pop())
    names = [versions[v] for v in vkeys]
    for name in names:
        print(f'->\t{name}')

    # Render HTML page from template
    try:
        print(f"Reading {HTML_TEMPLATE} file...")
        with open(Path(__file__).parent / HTML_TEMPLATE) as f:
            tpl = f.read()
        print(f"Rendering HTML...")
        html = Template(tpl).render(names=names, year=datetime.now().year)
        print(f"Updating {HTML_OUTPUT} file...")
        with open(dir_path / HTML_OUTPUT, 'w+') as f:
            f.write(html)
    except Exception as err:
        print(f"Aborted script because of unhandled {type(err).__name__}: {err}", file=sys.stderr, flush=True)
        sys.exit(1)
    else:
        print("Done")


if __name__ == '__main__':
    main()
