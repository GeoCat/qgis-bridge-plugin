"""
This script generates documentation based on the content of the current
repo, for the current master HEAD (if run with '--version latest' argument or
without arguments), all available tags (if run with the '--version all' argument),
or the latest available tag (if the '--version stable' argument is used)

The script file should be located in the documentation folder (with sphinx files
under ./source folder)

You can specify the output folder in which docs are to be produced, by using the
'--output [path]' argument. If not used, the documentation will be created under the
./build folder.
"""

import sys
import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Tuple

NAME = "GeoCat Bridge"
DEFAULT_DIR = "../build/docs"
THEMES_DIRNAME = "themes"
THEMES_REPO = "https://github.com/GeoCat/geocat-themes.git"
THEME_GEOCAT = "geocat_rtd"
THEME_RTD = "sphinx_rtd_theme"
VERSION_PREFIX = "v"
VERSION_REGEX = re.compile(rf"^{VERSION_PREFIX}(\d+)\.(\d+)\.(\d+)[-.]?(\w*)$")

# Version build options
V_ALLVER = 'all'
V_STABLE = 'stable'
V_LATEST = 'latest'


def printif(value):
    if value in (None, ''):
        return
    print(value)


def sh(cmd: str) -> Tuple[int, str]:
    """ Execute a shell command. """
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    stdout, _ = proc.communicate()
    return proc.returncode, stdout.decode("utf-8")


def clear_target(folder: Path):
    """ Empties (clears) the given target folder. """
    print(f"Removing folder '{folder}'...")
    shutil.rmtree(folder, ignore_errors=True)


def build_docs(src_dir: Path, dst_dir: Path, version: str, html_theme: str = None) -> int:
    """ Build HTML docs for the given version type in the given target folder. """
    results = []
    if version in (V_LATEST, V_ALLVER):
        # Also build latest if "all versions" was specified
        result = build_tag(src_dir, dst_dir, V_LATEST, html_theme)
        if version == V_LATEST:
            return result
        results.append(result)

    tags = get_tags()
    if not tags:
        return 1
    if version == V_STABLE:
        latest_key = sorted(tags.keys(), reverse=True)[0]
        latest_tag = tags[latest_key]
        print(f"Latest stable tag is {latest_tag}")
        results.append(build_tag(src_dir, dst_dir, latest_tag, html_theme))
    elif version == V_ALLVER:
        for _, tag in sorted(tags.items(), reverse=True):
            results.append(build_tag(src_dir, dst_dir, tag, html_theme))
    return 1 if any(results) else 0


def current_branch():
    """ Gets the current branch name. Returns None if the current branch could not be determined. """
    # Note: "git branch --show-current" does not work on older Git versions
    exit_code, sym_ref = sh("git symbolic-ref HEAD")
    if exit_code:
        # If command failed, force an error below
        sym_ref = None
    try:
        return sym_ref.strip().split('/')[-1]
    except (AttributeError, ValueError, TypeError, IndexError):
        print("Failed to determine current branch")
        return


def is_dirty() -> bool:
    """ Returns True if the current branch is dirty (i.e. has uncommitted edits). """
    exit_code, result = sh("git diff --stat")
    if exit_code:
        # Presume dirty if git command failed
        print('Failed to check if working branch is clean')
        return True
    if not result.strip():
        # Empty response: no differences
        print('Working branch is clean')
        return False
    lines = list(ln.strip() for ln in result.splitlines())
    if len(lines) == 2:
        # Only one difference found: check if it is a submodule (which can be ignored)
        exit_code, sub_result = sh("git submodule")
        if exit_code:
            # Presume dirty if git command failed
            return True
        submodules = tuple(ln.split()[1] for ln in sub_result.splitlines())
        return any(ln for ln in lines if ln.startswith(submodules))
    else:
        return True


def checkout(branch: str = None) -> Tuple[int, str]:
    """ Checks out the given branch name or master/main if omitted. """
    if not branch:
        branch = ''
    return sh(f"git checkout {branch} --recurse-submodules")


def get_tags(retry: bool = True):
    """ Returns a dictionary of {(major, minor, build, suffix): tag-string} for all valid Git tags. """
    print(f"Listing available git tags with '{VERSION_PREFIX}' prefix...")
    result = {}
    exit_code, tags = sh("git tag -l")
    if exit_code or not tags.strip():
        print("Failed to retrieve tags")
        if not tags.strip() and retry:
            print("Fetching tags from remote and retrying...")
            exit_code, _ = sh("git fetch --tags")
            if not exit_code:
                return get_tags(False)
            else:
                print("Failed to fetch tags from remote")
        return result
    for tag in (t.strip() for t in (tags or '').splitlines()):
        m = VERSION_REGEX.match(tag)
        if not m or len(m.groups()) != 4:
            # Skip non-(stable-)version tags
            print(f"\t{tag} (skipped)")
            continue
        print(f"\t{tag}")
        groups = tuple(int(g or 0) for g in m.groups()[:3]) + (m.groups()[3],)  # noqa
        result[groups] = tag
    return result


