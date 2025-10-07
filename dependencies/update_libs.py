"""
Setup script to clone and checkout project dependencies.
Alternative to git submodules for simpler dependency management.

Configuration is defined in config.json file in this directory.
"""
import json
import os
import sys
import shutil
from pathlib import Path

from scripts.shared import execute_subprocess, get_rootdir

CONFIG_FILE = 'config.json'


def get_parent_dir():
    """Returns the full path to the directory this script is in."""
    return Path(__file__).resolve().parent


def setup_dependency(name: str, url: str, main_branch: str = 'main', version: str = 'latest', **kwargs):
    """Clone and checkout a specific version of a dependency."""
    deps_dir = get_parent_dir()
    deps_dir.mkdir(exist_ok=True)

    working_dir = Path(os.getcwd()).resolve()
    dep_dir = deps_dir / name

    try:
        if dep_dir.exists():
            print(f"Updating {name}...")
            os.chdir(dep_dir)
            execute_subprocess('git fetch --tags')
            execute_subprocess('git fetch origin')
        else:
            print(f"Cloning {name} from {url} to {dep_dir}...")
            execute_subprocess(f'git clone {url} "{dep_dir}"')
            os.chdir(dep_dir)

        if version == 'latest':
            # Get latest tag
            exit_code, latest_tag = execute_subprocess('git describe --tags --abbrev=0')
            if exit_code == 0 and latest_tag.strip():
                print(f"Found latest tag: {latest_tag}")
                version = latest_tag.strip()
            else:
                print(f"No latest tag found: falling back to main branch")
                version = main_branch  # fallback to main branch

        print(f"Checking out {version}...")
        execute_subprocess(f'git checkout {version}')
    finally:
        os.chdir(working_dir)


def clear_folder_contents(folder_path):
    """Remove all contents from all subfolders in the given folder."""
    folder = Path(folder_path)

    if not folder.exists():
        print(f"Folder {folder_path} does not exist")
        return

    # Iterate through all subdirectories in folder
    for subfolder in folder.iterdir():
        if subfolder.is_dir():
            print(f"Clearing contents of {subfolder.name}...")

            # Remove all contents but keep the subfolder itself
            for item in subfolder.iterdir():
                if item.is_file():
                    item.unlink()  # Remove file
                    print(f"  Removed file: {item.name}")
                elif item.is_dir():
                    shutil.rmtree(item)  # Remove directory and all contents
                    print(f"  Removed directory: {item.name}")


def dependency_to_lib(target_dir: str, name: str, source_dir: str, **kwargs):
    """Copies the source_dir of the given dependency name to target_dir."""
    root_dir = get_rootdir()
    target_dir = root_dir / target_dir
    target_dir.mkdir(exist_ok=True)

    source_path = get_parent_dir() / name / source_dir
    target_path = target_dir / name

    if not source_path.exists():
        raise NotADirectoryError(f"source directory {source_path} does not exist - please check {CONFIG_FILE}")

    if target_path.exists():
        clear_folder_contents(target_path)
    else:
        target_path.mkdir(parents=True)

    for item in source_path.iterdir():
        if item.is_file():
            shutil.copy2(item, target_path)
            print(f"  Copied file: {item.name}")
        elif item.is_dir():
            shutil.copytree(item, target_path / item.name, dirs_exist_ok=True)
            print(f"  Copied directory: {item.name}")


def main():
    """Setup all project dependencies."""
    print(f"Searching and reading {CONFIG_FILE}...")
    try:
        config = json.load(open(CONFIG_FILE))
    except FileNotFoundError:
        print(f"❌ {CONFIG_FILE} not found")
        sys.exit(1)

    target_dir = config.get('target_dir')
    dependencies = config.get('dependencies')
    if not target_dir:
        print(f"❌ target_dir not found in {CONFIG_FILE}")
        sys.exit(1)
    if not dependencies:
        print(f"⚠️ No dependencies found in {CONFIG_FILE}: nothing to do")
        sys.exit(0)

    print("Setting up project dependencies...")

    for dep in dependencies:
        try:
            setup_dependency(**dep)
            print(f"✅ {dep['name']} updated successfully")
            dependency_to_lib(target_dir, **dep)
            print(f"✅ {dep['name']} copied to '{target_dir}/'")
        except Exception as e:
            print(f"❌ Failed to update {dep['name']}: {e}")
            sys.exit(1)

    print("\n✅ Finished dependency updates")


if __name__ == '__main__':
    main()
