"""
This script generates documentation based on the content of the current
repo, for the current master HEAD (if run with '--version latest' argument or
without arguments), all available tags (if run with the '--version all' argument),
or the latest available tag (if the '--version stable' argument is used)

The script file should be located in the documentation folder (with sphinx files
under ./content folder)

You can specify the output folder in which docs are to be produced, by using the
'--output [path]' argument. If not used, the documentation will be created under the
./build folder.
"""

import sys
import argparse
import os
import shutil
import subprocess
from pathlib import Path
from re import compile

NAME = "GeoCat Bridge"
DEFAULT_DIR = "../build/docs"
THEMES_DIRNAME = "themes"
THEMES_REPO = "https://github.com/GeoCat/geocat-themes.git"
VERSION_PREFIX = "v"
VERSION_REGEX = compile(rf"^{VERSION_PREFIX}(\d+)\.(\d+)\.(\d+)[-.]?(\w*)$")

# Version build options
V_ALLVER = 'all'
V_STABLE = 'stable'
V_LATEST = 'latest'


def sh(commands):
    """ Execute a shell command. """
    if isinstance(commands, str):
        commands = commands.split()
    out = subprocess.Popen(commands, stdout=subprocess.PIPE)
    stdout, stderr = out.communicate()
    return stdout.decode("utf-8")


def clear_target(folder: Path):
    """ Empties (clears) the given target folder. """
    print(f"Removing folder '{folder}'...")
    shutil.rmtree(folder, ignore_errors=True)


def build_docs(src_dir: Path, dst_dir: Path, version: str):
    """ Build HTML docs for the given version type in the given target folder. """
    if version in (V_LATEST, V_ALLVER):
        # Also build latest if "all versions" was specified
        build_tag(src_dir, dst_dir, V_LATEST)
        if version == V_LATEST:
            return

    tags = get_tags()
    if version == V_STABLE:
        latest_key = next(sorted(tags, reverse=True))
        latest_tag = tags[latest_key]
        print(f"Latest stable tag is {latest_tag}")
        build_tag(src_dir, dst_dir, latest_tag)
    elif version == V_ALLVER:
        for _, tag in sorted(tags.items()):
            build_tag(src_dir, dst_dir, tag)


def current_branch():
    """ Gets the current branch name. Returns None if the current branch could not be determined. """
    # return sh("git branch --show-current").strip() or None
    sym_ref = sh("git symbolic-ref HEAD")
    try:
        return sym_ref.strip().split('/')[-1]
    except (AttributeError, ValueError, TypeError, IndexError):
        return


def is_dirty() -> bool:
    """ Returns True if the current branch is dirty (i.e. has uncommitted edits). """
    return sh("git diff --stat").strip() != ''


def checkout(branch: str = None):
    """ Checks out the given branch name or master/main if omitted. """
    if not branch:
        branch = ''
    sh(f"git checkout {branch} --recurse-submodules")


def get_tags():
    """ Returns a dictionary of {(major, minor, build, suffix): tag-string} for all valid Git tags. """
    print(f"Listing available git tags with '{VERSION_PREFIX}' prefix...")
    result = {}
    tags = sh("git tag -l") or ''
    for tag in (t.strip() for t in tags.splitlines()):
        m = VERSION_REGEX.match(tag)
        if not m or not len(m.groups()) == 4:
            # Skip non-(stable-)version tags
            print(f"\t{tag} (skipped)")
            continue
        print(f"\t{tag}")
        groups = tuple(int(g or 0) for g in m.groups()[:3]) + (m.groups()[3],)  # noqa
        result[groups] = tag
    return result


def build_tag(src_dir: Path, dst_dir: Path, version: str):
    """ Checks out a specific version tag on the current branch and builds the documentation. """
    if version != V_LATEST:
        # Check out the correct tag
        sh(f"git checkout tags/{version} --recurse-submodules")
    src_dir = src_dir / "content"
    bld_dir = dst_dir / version
    if os.path.exists(bld_dir):
        shutil.rmtree(bld_dir)
    os.makedirs(bld_dir)
    print(f"Building HTML documentation for {NAME} {version if version != V_LATEST else f'({V_LATEST})'}")
    sh(f"sphinx-build -a {src_dir} {bld_dir}")


def main():
    parser = argparse.ArgumentParser(description=f'Build {NAME} HTML documentation')
    parser.add_argument('--output', help=f'Output directory (default={DEFAULT_DIR})')
    parser.add_argument('--clean', action='store_true', help='Clear entire output directory before run')
    parser.add_argument('--version', default=V_LATEST,
                        help=f"Version to build: must be a tag (e.g. '{VERSION_PREFIX}1.2.3') or "
                             f"'{V_LATEST}' (default if omitted), '{V_STABLE}' or '{V_ALLVER}')")
    parser.add_argument('--branch', help='Optional branch to check out (if not the default branch)')
    parser.set_defaults(clean=False)

    # Parse arguments, check version arg
    args = parser.parse_args()
    version = args.version.strip() or V_LATEST
    if version not in (V_LATEST, V_STABLE, V_ALLVER) and not VERSION_REGEX.match(version):
        print(f"--version must be a tag (e.g. '{VERSION_PREFIX}1.2.3') or "
              f"'{V_LATEST}' (default if omitted), '{V_STABLE}' or '{V_ALLVER}'")
        sys.exit(2)

    curdir = Path.cwd()
    docsrc_dir = Path(__file__).parent.resolve()
    themes_dir = docsrc_dir / THEMES_DIRNAME
    folder = Path(args.output).resolve() if args.output else (docsrc_dir / DEFAULT_DIR).resolve()
    if args.clean:
        clear_target(folder)

    # Update/clone themes
    if (themes_dir / '.git').exists():
        os.chdir(themes_dir)
        checkout()
    else:
        clear_target(themes_dir)
        os.chdir(docsrc_dir)
        sh(f'git clone {THEMES_REPO} {THEMES_DIRNAME}')
    os.chdir(curdir)

    # Checkout tag/latest
    has_edits = is_dirty()
    current = current_branch()
    working = current or args.branch
    if has_edits:
        print(f"Current branch{f' {repr(current)}' or ''} has edits: can only build {V_LATEST} version")
        if version == V_STABLE:
            print(f"Cannot build {V_STABLE} version")
            sys.exit(1)
        # If user selected "all", only build "latest"
        version = V_LATEST
    else:
        checkout(working)

    # Build HTML docs
    build_docs(docsrc_dir, folder, version)

    # Restore Git repo if needed
    if current and not has_edits:
        print(f"Restoring previously checked out branch '{current}'")
        checkout(current)


if __name__ == "__main__":
    main()
