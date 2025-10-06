"""
Setup script to clone and checkout project dependencies.
Alternative to git submodules for simpler dependency management.
"""

import os
import sys
import shutil
from pathlib import Path
from shared import execute_subprocess


TARGET_DIR = 'geocatbridge/libs'
DEPENDENCY_DIRNAME = 'dependencies'
DEPENDENCIES = [
    {
        'name': 'bridgestyle',
        'url': 'https://github.com/GeoCat/bridge-style.git',
        'version': 'latest',  # or specific tag like 'v1.2.3'
        'main_branch': 'master',
        'source_dir': 'src/bridgestyle'
    },
    # Add more dependencies here
]


def get_root_dir():
    """ Returns the root directory of the project (i.e. the parent of the /scripts folder)."""
    return Path(__file__).resolve().parent.parent


def setup_dependency(name: str, url: str, main_branch: str = 'main', version: str = 'latest', **kwargs):
    """Clone and checkout a specific version of a dependency."""
    deps_dir = get_root_dir() / DEPENDENCY_DIRNAME
    deps_dir.mkdir(exist_ok=True)

    working_dir = Path(os.getcwd()).resolve()
    dep_dir = deps_dir / name

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


def dependency_to_lib(name: str, source_dir: str, **kwargs):
    """Copies the source_dir of the given dependency name to TARGET_DIR."""
    root_dir = get_root_dir()
    target_dir = root_dir / TARGET_DIR
    target_dir.mkdir(exist_ok=True)

    source_path = root_dir / DEPENDENCY_DIRNAME / name / source_dir
    target_path = target_dir / name

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
    print("Setting up project dependencies...")

    for dep in DEPENDENCIES:
        try:
            setup_dependency(**dep)
            print(f"✅ {dep['name']} updated successfully")
            dependency_to_lib(**dep)
            print(f"✅ {dep['name']} copied to '{TARGET_DIR}/'")
        except Exception as e:
            print(f"❌ Failed to update {dep['name']}: {e}")
            sys.exit(1)

    print("\nFinished dependency updates")
    print(f"Dependency sources are located in the '{DEPENDENCY_DIRNAME}/' folder")


if __name__ == '__main__':
    main()