def build_tag(src_root: Path, dst_root: Path, version: str, html_theme: str = None) -> int:
    """
    Checks out a specific version tag on the current branch and builds the documentation.

    :param src_root:    The root folder of the documentation source files.
                        This usually is the same path as the directory that contains this builddocs.py script file.
    :param dst_root:    The destination folder in which to build all documentation versions.
    :param version:     The version for which to build documentation ('latest' or a tag).
    :param html_theme:  An optional override to apply to the Sphinx HTML theme.
                        If omitted, the theme as configured in conf.py is used.
    """
    if version != V_LATEST:
        # Check out the correct tag (use force option)
        print(f"Checking out {version} tag...")
        exit_code, result = checkout(f"-f tags/{version}")
        if exit_code:
            print(f"Failed to check out tag '{version}'", file=sys.stderr, flush=True)
            return exit_code
        # Remove patch suffix from version tag
        version = '.'.join(version.split('.')[:2])
    src_dir = src_root / "source"
    bld_dir = dst_root / version
    if os.path.exists(bld_dir):
        shutil.rmtree(bld_dir)
    os.makedirs(bld_dir)
    override = ''
    if html_theme:
        print(f"HTML theme override '{html_theme}' will be applied")
        override = f'-D html_theme={html_theme}'
    print(f"Building HTML documentation for {NAME} {version if version != V_LATEST else f'({V_LATEST})'}")
    exit_code, result = sh(f"sphinx-build -a {override} {src_dir} {bld_dir}")
    printif(result)
    if exit_code:
        print("Failed to build docs", file=sys.stderr, flush=True)
    return exit_code


def main():
    parser = argparse.ArgumentParser(description=f'Build {NAME} HTML documentation')
    parser.add_argument('--output', help=f'Output directory (default={DEFAULT_DIR})')
    parser.add_argument('--clean', action='store_true', help='Clear entire output directory before run')
    parser.add_argument('--version', help=f"Version to build: must be a tag (e.g. '{VERSION_PREFIX}1.2.3') or "
                                          f"'{V_LATEST}' (default if omitted), '{V_STABLE}' or '{V_ALLVER}')")
    parser.add_argument('--branch', help='Optional branch to check out (if not the default branch)')
    parser.add_argument('--theme', help=f"Override the default ReadTheDocs ('{THEME_RTD}') HTML theme in conf.py.\n"
                                        f"Choose between the '{THEME_GEOCAT}' theme or any of the Sphinx built-ins.")
    parser.set_defaults(clean=False)

    # Parse arguments
    args = parser.parse_args()
    version = (args.version or '').strip() or None

    if not version:
        # Get version from GitHub ref tag, if any (i.e. for release event)
        gh_ref = os.environ.get('GITHUB_REF', '')
        if gh_ref.startswith('refs/tags/'):
            tag = gh_ref[10:]
            if VERSION_REGEX.match(tag):
                print(f"Found tag in $GITHUB_REF {gh_ref}: using {tag} as --version argument")
                version = tag

    # Check final version argument
    if version not in (V_LATEST, V_STABLE, V_ALLVER, None) and not VERSION_REGEX.match(version):
        print(f"incorrect --version '{version}' specified", file=sys.stdout, flush=True)
        print(f"--version must be a tag (e.g. '{VERSION_PREFIX}1.2.3') or "
              f"'{V_LATEST}' (default if omitted), '{V_STABLE}' or '{V_ALLVER}'")
        sys.exit(2)
    else:
        if version is None:
            print(f"No --version specified: using default")
            version = V_LATEST
        print(f"Script set to build version '{version}'")

    result = 1
    current = None
    has_edits = None
    try:
        curdir = Path.cwd().resolve(strict=True)
        sys.path.insert(0, str(curdir))
        docsrc_dir = Path(__file__).parent.resolve(strict=True)
        if docsrc_dir.parent != curdir:
            sys.path.insert(1, str(docsrc_dir.parent))
        themes_dir = docsrc_dir / THEMES_DIRNAME

        # Try import something from geocatbridge (conf.py requires it)
        from geocatbridge.utils import meta

        folder = Path(args.output).resolve() if args.output else (docsrc_dir / DEFAULT_DIR).resolve()
        if args.clean:
            clear_target(folder)

        # Temporarily disable detached HEAD warnings
        sh("git config advice.detachedHead false")

        # Clone themes from Git if not present
        if not (themes_dir / '.git').exists():
            clear_target(themes_dir)
            os.chdir(docsrc_dir)
            print(f"Cloning '{THEMES_DIRNAME}' from {THEMES_REPO}...")
            exit_code, _ = sh(f'git clone {THEMES_REPO} {THEMES_DIRNAME}')
            if exit_code:
                print(f"Failed to clone {THEMES_REPO} into {docsrc_dir / THEMES_DIRNAME}", file=sys.stdout, flush=True)
                sys.exit(exit_code)
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
        elif current != working:
            print(f"Checking out {working if working else 'default'} branch...")
            exit_code, output = checkout(working)
            if exit_code:
                print(f"Failed to check out {working if working else 'default'} branch", file=sys.stdout, flush=True)
                sys.exit(exit_code)
            else:
                print(output)

        # Build HTML docs
        result = build_docs(docsrc_dir, folder, version, (args.theme or '').strip() or None)

    except SystemExit as err:
        result = err.code
    except Exception as err:
        print(f"Aborted script because of unhandled {type(err).__name__}: {err}", file=sys.stderr, flush=True)
        if isinstance(err, (ImportError, ModuleNotFoundError)):
            sep = '\n\t'
            print(f"Python paths:{sep}{f'{sep}'.join(sys.path)}")
    finally:
        # Restore Git repo if there were no errors
        if not result and current and not has_edits:
            print(f"Restoring initially checked out {current} branch...")
            exit_code, output = checkout(current)
            if exit_code:
                print(f"Failed to check out {current if current else 'default'} branch", file=sys.stdout, flush=True)
            else:
                print(output)
        print("Done")
        sys.exit(result)


if __name__ == "__main__":
    main()
